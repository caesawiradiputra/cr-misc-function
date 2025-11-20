# Database Connection Strategies

Multi-database abstraction layer using the **Strategy Pattern** for clean, maintainable database connectivity across MSSQL, PostgreSQL, MySQL, Trino, Hive, and Alibaba ODPS.

## Table of Contents
- [Architecture Overview](#architecture-overview)
- [Quick Start](#quick-start)
- [Supported Databases](#supported-databases)
- [Usage Patterns](#usage-patterns)
- [Advanced Features](#advanced-features)
- [Configuration](#configuration)
- [Extending the Framework](#extending-the-framework)
- [Migration from Legacy Code](#migration-from-legacy-code)

---

## Architecture Overview

### Design Pattern: Strategy Pattern

The connection framework uses the **Strategy Pattern** to encapsulate database-specific logic into separate strategy classes, making it easy to:

- ✅ Add new database support without modifying existing code
- ✅ Test database operations in isolation
- ✅ Copy only the strategies you need to other projects
- ✅ Maintain type safety with database-specific connection types

### Module Structure

```
app/connections/
├── connection_strategy.py          # High-level facade (DBConnectorStrategy)
├── connection.py                   # Legacy connector (being phased out)
└── strategies/                     # Modular strategy implementations
    ├── __init__.py                 # Public API exports
    ├── base.py                     # Base classes and abstractions
    ├── factory.py                  # Strategy factory with type overloads
    ├── mssql_strategy.py           # Microsoft SQL Server
    ├── postgres_strategy.py        # PostgreSQL & Hologres
    ├── mysql_strategy.py           # MySQL
    ├── trino_strategy.py           # Trino distributed queries
    ├── hive_strategy.py            # Apache Hive with OSS tables
    └── odps_strategy.py            # Alibaba MaxCompute (ODPS)
```

---

## Quick Start

### Basic Usage (Recommended)

```python
from app.connections.strategies import create_strategy

# Context manager automatically handles connection lifecycle
with create_strategy("mssql") as strategy:
    df = strategy.execute_query("SELECT * FROM users WHERE active = 1")
    print(f"Found {len(df)} active users")
```

### Using the Facade (Higher-Level API)

```python
from app.connections.connection_strategy import DBConnectorStrategy

# Facade provides file-or-string query execution
with DBConnectorStrategy("mssql") as conn:
    # Execute from string
    df = conn.execute_query("SELECT COUNT(*) as total FROM orders")
    
    # Execute from file
    df = conn.execute_query("queries/monthly_report.sql")
    
    # Non-query operations (INSERT/UPDATE/DELETE)
    rows_affected = conn.execute_non_query("DELETE FROM temp_data WHERE created < ?", 
                                           params=("2024-01-01",))
```

### Repository Pattern (Domain-Specific Logic)

```python
from app.connections.strategies import create_strategy
import pandas as pd

class UserRepository:
    def __init__(self):
        self.strategy = create_strategy("mssql")  # Type-inferred as MSSQLStrategy
        self.strategy.connect()
    
    def get_active_users(self) -> pd.DataFrame:
        return self.strategy.execute_query(
            "SELECT id, name, email FROM users WHERE active = 1"
        )
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        self.strategy.disconnect()

# Usage
with UserRepository() as repo:
    users = repo.get_active_users()
```

---

## Supported Databases

| Database | Strategy Class | `db_type` | Special Features |
|----------|----------------|-----------|------------------|
| **MSSQL** | `MSSQLStrategy` | `"mssql"` | ODBC Driver 17+, connection pooling |
| **PostgreSQL** | `PostgreSQLStrategy` | `"postgres"` | psycopg2, connection pooling |
| **Hologres** | `PostgreSQLStrategy` | `"hologres"` | Uses PostgreSQL protocol |
| **MySQL** | `MySQLStrategy` | `"mysql"` | mysql-connector-python, pooling |
| **Trino** | `TrinoStrategy` | `"trino"` | HTTPS auth, distributed queries |
| **Hive** | `HiveStrategy` | `"hive"` | LDAP auth, external OSS tables |
| **ODPS** | `ODPSStrategy` | `"odps"` | Alibaba MaxCompute, thread-safe |

---

## Usage Patterns

### 1. Query Execution (SELECT)

```python
from app.connections.strategies import create_strategy

strategy = create_strategy("postgres")
strategy.connect()

# Basic query
df = strategy.execute_query("SELECT * FROM products")

# Parameterized query (prevents SQL injection)
df = strategy.execute_query(
    "SELECT * FROM orders WHERE customer_id = ? AND status = ?",
    params=(123, "PENDING")
)

strategy.disconnect()
```

### 2. Non-Query Operations (INSERT/UPDATE/DELETE/DDL)

```python
from app.connections.strategies import create_strategy

with create_strategy("mssql") as strategy:
    # INSERT
    rows = strategy.execute_non_query(
        "INSERT INTO logs (message, created_at) VALUES (?, GETDATE())",
        params=("User logged in",)
    )
    print(f"Inserted {rows} rows")
    
    # UPDATE
    rows = strategy.execute_non_query(
        "UPDATE users SET last_login = GETDATE() WHERE user_id = ?",
        params=(456,)
    )
    
    # DDL
    strategy.execute_non_query("CREATE INDEX idx_user_email ON users(email)")
```

### 3. Bulk Table Creation from DataFrame

```python
import pandas as pd
from app.connections.strategies import create_strategy

# Sample data
df = pd.DataFrame({
    'product_id': [1, 2, 3],
    'name': ['Widget', 'Gadget', 'Doohickey'],
    'price': [19.99, 29.99, 39.99]
})

with create_strategy("mssql") as strategy:
    result = strategy.create_table(
        schema="dbo",
        table_name="products_staging",
        df=df,
        if_exists="append",  # Options: "fail", "replace", "append"
        index=False
    )
    print(result)  # "Table `dbo.products_staging` created in mssql."
```

### 4. Hive External Tables (OSS Storage)

```python
import pandas as pd
from app.connections.strategies import create_strategy

df = pd.DataFrame({
    'event_id': [1, 2, 3],
    'event_type': ['click', 'view', 'purchase'],
    'timestamp': pd.to_datetime(['2024-11-01', '2024-11-02', '2024-11-03'])
})

with create_strategy("hive") as strategy:
    result = strategy.create_table(
        schema="analytics",
        table_name="events",
        df=df,
        oss_path="oss://bucket/path/to/events/",  # Required for Hive
        if_exists="replace"
    )
    # Creates external Parquet table with MSCK REPAIR
```

### 5. Connection URL for SQLAlchemy

```python
from app.connections.strategies import create_strategy

strategy = create_strategy("postgres")
url = strategy.get_connection_url()
# postgresql://user:***@host:5432/database?pool_size=5&max_overflow=10

# Use with pandas directly
import pandas as pd
df = pd.read_sql("SELECT * FROM table", url)
```

---

## Advanced Features

### Type-Safe Strategy Selection

The factory function uses `@overload` decorators for precise type inference:

```python
from app.connections.strategies import create_strategy

# Type checker knows this is MSSQLStrategy
mssql = create_strategy("mssql")  
# mssql.connection is typed as PyodbcConnection

# Type checker knows this is PostgreSQLStrategy
postgres = create_strategy("postgres")
# postgres.connection is typed as Psycopg2Connection

# Dynamic types fall back to base
db_type = input("Enter db type: ")
dynamic = create_strategy(db_type)  # Type: DatabaseStrategy
```

### Custom Database-Specific Methods

Each strategy can implement database-specific features:

```python
from app.connections.strategies import MSSQLStrategy
from app.configs.config import database_config

# Extend MSSQLStrategy with custom methods
class ExtendedMSSQLStrategy(MSSQLStrategy):
    def execute_stored_procedure(self, proc_name: str, params=None):
        if not self.cursor:
            raise ConnectionError("No active cursor")
        
        if params:
            param_str = ", ".join([f"@{k}=?" for k in params.keys()])
            query = f"EXEC {proc_name} {param_str}"
            self.cursor.execute(query, tuple(params.values()))
        else:
            self.cursor.execute(f"EXEC {proc_name}")
        
        # Fetch results
        import pandas as pd
        columns = [desc[0] for desc in self.cursor.description]
        rows = self.cursor.fetchall()
        return pd.DataFrame.from_records(rows, columns=columns)

# Usage
strategy = ExtendedMSSQLStrategy(config)
strategy.connect()
df = strategy.execute_stored_procedure("sp_GetMonthlyReport", {"year": 2024, "month": 11})
```

### Thread-Safe Async Operations (ODPS)

ODPS strategy includes built-in thread locking for concurrent operations:

```python
from app.connections.strategies import create_strategy

strategy = create_strategy("odps")
strategy.connect()

# ODPS operations are automatically thread-safe
# Internal lock prevents concurrent SQL execution issues
df = strategy.execute_query("SELECT * FROM large_table")
```

---

## Configuration

### Environment Variables (`.env`)

```bash
# MSSQL Configuration
DATABASE_MSSQL_HOST=sql-server.example.com
DATABASE_MSSQL_PORT=1433
DATABASE_MSSQL_USER=app_user
DATABASE_MSSQL_PASSWORD=secret_password
DATABASE_MSSQL_DATABASE=production_db
DATABASE_MSSQL_DRIVER=ODBC Driver 17 for SQL Server

# PostgreSQL Configuration
DATABASE_POSTGRES_HOST=postgres.example.com
DATABASE_POSTGRES_PORT=5432
DATABASE_POSTGRES_USER=postgres_user
DATABASE_POSTGRES_PASSWORD=secret_password
DATABASE_POSTGRES_DATABASE=analytics_db

# ODPS (Alibaba MaxCompute) Configuration
ODPS_ACCESS_ID=your_access_id
ODPS_ACCESS_KEY=your_secret_key
ODPS_PROJECT=your_odps_project
ODPS_ENDPOINT=http://service.odps.aliyun.com/api
```

### Config Module (`app/configs/config.py`)

```python
import os
from dotenv import load_dotenv

load_dotenv()

database_config = {
    "mssql": {
        "host": os.getenv("DATABASE_MSSQL_HOST"),
        "port": int(os.getenv("DATABASE_MSSQL_PORT", 1433)),
        "user": os.getenv("DATABASE_MSSQL_USER"),
        "password": os.getenv("DATABASE_MSSQL_PASSWORD"),
        "database": os.getenv("DATABASE_MSSQL_DATABASE"),
        "driver": os.getenv("DATABASE_MSSQL_DRIVER"),
        "pool_size": 5,
        "max_overflow": 10,
    },
    # ... other databases
}

odps_config = {
    "access_id": os.getenv("ODPS_ACCESS_ID"),
    "secret_access_key": os.getenv("ODPS_ACCESS_KEY"),
    "default_project": os.getenv("ODPS_PROJECT"),
    "endpoint": os.getenv("ODPS_ENDPOINT"),
}
```

---

## Extending the Framework

### Adding a New Database Strategy

**Example: Adding Snowflake support**

1. **Create strategy file** (`strategies/snowflake_strategy.py`):

```python
from typing import Any
from urllib.parse import quote_plus
import snowflake.connector

from .base import RDBMSBaseStrategy

class SnowflakeStrategy(RDBMSBaseStrategy):
    """Strategy for Snowflake Data Warehouse."""

    def _create_connection(self) -> Any:
        return snowflake.connector.connect(
            user=self.config.user,
            password=self.config.password,
            account=self.config.host,  # Snowflake account identifier
            warehouse='COMPUTE_WH',
            database=self.config.database,
            schema='PUBLIC'
        )

    def _build_connection_url(self) -> str:
        encoded_password = quote_plus(self.config.password)
        return f"snowflake://{self.config.user}:{encoded_password}@{self.config.host}/{self.config.database}"
```

2. **Update factory** (`strategies/factory.py`):

```python
from .snowflake_strategy import SnowflakeStrategy

_STRATEGY_MAP = {
    # ... existing mappings
    "snowflake": SnowflakeStrategy,
}

@overload
def create_strategy(db_type: Literal["snowflake"]) -> SnowflakeStrategy: ...
```

3. **Export in `__init__.py`**:

```python
from .snowflake_strategy import SnowflakeStrategy

__all__ = [
    # ... existing exports
    "SnowflakeStrategy",
]
```

---

## Migration from Legacy Code

### Old Code (`connection.py`)

```python
from app.connections.connection import DBConnector

connector = DBConnector(db_type="mssql")
with connector as conn:
    df = conn.execute_query("SELECT * FROM users")
```

### New Code (Strategies)

```python
from app.connections.strategies import create_strategy

# Direct strategy usage
with create_strategy("mssql") as strategy:
    df = strategy.execute_query("SELECT * FROM users")

# Or use the facade for backward compatibility
from app.connections.connection_strategy import DBConnectorStrategy

with DBConnectorStrategy("mssql") as conn:
    df = conn.execute_query("SELECT * FROM users")
```

---

## Best Practices

### ✅ DO

- **Use context managers** for automatic connection cleanup
- **Use parameterized queries** to prevent SQL injection
- **Create repository classes** for domain-specific logic
- **Type-hint strategy instances** for better IDE support
- **Keep SQL queries in separate files** for complex logic

### ❌ DON'T

- Don't concatenate user input into SQL strings (use params)
- Don't forget to close connections (use context managers)
- Don't put business logic in strategy classes (use repositories)
- Don't mix database types in a single repository

---

## Minimal Setup for Other Projects

To use only **MSSQL** and **PostgreSQL** in another project:

### Files to Copy

```
app/connections/strategies/
├── __init__.py           # Edit: remove unused imports
├── base.py              # Keep as-is (or remove ODPSConfig if unneeded)
├── factory.py           # Edit: remove unused strategies from map
├── mssql_strategy.py    # Keep as-is
└── postgres_strategy.py # Keep as-is
```

### Minimal `__init__.py`

```python
from .base import DBConfig, DatabaseStrategy, RDBMSBaseStrategy, timed_operation
from .postgres_strategy import PostgreSQLStrategy
from .mssql_strategy import MSSQLStrategy
from .factory import create_strategy

__all__ = [
    "DBConfig", "DatabaseStrategy", "RDBMSBaseStrategy", "timed_operation",
    "PostgreSQLStrategy", "MSSQLStrategy", "create_strategy",
]
```

### Minimal `factory.py`

```python
from typing import overload, Literal
from app.configs.config import database_config
from .base import DBConfig, DatabaseStrategy
from .postgres_strategy import PostgreSQLStrategy
from .mssql_strategy import MSSQLStrategy

_STRATEGY_MAP = {
    "postgres": PostgreSQLStrategy,
    "mssql": MSSQLStrategy,
}

@overload
def create_strategy(db_type: Literal["postgres"]) -> PostgreSQLStrategy: ...

@overload
def create_strategy(db_type: Literal["mssql"]) -> MSSQLStrategy: ...

@overload
def create_strategy(db_type: str) -> DatabaseStrategy: ...

def create_strategy(db_type: str):
    if db_type not in database_config:
        raise ValueError(f"Unsupported database type: {db_type}")
    
    db_cfg = database_config[db_type]
    cfg = DBConfig(
        db_type=db_type,
        host=db_cfg["host"],
        port=db_cfg["port"],
        user=db_cfg["user"],
        password=db_cfg["password"],
        database=db_cfg["database"],
        driver=db_cfg.get("driver"),
        pool_size=db_cfg.get("pool_size", 5),
        max_overflow=db_cfg.get("max_overflow", 10),
    )
    
    strategy_cls = _STRATEGY_MAP.get(db_type)
    if not strategy_cls:
        raise ValueError(f"No strategy found for: {db_type}")
    return strategy_cls(cfg)
```

---

## Troubleshooting

### Import Errors

**Problem:** `ImportError: cannot import name 'create_strategy'`

**Solution:** Ensure `strategies/__init__.py` exports `create_strategy`:
```python
from .factory import create_strategy
__all__ = ["create_strategy", ...]
```

### Type Inference Not Working

**Problem:** IDE doesn't autocomplete strategy-specific methods

**Solution:** Use explicit type annotation:
```python
from app.connections.strategies import create_strategy, MSSQLStrategy

strategy: MSSQLStrategy = create_strategy("mssql")  # type: ignore
```

### Connection Pool Exhausted

**Problem:** `PoolError: QueuePool limit exceeded`

**Solution:** Increase pool size in config or ensure connections are closed:
```python
database_config["mssql"]["pool_size"] = 10
database_config["mssql"]["max_overflow"] = 20
```

---

## References

- **Strategy Pattern**: [Refactoring Guru - Strategy](https://refactoring.guru/design-patterns/strategy)
- **Repository Pattern**: [Martin Fowler - Repository](https://martinfowler.com/eaaCatalog/repository.html)
- **SQLAlchemy Docs**: [SQLAlchemy Connection Pooling](https://docs.sqlalchemy.org/en/20/core/pooling.html)
- **Type Hints**: [PEP 484 - Type Hints](https://peps.python.org/pep-0484/)
