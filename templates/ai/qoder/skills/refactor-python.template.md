---
name: refactor-python
description: Refactor Python code while guaranteeing identical behavior
---

# Refactor Python Code

Systematically improve Python code quality while **guaranteeing identical behavior**. Supports whole project, folder, single module, or single function scope.

## When to Use

- Python code needs quality improvements without behavior changes
- Type hints are missing or outdated
- Docstrings need to be added or updated
- Error handling needs to be made more specific

## Workflow

### Phase 1: Analysis

1. **Check Python version** — determines type hint syntax:
   - Python 3.9 → `typing.List`, `typing.Dict`, `Optional[X]`
   - Python 3.10+ → `list`, `dict`, `X | Y` (modern syntax)

2. **Check if helpers exist** before adding new ones — look in `{{UTILS_DIR}}/` and `{{CONFIGS_DIR}}/`

3. **Identify improvement opportunities**:
   - [ ] Python version identified?
   - [ ] Missing or incomplete type hints?
   - [ ] Missing/incomplete docstrings?
   - [ ] Changelog comments present (`# FIX:`, `# TODO: fixed`, `# UPDATED:`)?
   - [ ] Bare `except:` or generic `Exception` clauses?
   - [ ] Expensive computations inside loops?
   - [ ] Functions with optional arguments missing debug logging?
   - [ ] PEP 8 violations?

### Phase 2: Refactoring (Priority Order)

#### Priority 0 — Type Hints

Add to all function parameters, return values, class attributes.

**Python 3.10+**:

```python
def process_items(items: list[dict]) -> list[dict]:
    result: list[dict] = []
```

**Python 3.9**:

```python
from typing import List, Dict

def process_items(items: List[Dict]) -> List[Dict]:
    result: List[Dict] = []
```

#### Priority 1 — Docstrings (Google Style)

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

#### Priority 2 — Comments

**Remove**: Changelog comments, obvious comments, comments that duplicate code.
**Keep**: WHY comments only — `# !` alert, `# *` highlight, `# ?` question, `# //` deprecated.

#### Priority 3 — Error Handling

Replace bare/generic except with specific exception types. Add contextual logging.

#### Priority 4 — Performance

Move computations outside loops; cache values that don't change.

#### Priority 5 — Debug Logging

For functions with optional arguments, add entry-point logging with loguru (`{}` placeholders) or standard logging (`%s` format).

#### Priority 6 — Naming Conventions

| Element | Convention | Example |
| --- | --- | --- |
| Variables | `snake_case` | `order_count` |
| Functions | `snake_case` | `get_pending_orders()` |
| Classes | `PascalCase` | `OrderRepository` |
| Constants | `UPPER_CASE` | `MAX_RETRIES` |

#### Priority 7 — Formatting & PEP 8

Import order: stdlib → third-party → local, separated by blank lines.

### Phase 3: Validation

```powershell
uv run python -m py_compile <file>
uv run ruff check <file>
uv run ruff format <file>
uv run mypy <file>
uv run pytest -v
```

## Logic Preservation Rules

- Same behavior, return values, side effects
- Same function signatures
- Same imports — never remove without verifying unused
- Same exception behavior

## Validation

- [ ] Tests pass (behavior identical)
- [ ] Function signatures unchanged
- [ ] Type hints added to all public functions/classes
- [ ] Module docstring present
- [ ] No changelog comments remain
- [ ] Error handling explicit with specific exception types
- [ ] Imports organized (stdlib → third-party → local)
