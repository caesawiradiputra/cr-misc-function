# cr-misc-function

Multi-database connection abstraction layer with unified interface for MSSQL, PostgreSQL, MySQL, Trino, Hive, and Alibaba ODPS.

## Features

- **Unified Database Interface**: Single API for multiple database engines
- **Strategy Pattern Architecture**: Clean separation between database-specific implementations
- **Connection Pooling**: Built-in connection pooling with configurable pool sizes
- **Repository Pattern Support**: Domain-specific data access layers
- **Environment-Based Configuration**: Support for `.env` files and Vault secrets
- **Type Safety**: Full type hints with IDE autocomplete support
- **Context Manager Support**: Automatic connection lifecycle management
- **File-Based Queries**: Execute SQL from files or strings

## Supported Databases

| Database | Driver | Special Features |
| -------- | ------ | ---------------- |
| MSSQL | pyodbc | Connection pooling, parameterized queries |
| PostgreSQL | psycopg2 | Named parameters, JSONB support |
| Hologres | psycopg2 | PostgreSQL-compatible interface |
| MySQL | mysql-connector | Buffered cursors |
| Trino | trino | Distributed query engine |
| Hive | pyhive | OSS table support |
| ODPS | pyodps | Alibaba MaxCompute integration |

## Prerequisites

- Python 3.11 or higher
- Conda (recommended for environment management)
- Poetry 2.0+ for dependency management
- Database driver requirements (see [Installation](#installation))

## Installation

### Step 1: Create Conda Environment

```bash
conda env create -f environment.yml
conda activate cr-misc-function-env
```

### Step 2: Install Dependencies with Poetry

```bash
poetry install
```

This installs all required packages including:

- SQLAlchemy for database abstraction
- Pandas for data processing
- Pydantic for configuration validation
- Database drivers (pyodbc, psycopg2, mysql-connector, trino, pyhive, pyodps)
- Loguru for structured logging

### Step 3: Configure Environment Variables

Create a `.env` file in the project root:

```env
# MSSQL Configuration
DATABASE_MSSQL_SERVER=your-server.database.windows.net
DATABASE_MSSQL_PORT=1433
DATABASE_MSSQL_DATABASE=your_database
DATABASE_MSSQL_USER=your_username
DATABASE_MSSQL_PASSWORD=your_password

# PostgreSQL Configuration
DATABASE_POSTGRES_SERVER=localhost
DATABASE_POSTGRES_PORT=5432
DATABASE_POSTGRES_DATABASE=your_database
DATABASE_POSTGRES_USER=your_username
DATABASE_POSTGRES_PASSWORD=your_password
```

> [!NOTE]
> Configuration supports two-tier loading: `.env` file (default) and Vault secrets
> at `/vault/secrets/.env` (Docker/Kubernetes deployments). Vault secrets override
> local `.env` values.

## Quick Start

### Basic Database Connection

```python
from app.connections.strategies import create_strategy

# Pattern 1: Direct strategy with context manager (recommended)
with create_strategy("mssql") as strategy:
    df = strategy.execute_query("SELECT * FROM users WHERE status = ?", params=("active",))
    print(df.head())
```

### File-Based Query Execution

```python
from app.connections.connection_strategy import DBConnectorStrategy

# Pattern 2: Facade with file-or-string execution
with DBConnectorStrategy("postgres") as conn:
    # Automatically reads from file if exists
    df = conn.execute_query("queries/monthly_report.sql")
```

### Repository Pattern Usage

```python
from repositories.order_repository import OrderRepository

# Pattern 3: Domain-specific repository
with OrderRepository() as repo:
    pending_orders = repo.get_pending_orders(days=30)
    repo.insert_bulk_orders(orders_df)
```

## Configuration

### Database Configuration Structure

The configuration system loads from multiple sources with the following precedence:

1. **`.env` file** (project root) - loaded first
2. **Vault secrets** (`/vault/secrets/.env`) - overrides `.env` if present
3. **Config dictionaries** in `app/configs/config.py` - built from environment variables

### Environment Variables by Database

Each database type requires specific environment variables:

**MSSQL**: `DATABASE_MSSQL_SERVER`, `DATABASE_MSSQL_PORT`, `DATABASE_MSSQL_DATABASE`,
`DATABASE_MSSQL_USER`, `DATABASE_MSSQL_PASSWORD`

**PostgreSQL**: `DATABASE_POSTGRES_SERVER`, `DATABASE_POSTGRES_PORT`,
`DATABASE_POSTGRES_DATABASE`, `DATABASE_POSTGRES_USER`, `DATABASE_POSTGRES_PASSWORD`

**MySQL**: `DATABASE_MYSQL_SERVER`, `DATABASE_MYSQL_PORT`, `DATABASE_MYSQL_DATABASE`,
`DATABASE_MYSQL_USER`, `DATABASE_MYSQL_PASSWORD`

**Trino**: `DATABASE_TRINO_HOST`, `DATABASE_TRINO_PORT`, `DATABASE_TRINO_USER`,
`DATABASE_TRINO_CATALOG`, `DATABASE_TRINO_SCHEMA`

**Hive**: `DATABASE_HIVE_HOST`, `DATABASE_HIVE_PORT`, `DATABASE_HIVE_DATABASE`

**ODPS**: `DATABASE_ODPS_ACCESS_ID`, `DATABASE_ODPS_SECRET_KEY`, `DATABASE_ODPS_PROJECT`,
`DATABASE_ODPS_ENDPOINT`

> [!WARNING]
> Environment variables default to empty strings. Missing required fields are only
> validated when creating a strategy instance. Ensure all required configuration
> is present before instantiating strategies.

## Architecture

### Strategy Pattern Implementation

The project uses the Strategy Pattern to provide a unified interface across different
database engines:

```text
app/connections/strategies/
├── base.py              # Abstract base classes (DatabaseStrategy, RDBMSBaseStrategy)
├── factory.py           # Strategy factory with type overloads
├── mssql_strategy.py    # MSSQL implementation
├── postgres_strategy.py # PostgreSQL implementation
├── mysql_strategy.py    # MySQL implementation
├── trino_strategy.py    # Trino implementation
├── hive_strategy.py     # Hive implementation
└── odps_strategy.py     # ODPS implementation
```

### Key Components

**Base Strategy**: Abstract interface defining `connect()`, `disconnect()`, `execute_query()`,
`execute_non_query()`, `create_table()`, and `is_connected()`.

**Factory**: Routes database type to concrete strategy with configuration validation.

**Facade**: Public API in `connection_strategy.py` for backwards compatibility and
file-based query execution.

**Repository Layer**: Domain-specific abstraction over strategies (see `repositories/`).

### Connection Lifecycle

All strategies implement the context manager protocol:

```python
def __enter__(self):
    self.connect()
    return self

def __exit__(self, exc_type, exc_val, exc_tb):
    if exc_type:
        logger.error(f"Operation failed: {exc_val}")
    self.disconnect()
```

## Advanced Usage

### Creating Custom Repositories

```python
from app.connections.strategies import create_strategy
import pandas as pd

class InvoiceRepository:
    def __init__(self):
        self.strategy = create_strategy("mssql")
        self.strategy.connect()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.strategy.disconnect()

    def get_unpaid_invoices(self, customer_id: str) -> pd.DataFrame:
        query = """
        SELECT invoice_id, amount, due_date
        FROM invoices
        WHERE customer_id = ? AND status = 'unpaid'
        ORDER BY due_date
        """
        return self.strategy.execute_query(query, params=(customer_id,))
```

### Connection Pool Tuning

Adjust pool settings for high-concurrency scenarios:

```python
# In app/configs/config.py
DATABASE_MSSQL = {
    "server": os.environ.get("DATABASE_MSSQL_SERVER"),
    # ... other config
    "pool_size": 10,        # Default: 5
    "max_overflow": 20,     # Default: 10
}
```

### Adding New Database Support

1. Create strategy class in `app/connections/strategies/{db}_strategy.py`
2. Inherit from `RDBMSBaseStrategy` or `DatabaseStrategy`
3. Implement abstract methods
4. Add entry to factory in `app/connections/strategies/factory.py`
5. Add configuration variables to `app/configs/config.py`

See [app/connections/README.md](app/connections/README.md) for detailed implementation guide.

## Development Tools

### Environment Management Scripts

**Detect Undeclared Packages**:

```bash
python scripts/python/dev_detect_undeclared_packages.py --env cr-misc-function-env
```

Identifies packages installed in Conda environment but not declared in `pyproject.toml`.
Supports severity classification (INFO/WARNING/CRITICAL) with color-coded output.

**Generate Environment File**:

```bash
python scripts/python/dev_generate_env.py --env cr-misc-function-env
```

Generates portable `environment.yml` from Conda environment with Poetry detection.

**Remove Base-Only Packages**:

```bash
python scripts/python/dev_remove_base_only_packages.py
```

Removes packages that only exist in base Conda environment, not project-specific.

### Git Workflow Scripts

PowerShell scripts in `scripts/powershell/` for branch management:

- `git-create-clean-branch.ps1` - Create new feature branch
- `git-clean-branches.ps1` - Clean up merged branches
- `git-rebase-branch.ps1` - Interactive rebase workflow

## Further Reading

- [Architecture Guide](app/connections/README.md) - Detailed strategy implementation
- [Database Setup Guide](docs/database/SETUP_GUIDE.md) - Database-specific configuration
- [Deployment Guide](docs/deployment/DEPLOYMENT_GUIDE.md) - Production deployment
- [Logging Configuration](docs/logging-configuration.md) - Structured logging setup
- [Confluence Documentation](docs/confluence/) - Business system documentation
