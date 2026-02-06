<#
.SYNOPSIS
    Export and clean conda environment.yaml using Python module.

.DESCRIPTION
    This script performs a complete workflow:
    1. Exports the current conda environment using 'conda env export --no-builds'
    2. Calls Python module (app.utils.clean_environment) to clean the YAML
    3. Removes conda/OS/compiler internals and poetry packages

.PARAMETER EnvironmentFile
    Path to environment.yaml file. Defaults to './environment.yml'

.PARAMETER EnvironmentName
    Name of the conda environment to export. If not specified, exports the currently active environment.

.PARAMETER SkipExport
    Skip the conda export step and only clean an existing environment.yml file.

.PARAMETER BackupOriginal
    Create a backup of the original file before cleaning (.backup extension).

.PARAMETER KeepPoetry
    Keep poetry and related packages (by default they are removed).

.PARAMETER DryRun
    Show what would be removed without making changes to the file.

.EXAMPLE
    .\clean-environment-yaml.ps1

    Exports current environment and cleans it using Python module.

.EXAMPLE
    .\clean-environment-yaml.ps1 -SkipExport -DryRun

    Preview cleanup of existing environment.yml without exporting.

.EXAMPLE
    .\clean-environment-yaml.ps1 -BackupOriginal

    Export, backup, and clean the environment.

#>

[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [string]$EnvironmentFile = "environment.yml",

    [Parameter(Position = 1)]
    [string]$EnvironmentName,

    [switch]$SkipExport,
    [switch]$BackupOriginal,
    [switch]$KeepPoetry,
    [switch]$DryRun
)

#region Helper Functions
function Write-Step {
    param([string]$Message, [string]$Icon = "[*]")
    Write-Host "`n$Icon $Message" -ForegroundColor Cyan
}

function Write-Success {
    param([string]$Message)
    Write-Host "[OK] $Message" -ForegroundColor Green
}

function Write-Error-Custom {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

function Write-Info {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor Gray
}

function Get-PythonCommand {
    # Find Python executable - try conda's python first, then system python
    $pythonCandidates = @("python", "python3")

    foreach ($cmd in $pythonCandidates) {
        try {
            $null = & $cmd --version 2>&1
            if ($LASTEXITCODE -eq 0) {
                return $cmd
            }
        }
        catch {
            continue
        }
    }

    return $null
}
#endregion

try {
    Write-Host ""
    Write-Host "=================================================" -ForegroundColor Cyan
    Write-Host "     Export & Clean Conda environment.yaml" -ForegroundColor Cyan
    Write-Host "     (Using Python cleanup module)" -ForegroundColor Cyan
    Write-Host "=================================================" -ForegroundColor Cyan
    Write-Host ""

    # Resolve file path
    $resolvedPath = if ([System.IO.Path]::IsPathRooted($EnvironmentFile)) {
        $EnvironmentFile
    }
    else {
        Join-Path (Get-Location) $EnvironmentFile
    }

    Write-Verbose "Working with: $resolvedPath"

    # Step 1: Export conda environment (unless skipped)
    if (-not $SkipExport) {
        Write-Step "Exporting conda environment" "[EXPORT]"

        $condaCommand = if ($EnvironmentName) {
            "conda env export --name $EnvironmentName --no-builds"
        }
        else {
            "conda env export --no-builds"
        }

        Write-Info "Running: $condaCommand"

        try {
            & cmd /c "$condaCommand > `"$resolvedPath`"" 2>$null

            if ($LASTEXITCODE -ne 0) {
                Write-Error-Custom "Failed to export. Ensure conda is in PATH."
                exit 1
            }

            Write-Success "Environment exported successfully"
        }
        catch {
            Write-Error-Custom "Export error: $_"
            exit 1
        }
    }
    else {
        Write-Info "Skipping conda export"
    }

    # Step 2: Verify file exists
    Write-Step "Checking environment file" "[CHECK]"

    if (-not (Test-Path $resolvedPath)) {
        Write-Error-Custom "File not found: $resolvedPath"
        exit 1
    }

    $originalSize = (Get-Item $resolvedPath).Length / 1KB
    Write-Success "File found: $resolvedPath ($([math]::Round($originalSize, 2)) KB)"

    # Step 3: Check Python availability
    Write-Step "Checking Python environment" "[PYTHON]"

    $pythonCmd = Get-PythonCommand
    if (-not $pythonCmd) {
        Write-Error-Custom "Python not found in PATH"
        Write-Info "Ensure Python is installed and accessible"
        exit 1
    }

    Write-Success "Python found: $pythonCmd"

    # Step 4: Backup if requested
    if ($BackupOriginal -and -not $DryRun) {
        Write-Step "Creating backup" "[BACKUP]"
        $backupPath = "$resolvedPath.backup"
        Copy-Item -Path $resolvedPath -Destination $backupPath -Force
        Write-Success "Backup created: $(Split-Path $backupPath -Leaf)"
    }

    # Step 5: Call Python cleanup module
    Write-Step "Cleaning environment file" "[CLEAN]"

    # Find project root (where app/ folder is located)
    $scriptDir = Split-Path $PSScriptRoot -Parent
    $projectRoot = Split-Path $scriptDir -Parent
    $pythonModule = Join-Path $projectRoot "app\utils\clean_environment.py"

    if (-not (Test-Path $pythonModule)) {
        Write-Error-Custom "Python module not found: $pythonModule"
        Write-Info "Expected location: app/utils/clean_environment.py"
        exit 1
    }

    # Build Python command arguments
    $pythonArgs = @($pythonModule, $resolvedPath, "--verbose")

    if ($KeepPoetry) {
        $pythonArgs += "--keep-poetry"
    }

    if ($DryRun) {
        $pythonArgs += "--dry-run"
    }

    Write-Info "Calling: $pythonCmd app.utils.clean_environment"
    Write-Verbose "Full command: $pythonCmd $($pythonArgs -join ' ')"

    try {
        # Run Python module and capture output
        $output = & $pythonCmd @pythonArgs 2>&1

        if ($LASTEXITCODE -ne 0) {
            Write-Error-Custom "Python module failed"
            Write-Host $output

            # Check if ruamel.yaml is missing
            if ($output -match "No module named 'ruamel") {
                Write-Host ""
                Write-Info "The Python module requires 'ruamel.yaml'. Install it with:"
                Write-Host "  pip install ruamel.yaml" -ForegroundColor Cyan
                Write-Host "  or"
                Write-Host "  conda install ruamel.yaml" -ForegroundColor Cyan
            }
            exit 1
        }

        # Display Python module output
        Write-Host ""
        Write-Host $output -ForegroundColor White
        Write-Host ""

    }
    catch {
        Write-Error-Custom "Failed to run Python module: $_"
        exit 1
    }

    # Step 6: Summary
    if (-not $DryRun) {
        $newSize = (Get-Item $resolvedPath).Length / 1KB
        $spaceSaved = $originalSize - $newSize

        Write-Host ""
        Write-Host "=================================================" -ForegroundColor Green
        Write-Host "     Cleanup Complete" -ForegroundColor Green
        Write-Host "=================================================" -ForegroundColor Green
        Write-Host ""
        Write-Host "File size: $([math]::Round($originalSize, 2)) KB → $([math]::Round($newSize, 2)) KB" -ForegroundColor Cyan
        Write-Host "Space saved: $([math]::Round($spaceSaved, 2)) KB" -ForegroundColor Cyan

        if ($BackupOriginal) {
            Write-Host "Backup: $(Split-Path $backupPath -Leaf)" -ForegroundColor Cyan
        }

        Write-Host ""
        Write-Success "Your environment.yml is clean and ready to share!"
        Write-Info "Next: git add environment.yml; git commit -m 'chore: add cleaned environment.yml'"
    }
}
catch {
    Write-Host ""
    Write-Error-Custom "Script error: $_"
    if ($_.ScriptStackTrace) {
        Write-Host $_.ScriptStackTrace -ForegroundColor DarkGray
    }
    exit 1
}
