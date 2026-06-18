---
name: refactor-repositories
version: "1.0.0"
updated: "2026-06-18"
related_skills:
  - refactor-python
description: Apply mandatory structure and patterns to repository files in the repositories/ folder. Supplements /refactor-python with repository-specific standards. Use when the user triggers /refactor-repositories or asks to refactor repository classes.
---

# Refactor Repositories

Apply mandatory structure and patterns to files in the `repositories/` folder. These rules supplement `/refactor-python` with repository-specific standards.

## Target

If arguments specify a file or folder path, refactor that target. Otherwise, ask for the target.

## Mandatory Repository Structure

Every repository class MUST have this structure in exactly this order:

### 1. Class Constants (Required — Define Before `__init__`)

```python
class OrderRepository:
    """Repository for accessing order data."""

    DATABASE_TYPE: str = "mssql"   # lowercase: "mssql", "postgres", "mysql", "hive", "trino", "odps"
    SCHEMA: str = "dbo"            # For MSSQL/PostgreSQL/Hive (schema-based)
    # DATABASE: str = "db_name"    # For MySQL/Hive (database-based) — use instead of SCHEMA
    TABLE_NAME: str = "orders"
    COLUMNS: list[str] = [
        "order_id", "customer_id", "total_amount", "status", "created_at",
    ]
```

**Database-type mapping:**

| DB Type | Use | Example |
| --- | --- | --- |
| MSSQL | `SCHEMA` | `DATABASE_TYPE = "mssql"`, `SCHEMA = "dbo"` |
| PostgreSQL | `SCHEMA` | `DATABASE_TYPE = "postgres"`, `SCHEMA = "public"` |
| MySQL | `DATABASE` | `DATABASE_TYPE = "mysql"`, `DATABASE = "transactions_db"` |
| Hive | `DATABASE` | `DATABASE_TYPE = "hive"`, `DATABASE = "data_warehouse"` |

### 2. Initialization

```python
def __init__(self):
    """Initialize repository with database strategy connection."""
    self.strategy = create_strategy(self.DATABASE_TYPE)
    self.strategy.connect()
```

No other logic in `__init__`.

### 3. Context Manager Protocol

```python
def __enter__(self):
    return self

def __exit__(self, exc_type, exc_val, exc_tb):
    if exc_type:
        logger.error("[%s] Operation failed: %s", self.__class__.__name__, exc_val, exc_info=True)
    self.strategy.disconnect()
```

### 4. Public Methods — Domain-Specific Names

```python
# Good — domain-specific
def get_pending_orders(self, days: int = 30) -> pd.DataFrame | None: ...
def insert_bulk_orders(self, orders: list[dict]) -> int: ...

# Bad — generic CRUD (belongs to strategy layer)
def execute_query(self, sql: str): ...
def get_all(self): ...
```

## Return Type Consistency

| Method Type | Return Type |
| --- | --- |
| Query methods | `pd.DataFrame \| None` |
| Insert/Update/Delete | `int` (rows affected) |
| Single record lookup | `dict[str, Any] \| None` |

## Available Utilities (Use — Don't Duplicate)

Before referencing utilities, detect the project's utility module path. Common conventions:
- `{utils_dir}/repo_utils.py` — query helpers, placeholder generation, column validation
- `{utils_dir}/data_utils.py` — import/export converters (CSV, Parquet, JSON)

**`{utils_dir}`** is determined by scanning the project for files named `repo_utils.py` or `data_utils.py`. Typical locations: `utils/`, `app/utils/`, `src/utils/`. If not found, ask the user.

### Typical functions in `repo_utils`
`read_query_file`, `generate_placeholders`, `build_insert_query`, `build_update_query`, `validate_columns`, `build_select_columns`, `merge_query_params`

### Typical functions in `data_utils`
`export_to_csv`, `import_from_csv`, `export_to_parquet`, `import_from_parquet`, `export_to_json`, `import_from_json`, `convert_csv_to_parquet`, `convert_parquet_to_csv`, `convert_csv_to_json`, `convert_json_to_parquet`, `convert_json_to_csv`

## Error Handling Pattern

```python
def get_order_by_id(self, order_id: int) -> dict[str, Any] | None:
    query = f"SELECT * FROM {self.TABLE_NAME} WHERE order_id = ?"
    try:
        result = self.strategy.execute_query(query, params=(order_id,))
        if result is not None and len(result) > 0:
            return result.iloc[0].to_dict()
        return None
    except Exception as e:
        logger.error("[OrderRepository] Failed to fetch order %s: %s", order_id, e)
        return None
```

## Common Patterns

### Query Constants
```python
QUERY_PENDING = f"SELECT * FROM {SCHEMA}.{TABLE_NAME} WHERE status = 'PENDING'"
```

### External SQL Files
```python
query = read_query_file("queries/orders/by_date_range.sql")
return self.strategy.execute_query(query, params=(start, end))
```

### Bulk Insert
```python
def insert_bulk_orders(self, orders: list[dict[str, Any]]) -> int:
    if not orders: return 0
    query = build_insert_query(self.SCHEMA, self.TABLE_NAME, list(orders[0].keys()))
    rows_affected = 0
    for order in orders:
        rows_affected += self.strategy.execute_non_query(query, params=tuple(order.values()))
    return rows_affected
```

### Correct Usage (Context Manager)
```python
with OrderRepository() as repo:
    pending = repo.get_pending_orders()
```

## File Organization

```text
repositories/
+-- mssql/
|   +-- order_repo.py       -> OrderRepository
|   +-- user_repo.py        -> UserRepository
+-- postgres/
|   +-- shipment_repo.py    -> ShipmentRepository
+-- hive/
    +-- analytics_repo.py   -> AnalyticsRepository
```

Folder = database type (lowercase), filename = `{table_name}_repo.py`, class = `{TableName}Repository`.

## Refactoring Checklist

- [ ] `DATABASE_TYPE` constant defined (lowercase)
- [ ] `SCHEMA` or `DATABASE` constant defined
- [ ] `TABLE_NAME` matches actual database table name
- [ ] `COLUMNS` list includes all managed columns
- [ ] Constants defined BEFORE `__init__`
- [ ] `__init__` uses `create_strategy(self.DATABASE_TYPE)` and calls `connect()`
- [ ] `__enter__` and `__exit__` implemented
- [ ] All public methods are domain-specific
- [ ] Return types consistent
- [ ] Error handling catches database exceptions with context logging
- [ ] All methods have Google-style docstrings
- [ ] No business logic in repository (data access only)
- [ ] File in correct `repositories/{dbtype}/` subfolder
