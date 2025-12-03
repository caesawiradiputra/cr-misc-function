param(
    [switch]$DryRun = $false,
    [switch]$NoUpdate = $false,
    [switch]$Force = $false,
    [switch]$PurgeOnly = $false,
    [switch]$CleanupBackupTags = $false,
    [string[]]$ProtectedBranches = @("main", "master", "dev", "sit")
)

# Setup logging
$timestamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$logFile = Join-Path $PSScriptRoot "logs\clean-branches-$timestamp.log"
$logDir = Split-Path $logFile
if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
}

Start-Transcript -Path $logFile -Append

function Write-Info($msg)  { Write-Host "[INFO]  $msg" -ForegroundColor Cyan }
function Write-Warn($msg)  { Write-Host "[WARN]  $msg" -ForegroundColor Yellow }
function Write-Okay($msg)  { Write-Host "[OK]    $msg" -ForegroundColor Green }
function Write-Err($msg)   { Write-Host "[ERROR] $msg" -ForegroundColor Red }

# Initialize counters
$deletedCount = 0
$keptCount = 0
$protectedCount = 0
$updatedCount = 0
$failedCount = 0
$backupTagsDeletedCount = 0
$branchesToDelete = @()
$backupTagsToDelete = @()

Write-Host "=============================================================" -ForegroundColor Cyan
Write-Host "Branch Cleanup Utility" -ForegroundColor Cyan
Write-Host "=============================================================" -ForegroundColor Cyan
Write-Host ""

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

# User confirmation (skip if -Force)
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

# Fetch latest remote info
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

# Get list of all local branches
Write-Info "Gathering branch information"
$localBranches = git branch --format='%(refname:short)' | ForEach-Object { $_.Trim() }

# Get list of all remote branches
$remoteBranches = git branch -r --format='%(refname:short)' | ForEach-Object {
    ($_ -replace "^origin/", "").Trim()
}

# Update protected branches (unless -NoUpdate or -PurgeOnly)
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

# Identify branches to delete
Write-Info "Checking local branches for cleanup"

foreach ($branch in $localBranches) {
    if ($ProtectedBranches -contains $branch) {
        Write-Host "  [PROTECTED] '$branch'" -ForegroundColor Blue
        $protectedCount++
        continue
    }

    if ($remoteBranches -notcontains $branch) {
        Write-Host "  [DELETE] '$branch' (not on remote)" -ForegroundColor Yellow
        $branchesToDelete += $branch
    }
    else {
        Write-Host "  [KEEP] '$branch'" -ForegroundColor Green
        $keptCount++
    }
}

Write-Host ""

# Show deletion preview
if ($branchesToDelete.Count -gt 0) {
    Write-Host "Branches to be deleted ($($branchesToDelete.Count)):" -ForegroundColor Yellow
    foreach ($branch in $branchesToDelete) {
        Write-Host "  - $branch" -ForegroundColor DarkYellow
    }
    Write-Host ""
}

# Delete branches
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

# Cleanup backup tags created by reset-branches process
if ($CleanupBackupTags) {
    Write-Info "Checking for backup tags to cleanup"
    
    # Get all tags matching backup-*-* pattern
    $allTags = git tag --list "backup-*" 2>$null
    
    if ($null -eq $allTags -or $allTags.Count -eq 0) {
        Write-Info "No backup tags found"
    } else {
        # Convert single tag to array if needed
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
                # Delete local tag
                git tag -d $tag 2>$null
                if ($LASTEXITCODE -eq 0) {
                    # Delete remote tag
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
Write-Host "Summary:" -ForegroundColor Cyan
Write-Host "  Deleted:  $deletedCount" -ForegroundColor $(if ($deletedCount -gt 0) { 'Yellow' } else { 'Gray' })
Write-Host "  Kept:     $keptCount" -ForegroundColor Green
Write-Host "  Protected: $protectedCount" -ForegroundColor Blue
if (-not $NoUpdate) {
    Write-Host "  Updated:  $updatedCount" -ForegroundColor Green
}
if ($backupTagsDeletedCount -gt 0) {
    Write-Host "  Backup Tags Deleted: $backupTagsDeletedCount" -ForegroundColor Yellow
}
if ($failedCount -gt 0) {
    Write-Host "  Failed:   $failedCount" -ForegroundColor Red
}
Write-Host "=============================================================" -ForegroundColor Cyan

if ($DryRun) {
    Write-Host ""
    Write-Info "This was a DRY RUN - no branches were deleted"
    Write-Host "Run without -DryRun parameter to execute"
}

Write-Host ""
Write-Host "Log saved to: $logFile" -ForegroundColor Cyan

Stop-Transcript
