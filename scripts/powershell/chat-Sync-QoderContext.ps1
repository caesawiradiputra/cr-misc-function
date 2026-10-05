<#
.SYNOPSIS
    Synchronizes project QODER/ context (skills, agents, QODER.md) with global ~/.qoder folder

.DESCRIPTION
    This script syncs your project's QODER/ folder (skills/, agents/, QODER.md)
    to the global C:\Users\203715\.qoder folder.

    It will:
    - Add missing skills, agents, and config from project QODER/ to global folder
    - Update files that differ from project QODER/ (compares SHA256 hash)
    - Skip unchanged files
    - Preserve folder structure (skills/skill-name/SKILL.md, agents/*.md, etc.)
    - Never touch IDE-managed dirs (cache, extensions, projects, memories, etc.)

    This avoids manual copying every time you update a skill or agent.

.PARAMETER ProjectQoderPath
    Path to the project's QODER folder. Auto-detected if omitted.
    Searches upward from current directory for the nearest QODER/ folder.

.PARAMETER GlobalQoderPath
    Path to the global Qoder config folder. Defaults to C:\Users\203715\.qoder

.PARAMETER DryRun
    If specified, shows what would be done without making changes.

.PARAMETER Verbose
    Shows detailed output of all operations.

.EXAMPLE
    # Run from project folder — automatically detects QODER/ folder
    .\scripts\powershell\chat-Sync-QoderContext.ps1

.EXAMPLE
    # Preview changes without applying
    .\scripts\powershell\chat-Sync-QoderContext.ps1 -DryRun

.EXAMPLE
    # Show detailed output
    .\scripts\powershell\chat-Sync-QoderContext.ps1 -Verbose

.EXAMPLE
    # Specify custom paths
    .\scripts\powershell\chat-Sync-QoderContext.ps1 `
        -ProjectQoderPath "C:\path\to\project\QODER" `
        -GlobalQoderPath "C:\Users\203715\.qoder"

#>

param(
    [string]$ProjectQoderPath,
    [string]$GlobalQoderPath = "$env:USERPROFILE\.qoder",
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

function Sync-SingleFile {
    param(
        [string]$SourceFile,
        [string]$TargetFile,
        [string]$DisplayName
    )

    $FileSizeKB = [math]::Round((Get-Item $SourceFile).Length / 1KB, 1)

    if (Test-Path $TargetFile) {
        $SourceHash = (Get-FileHash -Path $SourceFile -Algorithm SHA256).Hash
        $TargetHash = (Get-FileHash -Path $TargetFile -Algorithm SHA256).Hash

        if ($SourceHash -ne $TargetHash) {
            Write-ColorOutput "  [UPDATED] $DisplayName ($FileSizeKB KB)" -Color $Colors.Success
            Write-VerboseOutput "Content differs - updating"

            if (-not $DryRun) {
                try {
                    Copy-Item -Path $SourceFile -Destination $TargetFile -Force
                    return "Updated"
                } catch {
                    Write-ColorOutput "    [ERROR] Failed to update - $($_.Exception.Message)" -Color $Colors.Error
                    return "Error"
                }
            }
            return "Updated"
        } else {
            Write-VerboseOutput "  [SKIP] (unchanged): $DisplayName"
            return "Skipped"
        }
    } else {
        Write-ColorOutput "  [ADDED] $DisplayName ($FileSizeKB KB)" -Color $Colors.Success
        Write-VerboseOutput "File missing in global - adding"

        if (-not $DryRun) {
            try {
                Copy-Item -Path $SourceFile -Destination $TargetFile -Force
                return "Added"
            } catch {
                Write-ColorOutput "    [ERROR] Failed to add - $($_.Exception.Message)" -Color $Colors.Error
                return "Error"
            }
        }
        return "Added"
    }
}

# Auto-detect project QODER path if not provided
if (-not $ProjectQoderPath) {
    $CurrentPath = (Get-Location).Path
    $SearchPath = $CurrentPath

    while ($SearchPath -ne (Split-Path -Parent $SearchPath)) {
        $PotentialPath = Join-Path $SearchPath "QODER"
        if (Test-Path $PotentialPath) {
            $ProjectQoderPath = $PotentialPath
            break
        }
        $SearchPath = Split-Path -Parent $SearchPath
    }
}

# If still not found, fall back to known project location
if (-not $ProjectQoderPath) {
    $ProjectQoderPath = "C:\Users\203715\Documents\Repo\cr-misc-function\cr-misc-function\QODER"
}

Write-ColorOutput "`n========================================" -Color $Colors.Info
Write-ColorOutput "Qoder Context Sync" -Color $Colors.Info
Write-ColorOutput "========================================`n" -Color $Colors.Info

# Validate source path
if (-not (Test-Path $ProjectQoderPath)) {
    Write-ColorOutput "X Project QODER/ folder not found: $ProjectQoderPath" -Color $Colors.Error
    exit 1
}

Write-VerboseOutput "Project QODER/: $ProjectQoderPath"
Write-VerboseOutput "Global ~/.qoder/: $GlobalQoderPath"

# Ensure global .qoder folder exists
if (-not (Test-Path $GlobalQoderPath)) {
    Write-ColorOutput "Creating global .qoder folder..." -Color $Colors.Info
    if (-not $DryRun) {
        New-Item -ItemType Directory -Path $GlobalQoderPath -Force | Out-Null
    }
}

Write-ColorOutput "[OK] Found project QODER/ folder`n" -Color $Colors.Success

# Initialize stats
$Added   = 0
$Updated = 0
$Skipped = 0
$Errors  = 0

# ------------------------------------------
# 1. Sync root files (QODER.md)
# ------------------------------------------
Write-ColorOutput "[Processing: root files]" -Color $Colors.Info

$RootFilesToSync = @("QODER.md")

foreach ($RootFile in $RootFilesToSync) {
    $SourceFile = Join-Path $ProjectQoderPath $RootFile
    $TargetFile = Join-Path $GlobalQoderPath $RootFile

    if (Test-Path $SourceFile) {
        $Result = Sync-SingleFile -SourceFile $SourceFile -TargetFile $TargetFile -DisplayName $RootFile
        switch ($Result) {
            "Added"   { $Added++ }
            "Updated" { $Updated++ }
            "Skipped" { $Skipped++ }
            "Error"   { $Errors++ }
        }
    } else {
        Write-VerboseOutput "$RootFile not found in project QODER/ - skipping"
    }
}

# ------------------------------------------
# 2. Sync folders (skills/, agents/)
# ------------------------------------------
$FoldersToSync = @("skills", "agents")

foreach ($Folder in $FoldersToSync) {
    $SourceFolder = Join-Path $ProjectQoderPath $Folder
    $TargetFolder = Join-Path $GlobalQoderPath $Folder

    if (-not (Test-Path $SourceFolder)) {
        Write-VerboseOutput "Source folder not found: $SourceFolder"
        continue
    }

    # Ensure target folder exists
    if (-not (Test-Path $TargetFolder)) {
        if (-not $DryRun) {
            New-Item -ItemType Directory -Path $TargetFolder -Force | Out-Null
        }
    }

    Write-ColorOutput "[Processing: $Folder/]" -Color $Colors.Info

    $SourceFiles = Get-ChildItem -Path $SourceFolder -File -Recurse

    if ($SourceFiles.Count -eq 0) {
        Write-VerboseOutput "No files found in $Folder/"
        continue
    }

    foreach ($File in $SourceFiles) {
        $RelativePath = $File.FullName.Substring($SourceFolder.Length + 1)
        $TargetFile   = Join-Path $TargetFolder $RelativePath

        # Ensure target subdirectory exists
        $TargetDir = Split-Path -Parent $TargetFile
        if (-not (Test-Path $TargetDir)) {
            if (-not $DryRun) {
                New-Item -ItemType Directory -Path $TargetDir -Force | Out-Null
            }
        }

        $Result = Sync-SingleFile -SourceFile $File.FullName -TargetFile $TargetFile -DisplayName "$Folder/$RelativePath"
        switch ($Result) {
            "Added"   { $Added++ }
            "Updated" { $Updated++ }
            "Skipped" { $Skipped++ }
            "Error"   { $Errors++ }
        }
    }
}

# ------------------------------------------
# Summary
# ------------------------------------------
Write-ColorOutput "`n========================================" -Color $Colors.Info
Write-ColorOutput "Sync Summary" -Color $Colors.Info
Write-ColorOutput "========================================`n" -Color $Colors.Info

Write-Host "  Added files:   " -NoNewline
Write-ColorOutput "$Added" -Color $Colors.Success

Write-Host "  Updated files: " -NoNewline
Write-ColorOutput "$Updated" -Color $Colors.Warning

Write-Host "  Skipped files: " -NoNewline
Write-ColorOutput "$Skipped" -Color ([ConsoleColor]::Gray)

Write-Host "  Errors:        " -NoNewline
if ($Errors -gt 0) {
    Write-ColorOutput "$Errors" -Color $Colors.Error
} else {
    Write-ColorOutput "$Errors" -Color $Colors.Success
}

if ($DryRun) {
    Write-ColorOutput "`n[DRY RUN] No files were actually modified" -Color $Colors.Warning
}

$TotalOps = $Added + $Updated + $Skipped
Write-ColorOutput "`n[OK] Sync complete: $TotalOps total files processed" -Color $Colors.Success
Write-ColorOutput "  Global ~/.qoder/: $GlobalQoderPath`n" -Color $Colors.Info

exit 0
