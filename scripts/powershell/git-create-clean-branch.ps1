<#
.SYNOPSIS
    Creates a clean branch by cherry-picking commits filtered by file paths.

.DESCRIPTION
    Shows commits from the feature branch that affected specific files or directories,
    then asks for confirmation. If confirmed, creates a new branch (with -clean suffix)
    from the base branch and cherry-picks those commits. Output is in reverse order
    (oldest to newest) to show the evolution of changes. After cherry-picking, the
    script offers to push the new clean branch to the remote.

.PARAMETER FeatureBranch
    The feature branch to analyze. If not specified, uses current branch.

.PARAMETER BaseBranch
    The base branch to compare against. Defaults to 'master'.

.PARAMETER FilePaths
    Array of file or directory paths to filter commits by.
    Only commits that touched these paths will be displayed.

.PARAMETER SkipFetch
    Skip the 'git fetch origin' step. Useful if you just fetched.

.PARAMETER LastN
    Optional: Only cherry-pick the last N commits instead of all filtered commits.
    If not specified (or set to 0), you'll be prompted interactively to choose
    between cherry-picking all commits or specifying a count.

.EXAMPLE
    .\git-create-clean-branch.ps1 -FilePaths "app/connections/", "README.md"

    Shows commits that modified connections or README, then asks for confirmation before
    creating clean branch and cherry-picking.

.EXAMPLE
    .\git-create-clean-branch.ps1 -FeatureBranch feature/new-api -BaseBranch dev -FilePaths "app/api/"

    Shows commits on feature/new-api that modified api folder, then creates feature/new-api-clean
    from dev and cherry-picks those commits.

.NOTES
    Author: Generated for cr-misc-function project
    Purpose: Create clean branch by cherry-picking commits filtered by specific files/paths

    CONFLICT HANDLING:
    If cherry-pick fails mid-process, the script exits with instructions. The clean branch
    remains with successfully picked commits. You CANNOT re-run the script as-is because
    the -clean branch already exists (prevents duplicate commits).

    Your options after a conflict:
    1. Resolve manually and continue:
       - Fix conflicts in the files
       - git add <resolved-files>
       - git cherry-pick --continue
       - Manually cherry-pick remaining commits or re-run script logic

    2. Start fresh (recommended):
       - git cherry-pick --abort (if in middle of conflict)
       - git checkout <feature-branch>
       - git branch -D <feature-branch-clean>
       - Re-run the script

    3. Abort and clean up:
       - git cherry-pick --abort
       - git checkout <feature-branch>
       - git branch -D <feature-branch-clean>
#>

[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [string]$FeatureBranch,

    [Parameter(Position = 1)]
    [string]$BaseBranch = "master",

    [Parameter(Mandatory = $true, Position = 2)]
    [string[]]$FilePaths,

    [Parameter()]
    [int]$LastN = 0,

    [switch]$SkipFetch
)

# Import shared helpers
Import-Module (Join-Path $PSScriptRoot "modules\GitScriptHelpers.psm1") -Force

# ============================================================================
# MAIN LOGIC
# ============================================================================

# Step 1: Validate we're in a git repository
Write-Step "Checking git repository" "[CHECK]"
$isGitRepo = git rev-parse --is-inside-work-tree 2>&1 | Where-Object { $_ -is [string] }
if (-not $isGitRepo) {
    Write-ErrorMsg "Not a git repository. Please run this script from inside a git repo."
    exit 1
}
Write-Success "Valid git repository"

# Step 2: Determine feature branch
if (-not $FeatureBranch) {
    $FeatureBranch = git rev-parse --abbrev-ref HEAD
    if ($FeatureBranch -eq "HEAD") {
        Write-ErrorMsg "You are in detached HEAD state. Please specify -FeatureBranch explicitly."
        exit 1
    }
    Write-Info "Using current branch: $FeatureBranch"
} else {
    Write-Info "Analyzing branch: $FeatureBranch"
}

# Step 3: Fetch latest from origin (unless skipped)
if (-not $SkipFetch) {
    Write-Step "Fetching latest changes" "[FETCH]"
    git fetch origin 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-ErrorMsg "Failed to fetch from origin"
        exit 1
    }
    Write-Success "Fetched latest from origin"
} else {
    Write-Info "Skipped fetch (--SkipFetch specified)"
}

# Step 4: Validate branches exist
Write-Step "Validating branches" "[VALIDATE]"

$featureExists = git rev-parse --verify "$FeatureBranch" 2>&1 | Where-Object { $_ -is [string] }
if (-not $featureExists) {
    Write-ErrorMsg "Branch '$FeatureBranch' does not exist"
    exit 1
}

$baseExists = git rev-parse --verify "origin/$BaseBranch" 2>&1 | Where-Object { $_ -is [string] }
if (-not $baseExists) {
    Write-ErrorMsg "Remote branch 'origin/$BaseBranch' does not exist"
    exit 1
}

Write-Success "Both branches validated"

# Step 5: Build and execute commit list command
Write-Step "Finding commits that touched specified paths" "[SEARCH]"

# Build git log command with file filter
$logArgs = @(
    "log",
    "--reverse",
    "--oneline",
    "--pretty=format:%C(yellow)%h%C(reset) | %C(cyan)%an%C(reset) | %s",
    "origin/$BaseBranch..$FeatureBranch",
    "--"
)
$logArgs += $FilePaths

# Count commits first
$countArgs = @(
    "rev-list",
    "--count",
    "origin/$BaseBranch..$FeatureBranch",
    "--"
)
$countArgs += $FilePaths

$commitCount = [int](& git @countArgs)

if ($commitCount -eq 0) {
    Write-Info "No commits found that modified the specified file paths."
    Write-Host "`nFiltered by paths:" -ForegroundColor Yellow
    foreach ($path in $FilePaths) {
        Write-Host "  - $path" -ForegroundColor Yellow
    }
    exit 0
}

# Display results
Write-Host "`n$commitCount commit(s) from $FeatureBranch that touched specified files:" -ForegroundColor Cyan
Write-Host ""
Write-Host "Clean branch will be created as: $FeatureBranch-clean from origin/$BaseBranch" -ForegroundColor Magenta
Write-Host ""
Write-Host "Filtered by paths:" -ForegroundColor Yellow
foreach ($path in $FilePaths) {
    Write-Host "  - $path" -ForegroundColor Yellow
}
Write-Host ""
Write-Host "No. | Commit Hash | Author | Message" -ForegroundColor DarkGray
Write-Host "-------------------------------------------------------------" -ForegroundColor DarkGray

$commits = @(& git @logArgs)
for ($i = 0; $i -lt $commits.Count; $i++) {
    $num = $commits.Count - $i
    Write-Host "$num. $($commits[$i])" -ForegroundColor White
}

Write-Host ""
Write-Host ""

# Step 6: Ask whether to cherry-pick all or last N commits
$commitsToCherry = $commitCount
[int]$parsedN = 0
if ($LastN -gt 0) {
    # If -LastN parameter was specified, use it
    if ($LastN -gt $commitCount) {
        Write-ErrorMsg "LastN ($LastN) is greater than total filtered commits ($commitCount)"
        exit 1
    }
    $commitsToCherry = $LastN
    Write-Host "Using last $LastN commit(s) from filtered results" -ForegroundColor Yellow
} else {
    # Otherwise, prompt the user interactively
    Write-Host "Total filtered commits: $commitCount" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Options:" -ForegroundColor Yellow
    Write-Host "  [a] Cherry-pick all $commitCount commit(s)" -ForegroundColor Yellow
    Write-Host "  [n] Cherry-pick last N commit(s) only" -ForegroundColor Yellow
    Write-Host ""
    while ($true) {
        $cherryChoice = Read-Host "Select option (a/n)"

        if ($cherryChoice -eq 'n' -or $cherryChoice -eq 'N') {
            $lastNInput = Read-Host "How many last commit(s) to cherry-pick? (1-$commitCount)"

            # Validate input
            if (-not [int]::TryParse($lastNInput, [ref]$parsedN)) {
                Write-ErrorMsg "Invalid number entered: $lastNInput"
                exit 1
            }

            if ($parsedN -lt 1 -or $parsedN -gt $commitCount) {
                Write-ErrorMsg "Number must be between 1 and $commitCount"
                exit 1
            }

            $commitsToCherry = $parsedN

            Write-Host ""
            Write-Host "Will cherry-pick last $commitsToCherry commit(s)" -ForegroundColor Cyan
            break
        } elseif ($cherryChoice -eq 'a' -or $cherryChoice -eq 'A') {
            break
        } else {
            Write-Warn "Invalid option: '$cherryChoice'. Please enter 'a' or 'n'."
        }
    }
}

Write-Host ""

# Step 7: Confirm before creating branch and cherry-picking
$cleanBranchName = "$FeatureBranch-clean"
Write-Host "This will create branch '$cleanBranchName' and cherry-pick $commitsToCherry commit(s)" -ForegroundColor Yellow
Write-Host ""
if (-not (Confirm-Action -Prompt "Continue? (y/N)" -Style YesNo)) {
    Write-Info "Operation cancelled. No changes made."
    exit 0
}

# Step 7b: Check for uncommitted changes
$dirtyFiles = git status --porcelain 2>&1 | Where-Object { $_ -is [string] }
if (-not [string]::IsNullOrWhiteSpace($dirtyFiles)) {
    Write-ErrorMsg "You have uncommitted changes. Please commit or stash them first."
    Write-Host "`nUncommitted files:" -ForegroundColor Yellow
    $dirtyFiles -split "`n" | ForEach-Object { Write-Host "  $_" -ForegroundColor Yellow }
    exit 1
}

# Step 8: Create clean branch
Write-Step "Creating clean branch: $cleanBranchName" "[CREATE]"

# Check if clean branch already exists locally
$cleanBranchExists = git rev-parse --verify "$cleanBranchName" 2>&1 | Where-Object { $_ -is [string] }
if ($cleanBranchExists) {
    Write-ErrorMsg "Branch '$cleanBranchName' already exists locally. Please delete it first or use a different name."
    exit 1
}

# Check if clean branch exists remotely
$remoteBranchExists = git ls-remote --heads origin "$cleanBranchName" 2>&1 | Where-Object { $_ -is [string] }
if ($remoteBranchExists) {
    Write-ErrorMsg "Branch '$cleanBranchName' already exists on remote. Please delete it first or use a different name."
    Write-Info "To delete remote branch: git push origin --delete $cleanBranchName"
    exit 1
}

# Create new branch from base
$originalBranch = git rev-parse --abbrev-ref HEAD 2>&1 | Where-Object { $_ -is [string] }
git checkout -b "$cleanBranchName" "origin/$BaseBranch" 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-ErrorMsg "Failed to create branch '$cleanBranchName'"
    exit 1
}

# Unset upstream tracking (branch should show as unpublished until explicitly pushed)
git branch --unset-upstream 2>&1 | Out-Null
Write-Success "Created and checked out branch: $cleanBranchName"

# Step 9: Get commit hashes and cherry-pick them
Write-Step "Cherry-picking commits" "[PICK]"

$hashArgs = @(
    "rev-list",
    "--reverse",
    "origin/$BaseBranch..$FeatureBranch",
    "--"
)
$hashArgs += $FilePaths

$commitHashes = @(& git @hashArgs)
$totalHashes = $commitHashes.Count

# If cherry-picking only last N, skip the earlier ones
$startIndex = 0
if ($commitsToCherry -lt $totalHashes) {
    $startIndex = $totalHashes - $commitsToCherry
    Write-Info "Skipping first $startIndex commit(s), cherry-picking last $commitsToCherry"
}

$successCount = 0

for ($i = $startIndex; $i -lt $commitHashes.Count; $i++) {
    $hash = $commitHashes[$i]
    Write-Host "Cherry-picking $hash..." -ForegroundColor Cyan
    git cherry-pick $hash 2>&1 | Out-Null

    if ($LASTEXITCODE -eq 0) {
        $successCount++
        Write-Host "  [OK] Successfully picked $hash" -ForegroundColor Green
    } else {
        Write-Host "  [ERROR] Failed to pick $hash" -ForegroundColor Red
        Write-Host "  Conflict detected. Resolve conflicts and run:" -ForegroundColor Yellow
        Write-Host "    git cherry-pick --continue" -ForegroundColor Yellow
        Write-Host "  Or skip this commit:" -ForegroundColor Yellow
        Write-Host "    git cherry-pick --skip" -ForegroundColor Yellow
        Write-Host "  Or abort and clean up:" -ForegroundColor Yellow
        Write-Host "    git cherry-pick --abort" -ForegroundColor Yellow
        Write-Host "    git checkout $originalBranch" -ForegroundColor Yellow
        Write-Host "    git branch -D $cleanBranchName" -ForegroundColor Yellow
        Write-Info "Successfully picked $successCount of $($commitHashes.Count - $startIndex) commits before failure."
        exit 1
    }
}

Write-Host ""
Write-Success "Cherry-pick complete: $successCount commit(s) picked"
Write-Success "New clean branch created: $cleanBranchName"
Write-Host ""

# Step 10: Push clean branch to remote
Write-Step "Pushing clean branch to remote" "[PUSH]"
Write-Host ""
Write-Host "This will push '$cleanBranchName' to origin and set up tracking." -ForegroundColor Yellow
Write-Host "IMPORTANT: This creates a NEW branch on remote, does NOT push to $BaseBranch" -ForegroundColor Yellow
Write-Host ""
if (Confirm-Action -Prompt "Push branch to remote? (y/N)" -Style YesNo) {
    git push origin "$cleanBranchName" 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-ErrorMsg "Failed to push branch to remote"
        Write-Info "You can push manually later: git push -u origin $cleanBranchName"
    } else {
        Write-Success "Branch pushed to remote"
        Write-Host ""
        Write-Info "Next step: Create Pull Request on GitHub/GitLab"
        Write-Info "  From: $cleanBranchName"
        Write-Info "  To: $BaseBranch"
    }
} else {
    Write-Info "Skipped push. You can push manually later:"
    Write-Host "  git push -u origin $cleanBranchName" -ForegroundColor Cyan
}

Write-Host ""
Write-Info "You are now on branch: $cleanBranchName"
