import asyncio
import functools
import os
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Dict, Literal, Optional, Protocol, Tuple, Union
from urllib.parse import quote_plus

import mysql.connector
import pandas as pd
import psycopg2
import pyodbc
import trino
from app.configs.config import database_config, odps_config
from app.configs.log_config import logger
from mysql.connector.abstracts import MySQLConnectionAbstract, MySQLCursorAbstract
from mysql.connector.pooling import PooledMySQLConnection
from odps import ODPS
from odps import errors as odps_errors
from odps.df import DataFrame as OdpsDataFrame
from psycopg2._psycopg import connection as Psycopg2_Connection
from psycopg2._psycopg import cursor as Psycopg2_Cursor
from pyhive import hive
from pyhive.hive import Connection as Hive_Connection
from pyhive.hive import Cursor as Hive_Cursor
from pyodbc import Connection as Pyodbc_Connection
from pyodbc import Cursor as Pyodbc_Cursor
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool
from trino.auth import BasicAuthentication
from trino.dbapi import Connection as Trino_Connection
from trino.dbapi import Cursor as Trino_Cursor
from sqlalchemy.engine.base import Engine


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


# * Union type for config with discriminated field
DatabaseConfig = Union[DBConfig, ODPSConfig]


# * Strategy Protocol for database operations
class DatabaseStrategy(Protocol):
    """Protocol for database-specific operations."""
    
    def connect(self) -> Any: ...
    def disconnect(self) -> None: ...
    def execute_query(self, query: str, params: Optional[Any]) -> pd.DataFrame: ...
    def execute_non_query(self, query: str, params: Optional[Any]) -> int: ...
    def create_table(
        self, 
        schema: Optional[str], 
        table_name: str, 
        df: pd.DataFrame, 
        **kwargs
    ) -> str: ...


# * Connection Protocol
class DBConnection(Protocol):
    def cursor(self) -> Any: ...
    def close(self) -> None: ...
    def commit(self) -> None: ...
    def rollback(self) -> None: ...


class ODPSTable(Protocol):
    def open_reader(self) -> Any: ...
    def exists(self) -> bool: ...


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


def _require_odps_connection_and_handle_errors(func):
    @functools.wraps(func)
    def wrapper(self: "DBConnector", *args, **kwargs):
        if self.db_type != "odps":
            return func(self, *args, **kwargs)

        if not self.connection:
            raise ConnectionError("ODPS connection not established")

        func_name = func.__name__
        sql_arg = kwargs.get("query_or_path") or args[0] if args else "N/A"
        logger.debug(f"Executing ODPS operation '{func_name}' with: {sql_arg[:200]}...")

        try:
            with self._odps_lock:
                return func(self, *args, **kwargs)
        except odps_errors.ODPSError as e:
            logger.error(f"ODPS error in '{func_name}': {e}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Unexpected error in '{func_name}': {e}", exc_info=True)
            raise

    return wrapper


class DBConnector:
    """Enhanced database connector with connection pooling, async support, and improved type safety."""

    def __init__(self, db_type: str):
        self.db_type = db_type
        self._validate_db_type()
        self.config = self._parse_config()  # * Single unified config

        self.connection: Optional[
            Union[
                Trino_Connection,
                Psycopg2_Connection,
                Hive_Connection,
                Pyodbc_Connection,
                PooledMySQLConnection,
                MySQLConnectionAbstract,
            ]
        ] = None
        self.connection_odps: Optional[ODPS] = None
        self.cursor: Optional[
            Union[
                Trino_Cursor,
                Psycopg2_Cursor,
                Hive_Cursor,
                Pyodbc_Cursor,
                MySQLCursorAbstract,
            ]
        ] = None
        self.engine: Optional[Engine] = None
        self._odps_lock = threading.Lock()
        
        # * Get pool size from unified config object
        self._thread_pool = ThreadPoolExecutor(max_workers=self.config.pool_size)

        if self.db_type != "odps":
            self.connect()

    def _validate_db_type(self):
        valid_types = list(database_config.keys()) + ["odps"]
        if self.db_type not in valid_types:
            raise ValueError(f"Unsupported DB type. Valid types: {valid_types}")

    def _parse_config(self) -> DatabaseConfig:
        """Validate and parse config for required fields, returning unified config object."""
        if self.db_type == "odps":
            for field in [
                "access_id",
                "secret_access_key",
                "default_project",
                "endpoint",
            ]:
                if not odps_config.get(field):
                    raise ValueError(f"[{self.db_type}] Missing ODPS config field: {field}")
            return ODPSConfig(db_type="odps", **odps_config)
        else:
            db_config = database_config[self.db_type]
            for field in ["host", "port", "user", "password", "database"]:
                if not db_config.get(field):
                    raise ValueError(f"[{self.db_type}] Missing DB config field: {field}")
            return DBConfig(
                db_type=self.db_type,
                host=db_config["host"],
                port=db_config["port"],
                user=db_config["user"],
                password=db_config["password"],
                database=db_config["database"],
                driver=db_config.get("driver"),
                pool_size=db_config.get("pool_size", 5),
                max_overflow=db_config.get("max_overflow", 10),
            )

    class DBConnectorError(Exception):
        pass

    class DBConnectorConnectionError(DBConnectorError):
        pass

    class DBConnectorQueryError(DBConnectorError):
        pass

    def _get_db_config(self) -> DBConfig:
        """Type guard to get DBConfig, raises if ODPS."""
        if isinstance(self.config, ODPSConfig):
            raise TypeError(f"[{self.db_type}] Expected DBConfig but got ODPSConfig")
        return self.config

    def _get_odps_config(self) -> ODPSConfig:
        """Type guard to get ODPSConfig, raises if not ODPS."""
        if isinstance(self.config, DBConfig):
            raise TypeError(f"[{self.db_type}] Expected ODPSConfig but got DBConfig")
        return self.config

    @property
    def is_connected(self) -> bool:
        """Check if database connection is established."""
        if self.db_type == "odps":
            return self.connection_odps is not None
        return self.connection is not None and self.cursor is not None

    def _require_connection(self, operation: str) -> None:
        """Validate connection state before operations."""
        if not self.is_connected:
            raise ConnectionError(
                f"[{self.db_type}] Cannot {operation}: No active connection. "
                f"Use context manager (with DBConnector(...)) or call connect() first."
            )

    def connect(self):
        """Establish connection with connection pooling."""
        if self.connection:
            return

        try:
            config = self._get_db_config()  # * Type-safe config access
            
            if self.db_type == "trino":
                self.connection = trino.dbapi.connect(
                    host=config.host,
                    port=config.port,
                    catalog="hive",
                    schema=config.database,
                    auth=BasicAuthentication(config.user, config.password),
                    http_scheme="https",
                    verify=False,
                )
            elif self.db_type in ["hologres", "postgres"]:
                self.connection = psycopg2.connect(
                    database=config.database,
                    user=config.user,
                    password=config.password,
                    host=config.host,
                    port=config.port,
                )
            elif self.db_type == "hive":
                self.connection = hive.Connection(
                    host=config.host,
                    port=config.port,
                    username=config.user,
                    password=config.password,
                    database=config.database,
                    auth="LDAP",
                )
            elif self.db_type == "mssql":
                driver = config.driver or "ODBC Driver 17 for SQL Server"
                conn_str = (
                    f"DRIVER={driver};"
                    f"SERVER={config.host},{config.port};"
                    f"DATABASE={config.database};"
                    f"UID={config.user};"
                    f"PWD={config.password}"
                )
                self.connection = pyodbc.connect(conn_str)
            elif self.db_type == "mysql":
                self.connection = mysql.connector.connect(
                    host=config.host,
                    port=config.port,
                    user=config.user,
                    password=config.password,
                    database=config.database,
                )

            if self.db_type != "odps":
                if self.connection:
                    self.cursor = self.connection.cursor()

            logger.info(f"Connected to {self.db_type} at {config.host}")

        except Exception as e:
            logger.error(f"[{self.db_type}] Connection failed: {e}", exc_info=True)
            raise ConnectionError(f"[{self.db_type}] Failed to connect: {e}")

    def get_sqlalchemy_url(self) -> str:
        """Generate SQLAlchemy URL with connection pooling."""
        if self.db_type == "odps":
            odps_cfg = self._get_odps_config()
            encoded_password = quote_plus(odps_cfg.secret_access_key)
            return f"odps://{odps_cfg.access_id}:{encoded_password}@{odps_cfg.endpoint}/{odps_cfg.default_project}"
        
        config = self._get_db_config()
        encoded_password = quote_plus(config.password)
        base_url = ""

        if self.db_type in ["hologres", "postgres"]:
            base_url = f"postgresql://{config.user}:{encoded_password}@{config.host}:{config.port}/{config.database}"
        elif self.db_type == "trino":
            base_url = f"trino://{config.user}:{encoded_password}@{config.host}:{config.port}/hive/{config.database}"
        elif self.db_type == "hive":
            base_url = f"hive://{config.user}:{encoded_password}@{config.host}:{config.port}/{config.database}?auth=LDAP"
        elif self.db_type == "mssql":
            driver = quote_plus(config.driver or "ODBC Driver 17 for SQL Server")
            base_url = f"mssql+pyodbc://{config.user}:{encoded_password}@{config.host}:{config.port}/{config.database}?driver={driver}"
        elif self.db_type == "mysql":
            base_url = f"mysql+mysqlconnector://{config.user}:{encoded_password}@{config.host}:{config.port}/{config.database}"

        # * Add connection pooling for supported databases
        if self.db_type in ["postgres", "mysql", "hologres"]:
            base_url += f"?pool_size={config.pool_size}&max_overflow={config.max_overflow}&pool_timeout=30"

        return base_url

    @contextmanager
    def _connection_context(self):
        """Context manager for thread-safe connection handling."""
        try:
            if not self.connection:
                self.connect()
            yield self.connection
        except Exception as e:
            logger.error(f"[{self.db_type}] Connection context error: {e}", exc_info=True)
            self.disconnect()
            raise
        finally:
            # * Only commit for DML/DDL, not for SELECT
            if self.db_type != "odps" and self.connection and hasattr(self, "cursor"):
                try:
                    if (
                        self.cursor
                        and hasattr(self.cursor, "description")
                        and self.cursor.description is None
                    ):
                        # * No result set: likely DML/DDL, so commit
                        self.connection.commit()
                except Exception as e:
                    logger.warning(f"[{self.db_type}] Auto-commit failed: {e}")

    async def execute_async(self, query: str, params=None):
        """Execute query asynchronously using thread pool."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._thread_pool, functools.partial(self.execute_query, query, params)
        )

    @timed_operation("Table creation")
    @_require_odps_connection_and_handle_errors
    def create_table(
        self,
        schema: Optional[str],
        table_name: str,
        df: pd.DataFrame,
        oss_path: Optional[str] = None,
        if_exists: Literal["fail", "replace", "append"] = "fail",
        index: bool = False,
    ) -> str:
        """Enhanced table creation with schema validation."""
        self._validate_schema(schema)
        full_table_name = f"{schema}.{table_name}" if schema else table_name

        if self.db_type == "hive":
            if not oss_path:
                raise ValueError(f"[{self.db_type}] OSS path required for Hive external table creation")
            return self._create_hive_table(full_table_name, df, oss_path)

        elif self.db_type == "odps":
            return self._create_odps_table(schema, table_name, df, if_exists)

        else:
            return self._create_rdbms_table(schema, table_name, df, if_exists, index)

    def _validate_schema(self, schema: Optional[str]):
        """Validate schema/table naming conventions."""
        if schema and not schema.isidentifier():
            raise ValueError(f"[{self.db_type}] Invalid schema name '{schema}': must be a valid Python identifier")

    def _create_hive_table(
        self, full_name: str, df: pd.DataFrame, oss_path: str
    ) -> str:
        """Create Hive external table implementation."""
        type_mapping = {
            "int64": "BIGINT",
            "float64": "DOUBLE",
            "object": "STRING",
            "bool": "BOOLEAN",
            "datetime64[ns]": "TIMESTAMP",
        }

        columns_ddl = ",\n    ".join(
            f"`{col}` {type_mapping.get(str(df[col].dtype), 'STRING')}"
            for col in df.columns
        )

        hive_ddl = f"""
        CREATE EXTERNAL TABLE IF NOT EXISTS {full_name} (
            {columns_ddl}
        )
        STORED AS PARQUET
        LOCATION '{oss_path}'
        """

        with self._connection_context():
            if self.cursor:
                self.cursor.execute(hive_ddl)
                self.cursor.execute(f"MSCK REPAIR TABLE {full_name}")
                return f"External table `{full_name}` created successfully in Hive."
            else:
                raise RuntimeError(f"[{self.db_type}] Cursor is not available for Hive table creation")

    def _create_odps_table(
        self, schema: Optional[str], table_name: str, df: pd.DataFrame, if_exists: str
    ) -> str:
        """Create ODPS table implementation."""
        odps_table_name = f"{schema}.{table_name}" if schema else table_name

        if self.connection_odps:
            if if_exists == "fail" and self.connection_odps.exist_table(
                odps_table_name
            ):
                raise ValueError(f"[{self.db_type}] Table '{odps_table_name}' already exists")

        odps_df = OdpsDataFrame(df)
        odps_df.persist(odps_table_name, rewrite=(if_exists == "replace"))
        return f"Table `{odps_table_name}` created in ODPS."

    def _create_rdbms_table(
        self,
        schema: Optional[str],
        table_name: str,
        df: pd.DataFrame,
        if_exists: Literal["fail", "replace", "append"],
        index: bool,
    ) -> str:
        """Create table in relational databases."""
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
                return f"Table `{schema}.{table_name}` created in {self.db_type}."
        else:
            raise RuntimeError(f"[{self.db_type}] Engine is not available for RDBMS table creation")

    def __enter__(self):
        """Context manager entry with SQLAlchemy engine creation."""
        if self.db_type == "odps":
            odps_cfg = self._get_odps_config()
            self.connection_odps = ODPS(
                odps_cfg.access_id,
                odps_cfg.secret_access_key,
                odps_cfg.default_project,
                endpoint=odps_cfg.endpoint,
            )
            self.engine = None  # Only create engine for non-ODPS
        else:
            self.connect()
            config = self._get_db_config()
            self.engine = create_engine(
                self.get_sqlalchemy_url(),
                poolclass=QueuePool,
                pool_size=config.pool_size,
                max_overflow=config.max_overflow,
            )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with proper cleanup."""
        if exc_type:
            logger.error(f"[{self.db_type}] Operation failed: {exc_val}", exc_info=True)
            if self.db_type != "odps" and self.connection:
                try:
                    self.connection.rollback()
                except Exception as e:
                    logger.error(f"[{self.db_type}] Rollback failed: {e}")

        self.disconnect()

    def disconnect(self) -> None:
        """Thread-safe disconnection and resource cleanup."""
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

        # ! Only shutdown thread pool here to avoid double shutdown
        if hasattr(self, "_thread_pool") and self._thread_pool:
            self._thread_pool.shutdown(wait=True)
            self._thread_pool = None

    @_require_odps_connection_and_handle_errors
    def execute_query(
        self,
        query_or_path: str,
        params: Optional[Union[Dict[str, Any], Tuple[Any, ...]]] = None,
    ) -> pd.DataFrame:
        """
        Executes a SQL query from a string or a SQL file and returns results as a Pandas DataFrame.
        This method is primarily for SELECT queries. For DDL/DML, use execute_non_query.

        Args:
            query_or_path: SQL string or path to SQL file.
            params: Query parameters (dict for named, tuple for positional).

        Returns:
            pd.DataFrame: Query results.
        """
        try:
            if os.path.isfile(query_or_path):
                with open(query_or_path, "r") as file:
                    query = file.read()
            else:
                query = query_or_path

            # * Mask sensitive info in logs and connection strings
            log_query = re.sub(r"(?i)(password\s*=\s*)'[^']+'", r"\1'***'", query)
            logger.info(
                f"[{self.db_type}] Executing SELECT query: {log_query[:300]}{'...' if len(log_query) > 300 else ''}"
            )

            if self.db_type == "odps":
                if self.connection_odps:
                    with self.connection_odps.execute_sql(
                        query
                    ).open_reader() as reader:
                        records = [dict(record) for record in reader]
                        df = pd.DataFrame(records)
                else:
                    raise RuntimeError(
                        f"[{self.db_type}] ODPS connection is not available for query execution"
                    )
            else:
                # * Use parameterized queries for safety
                if self.engine:
                    if params:
                        df = pd.read_sql(query, self.engine, params=params)
                    else:
                        df = pd.read_sql(query, self.engine)
                else:
                    raise RuntimeError(f"[{self.db_type}] Engine is not available for query execution")
            logger.info(
                f"[{self.db_type}] Query executed successfully. Fetched {len(df)} records."
            )
            return df

        except Exception as e:
            logger.error(
                f"[{self.db_type}] Error executing query: {str(e)}", exc_info=True
            )
            raise RuntimeError(f"[{self.db_type}] Query execution failed: {str(e)}")

    @_require_odps_connection_and_handle_errors
    def execute_non_query(
        self,
        query_or_path: str,
        params: Optional[Union[Dict[str, Any], Tuple[Any, ...]]] = None,
    ) -> int:
        """
        Executes a SQL statement that does not return rows (e.g., INSERT, UPDATE, DELETE, CREATE TABLE).
        Returns the number of affected rows (if applicable, or 0 for DDL).

        Args:
            query_or_path: SQL string or path to SQL file.
            params: Query parameters (dict for named, tuple for positional).

        Returns:
            int: Number of affected rows.
        """
        try:
            if os.path.isfile(query_or_path):
                with open(query_or_path, "r") as file:
                    query = file.read()
            else:
                query = query_or_path

            log_query = re.sub(r"(?i)(password\s*=\s*)'[^']+'", r"\1'***'", query)
            logger.info(
                f"[{self.db_type}] Executing DML/DDL statement: {log_query[:300]}{'...' if len(log_query) > 300 else ''}"
            )

            if self.db_type == "odps":
                if self.connection_odps:
                    instance = self.connection_odps.execute_sql(query)
                    instance.wait_for_success()
                    affected_rows = 0
                    logger.info(
                        f"[{self.db_type}] Non-query executed successfully. Instance ID: {instance.id}"
                    )
                else:
                    raise RuntimeError(
                        f"[{self.db_type}] ODPS connection is not available for non-query execution"
                    )
            else:
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
                if self.db_type not in ["trino", "hive"]:
                    if self.connection:
                        self.connection.commit()
                    else:
                        raise RuntimeError(f"[{self.db_type}] Connection is not available for commit")

            logger.info(
                f"[{self.db_type}] Non-query executed successfully. Affected rows: {affected_rows}."
            )
            return affected_rows

        except Exception as e:
            logger.error(
                f"[{self.db_type}] Error executing non-query: {str(e)}", exc_info=True
            )
            raise RuntimeError(f"[{self.db_type}] Non-query execution failed: {str(e)}")
