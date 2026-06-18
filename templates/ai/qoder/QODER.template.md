# Qoder AI — Project Configuration Template

> Replace all `{{PLACEHOLDER}}` values with your project's specifics.

---

## Environment: {{OPERATING_SYSTEM}}

This machine runs **{{OS_NAME}}** with **{{SHELL_NAME}}** as the primary shell.

### Command Execution Rules

- **Primary**: {{PRIMARY_SHELL}} — use for all complex operations
- **Secondary**: {{SECONDARY_SHELL}} — when primary is unnecessarily complex
- **Never use**: Linux/bash commands on Windows (or vice versa)
- **Chaining**: Use appropriate separator for your shell

### Python & Package Management

```powershell
{{PACKAGE_MANAGER}} sync                     # Install / sync dependencies
{{PACKAGE_MANAGER}} add package_name         # Add package
{{PACKAGE_MANAGER}} run python script.py     # Run with auto-activated venv
{{PACKAGE_MANAGER}} run mypy {{SOURCE_DIR}}/ # Type check
{{PACKAGE_MANAGER}} run ruff check .         # Lint
{{PACKAGE_MANAGER}} run ruff format .        # Format
{{PACKAGE_MANAGER}} run pytest tests/        # Run tests
```

---

## Project Standards

- **Package manager**: {{PACKAGE_MANAGER}} (not pip directly)
- **Python style**: Google-style docstrings, PEP 8, snake_case functions/variables, PascalCase classes
- **Commit format**: Conventional Commits + gitmoji (use `/commit` skill)
- **Type hints**: Match project Python version — check `pyproject.toml` first
- **Python version**: {{PYTHON_VERSION}}+ — use `X | Y` union syntax, `list[...]` generics

---

## Markdown Style

- **Code blocks must always specify a language.** Use ` ```text ` for plain text; never bare fences.
- **Table separators must have spaces around dashes.** Use `| --- | --- |`.

---

## Available Skills

| Skill | Description |
| --- | --- |
| `/commit` | Generate Conventional Commit + gitmoji message, review/refine, and commit |
| `/refactor-python` | Refactor Python code while preserving behavior |
| `/setup-workspace` | Audit and configure workspace settings, skills, and MCP servers |
| `/validate-lint-config` | Validate and sync ruff.toml + mypy.ini with environment |

> Add project-specific skills to `.qoder/skills/` and list them here.

---

## Qoder AI Capabilities

### Subagent Orchestration

- **Coding Agent**: Primary implementation — writing and editing code
- **Research Agent**: Exploring codebase, understanding patterns, searching symbols
- **Verify Agent**: Validating changes — running tests, lint, type checks
- **CodeReview Agent**: Reviewing changes before commit

### Memory System

Store and recall project-specific context across sessions:
- Architecture patterns and conventions
- Database configurations and strategy registrations
- Repository structure and naming conventions

---

## Architecture Quick Reference

### Core Patterns

1. **{{PATTERN_1_NAME}}** — {{PATTERN_1_DESCRIPTION}}
2. **{{PATTERN_2_NAME}}** — {{PATTERN_2_DESCRIPTION}}
3. **{{PATTERN_3_NAME}}** — {{PATTERN_3_DESCRIPTION}}

### Key Directories

- `{{SOURCE_DIR}}/` — Source code
- `{{CONFIGS_DIR}}/` — Configuration
- `{{UTILS_DIR}}/` — Utility functions
- `{{TESTS_DIR}}/` — Test files
- `{{DOCS_DIR}}/` — Documentation
- `templates/` — Reusable project templates

### Code Conventions

- **Type hints**: {{TYPE_HINT_STYLE}}
- **Linting**: {{LINT_RULES}} — {{LINE_LENGTH}}-char line length
- **Quotes**: Double quotes `"string"`
- **Imports**: Auto-sorted (stdlib → third-party → local)
