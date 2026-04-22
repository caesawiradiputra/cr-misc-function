---
name: refactor-python-code
description: "Refactor and polish Python code while preserving behavior, improving readability, documentation, and adherence to project standards. Supports whole project, folder, or single file refactoring."
---

# Refactor Python Code

Systematically improve Python code quality while guaranteeing identical behavior, preserving function signatures, and maintaining project architecture.

**Scope:** Refactor a whole project, a folder, a single module, or a function.
**Guarantee:** Code behaves identically; no breaking changes.

---

## Core Principles

### Logic Preservation (Non-Negotiable)

* ✅ **Same behavior** — Algorithm, logic, and flow unchanged
* ✅ **Same return values** — Outputs identical to original
* ✅ **Same side effects** — State modifications unchanged
* ✅ **Same signatures** — Parameter names, types, and defaults unchanged
* ✅ **Same observable effects** — No user-facing changes

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
| **Comments** | Should explain *why*, not *what* | Changelog comments (`# FIX:`, `# TODO: fixed`) |
| **Naming** | Clarity at a glance | Unclear variable/function names |
| **PEP 8** | Consistency and readability | Import ordering, line length, spacing |
| **Performance** | Avoid slow patterns | Loops with repeated computations, inefficient order |
| **Debug Logging** | Debuggability | Optional arguments with no visibility |

**Analysis Checklist:**

- [ ] Module docstring present and clear?
- [ ] Public functions/classes documented with Args, Returns, Raises?
- [ ] Comments explain *why*, not *what*?
- [ ] No redundant changelog comments?
- [ ] Variable/function names clear and consistent?
- [ ] PEP 8 compliant (imports, spacing, line length < 88)?
- [ ] Opportunities for performance optimization?
- [ ] Functions with optional arguments missing debug logging?

### Phase 2: Refactoring

Apply improvements in this priority order:

#### 1. Docstrings (Highest Priority)

**Google Style Format:**

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

#### 2. Comments (Second Priority)

**Remove:**
- Changelog comments: `# FIX:`, `# TODO: fixed`, `# UPDATED:`, `# BUGFIX:`
- Obvious comments: `x = 5  # Set x to 5`
- Duplicative comments: Comments that repeat the code

**Keep only:**
- *Why* the code exists: `# Lock prevents race condition on shared state`
- Non-obvious logic: Complex algorithms, workarounds
- Design decisions: `# Using Redis instead of in-memory cache for cluster support`

**Before:**
```python
# FIX: Added check for None on 2024-02-15
if item is not None:  # Item must not be None
    process(item)  # Process the item
```

**After:**
```python
# Prevents None reference exception in process()
if item is not None:
    process(item)
```

#### 3. Performance Optimization (Third Priority)

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

#### 4. Debug Logging for Optional Arguments (Fourth Priority)

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

#### 5. Naming Conventions (Fifth Priority)

**Only improve if clarity increases.**

| Element | Convention | Example |
| ------- | ---------- | ------- |
| Variables | `snake_case` | `order_count`, `user_email` |
| Functions | `snake_case` | `get_pending_orders()`, `calculate_total()` |
| Classes | `PascalCase` | `OrderRepository`, `DBConnectorStrategy` |
| Constants | `UPPER_CASE` | `MAX_RETRIES`, `DEFAULT_TIMEOUT` |

#### 6. Formatting & PEP 8 (Sixth Priority)

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

- [ ] Run tests to confirm output unchanged
- [ ] Manual testing for critical functions
- [ ] Check return types match original

**Code Quality Verification:**

- [ ] No imports removed unless unused
- [ ] Function signatures identical
- [ ] No breaking API changes
- [ ] Docstrings grammatically correct

**Project Standards Verification:**

- [ ] PEP 8 compliant
- [ ] Imports organized correctly
- [ ] Naming consistent with project convention
- [ ] Performance improvements applied safely

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

### Post-Refactor

- [ ] Behavior identical to original (tested)
- [ ] Function signatures unchanged
- [ ] Module docstring present and clear
- [ ] All public functions/classes documented
- [ ] Comments explain *why*, not *what*
- [ ] No changelog comments remain
- [ ] Code is PEP 8 compliant
- [ ] Naming is clear and consistent
- [ ] Imports organized correctly (stdlib → third-party → local)
- [ ] Performance optimizations applied (if opportunities found)
- [ ] Debug logging added for optional arguments (if applicable)
- [ ] Repository-specific rules followed (if in `repositories/`)
- [ ] No breaking changes to public APIs

---

## Validation Commands

```bash
# Syntax check
python -m py_compile <file>

# Lint and style check
ruff check <file>
ruff format <file>  # Auto-format if necessary

# Type checking
mypy <file>

# Run tests
pytest -v

# Full validation suite
python -m py_compile <file> && ruff check <file> && mypy <file> && pytest -v
```

---

## Decision Tree: When to Apply Each Improvement

```
Is this a repository file?
├─ YES → Apply Repository Mandatory Structure rules first
└─ NO → Continue below

Missing or incomplete docstrings?
├─ YES → Add/improve docstrings (Priority 1)
└─ NO → Continue

Redundant or changelog comments present?
├─ YES → Remove obvious/changelog comments (Priority 2)
└─ NO → Continue

Opportunities for performance optimization?
├─ YES → Move computations, optimize loop order (Priority 3)
└─ NO → Continue

Functions with optional arguments?
├─ YES → Add debug logging (Priority 4)
└─ NO → Continue

Unclear naming?
├─ YES → Improve clarity (Priority 5)
└─ NO → Continue

PEP 8 violations?
├─ YES → Fix formatting (Priority 6)
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

## Quick Reference

### When to Refactor

| Scenario | Action |
| ------ | --------- |
| Adding new feature | Refactor module first for clarity |
| Code is hard to understand | Refactor docstrings/comments |
| Tests are hard to write | Refactor function signatures/responsibilities |
| Performance is slow | Refactor loops and processing order |
| Debugging is difficult | Add debug logging for optional args |

### When NOT to Refactor

| Scenario | Reason |
| ------ | --------- |
| Code works perfectly | If it ain't broke, don't fix it |
| Refactoring changes behavior | Violates non-negotiable principle |
| Urgent production issue | Fix bug first, refactor later |
| No tests exist | Add tests first, then refactor |

### Anti-Patterns to Avoid

❌ **Changing logic while refactoring** — Behavior must remain identical
❌ **Adding new features** — Refactoring is code quality only
❌ **Removing imports used elsewhere** — Verify before removing
❌ **Over-optimizing** — Clarity > Micro-optimization
❌ **Inconsistent with project style** — Follow existing patterns

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

