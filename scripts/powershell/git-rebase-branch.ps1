<#
.SYNOPSIS
    Rebase a feature branch onto master and prepare for clean merge.

.DESCRIPTION
    This script guides you through rebasing a feature branch onto master branch,
    ensuring only your feature commits are included. It helps create a clean
    commit history by dropping unrelated commits from other branches.

.PARAMETER FeatureBranch
    The name of the feature/fix branch to rebase (e.g., 'feature/foo', 'fix/DA-1234').
    If not provided, uses the current branch.

.PARAMETER BaseBranch
    The base branch to rebase onto (default: 'master').
    Can be 'master', 'main', 'dev', etc.

.PARAMETER SkipFetch
    Skip fetching from origin. Use this if you've already fetched recently.

.EXAMPLE
    .\git-rebase-branch.ps1 -FeatureBranch "feature/foo"
    Rebases feature/foo onto master.

.EXAMPLE
    .\git-rebase-branch.ps1 -FeatureBranch "fix/DA-1234" -BaseBranch "dev"
    Rebases fix/DA-1234 onto dev branch.

.EXAMPLE
    .\git-rebase-branch.ps1
    Rebases current branch onto master.

.NOTES
    Author: Development Team
    Version: 1.0.0

    This script performs the following steps:
    1. Fetches latest changes from origin
    2. Checks out the feature branch
    3. Rebases feature branch onto base branch
    4. Verifies commits that will be merged
    5. Provides instructions for completing the merge

.LINK
    https://git-scm.com/docs/git-rebase
#>

[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [string]$FeatureBranch,

    [Parameter(Position = 1)]
    [string]$BaseBranch = "master",

    [switch]$SkipFetch
)

# Set strict mode and error handling
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# Import shared helpers
Import-Module (Join-Path $PSScriptRoot "modules\GitScriptHelpers.psm1") -Force

# ============================================================================
# HELPER FUNCTIONS - Status messages and Git utilities
# ============================================================================

function Test-GitRepository {
    git rev-parse --git-dir 2>&1 | Out-Null
    return $LASTEXITCODE -eq 0
}

function Get-CurrentBranch {
    try {
        $branch = git branch --show-current 2>&1 | Where-Object { $_ -is [string] }
    } catch {
        throw "Failed to get current branch"
    }
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to get current branch"
    }
    return $branch
}

function Test-BranchExists {
    param([Parameter(Mandatory)][string]$Branch)
    git rev-parse --verify "$Branch" 2>&1 | Out-Null
    return $LASTEXITCODE -eq 0
}

function Test-RemoteBranchExists {
    param([Parameter(Mandatory)][string]$Branch)
    git ls-remote --heads origin "$Branch" 2>&1 | Out-Null
    return $LASTEXITCODE -eq 0
}

function Get-UncommittedChanges {
    try {
        $status = git status --porcelain 2>&1 | Where-Object { $_ -is [string] }
    } catch {
        return $false
    }
    return -not [string]::IsNullOrWhiteSpace($status)
}

# ============================================================================
# MAIN LOGIC
# ============================================================================

try {
    Write-Host "`n" -NoNewline
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host "Git Rebase Branch - Clean Merge Helper" -ForegroundColor Cyan
    Write-Host "============================================================" -ForegroundColor Cyan

    # Step 0: Verify we're in a git repository
    Write-Step "Verifying git repository" "[CHECK]"
    if (-not (Test-GitRepository)) {
        throw "Not a git repository. Please run this script from within a git repository."
    }
    Write-Success "Git repository verified"

    # Determine feature branch
    if (-not $FeatureBranch) {
        $FeatureBranch = Get-CurrentBranch
        Write-Info "Using current branch: $FeatureBranch"
    }

    # Guard: prevent rebasing a branch onto itself
    if ($FeatureBranch -eq $BaseBranch) {
        Write-ErrorMsg "Feature branch '$FeatureBranch' is the same as base branch '$BaseBranch'. Nothing to rebase."
        exit 1
    }

    # Step 1: Check for uncommitted changes
    Write-Step "Checking for uncommitted changes" "[FILES]"
    if (Get-UncommittedChanges) {
        Write-ErrorMsg "You have uncommitted changes. Please commit or stash them first."
        Write-Host "`nRun one of these commands:"
        Write-Host "  git add . && git commit -m 'Your message'" -ForegroundColor Yellow
        Write-Host "  git stash" -ForegroundColor Yellow
        exit 1
    }
    Write-Success "Working directory is clean"

    # Step 2: Fetch from origin
    if (-not $SkipFetch) {
        Write-Step "Fetching latest changes from origin" "[FETCH]"
        git fetch origin --prune 2>&1 | Out-Null
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to fetch from origin"
        }
        Write-Success "Fetched latest changes"
    } else {
        Write-Info "Skipping fetch (using existing remote refs)"
    }

    # Step 3: Verify branches exist
    Write-Step "Verifying branches" "[CHECK]"

    if (-not (Test-RemoteBranchExists $BaseBranch)) {
        throw "Base branch 'origin/$BaseBranch' does not exist"
    }
    Write-Success "Base branch 'origin/$BaseBranch' exists"

    if (-not (Test-BranchExists $FeatureBranch)) {
        throw "Feature branch '$FeatureBranch' does not exist locally"
    }
    Write-Success "Feature branch '$FeatureBranch' exists"

    # Step 4: Checkout feature branch
    $currentBranch = Get-CurrentBranch
    if ($currentBranch -ne $FeatureBranch) {
        Write-Step "Checking out feature branch: $FeatureBranch" "[SWITCH]"
        git checkout $FeatureBranch 2>&1 | Out-Null
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to checkout branch '$FeatureBranch'"
        }
        Write-Success "Checked out '$FeatureBranch'"
    } else {
        Write-Info "Already on branch '$FeatureBranch'"
    }

    # Step 5: Show commits that will be rebased
    Write-Step "Commits to be rebased" "[COMMITS]"

    [int]$commitCount = git rev-list --count "origin/$BaseBranch..$FeatureBranch"

    if ($commitCount -eq 0) {
        Write-Info "No commits to rebase. $FeatureBranch is up to date with origin/$BaseBranch"
        exit 0
    }

    Write-Host "`n$commitCount commit(s) from $FeatureBranch will be replayed onto origin/$BaseBranch :" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Commit Hash | Author | Message" -ForegroundColor DarkGray
    Write-Host "-------------------------------------------------------------" -ForegroundColor DarkGray

    git log --reverse --oneline --pretty=format:"%C(yellow)%h%C(reset) | %C(cyan)%an%C(reset) | %s" "origin/$BaseBranch..$FeatureBranch"

    Write-Host ""
    Write-Host ""

    # Step 6: Confirm rebase
    Write-Host "This will:" -ForegroundColor Yellow
    Write-Host "  1. Replay your feature commits on top of origin/$BaseBranch" -ForegroundColor Yellow
    Write-Host "  2. Drop any commits that came from other branches" -ForegroundColor Yellow
    Write-Host "  3. May cause conflicts that you'll need to resolve" -ForegroundColor Yellow
    Write-Host ""
    $confirmation = $null
    while ($true) {
        $confirmation = Read-Host "Continue with rebase? (y/N)"
        $confirmation = $confirmation.Trim().ToLower()
        if ($confirmation -eq 'y' -or $confirmation -eq 'n') { break }
        if ([string]::IsNullOrWhiteSpace($confirmation)) { $confirmation = 'n'; break }
        Write-Warn "Invalid input: '$confirmation'. Please enter 'y' or 'n'."
    }

    if ($confirmation -eq 'n' -or $confirmation -eq 'N') {
        Write-Info "Rebase cancelled by user"
        exit 0
    }

    # Step 7: Create safety backup
    Write-Step "Creating safety backup branch" "[BACKUP]"
    $backupBranchName = "backup/$FeatureBranch-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
    git branch $backupBranchName 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to create backup branch '$backupBranchName'"
    }
    Write-Success "Backup created: $backupBranchName"
    Write-Info "If rebase fails, restore with: git reset --hard $backupBranchName"

    # Step 8: Perform rebase
    Write-Step "Rebasing $FeatureBranch onto origin/$BaseBranch" "[REBASE]"
    git rebase "origin/$BaseBranch" 2>&1 | Tee-Object -Variable rebaseOutput | Out-Null

    if ($LASTEXITCODE -ne 0) {
        Write-ErrorMsg "Rebase encountered conflicts!"
        # Show git's error output
        $rebaseOutput | ForEach-Object { Write-Host "  $_" -ForegroundColor Red }
        Write-Host "`n[HELP] To resolve conflicts:"
        Write-Host "  1. Fix conflicts in the listed files" -ForegroundColor Yellow
        Write-Host "  2. Run: git add <resolved-files>" -ForegroundColor Yellow
        Write-Host "  3. Run: git rebase --continue" -ForegroundColor Yellow

        Write-Host "`n[INFO] Understanding Current vs Incoming:" -ForegroundColor Cyan
        Write-Host "  Current  = $BaseBranch (base branch being rebased onto)" -ForegroundColor White
        Write-Host "  Incoming = $FeatureBranch (your feature commits being replayed)" -ForegroundColor White
        Write-Host "  Tip: Usually keep 'Incoming' to preserve your feature changes" -ForegroundColor Yellow

        Write-Host "`n[WARNING] To abort rebase: git rebase --abort" -ForegroundColor Red
        exit 1
    }

    Write-Success "Rebase completed successfully!"

    # Step 9: Verify rebased commits
    Write-Step "Verifying rebased commits" "[VERIFY]"

    # Count rebased commits
    [int]$rebasedCount = (git rev-list --count "origin/$BaseBranch..HEAD")

    Write-Host "`n$rebasedCount commit(s) ready to merge into $BaseBranch :" -ForegroundColor Green
    Write-Host ""
    Write-Host "Commit Hash | Author | Message" -ForegroundColor DarkGray
    Write-Host "-------------------------------------------------------------" -ForegroundColor DarkGray
    git log --pretty=format:"%C(yellow)%h%C(reset) | %C(cyan)%an%C(reset) | %s" "origin/$BaseBranch..HEAD"
    Write-Host ""
    Write-Host ""
    Write-Success "Only your feature commits are present ($rebasedCount commit(s))"

    # Step 9b: Offer to clean up backup branch
    Write-Host ""
    $cleanupBackup = $null
    while ($true) {
        $cleanupBackup = Read-Host "Rebase verified. Delete backup branch '$backupBranchName'? (y/N)"
        $cleanupBackup = $cleanupBackup.Trim().ToLower()
        if ($cleanupBackup -eq 'y' -or $cleanupBackup -eq 'n') { break }
        if ([string]::IsNullOrWhiteSpace($cleanupBackup)) { $cleanupBackup = 'n'; break }
        Write-Warn "Invalid input. Please enter 'y' or 'n'."
    }
    if ($cleanupBackup -eq 'y' -or $cleanupBackup -eq 'Y') {
        git branch -D $backupBranchName 2>&1 | Out-Null
        Write-Success "Backup branch deleted"
    } else {
        Write-Info "Backup retained. Clean up later with: git branch -D $backupBranchName"
    }

    # Step 10: Provide next steps
    Write-Host "`n" -NoNewline
    Write-Host "============================================================" -ForegroundColor Green
    Write-Host "[SUCCESS] Rebase Complete - Next Steps" -ForegroundColor Green
    Write-Host "============================================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Your backup branch is: $backupBranchName" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Option A: Direct merge to $BaseBranch" -ForegroundColor Cyan
    Write-Host "  git checkout $BaseBranch" -ForegroundColor White
    Write-Host "  git merge $FeatureBranch" -ForegroundColor White
    Write-Host "  git push origin $BaseBranch" -ForegroundColor White
    Write-Host ""
    Write-Host "Option B: Create Pull Request (Recommended)" -ForegroundColor Cyan
    Write-Host "  git push --force-with-lease origin $FeatureBranch" -ForegroundColor White
    Write-Host "  Then create PR on GitHub/GitLab with Squash and Merge" -ForegroundColor White
    Write-Host ""
    Write-Host "[NOTE] Use --force-with-lease to update remote branch after rebase" -ForegroundColor Yellow
    Write-Host ""

} catch {
    Write-Host "`n" -NoNewline
    Write-ErrorMsg "Script failed: $_"
    exit 1
} finally {
    # Detect if a rebase is still in progress (e.g., from Ctrl+C)
    try {
        $gitDir = git rev-parse --git-dir 2>&1 | Where-Object { $_ -is [string] }
        $rebaseMergeDir = Join-Path $gitDir "rebase-merge"
        $rebaseApplyDir = Join-Path $gitDir "rebase-apply"
        if ((Test-Path $rebaseMergeDir) -or (Test-Path $rebaseApplyDir)) {
            Write-Host "`n[WARNING] A rebase is still in progress." -ForegroundColor Red
            Write-Host "  To continue:  fix conflicts, git add <files>, then git rebase --continue" -ForegroundColor Yellow
            Write-Host "  To abort:     git rebase --abort" -ForegroundColor Yellow
            if ($backupBranchName) {
                Write-Host "  To hard-reset: git reset --hard $backupBranchName" -ForegroundColor Yellow
            }
        }
    } catch {
        # Silently ignore - not in a git repo or other error
    }
}
