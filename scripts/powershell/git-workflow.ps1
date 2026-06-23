<#
.SYNOPSIS
    Git workflow orchestrator - chains git utility scripts for common workflows.

.DESCRIPTION
    Provides high-level workflow commands that chain the individual git-*.ps1 scripts:

    Workflow map:
      git-clean-branches  -->  git-check-sync-set-dev  -->  git-init-feature
          (prune stale)         (sync dev, activate)         (create branch)
                                                                |
                                                                v
      git-reset-branches  <--  git-rebase-branch  <--  git-create-clean-branch
          (emergency)          (rebase onto base)       (cherry-pick filtered)

    Subcommands:
      prepare  - Clean stale branches, then sync dev with master
      start    - Sync dev with master, then create a new feature branch
      finish   - Rebase feature branch onto base for clean merge
      recover  - Reset all branches to remote state (emergency recovery)
      status   - Show current git state (branch, dirty files, remote sync)

.PARAMETER Action
    The workflow action to execute. Required.

.PARAMETER Force
    Pass -Force to underlying scripts (skip confirmation prompts).

.PARAMETER DryRun
    Pass -DryRun to underlying scripts where applicable.

.EXAMPLE
    .\git-workflow.ps1 prepare
    Cleans stale branches and syncs dev with master.

.EXAMPLE
    .\git-workflow.ps1 start -Force
    Syncs dev and creates a feature branch (auto-confirms prompts).

.EXAMPLE
    .\git-workflow.ps1 recover -DryRun
    Preview what the recovery reset would do.

.NOTES
    Author: Development Team
    Requires all git-*.ps1 scripts to be in the same directory.
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory, Position = 0)]
    [ValidateSet("prepare", "start", "finish", "recover", "status")]
    [string]$Action,

    [switch]$Force,
    [switch]$DryRun
)

# Import shared helpers
Import-Module (Join-Path $PSScriptRoot "modules\GitScriptHelpers.psm1") -Force

# Script directory for locating sibling scripts
$scriptDir = if ($PSScriptRoot) { $PSScriptRoot } else { $PWD.Path }

function Invoke-Script {
    <#
    .SYNOPSIS
        Run a sibling git-*.ps1 script with optional parameters.
    #>
    param(
        [string]$ScriptName,
        [string[]]$ExtraArgs = @()
    )

    $scriptPath = Join-Path $scriptDir $ScriptName
    if (-not (Test-Path $scriptPath)) {
        Write-ErrorMsg "Script not found: $scriptPath"
        return $false
    }

    $args_ = @()
    if ($Force) { $args_ += "-Force" }
    if ($DryRun) { $args_ += "-DryRun" }
    $args_ += $ExtraArgs

    Write-Host ""
    Write-Host "=============================================================" -ForegroundColor DarkCyan
    Write-Host "  Running: $ScriptName $($args_ -join ' ')" -ForegroundColor DarkCyan
    Write-Host "=============================================================" -ForegroundColor DarkCyan
    Write-Host ""

    & $scriptPath @args_
    $exitCode = $LASTEXITCODE

    if ($exitCode -ne 0) {
        Write-ErrorMsg "$ScriptName exited with code $exitCode. Aborting workflow."
        return $false
    }
    return $true
}

# ============================================================================
# MAIN LOGIC
# ============================================================================

Write-Host ""
Write-Host "=============================================================" -ForegroundColor Cyan
Write-Host "Git Workflow Orchestrator" -ForegroundColor Cyan
Write-Host "=============================================================" -ForegroundColor Cyan
Write-Host ""

switch ($Action) {

    "prepare" {
        # Clean stale branches, then sync dev with master
        Write-Info "Workflow: PREPARE (clean + sync)"
        Write-Host "  1. Clean stale local branches" -ForegroundColor White
        Write-Host "  2. Sync dev with master" -ForegroundColor White
        Write-Host ""

        if (-not (Invoke-Script "git-clean-branches.ps1")) { exit 1 }
        if (-not (Invoke-Script "git-check-sync-set-dev.ps1")) { exit 1 }

        Write-Success "PREPARE workflow complete"
    }

    "start" {
        # Sync dev with master, then create feature branch
        Write-Info "Workflow: START (sync + create feature branch)"
        Write-Host "  1. Sync dev with master" -ForegroundColor White
        Write-Host "  2. Create new feature branch" -ForegroundColor White
        Write-Host ""

        if (-not (Invoke-Script "git-check-sync-set-dev.ps1")) { exit 1 }
        if (-not (Invoke-Script "git-init-feature.ps1")) { exit 1 }

        Write-Success "START workflow complete"
    }

    "finish" {
        # Rebase feature branch onto base
        Write-Info "Workflow: FINISH (rebase feature branch)"
        Write-Host "  1. Rebase current feature branch onto master" -ForegroundColor White
        Write-Host ""

        $extraArgs = @()
        # Pass through any additional args the user might need
        if (-not (Invoke-Script "git-rebase-branch.ps1" -ExtraArgs $extraArgs)) { exit 1 }

        Write-Success "FINISH workflow complete"
        Write-Host ""
        Write-Info "Next steps:"
        Write-Host "  - Push rebased branch: git push --force-with-lease origin <branch>" -ForegroundColor White
        Write-Host "  - Create PR on GitHub/GitLab" -ForegroundColor White
    }

    "recover" {
        # Reset all branches to remote state
        Write-Info "Workflow: RECOVER (reset branches to remote state)"
        Write-Host "  WARNING: This is a DESTRUCTIVE operation" -ForegroundColor Red
        Write-Host "  All local changes on master/dev/sit will be lost" -ForegroundColor Red
        Write-Host ""

        if (-not (Invoke-Script "git-reset-branches.ps1")) { exit 1 }

        Write-Success "RECOVER workflow complete"
    }

    "status" {
        # Show current git state summary
        Write-Info "Current Git State"
        Write-Host ""

        # Current branch
        $currentBranch = git rev-parse --abbrev-ref HEAD 2>&1 | Where-Object { $_ -is [string] }
        Write-Host "  Branch:  $currentBranch" -ForegroundColor White

        # Dirty files
        $dirty = git status --porcelain 2>&1 | Where-Object { $_ -is [string] }
        if ($dirty) {
            $count = @($dirty).Count
            Write-Host "  Status:  $count uncommitted change(s)" -ForegroundColor Yellow
        } else {
            Write-Host "  Status:  Clean working directory" -ForegroundColor Green
        }

        # Remote tracking
        $upstream = git rev-parse --abbrev-ref "@{upstream}" 2>&1 | Where-Object { $_ -is [string] }
        if ($LASTEXITCODE -eq 0 -and $upstream) {
            Write-Host "  Tracking: $upstream" -ForegroundColor White

            # Ahead/behind count
            $ahead = [int](git rev-list --count "$upstream..HEAD" 2>&1 | Where-Object { $_ -is [string] })
            $behind = [int](git rev-list --count "HEAD..$upstream" 2>&1 | Where-Object { $_ -is [string] })

            if ($ahead -gt 0 -and $behind -gt 0) {
                Write-Host "  Ahead:   $ahead commit(s), Behind: $behind commit(s)" -ForegroundColor Yellow
            } elseif ($ahead -gt 0) {
                Write-Host "  Ahead:   $ahead commit(s) (needs push)" -ForegroundColor Yellow
            } elseif ($behind -gt 0) {
                Write-Host "  Behind:  $behind commit(s) (needs pull)" -ForegroundColor Yellow
            } else {
                Write-Host "  Sync:    Up to date with remote" -ForegroundColor Green
            }
        } else {
            Write-Host "  Tracking: No upstream set" -ForegroundColor DarkGray
        }

        # Dev-master sync check
        Write-Host ""
        $devMasterDiff = git diff "origin/master" "origin/dev" --stat 2>&1 | Where-Object { $_ -is [string] }
        if ($LASTEXITCODE -eq 0 -and -not $devMasterDiff) {
            Write-Info "Dev is in sync with master (no code differences)"
        } else {
            Write-Warn "Dev has code differences from master"
        }
    }
}

Write-Host ""
