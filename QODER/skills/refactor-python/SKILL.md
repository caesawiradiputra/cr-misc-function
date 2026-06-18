---
name: refactor-python
version: "1.0.0"
updated: "2026-06-18"
related_skills:
  - refactor-repositories
description: Systematically improve Python code quality while guaranteeing identical behavior. Supports whole project, folder, single module, or function scope. Use when the user triggers /refactor-python, asks to refactor Python code, or wants to improve code quality.
---

# Refactor Python Code

Systematically improve Python code quality while **guaranteeing identical behavior**.

**Guarantee**: Code behaves identically after refactoring — no breaking changes.

## Scope

If arguments specify a file, folder, or function, refactor that target. Otherwise ask the user to specify scope.

## Phase 1: Analysis (Do This First)

1. **Check Python version** — determines type hint syntax:
   - Python 3.9 -> `typing.List`, `typing.Dict`, `Optional[X]`
   - Python 3.10+ -> `list`, `dict`, `X | Y` (modern syntax)

2. **Check if helpers exist** before adding new ones:
   - `app/utils/repo_utils.py` — SQL/query utilities
   - `app/utils/data_utils.py` — data I/O and conversion

3. **Identify improvement opportunities**:
   - Missing/incomplete type hints or docstrings?
   - Changelog comments (`# FIX:`, `# TODO: fixed`, `# UPDATED:`)?
   - Bare `except:` or generic `Exception`?
   - Expensive computations inside loops?
   - Functions with optional args missing debug logging?
   - PEP 8 violations?

## Phase 2: Refactoring (Priority Order)

### Priority 0 — Type Hints (Highest)
Add to all function parameters, return values, class attributes. Use Python version-appropriate syntax.

### Priority 1 — Docstrings (Google Style)
Include: clear summary, Args (with types + descriptions), Returns, Raises (if applicable).

### Priority 2 — Comments
**Remove**: changelog comments (`# FIX:`, `# TODO: fixed`), obvious comments, duplicates.
**Keep only WHY comments**: `# !` alert, `# *` highlight, `# ?` question, `# //` deprecated.

### Priority 3 — Error Handling
Replace bare `except:` with specific exception types. Use logger for context.

```python
# Before
try: ...
except: return None

# After
try: ...
except KeyError:
    logger.debug("Not found: {}", key)
    return None
except Exception as e:
    logger.error("Unexpected error: {}", e)
    raise
```

### Priority 4 — Performance
Move computations outside loops; cache values that don't change.

### Priority 5 — Debug Logging for Optional Arguments
Add at function entry. Use loguru `{}` placeholders or stdlib `%s` — never f-strings in log calls.

### Priority 6 — Naming Conventions
`snake_case` for variables/functions, `PascalCase` for classes, `UPPER_CASE` for constants. Only rename if clarity increases.

### Priority 7 — Formatting & PEP 8
Import order: stdlib -> third-party -> local. Follow ruff rules.

## Phase 3: Validation

```powershell
# 1. Syntax check
python -m py_compile <file>
# 2. Lint and format
ruff check <file>
ruff format <file>
# 3. Type check
mypy <file>
# 4. Run tests
pytest -v
```

## Logic Preservation Rules (Non-Negotiable)

- Same behavior, same return values, same side effects
- Same function signatures (parameter names, types, defaults)
- Same imports — never remove without verifying unused
- Same exception behavior

## Critical Principles

**Never**: change behavior, remove imports without checking usages, change signatures, use wrong Python version syntax, refactor without tests.

**Always**: run tests before starting, verify Python version, use `git add -p` to stage incrementally, reuse existing helpers.

## Post-Refactor Checklist

- [ ] Tests pass (behavior identical)
- [ ] Function signatures unchanged
- [ ] Type hints added to all public functions/classes
- [ ] Module docstring present
- [ ] All public functions/classes documented
- [ ] No changelog comments remain
- [ ] Error handling explicit with specific exception types
- [ ] Imports organized (stdlib -> third-party -> local)
- [ ] No imports removed that are still used
- [ ] Performance optimizations applied safely
