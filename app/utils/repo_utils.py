"""Repository query and SQL generation utilities.

Provides reusable functions for SQL query building, parameter handling, and
database-agnostic placeholder generation. Used by repository classes to reduce
code duplication and maintain consistency.

All functions support multiple database types (MSSQL, PostgreSQL, MySQL, Hive)
with automatic handling of database-specific syntax differences.

Example:
    >>> from app.utils.repo_utils import read_query_file, generate_placeholders
    >>> query = read_query_file("queries/orders/pending.sql")
    >>> placeholders = generate_placeholders(3, "mssql")
    >>> params = (status, start_date, end_date)
"""

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def read_query_file(file_path: str, base_dir: str | None = None) -> str:
    """
    Read SQL query from file with validation.

    Validates that the file exists and is readable before reading.
    Supports absolute paths or relative paths from base_dir.

    Args:
        file_path: Path to SQL query file (absolute or relative).
        base_dir: Base directory for relative paths (default: project root).

    Returns:
        SQL query string from file.

    Raises:
        FileNotFoundError: If file does not exist.
        PermissionError: If file is not readable.
        ValueError: If file is empty.

    Example:
        >>> query = read_query_file("queries/orders/pending.sql")
        >>> df = strategy.execute_query(query)
    """
    # Resolve path
    if base_dir:
        full_path = Path(base_dir) / file_path
    else:
        full_path = Path(file_path)

    # Validate existence
    if not full_path.exists():
        raise FileNotFoundError(f"Query file not found: {full_path}")

    # Validate readability
    if not full_path.is_file():
        raise ValueError(f"Path is not a file: {full_path}")

    if not full_path.stat().st_size > 0:
        raise ValueError(f"Query file is empty: {full_path}")

    # Read file
    try:
        with open(full_path, encoding="utf-8") as f:
            content = f.read().strip()
        logger.debug(f"Loaded query from {full_path}")
        return content
    except PermissionError as e:
        raise PermissionError(f"Cannot read query file {full_path}: {e}") from e
    except Exception as e:
        logger.error(f"Failed to read query file {full_path}: {e}")
        raise


def generate_placeholders(count: int, db_type: str = "mssql") -> str:
    """
    Generate SQL parameter placeholders based on database type.

    Generates the correct placeholder syntax for the specified database:
    - MSSQL, MySQL: ? (positional)
    - PostgreSQL: %s (positional)
    - Hive: ? (positional)

    Args:
        count: Number of placeholders to generate.
        db_type: Database type ("mssql", "postgres", "mysql", "hive").

    Returns:
        Comma-separated placeholder string.

    Raises:
        ValueError: If count is zero or negative, or db_type is unknown.

    Example:
        >>> placeholders = generate_placeholders(3, "mssql")
        >>> placeholders
        '?, ?, ?'

        >>> placeholders = generate_placeholders(2, "postgres")
        >>> placeholders
        '%s, %s'
    """
    if count <= 0:
        raise ValueError(f"Placeholder count must be > 0, got {count}")

    db_type_lower = db_type.lower().strip()

    if db_type_lower in ("mssql", "mysql", "hive"):
        placeholder = "?"
    elif db_type_lower == "postgres":
        placeholder = "%s"
    else:
        raise ValueError(
            f"Unknown database type: {db_type}. "
            f"Supported: mssql, mysql, postgres, hive"
        )

    return ", ".join([placeholder] * count)


def build_insert_query(
    schema: str | None,
    table_name: str,
    columns: list[str],
    db_type: str = "mssql",
) -> str:
    """
    Build INSERT query with proper schema qualification and placeholders.

    Generates INSERT statement with correct column order and database-specific
    placeholder syntax. Returns only the query template (no actual values).

    Args:
        schema: Schema name (None for databases without schema).
        table_name: Table name.
        columns: List of column names in insertion order.
        db_type: Database type ("mssql", "postgres", "mysql", "hive").

    Returns:
        INSERT query template with placeholders (e.g., "INSERT INTO...VALUES(?, ?, ?)")

    Raises:
        ValueError: If columns list is empty or invalid.

    Example:
        >>> query = build_insert_query(
        ...     schema="dbo",
        ...     table_name="orders",
        ...     columns=["order_id", "customer_id", "total"],
        ...     db_type="mssql"
        ... )
        >>> query
        'INSERT INTO dbo.orders (order_id, customer_id, total) VALUES (?, ?, ?)'
    """
    if not columns:
        raise ValueError("Columns list cannot be empty")

    # Build table reference
    if schema:
        table_ref = f"{schema}.{table_name}"
    else:
        table_ref = table_name

    # Build column list
    column_list = ", ".join(columns)

    # Generate placeholders
    placeholders = generate_placeholders(len(columns), db_type)

    query = f"INSERT INTO {table_ref} ({column_list}) VALUES ({placeholders})"
    logger.debug(f"Generated INSERT query: {query}")
    return query


def build_update_query(
    schema: str | None,
    table_name: str,
    columns: list[str],
    where_column: str,
    db_type: str = "mssql",
) -> str:
    """
    Build UPDATE query with placeholders for columns and WHERE clause.

    Generates UPDATE statement that updates specified columns and filters by
    where_column. The WHERE clause placeholder comes last.

    Args:
        schema: Schema name (None for databases without schema).
        table_name: Table name.
        columns: List of column names to update.
        where_column: Column name for WHERE clause (e.g., "id").
        db_type: Database type ("mssql", "postgres", "mysql", "hive").

    Returns:
        UPDATE query template with placeholders.

    Raises:
        ValueError: If columns list is empty or where_column is empty.

    Example:
        >>> query = build_update_query(
        ...     schema="dbo",
        ...     table_name="orders",
        ...     columns=["status", "updated_at"],
        ...     where_column="order_id",
        ...     db_type="mssql"
        ... )
        >>> query
        'UPDATE dbo.orders SET status = ?, updated_at = ? WHERE order_id = ?'
    """
    if not columns:
        raise ValueError("Columns list cannot be empty")
    if not where_column:
        raise ValueError("Where column cannot be empty")

    # Build table reference
    if schema:
        table_ref = f"{schema}.{table_name}"
    else:
        table_ref = table_name

    # Get placeholder character
    db_type_lower = db_type.lower().strip()
    if db_type_lower in ("mssql", "mysql", "hive"):
        placeholder_char = "?"
    elif db_type_lower == "postgres":
        placeholder_char = "%s"
    else:
        raise ValueError(
            f"Unknown database type: {db_type}. "
            f"Supported: mssql, mysql, postgres, hive"
        )

    # Build SET clause
    set_clause = ", ".join([f"{col} = {placeholder_char}" for col in columns])

    query = f"UPDATE {table_ref} SET {set_clause} WHERE {where_column} = {placeholder_char}"
    logger.debug(f"Generated UPDATE query: {query}")
    return query


def validate_columns(
    provided_columns: list[str],
    expected_columns: list[str],
) -> tuple[bool, str]:
    """
    Validate that provided columns match expected columns.

    Checks that all provided columns exist in expected columns list and
    logs any missing or unexpected columns.

    Args:
        provided_columns: Columns supplied by user/caller.
        expected_columns: Expected/valid column list from COLUMNS constant.

    Returns:
        Tuple of (is_valid, message) where is_valid is True if all provided
        columns are valid.

    Example:
        >>> is_valid, msg = validate_columns(
        ...     ["order_id", "status"],
        ...     ["order_id", "customer_id", "status", "total"]
        ... )
        >>> is_valid
        True

        >>> is_valid, msg = validate_columns(
        ...     ["order_id", "invalid_col"],
        ...     ["order_id", "customer_id"]
        ... )
        >>> is_valid
        False
        >>> msg
        'Invalid columns: invalid_col'
    """
    if not provided_columns:
        return False, "No columns provided for validation"

    invalid_cols = [col for col in provided_columns if col not in expected_columns]

    if invalid_cols:
        return False, f"Invalid columns: {', '.join(invalid_cols)}"

    return True, "All columns valid"


def build_select_columns(
    columns: list[str],
    schema: str | None = None,
    table_name: str | None = None,
    alias: str | None = None,
) -> str:
    """
    Build SELECT column list with optional table qualification.

    Generates properly formatted column list for SELECT statements,
    optionally qualifying columns with table alias or name.

    Args:
        columns: List of column names to select.
        schema: Optional schema name (used for full qualification).
        table_name: Optional table name (used for full qualification).
        alias: Optional table alias (preferred over table_name for qualification).

    Returns:
        Comma-separated column list (e.g., "col1, col2, col3" or "t.col1, t.col2").

    Raises:
        ValueError: If columns list is empty.

    Example:
        >>> build_select_columns(["id", "name", "email"])
        'id, name, email'

        >>> build_select_columns(["id", "name"], alias="o")
        'o.id, o.name'

        >>> build_select_columns(["id", "status"], table_name="orders")
        'orders.id, orders.status'
    """
    if not columns:
        raise ValueError("Columns list cannot be empty")

    # Determine qualifier
    if alias:
        qualifier = f"{alias}."
    elif table_name:
        qualifier = f"{table_name}."
    else:
        qualifier = ""

    return ", ".join([f"{qualifier}{col}" for col in columns])


def merge_query_params(
    *param_groups: tuple[Any, ...] | list[Any],
) -> tuple[Any, ...]:
    """
    Merge multiple parameter groups into single tuple for multi-step queries.

    Flattens nested parameter tuples/lists into single sequence for queries
    requiring multiple parameter sets (e.g., date range + pagination).

    Args:
        *param_groups: Variable number of parameter tuples or lists.

    Returns:
        Single tuple containing all parameters in order.

    Example:
        >>> date_params = ("2024-01-01", "2024-12-31")
        >>> pagination_params = (0, 50)
        >>> query_params = merge_query_params(date_params, pagination_params)
        >>> query_params
        ('2024-01-01', '2024-12-31', 0, 50)
    """
    merged: list[Any] = []
    for group in param_groups:
        if isinstance(group, (tuple, list)):
            merged.extend(group)
        else:
            merged.append(group)
    return tuple(merged)



