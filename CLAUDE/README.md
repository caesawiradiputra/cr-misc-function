# CLAUDE/ — Global Claude Code Configuration

This folder contains global configuration for [Claude Code](https://claude.ai/code) — the equivalent of GitHub Copilot's `.copilot/` system, adapted for Claude's slash command model.

## Installation

Copy the contents to your global Claude config folder:

```powershell
# Create global commands folder if it doesn't exist
New-Item -ItemType Directory -Path "$env:USERPROFILE\.claude\commands" -Force

# Copy global instructions
Copy-Item -Path ".\CLAUDE\CLAUDE.md" -Destination "$env:USERPROFILE\.claude\CLAUDE.md"

# Copy all slash commands
Copy-Item -Path ".\CLAUDE\commands\*" -Destination "$env:USERPROFILE\.claude\commands\" -Recurse
```

After copying, the commands are available in **every project** on this machine.

---

## Folder Structure

```text
CLAUDE/
├── README.md                       ← This file
├── CLAUDE.md                       ← Global always-on instructions
└── commands/
    ├── generate-commit-message.md  ← /generate-commit-message
    ├── refine-commit-message.md    ← /refine-commit-message
    ├── generate-pr-message.md      ← /generate-pr-message
    ├── refactor-python.md          ← /refactor-python
    ├── refactor-repositories.md    ← /refactor-repositories
    ├── validate-lint-config.md     ← /validate-lint-config
    ├── create-readme.md            ← /create-readme
    ├── create-confluence-docs.md   ← /create-confluence-docs
    ├── generate-cde.md             ← /generate-cde
    ├── update-cde.md               ← /update-cde
    └── generate-cde-spreadsheet.md ← /generate-cde-spreadsheet
```

---

## How It Works

### `CLAUDE.md` — Always-On Instructions

Claude reads `~/.claude/CLAUDE.md` at the start of every session. This file contains:

- Windows PowerShell environment rules (use PS syntax, not bash)
- `uv` package manager commands
- Project standards (docstrings, naming, commit format)
- Index of available slash commands

No action needed — it applies automatically.

### `commands/` — Slash Commands

Each `.md` file in `~/.claude/commands/` becomes a `/slash-command`. Invoke by typing `/command-name` in the Claude Code prompt.

Some commands accept arguments: `/command-name <argument>`

---

## Available Commands

### Git & Commits

| Command | Description | Usage |
| --- | --- | --- |
| `/generate-commit-message` | Generate Conventional Commit + gitmoji from staged changes | `/generate-commit-message` |
| `/refine-commit-message` | Iteratively improve an existing commit message | Paste your message, then `/refine-commit-message` |
| `/generate-pr-message` | Generate PR messages + release folder for a branch deployment | `/generate-pr-message v1.0.0 dev` |

### Code Quality

| Command | Description | Usage |
| --- | --- | --- |
| `/refactor-python` | Refactor Python code while preserving behavior | `/refactor-python app/services/order_service.py` |
| `/refactor-repositories` | Apply mandatory repository class structure | `/refactor-repositories repositories/mssql/order_repo.py` |
| `/validate-lint-config` | Validate and sync ruff.toml + mypy.ini | `/validate-lint-config update` |

### Documentation

| Command | Description | Usage |
| --- | --- | --- |
| `/create-readme` | Create or update README.md | `/create-readme` |
| `/create-confluence-docs` | Generate Confluence-ready doc hierarchy | `/create-confluence-docs obligor api` |

### Data Governance (CDE)

| Command | Description | Usage |
| --- | --- | --- |
| `/generate-cde` | Mode A: Build enterprise CDE registry from scratch | `/generate-cde` |
| `/update-cde` | Mode B: Incremental CDE registry updates | `/update-cde add payment settlement CDE` |
| `/generate-cde-spreadsheet` | Generate CDE TSV files (Registry + Lineage + Usage) | `/generate-cde-spreadsheet onboarding` |

---

## Command Arguments

Commands that accept `$ARGUMENTS` use whatever text you type after the command name:

```text
/refactor-python app/utils/data_utils.py
                 ^^^^^^^^^^^^^^^^^^^^^^^^ → $ARGUMENTS
```

```text
/validate-lint-config update
                      ^^^^^^ → $ARGUMENTS (action: validate/update/sync/check-only)
```

```text
/update-cde add CDE-PAY-006 for settlement method in payments context
            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ → $ARGUMENTS
```

If no arguments are given, the command will ask for the required context.

---

## Copilot → Claude Mapping

This folder was created from `.copilot/` configuration. The mapping is:

| GitHub Copilot | Claude Code |
| --- | --- |
| `.github/copilot-instructions.md` | `~/.claude/CLAUDE.md` (global) or `CLAUDE.md` (project) |
| `.copilot/instructions/*.instructions.md` | Sections in `CLAUDE.md` |
| `.copilot/prompts/*.prompt.md` | `~/.claude/commands/*.md` |
| `.copilot/skills/*/SKILL.md` | `~/.claude/commands/*.md` |
| `.copilot/agents/*.agent.md` | `~/.claude/commands/*.md` |

---

## Per-Project Override

To override or extend global commands for a specific project, create a local `.claude/commands/` folder in the project root. Project-level commands take precedence over global ones with the same name.

```text
your-project/
├── .claude/
│   └── commands/
│       └── refactor-python.md   ← overrides global /refactor-python for this project
└── CLAUDE.md                    ← project-specific always-on instructions
```
