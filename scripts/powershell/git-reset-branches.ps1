<#
.SYNOPSIS
Reset Git branches (master, dev, sit) to their remote state with backup safeguards.

.DESCRIPTION
This script provides a safe way to reset local Git branches to match their remote counterparts.
It creates backup tags before making any changes, allowing recovery if needed. The script supports
dry-run mode for validation and can selectively reset only the SIT branch.

The script performs the following operations:
  1. Fetches all changes from origin
  2. Creates backup tags at current remote state (for recovery)
  3. Resets branches in order: master -> dev -> sit
  4. Force-pushes changes back to origin

This is useful for cleaning up corrupted branches or syncing with remote when local history diverges.

.PARAMETER DryRun
Switch parameter. When used, the script validates and displays what would happen without making
actual changes. Use this before running for real to verify the operations.

Example: .\git-reset-branches.ps1 -DryRun

.PARAMETER NoBackup
Switch parameter. When used, backup tags are NOT created before resetting. Use with caution.
By default (without this switch), backup tags are created for recovery.

Example: .\git-reset-branches.ps1 -NoBackup

.PARAMETER Force
Switch parameter. When used, bypasses the confirmation prompt. The script will proceed without
asking for user confirmation. Useful in CI/CD pipelines.

Example: .\git-reset-branches.ps1 -Force

.PARAMETER OnlySit
Switch parameter. When used, only the SIT branch is reset to match dev. Master and dev branches
are skipped. Useful for partial resets.

Example: .\git-reset-branches.ps1 -OnlySit

.EXAMPLE
# Basic usage with confirmation and backup:
.\git-reset-branches.ps1

.EXAMPLE
# Validate what would happen without making changes:
.\git-reset-branches.ps1 -DryRun

.EXAMPLE
# Reset only SIT branch to dev state with user confirmation:
.\git-reset-branches.ps1 -OnlySit

.EXAMPLE
# Full automated reset without backup and with auto-confirm (for CI/CD):
.\git-reset-branches.ps1 -NoBackup -Force

.EXAMPLE
# Dry-run to preview SIT-only reset:
.\git-reset-branches.ps1 -DryRun -OnlySit

.NOTES
Author: Development Team
LastModified: April 2026

The script creates timestamped log files in the .\logs\ directory for audit purposes.
All backup tags are pushed to origin for remote recovery capability.
#>
param(
    [switch]$DryRun = $false,
    [switch]$NoBackup = $false,
    [switch]$Force = $false,
    [switch]$OnlySit = $false
)


# ============================================================================
# SETUP LOGGING
# ============================================================================
# Initialize timestamped log file for audit trail and troubleshooting
$timestamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$logFile = Join-Path $PSScriptRoot "logs\reset-branches-$timestamp.log"
$logDir = Split-Path $logFile
if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
}

Start-Transcript -Path $logFile -Append

Write-Host "=============================================================" -ForegroundColor Cyan
Write-Host "Branch Reset Utility" -ForegroundColor Cyan
Write-Host "=============================================================" -ForegroundColor Cyan
Write-Host ""

if ($DryRun) {
    Write-Host "[DRY RUN MODE] No changes will be made" -ForegroundColor Yellow
    Write-Host ""
}

if ($OnlySit) {
    Write-Host "[SINGLE BRANCH MODE] Only SIT branch will be reset to dev state" -ForegroundColor Cyan
    Write-Host ""
}

if ($NoBackup) {
    Write-Host "[WARNING] Backup creation is DISABLED" -ForegroundColor Yellow
    Write-Host ""
}


# ============================================================================
# USER CONFIRMATION
# ============================================================================
# Prompt user for confirmation unless -Force switch is provided
# This is a safety measure to prevent accidental data loss
if (-not $Force) {
    Write-Host "[WARNING] This script will FORCE RESET branches!" -ForegroundColor Red
    if ($OnlySit) {
        Write-Host "This will:" -ForegroundColor Red
        Write-Host "  - Reset SIT branch to dev state" -ForegroundColor Red
        Write-Host "  - Discard uncommitted changes on SIT" -ForegroundColor Red
        Write-Host "  - Force push to origin" -ForegroundColor Red
    } else {
        Write-Host "This will:" -ForegroundColor Red
        Write-Host "  - Discard uncommitted changes" -ForegroundColor Red
        Write-Host "  - Rewrite branch history" -ForegroundColor Red
        Write-Host "  - Force push to origin" -ForegroundColor Red
    }
    Write-Host ""

    if (-not $NoBackup) {
        Write-Host "[OK] Backup tags WILL be created for recovery" -ForegroundColor Green
    }

    Write-Host ""
    $confirm = Read-Host "Type 'yes' to continue"

    if ($confirm -ne "yes") {
        Write-Host "[CANCELLED] Operation cancelled by user" -ForegroundColor Yellow
        Stop-Transcript
        exit 0
    }

    Write-Host ""
}


# ============================================================================
# FETCH LATEST CHANGES FROM REMOTE
# ============================================================================
# Pull the latest remote state before performing any resets
# This ensures we're resetting to the current remote branch state
Write-Host "Fetching latest changes from origin..." -ForegroundColor Cyan
if ($DryRun) {
    Write-Host "[DRY RUN] git fetch --all --prune" -ForegroundColor Gray
} else {
    git fetch --all --prune

    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Failed to fetch from origin" -ForegroundColor Red
        Stop-Transcript
        exit 1
    }
}

Write-Host "[OK] Fetch complete`n" -ForegroundColor Green

# Get list of local branches (for later use)
$localBranches = git branch --format='%(refname:short)' | ForEach-Object { $_.Trim() }

# Define protected branches
$protectedBranches = @("master", "dev", "sit")


# ============================================================================
# CREATE BACKUP TAGS
# ============================================================================
# Tag the current remote state before any resets for recovery purposes
# This allows restoring to the previous state if something goes wrong
# Backup tags are only created if -NoBackup switch is not used
if (-not $NoBackup) {
    Write-Host "Creating backup tags..." -ForegroundColor Cyan
    $backupCreatedCount = 0
    $backupSkippedCount = 0

    # Determine which branches to backup
    $branchesToBackup = $protectedBranches
    if ($OnlySit) {
        $branchesToBackup = @("sit")
    }

    foreach ($branch in $branchesToBackup) {
        # Get current commit ID of origin/$branch (remote state)
        $remoteId = git rev-parse "origin/$branch" 2>$null

        if ($LASTEXITCODE -eq 0 -and -not [string]::IsNullOrEmpty($remoteId)) {
            # Short commit hash for readability (first 8 characters)
            $remoteShortId = $remoteId.Substring(0, 8)

            # Check if a backup tag for this remote commit already exists (avoid duplicate backups)
            $existingTag = git tag -l "backup-$branch-$remoteShortId-*" 2>$null
            if ($null -ne $existingTag -and $existingTag.Count -gt 0) {
                Write-Host "  [SKIP] Branch 'origin/$branch' (ID: $remoteShortId) - backup already exists for this commit" -ForegroundColor Gray
                $backupSkippedCount++
                continue
            }

            # Create backup tag using REMOTE commit ID (the state about to be changed by reset)
            $tagName = "backup-$branch-$remoteShortId-$timestamp"
            if ($DryRun) {
                Write-Host "[DRY RUN] git tag $tagName origin/$branch" -ForegroundColor Gray
            } else {
                git tag $tagName "origin/$branch" 2>$null
                if ($LASTEXITCODE -eq 0) {
                    Write-Host "  [OK] Created tag: $tagName" -ForegroundColor Green
                    $backupCreatedCount++
                } else {
                    Write-Host "  [ERROR] Failed to create tag for '$branch'" -ForegroundColor Red
                }
            }
        } else {
            Write-Host "  [WARNING] Could not get commit ID for 'origin/$branch'" -ForegroundColor Yellow
        }
    }

    if (-not $DryRun) {
        Write-Host "Pushing backup tags to origin..." -ForegroundColor Cyan
        git push origin --tags 2>$null
        Write-Host "  [OK] Backup tags pushed to origin" -ForegroundColor Green
        Write-Host "  Summary: $backupCreatedCount created, $backupSkippedCount skipped`n" -ForegroundColor Cyan
    } else {
        Write-Host "[DRY RUN] git push origin --tags`n" -ForegroundColor Gray
    }
}


# ============================================================================
# VERIFY PROTECTED BRANCHES EXIST LOCALLY
# ============================================================================
# Check that all required branches exist locally before attempting reset
# If a branch doesn't exist locally, we'll warn the user but continue
Write-Host "Verifying protected branches exist..." -ForegroundColor Cyan

foreach ($branch in $protectedBranches) {
    if ($localBranches -notcontains $branch) {
        Write-Host "[WARNING] Branch '$branch' does not exist locally" -ForegroundColor Yellow
    }
}

Write-Host ""

# ============================================================================
# RESET PROTECTED BRANCHES
# ============================================================================
# Reset master, dev, and sit branches to match remote state
# These operations are skipped if -OnlySit parameter is used

# Only reset master and dev if not in -OnlySit mode
if (-not $OnlySit) {
    # --- MASTER BRANCH: Reset to remote state ---
    # Update master branch from origin
    Write-Host "Updating master branch..." -ForegroundColor Cyan
    if ($DryRun) {
        Write-Host "[DRY RUN] git checkout master" -ForegroundColor Gray
        Write-Host "[DRY RUN] git reset --hard origin/master" -ForegroundColor Gray
        Write-Host "[DRY RUN] git push origin master --force" -ForegroundColor Gray
        Write-Host "[OK] Master branch would be reset to origin/master`n" -ForegroundColor Green
    } else {
        git checkout master

        if ($LASTEXITCODE -eq 0) {
            git reset --hard origin/master

            if ($LASTEXITCODE -eq 0) {
                Write-Host "[OK] Master branch reset to origin/master" -ForegroundColor Green

                Write-Host "Pushing master to origin..." -ForegroundColor Yellow
                git push origin master --force

                if ($LASTEXITCODE -eq 0) {
                    Write-Host "[OK] Master branch pushed to origin`n" -ForegroundColor Green
                }
                else {
                    Write-Host "[ERROR] Failed to push master branch`n" -ForegroundColor Red
                    Stop-Transcript
                    exit 1
                }
            }
            else {
                Write-Host "[ERROR] Failed to reset master branch`n" -ForegroundColor Red
                Stop-Transcript
                exit 1
            }
        }
        else {
            Write-Host "[ERROR] Failed to checkout master branch`n" -ForegroundColor Red
            Stop-Transcript
            exit 1
        }
    }

    # --- DEV BRANCH: Reset to match master ---
    # Update dev branch from master
    if ($localBranches -contains "dev") {
        Write-Host "Updating dev branch from master..." -ForegroundColor Cyan
        if ($DryRun) {
            Write-Host "[DRY RUN] git checkout dev" -ForegroundColor Gray
            Write-Host "[DRY RUN] git reset --hard origin/master" -ForegroundColor Gray
            Write-Host "[DRY RUN] git push origin dev --force" -ForegroundColor Gray
            Write-Host "[OK] Dev branch would be reset to origin/master`n" -ForegroundColor Green
        } else {
            git checkout dev

            if ($LASTEXITCODE -eq 0) {
                git reset --hard origin/master

                if ($LASTEXITCODE -eq 0) {
                    Write-Host "[OK] Dev branch reset to origin/master" -ForegroundColor Green
                    Write-Host "Pushing dev to origin..." -ForegroundColor Yellow
                    git push origin dev --force

                    if ($LASTEXITCODE -eq 0) {
                        Write-Host "[OK] Dev branch pushed to origin`n" -ForegroundColor Green
                    }
                    else {
                        Write-Host "[ERROR] Failed to push dev branch`n" -ForegroundColor Red
                        Stop-Transcript
                        exit 1
                    }
                }
                else {
                    Write-Host "[ERROR] Failed to reset dev branch`n" -ForegroundColor Red
                    Stop-Transcript
                    exit 1
                }
            }
            else {
                Write-Host "[ERROR] Failed to checkout dev branch`n" -ForegroundColor Red
                Stop-Transcript
                exit 1
            }
        }
    }
    else {
        Write-Host "[WARNING] Dev branch does not exist, skipping...`n" -ForegroundColor Yellow
    }
} else {
    Write-Host "[SKIPPED] Master and dev branches (--OnlySit mode)`n" -ForegroundColor Cyan
}

# --- SIT BRANCH: Reset to match dev ---
# Update sit branch from dev
if ($localBranches -contains "sit") {
    Write-Host "Updating sit branch from dev..." -ForegroundColor Cyan
    if ($DryRun) {
        Write-Host "[DRY RUN] git checkout sit" -ForegroundColor Gray
        Write-Host "[DRY RUN] git reset --hard origin/dev" -ForegroundColor Gray
        Write-Host "[DRY RUN] git push origin sit --force" -ForegroundColor Gray
        Write-Host "[OK] Sit branch would be reset to origin/dev`n" -ForegroundColor Green
    } else {
        git checkout sit

        if ($LASTEXITCODE -eq 0) {
            git reset --hard origin/dev

            if ($LASTEXITCODE -eq 0) {
                Write-Host "[OK] Sit branch reset to origin/dev" -ForegroundColor Green
                Write-Host "Pushing sit to origin..." -ForegroundColor Yellow
                git push origin sit --force

                if ($LASTEXITCODE -eq 0) {
                    Write-Host "[OK] Sit branch pushed to origin`n" -ForegroundColor Green
                }
                else {
                    Write-Host "[ERROR] Failed to push sit branch`n" -ForegroundColor Red
                    Stop-Transcript
                    exit 1
                }
            }
            else {
                Write-Host "[ERROR] Failed to reset sit branch`n" -ForegroundColor Red
                Stop-Transcript
                exit 1
            }
        }
        else {
            Write-Host "[ERROR] Failed to checkout sit branch`n" -ForegroundColor Red
            Stop-Transcript
            exit 1
        }
    }
}
else {
    Write-Host "[WARNING] Sit branch does not exist, skipping...`n" -ForegroundColor Yellow
}

# ============================================================================
# SUMMARY AND CLEANUP
# ============================================================================
# Display results and cleanup

Write-Host "=============================================================" -ForegroundColor Cyan
if ($OnlySit) {
    Write-Host "[OK] SIT branch has been reset to dev state successfully!" -ForegroundColor Cyan
} else {
    Write-Host "[OK] All branches have been reset successfully!" -ForegroundColor Cyan
}
Write-Host "=============================================================" -ForegroundColor Cyan

if ($DryRun) {
    Write-Host ""
    Write-Host "[DRY RUN] This was a DRY RUN - no changes were made" -ForegroundColor Yellow
    Write-Host "[DRY RUN] Run without -DryRun parameter to execute" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Log saved to: $logFile" -ForegroundColor Cyan

Stop-Transcript
