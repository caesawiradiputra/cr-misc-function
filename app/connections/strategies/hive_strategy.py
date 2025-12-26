from typing import Literal, Optional
from urllib.parse import quote_plus

import pandas as pd
from pyhive import hive
from pyhive.hive import Connection as HiveConnection

from .base import RDBMSBaseStrategy, timed_operation


class HiveStrategy(RDBMSBaseStrategy):
    """Strategy for Apache Hive with external table support."""

    def _create_connection(self) -> HiveConnection:
        return hive.Connection(
            host=self.config.host,
            port=self.config.port,
            username=self.config.user,
            password=self.config.password,
            database=self.config.database,
            auth="LDAP",
        )

    def _build_connection_url(self) -> str:
        encoded_password = quote_plus(self.config.password)
        return f"hive://{self.config.user}:{encoded_password}@{self.config.host}:{self.config.port}/{self.config.database}?auth=LDAP"

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
        oss_path = kwargs.get("oss_path")
        if not oss_path:
            raise ValueError(
                f"[{self.db_type}] OSS path required for Hive external table creation"
            )

        full_name = f"{schema}.{table_name}" if schema else table_name
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
        if self.cursor:
            self.cursor.execute(hive_ddl)
            self.cursor.execute(f"MSCK REPAIR TABLE {full_name}")
            return f"External table `{full_name}` created successfully in Hive."
        raise RuntimeError(
            f"[{self.db_type}] Cursor is not available for Hive table creation"
        )
