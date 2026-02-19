<#
.SYNOPSIS
    Updates .github.template with changes from workspace .github folder

.DESCRIPTION
    This script compares .github\instructions and .github\prompts in a workspace
    with .github.template\instructions and .github.template\prompts (reference).
    
    It will:
    - Update existing files in .github.template if they differ in the workspace .github
    - Only update files that already exist in .github.template (no new files added)
    - Skip if .github doesn't exist in the workspace

.PARAMETER WorkspaceRoot
    The workspace root where .github folder exists. Defaults to current working directory.
    
    Example: C:\Users\203715\Documents\Repo\da-ndf4w-1p5c-monitoring-streamlit

.PARAMETER DryRun
    If specified, shows what would be done without making changes.

.PARAMETER Verbose
    Shows detailed output of all operations.

.EXAMPLE
    # Update template from current workspace
    .\update-template-from-workspace.ps1
    
.EXAMPLE
    # Preview changes without applying
    .\update-template-from-workspace.ps1 -DryRun
    
.EXAMPLE
    # Update from specific workspace
    .\update-template-from-workspace.ps1 -WorkspaceRoot "C:\path\to\workspace" -Verbose

#>

param(
    [string]$WorkspaceRoot = (Get-Location),
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
# Source is the workspace .github folder
$SourceGitHubPath = Join-Path $WorkspaceRoot ".github"
# Template is hardcoded to the cr-misc-function reference implementation
$GitHubTemplatePath = "C:\Users\203715\Documents\Repo\cr-misc-function\.github.template"

Write-ColorOutput "`n========================================" -Color $Colors.Info
Write-ColorOutput "Update .github.template from Workspace" -Color $Colors.Info
Write-ColorOutput "========================================`n" -Color $Colors.Info

# Validate workspace root
if (-not (Test-Path $WorkspaceRoot)) {
    Write-ColorOutput "X Workspace root not found: $WorkspaceRoot" -Color $Colors.Error
    exit 1
}

Write-VerboseOutput "Source workspace: $WorkspaceRoot"
Write-VerboseOutput ".github path: $SourceGitHubPath"
Write-VerboseOutput ".github.template path (target): $GitHubTemplatePath"

# Check if source .github exists
if (-not (Test-Path $SourceGitHubPath)) {
    Write-ColorOutput "X .github folder not found in workspace: $SourceGitHubPath" -Color $Colors.Error
    exit 1
}

Write-ColorOutput "Check Found .github folder in workspace`n" -Color $Colors.Success

# Check if .github.template exists
if (-not (Test-Path $GitHubTemplatePath)) {
    Write-ColorOutput "X .github.template not found: $GitHubTemplatePath" -Color $Colors.Error
    exit 1
}

Write-ColorOutput "Check Found .github.template folder`n" -Color $Colors.Success

# Initialize stats
$SyncStats = @{
    Updated = 0
    Skipped = 0
    Errors  = 0
}

# Process instructions and prompts folders
$FoldersToSync = @("instructions", "prompts")

foreach ($Folder in $FoldersToSync) {
    $SourceFolder = Join-Path $SourceGitHubPath $Folder
    $TargetFolder = Join-Path $GitHubTemplatePath $Folder
    
    if (-not (Test-Path $SourceFolder)) {
        Write-VerboseOutput "Source folder not found in workspace: $SourceFolder"
        continue
    }
    
    if (-not (Test-Path $TargetFolder)) {
        Write-VerboseOutput "Target folder not found in template: $TargetFolder"
        continue
    }
    
    Write-ColorOutput "`n[Processing: $Folder]" -Color $Colors.Info
    
    # Get all files from target template folder (only update existing files)
    $TemplateFiles = Get-ChildItem -Path $TargetFolder -File
    
    foreach ($File in $TemplateFiles) {
        $TargetFile = $File.FullName
        $SourceFile = Join-Path $SourceFolder $File.Name
        
        # Calculate file size for display
        $FileSizeKB = [math]::Round($File.Length / 1KB, 1)
        
        if (Test-Path $SourceFile) {
            # File exists in both - compare content
            $SourceHash = (Get-FileHash -Path $SourceFile -Algorithm SHA256).Hash
            $TargetHash = (Get-FileHash -Path $TargetFile -Algorithm SHA256).Hash
            
            if ($SourceHash -ne $TargetHash) {
                # Content differs - update template
                Write-ColorOutput "  Check [UPDATED] $($File.Name) ($FileSizeKB KB)" -Color $Colors.Success
                Write-VerboseOutput "  Content differs - updating template from workspace"
                
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
            # File missing in workspace - skip (only update existing files)
            Write-VerboseOutput "  Check SKIP (missing in workspace): $($File.Name)"
            $SyncStats.Skipped++
        }
    }
}

# Print summary
Write-ColorOutput "`n========================================" -Color $Colors.Info
Write-ColorOutput "Update Summary" -Color $Colors.Info
Write-ColorOutput "========================================`n" -Color $Colors.Info

Write-Host "  Updated files: " -NoNewline
Write-ColorOutput "$($SyncStats.Updated)" -Color $Colors.Success

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

$TotalOps = $SyncStats.Updated + $SyncStats.Skipped
Write-ColorOutput "`nUpdate complete: $TotalOps total files processed`n" -Color $Colors.Success

exit 0
