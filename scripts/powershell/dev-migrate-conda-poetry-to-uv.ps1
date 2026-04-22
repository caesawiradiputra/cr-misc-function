<#
.SYNOPSIS
Validate and prepare environment for Poetry + Conda → uv migration.

.DESCRIPTION
This script performs pre-migration checks and creates a safe rollback archive for migrating
from Poetry/Conda to uv package manager.

The script:
  1. Validates pyproject.toml exists and parses Python version requirement
  2. Checks Conda environment status and Python compatibility
  3. Creates backup archives in legacy/ folder (poetry.lock, pyproject.toml, Conda exports)
  4. Extracts dependencies from pyproject.toml for uv add commands
  5. Generates comprehensive migration guide (legacy/README.md) with VS Code setup
  6. Optionally removes Poetry artifacts (poetry.lock and pyproject.toml)

Output files in legacy/:
  - poetry.lock (backup of previous lock file)
  - pyproject.poetry.toml (backup of original pyproject.toml)
  - conda-env.yml (Conda environment export for rollback)
  - conda-explicit-lock.txt (Full Conda package list)
  - README.md (Detailed migration guide with uv commands)

.PARAMETER Force
Switch parameter. Overwrites existing backup files without prompting.
Useful for re-running the migration check after environment changes.

Example: .\dev-migrate-conda-poetry-to-uv.ps1 -Force

.PARAMETER RemovePoetryArtifacts
Switch parameter. Deletes poetry.lock and pyproject.toml (after backing up to legacy/).
Run this to clean up old Poetry files after verifying backups are safe.

⚠️  WARNING: This permanently removes poetry.lock and original pyproject.toml from project root.
Backups are created first, so you can restore from legacy/ if needed.

Example: .\dev-migrate-conda-poetry-to-uv.ps1 -RemovePoetryArtifacts

.PARAMETER GenerateMigrationGuideOnly
Switch parameter. Generates/regenerates only the migration guide without running validation or backups.
Useful to update the migration guide after dependencies have changed.

Does NOT require pyproject.toml or Conda environment to be present.
Quickly regenerates legacy/README_MIGRATION.md with current project settings.

Example: .\dev-migrate-conda-poetry-to-uv.ps1 -GenerateMigrationGuideOnly

.PARAMETER ProjectRoot
String parameter. Path to project root containing pyproject.toml.
If omitted, uses current working directory.

Default: Current location (Get-Location)
Example: .\dev-migrate-conda-poetry-to-uv.ps1 -ProjectRoot "C:\Users\user\projects\myapp"

.EXAMPLE
# Check migration readiness (no changes):
.\dev-migrate-conda-poetry-to-uv.ps1

.EXAMPLE
# Check and re-process with updated environment (overwrite existing backups):
.\dev-migrate-conda-poetry-to-uv.ps1 -Force

.EXAMPLE
# Check, backup, and clean up Poetry files:
.\dev-migrate-conda-poetry-to-uv.ps1 -RemovePoetryArtifacts

.EXAMPLE
# Full migration prep with cleanup (no confirmation required):
.\dev-migrate-conda-poetry-to-uv.ps1 -RemovePoetryArtifacts -Force

.EXAMPLE
# Only generate/regenerate migration guide (fast, no validation needed):
.\dev-migrate-conda-poetry-to-uv.ps1 -GenerateMigrationGuideOnly

.EXAMPLE
# Check a different project:
.\dev-migrate-conda-poetry-to-uv.ps1 -ProjectRoot "C:\projects\other-app"

.NOTES
Author: Development Team
LastModified: April 2026

After running this script, follow the migration guide in legacy/README.md:
  1. Activate Conda (py311 or py39)
  2. Run: uv init && uv venv
  3. Run: uv add [dependencies] (auto-generated commands in README.md)
  4. Update .vscode/settings.json (template in README.md)
  5. Verify: python --version & uv --version

See legacy/README.md for full step-by-step instructions.
#>
param (
    [switch]$Force,
    [switch]$RemovePoetryArtifacts,
    [switch]$GenerateMigrationGuideOnly,
    [string]$ProjectRoot
)

$ErrorActionPreference = "Stop"

function Write-Section($Text) {
    Write-Host ""
    Write-Host "===============================================" -ForegroundColor Cyan
    Write-Host $Text -ForegroundColor Cyan
    Write-Host "===============================================" -ForegroundColor Cyan
}

function Fail($Message) {
    Write-Host "[ERROR] $Message" -ForegroundColor Red
    exit 1
}

function Generate-LegacyReadme {
    param (
        [string]$LegacyReadmePath
    )

    $TemplateFile = "C:\Users\203715\Documents\Repo\cr-misc-function\cr-misc-function\templates\README_LEGACY.template.md"

    if (-not (Test-Path $TemplateFile)) {
        Write-Host "[!] Template not found: $TemplateFile" -ForegroundColor Yellow
        return
    }

    $template = Get-Content $TemplateFile -Raw
    $timestamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    $projectName = (Get-Item (Split-Path $LegacyReadmePath)).Parent.Name

    $content = $template -replace "{ProjectName}", $projectName -replace "{Timestamp}", $timestamp
    $content | Out-File -FilePath $LegacyReadmePath -Encoding UTF8 -Force
}

function Generate-MigrationReadme {
    param (
        [string]$ProjectFolderName,
        [string]$MigrationReadmePath,
        [array]$Dependencies,
        [array]$DevDependencies
    )

    # Helper function to format a dependency string
    # Input: pandas (==2.2.3) or xgboost>=3.0.5,<4.0.0 or pandas==2.2.3
    # Output: pandas==2.2.3 or 'xgboost>=3.0.5,<4.0.0' (quoted if contains comma)
    function Format-Dependency {
        param([string]$DepStr)

        # Remove quotes and trim
        $dep = $DepStr -replace "[`"`']", '' | ForEach-Object { $_.Trim() }

        # Try to extract package name and version from "name (spec)" format
        if ($dep -match '^([a-zA-Z0-9._-]+)\s*\((.+)\)$') {
            $pkgName = $Matches[1].Trim()
            $versionSpec = $Matches[2].Trim()

            # Quote if version spec contains comma or space
            if ($versionSpec -match '[,\s]') {
                return "'$pkgName$versionSpec'"
            } else {
                return "$pkgName$versionSpec"
            }
        }
        # Handle format without parentheses: name==version or name>=x,<y
        elseif ($dep -match '^([a-zA-Z0-9._-]+)([\<\>=!].*)$') {
            $pkgName = $Matches[1]
            $versionSpec = $Matches[2]

            # Quote if version spec contains comma
            if ($versionSpec -match ',') {
                return "'$pkgName$versionSpec'"
            } else {
                return "$pkgName$versionSpec"
            }
        }
        else {
            # No version spec, return as-is
            return $dep
        }
    }

    $TemplateFile = "C:\Users\203715\Documents\Repo\cr-misc-function\cr-misc-function\templates\README_MIGRATION.template.md"

    if (-not (Test-Path $TemplateFile)) {
        Write-Host "[!] Template not found: $TemplateFile" -ForegroundColor Yellow
        return
    }

    # Build unified uv add commands
    $UvAddLines = @()

    # Process main dependencies into a single command
    if ($Dependencies.Count -gt 0) {
        $FormattedDeps = @()
        foreach ($dep in $Dependencies) {
            $FormattedDeps += Format-Dependency $dep
        }
        $UvAddLines += "uv add $($FormattedDeps -join ' ')"
    }

    # Process dev dependencies into a single command
    if ($DevDependencies.Count -gt 0) {
        $FormattedDevDeps = @()
        foreach ($dep in $DevDependencies) {
            $FormattedDevDeps += Format-Dependency $dep
        }
        $UvAddLines += "uv add --dev $($FormattedDevDeps -join ' ')"
    }

    # Build the markdown section with code block
    $UvAddSection = if ($UvAddLines.Count -gt 0) {
        $backtick = '```'
        @"

Run these commands (or adjust versions as needed):

${backtick}bash
$($UvAddLines -join "`n")
${backtick}
"@
    } else {
        ""
    }

    $template = Get-Content $TemplateFile -Raw
    $timestamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'

    $content = $template -replace '{ProjectName}', $ProjectFolderName `
                         -replace '{Timestamp}', $timestamp `
                         -replace '{UvAddDependencies}', $UvAddSection
    $content | Out-File -FilePath $MigrationReadmePath -Encoding UTF8 -Force
}

# ============================================================================
# RESOLVE PROJECT ROOT
# ============================================================================
# ============================================================================
# Determine the project root directory (defaults to current working directory)

if (-not $ProjectRoot) {
    $ProjectRoot = Get-Location
}

$ProjectRoot = Resolve-Path $ProjectRoot -ErrorAction Stop

if (-not (Test-Path $ProjectRoot)) {
    Fail "Project root does not exist: $ProjectRoot"
}

Set-Location $ProjectRoot

Write-Section "Migration Utility - Poetry + Conda → uv"
Write-Host "Project root: $ProjectRoot"

# ============================================================================
# DETECT PROJECT FOLDER NAME
# ============================================================================
# Auto-detect project folder name from current directory
# Used for VS Code settings and terminal profiles

$ProjectFolderName = Split-Path -Leaf $ProjectRoot
Write-Host "[+] Detected project folder: $ProjectFolderName"

# ============================================================================
# MIGRATION GUIDE GENERATION ONLY MODE
# ============================================================================
# If -GenerateMigrationGuideOnly switch is used, skip all validation/backup
# and only generate the migration guide

if ($GenerateMigrationGuideOnly) {
    Write-Host ""
    Write-Host "[*] Generating migration guide only..." -ForegroundColor Cyan

    # Try to extract dependencies if pyproject.toml exists, otherwise use empty list
    $Dependencies = @()
    $DevDependencies = @()

    # Check for pyproject.toml in project root, or fall back to backed-up copy in legacy/
    $PyProjectPath = Join-Path $ProjectRoot "pyproject.toml"
    $PyProjectBackupPath = Join-Path -Path (Join-Path $ProjectRoot "legacy") -ChildPath "pyproject.poetry.toml"

    if (Test-Path $PyProjectPath) {
        $PyProjectContent = Get-Content $PyProjectPath -Raw
    } elseif (Test-Path $PyProjectBackupPath) {
        Write-Host "[~] Using backed-up pyproject.toml from legacy/" -ForegroundColor Yellow
        $PyProjectContent = Get-Content $PyProjectBackupPath -Raw
    } else {
        $PyProjectContent = $null
    }

    if ($PyProjectContent) {

        try {
            $depsPattern = 'dependencies\s*=\s*\[([\s\S]*?)\]'
            if ($PyProjectContent -match $depsPattern) {
                $DepsText = $Matches[1]
                # Split by comma followed by newline to preserve version specs with commas
                $DepsText -split ',\s*\n' | ForEach-Object {
                    $Dep = ($_ -replace "[`"`']", '').Trim()
                    if ($Dep -and $Dep -ne '') {
                        $Dependencies += $Dep
                    }
                }
            }

            $devDepsPattern = '\[project\.optional-dependencies\][\s\S]*?dev\s*=\s*\[([\s\S]*?)\]'
            if ($PyProjectContent -match $devDepsPattern) {
                $DevDepsText = $Matches[1]
                # Split by comma followed by newline to preserve version specs with commas
                $DevDepsText -split ',\s*\n' | ForEach-Object {
                    $Dep = ($_ -replace "[`"`']", '').Trim()
                    if ($Dep -and $Dep -ne '') {
                        $DevDependencies += $Dep
                    }
                }
            }
        }
        catch {
            Write-Host \"`[!`] Warning: Could not parse dependencies from pyproject.toml\" -ForegroundColor Yellow
        }
    } else {
        Write-Host \"`[!`] pyproject.toml not found - will generate guide with placeholder\" -ForegroundColor Yellow
    }

    # Ensure legacy directory exists
    $LegacyPath = Join-Path $ProjectRoot "legacy"
    if (-not (Test-Path $LegacyPath)) {
        New-Item -ItemType Directory -Path $LegacyPath | Out-Null
    }

    $MigrationGuidePath = Join-Path $LegacyPath "README_MIGRATION.md"

    # Generate migration guide using shared function
    Generate-MigrationReadme -ProjectFolderName $ProjectFolderName -MigrationReadmePath $MigrationGuidePath -Dependencies $Dependencies -DevDependencies $DevDependencies

    Write-Host "[+] Generated migration guide: README_MIGRATION.md" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next: Open legacy/README_MIGRATION.md and follow the steps" -ForegroundColor Green
    exit 0
}

# ============================================================================
# VALIDATE PYPROJECT.TOML
# ============================================================================
# Check that pyproject.toml exists and extract configuration

$PyProjectPath = Join-Path $ProjectRoot "pyproject.toml"

if (-not (Test-Path $PyProjectPath)) {
    Fail "pyproject.toml not found in project root."
}

Write-Host "[+] Found pyproject.toml"

$PyProjectContent = Get-Content $PyProjectPath -Raw

# Extract requires-python (simple regex)
$RequiresPython = $null
$pythonVersionPattern = 'requires-python\s*=\s*"(.*?)"'
if ($PyProjectContent -match $pythonVersionPattern) {
    $RequiresPython = $Matches[1]
    Write-Host "`[+`] requires-python: $RequiresPython"
}
else {
    Write-Host "`[!`] requires-python not found in pyproject.toml" -ForegroundColor Yellow
}

# Detect Poetry backend
$UsingPoetry = $false
$poetryCorePattern = "poetry.core"
if ($PyProjectContent -match $poetryCorePattern) {
    $UsingPoetry = $true
    Write-Host "`[!`] Poetry backend detected." -ForegroundColor Yellow
}

# ============================================================================
# BACKUP TO LEGACY/ (STEP 1)
# ============================================================================

Write-Section "Creating Legacy Backup"

$LegacyPath = Join-Path $ProjectRoot "legacy"

if (-not (Test-Path $LegacyPath)) {
    New-Item -ItemType Directory -Path $LegacyPath | Out-Null
    Write-Host "[+] Created legacy folder"
}

function Backup-File {
    param (
        [string]$Source,
        [string]$Destination
    )

    if (-not (Test-Path $Source)) {
        return
    }

    if ((Test-Path $Destination) -and (-not $Force)) {
        Write-Host "  [~] Skipped existing: $(Split-Path $Destination -Leaf)"
        return
    }

    Copy-Item $Source $Destination -Force
    Write-Host "  [+] Backed up: $(Split-Path $Destination -Leaf)"
}

if ($PoetryLockExists) {
    Backup-File `
        (Join-Path $ProjectRoot "poetry.lock") `
        (Join-Path $LegacyPath "poetry.lock")
}

Backup-File `
    (Join-Path $ProjectRoot "pyproject.toml") `
    (Join-Path $LegacyPath "pyproject.poetry.toml")

# Backup Dockerfile if it exists
$DockerfilePath = Join-Path $ProjectRoot "Dockerfile"
if (Test-Path $DockerfilePath) {
    Backup-File `
        $DockerfilePath `
        (Join-Path $LegacyPath "Dockerfile")
}

# Export Conda environment (if active)
$CondaPrefix = $env:CONDA_PREFIX
if ($CondaCommand -and $CondaPrefix) {
    Write-Host ""
    Write-Host "Exporting Conda environment..."

    $HistoryFile = Join-Path $LegacyPath "conda-env.yml"
    $ExplicitFile = Join-Path $LegacyPath "conda-explicit-lock.txt"

    try {
        if ((-not (Test-Path $HistoryFile)) -or $Force) {
            & conda env export --from-history | Out-File -FilePath $HistoryFile -Encoding UTF8
            Write-Host "  [+] Exported: conda-env.yml"
        }
        else {
            Write-Host "  [~] Skipped existing: conda-env.yml"
        }
    }
    catch {
        Write-Host "  [!] Failed to export conda-env: $_" -ForegroundColor Yellow
    }

    try {
        if ((-not (Test-Path $ExplicitFile)) -or $Force) {
            & conda list --explicit | Out-File -FilePath $ExplicitFile -Encoding UTF8
            Write-Host "  [+] Exported: conda-explicit-lock.txt"
        }
        else {
            Write-Host "  [~] Skipped existing: conda-explicit-lock.txt"
        }
    }
    catch {
        Write-Host "  [!] Failed to export conda lock: $_" -ForegroundColor Yellow
    }
}

# ============================================================================
# GENERATE README FILES (STEP 2 & 3)
# ============================================================================
# Step 2: Generate legacy readme
# Step 3: Parse dependencies from backed-up pyproject.toml and generate migration readme

# --- STEP 2: Generate README_LEGACY.md (Restoration & Rollback) ---
Write-Section "Generating README Files"

$LegacyReadmePath = Join-Path $LegacyPath "README_LEGACY.md"
Generate-LegacyReadme -LegacyReadmePath $LegacyReadmePath
Write-Host "[+] Created legacy/README_LEGACY.md"

# --- STEP 3: Parse dependencies from BACKED-UP pyproject.toml and generate migration readme ---
$PyProjectBackupPath = Join-Path $LegacyPath "pyproject.poetry.toml"
$Dependencies = @()
$DevDependencies = @()

if (Test-Path $PyProjectBackupPath) {
    $PyProjectContent = Get-Content $PyProjectBackupPath -Raw

    try {
        $depsPattern = 'dependencies\s*=\s*\[([\s\S]*?)\]'
        if ($PyProjectContent -match $depsPattern) {
            $DepsText = $Matches[1]
            # Split by comma followed by newline to preserve version specs with commas
            $DepsText -split ',\s*\n' | ForEach-Object {
                $Dep = ($_ -replace "[`"`']", '').Trim()
                if ($Dep -and $Dep -ne '') {
                    $Dependencies += $Dep
                }
            }
        }

        $devDepsPattern = '\[project\.optional-dependencies\][\s\S]*?dev\s*=\s*\[([\s\S]*?)\]'
        if ($PyProjectContent -match $devDepsPattern) {
            $DevDepsText = $Matches[1]
            # Split by comma followed by newline to preserve version specs with commas
            $DevDepsText -split ',\s*\n' | ForEach-Object {
                $Dep = ($_ -replace "[`"`']", '').Trim()
                if ($Dep -and $Dep -ne '') {
                    $DevDependencies += $Dep
                }
            }
        }
    }
    catch {
        Write-Host "[!] Warning: Could not parse dependencies from backed-up pyproject.toml" -ForegroundColor Yellow
    }
} else {
    Write-Host "[!] Backed-up pyproject.toml not found - migration guide will have placeholder" -ForegroundColor Yellow
}

$MigrationReadmePath = Join-Path $LegacyPath "README_MIGRATION.md"
Generate-MigrationReadme -ProjectFolderName $ProjectFolderName -MigrationReadmePath $MigrationReadmePath -Dependencies $Dependencies -DevDependencies $DevDependencies
Write-Host "[+] Created legacy/README_MIGRATION.md"

Write-Section "Migration Check Complete"

Write-Host "Archive created at: $LegacyPath"
Write-Host ""
Write-Host "[DOCS] Documentation files:" -ForegroundColor Cyan
Write-Host "   • legacy/README_LEGACY.md        - Rollback `& restoration instructions"
Write-Host "   • legacy/README_MIGRATION.md     - Step-by-step migration guide"
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Green
Write-Host "  1. Open: legacy/README_MIGRATION.md"
Write-Host "  2. Follow the 7-step migration walkthrough"
Write-Host "  3. When done, commit your changes:"
Write-Host "     git add pyproject.toml uv.lock .vscode/settings.json"
Write-Host 'git commit -m "chore: migrate from Poetry to uv"'
Write-Host ""

if ($RemovePoetryArtifacts) {
    Write-Host "[BACKUP] Backups created (in legacy/):" -ForegroundColor Yellow
    Write-Host "     • poetry.lock -> Backed up automatically"
    Write-Host "     • pyproject.toml -> Backed up as pyproject.poetry.toml"
    Write-Host ""
    Write-Host "Use README_LEGACY.md to restore if needed" -ForegroundColor Yellow
    Write-Host ""
}
