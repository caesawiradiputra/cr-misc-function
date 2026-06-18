# Claude Code Configuration — Quick Reference

Claude Code is Anthropic's CLI-based AI coding assistant. This reference documents how Claude Code is configured in this project.

## Configuration File Locations

Claude Code reads configuration from these locations:

```
[projectWorkspace]/
├── .claude/
│   ├── settings.json          ← Permissions, hooks (project-level)
│   └── settings.local.json   ← Local-only permissions (NOT committed)
├── CLAUDE/
│   ├── CLAUDE.md              ← Project instructions (global + project)
│   └── commands/              ← Slash command definitions
│       ├── commit.md
│       ├── generate-pr-message.md
│       ├── refactor-python.md
│       └── ... (more commands)
└── .claude/                   ← Settings directory
```

## settings.json Structure

The `.claude/settings.json` file controls:

### Permissions

Define what Claude Code is allowed or denied to do:

```json
{
  "permissions": {
    "deny": [
      "Read(**/.env)",       // Block reading env files
      "Edit(**/.env)",       // Block editing env files
      "Edit(legacy/**)",     // Block editing legacy code
      "Write(legacy/**)"    // Block writing legacy code
    ]
  }
}
```

### Hooks

Run commands automatically after Claude Code performs actions:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "powershell.exe",
            "args": ["-NoProfile", "-Command", "..."],
            "timeout": 60,
            "statusMessage": "ruff format + lint"
          }
        ]
      }
    ]
  }
}
```

**Common hook patterns:**
- `PostToolUse` with matcher `Edit|Write` — auto-format Python files after edits
- `PreToolUse` — validate before an action runs

## CLAUDE.md Structure

The `CLAUDE/CLAUDE.md` file is Claude Code's primary instruction file:

- **Environment rules**: Shell type (PowerShell vs bash), path conventions
- **Project standards**: Package manager, code style, commit format, type hints
- **Markdown style**: Language fences, table formatting
- **Available slash commands**: Quick reference table

## Slash Commands

Commands are defined as Markdown files in `CLAUDE/commands/`. Each file becomes a `/command-name` in Claude Code.

**Available commands in this project:**

| Command | Description |
| --- | --- |
| `/commit` | Generate Conventional Commit + gitmoji message |
| `/generate-pr-message` | Generate PR messages for deployment |
| `/clean-gone` | Delete local branches with deleted remotes |
| `/refactor-python` | Refactor Python preserving behavior |
| `/refactor-repositories` | Refactor repository classes |
| `/validate-lint-config` | Validate ruff.toml + mypy.ini |
| `/create-readme` | Create/update README.md |
| `/create-confluence-docs` | Generate Confluence documentation |
| `/generate-cde` | Build enterprise CDE registry |
| `/update-cde` | Incremental CDE registry update |
| `/generate-cde-spreadsheet` | Generate CDE spreadsheet |
| `/setup-workspace` | Set up workspace configuration |

## settings.local.json

The `.claude/settings.local.json` file stores local-only permission overrides. This file is NOT committed to version control and contains machine-specific allowlists.

## Relationship to Other AI Configs

Claude Code's configuration is separate from but parallel to:

- **GitHub Copilot**: `.github/copilot-instructions.md`, `.copilot/`
- **Qoder AI**: `AGENTS.md`, `.vscode/settings.json`, `.vscode/mcp.json`

The `AGENTS.md` file at the workspace root serves as a shared entry point that all AI agents can read. Claude Code also reads `CLAUDE/CLAUDE.md` for Claude-specific instructions.
