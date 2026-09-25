# Claude Code Configuration — Quick Reference

Claude Code is Anthropic's AI coding assistant (CLI, plus IDE extensions for
VS Code and forks such as Antigravity). This page explains where it reads
configuration from and how this repo's templates map onto those places.

- **New machine:** [docs/dev-machine-setup.md](../../../docs/dev-machine-setup.md)
- **The global config template itself:** [CLAUDE/README.md](../../../CLAUDE/README.md)

## Configuration File Locations

Claude Code reads a **global** (user) layer and a **project** layer:

```text
~/.claude/                          ← Global: applies to every project on this machine
├── CLAUDE.md                        ← Always-on instructions
├── settings.json                    ← Permissions, hooks, plugins, status line, autoMode
├── commands/*.md                    ← Slash commands (/name)
├── skills/<name>/SKILL.md           ← Skills (trigger on matching requests)
├── hooks/                           ← Scripts the settings.json hooks call
└── statusline-command.sh            ← Status line script
~/.claude.json                       ← Login state and user-scope MCP servers (managed by `claude mcp`)

<project>/                          ← Project: this repo only, committed
├── CLAUDE.md                        ← Project instructions
└── .claude/
    ├── settings.json                ← Shared permissions/hooks for everyone on the project
    ├── settings.local.json          ← Your machine-only overrides (gitignored)
    ├── commands/                    ← Project commands (override global ones of the same name)
    └── skills/                      ← Project skills
```

In **this** repo, `CLAUDE/` at the root is *not* read by Claude Code. It's
the template for `~/.claude/`, installed by the sync scripts
(`chat-Sync-ClaudeContext.ps1` / `chat-sync-claude-context.sh`) and the
new-machine guide.

Settings precedence, highest first: managed → command line → project local →
shared project → user. Some keys are user/managed-only: `autoMode` is ignored
in project settings.

## settings.json Structure

### Permissions

Block reads/edits of secrets and legacy snapshots:

```json
{
  "permissions": {
    "deny": [
      "Read(**/.env)",
      "Edit(**/.env)",
      "Edit(legacy/**)",
      "Write(legacy/**)"
    ]
  }
}
```

### Hooks

Run commands automatically around Claude Code's actions. The global WSL/Linux
template (`CLAUDE/linux-wsl/settings.json`) formats and lints every Python
file Claude edits:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "bash -c 'unset VIRTUAL_ENV; f=$(cat | jq -r \".tool_input.file_path // empty\"); if [ -n \"$f\" ] && [[ \"$f\" == *.py ]] && [ -f \"$f\" ]; then cd \"$(dirname \"$f\")\" || exit 0; uv run --no-sync ruff format \"$f\"; uv run --no-sync ruff check --fix \"$f\"; fi; exit 0'"
          }
        ]
      }
    ]
  }
}
```

The Windows template (`CLAUDE/windows/settings.json`) and this repo's own
`.claude/settings.json` run the same steps through `powershell.exe`.

Common hook events:

- `SessionStart`: inject context at the start of a session (the global template reports sibling repos)
- `UserPromptSubmit`: react to each prompt (the global template resolves `@repo/` mentions)
- `PreToolUse` / `PostToolUse`: validate before, or format after, a tool runs

## CLAUDE.md Structure

`CLAUDE/CLAUDE.md` (installed as `~/.claude/CLAUDE.md`) contains:

- **Environment rules**: detect Windows/PowerShell vs WSL/bash from the session, path conventions
- **Project standards**: uv, code style, commit format, type hints
- **Git branch strategy**: `master` / `dev` / `sit` and their merge rules
- **Execution discipline**: rules learned from real incidents
- **Markdown and comment style**
- **Available slash commands**: quick reference table

## Slash Commands

Each `.md` file in `commands/` becomes `/file-name`. The template ships 21;
the full list with usage is in [CLAUDE/README.md](../../../CLAUDE/README.md#available-commands).

## Relationship to Other AI Configs

Claude Code's configuration is separate from but parallel to:

- **GitHub Copilot**: `.github/copilot-instructions.md`, `.copilot/`
- **Qoder**: `AGENTS.md`, `QODER/`, `.vscode/mcp.json`

`AGENTS.md` at a workspace root is a shared entry point any agent can read;
Claude Code reads `CLAUDE.md` for Claude-specific instructions.
