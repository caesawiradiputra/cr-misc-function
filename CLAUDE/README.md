# CLAUDE/ — Global Claude Code Configuration

This folder contains global configuration for [Claude Code](https://claude.ai/code) — the equivalent of GitHub Copilot's `.copilot/` system, adapted for Claude's slash command model.

## Installation

> **Setting up a new machine?** Follow
> [docs/dev-machine-setup.md](../docs/dev-machine-setup.md). It installs
> *everything* here: settings, hooks, status line, skills, plugins, MCP.
> The commands below cover only `CLAUDE.md` + `commands/`, the two parts
> that change often and get re-synced.

Copy the contents to your global Claude config folder — use whichever
matches the shell actually running your Claude Code session (native Windows
vs. WSL2/Linux; see `CLAUDE.md`'s "Environment" section for how to tell).
`scripts/powershell/chat-Sync-ClaudeContext.ps1` / `scripts/bash/chat-sync-claude-context.sh`
automate exactly this and are the preferred way to keep the two in sync —
the manual commands below are the one-off/no-script fallback:

```powershell
# Windows/PowerShell
New-Item -ItemType Directory -Path "$env:USERPROFILE\.claude\commands" -Force
Copy-Item -Path ".\CLAUDE\CLAUDE.md" -Destination "$env:USERPROFILE\.claude\CLAUDE.md"
Copy-Item -Path ".\CLAUDE\commands\*" -Destination "$env:USERPROFILE\.claude\commands\" -Recurse
```

```bash
# Linux/WSL/bash
mkdir -p ~/.claude/commands
cp ./CLAUDE/CLAUDE.md ~/.claude/CLAUDE.md
cp -r ./CLAUDE/commands/. ~/.claude/commands/
```

After copying, the commands are available in **every project** on this machine.

---

## Folder Structure

```text
CLAUDE/
├── README.md                       ← This file
├── CLAUDE.md                       ← Global always-on instructions (shared — one file,
│                                       branches internally on Windows vs Linux/WSL, since
│                                       it's prose Claude reads, not something that has to
│                                       run as one shell or the other)
├── commands/                       ← Slash commands (shared — plain markdown, no OS-specific content)
│   ├── commit.md                   ← /commit
│   ├── clean-gone.md               ← /clean-gone
│   ├── generate-pr-message.md      ← /generate-pr-message
│   ├── refactor-python.md          ← /refactor-python
│   ├── refactor-repositories.md    ← /refactor-repositories
│   ├── validate-lint-config.md     ← /validate-lint-config
│   ├── create-readme.md            ← /create-readme
│   ├── create-confluence-docs.md   ← /create-confluence-docs
│   ├── generate-cde.md             ← /generate-cde
│   ├── update-cde.md               ← /update-cde
│   ├── generate-cde-spreadsheet.md ← /generate-cde-spreadsheet
│   ├── setup-workspace.md          ← /setup-workspace
│   └── <name>.md (x9)              ← "runs on Opus" wrappers that invoke a skill with
│                                       model: opus: /brainstorming, /writing-plans,
│                                       /systematic-debugging, /receiving-code-review,
│                                       /feature-dev-opus, /security-review-opus,
│                                       /spec-to-backlog, /formal-document-review,
│                                       /extract-session-preferences
├── skills/                         ← Global skills (shared — identical on both OSes)
├── statusline-command.sh           ← Shared — identical on both OSes
├── mcp-servers.json                ← Shared — just the mcpServers key, never the full .claude.json
├── windows/                        ← Only the parts that actually differ on native Windows
│   ├── settings.json                 (hooks call powershell.exe + the .ps1 scripts below)
│   └── hooks/                        (session-start-context.ps1, user-prompt-repo-focus.ps1, _repo-context-lib.ps1)
└── linux-wsl/                      ← Only the parts that actually differ on WSL2/Linux
    ├── settings.json                 (hooks call bash + the .sh scripts below)
    └── hooks/                        (session-start-context.sh, user-prompt-repo-focus.sh, _repo-context-lib.sh)
```

Everything here is a **point-in-time reference for setting up (or restoring)
this global config on a device** — not something that gets auto-synced like
`CLAUDE.md`/`commands/` do. Re-copy from the live `~/.claude/` on either side
whenever you want an updated snapshot. `settings.json` and `hooks/` are
genuinely OS-specific (different hook commands, `.ps1` vs `.sh`
implementations of the same three scripts); everything else (`skills/`,
`statusline-command.sh`, `mcpServers`) was identical on both OSes at capture
time, so it's kept as one shared copy instead of duplicated per OS.

**Windows paths are placeholders, not this machine's literal path.**
`windows/settings.json`'s hook file paths use `C:\Users\<WINDOWS_USERNAME>\...`
— replace `<WINDOWS_USERNAME>` with the actual Windows account name on
whatever device you're setting this up on; don't copy the placeholder
literally. (An earlier capture of this reference had the original machine's
real username baked into both `settings.json` and one skill file — sanitized
before committing, since a working reference for a *different* future device
shouldn't hardcode one specific machine's path.)

**Other placeholders (this repo is public).** Replace these when installing a
file into `~/.claude/`:

| Placeholder | Where | Replace with |
| --- | --- | --- |
| `<WINDOWS_USERNAME>` | `windows/settings.json`, `CLAUDE.md`, `skills/jira-ticket-kickoff`, `skills/jira-in-da-sync` | The Windows account name |
| `<ATLASSIAN_SITE>` | `skills/jira-ticket-kickoff`, `skills/bast-*` | The Atlassian site name (`<site>.atlassian.net`) |
| `<ATLASSIAN_CLOUD_ID>` | `skills/bast-*` | The site's cloud ID (from `getAccessibleAtlassianResources`) |
| `PROJ` (as in `PROJ-1234`) | `skills/jira-ticket-kickoff`, `skills/bast-*` | Your own Jira project key |
| `<BAST_TEMPLATE_PAGE_ID>` | `skills/bast-generator` | The Confluence page ID of your `BAST DATA` template copy |
| `<COMPANY>` | `skills/bast-generator/references/template-map.md` | The company name used in the BAST Scope checkbox |

Only `CLAUDE.md` and `commands/` are synced automatically
(`chat-Sync-ClaudeContext`), and neither has a placeholder that code runs:
`generate-pr-message` resolves `{jira-site}` at run time. Skills are copied
by hand, so substitute the placeholders at that point. Ticket keys shown as
`PROJ-1234` and repo names such as "a data-pipeline repo" are illustrative
only and need no substitution.

`scripts/` is deliberately **not** placeholdered: those scripts actually run
their `C:\Users\...` paths, so a placeholder would break them.

Excluded from every file here: `.credentials.json`, OAuth account info,
`sessions/`/`session-env/`/`projects/` (conversation transcripts),
`telemetry/`, `history.jsonl`, caches, and everything else in
`~/.claude.json`/`~/.claude/` beyond the config surface listed above —
nothing here should ever include secrets or usage data. Also excluded from
`skills/`: three Windows-only `*-workspace` scratch directories
(`documentation_auditor-workspace`, `jira-ticket-kickoff-workspace`,
`migrate-to-uv-workspace`) that are skill-eval/benchmark output, not
actual skills; and `skills/synced/`, which is claude.ai's cache of skills
synced from the account (UUID-named buckets), not skills authored here.

Also excluded from both `settings.json` files: the live
`autoMode.environment` block and any extra `autoMode.soft_deny` rules. They
describe this user's own orgs, repo paths, branch rules, and data
sensitivity, and this repo is public. Claude Code reads `autoMode` only from
user (`~/.claude/settings.json`) or managed settings, never from a project's
`.claude/settings*.json`. So write it per machine, and keep it
workspace-wide: entries that describe a single repo mislead auto mode in
every other repo.

---

## How It Works

### `CLAUDE.md` — Always-On Instructions

Claude reads `~/.claude/CLAUDE.md` at the start of every session. This file contains:

- Environment detection: Windows/PowerShell vs. Linux/WSL2/bash — determined
  from the session's own reported `Platform`/`Shell`, not assumed
- `uv` package manager commands (identical on both platforms)
- Project standards (docstrings, naming, commit format)
- Execution-discipline rules accumulated from real incidents (state-before-write,
  sweeping stale claims after a correction, multi-root workspace focus, etc.)
- Markdown/comment style rules
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
| `/commit` | Generate Conventional Commit + gitmoji message, review/refine, and commit | `/commit`, `/commit amend`, `/commit <guidance>` |
| `/generate-pr-message` | Generate PR messages + release folder for a branch deployment | `/generate-pr-message 1.2.0 "requirement text"` |
| `/clean-gone` | Delete local branches whose remote was deleted ([gone]), incl. worktrees | `/clean-gone` |

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

### Workspace

| Command | Description | Usage |
| --- | --- | --- |
| `/setup-workspace` | Set up or audit the workspace's Claude Code config (settings, permissions, hooks, MCP, skills), split correctly between workspace and global `~/.claude`; also audits IDE extensions and interpreters | `/setup-workspace` |

### Runs on Opus

Thin wrappers (`model: opus`) that invoke a plugin or global skill on the
strongest model. The underlying skill does the work; the wrapper just pins
the model.

| Command | Invokes |
| --- | --- |
| `/brainstorming` | Explore intent, requirements and design before implementation |
| `/writing-plans` | Turn a spec into a multi-step implementation plan |
| `/systematic-debugging` | Root-cause a bug before proposing fixes |
| `/receiving-code-review` | Evaluate incoming review feedback before implementing it |
| `/feature-dev-opus` | Guided feature development with architecture focus |
| `/security-review-opus` | Security review of pending changes on the branch |
| `/spec-to-backlog` | Confluence spec → Jira Epics and tickets |
| `/formal-document-review` | Review a contract, policy, or SP/demand letter |
| `/extract-session-preferences` | Extract durable preferences from the current session |

---

## Skills

Global skills in `skills/` trigger on their own when a request matches their
description. You can also call them by name.

| Skill | What it does |
| --- | --- |
| `migrate-to-uv` | Migrate a Poetry/Conda project to uv end to end (backup, `uv add`, config, verify) |
| `upgrade-python-version` | Move a project to a newer Python (e.g. 3.8 → 3.11): minimal dependency bumps, syntax-only rewrites, structure check, upgrade guide |
| `jira-ticket-kickoff` | Start or resume work on a ticket: fetch the requirement, sync `dev`, create the branch + `release/<TICKET>/` folder |
| `jira-in-da-sync` | Daily intake sweep over the source boards (`IN`, plus other boards in any status): clone assigned tickets that have no `PROJ` link (old ones are only listed), keep a checkpoint per board so later runs skip checked tickets, then remind which `PROJ` tickets still sit in Backlog / To Do / Data Analysis. State lives in `~/.claude/state/jira-in-da-sync.json` |
| `bast-generator` | Create a BAST handover page in Confluence from a ticket and its release folder |
| `bast-learn` | Learn a repo's BAST conventions from its older pages |
| `confluence-ops-docs` | Business/ops documentation for Confluence derived from a codebase |
| `documentation_auditor` | Audit docstrings and comments |
| `logging_auditor` | Audit logging strategy and log quality |
| `process-skill-auditor` | Audit how a skill or agent was used in a session |
| `extract-session-preferences` | Distill durable preferences from a session into memory / `CLAUDE.md` |
| `formal_document_reviewer` | Review formal documents (EN/ID) for unusual or high-impact terms |

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
