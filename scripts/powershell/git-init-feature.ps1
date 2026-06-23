<#
.SYNOPSIS
    Initialize a new feature branch from a base branch (default: dev).

.DESCRIPTION
    Creates a new feature branch following the naming convention fea/<TICKET>-<description>.
    The script validates the working tree is clean, fetches latest from origin, and
    optionally verifies dev is synced with master before creating the branch.

    Workflow position: Runs after git-check-sync-set-dev.ps1 and before development work.

.PARAMETER BranchName
    Full branch name (e.g., 'fea/DA-1234-add-caching'). If not provided, prompts interactively.

.PARAMETER BaseBranch
    Base branch to create from. Default: dev.

.PARAMETER SkipFetch
    Skip fetching from origin. Useful if you just fetched.

.PARAMETER SkipSyncCheck
    Skip checking if dev is in sync with master.

.PARAMETER Force
    Skip confirmation prompts.

.EXAMPLE
    .\git-init-feature.ps1 -BranchName "fea/DA-1234-add-caching"

.EXAMPLE
    .\git-init-feature.ps1
    Prompts for branch name interactively.

.EXAMPLE
    .\git-init-feature.ps1 -BaseBranch master -SkipSyncCheck
    Creates from master without sync check.

.NOTES
    Author: Development Team
    Naming convention: fea/<TICKET>-<description> (e.g., fea/DA-1234-add-caching)
#>

[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [string]$BranchName,

    [Parameter(Position = 1)]
    [string]$BaseBranch = "dev",

    [switch]$SkipFetch,
    [switch]$SkipSyncCheck,
    [switch]$Force
)

# Import shared helpers
Import-Module (Join-Path $PSScriptRoot "modules\GitScriptHelpers.psm1") -Force

# ============================================================================
# MAIN LOGIC
# ============================================================================

Write-Host ""
Write-Host "=============================================================" -ForegroundColor Cyan
Write-Host "Initialize Feature Branch" -ForegroundColor Cyan
Write-Host "=============================================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Validate git repository
Write-Step "Verifying git repository" "[CHECK]"
$null = git rev-parse --is-inside-work-tree 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-ErrorMsg "Not inside a Git repository. Please run from within a Git working directory."
    exit 1
}
Write-Success "Git repository verified"

# Step 2: Check for uncommitted changes
Write-Step "Checking working directory" "[CHECK]"
$dirtyFiles = git status --porcelain 2>&1 | Where-Object { $_ -is [string] }
if ($dirtyFiles) {
    Write-ErrorMsg "Working directory has uncommitted changes. Please commit or stash first."
    $dirtyFiles | ForEach-Object { Write-Host "  $_" -ForegroundColor Red }
    exit 1
}
Write-Success "Working directory is clean"

# Step 3: Fetch latest from origin
if (-not $SkipFetch) {
    Write-Step "Fetching latest changes" "[FETCH]"
    git fetch origin --prune 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-ErrorMsg "Failed to fetch from origin"
        exit 1
    }
    Write-Success "Fetched latest from origin"
} else {
    Write-Info "Skipped fetch (-SkipFetch specified)"
}

# Step 4: Verify base branch exists
Write-Step "Verifying base branch" "[CHECK]"
$baseExists = git rev-parse --verify "origin/$BaseBranch" 2>&1 | Where-Object { $_ -is [string] }
if (-not $baseExists) {
    Write-ErrorMsg "Remote branch 'origin/$BaseBranch' does not exist"
    exit 1
}
Write-Success "Base branch 'origin/$BaseBranch' verified"

# Step 5: Optional sync check (dev vs master)
if (-not $SkipSyncCheck -and $BaseBranch -eq "dev") {
    Write-Step "Checking dev-master sync" "[SYNC]"
    $diff = git diff "origin/master" "origin/dev" 2>&1 | Where-Object { $_ -is [string] }
    if ($diff) {
        Write-Warn "origin/dev has code differences from origin/master"
        Write-Host "  Run git-check-sync-set-dev.ps1 first to sync dev with master" -ForegroundColor Yellow
        Write-Host ""
        if (-not (Confirm-Action -Prompt "Continue anyway? (y/n)" -Style YesNo)) {
            Write-Info "Aborted. Run git-check-sync-set-dev.ps1 to sync first."
            exit 1
        }
    } else {
        Write-Success "origin/dev is in sync with origin/master"
    }
}

# Step 6: Get branch name (prompt if not provided)
if (-not $BranchName) {
    Write-Step "Branch name" "[INPUT]"
    Write-Host "Naming convention: fea/<TICKET>-<description>" -ForegroundColor Yellow
    Write-Host "Example: fea/DA-1234-add-caching" -ForegroundColor Yellow
    Write-Host ""

    while ($true) {
        $BranchName = Read-Host "Enter branch name"
        $BranchName = $BranchName.Trim()

        if ([string]::IsNullOrWhiteSpace($BranchName)) {
            Write-Warn "Branch name cannot be empty. Please enter a name."
            continue
        }

        # Validate naming convention (warn but don't block)
        if ($BranchName -notmatch "^(fea|fix|hotfix|chore|refactor)/[A-Z]+-\d+") {
            Write-Warn "Branch name doesn't follow convention: fea/<TICKET>-<description>"
            if (-not (Confirm-Action -Prompt "Use this name anyway? (y/n)" -Style YesNo)) {
                $BranchName = $null
                continue
            }
        }
        break
    }
}

# Step 7: Check branch doesn't already exist
Write-Step "Validating branch name" "[CHECK]"

$localExists = git rev-parse --verify "$BranchName" 2>&1 | Where-Object { $_ -is [string] }
if ($LASTEXITCODE -eq 0 -and $localExists) {
    Write-ErrorMsg "Branch '$BranchName' already exists locally"
    exit 1
}

$remoteExists = git ls-remote --heads origin "$BranchName" 2>&1 | Where-Object { $_ -is [string] }
if ($remoteExists) {
    Write-ErrorMsg "Branch '$BranchName' already exists on remote"
    exit 1
}
Write-Success "Branch name '$BranchName' is available"

# Step 8: Confirm and create
Write-Host ""
Write-Host "This will:" -ForegroundColor Yellow
Write-Host "  - Create branch '$BranchName' from origin/$BaseBranch" -ForegroundColor Yellow
Write-Host "  - Check out the new branch" -ForegroundColor Yellow
Write-Host "  - Push to origin with tracking" -ForegroundColor Yellow
Write-Host ""

if (-not $Force) {
    if (-not (Confirm-Action -Prompt "Create feature branch? (y/n)" -Style YesNo)) {
        Write-Info "Operation cancelled"
        exit 0
    }
}

# Step 9: Create branch
Write-Step "Creating branch" "[CREATE]"
$originalBranch = git rev-parse --abbrev-ref HEAD 2>&1 | Where-Object { $_ -is [string] }

git checkout -b "$BranchName" "origin/$BaseBranch" 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-ErrorMsg "Failed to create branch '$BranchName'"
    exit 1
}
Write-Success "Created and checked out branch: $BranchName"

# Step 10: Push to remote
Write-Step "Pushing to remote" "[PUSH]"
git push -u origin "$BranchName" 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Warn "Failed to push to remote. You can push manually later:"
    Write-Host "  git push -u origin $BranchName" -ForegroundColor Cyan
} else {
    Write-Success "Branch pushed to origin with tracking"
}

# Summary
Write-Host ""
Write-Host "=============================================================" -ForegroundColor Green
Write-Host "[SUCCESS] Feature branch ready" -ForegroundColor Green
Write-Host "=============================================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Branch: $BranchName" -ForegroundColor White
Write-Host "  Base:   origin/$BaseBranch" -ForegroundColor White
Write-Host "  Previous branch: $originalBranch" -ForegroundColor DarkGray
Write-Host ""
Write-Host "Start working on your feature. When ready:" -ForegroundColor Cyan
Write-Host "  - Commit changes: /commit" -ForegroundColor White
Write-Host "  - Rebase onto base: .\git-rebase-branch.ps1" -ForegroundColor White
Write-Host "  - Create PR on GitHub/GitLab" -ForegroundColor White
