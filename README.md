# cr-misc-function

Shared commons library providing reusable database abstraction, utility functions,
AI tooling templates, and development scripts for use across multiple projects.

## Features

- **Unified Database Interface**: Single API for 6 database engines (MSSQL, PostgreSQL, MySQL, Trino, Hive, ODPS)
- **Strategy Pattern Architecture**: Pluggable database implementations with zero coupling
- **Repository Pattern**: Type-safe, auto-generated CRUD with domain-specific business logic
- **Three-Tier Configuration**: Vault secrets, `.env` files, and environment variables with Pydantic validation
- **Utility Functions**: Copy-paste ready helpers for data I/O, dates, files, and SQL operations
- **AI Tooling**: 12 Qoder skills, 2 custom agents, Claude Code commands, and Copilot instructions
- **Reusable Templates**: Conda, Poetry, VS Code, ruff, mypy, and AI agent configs
- **Development Scripts**: Git workflows, environment management, and lint validation

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
> Configuration supports four-tier priority loading: Vault secrets
> at `/vault/secrets/.env` (Docker/Kubernetes), local `.env` file,
> environment variables, then built-in defaults. Higher tiers override lower.

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
from app.repositories.order_repository import OrderRepository

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

## Utility Functions

Copy-paste ready utilities in `app/utils/`:

| Module | Functions | Purpose |
| ------ | --------- | ------- |
| `data_utils.py` | 11 | CSV/Parquet/JSON import, export, and conversion |
| `repo_utils.py` | 7 | SQL query building, placeholder generation, column validation |
| `date_util.py` | — | Date parsing, formatting, and timezone handling |
| `file_util.py` | — | File reading, writing, and path operations |
| `pvc_data_manager.py` | — | PVC data lifecycle management |

## AI Tooling

### Qoder Skills (`QODER/skills/`)

12 slash-command skills for common development workflows:

| Skill | Trigger | Purpose |
| ----- | ------- | ------- |
| commit | `/commit` | Conventional Commits + gitmoji message generation |
| clean-gone | `/clean-gone` | Delete stale local branches and worktrees |
| refactor-python | `/refactor-python` | Systematic Python code quality improvement |
| refactor-repositories | `/refactor-repositories` | Repository pattern enforcement |
| generate-pr-message | `/generate-pr-message` | PR messages + per-ticket changelog |
| validate-lint-config | `/validate-lint-config` | Sync ruff.toml and mypy.ini with environment |
| create-readme | `/create-readme` | README generation following standards |
| create-confluence-docs | `/create-confluence-docs` | Hierarchical Confluence documentation |
| generate-cde | `/generate-cde` | CDE registry from scratch (Mode A) |
| update-cde | `/update-cde` | CDE incremental updates (Mode B) |
| generate-cde-spreadsheet | `/generate-cde-spreadsheet` | CDE TSV spreadsheets |
| setup-workspace | `/setup-workspace` | IDE/agent configuration audit |

Sync skills to global `~/.qoder/`:

```powershell
.\scripts\powershell\chat-Sync-QoderContext.ps1
```

### Other AI Configs

- **Claude Code**: Commands in `CLAUDE/commands/`, context in `CLAUDE/CLAUDE.md`
- **GitHub Copilot**: Instructions in `.github/copilot-instructions.md`
- **Templates**: Reusable AI configs in `templates/ai/` (Qoder, Claude, Copilot)

## Templates

Reusable project scaffolding in `templates/`:

```text
templates/
+-- ai/              - AI agent configs (Qoder, Claude Code, Copilot)
+-- conda/py311/     - Conda environment.yml (Python 3.11)
+-- conda/py39/      - Conda environment.yml (Python 3.9)
+-- vscode/          - VS Code extensions.json and settings.json
+-- ruff.toml        - Linting and formatting config
+-- mypy.ini         - Type checking config
```

## Development Scripts

### Environment Management

```powershell
# Detect undeclared packages
python scripts/python/dev_detect_undeclared_packages.py --env cr-misc-function-env

# Generate environment file from Conda
python scripts/python/dev_generate_env.py --env cr-misc-function-env
```

### Git Workflow

PowerShell scripts in `scripts/powershell/` with a shared helper module
(`modules/GitScriptHelpers.psm1`) for consistent output, prompts, and git utilities.

| Script | Purpose |
| ------ | ------- |
| `git-clean-branches.ps1` | Delete local branches gone from remote, update protected branches |
| `git-check-sync-set-dev.ps1` | Check dev-master sync (diff-based), activate dev if in sync |
| `git-init-feature.ps1` | Create feature branch with naming convention, auto-push |
| `git-create-clean-branch.ps1` | Cherry-pick filtered commits to a clean branch |
| `git-rebase-branch.ps1` | Rebase feature branch onto base for clean merge |
| `git-reset-branches.ps1` | Reset branches to remote state with backup tags (emergency) |
| `git-workflow.ps1` | Orchestrator chaining scripts: `prepare`, `start`, `finish`, `recover`, `status` |

Workflow order:

```text
git-clean-branches  -->  git-check-sync-set-dev  -->  git-init-feature
    (prune stale)         (sync dev, activate)         (create branch)
                                                            |
                                                            v
git-reset-branches  <--  git-rebase-branch  <--  git-create-clean-branch
    (emergency)          (rebase onto base)       (cherry-pick filtered)
```

Quick usage:

```powershell
# Full prepare: clean + sync
.\scripts\powershell\git-workflow.ps1 prepare

# Start feature: sync + create branch
.\scripts\powershell\git-workflow.ps1 start

# Check current state
.\scripts\powershell\git-workflow.ps1 status
```

### AI Context Sync

```powershell
# Sync Qoder skills, agents, and QODER.md to global ~/.qoder/
.\scripts\powershell\chat-Sync-QoderContext.ps1

# Sync Copilot instructions to global ~/.copilot/
.\scripts\powershell\chat-Sync-CopilotContext.ps1
```

## Further Reading

- [Database Setup Guide](docs/database/SETUP_GUIDE.md) - Database-specific configuration
- [Deployment Guide](docs/deployment/DEPLOYMENT_GUIDE.md) - Production deployment
- [Migration Guide](docs/deployment/MIGRATION_CONDA_TO_UV.md) - Conda to UV migration
- [Bootstrap Guide](docs/bootstrap.md) - New project setup from this library
- [Logging Configuration](docs/logging-configuration.md) - Structured logging setup
- [GitHub Workflow Guide](docs/guidelines/GITHUB-WORKFLOW-CONSOLIDATED.md) - Branch and PR conventions
