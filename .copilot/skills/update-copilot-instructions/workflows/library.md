# Library Workflow

**Project Type**: Utility functions, helper modules, SDK packages, reusable code libraries

**Applies to**: Code consumed by other projects as dependencies (internal or external packages)

**Key Focus**: Public API, testing, documentation, backward compatibility

---

## Workflow Steps

### 1. Analyze the Library

Read these files to understand the library's purpose:

- `README.md` - What does the library do?
- `pyproject.toml`, `setup.py`, or package manifest - What's the version, name, dependencies?
- Folder structure - What modules/packages does it contain?
- Examples or usage patterns - How do consumers use it?

**Questions to answer**:

- What problem does this library solve?
- Who are the consumers (internal teams, external users, both)?
- What are the main modules/exports?
- What language and framework?
- Are there specific testing or quality standards?

---

### 2. Fill Project Identity Section

Update the `PROJECT CONTEXT` section in `[projectWorkspace]/.github/copilot-instructions.md`:

```markdown
**Project Name**: [Actual library name, e.g., "cr-misc-function"]

**Description**: [1-2 sentences describing what the library does]
Example: "Miscellaneous utility functions and helpers for data processing, configuration management, and repository operations."

**Project Type**: Library

**Language**: Python 3.9+
**Framework**: [List frameworks/libraries, e.g., "Pydantic (config validation), SQLAlchemy (ORM)"]
**Key Dependencies**: [List main deps, e.g., "Pydantic, SQLAlchemy, pytest"]
```

---

### 3. Add Project-Specific Patterns

Document unique conventions for THIS library:

```markdown
**Project-Specific Patterns & Conventions**:
- Testing: Uses pytest with fixtures in `tests/` folder, min 80% coverage
- Code Style: Black formatting, mypy type checking, ruff linting
- Logging: Structured logging with `logging` module, no print() statements
- Error Handling: Custom exception hierarchy in `exceptions.py`
- Configuration: Pydantic models for validation, environment-based config
- Documentation: Docstrings required for public APIs (Google style)
- Versioning: Semantic versioning (MAJOR.MINOR.PATCH)
```

---

### 4. Select Awesome-Copilot References

**Always include these** (all projects):

- Code Generation Guidelines
- Security Standards (OWASP)
- AI Prompt Engineering & Safety
- Markdown Content Rules
- GitHub Flavored Markdown
- GitHub Actions CI/CD Best Practices

**Add these for Python libraries**:

- [Python Development](https://github.com/github/awesome-copilot/blob/main/instructions/python.instructions.md)

**Add these if applicable**:

- [Testing Best Practices](https://github.com/github/awesome-copilot/blob/main/instructions/testing.instructions.md) ← If pytest/unit tests
- [Database Access Patterns](https://github.com/github/awesome-copilot/blob/main/instructions/database-access.instructions.md) ← If uses ORM/database
- [Package Distribution](https://github.com/github/awesome-copilot/blob/main/instructions/package-distribution.instructions.md) ← If public package
- [API Design](https://github.com/github/awesome-copilot/blob/main/instructions/api-design.instructions.md) ← If has public API
- [Configuration Management](https://github.com/github/awesome-copilot/blob/main/instructions/configuration.instructions.md) ← If uses config files/env vars

**Example reference section**:

```markdown
### Language/Framework-Specific References

**For Python projects**:
- [Python Development](https://github.com/github/awesome-copilot/blob/main/instructions/python.instructions.md)

**For libraries with ORM**:
- [SQLAlchemy ORM Guidelines](https://github.com/github/awesome-copilot/blob/main/instructions/sqlalchemy.instructions.md)

**For configuration management**:
- [Pydantic Configuration Best Practices](https://github.com/github/awesome-copilot/blob/main/instructions/pydantic-config.instructions.md)
```

---

### 5. Document Project-Specific Instructions

If your library has special instructions in `.github/instructions/`, document them:

```markdown
## Project-Specific Instructions & Files

This workspace contains the following project-specific instructions:

**[instruction-name].md**
- Description: What this instruction covers (e.g., "Refactoring strategies for Python code")
- When to use: When you're [doing something specific]
- Location: `.github/instructions/refactor-python-code.instructions.md`

**[another-instruction].md**
- Description: [What it covers]
- When to use: [When to apply it]
- Location: [Path]
```

If no special instructions, replace with:

```markdown
## Project-Specific Instructions & Files

This library follows standard Python conventions. See the awesome-copilot references above for detailed guidance.
```

---

### 6. Validate Changes

**Checklist**:

- [ ] All `[PLACEHOLDER]` text replaced with actual values
- [ ] Project name is accurate
- [ ] Description matches the library's actual purpose (1-2 sentences)
- [ ] Project Type is "Library"
- [ ] Tech Stack lists actual language, frameworks, dependencies
- [ ] Project-Specific Patterns describe actual conventions used
- [ ] All awesome-copilot links are correct and applicable
- [ ] Entry Point Information section was NOT modified
- [ ] No task-specific file mappings added
- [ ] All sections are filled (no empty placeholders remain)

---

### 7. Update Metadata

Change the Last Updated section at the bottom:

```markdown
## Last Updated

- **Date**: April 22, 2026
- **Status**: Project context complete
- **Author**: GitHub Copilot
```

---

## Example: cr-misc-function Library

**Before**:

```markdown
**Project Name**: [PROJECT_NAME]

**Description**: [DESCRIBE PROJECT HERE]

**Project Type**: [API Service / Consumer App / Data Pipeline / Library / Other]

**Language**: [e.g., Python 3.9+]
```

**After**:

```markdown
**Project Name**: cr-misc-function

**Description**: Common miscellaneous utility functions and helpers for data processing, configuration management, and repository operations.

**Project Type**: Library

**Language**: Python 3.9+
**Framework**: Pydantic (configuration validation), SQLAlchemy (data access)
**Key Dependencies**: Pydantic, SQLAlchemy, pytest, mypy, ruff
```

**Project-Specific Patterns Example**:

```markdown
**Project-Specific Patterns & Conventions**:
- Testing: Uses pytest with `tests/` folder structure; minimum 80% code coverage
- Code Quality: Black for formatting, mypy for type checking, ruff for linting
- Configuration: Pydantic models for environment and file-based config validation
- Data Access: SQLAlchemy ORM for database operations; custom connection strategies
- Error Handling: Custom exception hierarchy; all public functions document exceptions
- Logging: Structured logging with `logging` module; no print statements in production code
- Documentation: Google-style docstrings required for all public functions/classes
- Versioning: Semantic versioning (MAJOR.MINOR.PATCH) in pyproject.toml
```

**References Example**:

```markdown
### Language/Framework-Specific References

**For Python projects**:
- [Python Development](https://github.com/github/awesome-copilot/blob/main/instructions/python.instructions.md)

**For data access and ORM**:
- [SQLAlchemy ORM Best Practices](https://github.com/github/awesome-copilot/blob/main/instructions/sqlalchemy.instructions.md)

**For configuration management**:
- [Pydantic Validation & Configuration](https://github.com/github/awesome-copilot/blob/main/instructions/pydantic.instructions.md)

**For testing**:
- [Pytest Testing Framework](https://github.com/github/awesome-copilot/blob/main/instructions/pytest.instructions.md)
```

---

## Success Criteria

✅ Project name, description, and type accurately reflect this library
✅ Tech Stack section lists actual language, frameworks, key dependencies
✅ Project-Specific Patterns describe real conventions used in this library
✅ All placeholder text `[EXAMPLE]` is replaced with actual values
✅ Awesome-copilot references are relevant to the library's technology stack
✅ Entry Point Information section was NOT modified
✅ Last Updated date is current
✅ No task-specific file mappings were added
✅ Documentation is clear and specific to this library's context

---

## Tips for Libraries

- **Public vs. Internal**: Clearly indicate if this is a public package (NPM, PyPI) or internal library (private)
- **Dependencies**: List only the most important dependencies, not the full tree
- **Testing**: Libraries should emphasize testing patterns and coverage requirements
- **Documentation**: Highlight any documentation standards for public API
- **Versioning**: Mention semantic versioning and backward compatibility concerns
