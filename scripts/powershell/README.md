# PowerShell Scripts – Git Branch Management & Environment Utilities

This folder contains PowerShell scripts for streamlining Git workflow, template synchronization, and environment management.

> Running Claude Code / your IDE inside WSL2 or another Linux shell instead of
> native Windows? Every script here has a bash port in
> [`../bash/`](../bash/README.md) with the same name, flags, and behavior —
> use whichever matches the shell actually running the session (see the
> global `~/.claude/CLAUDE.md` "Environment" section for how to tell).

## Overview

| Script | Purpose | Risk Level |
| -------- | --------- | ----------- |
| `git-check-sync-set-dev.ps1` | Verify dev/sit sync with master, set active branch | ✅ Safe |
| `dev-check_python_usage.ps1` | Display top Python processes by CPU | ✅ Safe |
| `git-create-clean-branch.ps1` | Cherry-pick filtered commits to create focused branch | ✅ Safe |
| `git-rebase-branch.ps1` | Interactive rebase of feature branch onto base | ⚠️ Caution |
| `git-clean-branches.ps1` | Remove stale local branches, optionally clean backup tags | ⚠️ Caution |
| `git-reset-branches.ps1` | Force-reset protected branches to remote (discards local) | 🔴 Destructive |
| `chat-sync-github-instructions.ps1` | Sync .github templates across projects | ✅ Safe |
| `chat-update-template-from-workspace.ps1` | Update reference template from workspace improvements | ✅ Safe |
| `dev-remove-base-only-packages.ps1` | Display conda removal command for base-only packages | ✅ Safe |

---

## Git Branch Management

### git-check-sync-set-dev.ps1

Verifies that remote `dev` and `sit` branches are in sync with `master`, then activates the local `dev` branch.

**Purpose:** Automate pre-development setup to ensure feature branches start from synchronized protected branches.

**Sync Detection:**

- Default: Branch is ancestor of `origin/master` (normal state)
- `-StrictEqual`: Branch tip equals `origin/master` exactly (stricter check)

**Behavior:**

1. Fetches latest remote refs (unless `-NoFetch`)
2. Tests if `dev` is ancestor of `master`
3. Tests if `sit` is ancestor of `master`
4. If both in sync: creates local `dev` branch and fast-forwards it
5. Returns exit code indicating sync status

**Usage:**

```powershell
cd cr-misc-function

# Basic check and set dev branch
./scripts/powershell/git-check-sync-set-dev.ps1

# Require exact tip equality
./scripts/powershell/git-check-sync-set-dev.ps1 -StrictEqual

# Custom branch names
./scripts/powershell/git-check-sync-set-dev.ps1 -Remote origin -Master main -Dev development -Sit staging

# Skip fetch (use cached refs)
./scripts/powershell/git-check-sync-set-dev.ps1 -NoFetch
```

**Parameters:**

- `-Remote <string>`: Remote name (default: `origin`)
- `-Master <string>`: Master branch name (default: `master`)
- `-Dev <string>`: Dev branch name (default: `dev`)
- `-Sit <string>`: SIT branch name (default: `sit`)
- `-StrictEqual`: Require exact commit equality to master
- `-NoFetch`: Skip `git fetch`

**Exit Codes:**

- `0`: Success — dev is now active, branches are synced
- `2`: Not in sync — one or more branches behind master
- `1`: Error — git failure, not a repo, or missing branches

---

### git-create-clean-branch.ps1

Cherry-picks commits from a feature branch, filtering by file paths to create a focused, clean branch.

**Purpose:** Isolate changes to specific files when creating a PR, leaving unrelated changes behind. Useful for extracting feature changes from a messy work-in-progress branch.

**Workflow:**

1. Lists commits from feature branch (displayed in reverse: oldest → newest)
2. Filters commits that touched specified file paths
3. Creates new `<branch>-clean` branch at base
4. Cherry-picks filtered commits onto clean branch
5. Handles conflicts with guidance

**Usage:**

```powershell
cd cr-misc-function

# Cherry-pick commits that touch specific paths
./scripts/powershell/git-create-clean-branch.ps1 -FeatureBranch feature/payment -BaseBranch master -FilePaths @("app/payment/*", "tests/payment/*")

# Without fetching
./scripts/powershell/git-create-clean-branch.ps1 -FeatureBranch feature/auth -BaseBranch develop -FilePaths @("app/auth/*") -SkipFetch
```

**Parameters:**

- `-FeatureBranch <string>`: Source branch to cherry-pick from (required)
- `-BaseBranch <string>`: Base branch for new clean branch (default: `master`)
- `-FilePaths <string[]>`: File path patterns to filter commits (required)
- `-SkipFetch`: Don't fetch from remote

**Behavior:**

- Displays commits in reverse chronological order (oldest first)
- Shows which commits touched the specified paths
- Creates branch named `<feature>-clean`
- Cherry-picks commits sequentially
- Reports conflicts if cherry-pick fails

**Exit Codes:**

- `0`: Success — clean branch created with all cherry-picks applied
- `1`: Error — invalid branch, fetch failed, or cherry-pick failed

---

### git-rebase-branch.ps1

Interactively rebases a feature branch onto its base branch to prepare for merge.

**Purpose:** Update feature branch with latest base branch changes before merging, linearizing history and resolving conflicts early.

**Workflow:**

1. Fetches latest remote changes (unless `-SkipFetch`)
2. Displays commits in feature branch
3. Checks out feature branch
4. Rebases onto base branch
5. Handles conflicts with user guidance

**Usage:**

```powershell
cd cr-misc-function

# Rebase feature onto master
./scripts/powershell/git-rebase-branch.ps1 -FeatureBranch feature/auth -BaseBranch master

# Rebase onto develop, skip fetch
./scripts/powershell/git-rebase-branch.ps1 -FeatureBranch my-feature -BaseBranch develop -SkipFetch
```

**Parameters:**

- `-FeatureBranch <string>`: Branch to rebase (required)
- `-BaseBranch <string>`: Target base to rebase onto (default: `master`)
- `-SkipFetch`: Don't fetch before rebase

**Behavior:**

- Checks if feature branch exists locally/remotely
- Fetches remote if not skipped
- Initiates interactive rebase
- User resolves conflicts as prompted
- Returns to original branch if rebase cancelled

**Exit Codes:**

- `0`: Success — rebase completed
- `1`: Error — branch not found, fetch failed, or rebase failed

---

## Branch Hygiene & Synchronization

### git-clean-branches.ps1

Removes stale local branches and updates protected branches. Optionally removes backup tags.

**Purpose:** Maintain clean local branch list after PRs are merged remotely. Also manages backup tags created by `git-reset-branches.ps1`.

**Behavior:**

1. Fetches latest remote with `--prune` (removes stale remote-tracking refs)
2. Optionally updates protected branches (`master`, `dev`, `sit`) by pulling latest
3. scans all local branches
4. Deletes branches not found on remote
5. Skips protected branches (never deletes: main, master, dev, sit)
6. Optionally removes all `backup-*-*-*` tags

**Protected Branches (customizable):**

- Default: `main`, `master`, `dev`, `sit`
- Pass `-ProtectedBranches` to override

**Usage:**

```powershell
cd cr-misc-function

# Basic cleanup (no protected branch update)
./scripts/powershell/git-clean-branches.ps1

# Update protected branches and cleanup
./scripts/powershell/git-clean-branches.ps1 -NoUpdate:$false

# Remove stale branches and backup tags
./scripts/powershell/git-clean-branches.ps1 -CleanupBackupTags

# Preview without making changes
./scripts/powershell/git-clean-branches.ps1 -DryRun

# Skip confirmation
./scripts/powershell/git-clean-branches.ps1 -Force

# Only cleanup orphaned branches, don't touch protected branches
./scripts/powershell/git-clean-branches.ps1 -PurgeOnly
```

**Parameters:**

- `-DryRun`: Show what would be deleted without making changes
- `-NoUpdate`: Skip pulling protected branches (only delete orphaned branches)
- `-Force`: Skip confirmation prompt
- `-PurgeOnly`: Only delete orphaned branches, skip protected branch pulls
- `-CleanupBackupTags`: Also remove backup tags (pattern: `backup-*-*-*`)
- `-ProtectedBranches <string[]>`: Custom protected branch names

**Output Color Coding:**

- 🟢 Green: Deleted branches
- 🟡 Yellow: Protected branch updates (checkout, pull)
- 🔴 Red: Failed operations
- ⚪ Gray: Skipped branches (not found locally)

**Exit Codes:**

- `0`: Success — cleanup complete
- `1`: Error — fetch, checkout, or pull failed

---

### git-reset-branches.ps1

Force-resets protected branches to match remote. **⚠️ Destructive—discards local commits.** Creates backup tags for recovery.

**Purpose:** Synchronize protected branches when local history diverged or needs discarding. Backup tags allow recovery of previous commit state.

**⚠️ DESTRUCTIVE OPERATION:**

- Discards all local commits not on remote
- Force-pushes to remote (overwrites remote history if diverged)
- Use only when certain local changes should be thrown away
- Not recommended for shared branches with active collaborators

**Backup Tag Format:**

- `backup-<branch>-<short-commit-id>-<timestamp>`
- Example: `backup-master-a1b2c3d4-20250103-140530`
- Skips backup if branch already synchronized with remote

**Workflow:**

1. Fetches latest remote refs with `--prune`
2. Gets remote commit IDs for each protected branch
3. For each protected branch:
   - Compares local vs remote commit ID
   - **Skips if already synchronized** (no backup needed)
   - Creates backup tag if different
4. For each protected branch:
   - Checks out the branch
   - Hard resets to `origin/<branch>`
   - Force-pushes to origin
5. Returns to `master` branch

**Usage:**

```powershell
cd cr-misc-function

# Reset with backup tags (safe)
./scripts/powershell/git-reset-branches.ps1

# Preview changes
./scripts/powershell/git-reset-branches.ps1 -DryRun

# Force reset without confirmation
./scripts/powershell/git-reset-branches.ps1 -Force

# Reset without creating backups (NOT recommended)
./scripts/powershell/git-reset-branches.ps1 -NoBackup -Force
```

**Parameters:**

- `-DryRun`: Preview operations without executing
- `-NoBackup`: Skip backup tag creation (not recommended)
- `-Force`: Skip confirmation prompts

**Example Output:**

```text
Creating backup tags...
  [OK] Created tag: backup-master-a1b2c3d4-20250103-140530
  [SKIP] Branch 'dev' (ID: b2c3d4e5) - already synchronized
  [OK] Created tag: backup-sit-c3d4e5f6-20250103-140530
  Summary: 2 created, 1 skipped

Resetting branches...
  [PROGRESS] Checking out 'master'...
  [OK] Reset master to origin/master
  [OK] Force-pushed master to origin
  ...
```

**Exit Codes:**

- `0`: Success — all branches reset and synced
- `1`: Error — fetch, reset, or push failed

**When to Use:**

- Local protected branch accidentally modified
- Discarding experimental commits on dev/sit
- Recovering from merge conflicts by adopting remote state
- Syncing after remote force-push

---

## .github Template Synchronization

### chat-sync-github-instructions.ps1

Syncs `.github\instructions` and `.github\prompts` with a centralized reference template.

**Purpose:** Maintain consistent `.github` files across all projects from a single source-of-truth template. Enables cross-project distribution of standardized workflows, instructions, and prompts.

**Usage from Any Workspace:**
The script can be called from any workspace to sync with the centralized reference template:

```powershell

# From any workspace - syncs .github folder to reference template

cd C:\Users\203715\Documents\Repo\da-ndf4w-1p5c-monitoring-streamlit\da-ndf4w-1p5c-monitoring-streamlit
C:\Users\203715\Documents\Repo\cr-misc-function\cr-misc-function\scripts\powershell\chat-sync-github-instructions.ps1 -Verbose

# Preview changes without applying

C:\Users\203715\Documents\Repo\cr-misc-function\cr-misc-function\scripts\powershell\chat-sync-github-instructions.ps1 -DryRun -Verbose

# Specify target workspace explicitly (optional - defaults to current directory parent)

C:\Users\203715\Documents\Repo\cr-misc-function\cr-misc-function\scripts\powershell\chat-sync-github-instructions.ps1 -TargetGitHubRoot "C:\path\to\another\workspace" -Verbose
```

**Behavior:**

1. Reads target workspace from current directory (or `-TargetGitHubRoot` parameter)
2. Looks for `.github` folder in target workspace
3. Compares files with hardcoded reference template at `C:\Users\203715\Documents\Repo\cr-misc-function\.github.template`
4. Uses SHA256 hash for fast, reliable file comparison
5. Categorizes each file:
   - **Added**: Exists in template but missing from `.github`
   - **Updated**: Exists in both but content differs (template version wins)
   - **Skipped**: Exists in both with identical content
6. Applies changes based on DryRun flag
7. Returns summary statistics and exit code

**Parameters:**

- `-TargetGitHubRoot <string>`: Workspace root where `.github` folder should be synced (defaults to parent of current working directory)
- `-DryRun`: Preview changes without applying (shows what would be added/updated/skipped)
- `-Verbose`: Print detailed output with color-coded results

**Exit Codes:**

- ` `: Success  all operations completed without errors
- `1`: Partial  operations completed but with errors encountered
- `2`: Skipped  template folder doesn't exist (no action taken)

**Common Use Cases:**

- Sync multiple projects to centralized `.github` reference
- Onboard new projects (sync their `.github` with reference template)
- Distribute `.github` updates across all projects
- Verify `.github` consistency across organization
- Automated sync in CI/CD pipeline or scheduled tasks

**Workflow Integration:**

Check what reference template differs:

```powershell

# From any workspace

cd C:\Users\203715\Documents\Repo\some-project\some-project
C:\Users\203715\Documents\Repo\cr-misc-function\cr-misc-function\scripts\powershell\chat-sync-github-instructions.ps1 -DryRun -Verbose
```

Apply reference template updates:

```powershell
C:\Users\203715\Documents\Repo\cr-misc-function\cr-misc-function\scripts\powershell\chat-sync-github-instructions.ps1 -Verbose
```

---

## Environment & Package Management

### dev-remove-base-only-packages.ps1

Displays the command to remove utility packages cluttering the conda environment.

**Purpose:** Analyze the current conda environment and display a ready-to-run command that removes packages (poetry, pipdeptree, pip-audit, etc.) that clutter project-specific environments.

**Base-Only Packages Identified:**

- `poetry` & `poetry-core` — Dependency and package management tools
- `pipdeptree` — Dependency tree visualization
- `pip-audit` — Pip package security auditing

**Optional Packages (with flags):**

- `jupyter`, `jupyterlab` — Notebook environments (use `-IncludeJupyter`)
- `ipython` — Interactive Python shell (use `-IncludeIPython`)

**Usage:**

```powershell
cd cr-misc-function

# Display the removal command
./scripts/powershell/dev-remove-base-only-packages.ps1

# Also identify Jupyter packages
./scripts/powershell/dev-remove-base-only-packages.ps1 -IncludeJupyter

# Identify all including IPython
./scripts/powershell/dev-remove-base-only-packages.ps1 -IncludeJupyter -IncludeIPython
```

**Parameters:**

- `-IncludeJupyter`: Also identify `jupyter` and `jupyterlab` packages
- `-IncludeIPython`: Also identify `ipython` package

**Behavior:**

1. Checks conda is available and identifies the active environment
2. Defines list of base-only packages to check
3. Scans the environment to find which packages are installed
4. Displays packages that will be removed
5. Shows the exact conda command to run
6. **You decide when to run it** — just copy and paste the command

**Example Output:**

```text
[*] Checking conda environment
[OK] Active environment: cr-misc-function-env

[*] Identifying packages to remove
[INFO] Target packages: poetry, poetry-core, pipdeptree, pip-audit

[*] Checking installed packages
[SCAN] Found 3 package(s) to remove:
  - poetry
  - poetry-core
  - pipdeptree

[*] Command to execute

conda remove --yes --quiet poetry poetry-core pipdeptree

=================================================
     Ready to Run
=================================================

[OK] Copy and run the command above when ready
[INFO] This will remove 3 package(s) from your environment
```

**Exit Codes:**

- `0`: Success — command displayed
- `1`: Error — conda not found or script error

**When to Use:**

- After setting up new project environment
- Before creating environment backups or sharing environments
- To reduce environment.yml bloat before committing

---

## System Utilities

### dev-check_python_usage.ps1

Displays top 5 Python processes by CPU usage.

**Purpose:** Quick view of which Python processes are consuming the most CPU, useful for monitoring background tasks and scripts.

**Behavior:**

- Lists processes named "python.*" (python.exe, pythonw.exe, etc.)
- Filters to processes with CPU > 0% usage
- Sorts by CPU usage (highest first)
- Shows: Process ID, CPU %, Memory usage (WorkingSet), Runtime

**Usage:**

```powershell
# Run from anywhere
./scripts/powershell/dev-check_python_usage.ps1
```

**Example Output:**

```text
Id     CPU WorkingSet Runtime
--     --- ---------- -------
12345  5.2 256000000  00:15:30
54321  2.1 128000000  00:08:15
...
```

**No Parameters:** Runs as-is, no configuration needed.

**Exit Codes:**

- `0`: Success — processes listed

**When to Use:**

- Check if Python processes are running
- Identify resource-hungry scripts
- Monitor background task CPU usage

---

## Prerequisites & Setup

**System Requirements:**

- Windows PowerShell 5.1+ or PowerShell Core 7+
- Git installed and on PATH
- For conda scripts: Conda/Miniconda/Anaconda installed
- Run scripts from inside the repository (have `.git/` folder in parent)

**Before Running Destructive Scripts:**

1. Review the script's behavior with `-DryRun` first
2. Backup important uncommitted work (`git stash`)
3. Understand the exit codes and error handling
4. Test on a feature branch before running on protected branches

---

## Safety Practices

| Script | Before Running | Risk | Recovery |
| -------- | --- | --- | --- |
| `git-clean-branches.ps1` | Use `-DryRun` | Low | Can restore from remote |
| `git-reset-branches.ps1` | Use `-DryRun`, backup commits | High | Use `git reflog` + backup tags |
| `git-rebase-branch.ps1` | Use `-SkipFetch`, backup local | Medium | Use `git reflog` to restore |
| `git-create-clean-branch.ps1` | Verify file paths filter | Low | Delete branch if wrong commits |
| Others | No special precaution | None | N/A |

---

## Common Workflows

**Daily Development:**

```powershell
# Check before starting work
./scripts/powershell/git-check-sync-set-dev.ps1

# Create clean feature branch focusing on specific files
./scripts/powershell/git-create-clean-branch.ps1 -FeatureBranch my-work -FilePaths @("app/auth/*")

# See what Python is running
./scripts/powershell/dev-check_python_usage.ps1
```

**Weekly Maintenance:**

```powershell
# Clean up stale branches
./scripts/powershell/git-clean-branches.ps1

# Update .github templates across projects
./scripts/powershell/chat-sync-github-instructions.ps1
```

**PR Preparation:**

```powershell
# Rebase feature onto latest master
./scripts/powershell/git-rebase-branch.ps1 -FeatureBranch feature/payment

# Create clean version focusing on payment changes only
./scripts/powershell/git-create-clean-branch.ps1 -FeatureBranch feature/payment-clean -FilePaths @("app/payment/*", "tests/payment/*")
```

**Emergency Recovery:**

```powershell
# See what's backed up
git tag | Select-String "backup-"

# Check commit state before reset
./scripts/powershell/git-reset-branches.ps1 -DryRun

# Reset to match remote with backups
./scripts/powershell/git-reset-branches.ps1 -Force
```

---

## Troubleshooting

**Script won't run ("cannot be loaded because running scripts is disabled"):**

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**Git command not found:**

- Install Git: <https://git-scm.com/download/win>
- Add to PATH: `C:\Program Files\Git\cmd`

**Conda command not found:**

- Install Conda: <https://docs.conda.io/projects/conda/en/latest/user-guide/install/windows.html>
- Restart terminal after installing

**Rebase conflicts:**

1. Open conflicted files in editor
2. Resolve conflicts (look for `<<<<<<<` markers)
3. Stage resolved files: `git add <file>`
4. Continue rebase: `git rebase --continue`
5. Or abort: `git rebase --abort`

**Reset went wrong:**

```powershell
# View reflog to find previous state
git reflog

# Restore to ref (e.g., HEAD@{5})
git reset --hard HEAD@{5}

# Or use backup tag
git reset --hard backup-master-a1b2c3d4-20250103-140530
```

---

## Logging

Scripts that perform destructive operations (`git-clean-branches`, `git-reset-branches`) create timestamped logs in the `logs/` folder:

- `git-clean-branches-*.log`
- `git-reset-branches-*.log`

Check logs for detailed operation timestamp, affected branches, and error details.

```text
