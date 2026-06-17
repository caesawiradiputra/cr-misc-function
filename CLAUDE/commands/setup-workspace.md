# Setup Workspace

Analyze the current workspace and set up or audit its Claude Code configuration (settings, permissions, hooks, MCP servers, skills, agents) — correctly split between workspace-local config and global (`~/.claude`) config.

## Usage

```text
/setup-workspace [focus]
```

If `$ARGUMENTS` is provided, focus on that area only (e.g. `mcp`, `hooks`, `skills`, `permissions`). Otherwise, audit everything.

Focus: **$ARGUMENTS**

---

## Step 1 — Run the Automation Recommender

Invoke the `claude-code-setup:claude-automation-recommender` skill on the current workspace to get baseline recommendations for hooks, subagents, skills, plugins, and MCP servers.

## Step 2 — Inventory Existing Config

Read both layers before changing anything:

- **Workspace**: `.claude/settings.json`, `.claude/settings.local.json`, `.claude/skills/`, `.claude/agents/`, `.mcp.json` (repo root, and any sub-repo roots in a multi-repo workspace)
- **Global**: `~/.claude/settings.json` (permissions, hooks, statusLine), `~/.claude.json` → `mcpServers` (user-scope MCP), `~/.claude/skills/`, `~/.claude/agents/`, `~/.claude/commands/`

## Step 3 — Classify Every Item (recommended + existing)

For each setting, permission rule, hook, MCP server, skill, and agent — recommended by Step 1 or already present — classify it:

- **Workspace-specific** → references this repo's file paths, table/topic names, services, ports, env vars, secrets, or domain logic. Belongs in workspace `.claude/settings.json`, `.claude/skills/`, `.claude/agents/`, or `.mcp.json`. Secrets/connection strings go in `.claude/settings.local.json` (gitignored), referenced via `${VAR}` in `.mcp.json`.
- **General-purpose** → would help on *any* project (e.g. `.env`/`token.json`/`credentials.json` deny rules, lint/format hooks for a language+tool combo the user uses broadly, doc-lookup MCP servers with no secrets, reusable skills/commands). Belongs in global `~/.claude/settings.json`, `~/.claude.json` user-scope `mcpServers`, `~/.claude/skills/`, or `~/.claude/commands/`.

When unsure whether a generic-looking item (e.g. a lint hook) should generalize to *all* projects vs. stay scoped here, ask the user — don't assume.

## Step 4 — Avoid Duplicates

Before adding anything to global config, check it isn't already there (e.g. `context7` MCP is commonly already registered at user-scope in `~/.claude.json`). If it exists globally, don't duplicate it in the workspace — remove the workspace copy instead.

## Step 5 — Flag Misplaced Existing Config

Separately call out anything *already present* that's in the wrong place:

- Generic config currently sitting in workspace `.claude/` → candidate to move to global
- Project-specific config currently sitting in global `~/.claude/` → candidate to move to this workspace

## Step 6 — Multi-Root Workspace & Editor Tooling Health

Only applies when the workspace is opened via a `*.code-workspace` whose `folders[]` has more than one entry. Skip for single-root workspaces — say so rather than inventing problems.

1. **Detect overlapping roots.** Flag any folder whose `path` physically contains another folder's path (e.g. an umbrella `"."` that contains the sub-project folders). Overlap is the root cause of a recurring class of VS Code extension failures: Ruff LSP `Stopping server timed out`/EPIPE/exit 1, Python env-discovery timeouts, and `command 'python.getRecommendedEnvironment' already exists` double-activation (logged as error, usually non-fatal). The only true cure is removing the overlap (drop `"path": "."` or restructure) — offer it, but it's optional if errors are non-fatal.
2. **Env discovery scope.** Flag a recursive `python-envs.workspaceSearchPaths` glob (`".\\**\\.venv"`, `**/.venv`) — it walks large `.venv` trees and causes 80s+ discovery / `configure` 30s timeouts. Prefer the non-recursive `[".venv", "*/.venv"]`.
3. **Ruff double-scan.** If an umbrella root with no `ruff.toml` contains children that each have one, a root-level lint descends into the children (verify with `ruff check .` from the root). Fix with a root `ruff.toml` whose `extend-exclude` lists the child folders so the umbrella lints nothing.
4. **Do NOT apply these — they backfire on recent (2026.x) Python tool extensions:**
   - `python-envs.pythonProjects` with **relative** paths — it's `resource`-scoped, so each folder resolves the paths against itself, spawning phantom concatenated-path projects and a `getDefaultEnvManagerSetting … reading 'length' of undefined` crash storm.
   - `python.useEnvironmentsExtension: false` — the 2026.x mypy/black/ruff extensions **depend on** the Python Environments API; disabling it crashes them with `Cannot read properties of undefined (reading 'onDidChangeEnvironment')`. Leave it at its global value.
5. **Verify before editing.** Confirm each finding against the actual extension logs at `%APPDATA%\Code\logs\<latest>\window*\exthost\<extension>\*.log`, and against installed extension versions and setting scopes — read the extension's `package.json` → `contributes.configuration` (a `window`-scoped setting can't be overridden per-folder; a `resource`-scoped one can). Present findings first; apply only verified-safe changes.

## Step 7 — Present a Plan, Then Apply

Summarize proposed changes as a short table: item → current location → target location → reason. Global config changes affect every project, so confirm with the user before editing `~/.claude/settings.json`, `~/.claude.json`, or adding files under `~/.claude/skills/`, `~/.claude/agents/`, `~/.claude/commands/`. Workspace-local changes can proceed directly.

After applying, validate any edited JSON files parse correctly, and note in memory (if this is a recurring workspace) what now lives where.
