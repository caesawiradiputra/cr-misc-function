<#
.SYNOPSIS
    Cleans up local Git branches that have been deleted on the remote.

.DESCRIPTION
    This script removes local Git branches that no longer exist on the remote repository.
    It can optionally update protected branches and remove backup tags created by reset-branches.

.PARAMETER DryRun
    Preview changes without deleting branches. Use to review what will be deleted.

.PARAMETER NoUpdate
    Skip updating protected branches from remote.

.PARAMETER Force
    Skip user confirmation prompt.

.PARAMETER PurgeOnly
    Only delete orphaned branches; skip protected branch updates.

.PARAMETER CleanupBackupTags
    Remove backup tags created by the reset-branches script.

.PARAMETER ProtectedBranches
    Branches that should never be deleted. Default: main, master, dev, sit
#>
param(
    [switch]$DryRun = $false,
    [switch]$NoUpdate = $false,
    [switch]$Force = $false,
    [switch]$PurgeOnly = $false,
    [switch]$CleanupBackupTags = $false,
    [string[]]$ProtectedBranches = @("main", "master", "dev", "sit")
)

# Import shared helpers
Import-Module (Join-Path $PSScriptRoot "modules\GitScriptHelpers.psm1") -Force

# ============================================================================
# SETUP & INITIALIZATION
# ============================================================================

# Setup logging - Create timestamped log file in logs/ subdirectory
$timestamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$logFile = Join-Path $PSScriptRoot "logs\clean-branches-$timestamp.log"
$logDir = Split-Path $logFile
if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
}


# Initialize operation counters and collections
$deletedCount = 0              # Branches successfully deleted
$keptCount = 0                 # Branches kept (exist on remote)
$protectedCount = 0            # Branches protected from deletion
$updatedCount = 0              # Protected branches successfully updated
$failedCount = 0               # Operations that failed
$backupTagsDeletedCount = 0    # Backup tags cleaned up
$branchesToDelete = [System.Collections.Generic.List[string]]::new()  # Branches marked for deletion
$backupTagsToDelete = [System.Collections.Generic.List[string]]::new() # Backup tags marked for deletion

Write-Host "=============================================================" -ForegroundColor Cyan
Write-Host "Branch Cleanup Utility" -ForegroundColor Cyan
Write-Host "=============================================================" -ForegroundColor Cyan
Write-Host ""

# Display active execution modes
if ($PurgeOnly) {
    Write-Info "PURGE ONLY MODE - Will only delete orphaned branches"
    Write-Host ""
}

if ($CleanupBackupTags) {
    Write-Info "BACKUP TAG CLEANUP - Will remove backup tags created by reset-branches"
    Write-Host ""
}

if ($DryRun) {
    Write-Info "DRY RUN MODE - No branches will be deleted"
    Write-Host ""
}

if ($NoUpdate) {
    Write-Warn "Protected branch updates are DISABLED"
    Write-Host ""
}

# Validate we are inside a Git repository
$repoRoot = git rev-parse --show-toplevel 2>&1 | Where-Object { $_ -is [string] }
if ($LASTEXITCODE -ne 0) {
    Write-ErrorMsg "Not inside a Git repository. Please run from within a Git working directory."
    exit 1
}
Write-Info "Repository: $repoRoot"
Write-Host ""

# User confirmation checkpoint - Require explicit 'yes' to proceed (unless -Force)
if (-not $Force) {
    Write-Host "[WARNING] This script will DELETE local branches!" -ForegroundColor Red
    Write-Host "This will:" -ForegroundColor Red
    if (-not $PurgeOnly) {
        Write-Host "  - Update protected branches ($($ProtectedBranches -join ', '))" -ForegroundColor Red
    }
    Write-Host "  - Delete branches not on remote" -ForegroundColor Red
    if ($CleanupBackupTags) {
        Write-Host "  - Delete backup tags created by reset-branches" -ForegroundColor Red
    }
    Write-Host "  - Protect: $($ProtectedBranches -join ', ')" -ForegroundColor Red
    Write-Host ""

    if (-not (Confirm-Action -Prompt "Type 'yes' to continue" -Style Explicit)) {
        exit 0
    }

    Write-Host ""
}

# Start logging after confirmation (avoids orphan log files on cancellation)
Start-Transcript -Path $logFile -Append

# ============================================================================
# PHASE 1: SYNC WITH REMOTE
# ============================================================================

# Fetch latest changes and prune deleted branches from remote tracking
Write-Info "Fetching latest changes from origin (with prune)"
if ($DryRun) {
    Write-Host "[DRY RUN] git fetch origin --prune" -ForegroundColor Gray
} else {
    git fetch origin --prune 2>&1 | Out-Null

    if ($LASTEXITCODE -ne 0) {
        Write-ErrorMsg "Failed to fetch from origin"
        Stop-Transcript
        exit 1
    }
}

Write-Success "Fetch complete"
Write-Host ""

# Gather current branch state
Write-Info "Gathering branch information"
$localBranches = git branch --format='%(refname:short)' | ForEach-Object { $_.Trim() }

# Extract remote branch names (strip 'origin/' prefix, filter symbolic HEAD ref)
$remoteBranches = git branch -r --format='%(refname:short)' | ForEach-Object {
    ($_ -replace "^origin/", "").Trim()
} | Where-Object { $_ -ne "HEAD" }

# Guard: abort if no remote branches found (prevents accidental deletion of all local branches)
if ($null -eq $remoteBranches -or @($remoteBranches).Count -eq 0) {
    Write-ErrorMsg "No remote branches found. Aborting to prevent accidental deletion of all local branches."
    Stop-Transcript
    exit 1
}

# ============================================================================
# PHASE 2: UPDATE PROTECTED BRANCHES (optional)
# ============================================================================

# Sync protected branches with latest remote changes (unless -NoUpdate or -PurgeOnly)
if (-not $NoUpdate -and -not $PurgeOnly) {
    Write-Info "Updating protected branches"

    $branchesToUpdate = $ProtectedBranches
    $originalBranch = (git rev-parse --abbrev-ref HEAD 2>&1 | Where-Object { $_ -is [string] })
    if (-not $originalBranch) { $originalBranch = (git branch --show-current).Trim() }
    $branchChanged = $false

    foreach ($branch in $branchesToUpdate) {
        if ($localBranches -contains $branch) {
            Write-Host "  Updating '$branch'..." -ForegroundColor Gray

            if ($DryRun) {
                Write-Host "    [DRY RUN] git checkout $branch; git pull origin $branch" -ForegroundColor Gray
            } else {
                # Checkout branch and pull latest changes
                git checkout $branch 2>&1 | Out-Null

                if ($LASTEXITCODE -eq 0) {
                    $branchChanged = $true
                    git pull origin $branch 2>&1 | Out-Null

                    if ($LASTEXITCODE -eq 0) {
                        Write-Success "  Updated '$branch'"
                        $updatedCount++
                    }
                    else {
                        Write-Warn "  Failed to pull '$branch'"
                        $failedCount++
                    }
                }
                else {
                    # Checkout failed — likely checked out in a worktree or has conflicts
                    Write-Warn "  Failed to checkout '$branch' (may be in use by a worktree)"
                    $failedCount++
                }
            }
        }
        else {
            Write-Info "  Skipping '$branch' (not found locally)"
        }
    }

    # Restore original branch if we changed it during updates
    if ($branchChanged -and $originalBranch -and -not $DryRun) {
        git checkout $originalBranch 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-Info "  Restored to original branch '$originalBranch'"
        } else {
            Write-Warn "  Could not restore to '$originalBranch'"
        }
    }

    Write-Host ""
}

# ============================================================================
# PHASE 3: IDENTIFY ORPHANED BRANCHES
# ============================================================================

# Classify branches: protected, keep (on remote), or delete (orphaned)
Write-Info "Checking local branches for cleanup"

foreach ($branch in $localBranches) {
    if ($ProtectedBranches -contains $branch) {
        # Protected branches are never deleted
        Write-Host "  [PROTECTED] '$branch'" -ForegroundColor Blue
        $protectedCount++
        continue
    }

    if ($remoteBranches -notcontains $branch) {
        # Branch exists locally but not on remote - mark for deletion
        Write-Host "  [DELETE] '$branch' (not on remote)" -ForegroundColor Yellow
        $branchesToDelete.Add($branch)
    }
    else {
        # Branch exists on remote - keep it
        Write-Host "  [KEEP] '$branch'" -ForegroundColor Green
        $keptCount++
    }
}

Write-Host ""

# ============================================================================
# PHASE 4: DELETE ORPHANED BRANCHES
# ============================================================================

# Preview branches to be deleted
if ($branchesToDelete.Count -gt 0) {
    Write-Host "Branches to be deleted ($($branchesToDelete.Count)):" -ForegroundColor Yellow
    foreach ($branch in $branchesToDelete) {
        Write-Host "  - $branch" -ForegroundColor DarkYellow
    }
    Write-Host ""
}

# Execute deletion (or preview in dry-run mode)
if ($branchesToDelete.Count -gt 0) {
    if ($DryRun) {
        Write-Info "DRY RUN: Would delete the following branches"
        foreach ($branch in $branchesToDelete) {
            Write-Host "  [DRY RUN] git branch -D $branch" -ForegroundColor Gray
        }
        $deletedCount = $branchesToDelete.Count
    } else {
        Write-Info "Deleting branches"
        # Guard: if current branch is marked for deletion, switch to a safe branch first
        $currentBranch = (git branch --show-current).Trim()
        if ($branchesToDelete -contains $currentBranch) {
            $safeBranch = $ProtectedBranches | Where-Object { $localBranches -contains $_ -and $_ -ne $currentBranch } | Select-Object -First 1
            if ($safeBranch) {
                Write-Warn "Current branch '$currentBranch' is marked for deletion. Switching to '$safeBranch' first."
                git checkout $safeBranch 2>&1 | Out-Null
            }
        }

        foreach ($branch in $branchesToDelete) {
            git branch -D $branch 2>&1 | Out-Null

            if ($LASTEXITCODE -eq 0) {
                Write-Success "  Deleted '$branch'"
                $deletedCount++
            }
            else {
                Write-ErrorMsg "  Failed to delete '$branch'"
                $failedCount++
            }
        }
    }
} else {
    Write-Info "No branches to delete"
}

Write-Host ""

# ============================================================================
# PHASE 5: CLEANUP BACKUP TAGS (optional)
# ============================================================================

# Remove backup tags created by the reset-branches script
if ($CleanupBackupTags) {
    Write-Info "Checking for backup tags to cleanup"

    # Get all tags matching backup-* pattern
    $allTags = git tag --list "backup-*" 2>&1 | Where-Object { $_ -is [string] } | ForEach-Object { $_.Trim() }

    if ($null -eq $allTags -or $allTags.Count -eq 0) {
        Write-Info "No backup tags found"
    } else {
        # Normalize to array (PowerShell returns string for single item)
        if ($allTags -is [string]) {
            $allTags = @($allTags)
        }

        Write-Host "Found $($allTags.Count) backup tag(s):"
        foreach ($tag in $allTags) {
            Write-Host "  [DELETE] '$tag'" -ForegroundColor Yellow
            $backupTagsToDelete.Add($tag)
        }

        Write-Host ""

        if ($DryRun) {
            Write-Info "DRY RUN: Would delete the following backup tags"
            foreach ($tag in $backupTagsToDelete) {
                Write-Host "  [DRY RUN] git tag -d $tag (local)" -ForegroundColor Gray
                Write-Host "  [DRY RUN] git push origin :refs/tags/$tag (remote)" -ForegroundColor Gray
            }
            $backupTagsDeletedCount = $backupTagsToDelete.Count
        } else {
            Write-Info "Deleting backup tags"
            foreach ($tag in $backupTagsToDelete) {
                # Delete local tag first
                git tag -d $tag 2>&1 | Out-Null
                if ($LASTEXITCODE -eq 0) {
                    # Delete remote tag (push empty ref to remote)
                    git push origin ":refs/tags/$tag" 2>&1 | Out-Null
                    if ($LASTEXITCODE -eq 0) {
                        Write-Success "  Deleted tag '$tag' (local and remote)"
                        $backupTagsDeletedCount++
                    } else {
                        Write-Warn "  Failed to delete remote tag '$tag' (local deleted)"
                        $failedCount++
                    }
                } else {
                    Write-ErrorMsg "  Failed to delete tag '$tag'"
                    $failedCount++
                }
            }
        }

        Write-Host ""
    }
}

Write-Host ""

# ============================================================================
# EXECUTION SUMMARY
# ============================================================================

Write-Host "Summary:" -ForegroundColor Cyan
Write-Host "  Deleted:  $deletedCount" -ForegroundColor $(if ($deletedCount -gt 0) { 'Yellow' } else { 'Gray' }) # Orphaned branches removed
Write-Host "  Kept:     $keptCount" -ForegroundColor Green                                  # Branches tracking remote
Write-Host "  Protected: $protectedCount" -ForegroundColor Blue                            # Never deleted
if (-not $NoUpdate -and -not $PurgeOnly) {
    Write-Host "  Updated:  $updatedCount" -ForegroundColor Green                          # Protected branches synced
}
if ($backupTagsDeletedCount -gt 0) {
    Write-Host "  Backup Tags Deleted: $backupTagsDeletedCount" -ForegroundColor Yellow  # Legacy tags cleaned
}
if ($failedCount -gt 0) {
    Write-Host "  Failed:   $failedCount" -ForegroundColor Red                            # Operations that errored
}
Write-Host "=============================================================" -ForegroundColor Cyan

if ($DryRun) {
    Write-Host ""
    Write-Info "This was a DRY RUN - no branches were deleted"
    Write-Host "Run without -DryRun parameter to execute"
}

Write-Host ""
Write-Host "Log saved to: $logFile" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

Stop-Transcript
