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
$path = "C:\Users\203715\Documents\Repo\project"
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

## Project Standards

- **Package manager**: uv (not pip directly). When a repository uses uv/pyproject.toml
  for local development alongside shared requirements files used by CI or Docker, manage
  local development dependencies through pyproject.toml/uv rather than modifying the
  shared requirements file solely to resolve local dependency conflicts.
- **Python style**: Google-style docstrings, PEP 8, snake_case functions/variables, PascalCase classes
- **Commit format**: Conventional Commits + gitmoji (see `/commit`)
- **Type hints**: Match project Python version — check `pyproject.toml` first

---

## Execution Discipline

Rules learned from a real incident (DA-1772 session, 2026-08-03): a Write call
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
  (Broadened 2026-08-12, DA-1768 session: the same rename silently missed a
  historical variant node, a final-table column, and a retired-but-not-removed
  column — three separate misses in one session, none of them prose claims.
  Broadened again 2026-08-21, da-privis pull_data session: making a retry
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
  da-privis session: a new readiness-check script addressed MaxCompute tables
  as `schema.table` because the SDK exposed a `schema=` parameter, while the
  pipeline's own SQL in the same repo had been addressing those identical
  tables as `project.table` all along. Three tables silently reported MISSING
  while holding data; the working reference was in the repo the whole time.)
- **Before concluding a git branch or ref doesn't exist, fetch first.** Local
  branch listings can be stale — `git branch -a` only shows what's already
  been fetched, not what actually exists on the remote. Run `git fetch --all
  --prune` (or at least `git fetch <remote>`) before declaring a branch
  absent or unavailable. (Added 2026-09-04, da-bfi-lakehouse-platform
  session: told the user "there's no develop branch" after checking only
  local refs; `origin/develop` existed the whole time but had never been
  fetched in this clone.)
- **Stick to the established focus root in a multi-root workspace.** Every
  folder under `C:\Users\203715\Documents\Repo\` is a non-git umbrella
  containing the real git repos one level down (each with its own
  `.code-workspace`, and sometimes its own trimming `ruff.toml`/`CLAUDE.md`).
  A Claude Code session's cwd is pinned to the umbrella (`folders[0]`) for
  the whole session regardless of which file is open or `@`-mentioned. Once
  a conversation is clearly focused on one sub-repo — by an explicit
  `@<repo>/` mention or by several turns of edits/reads all under one path —
  keep using that repo directly for file lookups; don't fall back to
  searching sibling repos or the umbrella unless the user asks about a
  different repo or the file genuinely isn't found. (Added 2026-09-09,
  da-obligor session: user flagged me re-searching the wrong root mid-
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
  the other. (Added 2026-09-10, da-lakehouse session: both issues stacked on
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
