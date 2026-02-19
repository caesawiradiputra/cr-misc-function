<#
.SYNOPSIS
    Display the command to remove base-only utility packages from conda environment.

.DESCRIPTION
    Analyzes the current conda environment and displays the command to remove
    packages that are typically only needed in the base conda environment but
    not required for project-specific work. You decide when to run the command.

    Base-only packages identified:
    - poetry, poetry-core: Dependency and package management
    - pipdeptree: Dependency tree visualization
    - pip-audit: Pip package security auditing
    - jupyter, jupyterlab: Notebook environments (optional)
    - ipython: Interactive Python shell (optional)

.PARAMETER IncludeJupyter
    Also identify jupyter and jupyterlab packages for removal.

.PARAMETER IncludeIPython
    Also identify ipython package for removal.

.EXAMPLE
    .\remove-base-only-packages.ps1

    Display the conda remove command for base-only packages.

.EXAMPLE
    .\remove-base-only-packages.ps1 -IncludeJupyter -IncludeIPython

    Include Jupyter and IPython in the list.

#>

[CmdletBinding()]
param(
    [switch]$IncludeJupyter,
    [switch]$IncludeIPython
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

function Write-Warning-Custom {
    param([string]$Message)
    Write-Host "[WARN] $Message" -ForegroundColor Yellow
}

function Write-Error-Custom {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

function Write-Info {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor Gray
}

function Get-InstalledPackages {
    <#
    .SYNOPSIS
        Get list of installed packages in the current conda environment.
    #>
    try {
        $output = & conda list --json 2>$null | ConvertFrom-Json
        return $output | Select-Object -ExpandProperty name | Sort-Object -Unique
    }
    catch {
        Write-Error-Custom "Failed to retrieve installed packages"
        return @()
    }
}

function Test-PackageInstalled {
    <#
    .SYNOPSIS
        Check if a specific package is installed.
    #>
    param([string]$PackageName, [string[]]$InstalledPackages)

    return $InstalledPackages -contains $PackageName
}
#endregion

try {
    Write-Host ""
    Write-Host "=================================================" -ForegroundColor Cyan
    Write-Host "     Remove Base-Only Packages" -ForegroundColor Cyan
    Write-Host "=================================================" -ForegroundColor Cyan
    Write-Host ""

    # Step 1: Check conda is available
    Write-Step "Checking conda environment" "[CHECK]"

    try {
        $condaInfo = & conda info --json 2>$null | ConvertFrom-Json
        $activeEnv = Split-Path $condaInfo.active_prefix -Leaf
        Write-Success "Active environment: $activeEnv"
    }
    catch {
        Write-Error-Custom "Conda not found or not accessible"
        Write-Info "Ensure conda is installed and available in PATH"
        exit 1
    }

    # Step 2: Define packages to remove
    Write-Step "Identifying packages to remove" "[LIST]"

    $baseOnlyPackages = @(
        "poetry",
        "poetry-core",
        "pipdeptree",
        "pip-audit"
    )

    if ($IncludeJupyter) {
        $baseOnlyPackages += @("jupyter", "jupyterlab")
    }

    if ($IncludeIPython) {
        $baseOnlyPackages += "ipython"
    }

    Write-Info "Target packages: $($baseOnlyPackages -join ', ')"

    # Step 3: Check which packages are installed
    Write-Step "Checking installed packages" "[SCAN]"

    $installedPackages = Get-InstalledPackages
    $packagesToRemove = @()

    foreach ($package in $baseOnlyPackages) {
        if (Test-PackageInstalled -PackageName $package -InstalledPackages $installedPackages) {
            $packagesToRemove += $package
        }
    }

    if ($packagesToRemove.Count -eq 0) {
        Write-Warning-Custom "No base-only packages are currently installed"
        Write-Info "Nothing to do!"
        exit 0
    }

    Write-Success "Found $($packagesToRemove.Count) package(s) to remove:"
    foreach ($pkg in $packagesToRemove) {
        Write-Host "  - $pkg" -ForegroundColor Yellow
    }

    # Step 4: Display the command to run
    Write-Step "Command to execute" "[COMMAND]"

    $removeCommand = "conda remove --yes --quiet $($packagesToRemove -join ' ')"
    Write-Host ""
    Write-Host $removeCommand -ForegroundColor Cyan
    Write-Host ""

    # Step 5: Summary
    Write-Host "=================================================" -ForegroundColor Green
    Write-Host "     Ready to Run" -ForegroundColor Green
    Write-Host "=================================================" -ForegroundColor Green
    Write-Host ""
    Write-Success "Copy and run the command above when ready"
    Write-Info "This will remove $($packagesToRemove.Count) package(s) from your environment"
    Write-Host ""
}
catch {
    Write-Host ""
    Write-Error-Custom "Script error: $_"
    if ($_.ScriptStackTrace) {
        Write-Host $_.ScriptStackTrace -ForegroundColor DarkGray
    }
    exit 1
}
