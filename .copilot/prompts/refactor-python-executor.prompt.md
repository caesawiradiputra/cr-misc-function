---
description: "Lightweight AI execution guide for quick Python refactoring. For comprehensive guidance, see refactor-python-code SKILL."
---

# Python Refactor - Quick Executor

⚡ **This is a lightweight execution guide for AI models to refactor code quickly.**

📖 **For comprehensive guidance, decision logic, real-world examples, and best practices, see:**
- [`skills/refactor-python-code/SKILL.md`](../skills/refactor-python-code/SKILL.md) — Authoritative refactoring guide
- Use the SKILL when working on repositories, complex refactoring, or architectural changes
- Use this prompt when you just need quick AI refactoring with minimal guidance

---

# Prerequisites

- **Python version**: Verify the project's Python version (3.9, 3.10, or 3.11+) — affects type hint syntax
- **Better Comments extension**: Install [Better Comments](https://marketplace.visualstudio.com/items?itemName=aaron-bond.better-comments) for enhanced comment visibility (optional but recommended)
- **Tests**: Ideally tests exist to validate behavior before/after refactoring

---

# Task

Improve the code in `${file}` (or `${selection}` if highlighted) by applying the refactoring workflow below.

---

# Constraints (Non-Negotiable)

* Code must behave **identically** — no algorithm, return value, or side effect changes
* Function signatures remain unchanged
* No new dependencies introduced
* No public APIs modified
* Python 3.9+ (use correct type hint syntax for target version: `typing.List` for 3.9, `list` for 3.10+)
* Type hints must be compatible with project's Python version

---

# Workflow

## 1. Analysis

Check for:
- **Python version compatibility** (3.9, 3.10, or 3.11+) — affects type hint syntax choices
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
- **Use Better Comments extension syntax for emphasis:**
  - `# !` for alerts/critical: `# ! Critical: Must handle None`
  - `# ?` for questions: `# ? Why use this approach?`
  - `# *` for highlights: `# * Performance-critical path`
  - `# //` for deprecated: `# // Old implementation`

Example with Better Comments:
```python
# ! Critical: Prevents race condition
if lock.acquire():
    process_data()

# ? Why not use asyncio here?
# * ThreadPoolExecutor is 2x faster for I/O on this dataset
executor = ThreadPoolExecutor(max_workers=5)
```

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
- [ ] Comments use Better Comments syntax for emphasis (optional but recommended)
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
