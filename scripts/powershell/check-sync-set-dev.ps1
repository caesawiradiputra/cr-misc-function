<#!
.SYNOPSIS
    Checks if remote dev and sit are in sync with remote master and, if yes, activates local dev for new branch creation.

.DESCRIPTION
    - Fetches refs (unless -NoFetch) and validates existence of remote branches.
    - "In sync with master" means: master is an ancestor of the target branch (or exactly equal with -StrictEqual).
    - If BOTH dev and sit are in sync with master, checks out local dev (creating/tracking it if missing) and fast-forwards.
    - Exits with code 0 on success (dev set active), non-zero otherwise.

.PARAMETER Remote
    Git remote name. Default: origin.

.PARAMETER Master
    Master branch name. Default: master.

.PARAMETER Dev
    Dev branch name. Default: dev.

.PARAMETER Sit
    SIT branch name. Default: sit.

.PARAMETER StrictEqual
    Require branch tip to equal master tip (instead of master being an ancestor).

.PARAMETER NoFetch
    Skip fetching remote refs.

.EXAMPLE
    .\scripts\powershell\check-sync-set-dev.ps1

.EXAMPLE
    .\scripts\powershell\check-sync-set-dev.ps1 -Remote origin -Master master -Dev dev -Sit sit -StrictEqual

.NOTES
    Requires Git to be installed and the script to be run inside a Git repository.
#>

[CmdletBinding()]
param(
    [string]$Remote = "origin",
    [string]$Master = "master",
    [string]$Dev    = "dev",
    [string]$Sit    = "sit",
    [switch]$StrictEqual,
    [switch]$NoFetch
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

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

function Test-MasterInBranch([string]$MasterSha, [string]$Remote, [string]$Branch, [switch]$StrictEqual) {
    if ($StrictEqual) {
        $branchSha = Get-RemoteSha -Remote $Remote -Branch $Branch
        return ($branchSha -eq $MasterSha)
    } else {
        git merge-base --is-ancestor $MasterSha "$Remote/$Branch" 2>$null | Out-Null
        return ($LASTEXITCODE -eq 0)
    }
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

try {
    Write-Info "Validating environment"
    Assert-GitAvailable
    Assert-InGitRepo

    if (-not $NoFetch) {
        Write-Info "Fetching '$Remote' (with prune)"
        git fetch $Remote --prune | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "git fetch failed" }
    } else {
        Write-Warn "Skipping fetch due to -NoFetch"
    }

    # ! Validate remote branches exist
    foreach ($b in @($Master, $Dev, $Sit)) {
        if (-not (Test-RemoteBranchExists -Remote $Remote -Branch $b)) {
            throw "Remote branch '$Remote/$b' does not exist"
        }
    }

    $masterSha = Get-RemoteSha -Remote $Remote -Branch $Master

    # * Check sync status
    $devSynced = Test-MasterInBranch -MasterSha $masterSha -Remote $Remote -Branch $Dev -StrictEqual:$StrictEqual
    $sitSynced = Test-MasterInBranch -MasterSha $masterSha -Remote $Remote -Branch $Sit -StrictEqual:$StrictEqual

    if ($StrictEqual) {
        Write-Info "Strict equality mode: branches must equal '$Remote/$Master' tip"
    } else {
        Write-Info "Ancestor mode: '$Remote/$Master' must be contained in branch history"
    }

    if ($devSynced) { Write-Okay "'$Remote/$Dev' is in sync with '$Remote/$Master'" }
    else { Write-Warn "'$Remote/$Dev' is NOT in sync with '$Remote/$Master'" }

    if ($sitSynced) { Write-Okay "'$Remote/$Sit' is in sync with '$Remote/$Master'" }
    else { Write-Warn "'$Remote/$Sit' is NOT in sync with '$Remote/$Master'" }

    if ($devSynced -and $sitSynced) {
        Write-Info "Both '$Dev' and '$Sit' are in sync. Activating local '$Dev'..."
        Ensure-LocalBranch -Branch $Dev -Remote $Remote | Out-Null
        Checkout-And-FF-Only -Branch $Dev
        Write-Okay "Active branch is now '$Dev'. You can create new branches from here."
        exit 0
    } else {
        Write-Err "Conditions not met: dev and sit must be in sync with master. Aborting."
        Write-Host "Suggested next steps:" -ForegroundColor DarkGray
        if (-not $devSynced) { Write-Host "  - Update '$Dev' with '$Master': git checkout $Dev; git pull --ff-only; git merge $Remote/$Master" -ForegroundColor DarkGray }
        if (-not $sitSynced) { Write-Host "  - Update '$Sit' with '$Master': git checkout $Sit; git pull --ff-only; git merge $Remote/$Master" -ForegroundColor DarkGray }
        exit 2
    }
}
catch {
    Write-Err $_.Exception.Message
    exit 1
}
