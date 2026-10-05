# Qoder AI Configuration — cr-misc-function

## Environment: Windows PowerShell

This machine runs **Windows** with **PowerShell** as the primary shell. Always use PowerShell syntax, or cmd.exe when simpler.

### Command Execution Rules

- **Primary**: PowerShell 5.1+ — use for all complex operations
- **Secondary**: cmd.exe — when PowerShell equivalent is unnecessarily complex
- **Never use**: Linux/bash commands (`ls -la`, `cat`, `grep`, `rm -rf`, `export`, etc.)
- **Chaining**: Use semicolons (`;`) not `&&` in PowerShell

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
# Correct
$path = "C:\Users\203715\Documents\Repo\project"

# Wrong
$path = "/home/user/project"
```

### Git

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
- **Commit format**: Conventional Commits + gitmoji (use `/commit` skill)
- **Type hints**: Match project Python version — check `pyproject.toml` first
- **Python 3.11+**: Use `X | Y` union syntax, `list[...]` generics (not `Optional`, `List`)

---

## Markdown Style

Rules VS Code cannot auto-fix — apply these manually when writing or editing Markdown files:

- **Code blocks must always specify a language.** Use ` ```text ` for plain text or output; never leave the opening fence bare.
- **Table separators must have spaces around dashes.** Use `| --- | --- |`, not `|---|---|`.

---

## Response Formatting

When generating any output the user needs to copy (code, commit messages, PR descriptions, SQL, configs, shell commands, markdown text):

### Rules

1. **Wrap all copy-paste content in a fenced code block.** If the user will copy it, it must be inside a fence. Explanatory prose goes before or after the block, never interleaved.
2. **One logical output = one code block.** Each distinct section gets exactly one fence containing the full output. Never split one section's output across multiple blocks.
3. **Never oscillate.** The critical failure to avoid: open a code block, close it mid-content, add a line of prose, open another block, close it, repeat. This makes copy-paste impossible. If the content belongs together, keep one fence open until the section is done.
4. **Always specify a language tag.** Use `powershell`, `python`, `sql`, `json`, `yaml`, `markdown` (for commit/PR messages), or `text` (for plain output). Never leave a fence bare.
5. **Too long for one block? Write a temp file.** If the output is too large for a single code block, write it to `~/.qoder/cache/temp/<descriptive-name>.md` and link the path in the response. Create the folder if needed. Safe to purge anytime with `Remove-Item ~/.qoder/cache/temp/*`.

### Correct Pattern

Prose before the block. Full output inside one fence. Next section: new prose, new fence.

````text
**Commit 1:**

```markdown
feat(auth): add OAuth2 login flow

- Implement token refresh logic
- Add session middleware
```

**Commit 2:**

```markdown
fix(auth): correct token expiry check

- Use UTC timestamps for comparison
```
````

### Wrong: Oscillation (in → out → in → out)

The content for Commit 1 is broken across plain text and fences. The user cannot select and copy Commit 1 in one action.

````text
**Commit 1:**

```markdown
feat(auth): add OAuth2 login flow
```
- Implement token refresh logic
- Add session middleware      <-- plain text leaked outside fence

```markdown
- Add session middleware      <-- duplicated to compensate
```

**Commit 2:**

fix(auth): correct token expiry    <-- entire message outside fence
check                              <-- orphaned line
````

---

## Available Skills

| Skill | Description |
| --- | --- |
| `/commit` | Generate Conventional Commit + gitmoji message, review/refine, and commit |
| `/generate-pr-message` | Generate PR messages + release folder for a branch deployment |
| `/clean-gone` | Delete local branches whose remote was deleted ([gone]), incl. worktrees |
| `/refactor-python` | Refactor Python code while preserving behavior |
| `/refactor-repositories` | Refactor repository classes to mandatory structure |
| `/validate-lint-config` | Validate and sync ruff.toml + mypy.ini with environment |
| `/create-readme` | Create or update README.md following project standards |
| `/create-confluence-docs` | Generate Confluence-ready documentation hierarchy |
| `/generate-cde` | Mode A: Build enterprise CDE registry from scratch |
| `/update-cde` | Mode B: Incremental CDE registry enhancement |
| `/generate-cde-spreadsheet` | Generate CDE spreadsheet (Master Registry + Lineage + Usage) |
| `/setup-workspace` | Audit and configure workspace settings, skills, and MCP servers |

---

## Qoder AI Capabilities

Leverage these capabilities when working on this project:

### Subagent Orchestration

- **Coding Agent**: Primary implementation — use for writing and editing code
- **Research Agent**: Use for exploring codebase, understanding patterns, searching symbols
- **Verify Agent**: Use for validating changes — run tests, lint, type checks
- **CodeReview Agent**: Use for reviewing changes before commit

### Memory System

Store and recall project-specific context across sessions:
- Architecture patterns (Strategy, Repository, Configuration Management)
- Database strategy registrations and their supported types
- Repository conventions and required structure
- Configuration tier priorities

### Skills

Skills are invoked via `/skill-name` and provide structured workflows. Each skill is a self-contained markdown file in `.qoder/skills/` with:
- When to use it
- Step-by-step workflow
- Validation criteria

---

## Architecture Quick Reference

### Three Core Patterns

1. **Strategy Pattern** (Database Abstraction) — `create_strategy(db_type)` → pluggable implementations
2. **Repository Pattern** (Domain CRUD) — Inherit `BaseRepository` + declare 4 constants
3. **Configuration Management** — Three-tier priority: Vault → .env → env vars → defaults

### Key Directories

- `app/connections/strategies/` — Database implementations
- `app/repositories/` — Base CRUD class + domain repositories
- `app/configs/` — Configuration management
- `app/utils/` — Utility functions (copy-paste ready)
- `scripts/powershell/` — Git workflows, environment setup
- `templates/` — Reusable project templates
- `docs/` — Architecture and deployment documentation

### Code Conventions

- **Type hints**: Modern syntax (`X | Y`, `list[...]`) — Python 3.11+
- **Ruff rules**: E, F, I, B, UP, C90 — 88-char line length
- **Quotes**: Double quotes `"string"`
- **Imports**: Auto-sorted (stdlib → third-party → local)
