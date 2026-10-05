---
name: setup-workspace
version: "1.0.0"
updated: "2026-06-18"
description: Analyze the current workspace and set up or audit IDE/agent configuration (settings, permissions, hooks, MCP servers, skills, agents). Correctly splits workspace-local vs global config. Use when the user triggers /setup-workspace or asks to configure their workspace.
---

# Setup Workspace

Analyze the current workspace and set up or audit its configuration — correctly split between workspace-local and global config.

## Usage

```text
/setup-workspace [focus]
```

If arguments specify a focus area (e.g. `mcp`, `hooks`, `skills`, `permissions`), audit that only. Otherwise, audit everything.

## Step 1 — Inventory Existing Config

Read both layers before changing anything:

- **Workspace**: `.vscode/settings.json`, `.qoder/skills/`, `.qoder/agents/`, workspace-level MCP config
- **AI tool configs**: `.claude/`, `.copilot/`, `.github/copilot-instructions.md`, `.cursor/rules/`, `.aider.conf.yml`
- **Global**: `~/.qoder/settings.json` (permissions, terminal auto-approve), `~/.qoder/skills/`

## Step 2 — Classify Every Item

For each setting, permission rule, hook, MCP server, skill, and agent:

- **Workspace-specific** -> references this repo's file paths, table names, services, ports, env vars, or domain logic. Belongs in workspace config.
- **General-purpose** -> would help on any project (e.g. deny rules for `.env`/credentials, lint/format hooks, reusable skills). Belongs in global config.

When unsure whether an item should generalize, ask the user.

## Step 3 — Avoid Duplicates

Before adding anything to global config, check it isn't already there. If it exists globally, don't duplicate in workspace — remove the workspace copy instead.

## Step 4 — Flag Misplaced Existing Config

Call out anything already present in the wrong place:
- Generic config in workspace -> candidate to move to global
- Project-specific config in global -> candidate to move to workspace

## Step 5 — Multi-Root Workspace Health

Only applies when workspace has multiple roots. Check for:

1. **Overlapping roots** — flag any folder whose path physically contains another's path
2. **Env discovery scope** — flag recursive `python-envs.workspaceSearchPaths` globs causing slow discovery
3. **Ruff double-scan** — if umbrella root has no `ruff.toml` but children do, root-level lint descends into children

## Step 6 — Present a Plan, Then Apply

Summarize proposed changes as a table: item -> current location -> target location -> reason. Global config changes affect every project — confirm with user before editing. Workspace-local changes can proceed directly.

After applying, validate any edited JSON files parse correctly.
