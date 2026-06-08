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

Action: **$ARGUMENTS**

---

## Automatic Checks (Always Run)

### Step 1 — Read Environment

```powershell
# Read environment file
Get-Content environment.yml
Get-Content pyproject.toml
```

Extract:

- Python version (e.g., `3.11`)
- All installed packages (pip + conda sections)

### Step 2 — Read Current Configs

```powershell
Get-Content ruff.toml
Get-Content mypy.ini
```

### Step 3 — Validate ruff.toml

**Python version:**

- Extract `target-version` from ruff.toml
- Compare against environment.yml Python version
- Warn if mismatch (targeting newer version than env is a problem)

**Rule selection:**

- Validate selected rules exist in current ruff version
- Common deprecated/renamed rules: `D` → `DOC`, `T` → check sub-rules
- Warn about non-existent rules

**Ignored rules:**

- Validate each ignored rule exists (may be deprecated)
- Check for contradictions (selecting parent but ignoring invalid child)

**Per-file ignores:**

- Verify each glob pattern has matching files in project:

  ```powershell
  Get-ChildItem -Path "app" -Recurse -Filter "*.py" | Select-String "etl" -List
  ```

- Remove patterns for non-existent directories
- Add patterns for detected directories (e.g., `scripts/`)

**Known third-party packages:**

- Extract all packages from `environment.yml`
- Find packages in env but missing from `known-third-party`:
  - Data: `pandas`, `polars`, `dask`, `numpy`, `scipy`
  - Databases: `sqlalchemy`, `psycopg2`, `pyodbc`, `pymongo`, `redis`
  - APIs: `requests`, `httpx`, `aiohttp`
  - Validation: `pydantic`, `marshmallow`
  - Logging: `loguru`, `structlog`
  - Others: `pyyaml`, `python-dotenv`, `rich`, `tqdm`
- Remove packages no longer in `environment.yml`
- Sort alphabetically

**Line length:**

- 88 is standard (Black/Ruff default)
- Warn if <79 (too strict) or >120 (too loose)

### Step 4 — Validate mypy.ini

**Python version:**

- Extract `python_version` from mypy.ini
- Compare against environment.yml
- Ensure format is valid (e.g., `3.11`, not `311`)

**Exclude patterns:**

- Verify directories exist: `.venv/`, `build/`, `dist/`
- Add `.git/`, `__pycache__/` if missing
- Remove patterns for non-existent directories

**Strictness:**

- `ignore_missing_imports = true` is pragmatic for data engineering
- Warn about conflicting settings (e.g., `strict = true` but `disallow_untyped_defs = false`)

### Step 5 — Project Structure Analysis

Scan for:

- Directories: `app/`, `src/`, `scripts/`, `tests/`
- Database model files (SQLAlchemy patterns)
- ETL/data processing scripts
- Async code (`async def`)
- CLI tools (click, argparse)

Rule recommendations based on structure:

- Database models detected → Add `F401` to models per-file ignore
- `scripts/` directory → Add per-file ignore for unused imports
- Tests directory → Ensure `S101` (assert) is ignored in tests

---

## When Action = `update`

Write fixed configs to these paths (never overwrite originals):

- `ruff.toml.updated`
- `mypy.ini.updated`

Then show diff:

```powershell
# Review with diff (requires diff tool, or use git diff)
git diff --no-index ruff.toml ruff.toml.updated
git diff --no-index mypy.ini mypy.ini.updated
```

After review, to adopt:

```powershell
Move-Item ruff.toml.updated ruff.toml -Force
Move-Item mypy.ini.updated mypy.ini -Force
git add ruff.toml mypy.ini
git commit -m "🔧 ci(lint): sync ruff.toml and mypy.ini with environment"
```

---

## Validation Report Format

```markdown
# Lint Configuration Validation Report

**Date**: YYYY-MM-DD
**Python Version**: 3.11
**Environment**: environment.yml

## Summary
- ✅ Valid rules: X
- ⚠️ Warnings: Y
- ❌ Invalid: Z
- 📝 Recommendations: N

## Ruff Configuration

### Valid
- E, F, I, B, UP, C90 ✓
- known-third-party: 12 packages ✓

### Warnings
- Rule X deprecated (renamed to Y)
- Package 'pandas' in environment but not in known-third-party

### Fixes Applied (if action=update)
- Added: psycopg2, loguru to known-third-party
- Removed: per-file ignore for non-existent scripts/ directory

## Mypy Configuration

### Valid
- python_version = 3.11 ✓
- ignore_missing_imports = true ✓

### Warnings
- Exclude pattern 'build/' doesn't exist yet (OK for future)

## Recommendations

1. Consider adding S (security) rules to ruff selection
2. Add tests/ per-file ignores for S101 (assert statements)
3. Sync known-third-party quarterly with environment.yml
```

---

## Ruff Rules Reference

| Rule Set | Purpose |
| --- | --- |
| `E`, `W` | PEP 8 errors/warnings |
| `F` | Pyflakes (undefined names, unused imports) |
| `I` | isort (import sorting) |
| `B` | Bugbear (common bugs) |
| `UP` | pyupgrade (modern Python) |
| `C` | mccabe complexity |
| `N` | pep8-naming |
| `S` | flake8-bandit (security) |
| `RUF` | Ruff-specific rules |

**Commonly ignored:**

- `E501` — Line too long (handled by formatter)
- `B008` — Function call in defaults (SQLAlchemy)
- `F401` — Unused imports (common in `__init__.py`, models)
- `S101` — Assert allowed (tests)

---

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
