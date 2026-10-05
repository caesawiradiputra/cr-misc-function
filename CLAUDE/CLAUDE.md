# Global Claude Instructions

## Environment: Windows/PowerShell OR Linux/WSL/bash — detect, don't assume

This machine hosts Claude Code sessions in **two different environments** depending on how the session was launched:

- **Native Windows** — PowerShell is the primary shell.
- **Linux/WSL2 (or another POSIX shell)** — bash is the primary shell. This happens whenever Claude Code, or the IDE's integrated terminal hosting it, is actually running inside WSL rather than directly on Windows.

**Determine which one you're in from the session's own reported environment, not from this file.** Every session's environment block reports the actual `Platform`, `Shell`, and `OS Version` (e.g. `Platform: linux`, `Shell: bash`, `Linux ...-microsoft-standard-WSL2` is WSL2/bash; `Platform: win32` with a PowerShell shell is native Windows). That signal is authoritative — this file only describes what to do once you know which case you're in, it does not mean you're always on native Windows. If a repo's own project-level config or scripts assume one shell only (e.g. a hook or script that hardcodes `powershell.exe`, or one that hardcodes `bash`), and the actual session is the other kind, use the counterpart instead of forcing the mismatched one — most of this repo's own tooling now ships both a `.ps1` and a matching `.sh` for exactly this reason (see `scripts/powershell/` + `scripts/bash/` in `cr-misc-function`).

**Global config under `~/.claude/` (hooks, statusline, scripts) must match whichever environment Claude Code and the IDE actually run in** — don't write or leave global hooks/scripts assuming Windows PowerShell if the sessions that use them actually run in WSL/bash, or vice versa. When in doubt, check what actually executed successfully in past sessions on this machine before assuming.

### Command Execution Rules

**If Windows/PowerShell primary:**

- **Primary**: PowerShell 5.1+ — use for all complex operations
- **Secondary**: cmd.exe — when PowerShell equivalent is unnecessarily complex
- **Never use**: Linux/bash commands (`ls -la`, `cat`, `grep`, `rm -rf`, `export`, etc.) unless bash is confirmed available (Git Bash, WSL interop) AND the actual shell in use for this session is bash

**If Linux/WSL2/bash primary:**

- **Primary**: bash/POSIX shell for everything
- PowerShell is only reachable if invoked explicitly (e.g. `powershell.exe` via WSL interop, when present) — never assume it's on PATH; check first (`command -v powershell.exe`)
- **Never use**: PowerShell/cmd.exe syntax in commands you actually execute in this session

### Command Reference

| Task | PowerShell (Windows) | bash (Linux/WSL) |
| --- | --- | --- |
| Navigate | `Set-Location "C:\path"` | `cd /path` |
| List files | `Get-ChildItem` | `ls -la` |
| Show file | `Get-Content file.txt` | `cat file.txt` |
| Search text | `Select-String -Path "*.py" -Pattern "x"` | `grep -rn "x" --include="*.py"` |
| Create dir | `New-Item -ItemType Directory -Path "a\b" -Force` | `mkdir -p a/b` |
| Delete dir | `Remove-Item -Path "folder" -Recurse -Force` | `rm -rf folder` |
| Set env var | `$env:VAR = "value"` | `export VAR=value` |
| Find command | `Get-Command python` | `command -v python` |

cmd.exe equivalents (Windows-only fallback, when PowerShell is unnecessarily complex): `cd`, `dir`, `type file.txt`, `findstr "x" file.txt`, `mkdir a\b`, `rmdir /s /q folder`, `set VAR=value`, `where python`.

### Chaining Commands

```powershell
# PowerShell: use semicolons
Set-Location C:\project; python --version; uv sync
```

```bash
# bash: use &&
cd /path/to/project && python --version && uv sync
```

### Virtual Environment

```powershell
# Activate (PowerShell)
& ".\.venv\Scripts\Activate.ps1"

# If blocked by execution policy:
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
& ".\.venv\Scripts\Activate.ps1"
```

```bash
# Activate (bash)
source .venv/bin/activate
```

### Python & Package Management (uv)

Identical on both platforms — `uv` is cross-shell:

```shell
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

Use the path style native to the actual environment — don't force Windows backslashes inside a WSL/bash session or vice versa:

```powershell
# Windows/PowerShell
$path = "C:\Users\<WINDOWS_USERNAME>\Documents\Repo\project"
```

```bash
# Linux/WSL/bash
path="/home/<user>/repo/project"
```

A WSL2 session and its "same machine" Windows side are **different filesystems with different home directories** (`/home/<user>` under WSL vs `C:\Users\<user>` on Windows) — a global config path that's correct on one side (e.g. `~/.claude`) resolves to a completely different physical location on the other. Don't assume a path that worked in one environment applies in the other just because it's "the same machine".

### Git (same syntax on all platforms)

```shell
git status
git add .
git add -p
git diff --staged
git commit -m "message"
git log --oneline -10
git push origin branch_name
```

---

## Docker and Network Speed in WSL

Facts established 2026-10-02 (a negative-list repo session). Only the facts
marked "confirmed" were verified; the rest are hypotheses to test.

- **Docker in WSL is a native engine, not Docker Desktop.** Confirmed: Ubuntu
  24.04 with `systemd=true`, installed with `sudo apt-get install docker.io
  docker-buildx`. Before that, `docker` on the PATH was the Windows Docker
  Desktop CLI reached through interop, which fails in WSL with "could not be
  found in this WSL distro" when WSL integration is off.
- **Keep the engine off unless needed.** The user's choice, because the corporate
  security policy blocked pulling images with Docker Desktop on Windows, and
  Docker can hog resources and crash WSL. Intended pattern: the service is
  disabled at boot (`sudo systemctl disable docker.service docker.socket`), start
  it with `sudo systemctl start docker` only for build tests, and stop it
  afterwards with `sudo systemctl stop docker.service docker.socket`. If
  `systemctl is-active docker` already shows `active`, say so rather than
  assuming it is off.
- **Cap build memory:** `docker build --memory=6g --memory-swap=6g ...`.
  `.wslconfig` currently gives WSL 16 GB, 8 CPUs and 8 GB swap, i.e. the whole
  host, so an uncapped build can starve Windows.
- **Run builds in the background** (`run_in_background`) with output sent to a
  log file; a base-image pull plus `apt-get` plus ODBC install takes many
  minutes on this network.
- **`sudo` needs a password and cannot be entered from a Claude session.** Give
  the user the exact `! sudo ...` commands to run instead. After
  `usermod -aG docker`, a new login (or a restarted Claude session) is needed
  before the group applies.
- **Downloads in WSL were much slower than on Windows — fixed by `autoProxy=true`.**
  Confirmed (2026-10-02 session, same-day follow-up): a Docker base image pull
  from WSL ran at ~0.1 MB/s (40 MB in ~376s) with `autoProxy=false`, NAT
  networking, DNS tunneling (`nameserver 10.255.255.254`), MTU 1500, WSL
  2.5.10. After setting `autoProxy=true` in `.wslconfig` and a full `wsl
  --shutdown`, repeated same-file 25MB `curl` downloads from WSL reached
  0.5-1.3 MB/s — matching `curl.exe` run both natively in PowerShell and via
  WSL interop (same range, same run-to-run spread). `autoProxy=true` alone was
  the fix; `networkingMode=mirrored`/`dnsTunneling=true` were not needed.
  `autoProxy=true` does not surface as `http_proxy`/`https_proxy` env vars
  inside the WSL shell — don't use their absence as a signal that it isn't
  working. The remaining 0.5-1.3 MB/s run-to-run spread is the underlying
  connection itself, not a WSL-vs-Windows gap: this machine's actual uplink is
  a mobile/cellular broadband connection (~9.6 Mbps down / ~5.3 Mbps up per
  Ookla, i.e. ~1.2 MB/s down ceiling) with heavy bufferbloat under load
  (latency jumps from ~25ms idle to 200-260ms loaded under Ookla's
  multi-stream test) — normal for mobile broadband, and enough by itself to
  explain single-stream `curl` numbers varying 2-3x between runs regardless of
  which OS initiated the request. Before re-chasing a WSL-specific networking
  cause for a slow transfer on this machine, re-check an independent speed
  test (e.g. speedtest.net) at that time first.
- **`.wslconfig` changes only take effect after `wsl --shutdown`,** which kills
  every running WSL process, including a running Docker build and the Claude
  session. Never suggest it while a build is running. To compare speeds, download
  the same large file with `curl.exe` on Windows and `curl` in WSL.
- **Claude Code itself can fail with `ERR_PROXY_TUNNEL` after `autoProxy=true`.**
  An already-running/resumed session (`claude --continue`) hit "Couldn't
  connect through your proxy (ERR_PROXY_TUNNEL) — the proxy refused the
  tunnel: check its credentials and that it allows this host," while a
  freshly started `claude` process on the same machine — same corporate
  PAC-based proxy that `autoProxy=true` mirrors into WSL (exposed to WSL
  processes as `WSL_PAC_URL`) — reached `api.anthropic.com` instantly. So it
  wasn't the proxy blocking the host outright — it was a stale/
  already-negotiated tunnel in the older process (most likely from before a
  `wsl --shutdown`, or a proxy-auth session expiring underneath it). Diagnose
  by testing a *fresh* `claude` process plus a direct `curl` to the Claude
  Code hosts before concluding the proxy itself is broken; if a fresh process
  also fails, that's the real signal of a proxy/allowlist problem worth
  escalating. One-off fix: restart the stuck session. Durable fix, in
  `~/.claude/settings.json`:
  ```json
  "env": {
    "NO_PROXY": "api.anthropic.com,claude.ai,claude.com,platform.claude.com,.anthropic.com,.claude.ai,.claude.com"
  }
  ```
  Scoped to Claude Code's own `env` block only — doesn't touch the shell's
  `http_proxy`/`https_proxy`, so `apt`/`pip`/`git` still go through the
  corporate proxy as before. Verify all four hosts return a real HTTP status
  direct (no `000`) before adding it. `env` is read once at Claude Code
  startup, so every running session needs restarting after this change;
  confirm with `/status`'s Proxy row.

---

## Project Standards

- **Package manager**: uv (not pip directly). When a repository uses uv/pyproject.toml
  for local development alongside shared requirements files used by CI or Docker, manage
  local development dependencies through pyproject.toml/uv rather than modifying the
  shared requirements file solely to resolve local dependency conflicts.
- **Python style**: Google-style docstrings, PEP 8, snake_case functions/variables, PascalCase classes
- **Commit format**: Conventional Commits + gitmoji (see `/commit`)
- **Type hints**: Match project Python version — check `pyproject.toml` first

---

## Git Branch Strategy

This branch topology and its merge strategies apply to repos the user created themselves, or any repo that already has `master`/`dev`/`sit` branches present — not universally to every repo. A repo created by someone else may follow a completely different flow (no `sit` branch, a different staging setup, trunk-based, etc.) — check which branches actually exist (`git branch -a` / `git ls-remote --heads`, fetching first) before assuming this structure applies, and defer to whatever convention that repo's own branches/history/CLAUDE.md actually show instead of forcing this pattern onto it. Confirmed explicitly by the user (data-pipeline repo session, 2026-09-24) after first learning the convention repo-by-repo, then clarifying it's cross-repo but not universal.

- **`master`/`main`** — the production state of the repo. Receives **merge commits from `dev`** (a regular merge, not squash) when `dev` is promoted to production.
- **`dev`/staging** — based/reset from `master`; the pre-production stage and the final check before a PR to `master`. Feature/fix/chore branches PR into `dev` using a **squash merge**, specifically to keep `dev`'s history clean (one commit per ticket, not the working branch's full commit-by-commit history).
- **`sit`** — based/reset from `dev`; the environment referred to for testing. Receives **merge commits (not squash)** directly from `fea`/`fix`/etc. branches — never from `dev`. Unlike `dev`, `sit` can carry commits from **multiple** feature/fix branches at once, since it exists for shared/simultaneous testing of several in-flight branches before each is individually ready to squash-merge into `dev`.
- **`fea`/`fix`/`chore`/etc.** — the actual work branches, based off `dev`. PR target is `dev`, not `master`.

**A PR opened against `dev` must be complete and final at the moment it's opened** — since it's expected to be squash-merged, nothing should need to land afterward. Concretely: generate and include the per-ticket release changelog (`release/<TICKET-ID>/CHANGELOG.md`, per the `/generate-pr-message` command) and any other doc updates *before* opening the PR, as part of the same branch, not as a follow-up once `dev` already has the feature merged. If something is missed after the squash-merge has already landed, fix it with a small new branch and a normal follow-up PR back into `dev` — **never** amend and force-push `dev` to fold a missed file into the already-merged commit. `dev`'s tip is shared history the moment a PR merges into it, and rewriting it is destructive even when the fix itself is trivial. (Learned 2026-09-24, a data-pipeline repo PROJ-1841 session: attempted exactly this — amending the just-merged squash commit and force-pushing `dev` to fold in a changelog file — and the user stopped it as destructive before it executed. The changelog shipped instead as a normal follow-up PR into `dev`.)

---

## Execution Discipline

Rules learned from a real incident (PROJ-1772 session, 2026-08-03): a Write call
overwrote an untracked, tested SQL file with no recovery path, then a follow-up
verification pass "confirmed" the reconstruction against a reference that was
already known to be wrong.

- **Check state before writing.** Before `Write` to any path you didn't just
  create yourself this turn, `Read` it (or check `git status`/`git diff`)
  first — no exceptions. Untracked files have no safety net; overwriting one
  can be unrecoverable.
- **Establish materiality before chasing fidelity.** Before spending more than
  one tool call verifying a low-level detail (exact whitespace, formatting,
  byte-for-byte match), state explicitly whether it's functionally material.
  Don't burn tool calls reproducing something whose relevance was never
  established.
- **Trust but verify the reference itself.** When checking reconstructed or
  new content against an existing "reference" (another file, a prior commit,
  a doc), confirm that reference is actually authoritative before diffing
  against it — a convenient reference isn't automatically a correct one.
  This extends to cross-system technical references too: before treating
  another system's example as a transferable template, confirm it matches
  the target's underlying engine, dialect, storage model, and relevant
  mechanism — a reference can be correct for its own context and still be
  the wrong template for the target. (Broadened 2026-10-01, a negative-list
  repo PROJ-1829 session: a Trino-dialect DDL and an `MSCK REPAIR TABLE`
  partition-refresh pattern from another repo were each initially applied
  to a MaxCompute/ODPS external table before correction.)
- **Sweep after correcting a claim, identifier, or behavioral constant.**
  After fixing a factual claim, renaming an identifier, or changing a related
  implementation detail in one location, grep the relevant changeset for stale
  occurrences of the old claim, identifier, or pattern before calling the fix
  done — corrections made in one place tend to leave stale duplicates
  elsewhere. This applies equally to **behavioral constants and rules** —
  retry counts, timeouts, thresholds, intervals, limits, default values,
  retry/fallback policies: changing the value invalidates every comment,
  docstring, configuration description, and runbook line that describes the
  old one. Sweep for those as part of the same change, not as a follow-up.
  (Broadened 2026-08-12, PROJ-1768 session: the same rename silently missed a
  historical variant node, a final-table column, and a retired-but-not-removed
  column — three separate misses in one session, none of them prose claims.
  Broadened again 2026-08-21, data-pipeline repo session: making a retry
  count Airflow-Variable-driven left `retries=5` / `~25 min` claims stale in
  four places — two Confluence docs, a docstring, and a comment — none caught
  by the written plan, all caught later by review.)
- **Add a new import in the same edit as its first usage — never as a
  separate, earlier edit.** If a lint-on-save hook (e.g. ruff) runs between
  edits, an import saved with no usage yet gets flagged unused and
  auto-removed before the follow-up edit that would have used it, so that
  next edit then fails with a module-not-found/undefined-name lint error.
  Combine the import line and the code referencing it into one `Edit`
  old_string/new_string pair (or one `Write`) so the file is never saved in
  a state where the import has no consumer yet. (Added 2026-08-27: this kept
  recurring — import added first, ruff auto-removed it as unused, next edit
  broke on the now-missing name.)
- **Match existing in-repo usage before assuming an external system's
  semantics.** When implementing against an external system, first check how
  the existing codebase successfully interacts with the same resource or
  operation, and follow that established pattern before inferring behavior
  from external API parameter names or assumptions. (Added 2026-08-21,
  data-pipeline repo session: a new readiness-check script addressed MaxCompute tables
  as `schema.table` because the SDK exposed a `schema=` parameter, while the
  pipeline's own SQL in the same repo had been addressing those identical
  tables as `project.table` all along. Three tables silently reported MISSING
  while holding data; the working reference was in the repo the whole time.)
- **Before concluding a git branch or ref doesn't exist, fetch first.** Local
  branch listings can be stale — `git branch -a` only shows what's already
  been fetched, not what actually exists on the remote. Run `git fetch --all
  --prune` (or at least `git fetch <remote>`) before declaring a branch
  absent or unavailable. (Added 2026-09-04, a lakehouse-platform repo
  session: told the user "there's no develop branch" after checking only
  local refs; `origin/develop` existed the whole time but had never been
  fetched in this clone.)
- **Stick to the established focus root in a multi-root workspace.** Every
  folder under `C:\Users\<WINDOWS_USERNAME>\Documents\Repo\` is a non-git umbrella
  containing the real git repos one level down (each with its own
  `.code-workspace`, and sometimes its own trimming `ruff.toml`/`CLAUDE.md`).
  A Claude Code session's cwd is pinned to the umbrella (`folders[0]`) for
  the whole session regardless of which file is open or `@`-mentioned. Once
  a conversation is clearly focused on one sub-repo — by an explicit
  `@<repo>/` mention or by several turns of edits/reads all under one path —
  keep using that repo directly for file lookups; don't fall back to
  searching sibling repos or the umbrella unless the user asks about a
  different repo or the file genuinely isn't found. (Added 2026-09-09,
  API repo session: user flagged me re-searching the wrong root mid-
  conversation after focus was already established. A global `SessionStart`
  hook and a `UserPromptSubmit` hook — `~/.claude/hooks/session-start-
  context.ps1` and `user-prompt-repo-focus.ps1` — reinforce this by
  reporting sibling repos at boot and re-resolving a specific one the first
  time it's `@`-mentioned each session.)
- **On a WSL-remote Antigravity/VS Code session, a Python extension error
  mentioning `pet` (Python Environment Tools) — `spawn .../python-env-tools/
  bin/pet ENOENT` or "PET failed after 3 restart attempts" — means the
  installed `ms-python.python` build is missing its native locator binary,
  not a settings/PATH problem.** Check first: `find
  ~/.antigravity-ide-server/extensions/ms-python.python-*/python-env-tools`
  — if the whole `python-env-tools/` dir is absent, the extension resolved to
  the `universal` variant (no bundled native binaries) instead of a
  platform-specific one (compare against `extensions.json`'s
  `targetPlatform` field for that entry). Reinstalling or picking a different
  version via "Install Another Version" does **not** fix this — the gallery
  serves `universal` regardless of version. Fix: download the *exact
  installed version's* `linux-x64` VSIX directly from the Marketplace API
  (`https://marketplace.visualstudio.com/_apis/public/gallery/publishers/
  ms-python/vsextensions/python/<version>/vspackage?targetPlatform=linux-x64`),
  `gunzip` it (curl saves it gzip-encoded, not a raw zip), extract
  `extension/python-env-tools/bin/pet` from it with Python's `zipfile`
  (`unzip` may not be installed), copy it into the installed extension's own
  `python-env-tools/bin/pet`, and `chmod +x` it. This recurs on every
  extension auto-update, since the binary lives inside the versioned,
  auto-replaced extension folder — disable Auto Update for `ms-python.python`
  specifically (Extensions panel → `...` → Disable Auto Update) to stop the
  cycle, or expect to redo the fix after each update. A separate, unrelated
  PATH issue can co-occur on the same kind of session: the remote extension
  host process often does not inherit `~/.local/bin` (check via `tr '\0' '\n'
  < /proc/<server-pid>/environ | grep ^PATH=`), which breaks `uv`-dependent
  discovery (`python-envs.alwaysUseUv`) separately from the `pet` binary
  issue — diagnose and fix each independently, don't assume fixing one fixes
  the other. (Added 2026-09-10, lakehouse repo session: both issues stacked on
  the same Antigravity-IDE-over-WSL session; the PET fix required extracting
  a binary from the official Marketplace VSIX since the repo's own GitHub
  releases ship no binary assets at all.)

---

## Markdown Style

Rules VS Code cannot auto-fix — apply these manually when writing or editing Markdown files:

- **Code blocks must always specify a language.** Use ` ```text ` for plain text or output; never leave the opening fence bare (` ``` `).
- **Table separators must have spaces around dashes.** Use `| --- | --- |`, not `|---|---|`.
- **Mermaid diagrams: use `<br/>` for line breaks, not `\n`.** `\n` inside a node or edge label renders as a literal backslash-n in some previewers (confirmed in VS Code's markdown preview) — use `<br/>` instead.

---

## Comment Style

- **Differentiate prose comments from commented-out/disabled lines.** When an
  explanatory/documentation comment sits directly above a disabled variable, config
  entry, or code statement, give the prose comment a doubled marker (`##`, or the
  language's equivalent doubled marker) and leave the disabled line itself on the
  single marker (`#`). The disabled line stays a one-character "delete the `#` to
  enable" toggle; the doubled marker signals "this is explanation, not something to
  uncomment." Example (`.env`):

  ```text
  ## Optional: only takes effect if the directory exists at startup.
  # SECRETS_DIR=/run/secrets
  ```

  Applies across all `#`-comment languages and formats: Python, PowerShell, `.env`,
  YAML, shell scripts, TOML.

---

## Available Slash Commands

| Command | Description |
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
| `/setup-workspace` | Set up or audit the workspace's Claude Code config (workspace vs global split) |
| `/brainstorming`, `/writing-plans`, `/systematic-debugging`, `/receiving-code-review`, `/feature-dev-opus`, `/security-review-opus`, `/spec-to-backlog`, `/formal-document-review`, `/extract-session-preferences` | Wrappers that run the matching skill on Opus |
