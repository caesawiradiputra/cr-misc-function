---
name: validate-lint-config
version: "1.0.0"
updated: "2026-06-18"
description: Validate and synchronize ruff.toml and mypy.ini with the actual project environment, Python version, and dependencies. Use when the user triggers /validate-lint-config, asks to check lint config, or wants to sync linting settings with the project.
---

# Validate Lint Config

Validate and synchronize `ruff.toml` and `mypy.ini` with the actual project environment, Python version, and dependencies.

## Usage

```text
/validate-lint-config [action]
```

**Actions:**
- `validate` (default) — Check configs and report issues (no file changes)
- `update` — Check, report, and write fixed config files
- `sync` — Sync `known-third-party` packages with `environment.yml`
- `check-only` — Quick validation without detailed report

## Automatic Checks (Always Run)

### Step 1 — Read Environment

Read `environment.yml` and `pyproject.toml`. Extract Python version and all installed packages.

### Step 2 — Read Current Configs

Read `ruff.toml` and `mypy.ini`.

### Step 3 — Validate ruff.toml

**Python version:**
- Compare `target-version` against environment Python version
- Warn if mismatch

**Rule selection:**
- Validate selected rules exist in current ruff version
- Warn about deprecated/renamed rules

**Ignored rules:**
- Validate each ignored rule exists
- Check for contradictions

**Per-file ignores:**
- Verify glob patterns have matching files in project
- Remove patterns for non-existent directories
- Add patterns for detected directories

**Known third-party packages:**
- Extract packages from `environment.yml`
- Find packages in env but missing from `known-third-party`:
  - Data: `pandas`, `polars`, `dask`, `numpy`, `scipy`
  - Databases: `sqlalchemy`, `psycopg2`, `pyodbc`, `pymongo`, `redis`
  - APIs: `requests`, `httpx`, `aiohttp`
  - Validation: `pydantic`, `marshmallow`
  - Logging: `loguru`, `structlog`
  - Others: `pyyaml`, `python-dotenv`, `rich`, `tqdm`
- Remove packages no longer in env, sort alphabetically

**Line length:**
- 88 is standard (Black/Ruff default)
- Warn if <79 or >120

### Step 4 — Validate mypy.ini

**Python version:** Compare `python_version` against environment. Ensure valid format (`3.11`, not `311`).

**Exclude patterns:** Verify directories exist, add `.git/`/`__pycache__/` if missing, remove non-existent.

**Strictness:** `ignore_missing_imports = true` is pragmatic. Warn about conflicting settings.

### Step 5 — Project Structure Analysis

Scan for: `app/`, `src/`, `scripts/`, `tests/`, database models, ETL scripts, async code, CLI tools.

Rule recommendations based on structure:
- Database models -> Add `F401` to models per-file ignore
- `scripts/` -> Add per-file ignore for unused imports
- Tests -> Ensure `S101` (assert) is ignored

## When Action = `update`

Write fixed configs to `ruff.toml.updated` and `mypy.ini.updated` (never overwrite originals). Show diff:

```powershell
git diff --no-index ruff.toml ruff.toml.updated
git diff --no-index mypy.ini mypy.ini.updated
```

After review:

```powershell
# Step 1 — Back up originals before overwriting
Copy-Item ruff.toml ruff.toml.bak
Copy-Item mypy.ini mypy.ini.bak

# Step 2 — Preview the replacement (dry-run)
Move-Item ruff.toml.updated ruff.toml -Force -WhatIf
Move-Item mypy.ini.updated mypy.ini -Force -WhatIf

# Step 3 — Apply the replacement
Move-Item ruff.toml.updated ruff.toml -Force
Move-Item mypy.ini.updated mypy.ini -Force
```

> **Tip:** Always run with `-WhatIf` first to verify the operation before committing. If something goes wrong, restore from the `.bak` copies.

## Validation Report Format

```markdown
# Lint Configuration Validation Report

**Date**: YYYY-MM-DD
**Python Version**: 3.11
**Environment**: environment.yml

## Summary
- Valid rules: X
- Warnings: Y
- Invalid: Z
- Recommendations: N

## Ruff Configuration
### Valid / ### Warnings / ### Fixes Applied

## Mypy Configuration
### Valid / ### Warnings

## Recommendations
1. ...
```

## Ruff Rules Reference

| Rule Set | Purpose |
| --- | --- |
| `E`, `W` | PEP 8 errors/warnings |
| `F` | Pyflakes |
| `I` | isort |
| `B` | Bugbear |
| `UP` | pyupgrade |
| `C` | mccabe complexity |
| `N` | pep8-naming |
| `S` | flake8-bandit (security) |
| `RUF` | Ruff-specific |

**Commonly ignored:** `E501` (line length, handled by formatter), `B008` (function call in defaults), `F401` (unused imports in `__init__.py`), `S101` (assert in tests).

## Quality Checklist

- [ ] Python version matches environment.yml exactly
- [ ] All selected ruff rules exist in current ruff version
- [ ] All ignored rules are intentional
- [ ] Per-file ignore directories exist in project
- [ ] known-third-party includes all major packages
- [ ] known-third-party is alphabetically sorted
- [ ] No deprecated rules or settings
- [ ] Mypy exclude patterns reference valid directories
- [ ] No conflicting rule selections/ignores
