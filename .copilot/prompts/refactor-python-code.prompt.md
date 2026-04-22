---
description: "Refactor and polish Python code while preserving behavior, improving readability, PEP 8 compliance, and docstrings"
---

# Refactor & Polish Python Code

You are an expert Python engineer performing a **non-breaking refactor** of an existing Python module to improve readability, maintainability, and documentation while ensuring behavior, API, and logic remain unchanged.

**📖 See**: [Python Coding Conventions](../instructions/python.instructions.md) for comprehensive project-specific best practices.

---

# Task

Improve the code in `${file}` (or `${selection}` if highlighted) by applying the refactoring workflow below.

---

# Constraints (Non-Negotiable)

* Code must behave **identically** — no algorithm, return value, or side effect changes
* Function signatures remain unchanged
* No new dependencies introduced
* No public APIs modified
* Python 3.9+

---

# Workflow

## 1. Analysis

Check for:
- Missing or incomplete docstrings
- Inconsistent docstring style
- Unclear variable/function names
- Redundant or changelog-style comments (`# FIX:`, `# TODO: fixed`, `# UPDATED:`)
- PEP 8 violations (imports, spacing, line length)
- Comments describing *what* instead of *why*

## 2. Refactoring

### Docstrings (Google Style)
- Add/improve module, function, and class docstrings
- Include: purpose, Args, Returns, Raises (if applicable)
- Be clear and complete

Example:
```python
def calculate_total(items: list) -> float:
    """Calculate total cost of items.

    Args:
        items: List of purchasable items.

    Returns:
        Total cost as float.
    """
```

### Comments
- Remove obvious/changelog comments
- Keep only comments that explain *why* or non-obvious logic

### Naming
- Follow Python conventions: `snake_case` (variables/functions), `PascalCase` (classes), `UPPER_CASE` (constants)
- Only improve if clarity increases

### Formatting
- Ensure PEP 8 compliance: line length, spacing, indentation
- Organize imports: stdlib → third-party → local modules

### Structure
Organize as: docstring → imports → constants → classes → functions

---

## 3. Validation

Verify:
- Behavior unchanged (test if possible)
- Function signatures identical
- No imports removed unless unused
- Docstrings grammatically correct
- Project style rules followed

---

# Output

Return **only the fully refactored Python code** — no explanations, diffs, or commentary.

---

# Quality Checklist

- [ ] Behavior identical to original
- [ ] Module has clear docstring
- [ ] Public functions/classes documented
- [ ] Comments explain non-obvious logic only
- [ ] PEP 8 compliant
- [ ] Naming clear and consistent
- [ ] Imports organized correctly
- [ ] Applied performance optimizations where applicable
- [ ] Debug logging added for optional arguments (if applicable)

---

# Validation

```bash
python -m py_compile <file>
ruff check <file>
mypy <file>          # if mypy enabled
pytest -v             # if tests exist
```

---

# Success Criteria

✅ Code behaves identically to original
✅ Docstrings consistent and complete
✅ PEP 8 compliant
✅ Comments are minimal and meaningful
✅ No breaking changes
