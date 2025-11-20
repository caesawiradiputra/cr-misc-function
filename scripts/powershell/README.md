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
Removes local branches that have been deleted from remote and updates protected branches (`master`, `dev`, `sit`) to match their remote counterparts.

**Purpose:** Clean up stale local branches after PRs are merged or branches are deleted remotely.

**Behavior:**
1. Fetches latest remote info with `--prune` to remove stale remote-tracking refs
2. Updates protected branches (`master`, `dev`, `sit`) by checking out and pulling each
3. Scans all local branches and deletes those not present on remote
4. Protected branches (`main`, `master`, `dev`, `sit`) are never deleted

**Usage:**

```powershell
cd cr-misc-function
./scripts/powershell/clean-branches.ps1
```

**Output:**
- Green: Successful operations
- Yellow: Branch checkouts and pull operations in progress
- Red: Failed operations (pull/checkout errors)
- Gray: Skipped branches (not present locally)

---

### reset-branches.ps1
Hard resets protected branches (`master`, `dev`, `sit`) to match their remote counterparts and force-pushes to origin. **Use with caution—this discards local commits.**

**Purpose:** Synchronize protected branches with remote when local history has diverged or needs to be discarded.

**Behavior:**
1. Fetches latest remote changes with `--prune`
2. Verifies all protected branches exist locally
3. For each protected branch (`master`, `dev`, `sit`):
   - Checks out the branch
   - Hard resets to `origin/<branch>`
   - Force-pushes to origin (overwrites remote if diverged)
4. Returns to `master` branch when complete

**⚠️ Warning:**
- **Discards all local commits** not present on remote
- **Force-pushes** can overwrite remote branch history
- Use only when you're certain local changes should be discarded
- Not recommended for shared branches with active collaborators

**Usage:**

```powershell
cd cr-misc-function
./scripts/powershell/reset-branches.ps1
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

