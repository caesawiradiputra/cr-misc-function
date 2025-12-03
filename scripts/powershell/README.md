# PowerShell Git Utilities

This folder contains helper scripts to streamline Git branch hygiene and synchronization for this repo.

## Scripts

### check-sync-set-dev.ps1
Checks whether remote `dev` and `sit` are in sync with remote `master`. If both are in sync, the script makes the local `dev` branch active (creating a tracking branch if needed) and fast-forwards it.

**Purpose:** Automate pre-development checks to ensure feature branches start from synchronized protected branches.

**Sync Rules:**
- Default: `origin/master` is an ancestor of the branch
- `-StrictEqual`: branch tip must equal `origin/master` tip exactly

**Exit Codes:**
- `0`: Success — `dev` is now the active local branch
- `2`: Not in sync — script prints which branches are behind master
- `1`: Error — git not found, not a repo, or missing remote branches

**Usage:**

```powershell
cd cr-misc-function

# Basic usage
./scripts/powershell/check-sync-set-dev.ps1

# Require exact equality
./scripts/powershell/check-sync-set-dev.ps1 -StrictEqual

# Custom remote/branch names
./scripts/powershell/check-sync-set-dev.ps1 -Remote origin -Master master -Dev dev -Sit sit

# Skip fetch if you already fetched
./scripts/powershell/check-sync-set-dev.ps1 -NoFetch
```

**Parameters:**
- `-Remote <string>`: Git remote name (default: `origin`)
- `-Master <string>`: Master branch name (default: `master`)
- `-Dev <string>`: Dev branch name (default: `dev`)
- `-Sit <string>`: SIT branch name (default: `sit`)
- `-StrictEqual`: Require exact equality to master tip
- `-NoFetch`: Skip `git fetch` (uses existing refs)

---

### clean-branches.ps1
Removes local branches that have been deleted from remote and updates protected branches (`master`, `dev`, `sit`) to match their remote counterparts. Optionally removes backup tags created by the `reset-branches.ps1` process.

**Purpose:** Clean up stale local branches after PRs are merged or branches are deleted remotely. Also optionally removes backup tags created during reset operations.

**Behavior:**
1. Fetches latest remote info with `--prune` to remove stale remote-tracking refs
2. Updates protected branches (`master`, `dev`, `sit`) by checking out and pulling each
3. Scans all local branches and deletes those not present on remote
4. Protected branches (`main`, `master`, `dev`, `sit`) are never deleted
5. (Optional) Removes all backup tags matching `backup-*-*` pattern created by reset-branches

**Parameters:**
- `-DryRun`: Preview what will be deleted without making changes
- `-NoUpdate`: Skip updating protected branches, only delete orphaned branches
- `-Force`: Skip user confirmation prompt
- `-PurgeOnly`: Only delete orphaned branches, skip protected branch updates
- `-CleanupBackupTags`: Remove backup tags created by reset-branches (pattern: `backup-<branch>-<timestamp>`)
- `-ProtectedBranches <string[]>`: Custom list of protected branches (default: main, master, dev, sit)

**Usage:**

```powershell
cd cr-misc-function

# Basic cleanup
./scripts/powershell/clean-branches.ps1

# Cleanup with backup tag removal
./scripts/powershell/clean-branches.ps1 -CleanupBackupTags

# Preview changes without executing
./scripts/powershell/clean-branches.ps1 -DryRun

# Force cleanup without confirmation
./scripts/powershell/clean-branches.ps1 -Force

# Cleanup backup tags only
./scripts/powershell/clean-branches.ps1 -PurgeOnly -CleanupBackupTags -Force
```

**Output:**
- Green: Successful operations
- Yellow: Branch checkouts and pull operations in progress
- Red: Failed operations (pull/checkout errors)
- Gray: Skipped branches (not present locally)

---

### reset-branches.ps1
Hard resets protected branches (`master`, `dev`, `sit`) to match their remote counterparts and force-pushes to origin. **Use with caution—this discards local commits.** Creates backup tags for recovery containing the commit ID for easy identification.

**Purpose:** Synchronize protected branches with remote when local history has diverged or needs to be discarded. Backup tags help identify the exact commit being saved.

**Backup Tag Naming:**
- Format: `backup-<branch>-<commit-id>-<timestamp>`
- Example: `backup-master-a1b2c3d4-20250103-140530`
- Branches already synchronized with remote are **skipped** (not backed up)

**Behavior:**
1. Fetches latest remote changes with `--prune`
2. Gets commit IDs for each protected branch from remote
3. For each protected branch (`master`, `dev`, `sit`):
   - Compares local and remote commit IDs
   - **Skips backup if already synchronized** (IDs match)
   - Creates backup tag including commit ID if different
4. Verifies all protected branches exist locally
5. For each protected branch:
   - Checks out the branch
   - Hard resets to `origin/<branch>`
   - Force-pushes to origin (overwrites remote if diverged)
6. Returns to `master` branch when complete

**⚠️ Warning:**
- **Discards all local commits** not present on remote
- **Force-pushes** can overwrite remote branch history
- Use only when you're certain local changes should be discarded
- Not recommended for shared branches with active collaborators

**Parameters:**
- `-DryRun`: Preview operations without making changes
- `-NoBackup`: Skip backup tag creation (not recommended)
- `-Force`: Skip user confirmation prompt

**Usage:**

```powershell
cd cr-misc-function

# Standard reset with backup tags
./scripts/powershell/reset-branches.ps1

# Preview changes without executing
./scripts/powershell/reset-branches.ps1 -DryRun

# Force reset without confirmation
./scripts/powershell/reset-branches.ps1 -Force

# Reset without creating backups (not recommended)
./scripts/powershell/reset-branches.ps1 -NoBackup -Force
```

**Output Example:**
```
Creating backup tags...
  [OK] Created tag: backup-master-a1b2c3d4-20250103-140530
  [SKIP] Branch 'dev' (ID: b2c3d4e5) - already synchronized
  [OK] Created tag: backup-sit-c3d4e5f6-20250103-140530
  Summary: 2 created, 1 skipped
```

**Exit Codes:**
- `0`: Success — all branches reset and pushed
- `1`: Error — fetch failed, reset failed, or push failed

**Common Use Cases:**
- Local protected branch accidentally modified
- Need to discard experimental changes on `dev`/`sit`
- Recovering from merge conflicts by adopting remote state
- Synchronizing after force-push to remote

---

## Prerequisites

- Windows PowerShell 5.1+ or PowerShell Core 7+
- Git installed and available on PATH
- Run scripts from inside the Git repository (this repo)
- Appropriate permissions to push to remote (for `reset-branches.ps1`)

## Safety Tips

- **Always review** what branches will be modified before running scripts
- Use `clean-branches.ps1` regularly to maintain hygiene
- Use `reset-branches.ps1` **only when you understand the consequences**
- Consider backing up important local changes with `git stash` before running reset operations
- If your remote is not `origin`, pass `-Remote <name>` where supported
- If your mainline is not `master`, pass `-Master <name>` where supported
- Use `-NoFetch` for offline checks when you know your refs are up to date

## Workflow Examples

**Weekly branch cleanup:**
```powershell
# Clean up merged feature branches
./scripts/powershell/clean-branches.ps1
```

**Before starting new feature:**
```powershell
# Ensure dev/sit are synced with master
./scripts/powershell/check-sync-set-dev.ps1
```

**Recover from accidental commits on protected branch:**
```powershell
# Hard reset to match remote (⚠️ destroys local changes)
./scripts/powershell/reset-branches.ps1
```

