<#
.SYNOPSIS
    Synchronizes project .copilot context with global ~/.copilot folder

.DESCRIPTION
    This script syncs your project's .copilot folder (instructions, prompts, agents,
    skills, references) to the global C:\Users\203715\.copilot folder.

    It will:
    - Add missing files from project .copilot to global folder
    - Update files that differ from project .copilot
    - Skip unchanged files (compares SHA256 hash)
    - Preserve folder structure

    This avoids manual copying every time you make changes to instructions, prompts, etc.

.PARAMETER ProjectCopilotPath
    Path to the project's .copilot folder. Defaults to current project's .copilot.
    Example: C:\Users\203715\Documents\Repo\cr-misc-function\cr-misc-function\.copilot

.PARAMETER GlobalCopilotPath
    Path to the global copilot folder. Defaults to C:\Users\203715\.copilot

.PARAMETER DryRun
    If specified, shows what would be done without making changes.

.PARAMETER Verbose
    Shows detailed output of all operations.

.EXAMPLE
    # Run from project folder - automatically detects .copilot folder
    .\scripts\powershell\Sync-CopilotContext.ps1

.EXAMPLE
    # Preview changes without applying
    .\scripts\powershell\Sync-CopilotContext.ps1 -DryRun

.EXAMPLE
    # Show detailed output
    .\scripts\powershell\Sync-CopilotContext.ps1 -Verbose

.EXAMPLE
    # Specify custom paths
    .\scripts\powershell\Sync-CopilotContext.ps1 `
        -ProjectCopilotPath "C:\path\to\project\.copilot" `
        -GlobalCopilotPath "C:\Users\203715\.copilot"

#>

param(
    [string]$ProjectCopilotPath,
    [string]$GlobalCopilotPath = "C:\Users\203715\.copilot",
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

# Auto-detect project .copilot path if not provided
if (-not $ProjectCopilotPath) {
    # Look for .copilot folder in current directory or parent directories
    $CurrentPath = (Get-Location).Path
    $SearchPath = $CurrentPath

    while ($SearchPath -ne (Split-Path -Parent $SearchPath)) {
        $PotentialPath = Join-Path $SearchPath ".copilot"
        if (Test-Path $PotentialPath) {
            $ProjectCopilotPath = $PotentialPath
            break
        }
        $SearchPath = Split-Path -Parent $SearchPath
    }
}

# If still not found, try common project locations
if (-not $ProjectCopilotPath) {
    $ProjectCopilotPath = "C:\Users\203715\Documents\Repo\cr-misc-function\cr-misc-function\.copilot"
}

Write-ColorOutput "`n========================================" -Color $Colors.Info
Write-ColorOutput "Copilot Context Sync" -Color $Colors.Info
Write-ColorOutput "========================================`n" -Color $Colors.Info

# Validate paths
if (-not (Test-Path $ProjectCopilotPath)) {
    Write-ColorOutput "X Project .copilot folder not found: $ProjectCopilotPath" -Color $Colors.Error
    exit 1
}

Write-VerboseOutput "Project .copilot: $ProjectCopilotPath"
Write-VerboseOutput "Global .copilot: $GlobalCopilotPath"

# Ensure global .copilot folder exists
if (-not (Test-Path $GlobalCopilotPath)) {
    Write-ColorOutput "Creating global .copilot folder..." -Color $Colors.Info
    if (-not $DryRun) {
        New-Item -ItemType Directory -Path $GlobalCopilotPath | Out-Null
    }
}

Write-ColorOutput "[OK] Found project .copilot folder`n" -Color $Colors.Success

# Initialize stats
$SyncStats = @{
    Added   = 0
    Updated = 0
    Skipped = 0
    Errors  = 0
}

# Process folders
$FoldersToSync = @("instructions", "prompts", "agents", "skills", "references")

foreach ($Folder in $FoldersToSync) {
    $SourceFolder = Join-Path $ProjectCopilotPath $Folder
    $TargetFolder = Join-Path $GlobalCopilotPath $Folder

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

    Write-ColorOutput "[Processing: $Folder]" -Color $Colors.Info

    # Get all files from source folder recursively
    $SourceFiles = Get-ChildItem -Path $SourceFolder -File -Recurse

    if ($SourceFiles.Count -eq 0) {
        Write-VerboseOutput "No files found in $Folder"
        continue
    }

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
                Write-ColorOutput "  [UPDATED] $RelativePath ($FileSizeKB KB)" -Color $Colors.Success
                Write-VerboseOutput "Content differs - updating"

                if (-not $DryRun) {
                    try {
                        Copy-Item -Path $SourceFile -Destination $TargetFile -Force
                        $SyncStats.Updated++
                    } catch {
                        Write-ColorOutput "    [ERROR] Failed to update - $($_.Exception.Message)" -Color $Colors.Error
                        $SyncStats.Errors++
                    }
                } else {
                    $SyncStats.Updated++
                }
            } else {
                # Content is the same - skip
                Write-VerboseOutput "  [SKIP] (unchanged): $RelativePath"
                $SyncStats.Skipped++
            }
        } else {
            # File doesn't exist in target - add it
            Write-ColorOutput "  [ADDED] $RelativePath ($FileSizeKB KB)" -Color $Colors.Success
            Write-VerboseOutput "File missing in global - adding"

            if (-not $DryRun) {
                try {
                    Copy-Item -Path $SourceFile -Destination $TargetFile -Force
                    $SyncStats.Added++
                } catch {
                    Write-ColorOutput "    [ERROR] Failed to add - $($_.Exception.Message)" -Color $Colors.Error
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
    Write-ColorOutput "`n[DRY RUN] No files were actually modified" -Color $Colors.Warning
}

$TotalOps = $SyncStats.Added + $SyncStats.Updated + $SyncStats.Skipped
Write-ColorOutput "`n[OK] Sync complete: $TotalOps total files processed" -Color $Colors.Success
Write-ColorOutput "  Global .copilot: $GlobalCopilotPath`n" -Color $Colors.Info

exit 0
