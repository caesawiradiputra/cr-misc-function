# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Location

The workspace root (`cr-misc-function\`) is **not** the git repo — the repo lives in the child folder of the same name (`cr-misc-function\cr-misc-function\`). Run all git commands from the child folder.

## Commands

```powershell
uv sync                   # Install / sync all dependencies
uv run ruff check .       # Lint
uv run ruff format .      # Format
uv run mypy .             # Type check
uv run python -m app.main # Run entry point
```

No test suite exists yet. CI runs ruff + mypy on pushes to `master`, `dev`, and `sit`.

## Architecture

This is a **Python 3.11 data-engineering utility library** used in Kubernetes-based data pipelines at BFI. It connects to multiple databases and Alibaba Cloud services.

### Connection Layer (`app/connections/`)

Two parallel implementations exist — use the **strategy-based** one (not the monolithic `connection.py`):

- `app/connections/strategies/base.py` — `DatabaseStrategy` (ABC) + `RDBMSBaseStrategy` (shared RDBMS logic)
- `app/connections/strategies/factory.py` — `create_strategy(db_type)` factory with typed overloads
- One concrete strategy per database: `MSSQLStrategy`, `PostgreSQLStrategy`, `MySQLStrategy`, `TrinoStrategy`, `HiveStrategy`, `ODPSStrategy`
- All strategies are context managers (`with create_strategy("mssql") as s:`)
- `app/connections/oss.py` — `OSSConnector` for Alibaba Cloud OSS file operations (upload/download/refresh)

`connection.py` is the older monolithic `DBConnector` class — kept for reference but the strategies are the active implementation.

### Repository Layer (`app/repositories/`)

- `BaseRepository` builds parameterized SQL from class-level constants (`DATABASE_TYPE`, `SCHEMA`/`DATABASE`, `TABLE_NAME`, `COLUMNS`)
- Inherits generic CRUD: `select_all`, `select_one`, `select_where`, `insert_one`, `insert_bulk`, `update_where`, `delete_where`, `count`
- Column names are validated against `COLUMNS` to prevent identifier injection
- Subclasses declare constants + add domain methods. See `OrderRepository` as the reference implementation.

### Configuration (`app/configs/`)

- `config_schemas.py` — Pydantic v2 models: `DatabaseConfig`, `LoggingConfig`, `AppConfig`, `ODPSConfig`, `OSSConfig`, `KafkaConfig`, `ElasticsearchConfig`
- `config.py` — loads `.env` (or `/vault/secrets/.env` in Kubernetes), instantiates all schemas, exposes module-level variables. Import from here: `from app.configs.config import DATABASE_MSSQL, ODPS, LOGGING_CONFIG`
- `log_config.py` — loguru-based logger with JSON/text console format and optional file rotation. Call `init_logging()` at entry points.
- `database_config` dict in `config.py` drives which databases `create_strategy()` can resolve.

### PVC Data Manager (`app/utils/pvc_data_manager.py`)

Used for sharing DataFrames between Airflow/Kubernetes DAG tasks without repeated OSS round-trips:

- In Kubernetes: uses `/shared-data` PVC mount
- Locally: uses `./shared-data/`
- `is_output_fresh()` checks file age against `TASK_OUTPUT_CACHE_HOURS` — set `ENABLE_TASK_OUTPUT_CACHE=false` to disable

### Services (`services/`)

Standalone utility functions (e.g., `data_cleaner.py`) — not tied to the app package, usable independently.

### Dev Scripts (`scripts/powershell/`, `scripts/bash/`)

Git workflow, template-sync, and environment-management scripts ship in two
parallel forms: `scripts/powershell/*.ps1` for native Windows sessions, and
`scripts/bash/*.sh` for sessions where Claude Code or the IDE actually runs
inside WSL2/Linux instead. Same script names, same flags, same behavior —
pick whichever matches the shell actually running the session (see the
global `~/.claude/CLAUDE.md` "Environment" section). See
`scripts/powershell/README.md` / `scripts/bash/README.md` for the full
script overview and risk levels.

## Key Conventions

- **Placeholder**: MSSQL/MySQL/Hive use `?`; PostgreSQL/Trino use `%s` — `BaseRepository._placeholder()` handles this automatically
- **Config validation** is deferred to connection time, not import time — missing env vars don't fail at startup
- `odps_config` in `config.py` is a plain dict (not `DatabaseConfig`), mapped separately from `database_config`
- `hologres` maps to `PostgreSQLStrategy` (shares PostgreSQL wire protocol)
- Log format defaults to `json` for production (Grafana); set `LOG_FORMAT=text` for local development
- Python 3.11 union syntax (`X | Y`, `list[str]`) throughout — do not use `Optional` or `Union`

## Committing Claude Code Setup

When adding or updating the AI assistant config in this repo, use branch
`chore/claude-code-setup` and the commit message below.

```text
🔧 chore(claude): add AI assistant config (Claude Code, Copilot)

- Add .claude/settings.json (permissions + hooks) and CLAUDE.md project guidance
- Add CLAUDE/ template (CLAUDE.md + slash commands)
- Add .copilot/ (skills, instructions, prompts) and .github/copilot-instructions.md
- Ignore .claude/settings.local.json (machine-specific permission overrides)
```

### What this setup provides

- **`.claude/settings.json`** — shared Claude Code config:
  - `permissions.deny` blocks reading/editing `.env`, `.env.dev`, `.env.prod`,
    `token.json`, and editing/writing anything under `legacy/**` (rollback/
    reference snapshots — see AGENTS.md)
  - `hooks.PostToolUse` runs `ruff format` + `ruff check --fix` automatically
    whenever Claude edits or writes a `.py` file
- **`.claude/settings.local.json`** — this machine's permission allow-list
  (absolute paths); gitignored, never committed
- **`CLAUDE/`** — canonical source for this project's `CLAUDE.md` and custom
  slash commands (`CLAUDE/commands/`); synced to the user's global
  `~/.claude/commands` via `scripts/powershell/chat-Sync-ClaudeContext.ps1`
- **`.copilot/`** — GitHub Copilot skills, instructions, and prompts; synced
  to `~/.copilot/` via `chat-Sync-CopilotContext.ps1`
- **`.github/copilot-instructions.md`** / **`.github/domain-copilot-instructions.md`**
  — repo-wide and domain-specific Copilot instructions

This repo doubles as a **template/config source**: `.claude/`, `CLAUDE/`,
`.copilot/`, and `.github/` here are designed to be copy-pasted into other
projects as a starting point.
