<#!
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
    [switch]$NoFetch
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# ============================================================================
# HELPER FUNCTIONS - Status messages with color coding
# ============================================================================

function Write-Info($msg)  { Write-Host "[INFO]  $msg" -ForegroundColor Cyan }
function Write-Warn($msg)  { Write-Host "[WARN]  $msg" -ForegroundColor Yellow }
function Write-Okay($msg)  { Write-Host "[OK]    $msg" -ForegroundColor Green }
function Write-Err($msg)   { Write-Host "[ERROR] $msg" -ForegroundColor Red }

function Assert-GitAvailable {
    if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
        throw "Git is not installed or not available in PATH."
    }
}

function Assert-InGitRepo {
    git rev-parse --is-inside-work-tree 2>$null | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Current directory is not a Git repository."
    }
}

function Test-RemoteBranchExists([string]$Remote, [string]$Branch) {
    git show-ref --verify --quiet "refs/remotes/$Remote/$Branch"
    return ($LASTEXITCODE -eq 0)
}

function Get-RemoteSha([string]$Remote, [string]$Branch) {
    $sha = (git rev-parse "$Remote/$Branch" 2>$null).Trim()
    if ($LASTEXITCODE -ne 0 -or -not $sha) {
        throw "Failed to resolve $Remote/$Branch"
    }
    return $sha
}

function Test-MasterInBranch([string]$Remote, [string]$Master, [string]$Branch) {
    # Check if branches have the same code changes (no diff means sync)
    $diff = git diff "$Remote/$Master" "$Remote/$Branch" 2>$null
    return -not $diff
}

function Ensure-LocalBranch([string]$Branch, [string]$Remote) {
    git show-ref --verify --quiet "refs/heads/$Branch"
    if ($LASTEXITCODE -eq 0) {
        return $true
    }
    # Create local branch tracking remote
    Write-Info "Creating local branch '$Branch' tracking '$Remote/$Branch'"
    git checkout -b $Branch --track "$Remote/$Branch" | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Failed to create local branch '$Branch'" }
    return $true
}

function Checkout-And-FF-Only([string]$Branch) {
    Write-Info "Checking out local branch '$Branch'"
    git checkout $Branch | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Failed to checkout '$Branch'" }

    Write-Info "Fast-forwarding '$Branch'"
    git pull --ff-only | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Failed to fast-forward '$Branch'" }
}

function Display-BranchDiffs([string]$Remote, [string]$Master, [string]$Dev) {
    Write-Host ""
    Write-Host "=== BRANCH DIFF SUMMARY ===" -ForegroundColor Cyan

    Write-Host ""
    Write-Host "$Remote/$Master <-> $Remote/$Dev" -ForegroundColor Cyan
    git diff "$Remote/$Master" "$Remote/$Dev" --stat 2>$null
}

function Update-LocalBranches([string]$Remote, [string]$Master, [string]$Dev) {
    Write-Info "Updating local protected branches from remote..."

    foreach ($Branch in @($Master, $Dev)) {
        git show-ref --verify --quiet "refs/heads/$Branch" 2>$null
        if ($LASTEXITCODE -eq 0) {
            $currentBranch = (git rev-parse --abbrev-ref HEAD 2>$null).Trim()

            if ($currentBranch -ne $Branch) {
                $prevErrorAction = $ErrorActionPreference
                $ErrorActionPreference = 'Continue'

                git checkout $Branch 2>$null | Out-Null
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

            git pull $Remote 2>$null | Out-Null
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

    # Step 2: Fetch latest changes
    if (-not $NoFetch) {
        Write-Info "Fetching '$Remote' (with prune)"
        git fetch $Remote --prune | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "git fetch failed" }
    } else {
        Write-Warn "Skipping fetch due to -NoFetch"
    }

    Update-LocalBranches -Remote $Remote -Master $Master -Dev $Dev

    # Step 3: Verify protected branches exist
    foreach ($b in @($Master, $Dev)) {
        if (-not (Test-RemoteBranchExists -Remote $Remote -Branch $b)) {
            throw "Remote branch '$Remote/$b' does not exist"
        }
    }

    # Step 4: Compare code changes
    Write-Info "Comparing code changes between branches..."
    $devSynced = Test-MasterInBranch -Remote $Remote -Master $Master -Branch $Dev

    if ($devSynced) {
        Write-Okay "'$Remote/$Dev' has NO code differences from '$Remote/$Master'"
    } else {
        Write-Warn "'$Remote/$Dev' HAS code differences from '$Remote/$Master'"
    }

    # Step 5: Activate dev if in sync
    if ($devSynced) {
        Write-Okay "'$Dev' is in sync with '$Master' (same code)."

        Display-BranchDiffs -Remote $Remote -Master $Master -Dev $Dev

        Write-Host ""
        Write-Host "About to:" -ForegroundColor Cyan
        Write-Host "  1. Create/ensure local '$Dev' tracking '$Remote/$Dev'" -ForegroundColor DarkGray
        Write-Host "  2. Checkout local '$Dev'" -ForegroundColor DarkGray
        Write-Host "  3. Fast-forward '$Dev' with latest changes" -ForegroundColor DarkGray
        Write-Host ""
        $confirm = Read-Host "Proceed with syncing and activating '$Dev'? (y/n)"
        if ($confirm -ne 'y' -and $confirm -ne 'Y') {
            Write-Warn "Sync cancelled by user"
            exit 0
        }
        Write-Info "Activating local '$Dev'..."
        Ensure-LocalBranch -Branch $Dev -Remote $Remote | Out-Null
        Checkout-And-FF-Only -Branch $Dev
        Write-Okay "Active branch is now '$Dev'. You can create new branches from here."
        exit 0
    } else {
        Write-Err "Conditions not met: '$Dev' must have no code differences from '$Master'. Aborting."
        Write-Host "Suggested next steps:" -ForegroundColor DarkGray
        Write-Host "  - View differences: git diff $Remote/$Master $Remote/$Dev" -ForegroundColor DarkGray
        Write-Host "  - Sync dev with master: git checkout $Dev; git merge $Remote/$Master" -ForegroundColor DarkGray
        exit 2
    }
}
catch {
    Write-Err $_.Exception.Message
    exit 1
}
