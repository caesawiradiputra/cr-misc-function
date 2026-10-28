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

## Step 6 — Editor Resolution & Multi-Root Tooling Health

This step has two halves with different applicability — check which you're in before skipping anything:

- **Rules 1–5 are multi-root only.** They apply when the workspace is opened via a `*.code-workspace` whose `folders[]` has more than one entry. Every failure mode they describe needs two roots to exist at all, so skip them for a single-root workspace — and say so rather than inventing problems.
- **Rules 6–7 always apply**, single-root included. They establish *which editor* and *which window* you are actually looking at; no finding anywhere in this command is trustworthy without them, and a single-root workspace on a multi-editor machine is just as easy to misread as a multi-root one.

**Scale the depth to the task.** Rules 1–5 and rule 6 are cheap filesystem/config checks — always run them where they apply. Rule 7's log forensics is the expensive part: run it only when the task actually turns on it (the user reports errors or slowness, or asks what to disable and why), not as blanket verification of every finding. Advisory, reversible output does not need the evidence depth of a change that edits shared config.

1. **Detect overlapping roots.** Flag any folder whose `path` physically contains another folder's path (e.g. an umbrella `"."` that contains the sub-project folders). Overlap is the root cause of a recurring class of VS Code extension failures: Ruff LSP `Stopping server timed out`/EPIPE/exit 1, Python env-discovery timeouts, and `command 'python.getRecommendedEnvironment' already exists` double-activation (logged as error, usually non-fatal). The only true cure is removing the overlap (drop `"path": "."` or restructure) — offer it, but it's optional if errors are non-fatal.
2. **Env discovery scope.** Flag a recursive `python-envs.workspaceSearchPaths` glob (`".\\**\\.venv"`, `**/.venv`) — it walks large `.venv` trees and causes 80s+ discovery / `configure` 30s timeouts. Prefer the non-recursive `[".venv", "*/.venv"]`.
3. **Ruff double-scan.** If an umbrella root with no `ruff.toml` contains children that each have one, a root-level lint descends into the children (verify with `ruff check .` from the root). Fix with a root `ruff.toml` whose `extend-exclude` lists the child folders so the umbrella lints nothing.
4. **Pyrefly interpreter discovery per sub-project.** In a multi-root workspace where each sub-project has its own `pyproject.toml` + `.venv` (no shared top-level one), the Pyrefly extension — notably under the **Antigravity IDE** with the Pyrefly extension enabled — repeatedly logs `While finding Python interpreter: ... no Python interpreter could be found to query for values` and re-runs its recheck on every file open/save. Root cause: there's no `pyrefly.toml`/`[tool.pyrefly]` at that sub-project's root, so Pyrefly falls back to auto-importing the nearest `mypy.ini` (`preset: legacy`) — which supplies lint settings but no interpreter path, so resolution never succeeds and the check loops. Fix: run `uvx pyrefly init` from **inside each sub-project directory** (not the umbrella root) to generate a native `pyrefly.toml` that resolves to that folder's own `.venv`; reload the window afterward so the LSP drops the legacy mypy.ini fallback.
5. **Do NOT apply these — they backfire on recent (2026.x) Python tool extensions:**
   - `python-envs.pythonProjects` with **relative** paths — it's `resource`-scoped, so each folder resolves the paths against itself, spawning phantom concatenated-path projects and a `getDefaultEnvManagerSetting … reading 'length' of undefined` crash storm.
   - `python.useEnvironmentsExtension: false` — the 2026.x mypy/black/ruff extensions **depend on** the Python Environments API; disabling it crashes them with `Cannot read properties of undefined (reading 'onDidChangeEnvironment')`. Leave it at its global value.
6. **Resolve the active editor before inspecting anything.** Multiple VS Code-family editors (stock VS Code, Antigravity IDE, Qoder, Cursor, …) are routinely installed side by side, each with its own extensions directory, settings, and log tree. Before enumerating extensions or reading any editor's settings/logs, resolve which editor process is actually hosting the session (e.g. via `$env:VSCODE_CWD`, or the most reliable signal available in the environment), and validate that the extensions/settings/log paths you inspect actually belong to *that* instance rather than a same-named guess. Do not infer the editor from whichever `code`-like binary is first on `PATH` — on a multi-editor machine it resolves ambiguously. If identity cannot be confirmed, or if new information contradicts an assumption already made, stop and re-resolve before producing any extension-specific finding — do not fall back to investigating another plausible-looking location under the same unverified method. Editor identity and workspace/root identity are separate questions; resolve both — each has its own method:
   - **Editor identity:** read `$env:VSCODE_CWD`; it points at the hosting editor's install directory. Then confirm the matching `%APPDATA%\<Editor>` data directory actually exists rather than deriving it from the display name — an editor may ship more than one same-prefixed directory (one for the workbench, one for a companion agent process), and only one holds the `logs/` tree.
   - **Workspace/window identity:** log folders are named `window1..N` with no workspace label, and window numbers are reused across reloads. Never infer which window is yours from position, recency, or which extensions happened to activate. Resolve it positively by grepping the windows' own extension logs for the repo path:
     `Select-String -Path "<logs>\<session>\window*\exthost\*\*.log" -Pattern "Documents[\\/]Repo[\\/]"`
     One window can host several roots and several windows can host the same repo, so map all of them before citing any log line as evidence.
   - **Never enumerate extensions with `code --list-extensions`.** On a multi-editor machine `code` resolves through `PATH` to whichever editor is first (typically stock VS Code), so it returns the *wrong* editor's extension set — and it writes a `cli.log`-only session folder into that editor's log tree, which later reads as if someone had used that editor. Read the hosting editor's own `<extensions-dir>/extensions.json` instead: it is authoritative for both id and version, and costs one file read.
7. **Verify before editing — but scope the verification to what the finding turns on.** Extension logs answer exactly one question: *is this extension actually activating and costing something here?* Read them only for findings that depend on that (the `safe to disable` class in Step 7, and any claim about errors or slowness), and only in a window you have positively mapped to this workspace under rule 6 — **a log line from another workspace's window is not evidence about this one**, even when the extension would plausibly behave the same way. Logs live under the resolved editor's own log tree (for stock VS Code, `%APPDATA%\Code\logs\<latest>\window*\exthost\<extension>\*.log`; other editors use their own `%APPDATA%\<Editor>` directory, confirmed per rule 6, not assumed from the display name). Check installed versions from `extensions.json`, and a setting's scope from the extension's `package.json` → `contributes.configuration` (a `window`-scoped setting can't be overridden per-folder; a `resource`-scoped one can) — the scope check only when you are actually about to recommend a setting whose scope matters. Present findings first; apply only verified-safe changes.

## Step 7 — Recommend Extensions To Enable/Disable

**Mandatory in every full audit, not just when the user asks about extensions specifically** — do not let Step 6's troubleshooting depth cause this step to get skipped or deprioritized. Two obligations every run:

1. **Recommend extensions for the current workspace** — which VS Code extensions the detected stack (languages, frameworks, linters/formatters, IaC tools) actually calls for, whether or not they're installed yet.
2. **Audit what's already installed/globally enabled against this workspace** — read the resolved editor's `extensions.json` (rule 6.6) as the authoritative "currently enabled" list, and for every entry that is `unused` or `safe to disable` per the table below, explicitly recommend disabling it **at the workspace level** (rule 3 below) — a global enable is the default for every project until someone narrows it, so an unrelated extension being globally enabled is expected, not itself a finding; the finding is that this specific workspace doesn't need it.

Based on the stack actually detected in the workspace (languages, frameworks, linters/formatters, IaC tools), recommend which VS Code extensions should be active here and which shouldn't:

1. **Decide from repo markers, not from logs.** Read the authoritative installed list once from `<extensions-dir>/extensions.json` — and do **not** cache it between runs: it changes on every install, uninstall and auto-update, and re-reading it costs a single call, which is cheaper than reasoning about whether a cache went stale. Then classify each installed extension against what the repo actually contains. A filesystem predicate settles nearly every case by itself:

   | Class | Sufficient evidence | Example |
   | --- | --- | --- |
   | required | named in repo config, or the toolchain can't run without it | `ruff.toml` → Ruff; `pyrefly.toml` → Pyrefly |
   | actively used | marker present **and**, for a linter/formatter, its binary resolves on PATH or in the project venv | `.ipynb` files → Jupyter |
   | potentially useful | relevant file types present but no config for them | a couple of `.yaml` files → YAML |
   | unused | marker absent | no `dbt_project.yml` → dbt Power User |
   | safe to disable | unused **and** measurably costing something — the **only** class that justifies reading logs (rule 6.7) | an unused extension that spawns servers or errors on activation |
   | unknown | can't establish either way — say so rather than guessing | |

   Don't recommend extensions for tooling the repo doesn't use. Persist these verdicts nowhere but this workspace's own `extensions.json` (rule 2): the marker→extension *rule* generalizes across projects, but a cached *verdict* is wrong the day the repo gains a dependency.
2. **Write `.vscode/extensions.json`** with a `recommendations` array for the stack-matched extensions, and `unwantedRecommendations` for ones known to conflict or add noise here (e.g. a competing formatter/linter for the same language). This is a soft prompt for anyone opening the folder — it does not force-enable or disable anything.
3. **State the actual enable/disable mechanism and its limits.** VS Code has no config file that force-enables or force-disables an extension per workspace — that's a per-window user action: Extensions panel → gear icon on the extension → **Disable (Workspace)** / **Enable (Workspace)**. Tell the user which extensions to toggle this way, rather than implying `extensions.json` does it.
4. **In a multi-root workspace, disable is per-window, not per-folder.** "Disable (Workspace)" applies to the whole window, not to one root inside a multi-root `*.code-workspace`. There is no native way to have an extension active for one root folder and inactive for another in the same window. If the user needs true per-folder isolation, the only fix is opening that folder as its own single-folder window instead of the multi-root file — say so plainly rather than searching for a config workaround.
5. **Settings-based extension behavior still needs correct scope.** When an extension's *behavior* (not enable/disable) should differ per folder — e.g. a linter's executable path — check that setting's scope in the extension's `package.json` → `contributes.configuration` (see Step 6.7). A `resource`-scoped setting can live in that folder's `.vscode/settings.json`; a `window`/`application`-scoped setting is ignored there in a multi-root workspace and must go in the `.code-workspace` file's own `settings` block (using `${workspaceFolder:<name>}` to target one root) or in User settings. Verify this before assuming a folder-level `.vscode/settings.json` entry is being read — it silently isn't, for window-scoped settings, in a multi-root setup.
6. **`${workspaceFolder:<name>}` is not guaranteed to be resolved by the extension that reads it.** VS Code only substitutes this variable automatically in a fixed set of contexts (`tasks.json`, `launch.json`, and settings an extension explicitly runs through its own variable-resolution call) — it is not applied generically to every extension setting. An extension that just does `vscode.workspace.getConfiguration().get('foo')` and uses the raw string (e.g. handing it to `child_process.spawn`) will pass `${workspaceFolder:<name>}` through unresolved. Confirmed case: `sqlfluff.executablePath`/`sqlfluff.workingDirectory` set in a `.code-workspace` `settings` block to `${workspaceFolder:<repo>}/.venv/bin/sqlfluff` failed with `spawn ${workspaceFolder:<repo>}/.venv/bin/sqlfluff ENOENT` — the literal, unexpanded string reached `spawn()`. This reads like a missing-executable problem, not a variable-substitution one, so it's easy to misdiagnose. When recommending `${workspaceFolder:<name>}` for a window-scoped extension setting, either confirm from the extension's own docs/source that it resolves the variable, or skip the variable and just hardcode the absolute path in the `.code-workspace` settings block — an absolute path always works and costs nothing in portability if the workspace is already machine-specific.

## Step 8 — Secrets Deny Rules & Baseline Files

Run for **every repo root** of the workspace, in all three situations: a fresh workspace, a new clone, and an existing workspace being audited. Repos differ, so inspect each one (`git ls-files` plus `ls -a`) instead of assuming a fixed list.

**Umbrella folder.** When the session starts in a folder that is not itself a git repo and holds the real repos one level down (check `git rev-parse --show-toplevel`, then list child folders containing `.git`, and the `folders[]` of any `*.code-workspace`), treat each child repo as a repo root and run every item below in it. Also create the umbrella's own `.claude/settings.json` (empty or legacy-free deny list) and `.mcp.json`, because Claude Code reads those from the session's working directory. The global deny set uses `**/` patterns, so it already covers every child repo; only repo-specific rules go into each child's own `.claude/settings.json`. Skip child folders that are not repos, and list them in the report.

1. **Find the secret-bearing files.** Search each repo (excluding `.venv`, `node_modules`, `.git`) for: `.env`, `.env.*`, `profile.yaml`/`profiles.yml`, `settings.local.json`, `credentials*.json`, `token.json`, `service-account*.json`, `*.pem`, `*.key`, `*.pfx`/`*.p12`, `id_rsa*`/`id_ed25519*`, `.netrc`, `.git-credentials`, `kubeconfig`, `*.tfvars`, `*.tfstate`, `secrets/**`. Also read `.gitignore` and `.dockerignore` for hints about what the repo already treats as secret.
2. **Global layer holds the common secret files.** Read `~/.claude/settings.json` `permissions.deny`. If it already has deny rules (or any rule for a secret file), merge the whole common set below into it: add the missing rules, never remove or reorder the user's entries. If it has none, propose creating the block. Global changes need the user's OK (Step 10). Every pattern gets both a `Read(...)` and an `Edit(...)` rule, because Edit also exposes content, and uses the `**/` prefix so nested copies are covered. Common set:
   - `**/.env` and the `.env.*` variants `dev`, `prod`, `local`, `staging`, `sit`, `uat`, `test`
   - `**/profile.yaml`, `**/profiles.yml`, `**/settings.local.json`, `**/credentials*.json`, `**/token.json`, `**/service-account*.json`
   - `**/*.pem`, `**/*.key`, `**/*.pfx`, `**/*.p12`, `**/id_rsa*`, `**/id_ed25519*`, `**/.netrc`, `**/.git-credentials`, `**/kubeconfig`, `**/*.tfvars`, `**/*.tfstate`, `**/secrets/**`
   - **`.env.template` (and `.env.example`) must stay readable.** Deny rules have no exceptions, so never use the `**/.env.*` wildcard; list the concrete variants and skip `template` and `example`.
3. **Local layer holds only what is specific to the repo.** In `<repo>/.claude/settings.json` (create when missing, otherwise merge, never remove the user's entries) put only rules the global set does not already cover: an extra `.env.<name>` variant or secret file found in step 1 (for example `Read`/`Edit` of `**/.env.sit2` or a repo-named credentials file), plus `Edit(legacy/**)` and `Write(legacy/**)` when the repo has a `legacy/` folder. Do not repeat the common set locally; if a local rule is now covered by the global set, offer to remove it. If the global layer cannot be changed (the user declines), fall back to writing the common set locally and say so.
4. **Keep secrets out of git.** Make sure each repo's `.gitignore` ignores `.env*` with `!.env.template` (and `!.env.example`), `.claude/settings.local.json` and the other files found in step 1. If a secret file is already tracked (`git ls-files`), report it loudly and do not untrack it without asking.
5. **Create `.mcp.json` at each repo root when missing,** even if no MCP server is used:

   ```json
   {
     "mcpServers": {}
   }
   ```

   Never overwrite an existing file. Do not copy a server that is already registered at user scope (Step 4). Credentials go in `${VAR}` references, never in the file, so it can be committed. Templates for common servers (for example Postgres) are in `templates/ai/claude-code/mcp/` of the `cr-misc-function` repo; the secret values go in the `env` block of `.claude/settings.local.json` or come from the shell, as that folder's README explains.
6. **Create `<repo>/.claude/settings.json` when missing** with the standard content: the `$schema` line plus a `permissions.deny` array holding only the repo-specific rules from step 3 (an empty array when the repo has none), for example:

   ```json
   {
     "$schema": "https://json.schemastore.org/claude-code-settings.json",
     "permissions": {
       "deny": [
         "Edit(legacy/**)",
         "Write(legacy/**)"
       ]
     }
   }
   ```

   Do not add hooks here; the lint hook lives in the global settings.
7. **Limits to tell the user:** `Read`/`Edit` denies do not stop a shell command such as `cat .env`, so also avoid allowing broad `Bash(cat:*)` style rules, and a denied file can still be loaded by the program being run. Validate every edited JSON file parses, and list per repo what was created, merged or already fine.

## Step 9 — Sync Environments & Debug Launch Configs

Run for every sub-repo of the workspace (each repo respectively), after the audit and before the plan.

1. **`uv sync` where the venv is missing.** For each repo with `pyproject.toml` + `uv.lock` and no `.venv`, run `unset VIRTUAL_ENV; uv sync` inside that repo (long-running, use a generous timeout). Without a `.venv`, the ruff hook, Pylance, mypy and Pyrefly cannot resolve an interpreter.
   - If a build fails because a system library is missing (e.g. `psycopg2` → `pg_config` / `libpq-dev`, `pyodbc` → `unixodbc-dev`, plus `build-essential`), do **not** edit `pyproject.toml`/`uv.lock`. `sudo` needs a password that cannot be entered from a Claude session, so give the user the exact `! sudo apt-get install -y ...` command, then re-run `uv sync` once they confirm. Offer a binary-wheel swap (e.g. `psycopg2-binary`) only as an explicit choice, after checking that the package is actually used.
   - Report per repo: synced, or failed with the one-line cause.
2. **Add or modify `.vscode/launch.json` per repo.** Read the existing file first; merge by configuration `name` (add missing, update changed, never delete the user's own entries) and never overwrite blindly. Derive configs from the repo, not from a template:
   - FastAPI/ASGI app → a `debugpy` config with `"module": "uvicorn"` and `app.<module>:app`; take the port from the `Dockerfile` `CMD` and bind `127.0.0.1`. Offer a `--reload` and a no-reload variant (breakpoints are more stable without reload).
   - `tests/` + pytest → "pytest: current file" and "pytest: all tests" (`"module": "pytest"`, `justMyCode: false`).
   - Script-per-folder repos (consumers, jobs, crawlers) → one config per runnable `main.py`/entry script plus a "current file" config. Check each entry point with a grep for `__main__`/module-level run calls, and skip placeholders (e.g. a `uv init` root `main.py`).
   - Use `"type": "debugpy"`, `"cwd": "${workspaceFolder}"` (so a root `.env` is found by `load_dotenv()`), `"console": "integratedTerminal"`. Do not read or embed `.env` values; mention which env file the entry point needs and whether it exists.
   - Debugging an entry point runs it for real (queue consumers connect to the broker and database from `.env`); say so in the summary. Do not start a debug session yourself.
   - Validate each file parses as JSON. If `.vscode/` is not gitignored, leave the file uncommitted and say so (multi-repo sessions commit only in the focus repo).

## Step 10 — Present a Plan, Then Apply

Summarize proposed changes as a short table: item → current location → target location → reason. Include the `uv sync` results and the launch configs added or changed (Step 9), and the global and per-repo secrets deny rules and baseline files (Step 8). Global config changes affect every project, so confirm with the user before editing `~/.claude/settings.json`, `~/.claude.json`, or adding files under `~/.claude/skills/`, `~/.claude/agents/`, `~/.claude/commands/`. Workspace-local changes can proceed directly.

After applying, validate any edited JSON files parse correctly, and note in memory (if this is a recurring workspace) what now lives where.
