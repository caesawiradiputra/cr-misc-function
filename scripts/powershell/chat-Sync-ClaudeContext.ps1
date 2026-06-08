<#
.SYNOPSIS
    Synchronizes project CLAUDE/ context with global ~/.claude folder

.DESCRIPTION
    This script syncs your project's CLAUDE/ folder (CLAUDE.md + commands/)
    to the global C:\Users\203715\.claude folder.

    It will:
    - Add missing files from project CLAUDE/ to global folder
    - Update files that differ from project CLAUDE/
    - Skip unchanged files (compares SHA256 hash)
    - Preserve folder structure

    This avoids manual copying every time you update instructions or slash commands.

.PARAMETER ProjectClaudePath
    Path to the project's CLAUDE folder. Defaults to current project's CLAUDE/.
    Example: C:\Users\203715\Documents\Repo\cr-misc-function\cr-misc-function\CLAUDE

.PARAMETER GlobalClaudePath
    Path to the global Claude config folder. Defaults to C:\Users\203715\.claude

.PARAMETER DryRun
    If specified, shows what would be done without making changes.

.PARAMETER Verbose
    Shows detailed output of all operations.

.EXAMPLE
    # Run from project folder - automatically detects CLAUDE/ folder
    .\scripts\powershell\chat-Sync-ClaudeContext.ps1

.EXAMPLE
    # Preview changes without applying
    .\scripts\powershell\chat-Sync-ClaudeContext.ps1 -DryRun

.EXAMPLE
    # Show detailed output
    .\scripts\powershell\chat-Sync-ClaudeContext.ps1 -Verbose

.EXAMPLE
    # Specify custom paths
    .\scripts\powershell\chat-Sync-ClaudeContext.ps1 `
        -ProjectClaudePath "C:\path\to\project\CLAUDE" `
        -GlobalClaudePath "C:\Users\203715\.claude"

#>

param(
    [string]$ProjectClaudePath,
    [string]$GlobalClaudePath = "C:\Users\203715\.claude",
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

# Auto-detect project CLAUDE path if not provided
if (-not $ProjectClaudePath) {
    $CurrentPath = (Get-Location).Path
    $SearchPath = $CurrentPath

    while ($SearchPath -ne (Split-Path -Parent $SearchPath)) {
        $PotentialPath = Join-Path $SearchPath "CLAUDE"
        if (Test-Path $PotentialPath) {
            $ProjectClaudePath = $PotentialPath
            break
        }
        $SearchPath = Split-Path -Parent $SearchPath
    }
}

# If still not found, fall back to known project location
if (-not $ProjectClaudePath) {
    $ProjectClaudePath = "C:\Users\203715\Documents\Repo\cr-misc-function\cr-misc-function\CLAUDE"
}

Write-ColorOutput "`n========================================" -Color $Colors.Info
Write-ColorOutput "Claude Context Sync" -Color $Colors.Info
Write-ColorOutput "========================================`n" -Color $Colors.Info

# Validate source path
if (-not (Test-Path $ProjectClaudePath)) {
    Write-ColorOutput "X Project CLAUDE/ folder not found: $ProjectClaudePath" -Color $Colors.Error
    exit 1
}

Write-VerboseOutput "Project CLAUDE/: $ProjectClaudePath"
Write-VerboseOutput "Global .claude/: $GlobalClaudePath"

# Ensure global .claude folder exists
if (-not (Test-Path $GlobalClaudePath)) {
    Write-ColorOutput "Creating global .claude folder..." -Color $Colors.Info
    if (-not $DryRun) {
        New-Item -ItemType Directory -Path $GlobalClaudePath -Force | Out-Null
    }
}

Write-ColorOutput "[OK] Found project CLAUDE/ folder`n" -Color $Colors.Success

# Initialize stats
$Added   = 0
$Updated = 0
$Skipped = 0
$Errors  = 0

# ------------------------------------------
# 1. Sync root CLAUDE.md
# ------------------------------------------
Write-ColorOutput "[Processing: root files]" -Color $Colors.Info

$SourceClaudeMd = Join-Path $ProjectClaudePath "CLAUDE.md"
$TargetClaudeMd = Join-Path $GlobalClaudePath "CLAUDE.md"

if (Test-Path $SourceClaudeMd) {
    $Result = Sync-SingleFile -SourceFile $SourceClaudeMd -TargetFile $TargetClaudeMd -DisplayName "CLAUDE.md"
    switch ($Result) {
        "Added"   { $Added++ }
        "Updated" { $Updated++ }
        "Skipped" { $Skipped++ }
        "Error"   { $Errors++ }
    }
} else {
    Write-VerboseOutput "CLAUDE.md not found in project CLAUDE/ - skipping"
}

# ------------------------------------------
# 2. Sync commands/ folder
# ------------------------------------------
$FoldersToSync = @("commands")

foreach ($Folder in $FoldersToSync) {
    $SourceFolder = Join-Path $ProjectClaudePath $Folder
    $TargetFolder = Join-Path $GlobalClaudePath $Folder

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
Write-ColorOutput "  Global .claude/: $GlobalClaudePath`n" -Color $Colors.Info

exit 0
