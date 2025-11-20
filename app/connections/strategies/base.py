import functools
import time
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional, Union, Dict, Tuple, Literal

import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.engine.base import Engine
from sqlalchemy.pool import QueuePool

from app.configs.log_config import logger

# * Configuration Models
@dataclass
class DBConfig:
    db_type: str  # * Discriminator field
    host: str
    port: int
    user: str
    password: str
    database: str
    driver: Optional[str] = None
    pool_size: int = 5
    max_overflow: int = 10


@dataclass
class ODPSConfig:
    db_type: str  # * Discriminator field (always "odps")
    access_id: str
    secret_access_key: str
    default_project: str
    endpoint: str
    pool_size: int = 3
    max_overflow: int = 0  # * Not used but added for consistency


DatabaseConfig = Union[DBConfig, ODPSConfig]

# * Decorators

def timed_operation(name: str):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start = time.monotonic()
            result = func(*args, **kwargs)
            logger.info(f"{name} took {time.monotonic()-start:.2f}s")
            return result
        return wrapper
    return decorator


class DatabaseStrategy(ABC):
    """Abstract base class for database-specific operations."""

    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.db_type = config.db_type

    @abstractmethod
    def connect(self) -> None: ...

    @abstractmethod
    def disconnect(self) -> None: ...

    @abstractmethod
    def is_connected(self) -> bool: ...

    @abstractmethod
    def execute_query(
        self, query: str, params: Optional[Union[Dict[str, Any], Tuple[Any, ...]]] = None
    ) -> pd.DataFrame: ...

    @abstractmethod
    def execute_non_query(
        self, query: str, params: Optional[Union[Dict[str, Any], Tuple[Any, ...]]] = None
    ) -> int: ...

    @abstractmethod
    def create_table(
        self,
        schema: Optional[str],
        table_name: str,
        df: pd.DataFrame,
        if_exists: Literal["fail", "replace", "append"] = "fail",
        index: bool = False,
        **kwargs,
    ) -> str: ...

    @abstractmethod
    def get_connection_url(self) -> str: ...

    def _validate_schema(self, schema: Optional[str]) -> None:
        if schema and not schema.isidentifier():
            raise ValueError(
                f"[{self.db_type}] Invalid schema name '{schema}': must be a valid Python identifier"
            )

    def _mask_password(self, text: str) -> str:
        return re.sub(r"(?i)(password\s*=\s*)'[^']+'", r"\1'***'", text)


class RDBMSBaseStrategy(DatabaseStrategy, ABC):
    """Base strategy for relational databases with shared functionality."""

    def __init__(self, config: DBConfig):
        super().__init__(config)
        if not isinstance(config, DBConfig):
            raise TypeError(f"[{config.db_type}] RDBMSBaseStrategy requires DBConfig")
        self.config: DBConfig = config
        self.connection: Optional[Any] = None
        self.cursor: Optional[Any] = None
        self.engine: Optional[Engine] = None

    @abstractmethod
    def _create_connection(self) -> Any: ...

    @abstractmethod
    def _build_connection_url(self) -> str: ...

    def _supports_connection_pooling(self) -> bool:
        return self.db_type in ["postgres", "mysql", "hologres"]

    def _requires_commit(self) -> bool:
        return self.db_type not in ["trino", "hive"]

    def connect(self) -> None:
        if self.connection:
            return
        try:
            self.connection = self._create_connection()
            if self.connection:
                self.cursor = self.connection.cursor()
            self.engine = create_engine(
                self.get_connection_url(),
                poolclass=QueuePool,
                pool_size=self.config.pool_size,
                max_overflow=self.config.max_overflow,
            )
            logger.info(f"[{self.db_type}] Connected to {self.config.host}")
        except Exception as e:
            logger.error(f"[{self.db_type}] Connection failed: {e}", exc_info=True)
            raise ConnectionError(f"[{self.db_type}] Failed to connect: {e}")

    def disconnect(self) -> None:
        if self.cursor:
            try:
                self.cursor.close()
            except Exception as e:
                logger.warning(f"[{self.db_type}] Cursor close failed: {e}")
            finally:
                self.cursor = None
        if self.connection:
            try:
                self.connection.close()
            except Exception as e:
                logger.warning(f"[{self.db_type}] Connection close failed: {e}")
            finally:
                self.connection = None
        if self.engine:
            self.engine.dispose()
            self.engine = None

    def is_connected(self) -> bool:
        return self.connection is not None and self.cursor is not None

    def execute_query(
        self, query: str, params: Optional[Union[Dict[str, Any], Tuple[Any, ...]]] = None
    ) -> pd.DataFrame:
        if not self.is_connected():
            raise ConnectionError(
                f"[{self.db_type}] No active connection. Call connect() first."
            )
        try:
            log_query = self._mask_password(query)
            logger.info(
                f"[{self.db_type}] Executing SELECT query: {log_query[:300]}{'...' if len(log_query) > 300 else ''}"
            )
            if self.engine:
                if params:
                    df = pd.read_sql(query, self.engine, params=params)
                else:
                    df = pd.read_sql(query, self.engine)
            else:
                raise RuntimeError(
                    f"[{self.db_type}] Engine is not available for query execution"
                )
            logger.info(f"[{self.db_type}] Query executed successfully. Fetched {len(df)} records.")
            return df
        except Exception as e:
            logger.error(f"[{self.db_type}] Error executing query: {str(e)}", exc_info=True)
            raise RuntimeError(f"[{self.db_type}] Query execution failed: {str(e)}")

    def execute_non_query(
        self, query: str, params: Optional[Union[Dict[str, Any], Tuple[Any, ...]]] = None
    ) -> int:
        if not self.is_connected():
            raise ConnectionError(
                f"[{self.db_type}] No active connection. Call connect() first."
            )
        try:
            log_query = self._mask_password(query)
            logger.info(
                f"[{self.db_type}] Executing DML/DDL statement: {log_query[:300]}{'...' if len(log_query) > 300 else ''}"
            )
            if self.cursor:
                if params:
                    self.cursor.execute(query, params)
                else:
                    self.cursor.execute(query)
            else:
                raise RuntimeError(
                    f"[{self.db_type}] Cursor is not available for non-query execution"
                )
            affected_rows = self.cursor.rowcount
            if self._requires_commit():
                if self.connection:
                    self.connection.commit()
                else:
                    raise RuntimeError(
                        f"[{self.db_type}] Connection is not available for commit"
                    )
            logger.info(
                f"[{self.db_type}] Non-query executed successfully. Affected rows: {affected_rows}."
            )
            return affected_rows
        except Exception as e:
            logger.error(
                f"[{self.db_type}] Error executing non-query: {str(e)}", exc_info=True
            )
            raise RuntimeError(f"[{self.db_type}] Non-query execution failed: {str(e)}")

    @timed_operation("Table creation")
    def create_table(
        self,
        schema: Optional[str],
        table_name: str,
        df: pd.DataFrame,
        if_exists: Literal["fail", "replace", "append"] = "fail",
        index: bool = False,
        **kwargs,
    ) -> str:
        if not self.is_connected():
            raise ConnectionError(
                f"[{self.db_type}] No active connection. Call connect() first."
            )
        self._validate_schema(schema)
        df.columns = df.columns.str.replace("[^a-zA-Z0-9_]", "_", regex=True)
        if self.engine:
            with self.engine.begin() as conn:
                df.to_sql(
                    table_name,
                    con=conn,
                    schema=schema,
                    if_exists=if_exists,
                    index=index,
                    chunksize=10000,
                )
                full_name = f"{schema}.{table_name}" if schema else table_name
                return f"Table `{full_name}` created in {self.db_type}."
        raise RuntimeError(
            f"[{self.db_type}] Engine is not available for RDBMS table creation"
        )

    def get_connection_url(self) -> str:
        base_url = self._build_connection_url()
        if self._supports_connection_pooling():
            separator = "&" if "?" in base_url else "?"
            base_url += f"{separator}pool_size={self.config.pool_size}&max_overflow={self.config.max_overflow}&pool_timeout=30"
        return base_url
