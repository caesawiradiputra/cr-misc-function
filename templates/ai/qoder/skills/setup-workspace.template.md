---
name: setup-workspace
description: Audit and configure workspace settings, skills, and MCP servers
---

# Setup Workspace

Analyze the current workspace and set up or audit its Qoder AI configuration — correctly split between workspace-local config and global config.

## When to Use

- Setting up a new workspace for Qoder AI
- Auditing existing configuration for correctness
- Classifying which settings should be workspace-local vs. global

## Workflow

### Step 1 — Inventory Existing Config

Read both layers before changing anything:

- **Workspace**: `.qoder/`, `AGENTS.md`, `.vscode/settings.json`, `.vscode/mcp.json`
- **Global**: Qoder user settings (platform-specific path)

### Step 2 — Classify Every Item

- **Workspace-specific** → references this repo's file paths, services, ports, env vars, secrets, or domain logic. Belongs in workspace `.qoder/` or `AGENTS.md`.
- **General-purpose** → would help on *any* project (lint/format patterns, reusable skills). Belongs in global config.

When unsure, ask the user — don't assume.

### Step 3 — Avoid Duplicates

Before adding anything to global config, check it isn't already there. If it exists globally, don't duplicate in workspace.

### Step 4 — Flag Misplaced Existing Config

- Generic config in workspace → candidate to move to global
- Project-specific config in global → candidate to move to workspace

### Step 5 — Multi-Root Workspace Health (if applicable)

Only applies for `*.code-workspace` with multiple `folders[]` entries:

1. **Detect overlapping roots** — flag nested paths
2. **Env discovery scope** — flag recursive globs; prefer non-recursive
3. **Ruff double-scan** — check for root lint descending into children
4. **Verify before editing** — confirm findings against actual extension logs

### Step 6 — Present a Plan, Then Apply

Summarize proposed changes as a table: item → current location → target location → reason. Confirm with user before editing global config. Workspace-local changes can proceed directly.

Validate edited JSON files parse correctly after applying.

## Validation

- [ ] All existing config items classified (workspace vs. global)
- [ ] No duplicates between workspace and global config
- [ ] Misplaced items flagged
- [ ] Multi-root workspace issues identified (if applicable)
- [ ] Plan presented before changes applied
- [ ] JSON files validated after editing
