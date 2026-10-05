"""Abstract base repository providing generic table CRUD operations.

Defines a reusable foundation for all repository classes with common operations
(select_all, select_one, select_where, insert_one, insert_bulk, update_where,
delete_where, count) built from class-level constants. Subclasses only need to
declare DATABASE_TYPE, SCHEMA/DATABASE, TABLE_NAME, and COLUMNS, then add
any domain-specific methods on top.

Example:
    class UserRepository(BaseRepository):
        DATABASE_TYPE = "mssql"
        SCHEMA = "dbo"
        TABLE_NAME = "users"
        COLUMNS = ["user_id", "email", "created_at"]

    with UserRepository() as repo:
        all_users = repo.select_all()
        user = repo.select_one("user_id", 42)
        active = repo.select_where({"is_active": 1})
"""

import logging
from typing import Any, Literal

import pandas as pd

from app.connections.strategies import create_strategy
from app.utils.repo_utils import validate_columns

logger = logging.getLogger(__name__)


class BaseRepository:
    """Abstract base for all domain repositories.

    Provides generic CRUD operations derived from class-level constants.
    Subclasses must define DATABASE_TYPE, SCHEMA (or DATABASE for MySQL),
    TABLE_NAME, and COLUMNS to enable all built-in operations.

    Column names passed to any method are validated against COLUMNS to
    prevent SQL injection through identifier manipulation.

    Attributes:
        strategy: Active database strategy instance (set in __init__).
    """

    DATABASE_TYPE: str = ""
    SCHEMA: str = ""      # Use for MSSQL, PostgreSQL, Hive
    DATABASE: str = ""    # Use for MySQL
    TABLE_NAME: str = ""
    COLUMNS: list[str] = []

    def __init__(self) -> None:
        """Initialize repository and establish database connection."""
        self.strategy = create_strategy(self.DATABASE_TYPE)
        self.strategy.connect()

    # ─── Internal helpers ────────────────────────────────────────────────────

    def _qualified_table(self) -> str:
        """Return fully qualified table name (schema.table or just table)."""
        prefix = self.SCHEMA or self.DATABASE
        return f"{prefix}.{self.TABLE_NAME}" if prefix else self.TABLE_NAME

    def _placeholder(self) -> str:
        """Return the single placeholder character for this database type."""
        if self.DATABASE_TYPE.lower() in ("mssql", "mysql", "hive"):
            return "?"
        return "%s"

    def _validate_col_names(self, columns: list[str]) -> None:
        """Raise ValueError if any column name is not in COLUMNS.

        Args:
            columns: Column names to validate.

        Raises:
            ValueError: If COLUMNS is defined and any column is not in it.
        """
        if not self.COLUMNS:
            return
        is_valid, msg = validate_columns(columns, self.COLUMNS)
        if not is_valid:
            raise ValueError(f"[{self.__class__.__name__}] {msg}")

    def _build_where_clause(self, conditions: dict[str, Any]) -> tuple[str, tuple[Any, ...]]:
        """Build a parameterized WHERE clause from a conditions dict.

        Args:
            conditions: Column→value pairs (AND-joined).

        Returns:
            Tuple of (where_clause_string, params_tuple).
        """
        ph = self._placeholder()
        parts = [f"{col} = {ph}" for col in conditions]
        return " AND ".join(parts), tuple(conditions.values())

    # ─── Generic CRUD operations ─────────────────────────────────────────────

    def select_all(
        self,
        columns: list[str] | None = None,
        limit: int | None = None,
    ) -> pd.DataFrame:
        """Fetch all rows from the table.

        Args:
            columns: Subset of column names to retrieve. Defaults to all COLUMNS.
                     Pass None or an empty list to select all columns (*).
            limit: Maximum number of rows to return. No limit when None.

        Returns:
            DataFrame of all matching rows.

        Raises:
            ValueError: If any requested column name is not in COLUMNS.
        """
        logger.debug("select_all called with columns=%s, limit=%s", columns, limit)

        col_list = columns or self.COLUMNS
        if col_list:
            self._validate_col_names(col_list)
            select_clause = ", ".join(col_list)
        else:
            select_clause = "*"

        table = self._qualified_table()
        # MSSQL uses TOP N; all others use LIMIT N
        if limit is not None:
            if self.DATABASE_TYPE.lower() == "mssql":
                query = f"SELECT TOP {int(limit)} {select_clause} FROM {table}"
            else:
                query = f"SELECT {select_clause} FROM {table} LIMIT {int(limit)}"
        else:
            query = f"SELECT {select_clause} FROM {table}"

        return self.strategy.execute_query(query)

    def select_one(self, pk_column: str, pk_value: Any) -> dict[str, Any] | None:
        """Fetch a single record by primary key.

        Args:
            pk_column: Primary key column name.
            pk_value: Value to match.

        Returns:
            Dict of column→value for the first matching row, or None if not found.

        Raises:
            ValueError: If pk_column is not in COLUMNS.
        """
        logger.debug("select_one called with pk_column=%s", pk_column)
        self._validate_col_names([pk_column])

        ph = self._placeholder()
        query = f"SELECT * FROM {self._qualified_table()} WHERE {pk_column} = {ph}"
        df = self.strategy.execute_query(query, params=(pk_value,))

        if df is not None and not df.empty:
            return {str(k): v for k, v in df.iloc[0].to_dict().items()}
        return None

    def select_where(
        self,
        conditions: dict[str, Any],
        columns: list[str] | None = None,
    ) -> pd.DataFrame:
        """Fetch rows matching all conditions (AND logic).

        Args:
            conditions: Column→value pairs used for the WHERE clause.
            columns: Subset of columns to retrieve. Defaults to all COLUMNS.

        Returns:
            DataFrame of matching rows.

        Raises:
            ValueError: If any column name is not in COLUMNS.
        """
        logger.debug("select_where called with conditions=%s", list(conditions.keys()))
        self._validate_col_names(list(conditions.keys()))

        col_list = columns or self.COLUMNS
        if col_list:
            self._validate_col_names(col_list)
            select_clause = ", ".join(col_list)
        else:
            select_clause = "*"

        where_clause, params = self._build_where_clause(conditions)
        query = f"SELECT {select_clause} FROM {self._qualified_table()} WHERE {where_clause}"
        return self.strategy.execute_query(query, params=params)

    def insert_one(self, data: dict[str, Any]) -> int:
        """Insert a single record.

        Args:
            data: Column→value pairs representing the new row.

        Returns:
            Number of rows affected (1 on success).

        Raises:
            ValueError: If any column name is not in COLUMNS.
        """
        logger.debug("insert_one called with columns=%s", list(data.keys()))
        self._validate_col_names(list(data.keys()))

        ph = self._placeholder()
        col_list = ", ".join(data.keys())
        placeholders = ", ".join([ph] * len(data))
        table = self._qualified_table()
        query = f"INSERT INTO {table} ({col_list}) VALUES ({placeholders})"
        return self.strategy.execute_non_query(query, params=tuple(data.values()))

    def insert_bulk(
        self,
        df: pd.DataFrame,
        if_exists: Literal["fail", "replace", "append"] = "append",
    ) -> str:
        """Bulk-insert a DataFrame into the table via SQLAlchemy.

        Args:
            df: DataFrame whose columns match the table schema.
            if_exists: Behaviour when the table already exists:
                "fail" raises an error, "replace" drops and recreates,
                "append" adds rows to existing data.

        Returns:
            Success message from the strategy.

        Raises:
            ValueError: If any DataFrame column name is not in COLUMNS.
        """
        logger.debug("insert_bulk called with %d rows", len(df))
        self._validate_col_names(list(df.columns))

        schema = self.SCHEMA or self.DATABASE or None
        return self.strategy.create_table(
            schema=schema,
            table_name=self.TABLE_NAME,
            df=df,
            if_exists=if_exists,
            index=False,
        )

    def update_where(
        self,
        data: dict[str, Any],
        conditions: dict[str, Any],
    ) -> int:
        """Update columns in rows matching all conditions (AND logic).

        Args:
            data: Column→value pairs to SET.
            conditions: Column→value pairs for the WHERE clause.

        Returns:
            Number of rows affected.

        Raises:
            ValueError: If any column name is not in COLUMNS.
        """
        logger.debug(
            "update_where called with data=%s, conditions=%s",
            list(data.keys()),
            list(conditions.keys()),
        )
        self._validate_col_names(list(data.keys()) + list(conditions.keys()))

        ph = self._placeholder()
        set_clause = ", ".join([f"{col} = {ph}" for col in data])
        where_clause, where_params = self._build_where_clause(conditions)
        table = self._qualified_table()
        query = f"UPDATE {table} SET {set_clause} WHERE {where_clause}"
        params = tuple(data.values()) + where_params
        return self.strategy.execute_non_query(query, params=params)

    def delete_where(self, conditions: dict[str, Any]) -> int:
        """Delete rows matching all conditions (AND logic).

        Args:
            conditions: Column→value pairs for the WHERE clause.

        Returns:
            Number of rows deleted.

        Raises:
            ValueError: If any column name is not in COLUMNS.
        """
        logger.debug("delete_where called with conditions=%s", list(conditions.keys()))
        self._validate_col_names(list(conditions.keys()))

        where_clause, params = self._build_where_clause(conditions)
        query = f"DELETE FROM {self._qualified_table()} WHERE {where_clause}"
        return self.strategy.execute_non_query(query, params=params)

    def count(self) -> int:
        """Count total rows in the table.

        Returns:
            Integer row count.
        """
        query = f"SELECT COUNT(*) AS total FROM {self._qualified_table()}"
        df = self.strategy.execute_query(query)
        if df is not None and not df.empty:
            return int(df.iloc[0]["total"])
        return 0

    # ─── Lifecycle ───────────────────────────────────────────────────────────

    def __enter__(self):
        """Enter context manager (connection already established in __init__)."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context manager and disconnect.

        Args:
            exc_type: Exception type if raised during context.
            exc_val: Exception value if raised during context.
            exc_tb: Exception traceback if raised during context.
        """
        if exc_type:
            logger.error(
                "[%s] Operation failed: %s",
                self.__class__.__name__,
                exc_val,
                exc_info=True,
            )
        self.strategy.disconnect()
