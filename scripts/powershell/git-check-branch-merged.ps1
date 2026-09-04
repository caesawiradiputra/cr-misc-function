<#
.SYNOPSIS
    Scans all non-protected remote branches and reports which are safe to delete
    (already fully merged into a base branch).

.DESCRIPTION
    For every branch on the remote (excluding the base branch and protected branches),
    determines whether it is already fully merged into the base branch (default: dev).

    The comparison is diff-based (code content), not commit-history-based. A commit-ancestry
    check (e.g. rev-list ahead/behind) does not work here because merges to the base branch
    are typically done via squash merge - a feature branch's individual commits are never
    reachable from the base, so it would always look "ahead" even when fully merged.

    A plain full-tree `git diff origin/<base> origin/<branch>` isn't reliable either: once
    OTHER feature branches are squash-merged into the base afterward, the base moves ahead
    with unrelated changes, and a full-tree diff would flag an old (already-merged) branch as
    "different" for that reason alone. To avoid that false positive, the check is scoped to
    only the files each branch itself touched since it diverged from the base
    (`git diff <merge-base> origin/<branch>` for the file list, then `git diff origin/<base>
    origin/<branch> -- <those files>`). If that scoped diff is empty, the base's current
    version of every file the branch touched already matches the branch, regardless of what
    else has landed on the base since.

    This script only REPORTS - it never deletes, checks out, or otherwise mutates anything.
    Only remote-tracking refs are read; local branch/working-tree state is not touched.
    Intended workflow:
      1. Run this script to see which remote branches are safe to delete.
      2. Delete those branches yourself (e.g. on GitHub's web UI).
      3. Run git-clean-branches.ps1 to prune local branches whose remote was deleted.

.PARAMETER BaseBranch
    Base branch to compare against. Default: dev.

.PARAMETER Remote
    Git remote name. Default: origin.

.PARAMETER NoFetch
    Skip fetching remote refs before comparing. Uses whatever refs are currently cached.

.PARAMETER ProtectedBranches
    Branches excluded from the scan (never reported). Default: main, master, dev, sit.

.EXAMPLE
    .\git-check-branch-merged.ps1
    Scans all remote branches against origin/dev.

.EXAMPLE
    .\git-check-branch-merged.ps1 -BaseBranch master -NoFetch

.NOTES
    Exit codes:
      0 - Scan completed (see output for per-branch results; nothing was deleted)
      1 - Error (not a repo, fetch failed, missing base branch, git failure)
#>

[CmdletBinding()]
param(
    [string]$BaseBranch = "dev",

    [string]$Remote = "origin",

    [switch]$NoFetch,

    [string[]]$ProtectedBranches = @("main", "master", "dev", "sit")
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# Import shared helpers
Import-Module (Join-Path $PSScriptRoot "modules\GitScriptHelpers.psm1") -Force

# ============================================================================
# HELPER FUNCTIONS
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

function Test-RemoteRefExists([string]$Remote, [string]$Name) {
    $prevEAP = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
    git show-ref --verify --quiet "refs/remotes/$Remote/$Name" 2>&1 | Out-Null
    $code = $LASTEXITCODE
    $ErrorActionPreference = $prevEAP
    return ($code -eq 0)
}

function Test-LocalRefExists([string]$Name) {
    $prevEAP = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
    git show-ref --verify --quiet "refs/heads/$Name" 2>&1 | Out-Null
    $code = $LASTEXITCODE
    $ErrorActionPreference = $prevEAP
    return ($code -eq 0)
}

function Test-BranchMergedIntoBase {
    <#
    .SYNOPSIS
        Diff-based, merge-base-scoped check for whether $Branch is safe to delete relative to $BaseBranch.

    .OUTPUTS
        Hashtable with: Status ('Safe'|'HasChanges'|'Error'), Detail (string)
    #>
    param(
        [Parameter(Mandatory)][string]$Remote,
        [Parameter(Mandatory)][string]$BaseBranch,
        [Parameter(Mandatory)][string]$Branch
    )

    $prevEAP = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
    $mergeBase = (git merge-base "$Remote/$BaseBranch" "$Remote/$Branch" 2>&1 | Where-Object { $_ -is [string] })
    $code = $LASTEXITCODE
    $ErrorActionPreference = $prevEAP
    if ($code -ne 0 -or -not $mergeBase) {
        return @{ Status = 'Error'; Detail = 'No common ancestor with base branch' }
    }
    $mergeBase = ($mergeBase | Select-Object -First 1).Trim()

    $prevEAP = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
    $touchedFiles = @(git diff --name-only "$mergeBase" "$Remote/$Branch" 2>&1 | Where-Object { $_ -is [string] })
    $code = $LASTEXITCODE
    $ErrorActionPreference = $prevEAP
    if ($code -ne 0) {
        return @{ Status = 'Error'; Detail = 'git diff --name-only failed' }
    }

    if ($touchedFiles.Count -eq 0) {
        return @{ Status = 'Safe'; Detail = 'No file changes since diverging from base' }
    }

    $prevEAP = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
    $diff = git diff "$Remote/$BaseBranch" "$Remote/$Branch" -- $touchedFiles 2>&1 | Where-Object { $_ -is [string] }
    $code = $LASTEXITCODE
    $ErrorActionPreference = $prevEAP
    if ($code -ne 0) {
        return @{ Status = 'Error'; Detail = 'git diff failed' }
    }

    if ($diff) {
        return @{ Status = 'HasChanges'; Detail = "$($touchedFiles.Count) file(s) touched; differs from base on at least one" }
    }

    return @{ Status = 'Safe'; Detail = "$($touchedFiles.Count) file(s) touched; base already matches" }
}

# ============================================================================
# MAIN LOGIC
# ============================================================================

try {
    Write-Host ""
    Write-Host "=============================================================" -ForegroundColor Cyan
    Write-Host "Scan Branches - Safe to Delete Report" -ForegroundColor Cyan
    Write-Host "=============================================================" -ForegroundColor Cyan
    Write-Host ""

    # Step 1: Validate environment
    Write-Step "Validating environment" "[CHECK]"
    Assert-GitAvailable
    Assert-InGitRepo
    Write-Success "Git repository verified"

    # Step 2: Fetch latest remote refs
    if (-not $NoFetch) {
        Write-Step "Fetching latest changes" "[FETCH]"
        git fetch $Remote --prune 2>&1 | Out-Null
        if ($LASTEXITCODE -ne 0) {
            Write-ErrorMsg "Failed to fetch from '$Remote'"
            exit 1
        }
        Write-Success "Fetched latest from '$Remote'"
    } else {
        Write-Info "Skipped fetch (-NoFetch specified)"
    }

    # Step 3: Verify base branch exists on remote
    Write-Step "Verifying base branch" "[CHECK]"
    if (-not (Test-RemoteRefExists -Remote $Remote -Name $BaseBranch)) {
        Write-ErrorMsg "Remote branch '$Remote/$BaseBranch' does not exist"
        exit 1
    }
    Write-Success "'$Remote/$BaseBranch' verified"

    # Step 4: Enumerate candidate remote branches (exclude base + protected)
    Write-Step "Enumerating remote branches" "[SCAN]"
    $prevEAP = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
    $remoteBranches = git branch -r --format='%(refname:short)' 2>&1 | Where-Object { $_ -is [string] } | ForEach-Object {
        ($_ -replace "^$Remote/", "").Trim()
    } | Where-Object { $_ -ne "HEAD" -and $_ -ne $Remote -and $_ -ne $BaseBranch -and $ProtectedBranches -notcontains $_ }
    $ErrorActionPreference = $prevEAP
    $remoteBranches = @($remoteBranches)

    if ($remoteBranches.Count -eq 0) {
        Write-Info "No candidate branches to scan (everything is protected or the base branch)"
        exit 0
    }
    Write-Success "Found $($remoteBranches.Count) candidate branch(es) to scan"
    Write-Host ""

    # Step 5: Compare each candidate against the base branch
    $safe = [System.Collections.Generic.List[string]]::new()
    $hasChanges = [System.Collections.Generic.List[string]]::new()
    $errored = [System.Collections.Generic.List[string]]::new()

    foreach ($branch in $remoteBranches) {
        $result = Test-BranchMergedIntoBase -Remote $Remote -BaseBranch $BaseBranch -Branch $branch
        $localNote = if (Test-LocalRefExists -Name $branch) { " [local copy exists]" } else { "" }

        switch ($result.Status) {
            'Safe' {
                Write-Host "  [SAFE]        " -ForegroundColor Green -NoNewline
                Write-Host "$branch$localNote" -ForegroundColor White
                $safe.Add($branch)
            }
            'HasChanges' {
                Write-Host "  [HAS CHANGES] " -ForegroundColor Yellow -NoNewline
                Write-Host "$branch$localNote " -ForegroundColor White -NoNewline
                Write-Host "($($result.Detail))" -ForegroundColor DarkYellow
                $hasChanges.Add($branch)
            }
            'Error' {
                Write-Host "  [ERROR]       " -ForegroundColor Red -NoNewline
                Write-Host "$branch$localNote " -ForegroundColor White -NoNewline
                Write-Host "($($result.Detail))" -ForegroundColor DarkRed
                $errored.Add($branch)
            }
        }
    }

    # ========================================================================
    # SUMMARY
    # ========================================================================
    Write-Host ""
    Write-Host "=============================================================" -ForegroundColor Cyan
    Write-Host "Summary" -ForegroundColor Cyan
    Write-Host "=============================================================" -ForegroundColor Cyan
    Write-Host "  Safe to delete: $($safe.Count)" -ForegroundColor Green
    Write-Host "  Has changes:    $($hasChanges.Count)" -ForegroundColor Yellow
    Write-Host "  Errors:         $($errored.Count)" -ForegroundColor Red
    Write-Host ""

    if ($safe.Count -gt 0) {
        Write-Host "Safe to delete (no code differences from '$BaseBranch'):" -ForegroundColor Green
        foreach ($b in $safe) { Write-Host "  - $b" -ForegroundColor Green }
        Write-Host ""
        Write-Info "Nothing was deleted. Delete these on GitHub, then run git-clean-branches.ps1 to prune local copies."
    } else {
        Write-Info "No branches are currently safe to delete."
    }

    exit 0
}
catch {
    Write-ErrorMsg $_.Exception.Message
    exit 1
}
