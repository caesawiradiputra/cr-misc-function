"""Facade module wrapping modular strategy implementations.

This file previously contained all strategy classes in a single monolith.
It now delegates to the modular implementation under
`app.connections.strategies` for maintainability and testability.

Public API intentionally preserved: `DBConnectorStrategy` remains the
entry point for consumers wanting a higher-level facade.
"""

import os
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Literal

import pandas as pd

from app.configs.log_config import logger
from app.connections.strategies import (
    DatabaseStrategy,
    create_strategy,
)


class DBConnectorStrategy:
    """Facade over a concrete `DatabaseStrategy`.

    Responsibilities:
    - Provide context manager convenience
    - Support file-or-string SQL execution helper
    - Expose async hook point (can be extended later)
    - Preserve previous public method names for backwards compatibility
    """

    def __init__(self, db_type: str):
        self.db_type = db_type
        self._strategy: DatabaseStrategy = create_strategy(db_type)
        # Thread pool sized by underlying strategy pool size (if present)
        pool_size = getattr(self._strategy.config, "pool_size", 5)
        self._thread_pool = ThreadPoolExecutor(max_workers=pool_size)

    @property
    def is_connected(self) -> bool:  # * Backwards compatible property name
        return self._strategy.is_connected()

    def connect(self) -> None:
        self._strategy.connect()

    def disconnect(self) -> None:
        self._strategy.disconnect()
        if self._thread_pool:
            self._thread_pool.shutdown(wait=True)
            self._thread_pool = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            logger.error(f"[{self.db_type}] Operation failed: {exc_val}", exc_info=True)
        self.disconnect()

    def _read_query(self, query_or_path: str) -> str:
        if os.path.isfile(query_or_path):
            with open(query_or_path) as f:
                return f.read()
        return query_or_path

    def execute_query(
        self,
        query_or_path: str,
        params: dict[str, Any] | tuple[Any, ...] | None = None,
    ) -> pd.DataFrame:
        query = self._read_query(query_or_path)
        return self._strategy.execute_query(query, params)

    def execute_non_query(
        self,
        query_or_path: str,
        params: dict[str, Any] | tuple[Any, ...] | None = None,
    ) -> int:
        query = self._read_query(query_or_path)
        return self._strategy.execute_non_query(query, params)

    def create_table(
        self,
        schema: str | None,
        table_name: str,
        df: pd.DataFrame,
        oss_path: str | None = None,
        if_exists: Literal["fail", "replace", "append"] = "fail",
        index: bool = False,
    ) -> str:
        return self._strategy.create_table(
            schema=schema,
            table_name=table_name,
            df=df,
            if_exists=if_exists,
            index=index,
            oss_path=oss_path,
        )

    def get_sqlalchemy_url(self) -> str:
        return self._strategy.get_connection_url()


__all__ = ["DBConnectorStrategy"]
