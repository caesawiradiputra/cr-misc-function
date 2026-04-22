---
description: 'Comprehensive guidelines for refactoring Python code while preserving behavior and improving quality'
applyTo: '**/*.py'
---

# Python Code Refactoring Guidelines

Instructions for refactoring Python code in this project while preserving functionality and improving readability, maintainability, and documentation quality.

**For repository-specific refactoring:** See [Repository Refactoring Guidelines](./refactor-repositories.instructions.md) for specialized patterns in `repositories/` folder.

---

## Refactoring Principles

### Logic Preservation (Critical)

Code must behave **identically** after refactoring:

* **No algorithm changes** — Same flow and logic
* **No return value changes** — Same outputs
* **No side effect changes** — Same state modifications
* **No signature changes** — Same parameters and defaults
* **No external behavior changes** — Same observable effects

---

## Project Structure Awareness

Before introducing new helper logic, check whether the project already provides an appropriate location or existing implementation.

### Inspect These Directories

* `configs/` — Configuration structures, constants, environment handling
* `utils/` — Shared helper functions

### Decision Rule

**Before adding any helper code:**

1. Check `utils/` for an existing helper
2. If found → **reuse it**
3. Check `configs/` for existing patterns → **follow them**
4. Only create new utilities if:
   * Logic is reused multiple times, AND
   * No equivalent helper already exists
5. Do **not** restructure `configs/` or `utils/` unless absolutely necessary

### Objectives

* **Reuse existing utilities** — Avoid duplicating logic that already exists
* **Respect configuration patterns** — Follow established patterns in `configs/`
* **Maintain architecture** — Keep project structure consistent
* **Minimize scope** — Only modify what's necessary

---

## Performance Optimization During Refactoring

Apply performance improvements **without changing behavior or APIs**.

### Loop Optimization

**Move computations outside loops** if they don't depend on loop variables:

```python
# BAD: Recomputes expensive_function() every iteration
for item in items:
    result = expensive_function()
    process(item, result)

# GOOD: Compute once, reuse in loop
result = expensive_function()
for item in items:
    process(item, result)
```

**Cache values that don't change between iterations**:

```python
# BAD: len(items) called repeatedly
for i in range(len(items)):
    if i < len(items) - 1:
        process(items[i])

# GOOD: Cache the length
items_length = len(items)
for i in range(items_length):
    if i < items_length - 1:
        process(items[i])
```

### Processing Order Optimization

**Order operations for efficiency** — Reduce unnecessary work:

```python
# BAD: Validates all items, then filters
valid = [validate(item) for item in items]
results = [v for v in valid if v is not None]

# GOOD: Filter first to reduce validation overhead
filtered = [item for item in items if item is not None]
results = [validate(item) for item in filtered]
```

**Use early exit patterns** — Skip expensive operations:

```python
# BAD: Always processes entire collection
for item in large_collection:
    if is_critical(item):
        process_critical(item)

# GOOD: Process critical items first, skip the rest
critical = [item for item in large_collection if is_critical(item)]
for item in critical:
    process_critical(item)
```

### Resource Efficiency

* **Reuse instead of recreate** — Reuse objects like connections and compiled regexes
* **Lazy evaluation** — Defer expensive operations until results are needed
* **Caching** — Cache results of expensive operations if called multiple times with same inputs

### Optimization Constraints

* **Produce identical output** — All optimizations must yield the same results
* **Preserve readability** — Don't sacrifice clarity for marginal gains
* **Maintain compatibility** — No changes to behavior or side effects

---

## Debug Logging for Optional Arguments

When refactoring functions with optional arguments, add debug-level logging to show which arguments are being used.

### Purpose

* Improve debuggability and troubleshooting
* Provide visibility into default vs. supplied argument values
* Aid in monitoring which code paths are executing

### Implementation

**Add debug logs at function entry**:
- Log optional argument values at `DEBUG` level
- Use `logger` from `app.configs.log_config`
- Only log optional arguments, not every variable

Example:

```python
import logging

logger = logging.getLogger(__name__)

def process_data(data: list, timeout: int = 30, retry: bool = False) -> dict:
    """
    Process data with optional timeout and retry behavior.

    Args:
        data: Input data to process.
        timeout: Maximum time in seconds (default: 30).
        retry: Whether to retry on failure (default: False).

    Returns:
        Processed data dictionary.
    """
    logger.debug(
        "process_data called with timeout=%s, retry=%s",
        timeout,
        retry,
    )
    # ... function implementation
```

### Logging Constraints

* **Only add logging, don't change behavior** — Debug logging must not alter function logic or output
* **Use `DEBUG` level only** — Not `INFO` or `WARNING` (keeps logs clean in production)
* **Avoid excessive logging** — Log optional arguments, not every local variable
* **Respect project patterns** — Follow conventions from `app.configs.log_config`

---

## Code Quality Improvements

### Docstring Standards

**Use Google style consistently across the file**:

Elements to include:
* **Purpose/summary** — What the code does
* **Args** — Parameter names, types, descriptions
* **Returns** — Return value and type
* **Raises** — Exceptions raised (if applicable)
* **Side effects** — Important state changes (if relevant)

Example:

```python
def calculate_total(items: list[Item]) -> float:
    """
    Calculate the total price of items.

    Args:
        items: List of purchasable items to sum.

    Returns:
        Total cost of all items as float.

    Raises:
        ValueError: If items list is empty.
    """
```

### Comment Guidelines

**Remove:**
* Changelog-style comments (`# FIX:`, `# TODO: fixed`, `# UPDATED:`, `# BUGFIX:`)
* Obvious comments explaining simple statements
* Comments that duplicate the code

**Keep only comments that:**
* Explain *why* something exists
* Clarify non-obvious logic
* Document design decisions
* Explain workarounds for external limitations

### Naming Conventions

| Element   | Style      | Example        |
| --------- | ---------- | -------------- |
| Variables | snake_case | `user_count`   |
| Functions | snake_case | `get_user()`   |
| Classes   | PascalCase | `UserManager`  |
| Constants | UPPER_CASE | `MAX_RETRIES`  |

**Only improve naming if clarity increases** — Avoid unnecessary renames.

### Formatting & Organization

**Ensure PEP 8 compliance**:
* Proper line length (typically 88 with Black, 79 with strict mode)
* Correct spacing and indentation
* Organized imports
* Logical grouping of related code

**Import order**:
1. Standard library
2. Third-party libraries
3. Local modules

**File structure**:
1. Module docstring and license
2. Imports
3. Constants
4. Classes
5. Functions

---

## Refactoring Workflow

### Phase 1: Analysis

Before making any changes:

- [ ] Missing or incomplete docstrings?
- [ ] Inconsistent docstring formatting?
- [ ] Unclear variable or function names?
- [ ] Redundant or changelog-style comments?
- [ ] PEP 8 violations (imports, spacing, line length)?
- [ ] Comments describing *what* instead of *why*?
- [ ] Opportunities for performance optimization?
- [ ] Functions with optional arguments missing debug logging?

### Phase 2: Refactoring

Apply improvements in this order:

1. **Docstrings** — Add/improve module, function, and class documentation
2. **Comments** — Remove obvious/changelog comments, keep explanatory ones
3. **Performance** — Apply optimization patterns (moved loops, process order, caching)
4. **Debug Logging** — Add logs for optional arguments where applicable
5. **Naming** — Improve clarity only where it matters
6. **Formatting** — Ensure PEP 8 compliance
7. **Structure** — Organize file logically if needed

### Phase 3: Validation

Verify the refactoring:

- [ ] Code behavior unchanged (test if possible)
- [ ] Function signatures identical
- [ ] No required imports removed
- [ ] No unused imports introduced
- [ ] Docstrings grammatically correct and complete
- [ ] Project style rules followed
- [ ] Performance improvements applied (if applicable)
- [ ] Debug logging added for optional arguments (if applicable)

---

## Validation Commands

```bash
# Syntax check
python -m py_compile <file>

# Lint check
ruff check <file>

# Type checking (if enabled)
mypy <file>

# Run tests
pytest -v
```

---

## Quality Checklist

### Pre-Refactor

- [ ] File is readable and syntactically valid
- [ ] Original behavior is known or testable

### Post-Refactor

- [ ] Behavior identical to original
- [ ] Module has clear docstring
- [ ] All public functions/classes documented
- [ ] Comments explain *why*, not *what*
- [ ] Code is PEP 8 compliant
- [ ] Naming is clear and consistent
- [ ] Imports organized correctly
- [ ] Performance improvements applied (if applicable)
- [ ] Debug logging added for optional arguments (if applicable)
- [ ] No breaking changes to public APIs

---

## Module-Specific Refactoring Rules

### `repositories/` — Data Access Layer

**For comprehensive repository refactoring rules, see:** [Repository Refactoring Guidelines](./refactor-repositories.instructions.md)

**Quick Reference - Mandatory Structure Rules:**

1. **Organization by Database Type**
   - Organize repository files into subfolders by database type
   - Structure: `repositories/{dbtype}/{table_name}_repo.py`
   - Examples:
     - `repositories/mssql/order_repo.py`
     - `repositories/postgres/user_repo.py`
     - `repositories/hive/event_repo.py`

2. **Repository File Naming**
   - Filename format: `{table_name}_repo.py` (lowercase, snake_case)
   - Class name format: `{TableName}Repository` (PascalCase)
   - Example: `user_repo.py` → `UserRepository` class

3. **Required Class Constants**
   - Every repository class MUST define:
     - `DATABASE_TYPE: str` — The database type (e.g., `"mssql"`, `"postgres"`, `"mysql"`)
     - `SCHEMA: str` or `DATABASE: str` — Schema name (MSSQL/PostgreSQL) or database name (MySQL)
     - `TABLE_NAME: str` — The actual database table name
     - `COLUMNS: list[str]` — List of column names the repository manages

   Example (MSSQL):
   ```python
   class OrderRepository:
       """Repository for order data access."""

       DATABASE_TYPE = "mssql"
       SCHEMA = "dbo"
       TABLE_NAME = "orders"
       COLUMNS = ["order_id", "customer_id", "total_amount", "status", "created_at"]

       def __init__(self):
           self.strategy = create_strategy(self.DATABASE_TYPE)
           self.strategy.connect()
   ```

4. **Repository Context Manager Pattern**
   - Use context manager (`__enter__` / `__exit__`) for automatic connection lifecycle management
   - Always implement cleanup in `__exit__`

**⚠️ Full details:** See [Repository Refactoring Guidelines](./refactor-repositories.instructions.md) for comprehensive patterns, query standards, error handling, and validation checklists.

### `configs/` — Configuration Management

**Mandatory Rules:**

1. **Plain Method (Simple Approach)**
   - Use plain `os.environ.get()` for configuration loading
   - Do NOT use Pydantic, dataclasses, or other validation frameworks
   - Keep configs simple and straightforward
   - Example imports:
     ```python
     import os
     from datetime import datetime, timedelta
     from typing import Any, Dict
     from dotenv import load_dotenv
     ```
   - This is the ONLY approved approach for config.py

2. **Environment Variable Loading Order**
   - Load `.env` file first (project root)
   - Check for Vault secrets in Docker/Kubernetes deployments (`/vault/secrets/.env`)
   - Override `.env` with Vault if both exist
   - Example:
     ```python
     load_dotenv()
     VAULT_ENV_FILE = "/vault/secrets/.env"
     if os.path.exists(VAULT_ENV_FILE):
         load_dotenv(dotenv_path=VAULT_ENV_FILE, override=True)
     ```

3. **Constant Definition**
   - Use `UPPER_CASE` for all configuration constants
   - Define constants at module level for easy reference
   - Use empty string as default when env var is missing
   - Example:
     ```python
     DATABASE_MSSQL_HOST: str = os.environ.get("DATABASE_MSSQL_HOST", "")
     DATABASE_MSSQL_PORT: str = os.environ.get("DATABASE_MSSQL_PORT", "")
     DATABASE_MSSQL_USER: str = os.environ.get("DATABASE_MSSQL_USER", "")
     ```

4. **Configuration Dictionaries**
   - Group related configs into simple dictionaries at module level
   - Each config group is a `Dict[str, Any]`
   - Example:
     ```python
     DATABASE_MSSQL: Dict[str, Any] = {
         "user": DATABASE_MSSQL_USER,
         "password": DATABASE_MSSQL_PASSWORD,
         "host": DATABASE_MSSQL_HOST,
         "port": DATABASE_MSSQL_PORT,
     }
     ```

5. **Configuration Validation**
   - Validation happens in the factory or connection layer, NOT in config.py
   - Config.py loads values, factory/connection validates them
   - Fail fast at factory/connection time with clear error messages
   - Example in factory.py:
     ```python
     if not config.get("host"):
         raise ValueError(f"[mssql] Missing required config: host")
     ```

---

### `connections/strategies/` — Database Strategy Pattern

**Mandatory Rules:**

1. **File Organization by Database Type**
   - One strategy implementation per database
   - Filename format: `{dbtype}_strategy.py` (lowercase)
   - Examples: `mssql_strategy.py`, `postgres_strategy.py`, `trino_strategy.py`

2. **Class Naming**
   - Format: `{DBType}Strategy` (PascalCase)
   - Example: `MSSQLStrategy`, `PostgresStrategy`, `TrinoStrategy`

3. **Base Class Contract**
   - All strategies MUST inherit from `DatabaseStrategy` (defined in `base.py`)
   - Implement all abstract methods defined in base class
   - Do NOT add new abstract methods without updating all implementations

4. **Connection Pooling Documentation**
   - Document pool settings in class docstring
   - Include default `pool_size` and `max_overflow` values
   - Example:
     ```python
     class MSSQLStrategy(DatabaseStrategy):
         """MSSQL database strategy with connection pooling.

         Connection pool settings:
         - pool_size: 5 (number of persistent connections)
         - max_overflow: 10 (additional connections beyond pool_size)
         """
     ```

5. **Error Handling Standardization**
   - Catch database-specific exceptions in each strategy
   - Convert to standardized error types for consistent error handling
   - Do NOT let database-specific exceptions bubble up
   - Example:
     ```python
     try:
         result = self.engine.execute(query)
     except pyodbc.IntegrityError as e:
         raise ValueError(f"Data integrity violation: {e}")
     except pyodbc.DatabaseError as e:
         raise RuntimeError(f"Database error: {e}")
     ```

6. **Resource Cleanup**
   - Implement proper `disconnect()` method for cleanup
   - Close all connections, release all resources
   - Ensure idempotent (safe to call multiple times)
   - Example:
     ```python
     def disconnect(self):
         """Disconnect and release all resources."""
         if self.engine:
             self.engine.dispose()
             self.engine = None
     ```

---

### `app/` — Main Application Module

**Mandatory Rules:**

1. **File Organization by Responsibility**
   - `main.py` — Entry point and initialization ONLY
   - `{feature}_service.py` — Business logic and domain operations
   - `{feature}_handler.py` — Request/response handling and API contracts
   - Example structure:
     ```
     app/
     ├── main.py
     ├── order_service.py
     ├── order_handler.py
     ├── user_service.py
     └── user_handler.py
     ```

2. **Main Module Content**
   - Keep `main.py` minimal (entry point only)
   - Import and instantiate services, then run/serve
   - Do NOT contain business logic in `main.py`

3. **Import Organization**
   - Keep imports minimal in `main.py`
   - Import from services, not directly from utils or configs
   - Avoid importing everything at module level

4. **Dependency Injection**
   - Pass dependencies explicitly to functions/classes
   - Do NOT use global variables for shared dependencies
   - Avoid circular imports by respecting module boundaries

5. **Error Handling Centralization**
   - Handlers catch exceptions from services
   - Centralize error handling in decorators or middleware
   - Do NOT scatter error handling across multiple modules
   - Example:
     ```python
     @handle_errors
     def process_order(order_data):
         # Errors are caught and formatted by decorator
         result = order_service.create(order_data)
         return result
     ```

---

### `utils/` — Utility Functions

**Mandatory Rules:**

1. **Single Responsibility per File**
   - Each utility file handles ONE concern
   - Examples:
     - `date_utils.py` — Date/time manipulation and formatting
     - `parsing_utils.py` — Data parsing and deserialization
     - `validation_utils.py` — Input validation and type checking
     - `repo_utils.py` — Repository-layer utilities (query building, file loading)
   - Do NOT create `helpers.py` or `common_utils.py` (too generic)

2. **Standalone Implementation**
   - Utility functions should NOT import from other utility files
   - Keep utils independent and reusable in isolation
   - Minimize dependencies to stdlib and well-known third-party libraries

3. **Type Hints on All Functions**
   - Always include type hints on utility function signatures
   - Improves reusability and IDE support
   - Use modern union syntax: `str | None` instead of `Optional[str]`
   - Use modern syntax: `list[Item]`, `dict[str, int]` instead of `List[Item]`, `Dict[str, int]`
   - Example:
     ```python
     def format_date(date: datetime, fmt: str = "%Y-%m-%d") -> str:
         """Format a datetime object to string."""
         return date.strftime(fmt)

     def find_user(user_id: int) -> dict[str, str] | None:
         """Find a user by ID or return None if not found."""
         # Use | None instead of Optional
         ...
     ```

4. **Documentation for Public Functions**
   - Every public function requires a docstring
   - Include usage example in docstring when helpful
   - Example:
     ```python
     def parse_phone(phone: str) -> str:
         """Parse and normalize a phone number.

         Args:
             phone: Raw phone number string (any format).

         Returns:
             Normalized phone number in format: +1-XXX-XXX-XXXX

         Example:
             >>> parse_phone("5551234567")
             "+1-555-123-4567"
         """
     ```

---

## Success Criteria

✅ Refactored code behaves identically to original
✅ Docstrings are consistent, complete, and follow Google style
✅ Code is PEP 8 compliant
✅ Comments are minimal and explain design decisions
✅ Performance optimizations applied without sacrificing readability
✅ Debug logging visible for optional arguments
✅ No breaking changes to function signatures or public APIs
✅ Module-specific rules followed (repositories with DATABASE_TYPE, SCHEMA/DATABASE, TABLE_NAME, and COLUMNS constants)
