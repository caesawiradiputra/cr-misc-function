param (
    [switch]$Force,
    [switch]$RemovePoetryArtifacts,
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

# ------------------------------------------------------------
# Resolve Project Root
# Use current working directory as project root
# ------------------------------------------------------------

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

# ------------------------------------------------------------
# Validate pyproject.toml
# ------------------------------------------------------------

$PyProjectPath = Join-Path $ProjectRoot "pyproject.toml"

if (-not (Test-Path $PyProjectPath)) {
    Fail "pyproject.toml not found in project root."
}

Write-Host "[+] Found pyproject.toml"

$PyProjectContent = Get-Content $PyProjectPath -Raw

# Extract requires-python (simple regex)
$RequiresPython = $null
if ($PyProjectContent -match 'requires-python\s*=\s*"(.*?)"') {
    $RequiresPython = $Matches[1]
    Write-Host "[+] requires-python: $RequiresPython"
}
else {
    Write-Host "[!] requires-python not found in pyproject.toml" -ForegroundColor Yellow
}

# Detect Poetry backend
$UsingPoetry = $false
if ($PyProjectContent -match "poetry.core") {
    $UsingPoetry = $true
    Write-Host "[!] Poetry backend detected." -ForegroundColor Yellow
}

# Detect uv lock
$UvLockExists = Test-Path (Join-Path $ProjectRoot "uv.lock")
$PoetryLockExists = Test-Path (Join-Path $ProjectRoot "poetry.lock")

if ($UvLockExists) {
    Write-Host "[+] uv.lock detected"
}
if ($PoetryLockExists) {
    Write-Host "[+] poetry.lock detected"
}

# ------------------------------------------------------------
# Validate Conda Environment
# ------------------------------------------------------------

Write-Section "Conda Validation"

$CondaCommand = Get-Command conda -ErrorAction SilentlyContinue

if (-not $CondaCommand) {
    Write-Host "[!] Conda not found in PATH." -ForegroundColor Yellow
}
else {
    try {
        $CondaPrefix = $env:CONDA_PREFIX
        $CondaEnv = $env:CONDA_DEFAULT_ENV

        if (-not $CondaPrefix) {
            Write-Host "[!] No active Conda environment." -ForegroundColor Yellow
        }
        else {
            $EnvName = if ($CondaEnv) { $CondaEnv } else { Split-Path $CondaPrefix -Leaf }
            Write-Host "[+] Active Conda env: $EnvName"
            Write-Host "    Path: $CondaPrefix"

            $PythonPath = (Get-Command python).Source
            Write-Host "[+] Active Python: $PythonPath"

            if ($PythonPath -notlike "$CondaPrefix*") {
                Write-Host "[!] Python interpreter does not match active Conda env." -ForegroundColor Yellow
            }

            $PythonVersion = python --version
            Write-Host "[+] Python version: $PythonVersion"

            if ($RequiresPython) {
                Write-Host "[~] Ensure Python satisfies requires-python constraint."
            }
        }
    }
    catch {
        Write-Host "[!] Failed to inspect Conda: $_" -ForegroundColor Yellow
    }
}

# ------------------------------------------------------------
# Backup to legacy/
# ------------------------------------------------------------

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

# Create README
$ReadmePath = Join-Path $LegacyPath "README.md"

if ((-not (Test-Path $ReadmePath)) -or $Force) {
@"
# Legacy Environment Archive

Migration from Poetry + Conda to uv.

Migration date: $(Get-Date -Format "yyyy-MM-dd")

This folder contains:

- poetry.lock
- Original pyproject.toml
- Conda export (from-history)
- Conda explicit lock

Do not modify.
Used only for rollback.
"@ | Set-Content -Path $ReadmePath
    Write-Host "[+] Created legacy README"
}

# ------------------------------------------------------------
# Optional Poetry Cleanup
# ------------------------------------------------------------

if ($RemovePoetryArtifacts -and $PoetryLockExists) {
    Write-Section "Removing Poetry Artifacts"
    Remove-Item (Join-Path $ProjectRoot "poetry.lock") -Force
    Write-Host "[+] Removed poetry.lock"
}

Write-Section "Migration Check Completed"
Write-Host "Next steps:"
Write-Host "  1. Ensure build-system uses hatchling"
Write-Host "  2. Run: uv sync"
if (Test-Path $DockerfilePath) {
    Write-Host "  3. Update Dockerfile to use uv instead of pip/poetry" -ForegroundColor Yellow
    Write-Host "  4. Commit changes"
}
else {
    Write-Host "  3. Commit changes"
}
