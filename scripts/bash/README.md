# Bash Scripts – Git Branch Management & Environment Utilities

Bash ports of every script in [`../powershell/`](../powershell/README.md), for
sessions where Claude Code (or the IDE's integrated terminal hosting it) is
actually running on Linux/WSL2/another POSIX shell instead of native Windows
— see the global `~/.claude/CLAUDE.md` "Environment" section for how to tell
which one a given session is. Same names (kebab-case, `.sh` instead of
`.ps1`), same flags (as `--kebab-case` long options instead of PowerShell's
`-PascalCase` parameters), same behavior, same risk levels. Detailed
per-script docs (parameters, workflow, exit codes, conflict handling) live in
the PowerShell README linked above — read it for the *what*; run `<script>
--help` for the bash *how*.

Shared helpers live in `modules/git-script-helpers.sh` (the bash port of
`../powershell/modules/GitScriptHelpers.psm1`): `write_step`, `write_info`,
`write_warn`, `write_success`, `write_error_msg`, `confirm_action`.

`validate.sh` syntax-checks (`bash -n`, no execution) the git-*.sh scripts
that depend on the shared helpers module — the bash equivalent of
`modules/_validate.ps1`'s PowerShell-AST check.

## Overview

| Script | Purpose | Risk Level |
| -------- | --------- | ----------- |
| `git-check-sync-set-dev.sh` | Verify dev/sit sync with master, set active branch | ✅ Safe |
| `dev-check-python-usage.sh` | Display top Python processes by CPU | ✅ Safe |
| `git-create-clean-branch.sh` | Cherry-pick filtered commits to create focused branch | ✅ Safe |
| `git-rebase-branch.sh` | Interactive rebase of feature branch onto base | ⚠️ Caution |
| `git-clean-branches.sh` | Remove stale local branches, optionally clean backup tags | ⚠️ Caution |
| `git-reset-branches.sh` | Force-reset protected branches to remote (discards local) | 🔴 Destructive |
| `git-init-feature.sh` | Scaffold a new feature branch off a synced base | ✅ Safe |
| `git-workflow.sh` | Orchestrator dispatching to the other `git-*.sh` scripts | Varies by action |
| `git-check-branch-merged.sh` | Read-only scan for branches already merged/safe to delete | ✅ Safe |
| `chat-sync-claude-context.sh` | Sync project `CLAUDE/` → global `~/.claude` | ✅ Safe |
| `chat-sync-copilot-context.sh` | Sync project `.copilot/` → global `~/.copilot` | ✅ Safe |
| `chat-sync-qoder-context.sh` | Sync project `QODER.md`/`QODER/` → global `~/.qoder` | ✅ Safe |
| `chat-sync-github-instructions.sh` | Sync `.github` templates across projects | ✅ Safe |
| `chat-update-template-from-workspace.sh` | Update reference `.github` template from workspace improvements | ✅ Safe |
| `chat-update-claude-template-from-workspace.sh` | Update this repo's `CLAUDE/` template from a workspace's global commands | ✅ Safe |
| `chat-update-qoder-template-from-workspace.sh` | Update this repo's `QODER/` template from a workspace's global config | ✅ Safe |
| `conda-py311-init-env.sh` | Initialize/activate the project's Python 3.11 conda env | ✅ Safe |
| `conda-py39-init-env.sh` | Initialize/activate the project's Python 3.9 conda env | ✅ Safe |
| `dev-remove-base-only-packages.sh` | Display conda removal command for base-only packages | ✅ Safe |
| `dev-migrate-conda-poetry-to-uv.sh` | Migrate a conda/poetry project to uv | ⚠️ Caution |

---

## Notes on the port

- Hardcoded Windows user paths (`C:\Users\203715\...`) in the originals
  become `$HOME`-relative or auto-detected paths here — a WSL2 session and
  its "same machine" Windows side are different filesystems with different
  home directories, so a path that's correct on one side is not correct on
  the other just because it's the same physical machine.
- `Confirm-Action`/`confirm_action` uses bash's own exit-code convention:
  `0` = confirmed, `1` = cancelled — the inverse of PowerShell's `-not
  (Confirm-Action ...)` check, so call sites read `if ! confirm_action ...;
  then ...; fi`.
- Every script preserves the original's exact confirmation prompts, safety
  guards, and exit codes — these were ported for behavioral fidelity, not
  rewritten or "improved" in translation. `git-reset-branches.sh` in
  particular preserves every safeguard from the destructive original
  line-for-line (see its header comment for the full list).
