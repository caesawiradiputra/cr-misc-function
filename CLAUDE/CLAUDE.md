# Global Claude Instructions

## Environment: Windows PowerShell

This machine runs **Windows** with **PowerShell** as the primary shell. Always use PowerShell syntax, or cmd.exe when simpler.

### Command Execution Rules

- **Primary**: PowerShell 5.1+ — use for all complex operations
- **Secondary**: cmd.exe — when PowerShell equivalent is unnecessarily complex
- **Never use**: Linux/bash commands (`ls -la`, `cat`, `grep`, `rm -rf`, `export`, etc.)

### Command Reference

| Task | PowerShell | cmd.exe |
| --- | --- | --- |
| Navigate | `Set-Location "C:\path"` | `cd C:\path` |
| List files | `Get-ChildItem` | `dir` |
| Show file | `Get-Content file.txt` | `type file.txt` |
| Search text | `Select-String -Path "*.py" -Pattern "x"` | `findstr "x" file.txt` |
| Create dir | `New-Item -ItemType Directory -Path "a\b" -Force` | `mkdir a\b` |
| Delete dir | `Remove-Item -Path "folder" -Recurse -Force` | `rmdir /s /q folder` |
| Set env var | `$env:VAR = "value"` | `set VAR=value` |
| Find command | `Get-Command python` | `where python` |

### Chaining Commands

```powershell
# PowerShell: use semicolons
Set-Location C:\project; python --version; uv sync

# NOT bash syntax
# cd /project && python --version && poetry install  ← WRONG
```

### Virtual Environment

```powershell
# Activate (PowerShell)
& ".\.venv\Scripts\Activate.ps1"

# If blocked by execution policy:
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
& ".\.venv\Scripts\Activate.ps1"
```

### Python & Package Management (uv)

```powershell
uv sync                     # Install / sync dependencies
uv add package_name         # Add package
uv add --dev package_name   # Add dev dependency
uv remove package_name      # Remove package
uv run python script.py     # Run with auto-activated venv
uv run mypy app/            # Type check
uv run ruff check .         # Lint
uv run ruff format .        # Format
uv run pytest tests/        # Run tests
```

### Path Handling

Always use backslashes for Windows paths:

```powershell
# ✅ Correct
$path = "C:\Users\203715\Documents\Repo\project"

# ❌ Wrong
$path = "/home/user/project"
```

### Git (same syntax on all platforms)

```powershell
git status
git add .
git add -p
git diff --staged
git commit -m "message"
git log --oneline -10
git push origin branch_name
```

---

## Project Standards

- **Package manager**: uv (not pip directly)
- **Python style**: Google-style docstrings, PEP 8, snake_case functions/variables, PascalCase classes
- **Commit format**: Conventional Commits + gitmoji (see `/generate-commit-message`)
- **Type hints**: Match project Python version — check `pyproject.toml` first

---

## Markdown Style

Rules VS Code cannot auto-fix — apply these manually when writing or editing Markdown files:

- **Code blocks must always specify a language.** Use ` ```text ` for plain text or output; never leave the opening fence bare (` ``` `).
- **Table separators must have spaces around dashes.** Use `| --- | --- |`, not `|---|---|`.

---

## Available Slash Commands

| Command | Description |
| --- | --- |
| `/generate-commit-message` | Generate Conventional Commit message from staged changes |
| `/refine-commit-message` | Iteratively improve an existing commit message |
| `/generate-pr-message` | Generate PR messages + release folder for a branch deployment |
| `/refactor-python` | Refactor Python code while preserving behavior |
| `/refactor-repositories` | Refactor repository classes to mandatory structure |
| `/validate-lint-config` | Validate and sync ruff.toml + mypy.ini with environment |
| `/create-readme` | Create or update README.md following project standards |
| `/create-confluence-docs` | Generate Confluence-ready documentation hierarchy |
| `/generate-cde` | Mode A: Build enterprise CDE registry from scratch |
| `/update-cde` | Mode B: Incremental CDE registry enhancement |
| `/generate-cde-spreadsheet` | Generate CDE spreadsheet (Master Registry + Lineage + Usage) |
