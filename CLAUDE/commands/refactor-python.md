# Refactor Python Code

Systematically improve Python code quality while **guaranteeing identical behavior**. Supports whole project, folder, single module, or single function scope.

**Guarantee**: Code behaves identically after refactoring — no breaking changes.

## Scope: $ARGUMENTS

If `$ARGUMENTS` is provided, refactor the specified file, folder, or function. Otherwise ask the user to specify scope.

---

## Phase 1: Analysis (Do This First)

Before making any changes:

1. **Check Python version** — determines which type hint syntax to use:

   ```powershell
   # Check pyproject.toml or environment.yml
   Get-Content pyproject.toml | Select-String "python"
   ```

   - Python 3.9 → use `typing.List`, `typing.Dict`, `Optional[X]`
   - Python 3.10+ → use `list`, `dict`, `X | Y` (modern syntax)

2. **Check if helpers exist** before adding new ones:
   - `app/utils/repo_utils.py` — SQL/query utilities
   - `app/utils/data_utils.py` — data I/O and conversion utilities
   - `app/configs/` — configuration patterns

3. **Identify improvement opportunities** using this checklist:
   - [ ] Python version identified?
   - [ ] Missing or incomplete type hints?
   - [ ] Missing/incomplete docstrings?
   - [ ] Changelog comments present (`# FIX:`, `# TODO: fixed`, `# UPDATED:`)?
   - [ ] Bare `except:` or generic `Exception` clauses?
   - [ ] Expensive computations inside loops?
   - [ ] Functions with optional arguments missing debug logging?
   - [ ] PEP 8 violations (imports, spacing, line length)?
   - [ ] Unclear naming?

---

## Phase 2: Refactoring (Priority Order)

Apply improvements in this exact order:

### Priority 0 — Type Hints (Highest)

Add to: all function parameters, return values, class attributes, and non-obvious variables.

**Python 3.10+ (modern):**

```python
def process_items(items: list[dict]) -> list[dict]:
    result: list[dict] = []
    ...
```

**Python 3.9 (legacy):**

```python
from typing import Any, List, Dict, Optional

def process_items(items: List[Dict]) -> List[Dict]:
    result: List[Dict] = []
    ...
```

### Priority 1 — Docstrings (Google Style)

```python
def fetch_orders(days: int = 30, status: str = "pending") -> pd.DataFrame | None:
    """Fetch orders from the past N days with given status.

    Args:
        days: Number of days to look back. Default: 30.
        status: Order status filter. Default: "pending".

    Returns:
        DataFrame with matching orders, or None if no results.

    Raises:
        ValueError: If days is negative.
    """
```

Include: clear summary, Args (with types + descriptions), Returns, Raises (if applicable).

### Priority 2 — Comments

**Remove:**

- Changelog comments: `# FIX:`, `# TODO: fixed`, `# UPDATED:`, `# BUGFIX:`
- Obvious comments: `x = 5  # Set x to 5`
- Comments that duplicate the code

**Keep only WHY comments:**

```python
# ! Critical: Lock prevents race condition on shared state
# * Performance-critical path — do not add logging here
# ? Why use ThreadPoolExecutor instead of asyncio here?
```

Better Comments syntax: `# !` alert, `# *` highlight, `# ?` question, `# //` deprecated.

### Priority 3 — Error Handling

**Replace bare/generic:**

```python
# ❌ Before
try:
    order = db.find(order_id)
except:
    return None

# ✅ After
try:
    order = db.find(order_id)
    return order
except KeyError:
    logger.debug("Order not found: {}", order_id)
    return None
except Exception as e:
    logger.error("Unexpected error retrieving order {}: {}", order_id, e)
    raise
```

### Priority 4 — Performance

Move computations outside loops; cache values that don't change:

```python
# ❌ Before
for item in items:
    config = load_config()  # Called every iteration!
    process(item, config)

# ✅ After
config = load_config()      # Called once
for item in items:
    process(item, config)
```

### Priority 5 — Debug Logging for Optional Arguments

Add at function entry to show which optional args are active:

```python
# Loguru (preferred): use {} placeholders — never f-strings
from loguru import logger

def fetch_orders(days: int = 30, format: str = "csv") -> pd.DataFrame:
    logger.debug("fetch_orders called: days={}, format={}", days, format)
    ...

# Standard logging: use %s — never f-strings
import logging
logger = logging.getLogger(__name__)

def fetch_orders(days: int = 30, format: str = "csv"):
    logger.debug("fetch_orders called: days=%s, format=%s", days, format)
```

### Priority 6 — Naming Conventions

| Element | Convention | Example |
| --- | --- | --- |
| Variables | `snake_case` | `order_count`, `user_email` |
| Functions | `snake_case` | `get_pending_orders()` |
| Classes | `PascalCase` | `OrderRepository` |
| Constants | `UPPER_CASE` | `MAX_RETRIES` |

Only rename if clarity increases.

### Priority 7 — Formatting & PEP 8

Import order:

```python
# Standard library
import os
from pathlib import Path

# Third-party
import pandas as pd
from sqlalchemy import create_engine

# Local
from app.configs import log_config
from app.utils.repo_utils import read_query_file
```

---

## Phase 3: Validation

Run these commands after refactoring:

```powershell
# 1. Syntax check
uv run python -m py_compile <file>

# 2. Lint and format
uv run ruff check <file>
uv run ruff format <file>

# 3. Type check
uv run mypy <file>

# 4. Run tests
uv run pytest -v
```

---

## Logic Preservation Rules (Non-Negotiable)

- Same behavior, same return values, same side effects
- Same function signatures (parameter names, types, defaults)
- Same imports — never remove without verifying unused
- Same exception behavior

---

## Critical Principles

**Never:**

- Change behavior while refactoring
- Remove imports without checking all usages
- Change function signatures
- Use Python 3.10+ syntax on Python 3.9 projects
- Refactor without running tests before AND after

**Always:**

- Run tests before starting
- Verify Python version before choosing type hint syntax
- Use `git add -p` to stage incrementally
- Reuse `app/utils/repo_utils.py` and `app/utils/data_utils.py` helpers

---

## Post-Refactor Checklist

- [ ] Tests pass (behavior identical)
- [ ] Function signatures unchanged
- [ ] Type hints added to all public functions/classes
- [ ] Module docstring present
- [ ] All public functions/classes documented
- [ ] No changelog comments remain
- [ ] Error handling explicit with specific exception types
- [ ] Imports organized (stdlib → third-party → local)
- [ ] No imports removed that are still used
- [ ] Performance optimizations applied safely
- [ ] Repository-specific rules followed (if in `repositories/`) → see `/refactor-repositories`
