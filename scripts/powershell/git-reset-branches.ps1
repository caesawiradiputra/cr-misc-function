param(
    [switch]$DryRun = $false,
    [switch]$NoBackup = $false,
    [switch]$Force = $false,
    [switch]$OnlySit = $false
)

# Setup logging
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

# User confirmation (skip if -Force is used)
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

# Fetch latest remote info
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

# Create backup tags (unless -NoBackup is used)
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

# Verify all protected branches exist locally
Write-Host "Verifying protected branches exist..." -ForegroundColor Cyan

foreach ($branch in $protectedBranches) {
    if ($localBranches -notcontains $branch) {
        Write-Host "[WARNING] Branch '$branch' does not exist locally" -ForegroundColor Yellow
    }
}

Write-Host ""

# Only reset master and dev if not in -OnlySit mode
if (-not $OnlySit) {
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
