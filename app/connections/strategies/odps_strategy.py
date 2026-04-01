import re
import threading
from typing import Any, Literal
from urllib.parse import quote_plus

import pandas as pd
from odps import ODPS
from odps import errors as odps_errors
from odps.df import DataFrame as OdpsDataFrame

from app.configs.log_config import logger

from .base import DatabaseStrategy, ODPSConfig, timed_operation


class ODPSStrategy(DatabaseStrategy):
    """Strategy for Alibaba MaxCompute (ODPS)."""

    def __init__(self, config: ODPSConfig):
        super().__init__(config)
        if not isinstance(config, ODPSConfig):
            raise TypeError(f"[{config.db_type}] ODPSStrategy requires ODPSConfig")
        self.config: ODPSConfig = config
        self.connection: ODPS | None = None
        self._odps_lock = threading.Lock()

    def connect(self) -> None:
        if self.connection:
            return
        try:
            self.connection = ODPS(
                self.config.access_id,
                self.config.secret_access_key,
                self.config.default_project,
                endpoint=self.config.endpoint,
            )
            logger.info(
                f"[{self.db_type}] Connected to ODPS project {self.config.default_project}"
            )
        except Exception as e:
            logger.error(f"[{self.db_type}] Connection failed: {e}", exc_info=True)
            raise ConnectionError(f"[{self.db_type}] Failed to connect: {e}") from e

    def disconnect(self) -> None:
        self.connection = None

    def is_connected(self) -> bool:
        return self.connection is not None

    def execute_query(
        self,
        query: str,
        params: dict[str, Any] | tuple[Any, ...] | None = None,
    ) -> pd.DataFrame:
        if not self.is_connected():
            raise ConnectionError(
                f"[{self.db_type}] No active connection. Call connect() first."
            )
        try:
            log_query = re.sub(r"(?i)(password\s*=\s*)'[^']+'", r"\1'***'", query)
            logger.info(
                f"[{self.db_type}] Executing SELECT query: {log_query[:300]}{'...' if len(log_query) > 300 else ''}"
            )
            with self._odps_lock:
                if self.connection:
                    with self.connection.execute_sql(query).open_reader() as reader:
                        records = [dict(record) for record in reader]
                        df = pd.DataFrame(records)
                else:
                    raise ConnectionError(
                        f"[{self.db_type}] No active connection. Call connect() first."
                    )
            logger.info(
                f"[{self.db_type}] Query executed successfully. Fetched {len(df)} records."
            )
            return df
        except odps_errors.ODPSError as e:
            logger.error(f"[{self.db_type}] ODPS error: {e}", exc_info=True)
            raise RuntimeError(f"[{self.db_type}] ODPS query failed: {str(e)}") from e
        except Exception as e:
            logger.error(
                f"[{self.db_type}] Error executing query: {str(e)}", exc_info=True
            )
            raise RuntimeError(f"[{self.db_type}] Query execution failed: {str(e)}") from e

    def execute_non_query(
        self,
        query: str,
        params: dict[str, Any] | tuple[Any, ...] | None = None,
    ) -> int:
        if not self.is_connected():
            raise ConnectionError(
                f"[{self.db_type}] No active connection. Call connect() first."
            )
        try:
            log_query = re.sub(r"(?i)(password\s*=\s*)'[^']+'", r"\1'***'", query)
            logger.info(
                f"[{self.db_type}] Executing DML/DDL statement: {log_query[:300]}{'...' if len(log_query) > 300 else ''}"
            )
            with self._odps_lock:
                if self.connection:
                    instance = self.connection.execute_sql(query)
                    instance.wait_for_success()
                else:
                    raise ConnectionError(
                        f"[{self.db_type}] No active connection. Call connect() first."
                    )
            logger.info(
                f"[{self.db_type}] Non-query executed successfully. Instance ID: {instance.id}"
            )
            return 0
        except odps_errors.ODPSError as e:
            logger.error(f"[{self.db_type}] ODPS error: {e}", exc_info=True)
            raise RuntimeError(f"[{self.db_type}] ODPS non-query failed: {str(e)}") from e
        except Exception as e:
            logger.error(
                f"[{self.db_type}] Error executing non-query: {str(e)}", exc_info=True
            )
            raise RuntimeError(f"[{self.db_type}] Non-query execution failed: {str(e)}") from e

    @timed_operation("Table creation")
    def create_table(
        self,
        schema: str | None,
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
        if schema and not schema.isidentifier():
            raise ValueError(
                f"[{self.db_type}] Invalid schema name '{schema}': must be a valid Python identifier"
            )
        odps_table_name = f"{schema}.{table_name}" if schema else table_name
        if (
            if_exists == "fail"
            and self.connection
            and self.connection.exist_table(odps_table_name)
        ):
            raise ValueError(
                f"[{self.db_type}] Table '{odps_table_name}' already exists"
            )
        odps_df = OdpsDataFrame(df)
        odps_df.persist(odps_table_name, rewrite=(if_exists == "replace"))
        return f"Table `{odps_table_name}` created in ODPS."

    def get_connection_url(self) -> str:
        encoded_password = quote_plus(self.config.secret_access_key)
        return f"odps://{self.config.access_id}:{encoded_password}@{self.config.endpoint}/{self.config.default_project}"
