# Qoder AI — Global User Configuration Guide

This document describes what should go in Qoder's global user configuration — settings that apply across **all projects**, not just a single workspace.

## Global Settings Path

```
C:\Users\203715\AppData\Roaming\Qoder\User\settings.json
```

On other platforms:
- **macOS**: `~/Library/Application Support/Qoder/User/settings.json`
- **Linux**: `~/.config/Qoder/User/settings.json`

---

## What Belongs in Global Config

### 1. Terminal Auto-Approval Rules

Rules for commands Qoder can execute without asking the user first. These should be **safe, read-only, or idempotent** operations that are universally useful:

```jsonc
{
  "qoder.terminal.autoApprove": [
    "git status",
    "git log",
    "git diff",
    "git branch --show-current",
    "git fetch --prune",
    "python --version",
    "uv --version",
    "uv run python -m py_compile *",
    "uv run ruff check *",
    "uv run ruff format --check *",
    "uv run mypy *",
    "uv run pytest *",
    "Get-ChildItem *",
    "Get-Content *",
    "Test-Path *",
    "Select-String *",
    "dir *",
    "type *",
    "where *"
  ]
}
```

### 2. Universal Coding Standards

Standards that apply regardless of project:

- **Conventional Commits + gitmoji** — consistent commit messaging across all repos
- **Double quotes for strings** — consistency in all languages
- **Trailing newlines** — always end files with a newline
- **UTF-8 encoding** — all files UTF-8 without BOM

### 3. Default AI Behavior Preferences

| Setting | Value | Reason |
| --- | --- | --- |
| Ask before destructive operations | `true` | Safety first |
| Present changes before applying | `true` | User review required |
| Use memory for project context | `true` | Persist learnings across sessions |
| Verify with tests after changes | `true` | Catch regressions early |

### 4. Global MCP Servers

MCP servers that are useful across all projects (no project-specific secrets):

```jsonc
{
  "mcpServers": {
    "context7": {
      "command": "npx",
      "args": ["-y", "@upstash/context7-mcp"]
    }
  }
}
```

> **Note**: Project-specific MCP servers (with secrets, specific ports, or domain URLs) should go in `.vscode/mcp.json` at the workspace level, not here.

### 5. Global Skills

Reusable skills that apply to any project should be stored globally. These are the same skill format as workspace skills but available everywhere:

- `/commit` — Conventional Commit + gitmoji workflow
- `/refactor-python` — Python refactoring with behavior preservation
- `/setup-workspace` — Workspace configuration audit

These can be stored in the global Qoder skills directory.

---

## What Does NOT Belong in Global Config

| Item | Where It Belongs | Reason |
| --- | --- | --- |
| Database connection strings | Workspace `.env` or `.vscode/mcp.json` | Project-specific secrets |
| Service URLs and ports | Workspace `.qoder/QODER.md` | Project-specific endpoints |
| Table/topic names | Workspace `AGENTS.md` | Project-specific domain logic |
| Branch naming conventions | Workspace `AGENTS.md` | May vary by team/project |
| CI/CD pipeline references | Workspace `.qoder/QODER.md` | Project-specific workflows |
| Custom skill files for domain logic | Workspace `.qoder/skills/` | Project-specific workflows |

---

## Classification Decision Tree

```text
Does this setting reference a specific project's paths, services, or secrets?
├─ YES → Workspace-level config
│        .qoder/QODER.md, AGENTS.md, .vscode/settings.json, .vscode/mcp.json
└─ NO → Would this help on ANY project?
   ├─ YES → Global config
   │        C:\Users\203715\AppData\Roaming\Qoder\User\settings.json
   └─ NOT SURE → Ask the user before deciding
```

---

## Migration from Other AI Tools

If you have existing global configuration from Claude Code or GitHub Copilot:

| Source | What to Migrate | Target |
| --- | --- | --- |
| `~/.claude/settings.json` permissions | Auto-approval rules | Qoder `settings.json` terminal auto-approve |
| `~/.claude.json` mcpServers | Non-project MCP servers | Qoder `settings.json` mcpServers |
| `~/.claude/commands/` | Universal slash commands | Qoder global skills directory |
| `.copilot/` settings | VS Code settings | `.vscode/settings.json` (workspace) or global |

---

## Validation

After setting up global config:

- [ ] Auto-approval rules are all safe (read-only or idempotent)
- [ ] No project-specific secrets in global config
- [ ] MCP servers in global config have no project-specific URLs
- [ ] Global skills are truly universal (not domain-specific)
- [ ] JSON files parse correctly
