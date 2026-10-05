---
name: new-db-repository
description: Scaffold a new repository (and, if needed, a new DatabaseStrategy) following this repo's strategy + repository pattern. Use whenever the user asks to add CRUD access to a new table, or add support for a new database type, in this cr-misc-function repo.
---

# New DB Repository / Strategy

This repo has two layers, always used together:

- **Strategy layer** (`app/connections/strategies/`) — one class per database
  *type* (mssql, postgres, mysql, trino, hive, odps). Handles connecting and
  running raw SQL.
- **Repository layer** (`app/repositories/`) — one class per *table*. Builds
  parameterized SQL from class-level constants and inherits generic CRUD from
  `BaseRepository`.

Read `app/repositories/base_repository.py` and `app/repositories/order_repository.py`
(the reference implementation) before writing anything — they show the exact
shape to follow.

## Case A — new table on an already-supported database type

This is the common case. `_STRATEGY_MAP` in `app/connections/strategies/factory.py`
already lists the supported `db_type` values (`postgres`, `hologres`, `mysql`,
`mssql`, `trino`, `hive`, `odps`) — if the target database type is one of
these, only a repository class is needed:

1. Create `app/repositories/<name>_repository.py`:
   ```python
   from app.repositories.base_repository import BaseRepository


   class <Name>Repository(BaseRepository):
       DATABASE_TYPE = "<db_type>"     # one of _STRATEGY_MAP's keys
       SCHEMA = "<schema>"             # MSSQL/PostgreSQL/Hive; use DATABASE for MySQL instead
       TABLE_NAME = "<table>"
       COLUMNS = ["<col1>", "<col2>", ...]  # must match the real table columns exactly

       # Add domain-specific methods here, on top of the inherited
       # select_all/select_one/select_where/insert_one/insert_bulk/
       # update_where/delete_where/count.
   ```
2. Ask the user for the real column list rather than guessing it — `COLUMNS`
   is used to validate every column name passed to any inherited method
   (`_validate_col_names` in `base_repository.py`), so a wrong or incomplete
   list silently blocks valid calls or lets typos through.
3. For MySQL, set `DATABASE = "<db_name>"` instead of `SCHEMA` — `_qualified_table()`
   falls back to `SCHEMA or DATABASE`.
4. Domain methods that need custom SQL should call `self.strategy.execute_query(...)`
   / `self.strategy.execute_non_query(...)` directly, matching
   `OrderRepository.get_pending_orders`'s style: parameterized query, a
   `logger.debug` at entry, and a docstring with an example usage block.
5. Confirm the target `db_type` is already registered in `database_config`
   (or `odps_config`) in `app/configs/config.py` — if not, that's Case B.

## Case B — new database type (no existing strategy)

Only needed when the database type isn't already in `_STRATEGY_MAP`.

1. Add a config entry in `app/configs/config.py`'s `database_config` dict
   (or a new schema in `config_schemas.py` if it needs fields `DBConfig`
   doesn't have).
2. Create `app/connections/strategies/<name>_strategy.py`. If it's a
   standard RDBMS reachable over SQLAlchemy, subclass `RDBMSBaseStrategy`
   (see `postgres_strategy.py` for the minimal shape — just
   `_create_connection()` and `_build_connection_url()`). Otherwise subclass
   `DatabaseStrategy` directly and implement all abstract methods
   (`connect`, `disconnect`, `is_connected`, `execute_query`,
   `execute_non_query`, `create_table`, `get_connection_url`) — `odps_strategy.py`
   is the reference for a non-RDBMS strategy.
3. Register the new class in `_STRATEGY_MAP` in
   `app/connections/strategies/factory.py`, and add a matching `@overload`
   for `create_strategy` so callers get the concrete return type.
4. Then follow Case A to add the repository class(es) on top.

## After scaffolding

- Run `uv run ruff format . && uv run ruff check --fix .` and `uv run mypy .`
  on the new/changed files (the repo's CI runs both on push).
- There is no test suite yet (per `CLAUDE.md`) — don't add one unless asked.
- Never widen `COLUMNS` or skip `_validate_col_names` to "make it work" —
  it's the repo's identifier-injection guard, not incidental validation.
