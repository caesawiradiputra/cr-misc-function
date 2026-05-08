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

Start-Transcript -Path $logFile -Append

# Logging helper functions - Color-coded status messages
function Write-Info($msg)  { Write-Host "[INFO]  $msg" -ForegroundColor Cyan }
function Write-Warn($msg)  { Write-Host "[WARN]  $msg" -ForegroundColor Yellow }
function Write-Okay($msg)  { Write-Host "[OK]    $msg" -ForegroundColor Green }
function Write-Err($msg)   { Write-Host "[ERROR] $msg" -ForegroundColor Red }

# Initialize operation counters and collections
$deletedCount = 0              # Branches successfully deleted
$keptCount = 0                 # Branches kept (exist on remote)
$protectedCount = 0            # Branches protected from deletion
$updatedCount = 0              # Protected branches successfully updated
$failedCount = 0               # Operations that failed
$backupTagsDeletedCount = 0    # Backup tags cleaned up
$branchesToDelete = @()        # Collection of branches marked for deletion
$backupTagsToDelete = @()      # Collection of backup tags marked for deletion

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

# User confirmation checkpoint - Require explicit 'yes' to proceed (unless -Force)
if (-not $Force) {
    Write-Host "[WARNING] This script will DELETE local branches!" -ForegroundColor Red
    Write-Host "This will:" -ForegroundColor Red
    if (-not $PurgeOnly) {
        Write-Host "  - Update protected branches (master, dev, sit)" -ForegroundColor Red
    }
    Write-Host "  - Delete branches not on remote" -ForegroundColor Red
    if ($CleanupBackupTags) {
        Write-Host "  - Delete backup tags created by reset-branches" -ForegroundColor Red
    }
    Write-Host "  - Protect: $($ProtectedBranches -join ', ')" -ForegroundColor Red
    Write-Host ""

    $confirm = Read-Host "Type 'yes' to continue"

    if ($confirm -ne "yes") {
        Write-Warn "Operation cancelled by user"
        Stop-Transcript
        exit 0
    }

    Write-Host ""
}

# ============================================================================
# PHASE 1: SYNC WITH REMOTE
# ============================================================================

# Fetch latest changes and prune deleted branches from remote tracking
Write-Info "Fetching latest changes from origin (with prune)"
if ($DryRun) {
    Write-Host "[DRY RUN] git fetch --all --prune" -ForegroundColor Gray
} else {
    git fetch --all --prune

    if ($LASTEXITCODE -ne 0) {
        Write-Err "Failed to fetch from origin"
        Stop-Transcript
        exit 1
    }
}

Write-Okay "Fetch complete"
Write-Host ""

# Gather current branch state
Write-Info "Gathering branch information"
$localBranches = git branch --format='%(refname:short)' | ForEach-Object { $_.Trim() }

# Extract remote branch names (strip 'origin/' prefix)
$remoteBranches = git branch -r --format='%(refname:short)' | ForEach-Object {
    ($_ -replace "^origin/", "").Trim()
}

# ============================================================================
# PHASE 2: UPDATE PROTECTED BRANCHES (optional)
# ============================================================================

# Sync protected branches with latest remote changes (unless -NoUpdate or -PurgeOnly)
if (-not $NoUpdate -and -not $PurgeOnly) {
    Write-Info "Updating protected branches"

    $branchesToUpdate = @("master", "dev", "sit")

    foreach ($branch in $branchesToUpdate) {
        if ($localBranches -contains $branch) {
            Write-Host "  Updating '$branch'..." -ForegroundColor Gray

            if ($DryRun) {
                Write-Host "    [DRY RUN] git checkout $branch" -ForegroundColor Gray
                Write-Host "    [DRY RUN] git pull origin $branch" -ForegroundColor Gray
            } else {
                # Checkout branch and pull latest changes
                git checkout $branch 2>$null

                if ($LASTEXITCODE -eq 0) {
                    git pull origin $branch 2>$null

                    if ($LASTEXITCODE -eq 0) {
                        Write-Okay "  Updated '$branch'"
                        $updatedCount++
                    }
                    else {
                        Write-Warn "  Failed to pull '$branch'"
                        $failedCount++
                    }
                }
                else {
                    Write-Warn "  Failed to checkout '$branch'"
                    $failedCount++
                }
            }
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
        $branchesToDelete += $branch
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
        foreach ($branch in $branchesToDelete) {
            git branch -D $branch 2>$null

            if ($LASTEXITCODE -eq 0) {
                Write-Okay "  Deleted '$branch'"
                $deletedCount++
            }
            else {
                Write-Err "  Failed to delete '$branch'"
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
    $allTags = git tag --list "backup-*" 2>$null

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
            $backupTagsToDelete += $tag
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
                git tag -d $tag 2>$null
                if ($LASTEXITCODE -eq 0) {
                    # Delete remote tag (push empty ref to remote)
                    git push origin ":refs/tags/$tag" 2>$null
                    if ($LASTEXITCODE -eq 0) {
                        Write-Okay "  Deleted tag '$tag' (local and remote)"
                        $backupTagsDeletedCount++
                    } else {
                        Write-Warn "  Failed to delete remote tag '$tag' (local deleted)"
                        $backupTagsDeletedCount++
                    }
                } else {
                    Write-Err "  Failed to delete tag '$tag'"
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
if (-not $NoUpdate) {
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
