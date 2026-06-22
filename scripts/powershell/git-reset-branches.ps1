<#
.SYNOPSIS
Reset Git branches (master, dev, sit) to their remote state with backup safeguards.

.DESCRIPTION
This script provides a safe way to reset local Git branches to match their remote counterparts.
It creates backup tags before making any changes, allowing recovery if needed. The script supports
dry-run mode for validation and can selectively reset only the DEV or only the SIT branch.

The script performs a cascading reset:
  1. Fetches latest changes from origin
  2. Creates backup tags at current remote state (for recovery)
  3. Resets master to origin/master, then dev to origin/master, then sit to origin/dev
  4. Force-pushes changes back to origin (with --force-with-lease for safety)

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

.PARAMETER OnlyDev
Switch parameter. When used, only the DEV branch is reset to match master. Master and SIT branches
are skipped. Useful for partial resets. Cannot be combined with -OnlySit.

Example: .\git-reset-branches.ps1 -OnlyDev

.PARAMETER OnlySit
Switch parameter. When used, only the SIT branch is reset to match dev. Master and dev branches
are skipped. Useful for partial resets. Cannot be combined with -OnlyDev.

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
# Reset only DEV branch to master state with user confirmation:
.\git-reset-branches.ps1 -OnlyDev

.EXAMPLE
# Dry-run to preview SIT-only reset:
.\git-reset-branches.ps1 -DryRun -OnlySit

.EXAMPLE
# Dry-run to preview DEV-only reset:
.\git-reset-branches.ps1 -DryRun -OnlyDev

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
    [switch]$OnlyDev = $false,
    [switch]$OnlySit = $false
)


# ============================================================================
# MUTUAL EXCLUSIVITY GUARD
# ============================================================================
if ($OnlyDev -and $OnlySit) {
    Write-Host "[ERROR] -OnlyDev and -OnlySit are mutually exclusive. Please choose one." -ForegroundColor Red
    exit 1
}


# ============================================================================
# SETUP LOGGING
# ============================================================================
$timestamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$scriptDir = if ($PSScriptRoot) { $PSScriptRoot } else { $PWD.Path }
$logFile = Join-Path $scriptDir "logs\reset-branches-$timestamp.log"
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

if ($OnlyDev) {
    Write-Host "[SINGLE BRANCH MODE] Only DEV branch will be reset to master state" -ForegroundColor Cyan
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
# GIT REPOSITORY VALIDATION
# ============================================================================
$null = git rev-parse --is-inside-work-tree 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] This script must be run from inside a Git repository" -ForegroundColor Red
    Stop-Transcript
    exit 1
}


# ============================================================================
# UNCOMMITTED CHANGES CHECK
# ============================================================================
$dirtyFiles = git status --porcelain 2>&1
$dirtyFiles = $dirtyFiles | Where-Object { $_ -is [string] }
if ($dirtyFiles) {
    Write-Host "[ERROR] Working directory has uncommitted changes:" -ForegroundColor Red
    $dirtyFiles | ForEach-Object { Write-Host "  $_" -ForegroundColor Red }
    Write-Host "Please commit or stash changes before running this script." -ForegroundColor Yellow
    Stop-Transcript
    exit 1
}


# ============================================================================
# USER CONFIRMATION
# ============================================================================
if (-not $Force) {
    Write-Host "[WARNING] This script will FORCE RESET branches!" -ForegroundColor Red
    if ($OnlyDev) {
        Write-Host "This will:" -ForegroundColor Red
        Write-Host "  - Reset DEV branch to master state" -ForegroundColor Red
        Write-Host "  - Discard uncommitted changes on DEV" -ForegroundColor Red
        Write-Host "  - Force push to origin" -ForegroundColor Red
    } elseif ($OnlySit) {
        Write-Host "This will:" -ForegroundColor Red
        Write-Host "  - Reset SIT branch to dev state" -ForegroundColor Red
        Write-Host "  - Discard uncommitted changes on SIT" -ForegroundColor Red
        Write-Host "  - Force push to origin" -ForegroundColor Red
    } else {
        Write-Host "This will:" -ForegroundColor Red
        Write-Host "  - Reset master, dev, and sit branches" -ForegroundColor Red
        Write-Host "  - Rewrite branch history" -ForegroundColor Red
        Write-Host "  - Force push to origin" -ForegroundColor Red
    }
    Write-Host ""

    if (-not $NoBackup) {
        Write-Host "[OK] Backup tags WILL be created for recovery" -ForegroundColor Green
    }

    Write-Host ""

    $confirm = $null
    while ($true) {
        $confirm = Read-Host "Type 'yes' to continue"
        $confirm = $confirm.Trim().ToLower()
        if ($confirm -eq 'yes' -or $confirm -eq '') {
            break
        }
        Write-Host "[WARN] Invalid input: '$confirm'. Type 'yes' to confirm or press Enter to cancel." -ForegroundColor Yellow
    }

    if ($confirm -ne 'yes') {
        Write-Host "[CANCELLED] Operation cancelled by user" -ForegroundColor Yellow
        Stop-Transcript
        exit 0
    }

    Write-Host ""
}


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

function Reset-Branch {
    param(
        [string]$BranchName,
        [string]$ResetTarget,
        [switch]$DryRun
    )

    Write-Host "Updating $BranchName branch..." -ForegroundColor Cyan

    if ($DryRun) {
        Write-Host "[DRY RUN] git checkout $BranchName" -ForegroundColor Gray
        Write-Host "[DRY RUN] git reset --hard $ResetTarget" -ForegroundColor Gray
        Write-Host "[DRY RUN] git push origin $BranchName --force-with-lease" -ForegroundColor Gray
        Write-Host "[OK] $BranchName branch would be reset to $ResetTarget`n" -ForegroundColor Green
        return $true
    }

    git checkout $BranchName 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Failed to checkout $BranchName branch`n" -ForegroundColor Red
        return $false
    }

    git reset --hard $ResetTarget
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Failed to reset $BranchName branch`n" -ForegroundColor Red
        return $false
    }

    Write-Host "[OK] $BranchName branch reset to $ResetTarget" -ForegroundColor Green
    Write-Host "Pushing $BranchName to origin..." -ForegroundColor Yellow
    git push origin $BranchName --force-with-lease

    if ($LASTEXITCODE -eq 0) {
        Write-Host "[OK] $BranchName branch pushed to origin`n" -ForegroundColor Green
        return $true
    } else {
        Write-Host "[ERROR] Failed to push $BranchName branch`n" -ForegroundColor Red
        return $false
    }
}


# ============================================================================
# FETCH LATEST CHANGES FROM REMOTE
# ============================================================================
Write-Host "Fetching latest changes from origin..." -ForegroundColor Cyan
if ($DryRun) {
    Write-Host "[DRY RUN] git fetch origin --prune" -ForegroundColor Gray
} else {
    git fetch origin --prune 2>&1 | Out-Null

    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Failed to fetch from origin" -ForegroundColor Red
        Stop-Transcript
        exit 1
    }
}

Write-Host "[OK] Fetch complete`n" -ForegroundColor Green

# Get list of local branches (for later use)
$localBranches = git branch --format='%(refname:short)' | Where-Object { $_ -is [string] } | ForEach-Object { $_.Trim() }

# Define protected branches
$protectedBranches = @("master", "dev", "sit")


# ============================================================================
# CREATE BACKUP TAGS
# ============================================================================
$backupTagsToPush = @()

if (-not $NoBackup) {
    Write-Host "Creating backup tags..." -ForegroundColor Cyan
    $backupCreatedCount = 0
    $backupSkippedCount = 0

    # Determine which branches to backup
    $branchesToBackup = $protectedBranches
    if ($OnlyDev) {
        $branchesToBackup = @("dev")
    } elseif ($OnlySit) {
        $branchesToBackup = @("sit")
    }

    foreach ($branch in $branchesToBackup) {
        # Get current commit ID of origin/$branch (remote state)
        $remoteId = git rev-parse "origin/$branch" 2>&1 | Where-Object { $_ -is [string] }

        if ($LASTEXITCODE -eq 0 -and -not [string]::IsNullOrEmpty($remoteId)) {
            # Short commit hash for readability (first 8 characters, with safety check)
            $remoteShortId = if ($remoteId.Length -ge 8) { $remoteId.Substring(0, 8) } else { $remoteId }

            # Check if a backup tag for this remote commit already exists (avoid duplicate backups)
            $existingTag = git tag -l "backup-$branch-$remoteShortId-*" 2>&1 | Where-Object { $_ -is [string] }
            if (-not [string]::IsNullOrEmpty($existingTag)) {
                Write-Host "  [SKIP] Branch 'origin/$branch' (ID: $remoteShortId) - backup already exists for this commit" -ForegroundColor Gray
                $backupSkippedCount++
                continue
            }

            # Create backup tag using REMOTE commit ID (the state about to be changed by reset)
            $tagName = "backup-$branch-$remoteShortId-$timestamp"
            if ($DryRun) {
                Write-Host "[DRY RUN] git tag $tagName origin/$branch" -ForegroundColor Gray
            } else {
                git tag $tagName "origin/$branch" 2>&1 | Out-Null
                if ($LASTEXITCODE -eq 0) {
                    Write-Host "  [OK] Created tag: $tagName" -ForegroundColor Green
                    $backupCreatedCount++
                    $backupTagsToPush += $tagName
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
        if ($backupTagsToPush.Count -gt 0) {
            git push origin @backupTagsToPush 2>&1 | Out-Null
            if ($LASTEXITCODE -eq 0) {
                Write-Host "  [OK] Backup tags pushed to origin" -ForegroundColor Green
            } else {
                Write-Host "  [ERROR] Failed to push backup tags to origin. Aborting to prevent unrecoverable reset." -ForegroundColor Red
                Stop-Transcript
                exit 1
            }
        } else {
            Write-Host "  [SKIP] No new backup tags to push" -ForegroundColor Gray
        }
        Write-Host "  Summary: $backupCreatedCount created, $backupSkippedCount skipped`n" -ForegroundColor Cyan
    } else {
        Write-Host "[DRY RUN] git push origin <backup-tags>`n" -ForegroundColor Gray
    }
}


# ============================================================================
# VERIFY PROTECTED BRANCHES EXIST LOCALLY
# ============================================================================
Write-Host "Verifying protected branches exist..." -ForegroundColor Cyan

# Only verify branches that will actually be operated on
$branchesToVerify = $protectedBranches
if ($OnlyDev) { $branchesToVerify = @("dev") }
elseif ($OnlySit) { $branchesToVerify = @("sit") }

foreach ($branch in $branchesToVerify) {
    if ($localBranches -notcontains $branch) {
        Write-Host "[WARNING] Branch '$branch' does not exist locally" -ForegroundColor Yellow
    }
}

Write-Host ""

# ============================================================================
# SAVE ORIGINAL BRANCH
# ============================================================================
$originalBranch = git rev-parse --abbrev-ref HEAD 2>&1 | Where-Object { $_ -is [string] }


# ============================================================================
# RESET PROTECTED BRANCHES
# ============================================================================
$resetFailed = $false

# Only reset master if not in -OnlySit or -OnlyDev mode
if (-not $OnlySit -and -not $OnlyDev) {
    # --- MASTER BRANCH: Reset to remote state ---
    if (-not (Reset-Branch -BranchName "master" -ResetTarget "origin/master" -DryRun:$DryRun)) {
        $resetFailed = $true
    }

    # --- DEV BRANCH: Reset to match master --- (full reset mode)
    if (-not $resetFailed -and $localBranches -contains "dev") {
        if (-not (Reset-Branch -BranchName "dev" -ResetTarget "origin/master" -DryRun:$DryRun)) {
            $resetFailed = $true
        }
    } elseif (-not $resetFailed) {
        Write-Host "[WARNING] Dev branch does not exist, skipping...`n" -ForegroundColor Yellow
    }
} elseif ($OnlyDev) {
    # --- DEV BRANCH (OnlyDev mode): Reset to match master ---
    Write-Host "[SKIPPED] Master branch (--OnlyDev mode)`n" -ForegroundColor Cyan
    if ($localBranches -contains "dev") {
        if (-not (Reset-Branch -BranchName "dev" -ResetTarget "origin/master" -DryRun:$DryRun)) {
            $resetFailed = $true
        }
    } else {
        Write-Host "[WARNING] Dev branch does not exist, skipping...`n" -ForegroundColor Yellow
    }
} else {
    Write-Host "[SKIPPED] Master and dev branches (--OnlySit mode)`n" -ForegroundColor Cyan
}

# --- SIT BRANCH: Reset to match dev --- (skipped in OnlyDev mode)
if (-not $resetFailed) {
    if ($OnlyDev) {
        Write-Host "[SKIPPED] Sit branch (--OnlyDev mode)`n" -ForegroundColor Cyan
    } elseif ($localBranches -contains "sit") {
        if (-not (Reset-Branch -BranchName "sit" -ResetTarget "origin/dev" -DryRun:$DryRun)) {
            $resetFailed = $true
        }
    } else {
        Write-Host "[WARNING] Sit branch does not exist, skipping...`n" -ForegroundColor Yellow
    }
}

if ($resetFailed) {
    Stop-Transcript
    exit 1
}


# ============================================================================
# RESTORE ORIGINAL BRANCH
# ============================================================================
if (-not $DryRun -and $originalBranch) {
    git checkout $originalBranch 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[OK] Restored original branch: $originalBranch" -ForegroundColor Green
    } else {
        Write-Host "[WARNING] Could not restore original branch: $originalBranch" -ForegroundColor Yellow
    }
}


# ============================================================================
# SUMMARY AND CLEANUP
# ============================================================================

Write-Host "=============================================================" -ForegroundColor Cyan
if ($DryRun) {
    if ($OnlyDev) {
        Write-Host "[DRY RUN] DEV branch reset preview complete - no changes made" -ForegroundColor Cyan
    } elseif ($OnlySit) {
        Write-Host "[DRY RUN] SIT branch reset preview complete - no changes made" -ForegroundColor Cyan
    } else {
        Write-Host "[DRY RUN] Branch reset preview complete - no changes made" -ForegroundColor Cyan
    }
} else {
    if ($OnlyDev) {
        Write-Host "[OK] DEV branch has been reset to master state successfully!" -ForegroundColor Cyan
    } elseif ($OnlySit) {
        Write-Host "[OK] SIT branch has been reset to dev state successfully!" -ForegroundColor Cyan
    } else {
        Write-Host "[OK] All branches have been reset successfully!" -ForegroundColor Cyan
    }
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
