---
description: Validate and update ruff.toml and mypy.ini based on project environment and content
---

# Validate and Update Lint/Type-Check Configurations

**Purpose**: Ensure ruff.toml and mypy.ini are synchronized with the actual project environment, dependencies, and code structure.

**Critical**: Configuration validity directly impacts code quality checks. Invalid or outdated rules must be removed to prevent check failures.

You are an expert at validating Python linter (ruff) and type-checker (mypy) configurations against project environments and code patterns.

---

## 📋 Usage

```
/validate-lint-config [action]
```

**Parameters:**
- `[action]` - Action to perform (optional, defaults to `validate`)
  - `validate` - Check configs and report issues (no changes)
  - `update` - Check, report, and create updated files with fixes
  - `check-only` - Quick validation of current configs
  - `sync` - Sync known-third-party packages with environment.yml

**Examples:**
- `/validate-lint-config` - Validate current ruff.toml and mypy.ini
- `/validate-lint-config validate` - Full validation report (same as above)
- `/validate-lint-config update` - Validate and create fixed config files
- `/validate-lint-config sync` - Add missing packages to known-third-party from environment.yml
- `/validate-lint-config check-only` - Quick validation without detailed report

---

## 🔍 Validation Checks

### 1. Ruff Configuration Validation

**Check Python Version:**
- Extract target-version from ruff.toml
- Compare against environment.yml Python version
- Warn if mismatch (e.g., ruff targets py310 but env is py311)
- Note: OK to target older version (broader compatibility), warn if newer

**Check Rule Selection:**
- Validate selected rules exist in current ruff version (rules may be renamed/removed)
- Common deprecated/moved ruff rules:
  - `D` → moved to `DOC` (docstring checks)
  - `N` → still valid (naming conventions)
  - `S` → still valid (security)
  - `T` → `T201` (print statements), others in `RUF` or `LOG`
- Warn about any rules that don't exist in current ruff

**Check Ignored Rules:**
- Validate each ignored rule exists (may be deprecated/renamed)
- Warn about ignoring rules that don't exist (user may have removed them from ruff)
- Check for contradictions (selecting parent rule but ignoring child)
- Example: if selecting `E` but ignoring `E501`, that's OK (intentional)
- Example: if selecting `B` but ignoring non-existent `B999`, that's invalid

**Check Per-File Ignores:**
- Verify file patterns exist in project
  - `app/**/etl*.py` - Check if etl files exist in app/
  - `app/**/models/*.py` - Check if models/ directory exists
  - `tests/**/*.py` - Check if tests/ directory exists
- Remove patterns for non-existent directories
- Add patterns for new directories if needed (e.g., `/scripts/`)

**Check Known Third-Party Packages:**
- Extract packages from environment.yml (pip and conda)
- Compare against known-third-party list
- Add missing major packages:
  - Data: pandas, polars, dask, numpy, scipy
  - Databases: sqlalchemy, psycopg2, mysql-connector, pyodbc, pymongo, redis
  - APIs: requests, httpx, aiohttp
  - Async: asyncio, trio, anyio
  - Validation: pydantic, marshmallow
  - Task queues: celery, rq
  - Logging: loguru, structlog
  - Time: pytz, tzlocal
  - Others: pyyaml, python-dotenv, rich, tqdm
- Remove packages from known-third-party that are no longer in environment.yml
- Reorder alphabetically for consistency

**Check Line Length:**
- Verify line-length setting matches project convention (88 is standard for Black/Ruff)
- Warn if set to value likely to cause issues (<79 too strict, >120 too loose)

**Check Format Settings:**
- Validate quote-style (double/single)
- Validate indent-style (space/tab)
- Warn about mixed indentation patterns

### 2. Mypy Configuration Validation

**Check Python Version:**
- Extract python_version from mypy.ini
- Compare against environment.yml Python version
- Ensure format is valid (e.g., 3.11, not 311)

**Check Import Handling:**
- `ignore_missing_imports = true` is common in data engineering
- Warn if false but many untyped packages are installed (like pandas, sqlalchemy)
- Consider more targeted approach if possible

**Check Strictness Settings:**
- `disallow_untyped_defs = false` is pragmatic for data/SQL code
- `check_untyped_defs = false` is OK for iterative typing
- Warn about conflicting settings (e.g., strict_equality=true but disallow_untyped_defs=false)

**Check Exclude Patterns:**
- Verify directories exist:
  - `.venv/`, `.conda/` - Virtual environments (expected)
  - `build/`, `dist/` - Build outputs (expected)
  - Add `.git/`, `__pycache__/` if missing
- Add any new build directories
- Remove patterns for non-existent directories

**Check Plugin Settings:**
- Warn if using plugins not installed in environment.yml
- Note any missing recommended plugins

### 3. Project Content Analysis

**Analyze Project Structure:**
- Detect directories: `app/`, `src/`, `lib/`, `scripts/`, `tests/`
- Check for database model files (SQLAlchemy patterns)
- Check for ETL/data processing scripts
- Identify async code (async def patterns)
- Identify CLI tools (click, argparse)

**Rule Recommendations Based on Structure:**
- If database models detected: Add `F401` to models per-file ignore (SQLAlchemy uses dynamic attributes)
- If async code detected: Keep `E501` ignored (async lines often long)
- If CLI detected: Add `CLT00` rules to selection
- If dataclass/pydantic heavy: Add `A003` to ignore (shadowing builtins is common)
- If scripts/ directory: Add per-file ignore for unused imports

**Test File Detection:**
- Confirm tests/ directory exists
- Ensure S101 (assert allowed) is ignored in tests
- Recommend test markers if pytest.ini exists

---

## 🔧 Update Actions

### When action = `update`:

**Create Fixed Configurations:**

1. **Generate Updated ruff.toml**
   - Fix all invalid rules
   - Sync known-third-party with environment.yml
   - Remove ignore rules for non-existent rules
   - Remove per-file ignores for non-existent directories
   - Add missing recommended rules for project type
   - Write to: `ruff.toml.updated` (don't overwrite)

2. **Generate Updated mypy.ini**
   - Fix Python version format if needed
   - Update exclude patterns for existing directories
   - Write to: `mypy.ini.updated` (don't overwrite)

3. **Report Changes**
   - List all changes made
   - Show before/after for each section
   - Explain reasoning for additions/removals
   - Provide git commands to review and adopt

### File Output Format

Create files in `.github.template/configs/` directory:
- `.github.template/configs/ruff.toml.updated`
- `.github.template/configs/mypy.ini.updated`
- `.github.template/configs/lint-config-report.md` (validation report)

Or provide content in chat for manual review before committing.

---

## 📊 Output Format

### Validation Report (always generated)

```markdown
# Lint Configuration Validation Report

**Date**: YYYY-MM-DD
**Python Version**: 3.11
**Environment**: environment.yml

## 📋 Summary
- ✅ Valid rules: X
- ⚠️ Warnings: Y
- ❌ Invalid: Z
- 📝 Recommendations: N

## Ruff Configuration

### Valid Rules
- E, F, I, B, UP, C90 ✓

### Warnings
- Rule X deprecated in ruff 0.6.0 (renamed to Y)
- Package pandas in environment but not in known-third-party

### Fixes Applied (if action=update)
- Added: psycopg2 to known-third-party
- Updated: per-file ignore pattern for new tests/ structure
- Removed: ignore rule B905 (deprecated)

## Mypy Configuration

### Valid Settings
- Python version: 3.11 ✓
- Import handling: pragmatic ✓

### Warnings
- Exclude pattern .venv/ exists but is typical

### Fixes Applied
- None required

## Recommendations

1. Consider adding S (security) rules to ruff selection
2. Add tests/ per-file ignores for test assertions
3. Sync known-third-party quarterly with environment.yml

---

## Quality Checklist

- [ ] Python version matches environment.yml
- [ ] All selected rules exist in current ruff/mypy versions
- [ ] All ignored rules are intentional (documented)
- [ ] Per-file ignore patterns match actual directories
- [ ] known-third-party includes all major from environment.yml
- [ ] No deprecated rules or settings used
- [ ] Exclude patterns reference existing directories
- [ ] Strictness settings are appropriate for project type
```

---

## Validation Workflow

### Automatic Checks (always run):

1. **ALWAYS** read environment.yml to extract Python version and packages
2. **ALWAYS** read ruff.toml and mypy.ini current state
3. **ALWAYS** validate Python version consistency between files
4. **ALWAYS** check if selected rules exist
5. **ALWAYS** check if ignored rules exist
6. **ALWAYS** scan project structure for directories
7. **ALWAYS** generate validation report

### Update Workflow (when action=update):

1. Perform all automatic checks
2. **Create** fixed configuration files (don't overwrite existing)
3. Show diff between current and updated versions
4. List files ready for review

### Git Integration

After update, user runs:
```bash
# Review changes
diff -u ruff.toml ruff.toml.updated
diff -u mypy.ini mypy.ini.updated

# If satisfied:
mv ruff.toml.updated ruff.toml
mv mypy.ini.updated mypy.ini
git add ruff.toml mypy.ini
git commit -m "chore(lint): sync ruff.toml and mypy.ini with environment"
```

---

## Ruff Rules Reference

**Common Rule Sets:**
- `E`, `W` - PEP 8 errors/warnings
- `F` - Pyflakes (undefined names, unused imports)
- `I` - isort (import sorting)
- `B` - Bugbear (real bugs)
- `UP` - pyupgrade (modern Python)
- `C` - mccabe complexity
- `N` - pep8-naming
- `D` - pydocstyle (docstrings) → moved to DOC
- `S` - flake8-bandit (security)
- `A` - flake8-builtins (shadowing builtins)
- `T` - flake8-print (print statements)
- `RUF` - Ruff-specific rules

**Commonly Ignored Rules:**
- `E501` - Line too long (handled by formatter)
- `B008` - Function call in defaults (SQLAlchemy)
- `D1` - Missing docstrings
- `F401` - Unused imports (common in __init__.py, models)
- `F841` - Unused variables (common in pandas)
- `S101` - Assert allowed (tests)

---

## Mypy Settings Reference

**Key Settings for Data Engineering:**
- `python_version` - Must match project Python
- `ignore_missing_imports` - Pragmatic for untyped packages
- `disallow_untyped_defs` - false for iterative typing
- `check_untyped_defs` - false allows calling untyped code
- `warn_unused_ignores` - true to catch obsolete ignores
- `exclude` - Skip large directories: venv, conda, build

**Strictness Levels:**
- `strict = true` - All checks on (rarely used in data/SQL code)
- Custom selective strictness - Recommended approach

---

## Quality Checklist

Before accepting generated configs:
- [ ] Python version matches environment.yml exactly
- [ ] All selected ruff rules exist in current ruff version
- [ ] All ignored ruff rules are intentional and documented
- [ ] All per-file ignore directories exist in project
- [ ] known-third-party includes all major packages from environment
- [ ] known-third-party is alphabetically sorted
- [ ] No deprecated ruff rules or mypy settings used
- [ ] Mypy exclude patterns reference valid directories
- [ ] Strictness settings appropriate for project type
- [ ] No conflicting rule selections/ignores
- [ ] Validation report explains all changes/recommendations

---

You are now ready to validate and update lint/type-checker configurations. Always prioritize validity over strictness—a valid but pragmatic config beats an invalid strict config that blocks development.
