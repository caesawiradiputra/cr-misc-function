<#
.SYNOPSIS
    Checks if dev branch has the same code changes as master branch (diff-based sync check).

.DESCRIPTION
    - Fetches refs (unless -NoFetch) and validates existence of remote branches.
    - "In sync" means: no code differences between branches (git diff is empty).
    - Compares actual code changes, not commit history.
    - If dev is in sync with master, checks out local dev (creating/tracking it if missing) and fast-forwards.
    - Exits with code 0 on success (dev set active), non-zero otherwise.

.PARAMETER Remote
    Git remote name. Default: origin.

.PARAMETER Master
    Master branch name. Default: master.

.PARAMETER Dev
    Dev branch name. Default: dev.

.PARAMETER NoFetch
    Skip fetching remote refs.

.PARAMETER Force
    Skip the confirmation prompt and proceed directly with sync.

.EXAMPLE
    .\scripts\powershell\check-sync-set-dev.ps1

.EXAMPLE
    .\scripts\powershell\check-sync-set-dev.ps1 -Remote origin -Master master -Dev dev

.NOTES
    Requires Git to be installed and the script to be run inside a Git repository.
    Checks sync by comparing code diffs, not commit history.
#>

[CmdletBinding()]
param(
    [string]$Remote = "origin",
    [string]$Master = "master",
    [string]$Dev    = "dev",
    [switch]$NoFetch,
    [switch]$Force
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# Import shared helpers
Import-Module (Join-Path $PSScriptRoot "modules\GitScriptHelpers.psm1") -Force

# ============================================================================
# HELPER FUNCTIONS - Status messages with color coding
# ============================================================================


function Assert-GitAvailable {
    if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
        throw "Git is not installed or not available in PATH."
    }
}

function Assert-InGitRepo {
    $prevEAP = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
    git rev-parse --is-inside-work-tree 2>&1 | Out-Null
    $code = $LASTEXITCODE
    $ErrorActionPreference = $prevEAP
    if ($code -ne 0) {
        throw "Current directory is not a Git repository."
    }
}

function Test-RemoteBranchExists([string]$Remote, [string]$Branch) {
    $prevEAP = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
    git show-ref --verify --quiet "refs/remotes/$Remote/$Branch" 2>&1 | Out-Null
    $code = $LASTEXITCODE
    $ErrorActionPreference = $prevEAP
    return ($code -eq 0)
}

function Test-MasterInBranch([string]$Remote, [string]$Master, [string]$Branch) {
    # Check if branches have the same code changes (no diff means sync)
    $prevEAP = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
    $diff = git diff "$Remote/$Master" "$Remote/$Branch" 2>&1 | Where-Object { $_ -is [string] }
    $code = $LASTEXITCODE
    $ErrorActionPreference = $prevEAP
    if ($code -ne 0) {
        throw "git diff between '$Remote/$Master' and '$Remote/$Branch' failed (exit code $code)."
    }
    return -not $diff
}

function Ensure-LocalBranch([string]$Branch, [string]$Remote) {
    $prevEAP = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
    git show-ref --verify --quiet "refs/heads/$Branch" 2>&1 | Out-Null
    $exists = ($LASTEXITCODE -eq 0)
    $ErrorActionPreference = $prevEAP
    if ($exists) {
        return $true
    }
    # Create local branch tracking remote
    Write-Info "Creating local branch '$Branch' tracking '$Remote/$Branch'"
    $prevEAP = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
    git checkout -b "$Branch" --track "$Remote/$Branch" 2>&1 | Out-Null
    $code = $LASTEXITCODE
    $ErrorActionPreference = $prevEAP
    if ($code -ne 0) { throw "Failed to create local branch '$Branch'" }
    return $true
}

function Checkout-And-FF-Only([string]$Branch) {
    Write-Info "Checking out local branch '$Branch'"
    $prevEAP = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
    git checkout "$Branch" 2>&1 | Out-Null
    $code = $LASTEXITCODE
    $ErrorActionPreference = $prevEAP
    if ($code -ne 0) { throw "Failed to checkout '$Branch'" }

    Write-Info "Fast-forwarding '$Branch'"
    $prevEAP = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
    git pull --ff-only 2>&1 | Out-Null
    $code = $LASTEXITCODE
    $ErrorActionPreference = $prevEAP
    if ($code -ne 0) { throw "Failed to fast-forward '$Branch'" }
}

function Display-BranchDiffs([string]$Remote, [string]$Master, [string]$Dev) {
    Write-Host ""
    Write-Host "=== BRANCH DIFF SUMMARY ===" -ForegroundColor Cyan

    Write-Host ""
    Write-Host "$Remote/$Master <-> $Remote/$Dev" -ForegroundColor Cyan
    $prevEAP = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
    git diff "$Remote/$Master" "$Remote/$Dev" --stat 2>&1 | Where-Object { $_ -is [string] }
    $ErrorActionPreference = $prevEAP
}

function Update-LocalBranches([string]$Remote, [string]$Master, [string]$Dev) {
    Write-Info "Updating local protected branches from remote..."

    foreach ($Branch in @($Master, $Dev)) {
        git show-ref --verify --quiet "refs/heads/$Branch" 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) {
            $currentBranch = (git rev-parse --abbrev-ref HEAD 2>&1 | Where-Object { $_ -is [string] }).Trim()

            if ($currentBranch -ne $Branch) {
                $prevErrorAction = $ErrorActionPreference
                $ErrorActionPreference = 'Continue'

                git checkout "$Branch" 2>&1 | Out-Null
                $checkoutCode = $LASTEXITCODE

                $ErrorActionPreference = $prevErrorAction

                if ($checkoutCode -ne 0) {
                    Write-Warn "Failed to checkout '$Branch', skipping pull..."
                    continue
                }
            }

            Write-Info "Pulling '$Branch' from '$Remote/$Branch'"

            $prevErrorAction = $ErrorActionPreference
            $ErrorActionPreference = 'Continue'

            git pull --ff-only $Remote 2>&1 | Out-Null
            $pullCode = $LASTEXITCODE

            $ErrorActionPreference = $prevErrorAction

            if ($pullCode -ne 0) {
                Write-Warn "Failed to pull '$Branch', but continuing..."
            }
        }
    }
}

# ============================================================================
# MAIN LOGIC
# ============================================================================

try {
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host "Check Sync and Set Dev Branch" -ForegroundColor Cyan
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host ""

    # Step 1: Validate environment
    Write-Info "Validating environment"
    Assert-GitAvailable
    Assert-InGitRepo

    # Save original branch to restore on non-success exits
    $prevEAP = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
    $originalBranch = (git rev-parse --abbrev-ref HEAD 2>&1 | Where-Object { $_ -is [string] }).Trim()
    $ErrorActionPreference = $prevEAP

    # Step 2: Fetch latest changes
    if (-not $NoFetch) {
        Write-Info "Fetching '$Remote' (with prune)"
        $prevEAP = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
        git fetch $Remote --prune 2>&1 | Out-Null
        $code = $LASTEXITCODE
        $ErrorActionPreference = $prevEAP
        if ($code -ne 0) { throw "git fetch failed" }
    } else {
        Write-Warn "Skipping fetch due to -NoFetch"
    }

    # Step 3: Verify protected branches exist (read-only, before mutating local state)
    foreach ($b in @($Master, $Dev)) {
        if (-not (Test-RemoteBranchExists -Remote $Remote -Branch $b)) {
            throw "Remote branch '$Remote/$b' does not exist"
        }
    }

    # Step 4: Compare code changes (read-only, before mutating local state)
    Write-Info "Comparing code changes between branches..."
    $devSynced = Test-MasterInBranch -Remote $Remote -Master $Master -Branch $Dev

    if ($devSynced) {
        Write-Success "'$Remote/$Dev' has NO code differences from '$Remote/$Master'"
    } else {
        Write-Warn "'$Remote/$Dev' HAS code differences from '$Remote/$Master'"
    }

    # Step 5: Activate dev if in sync
    if ($devSynced) {
        Write-Success "'$Dev' is in sync with '$Master' (same code)."

        Write-Host ""
        Write-Host "About to:" -ForegroundColor Cyan
        Write-Host "  1. Update local '$Master' and '$Dev' from remote" -ForegroundColor DarkGray
        Write-Host "  2. Create/ensure local '$Dev' tracking '$Remote/$Dev'" -ForegroundColor DarkGray
        Write-Host "  3. Checkout local '$Dev'" -ForegroundColor DarkGray
        Write-Host "  4. Fast-forward '$Dev' with latest changes" -ForegroundColor DarkGray
        Write-Host ""

        if (-not $Force) {
            if (-not (Confirm-Action -Prompt "Proceed with syncing and activating '$Dev'? (y/n)" -Style YesNo)) {
                Write-Warn "Sync cancelled by user"
                exit 3
            }
        } else {
            Write-Info "Skipping confirmation (-Force)"
        }

        # Only mutate local state after confirmation
        Update-LocalBranches -Remote $Remote -Master $Master -Dev $Dev

        # Ensure local dev branch exists (tracking remote) BEFORE checkout
        Write-Info "Activating local '$Dev'..."
        Ensure-LocalBranch -Branch $Dev -Remote $Remote | Out-Null
        Checkout-And-FF-Only -Branch $Dev
        Write-Success "Active branch is now '$Dev'. You can create new branches from here."
        exit 0
    } else {
        Display-BranchDiffs -Remote $Remote -Master $Master -Dev $Dev

        Write-ErrorMsg "Conditions not met: '$Dev' must have no code differences from '$Master'. Aborting."
        Write-Host "Suggested next steps:" -ForegroundColor DarkGray
        Write-Host "  - View differences: git diff $Remote/$Master $Remote/$Dev" -ForegroundColor DarkGray
        Write-Host "  - Sync dev with master: git checkout $Dev; git merge $Remote/$Master" -ForegroundColor DarkGray

        # Restore original branch since we didn't succeed
        if ($originalBranch) {
            git checkout "$originalBranch" 2>&1 | Out-Null
        }
        exit 2
    }
}
catch {
    Write-ErrorMsg $_.Exception.Message

    # Restore original branch on error
    if ($originalBranch) {
        git checkout "$originalBranch" 2>&1 | Out-Null
    }
    exit 1
}
