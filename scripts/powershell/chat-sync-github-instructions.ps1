<#
.SYNOPSIS
    Synchronizes .github instructions and prompts with .github.template

.DESCRIPTION
    This script compares .github\instructions and .github\prompts with
    .github.template\instructions and .github.template\prompts.

    It will:
    - Add missing files from .github.template to .github
    - Replace files in .github that differ from .github.template
    - Skip if .github.template doesn't exist in the workspace

.PARAMETER TargetGitHubRoot
    The workspace root where .github folder should be synced. Defaults to parent of current working directory.

    When called from another workspace, this will be automatically detected from the current directory.
    For example: C:\Users\203715\Documents\Repo\da-ndf4w-1p5c-monitoring-streamlit

.PARAMETER DryRun
    If specified, shows what would be done without making changes.

.PARAMETER Verbose
    Shows detailed output of all operations.

.EXAMPLE
    # Run from workspace directory - automatically detects parent .github folder
    .\sync-github-instructions.ps1

.EXAMPLE
    # Preview changes without applying
    .\sync-github-instructions.ps1 -DryRun

.EXAMPLE
    # Specify target workspace explicitly
    .\sync-github-instructions.ps1 -TargetGitHubRoot "C:\path\to\workspace" -Verbose

#>

param(
    [string]$TargetGitHubRoot = (Split-Path -Parent (Get-Location)),
    [switch]$DryRun,
    [switch]$Verbose
)

# Enable verbose output if requested
if ($Verbose) {
    $VerbosePreference = "Continue"
}

# Color constants for output
$Colors = @{
    Success = [ConsoleColor]::Green
    Warning = [ConsoleColor]::Yellow
    Error   = [ConsoleColor]::Red
    Info    = [ConsoleColor]::Cyan
}

function Write-ColorOutput {
    param(
        [string]$Message,
        [ConsoleColor]$Color = [ConsoleColor]::White
    )
    Write-Host $Message -ForegroundColor $Color
}

function Write-VerboseOutput {
    param([string]$Message)
    if ($Verbose) {
        Write-ColorOutput "  -> $Message" -Color ([ConsoleColor]::Gray)
    }
}

# Define paths
# Template is hardcoded to the cr-misc-function reference implementation
$GitHubTemplatePath = "C:\Users\203715\Documents\Repo\cr-misc-function\.github.template"
# Target .github is in the workspace passed as parameter (defaults to current directory parent)
$GitHubPath = Join-Path $TargetGitHubRoot ".github"

Write-ColorOutput "`n========================================" -Color $Colors.Info
Write-ColorOutput "GitHub Instructions & Prompts Sync" -Color $Colors.Info
Write-ColorOutput "========================================`n" -Color $Colors.Info

# Validate target workspace root
if (-not (Test-Path $TargetGitHubRoot)) {
    Write-ColorOutput "X Target workspace root not found: $TargetGitHubRoot" -Color $Colors.Error
    exit 1
}

Write-VerboseOutput "Target workspace: $TargetGitHubRoot"
Write-VerboseOutput ".github path: $GitHubPath"
Write-VerboseOutput ".github.template path (reference): $GitHubTemplatePath"

# Check if .github.template exists
if (-not (Test-Path $GitHubTemplatePath)) {
    Write-ColorOutput "O .github.template not found - skipping sync" -Color $Colors.Warning
    Write-ColorOutput "  (This is normal if .github.template doesn't exist in this workspace)`n" -Color $Colors.Warning
    exit 0
}

Write-ColorOutput "Check Found .github.template folder`n" -Color $Colors.Success

# Ensure .github folder exists
if (-not (Test-Path $GitHubPath)) {
    Write-ColorOutput "Creating .github folder..." -Color $Colors.Info
    if (-not $DryRun) {
        New-Item -ItemType Directory -Path $GitHubPath | Out-Null
    }
}

# Initialize stats
$SyncStats = @{
    Added   = 0
    Updated = 0
    Skipped = 0
    Errors  = 0
}

# Process instructions, prompts, agents, and skills folders
$FoldersToSync = @("instructions", "prompts", "agents", "skills")

foreach ($Folder in $FoldersToSync) {
    $SourceFolder = Join-Path $GitHubTemplatePath $Folder
    $TargetFolder = Join-Path $GitHubPath $Folder

    if (-not (Test-Path $SourceFolder)) {
        Write-VerboseOutput "Source folder not found: $SourceFolder"
        continue
    }

    # Ensure target folder exists
    if (-not (Test-Path $TargetFolder)) {
        if (-not $DryRun) {
            New-Item -ItemType Directory -Path $TargetFolder | Out-Null
        }
    }

    Write-ColorOutput "`n[Processing: $Folder]" -Color $Colors.Info

    # Get all files from source folder recursively (including subfolders)
    $SourceFiles = Get-ChildItem -Path $SourceFolder -File -Recurse

    foreach ($File in $SourceFiles) {
        $SourceFile = $File.FullName

        # Calculate relative path to preserve folder structure
        $RelativePath = $File.FullName.Substring($SourceFolder.Length + 1)
        $TargetFile = Join-Path $TargetFolder $RelativePath

        # Ensure target subdirectory exists
        $TargetDir = Split-Path -Parent $TargetFile
        if (-not (Test-Path $TargetDir)) {
            if (-not $DryRun) {
                New-Item -ItemType Directory -Path $TargetDir -Force | Out-Null
            }
        }

        # Calculate file size for display
        $FileSizeKB = [math]::Round($File.Length / 1KB, 1)

        if (Test-Path $TargetFile) {
            # File exists in both - compare content
            $SourceHash = (Get-FileHash -Path $SourceFile -Algorithm SHA256).Hash
            $TargetHash = (Get-FileHash -Path $TargetFile -Algorithm SHA256).Hash

            if ($SourceHash -ne $TargetHash) {
                # Content differs - update
                Write-ColorOutput "  Check [UPDATED] $($File.Name) ($FileSizeKB KB)" -Color $Colors.Success
                Write-VerboseOutput "  Content differs - updating from template"

                if (-not $DryRun) {
                    try {
                        Copy-Item -Path $SourceFile -Destination $TargetFile -Force
                        $SyncStats.Updated++
                    } catch {
                        Write-ColorOutput "    ERROR: Failed to update file - $($_.Exception.Message)" -Color $Colors.Error
                        $SyncStats.Errors++
                    }
                } else {
                    $SyncStats.Updated++
                }
            } else {
                # Content is the same - skip
                Write-VerboseOutput "  Check SKIP (unchanged): $($File.Name)"
                $SyncStats.Skipped++
            }
        } else {
            # File doesn't exist in target - add it
            Write-ColorOutput "  Check [ADDED] $($File.Name) ($FileSizeKB KB)" -Color $Colors.Success
            Write-VerboseOutput "  File missing in .github - adding from template"

            if (-not $DryRun) {
                try {
                    Copy-Item -Path $SourceFile -Destination $TargetFile -Force
                    $SyncStats.Added++
                } catch {
                    Write-ColorOutput "    ERROR: Failed to add file - $($_.Exception.Message)" -Color $Colors.Error
                    $SyncStats.Errors++
                }
            } else {
                $SyncStats.Added++
            }
        }
    }
}

# Print summary
Write-ColorOutput "`n========================================" -Color $Colors.Info
Write-ColorOutput "Sync Summary" -Color $Colors.Info
Write-ColorOutput "========================================`n" -Color $Colors.Info

Write-Host "  Added files:  " -NoNewline
Write-ColorOutput "$($SyncStats.Added)" -Color $Colors.Success

Write-Host "  Updated files: " -NoNewline
Write-ColorOutput "$($SyncStats.Updated)" -Color $Colors.Warning

Write-Host "  Skipped files: " -NoNewline
Write-ColorOutput "$($SyncStats.Skipped)" -Color ([ConsoleColor]::Gray)

Write-Host "  Errors:        " -NoNewline
if ($SyncStats.Errors -gt 0) {
    Write-ColorOutput "$($SyncStats.Errors)" -Color $Colors.Error
} else {
    Write-ColorOutput "$($SyncStats.Errors)" -Color $Colors.Success
}

if ($DryRun) {
    Write-ColorOutput "`nDRY RUN - No files were actually modified" -Color $Colors.Warning
}

$TotalOps = $SyncStats.Added + $SyncStats.Updated + $SyncStats.Skipped
Write-ColorOutput "`nSync complete: $TotalOps total files processed`n" -Color $Colors.Success

exit 0
