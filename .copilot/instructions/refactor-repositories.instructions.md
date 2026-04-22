---
description: 'Refactoring guidelines specific to the repositories data access layer'
applyTo: 'repositories/**/*.py'
---

# Repository Refactoring Guidelines

Specialized refactoring rules for all files in the `repositories/` folder. These supplement the general [Python refactoring guidelines](./refactor-python-code.instructions.md) with repository-specific patterns.

---

## Repository Mandatory Structure

Every repository class MUST follow this standardized structure (in order):

### 1. Class Constants (Required)

Define exactly these constants at the top of the class:

```python
class OrderRepository:
    """Repository for accessing order data."""

    # Database and schema/database configuration
    DATABASE_TYPE: str = "mssql"  # or "postgres", "mysql", "hive", etc.
    SCHEMA: str = "dbo"  # MSSQL, PostgreSQL, or Hive schema name
    # OR use DATABASE for MySQL:
    # DATABASE: str = "your_database_name"

    TABLE_NAME: str = "orders"
    COLUMNS: list[str] = [
        "order_id",
        "customer_id",
        "total_amount",
        "status",
        "created_at",
    ]
```

**Rules:**
- `DATABASE_TYPE` MUST specify the database type (e.g., `"mssql"`, `"postgres"`, `"mysql"`, `"hive"`)
- Use **SCHEMA** for: MSSQL, PostgreSQL, Hive (schema-based databases)
- Use **DATABASE** for: MySQL (database-based tables)
- Include both if your strategy handles multiple database types
- `TABLE_NAME` MUST be the exact database table name
- `COLUMNS` MUST list all columns the repository manages
- Constants MUST be defined before `__init__`
- All constants are **non-negotiable** in every repository

**Database-Specific Examples:**

MSSQL (uses schema):
```python
DATABASE_TYPE = "mssql"
SCHEMA = "dbo"
TABLE_NAME = "orders"
```

PostgreSQL (uses schema):
```python
DATABASE_TYPE = "postgres"
SCHEMA = "public"  # or custom schema like "sales"
TABLE_NAME = "orders"
```

MySQL (uses database):
```python
DATABASE_TYPE = "mysql"
DATABASE = "transactions_db"
TABLE_NAME = "orders"
```

Hive (uses database):
```python
DATABASE_TYPE = "hive"
DATABASE = "data_warehouse"
TABLE_NAME = "orders"
```

### 2. Initialization (Standard Pattern)

```python
def __init__(self):
    """Initialize repository with database strategy connection."""
    self.strategy = create_strategy(self.DATABASE_TYPE)
    self.strategy.connect()
```

**Rules:**
- Initialize `self.strategy` using `self.DATABASE_TYPE` constant
- Call `connect()` immediately
- No other logic in `__init__`
- Use context manager pattern for lifecycle management (`__enter__` / `__exit__`)

### 3. Public Methods (Domain-Specific)

All repository methods should be domain-specific queries, not generic CRUD operations when possible.

**Good naming:**
- `get_pending_orders(days: int) -> pd.DataFrame`
- `get_orders_by_status(status: str) -> pd.DataFrame`
- `insert_bulk_orders(orders: list[dict]) -> int`

**Avoid generic names:**
- ❌ `get_all()` → Instead: `get_all_orders() -> pd.DataFrame`
- ❌ `insert()` → Instead: `insert_order(order: dict) -> int`
- ❌ `find()` → Instead: `find_by_customer(customer_id: int) -> pd.DataFrame`
- ❌ `execute_query()` → This is for internal strategy use only; use domain-specific names instead
- ❌ `execute_non_query()` → This is for internal strategy use only; use `insert_*()`, `update_*()`, `delete_*()` instead

**Note:** Generic names like `execute_query()` and `execute_non_query()` belong to the database **strategy layer** (internal implementation). Never expose these in repository public methods. Always wrap them in domain-specific methods.

### 4. Context Manager Protocol

All repositories MUST implement lifecycle management:

```python
def __enter__(self):
    """Enter context manager."""
    return self

def __exit__(self, exc_type, exc_val, exc_tb):
    """Exit context manager and cleanup."""
    if exc_type:
        logger.error(f"[{self.__class__.__name__}] Operation failed: {exc_val}", exc_info=True)
    self.strategy.disconnect()
```

---

## Query Method Standards

### Built-in Repository Utilities

**Repository utilities are organized in two modules:**

```python
# Query and SQL utilities (7 functions)
from app.utils.repo_utils import (
    read_query_file,
    generate_placeholders,
    build_insert_query,
    build_update_query,
    validate_columns,
    build_select_columns,
    merge_query_params,
)

# Data format I/O and conversion utilities (11 functions)
from app.utils.data_utils import (
    # CSV operations
    export_to_csv,
    import_from_csv,
    # Parquet operations
    export_to_parquet,
    import_from_parquet,
    # JSON operations
    export_to_json,
    import_from_json,
    # Format converters
    convert_csv_to_parquet,
    convert_parquet_to_csv,
    convert_csv_to_json,
    convert_json_to_parquet,
    convert_parquet_to_json,
    convert_json_to_csv,
)
```

**repo_utils: Query and SQL Functions (7 functions):**

| Function | Purpose | Example |
| ------ | --------- | --------- |
| `read_query_file(path)` | Load SQL from file with validation | `query = read_query_file("queries/orders/pending.sql")` |
| `generate_placeholders(count, db_type)` | Generate `?` or `%s` based on db | `generate_placeholders(3, "mssql")` → `"?, ?, ?"` |
| `build_insert_query(schema, table, cols)` | Generate INSERT with placeholders | `build_insert_query("dbo", "orders", ["id", "name"])` |
| `build_update_query(schema, table, cols, where_col)` | Generate UPDATE with placeholders | `build_update_query("dbo", "orders", ["status"], "id")` |
| `validate_columns(provided, expected)` | Validate column names | `validate_columns(["id", "name"], COLUMNS)` |
| `build_select_columns(cols, alias="t")` | Build SELECT column list | `build_select_columns(["id", "name"], alias="o")` |
| `merge_query_params(*groups)` | Flatten parameter tuples | `merge_query_params((start, end), (limit, offset))` |

**data_utils: Data I/O and Conversion Functions (11 functions):**

| Function | Purpose | Example |
| ------ | --------- | --------- |
| `export_to_csv(df, path)` | Export DataFrame to CSV | `export_to_csv(df, "output.csv", overwrite=True)` |
| `import_from_csv(path, columns, dtype)` | Import CSV to DataFrame | `df = import_from_csv("data.csv", dtype={"id": "int64"})` |
| `export_to_parquet(df, path, compression)` | Export to Parquet (efficient) | `export_to_parquet(df, "output.parquet", compression="snappy")` |
| `import_from_parquet(path, columns)` | Import Parquet with preserved types | `df = import_from_parquet("data.parquet")` |
| `export_to_json(df, path, orient)` | Export DataFrame to JSON | `export_to_json(df, "data.json", orient="records", indent=2)` |
| `import_from_json(path, orient, dtype)` | Import JSON to DataFrame | `df = import_from_json("data.json", orient="records")` |
| `convert_csv_to_parquet(in, out)` | CSV → Parquet (with compression) | `convert_csv_to_parquet("raw.csv", "data.parquet")` |
| `convert_parquet_to_csv(in, out)` | Parquet → CSV | `convert_parquet_to_csv("data.parquet", "export.csv")` |
| `convert_csv_to_json(in, out, orient)` | CSV → JSON | `convert_csv_to_json("data.csv", "api.json", orient="records")` |
| `convert_json_to_parquet(in, out)` | JSON → Parquet (efficient storage) | `convert_json_to_parquet("api.json", "snapshot.parquet")` |
| `convert_parquet_to_json(in, out)` | Parquet → JSON | `convert_parquet_to_json("snapshot.parquet", "export.json")` |
| `convert_json_to_csv(in, out, orient)` | JSON → CSV (human-readable) | `convert_json_to_csv("api.json", "export.csv")` |

### Using Query Files

Load external SQL files instead of embedding in code:

```python
from app.utils.repo_utils import read_query_file

class OrderRepository:
    DATABASE_TYPE = "mssql"
    SCHEMA = "dbo"
    TABLE_NAME = "orders"
    COLUMNS = ["order_id", "customer_id", "status", "created_at"]

    def __init__(self):
        self.strategy = create_strategy(self.DATABASE_TYPE)
        self.strategy.connect()

    def get_pending_orders(self) -> pd.DataFrame:
        """Retrieve all pending orders from external query file."""
        try:
            query = read_query_file("queries/orders/pending.sql")
            return self.strategy.execute_query(query)
        except FileNotFoundError as e:
            logger.error(f"Query file not found: {e}")
            return None
```

**Query file validation ensures:**
- ✅ File exists at specified path
- ✅ File is readable (not locked)
- ✅ File is not empty
- ✅ Proper encoding (UTF-8)
- ✅ File load errors logged with full context

### Using Data I/O and Format Conversion

For data import/export and format conversions, use utilities from `app.utils.data_utils`:

| Function | Purpose |
|----------|---------|
| `export_to_csv()` | Export DataFrame to CSV (human-readable, spreadsheet-friendly) |
| `import_from_csv()` | Import DataFrame from CSV with column/type filtering |
| `export_to_parquet()` | Export DataFrame to Parquet (50-70% smaller, 2-5x faster) |
| `import_from_parquet()` | Import DataFrame from Parquet with column selection |
| `export_to_json()` | Export DataFrame to JSON (API-ready, flexible structure) |
| `import_from_json()` | Import DataFrame from JSON with type mapping |
| `convert_csv_to_parquet()` | Convert CSV → Parquet (raw data → efficient storage) |
| `convert_parquet_to_csv()` | Convert Parquet → CSV |
| `convert_csv_to_json()` | Convert CSV → JSON |
| `convert_parquet_to_json()` | Convert Parquet → JSON |
| `convert_json_to_parquet()` | Convert JSON → Parquet |
| `convert_json_to_csv()` | Convert JSON → CSV |

All functions have comprehensive docstrings with usage examples, parameter details, and return types. Consult the docstrings directly:

```python
from app.utils.data_utils import export_to_csv, convert_csv_to_parquet
help(export_to_csv)  # View full docstring with examples
help(convert_csv_to_parquet)
```

**Quick reference:**
- All converters use pandas DataFrame as intermediate representation
- Compression options for Parquet: snappy, gzip, brotli, lz4, zstd
- JSON orient options: records (default), split, index, columns, values
- All functions validate file paths, handle errors, and log operations

---

### Return Type Consistency

- **Query methods:** Always return `pd.DataFrame | None`
- **Insert/Update/Delete:** Always return `int` (rows affected)
- **Single record lookups:** Return `dict[str, Any] | None`

Example:

```python
def get_orders_by_status(self, status: str) -> pd.DataFrame | None:
    """Retrieve all orders with specified status."""
    query = "SELECT * FROM orders WHERE status = ?"
    try:
        return self.strategy.execute_query(query, params=(status,))
    except Exception as e:
        logger.error(f"Failed to fetch orders: {e}")
        return None

def insert_order(self, order_data: dict[str, Any]) -> int:
    """Insert new order and return row count."""
    columns = ", ".join(order_data.keys())
    placeholders = ", ".join(["?"] * len(order_data))
    query = f"INSERT INTO {self.TABLE_NAME} ({columns}) VALUES ({placeholders})"
    return self.strategy.execute_non_query(query, params=tuple(order_data.values()))
```

### Parameter Handling

- Use positional parameters for database compatibility
- Pass tuples for positional params: `params=(value1, value2)`
- Document parameter order in docstring if complex

```python
def get_orders_in_range(self, start_date: str, end_date: str) -> pd.DataFrame:
    """
    Get orders created between date range.

    Args:
        start_date: Start date (YYYY-MM-DD format).
        end_date: End date (YYYY-MM-DD format).

    Returns:
        DataFrame of matching orders.
    """
    query = f"SELECT * FROM {self.TABLE_NAME} WHERE created_at BETWEEN ? AND ?"
    return self.strategy.execute_query(query, params=(start_date, end_date))
```

### Error Handling in Repository Methods

- Catch database errors at the repository level
- Log with context (table, operation, user if available)
- Re-raise or return None based on method contract

```python
def get_order_by_id(self, order_id: int) -> dict[str, Any] | None:
    """Retrieve single order by ID."""
    query = f"SELECT * FROM {self.TABLE_NAME} WHERE order_id = ?"
    try:
        result = self.strategy.execute_query(query, params=(order_id,))
        if result is not None and len(result) > 0:
            return result.iloc[0].to_dict()
        return None
    except Exception as e:
        logger.error(f"[OrderRepository] Failed to fetch order {order_id}: {e}")
        return None
```

---

## Refactoring Checklist for Repositories

Before finalizing any repository refactoring:

- [ ] Class has `DATABASE_TYPE` constant specifying database type ("mssql", "postgres", etc.)
- [ ] Class has either `SCHEMA` (for MSSQL/PostgreSQL/Hive) or `DATABASE` (for MySQL/Hive)
- [ ] Class has `TABLE_NAME` constant (exact database table name)
- [ ] Class has `COLUMNS` list of all managed columns
- [ ] All public methods are domain-specific (not generic CRUD)
- [ ] Return types are consistent (`pd.DataFrame | None`, `int`, or `dict | None`)
- [ ] Query methods use positional parameters with tuples
- [ ] Error handling catches database-specific exceptions
- [ ] Class implements context manager (`__enter__` / `__exit__`)
- [ ] Docstrings document Args, Returns, and parameter order
- [ ] No direct database connections—uses `self.strategy`
- [ ] Logging includes context (method name, table, key identifiers)
- [ ] No business logic—only data access and transformation

---

## Common Refactoring Patterns in Repositories

### Pattern 1: Extract Query to Named Constant

When queries are reused, store as class-level constant:

```python
class OrderRepository:
    DATABASE_TYPE = "mssql"
    SCHEMA = "dbo"
    TABLE_NAME = "orders"
    COLUMNS = ["order_id", "customer_id", "status"]

    # Query constants at module level
    QUERY_PENDING = f"SELECT * FROM {SCHEMA}.{TABLE_NAME} WHERE status = 'PENDING'"
    QUERY_BY_DATE_RANGE = f"SELECT * FROM {SCHEMA}.{TABLE_NAME} WHERE created_at BETWEEN ? AND ?"

    def get_pending_orders(self) -> pd.DataFrame:
        return self.strategy.execute_query(self.QUERY_PENDING)

    def get_orders_by_date(self, start: str, end: str) -> pd.DataFrame:
        return self.strategy.execute_query(self.QUERY_BY_DATE_RANGE, params=(start, end))
```

### Pattern 2: Batch Operations Efficiently

Use `execute_non_query()` for bulk inserts/updates to reduce round trips:

```python
def insert_bulk_orders(self, orders: list[dict[str, Any]]) -> int:
    """Insert multiple orders in single operation."""
    if not orders:
        return 0

    # Prepare bulk insert query
    columns = ", ".join(orders[0].keys())
    placeholders = ", ".join(["?"] * len(orders[0]))
    query = f"INSERT INTO {self.TABLE_NAME} ({columns}) VALUES ({placeholders})"

    rows_affected = 0
    for order in orders:
        rows = self.strategy.execute_non_query(query, params=tuple(order.values()))
        rows_affected += rows

    return rows_affected
```

### Pattern 3: Transform Results Before Returning

Convert DataFrames to domain objects when appropriate:

```python
def get_orders_as_dicts(self, status: str) -> list[dict[str, Any]]:
    """Get orders as list of dictionaries."""
    query = f"SELECT * FROM {self.TABLE_NAME} WHERE status = ?"
    df = self.strategy.execute_query(query, params=(status,))

    if df is None or df.empty:
        return []

    return df.to_dict(orient="records")
```

---

## File Organization

### Naming Convention

```
repositories/
├── {dbtype}/                    # Organized by database type
│   ├── order_repo.py           # One table per file
│   ├── user_repo.py
│   └── shipment_repo.py
```

**Rules:**
- Folder = database type (mssql, postgres, hive, etc.)
- Filename = `{table_name}_repo.py` (lowercase, snake_case)
- Class name = `{TableName}Repository` (PascalCase)
- Example: `order_repo.py` → `OrderRepository` class

### File Structure Order

Within each repository file:

1. Imports (standard lib, third-party, local)
2. Logger initialization
3. Repository class definition:
   - Docstring
   - `TABLE_NAME` constant
   - `COLUMNS` constant
   - Query constants (if any)
   - `__init__`
   - `__enter__` / `__exit__`
   - Public methods (domain-specific queries)
   - Private methods (helpers, if any)

---

## Connection Lifecycle

### Correct Usage in Application

```python
# GOOD: Use context manager for automatic cleanup
with OrderRepository() as repo:
    pending_orders = repo.get_pending_orders()
    # disconnect() called automatically on exit

# BAD: Manual management (error-prone)
repo = OrderRepository()
orders = repo.get_pending_orders()
repo.strategy.disconnect()  # Easily forgotten
```

### Error Safety

Context manager ensures cleanup even on errors:

```python
with OrderRepository() as repo:
    try:
        orders = repo.get_pending_orders()
    except Exception as e:
        # __exit__ still called, cleanup guaranteed
        logger.error(f"Database error: {e}")
```

---

## Validation Checklist

✅ `DATABASE_TYPE` constant defined and matches strategy type
✅ `SCHEMA` or `DATABASE` constant defined (based on db type)
✅ `TABLE_NAME` constant defined and matches real database table
✅ `COLUMNS` list includes all managed columns
✅ All public methods are domain-specific operations
✅ Return types consistent and documented
✅ Error handling at the repository level
✅ Context manager protocol implemented
✅ No circular imports or dependency issues
✅ Logging includes relevant context
✅ File organized by database type in proper subfolder
✅ Class and file naming follows conventions
✅ All methods have Google-style docstrings

---

## Related Guidelines

- **General Refactoring:** [Python Code Refactoring Guidelines](./refactor-python-code.instructions.md)
- **Architecture Context:** [Codebase Overview](./../../.github/copilot-instructions.md) — Architecture: Strategy Pattern for Database Abstraction
- **Database Strategies:** [Connection Strategies Documentation](./../../.github/copilot-instructions.md) — Database Strategy Implementations
