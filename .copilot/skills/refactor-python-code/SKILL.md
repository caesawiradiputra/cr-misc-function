---
name: refactor-python-code
description: "Refactor and polish Python code while preserving behavior, improving readability, documentation, and adherence to project standards. Supports whole project, folder, or single file refactoring."
---

# Refactor Python Code

Systematically improve Python code quality while guaranteeing identical behavior, preserving function signatures, and maintaining project architecture.

**Scope:** Refactor a whole project, a folder, a single module, or a function.
**Guarantee:** Code behaves identically; no breaking changes.

## Quick Navigation

**New to refactoring?** → Start with [When to Use This Skill](#when-to-use-this-skill)

**Ready to refactor?** → Jump to [Refactoring Workflow](#refactoring-workflow)

**Need specific rules?** → See [Repository-Specific Rules](#repository-specific-refactoring-rules)

**Stuck or have questions?** → Check [Troubleshooting & Best Practices](#troubleshooting-and-critical-principles)

**Want examples?** → Browse [Real-World Examples](#real-world-examples)

---

## When to Use This Skill

**✅ USE THIS SKILL FOR:**
- Improving code readability and maintainability
- Adding/improving docstrings and comments
- Optimizing performance (loops, caching, processing order)
- Ensuring PEP 8 compliance and consistent naming
- Refactoring repository classes with mandatory structure
- Adding debug logging for debuggability
- Improving code clarity without changing behavior

**❌ DO NOT USE IF:**
- Code is working perfectly and requires no changes
- Refactoring would change behavior or logic
- There's an urgent production issue (fix bug first)
- Tests don't exist yet (add tests first, then refactor)
- You need to add new features (separate task from refactoring)
- You're not sure if behavior will change (verify with tests first)

**Prerequisites:**
- Original code is syntactically valid
- Tests exist (or you can manually verify behavior)
- Git repository initialized (to save work safely)
- Understanding of project architecture and standards
- **Python version identified** (3.9, 3.10, 3.11+) — Determines which syntax to use

---

## Core Principles

### Logic Preservation (Non-Negotiable)

* ✅ **Same behavior** — Algorithm, logic, and flow unchanged
* ✅ **Same return values** — Outputs identical to original
* ✅ **Same side effects** — State modifications unchanged
* ✅ **Same signatures** — Parameter names, types, and defaults unchanged
* ✅ **Same observable effects** — No user-facing changes
* ✅ **Same imports** — Don't remove used imports
* ✅ **Same exceptions** — Error handling paths unchanged

### Project Structure Awareness

Before adding new helpers, verify they don't already exist:

1. **Check `app/utils/`** — Shared utility functions (repo_utils.py, data_utils.py)
2. **Check `app/configs/`** — Configuration patterns and constants
3. **Reuse existing helpers** — Don't duplicate logic
4. **Respect architecture** — Maintain folder organization

### Scope Flexibility

This skill applies to any scope:

| Scope | Example | Approach |
| ------ | --------- | --------- |
| **Whole Project** | `app/` folder | Refactor all files; respect module boundaries |
| **Single Folder** | `repositories/` | Apply folder-specific rules (mandatory structure) |
| **Single Module** | `app/connections/connection_strategy.py` | Refactor this file only |
| **Single Function** | `get_user_orders()` in `repositories/` | Refactor function + class context |

---

## Refactoring Workflow

### Phase 1: Analysis

Before making any changes, identify improvement opportunities:

| Check | Why | What to Look For |
| ------ | --------- | --------- |
| **Docstrings** | Critical for maintainability | Missing or incomplete module/class/function docs |
| **Type Hints** | Clarity and IDE support | Missing or incomplete type annotations |
| **Comments** | Should explain *why*, not *what* | Changelog comments (`# FIX:`, `# TODO: fixed`) |
| **Naming** | Clarity at a glance | Unclear variable/function names |
| **Error Handling** | Robustness and clarity | Bare except clauses, missing validation |
| **Python Version** | Compatibility | Syntax incompatible with target Python version |
| **PEP 8** | Consistency and readability | Import ordering, line length, spacing |
| **Performance** | Avoid slow patterns | Loops with repeated computations, inefficient order |
| **Debug Logging** | Debuggability | Optional arguments with no visibility |
| **Context Managers** | Resource management | Missing `__enter__`/`__exit__` where applicable |

**Analysis Checklist:**

- [ ] **Project Python version verified?** (3.9, 3.10, or 3.11+) — Check `pyproject.toml` or `environment.yml`
- [ ] Module docstring present and clear?
- [ ] Public functions/classes documented with Args, Returns, Raises?
- [ ] Type hints present for function signatures (compatible with Python version)?
- [ ] Error handling explicit (no bare except clauses)?
- [ ] Comments explain *why*, not *what*? (Consider Better Comments extension)
- [ ] No redundant changelog comments?
- [ ] Variable/function names clear and consistent?
- [ ] PEP 8 compliant (imports, spacing, line length < 88)?
- [ ] Opportunities for performance optimization?
- [ ] Functions with optional arguments missing debug logging?
- [ ] Resource-managing classes have context manager pattern?
- [ ] Exception types are specific, not generic?

### Phase 2: Refactoring

Apply improvements in this priority order:

#### 0. Type Hints (Highest Priority - Precedes Docstrings)

**Why:** Type hints enable IDE support, catch bugs early, and are required for modern Python.

**FIRST: Determine project Python version** (affects which syntax to use):

- **Python 3.9**: Use `typing.List`, `typing.Dict`, `typing.Optional[T]` (pre-3.10 syntax)
- **Python 3.10+**: Use `list`, `dict`, `X | Y` (modern syntax) — PREFERRED
- **Python 3.11+**: Use `list[dict]`, modern union syntax, built-in generics
- Check `pyproject.toml` or `environment.yml` for `python = "3.9"` vs `python = "3.10+"`

**Add type hints to:**
- Function parameters (all, not just some)
- Function return values
- Class attributes (in `__init__`)
- Function variables (when non-obvious)

**Python 3.10+ Example (Modern Syntax - PREFERRED):**
```python
from typing import Any
import pandas as pd

def process_items(items: list[dict]) -> list[dict]:
    """Process items and return transformed results.

    Args:
        items: List of dictionaries to process.

    Returns:
        List of processed dictionaries.
    """
    result: list[dict] = []
    for item in items:
        processed: dict[str, Any] = transform(item)
        result.append(processed)
    return result
```

**Python 3.9 Example (Legacy Syntax - For Older Projects):**
```python
from typing import Any, List, Dict, Optional
import pandas as pd

def process_items(items: List[Dict]) -> List[Dict]:
    """Process items and return transformed results.

    Args:
        items: List of dictionaries to process.

    Returns:
        List of processed dictionaries.
    """
    result: List[Dict] = []
    for item in items:
        processed: Dict[str, Any] = transform(item)
        result.append(processed)
    return result
```

**Constraints:**
- **Python 3.10+**: Use modern syntax (`X | Y`, `list[dict]`), not `Optional[X]` or `List[Dict]`
- **Python 3.9**: Use `typing.List`, `typing.Dict`, `typing.Optional[X]` (modern syntax causes SyntaxError)
- Type hints should be concise and accurate
- Use `Any` sparingly (only when truly unknown)
- Avoid overly complex type hints (readability > perfection)
- **Check project's Python constraint before refactoring**

```python
def process_data(data: list[dict], timeout: int = 30) -> pd.DataFrame:
    """Process raw data and return aggregated results.

    Validates input data, applies transformations, and aggregates
    results by category with configurable timeout.

    Args:
        data: List of dictionaries containing raw event data.
        timeout: Processing timeout in seconds. Default: 30.

    Returns:
        Aggregated data as pandas DataFrame with columns:
        - category: Grouping category
        - count: Number of items in category
        - total: Sum of values per category

    Raises:
        ValueError: If data is empty or malformed.
        TimeoutError: If processing exceeds timeout.
    """
```

**Include:**
- Clear purpose/summary
- Args with types and descriptions
- Returns with type and details
- Raises if exceptions are thrown
- Side effects if relevant

#### 2. Comments (Third Priority)

**Remove:**
- Changelog comments: `# FIX:`, `# TODO: fixed`, `# UPDATED:`, `# BUGFIX:`
- Obvious comments: `x = 5  # Set x to 5`
- Duplicative comments: Comments that repeat the code

**Keep only:**
- *Why* the code exists: `# Lock prevents race condition on shared state`
- Non-obvious logic: Complex algorithms, workarounds
- Design decisions: `# Using Redis instead of in-memory cache for cluster support`

**Use Better Comments Extension** (Optional but Recommended):

Install VS Code extension: [Better Comments](https://marketplace.visualstudio.com/items?itemName=aaron-bond.better-comments)

**Better Comments Syntax:**
- `!` → **Alert/Important** (red): `# ! Critical: Must handle null pointer`
- `?` → **Question/Clarification** (blue): `# ? Why use Redis instead of Memcached?`
- `*` → **Highlight/Emphasis** (green): `# * Performance-critical path`
- `//` → **Strikethrough/Deprecated** (gray): `# // Old implementation, kept for reference`
- `TODO:` → **Todo item** (orange): `# TODO: Refactor this function`

**Examples with Better Comments:**
```python
# ! Critical: Order matters for transaction rollback
for item in items:
    process(item)
    save_to_database(item)

# ? Why use ThreadPoolExecutor instead of asyncio?
# * Performance: Empirically faster for I/O-bound tasks on this dataset
executor = ThreadPoolExecutor(max_workers=5)

# // Old implementation kept for backward compatibility
# def legacy_get_user():
#     return None
```

**Before (without Better Comments):**
```python
# FIX: Added check for None on 2024-02-15
if item is not None:  # Item must not be None
    process(item)  # Process the item
```

**After (with Better Comments):**
```python
# ! Prevents None reference exception in process()
if item is not None:
    process(item)
```

#### 3. Error Handling (Fourth Priority)

**Improve explicit error handling:**

**Remove:**
- Bare `except:` clauses (catch-all, hides bugs)
- Generic `Exception` without reason (be specific)
- Silent failures without logging

**Add:**
- Specific exception types (`ValueError`, `TimeoutError`, `KeyError`)
- Error logging with context
- Validation at function entry
- Type guards to prevent errors

**Before:**
```python
def get_order(order_id):
    try:
        order = database.find(order_id)
        return order
    except:
        return None
```

**After:**
```python
def get_order(order_id: int) -> dict[str, Any] | None:
    """Retrieve order by ID.

    Args:
        order_id: Order identifier.

    Returns:
        Order dictionary or None if not found.

    Raises:
        ValueError: If order_id is invalid.
    """
    if not isinstance(order_id, int) or order_id <= 0:
        raise ValueError(f"order_id must be positive integer, got {order_id}")

    try:
        order = database.find(order_id)
        return order
    except KeyError:
        logger.debug(f"Order not found: {order_id}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error retrieving order {order_id}: {e}", exc_info=True)
        raise
```

#### 4. Performance Optimization (Fifth Priority)

**Move Computations Outside Loops:**

```python
# BAD: Expensive operation repeated every iteration
for item in items:
    result = expensive_function()
    process(item, result)

# GOOD: Compute once, reuse in loop
result = expensive_function()
for item in items:
    process(item, result)
```

**Cache Values That Don't Change:**

```python
# BAD: len() called repeatedly
for i in range(len(large_list)):
    print(large_list[i])

# GOOD: Cache the length
list_length = len(large_list)
for i in range(list_length):
    print(large_list[i])
```

**Optimize Processing Order:**

```python
# BAD: Validates all items, then filters
results = [process(validate(item)) for item in items]

# GOOD: Filter first to reduce validation overhead
valid_items = [item for item in items if is_valid(item)]
results = [process(item) for item in valid_items]
```

#### 5. Debug Logging for Optional Arguments (Sixth Priority)

**Add at function entry to show which arguments are used:**

```python
import logging

logger = logging.getLogger(__name__)

def fetch_orders(days: int = 30, format: str = "csv") -> pd.DataFrame:
    """Fetch orders from the past N days.

    Args:
        days: Number of days to fetch. Default: 30.
        format: Output format (csv, json, parquet). Default: csv.

    Returns:
        Orders DataFrame.
    """
    logger.debug(f"fetch_orders called: days={days}, format={format}")
    # ... implementation
```

**Constraints:**
- Log only optional arguments (not every variable)
- Use `DEBUG` level only (production logs stay clean)
- Respect patterns from `app.configs.log_config`

#### 6. Naming Conventions (Seventh Priority)

**Only improve if clarity increases.**

| Element | Convention | Example |
| ------- | ---------- | ------- |
| Variables | `snake_case` | `order_count`, `user_email` |
| Functions | `snake_case` | `get_pending_orders()`, `calculate_total()` |
| Classes | `PascalCase` | `OrderRepository`, `DBConnectorStrategy` |
| Constants | `UPPER_CASE` | `MAX_RETRIES`, `DEFAULT_TIMEOUT` |

#### 7. Formatting & PEP 8 (Eighth Priority)

**Import Organization:**

```python
# Standard library
import os
import sys
from pathlib import Path

# Third-party
import pandas as pd
from sqlalchemy import create_engine

# Local modules
from app.configs import log_config
from app.utils.repo_utils import read_query_file
```

**File Structure:**

1. Module docstring + license
2. Imports
3. Constants
4. Classes
5. Functions

---

### Phase 3: Validation

Verify the refactoring was successful:

**Behavioral Verification:**

- [ ] Run tests to confirm output unchanged (`pytest -v`)
- [ ] Manual testing for critical functions
- [ ] Check return types match original
- [ ] Verify exception behavior unchanged
- [ ] Check side effects still occur (file writes, API calls, etc.)

**Code Quality Verification:**

- [ ] No imports removed unless confirmed unused (grep/import checker)
- [ ] Function signatures identical
- [ ] No breaking API changes
- [ ] Docstrings grammatically correct
- [ ] Type hints accurate and consistent
- [ ] Error handling explicit and specific

**Project Standards Verification:**

- [ ] PEP 8 compliant (`ruff check`, `black --check`)
- [ ] Imports organized correctly (stdlib → third-party → local)
- [ ] Naming consistent with project convention
- [ ] Performance improvements applied safely
- [ ] No unnecessary complexity added
- [ ] No imports removed that are used elsewhere

---

## Repository-Specific Refactoring Rules

### `repositories/` Folder: Mandatory Structure

Every repository class MUST have this structure (in order):

**1. Class Constants (Required):**

```python
class OrderRepository:
    DATABASE_TYPE = "mssql"  # or "postgres", "mysql", "hive"
    SCHEMA = "dbo"           # For MSSQL/PostgreSQL/Hive
    # DATABASE = "db_name"   # For MySQL (use DATABASE instead of SCHEMA)
    TABLE_NAME = "orders"
    COLUMNS = ["id", "customer_id", "total", "status", "created_at"]
```

**Rules:**
- `DATABASE_TYPE` MUST specify the database (lowercase: "mssql", "postgres", "mysql", "hive", "trino", "odps")
- Use `SCHEMA` for MSSQL/PostgreSQL/Hive; use `DATABASE` for MySQL
- `TABLE_NAME` MUST match the actual database table name
- `COLUMNS` MUST list all managed columns
- Constants defined BEFORE `__init__`

**2. Context Manager Pattern:**

```python
def __init__(self):
    self.strategy = create_strategy(self.DATABASE_TYPE)
    self.strategy.connect()

def __enter__(self):
    return self

def __exit__(self, exc_type, exc_val, exc_tb):
    if exc_type:
        logger.error(f"Operation failed: {exc_val}", exc_info=True)
    self.strategy.disconnect()
```

**3. Public Methods (Domain-Specific Names):**

```python
def get_pending_orders(self, days: int = 30) -> pd.DataFrame | None:
    """Get pending orders from the past N days."""
    # ✅ Good: Domain-specific name

def insert_bulk_orders(self, orders: list[dict]) -> int:
    """Insert multiple orders and return count inserted."""
    # ✅ Good: Clear domain action
```

**Avoid Generic Names:**

- ❌ `execute_query()` → Use domain-specific names instead
- ❌ `get_all()` → Use `get_all_orders()`
- ❌ `find()` → Use `find_by_customer()`

### Query and Data Utilities

**Built-in utilities in `app/utils/`:**

**`repo_utils.py` (7 functions):**
- `read_query_file(path)` — Load SQL with validation
- `generate_placeholders(count, db_type)` — Generate `?` or `%s`
- `build_insert_query()` — Generate INSERT statements
- `build_update_query()` — Generate UPDATE statements
- `validate_columns()` — Validate column names
- `build_select_columns()` — Build column list
- `merge_query_params()` — Flatten parameter tuples

**`data_utils.py` (11 functions):**
- `export_to_csv()`, `import_from_csv()`
- `export_to_parquet()`, `import_from_parquet()`
- `export_to_json()`, `import_from_json()`
- `convert_csv_to_parquet()`, `convert_parquet_to_csv()`
- `convert_csv_to_json()`, `convert_json_to_parquet()`, `convert_json_to_csv()`

**Reuse these utilities instead of duplicating logic.**

### Return Type Consistency

- **Query methods** → `pd.DataFrame | None`
- **Insert/Update/Delete** → `int` (rows affected)
- **Single record lookups** → `dict[str, Any] | None`

---

## Quality Checklist

### Pre-Refactor

- [ ] Code is syntactically valid
- [ ] Original behavior understood or testable
- [ ] Scope clearly identified (whole project/folder/file)
- [ ] Project Python version identified (3.9, 3.10, 3.11+)
- [ ] Better Comments extension installed (optional but recommended)

### Post-Refactor

- [ ] Behavior identical to original (tested)
- [ ] Function signatures unchanged
- [ ] Type hints added to all public functions/classes
- [ ] Module docstring present and clear
- [ ] All public functions/classes documented
- [ ] Comments explain *why*, not *what*
- [ ] No changelog comments remain
- [ ] Error handling explicit with specific exception types
- [ ] Code is PEP 8 compliant
- [ ] Naming is clear and consistent
- [ ] Imports organized correctly (stdlib → third-party → local)
- [ ] No imports removed unless unused
- [ ] Performance optimizations applied (if opportunities found)
- [ ] Debug logging added for optional arguments (if applicable)
- [ ] Repository-specific rules followed (if in `repositories/`)
- [ ] No breaking changes to public APIs
- [ ] All imports are actually used in the file
- [ ] Comments use Better Comments extension syntax (optional but recommended)

---

## Validation Commands

```bash
# Check project Python version FIRST (determines type hint syntax)
python --version  # Or check pyproject.toml, environment.yml

# Syntax check
python -m py_compile <file>

# Lint and style check
ruff check <file>
ruff format <file>  # Auto-format if necessary

# Type checking (validates type hints for your Python version)
mypy <file>

# Run tests
pytest -v

# Full validation suite (check version first, then validate)
python --version && python -m py_compile <file> && ruff check <file> && mypy <file> && pytest -v
```

**Python Version Check Tip:**
Always verify the project's Python version BEFORE refactoring:
```bash
# Check pyproject.toml
cat pyproject.toml | grep "python ="

# Or check environment.yml
cat environment.yml | grep "python"

# Or check the running Python version
python --version
```

**Why it matters:**
- **Python 3.9**: Use `typing.List`, `typing.Dict`, `typing.Optional[X]`
- **Python 3.10+**: Use `list`, `dict`, `X | Y` (modern syntax)

---

## Decision Tree: When to Apply Each Improvement

```
**Python version identified?**
├─ Check pyproject.toml or environment.yml
├─ If 3.9: Use typing.List, typing.Dict, Optional[X]
└─ If 3.10+: Use list, dict, X | Y (modern syntax)

Is this a repository file?
├─ YES → Apply Repository Mandatory Structure rules first
└─ NO → Continue below

Missing or incomplete type hints?
├─ YES → Add type hints (Priority 0 - HIGHEST, respecting Python version)
└─ NO → Continue

Missing or incomplete docstrings?
├─ YES → Add/improve docstrings (Priority 1)
└─ NO → Continue

Redundant or changelog comments present?
├─ YES → Remove obvious/changelog comments (Priority 2)
└─ NO → Continue

Error handling not explicit?
├─ YES → Add specific exception types and handling (Priority 3)
└─ NO → Continue

Opportunities for performance optimization?
├─ YES → Move computations, optimize loop order (Priority 4)
└─ NO → Continue

Functions with optional arguments?
├─ YES → Add debug logging (Priority 5)
└─ NO → Continue

Unclear naming?
├─ YES → Improve clarity (Priority 6)
└─ NO → Continue

PEP 8 violations?
├─ YES → Fix formatting (Priority 7)
└─ NO → VALIDATION COMPLETE
```

---

## Real-World Examples

### Example 1: Simple Function Refactoring

**Before:**

```python
def get_user_orders(user_id):
    # Get orders for a user
    query = "SELECT * FROM orders WHERE user_id = ?"
    df = execute_query(query, (user_id,))
    return df
```

**After:**

```python
def get_user_orders(user_id: int) -> pd.DataFrame | None:
    """Retrieve all orders for a specific user.

    Args:
        user_id: The unique identifier of the user.

    Returns:
        DataFrame with user's orders or None if user not found.
    """
    query = "SELECT id, amount, status, created_at FROM orders WHERE user_id = ?"
    return self.strategy.execute_query(query, params=(user_id,))
```

**Changes:**
- ✅ Added type hints
- ✅ Added comprehensive docstring
- ✅ Removed obvious comment
- ✅ Specified columns instead of `*`

---

### Example 2: Loop Optimization

**Before:**

```python
results = []
for item in items:
    config = load_config()  # Expensive, repeated!
    if item.valid:
        processed = process(item, config)
        results.append(processed)
```

**After:**

```python
# Load config once, reuse in loop
config = load_config()
results = []
for item in items:
    if item.valid:
        processed = process(item, config)
        results.append(processed)
```

**Changes:**
- ✅ Moved expensive operation outside loop
- ✅ Same behavior, better performance

---

### Example 3: Repository Refactoring

**Before:**

```python
class OrderRepository:
    def __init__(self):
        self.db = "mssql"

    def execute_query(self, sql):
        # Generic method, not domain-specific
        return self.strategy.execute_query(sql)
```

**After:**

```python
class OrderRepository:
    DATABASE_TYPE = "mssql"
    SCHEMA = "dbo"
    TABLE_NAME = "orders"
    COLUMNS = ["id", "customer_id", "amount", "status"]

    def __init__(self):
        self.strategy = create_strategy(self.DATABASE_TYPE)
        self.strategy.connect()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            logger.error(f"Operation failed: {exc_val}", exc_info=True)
        self.strategy.disconnect()

    def get_pending_orders(self) -> pd.DataFrame | None:
        """Retrieve all pending orders.

        Returns:
            DataFrame with pending orders.
        """
        query = f"""
        SELECT id, customer_id, amount, status
        FROM {self.SCHEMA}.{self.TABLE_NAME}
        WHERE status = 'PENDING'
        """
        return self.strategy.execute_query(query)
```

**Changes:**
- ✅ Added mandatory constants
- ✅ Implemented context manager pattern
- ✅ Renamed to domain-specific method
- ✅ Added comprehensive docstring

---

## Troubleshooting and Critical Principles

### Common Issues & Solutions

| Problem | Cause | Solution |
|---------|-------|----------|
| **Type hints cause SyntaxError** | Using Python 3.10+ syntax on Python 3.9 project | Check `pyproject.toml` for `python = "3.9"`; use `typing.List`, `Optional[X]` instead of `list`, `X \| Y` |
| **Tests fail after refactoring** | Logic was changed accidentally | Review diff carefully; undo refactoring; start over |
| **Import errors** | Removed needed import | Check grep for usage; restore import |
| **Type hints don't match** | Incomplete type hint update or wrong Python version syntax | Run mypy to catch inconsistencies; verify Python version |
| **Exception handling broken** | Changed exception type | Verify original exception type still raised |
| **Performance worse** | Optimization was incorrect | Benchmark before/after; revert if slower |
| **Code is less readable** | Over-optimization or poor naming | Prioritize clarity over performance |
| **Refactored code won't run** | Python version incompatible syntax | Check target Python version; use `from typing import List, Dict` for 3.9 |

### Critical Principles: Never Assume

**🔴 DO NOT:**

1. **Change behavior while refactoring**
   - Always run tests before and after
   - Compare outputs/side effects
   - Example: Don't change `except Exception:` to `except ValueError:` unless sure

2. **Remove imports without checking**
   - Grep for usage in the file AND elsewhere
   - Check `__all__` exports
   - Don't remove even if "unused" by IDE

3. **Change function signatures**
   - Keep parameter names, types, defaults identical
   - Add type hints to existing params, don't remove/rename them

4. **Optimize without measuring**
   - Profile before and after
   - Don't trade clarity for premature optimization
   - Benchmark performance improvements

5. **Refactor without tests**
   - Add tests first if none exist
   - Run tests before AND after refactoring
   - If tests fail, revert and investigate

**✅ DO INSTEAD:**

- Run tests before you start refactoring
- Run tests after each change
- Use git to save intermediate steps (`git add -p`)
- Compare original vs refactored behavior
- Verify imports are actually used
- Keep diffs small and focused

### Anti-Patterns to Avoid

❌ **Changing logic while refactoring** — Behavior must remain identical
❌ **Adding new features** — Refactoring is code quality only
❌ **Removing imports without checking everywhere** — Verify before removing
❌ **Over-optimizing** — Clarity > Micro-optimization
❌ **Inconsistent with project style** — Follow existing patterns
❌ **Refactoring without tests** — Tests are your safety net
❌ **Changing exception types** — Keep the same exceptions thrown
❌ **Removing error handling** — Keep validation and error checks
❌ **Using Python 3.10+ syntax on Python 3.9 projects** — Check version before applying modern type hint syntax
❌ **Not using Better Comments for critical comments** — Use `# !` for alerts, `# *` for highlights, `# ?` for questions

---

## Integration with Project Standards

This skill respects and enforces:

- **Architecture:** Database strategy pattern, repository pattern, configuration management
- **Code Style:** Google-style docstrings, PEP 8, snake_case naming
- **Performance:** Loop optimization, caching, resource efficiency
- **Testing:** Behavior-preserving changes enable efficient testing
- **Utilities:** Reuses `repo_utils.py` and `data_utils.py` helpers

---

## Next Steps

1. **Identify refactoring scope:** Whole project, folder, module, or function
2. **Run Analysis phase:** Check for improvement opportunities
3. **Apply Refactoring phase:** Implement improvements in priority order
4. **Run Validation phase:** Verify behavior and quality
5. **Commit changes:** Use `generate-commit-message` skill for well-structured commits

