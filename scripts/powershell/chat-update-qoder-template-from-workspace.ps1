<#
.SYNOPSIS
    Updates QODER/ template with changes from the global ~/.qoder/ folder

.DESCRIPTION
    This script compares the global ~/.qoder/ folder with the canonical
    template at cr-misc-function\cr-misc-function\QODER\.

    It will:
    - Update existing files in the template if they differ in global
    - Only update files that already exist in the template (no new files added)
    - Skip files missing from global or unchanged

    Use this to propagate improvements made in ~/.qoder/ (where Qoder
    actively reads skills, agents, and QODER.md) back to the canonical
    template source in cr-misc-function.

    This is the reverse of chat-Sync-QoderContext.ps1, which pushes the
    template out to the global ~/.qoder folder.

.PARAMETER SourcePath
    Path to the source .qoder/ folder. Defaults to ~/.qoder/ (global).
    Override to pull from a specific project's .qoder/ folder instead.

.PARAMETER QoderTemplatePath
    Path to the canonical QODER/ template folder. Defaults to the
    cr-misc-function project's QODER/ folder.

.PARAMETER DryRun
    If specified, shows what would be done without making changes.

.PARAMETER Verbose
    Shows detailed output of all operations.

.EXAMPLE
    # Update template from global ~/.qoder/ (default)
    .\scripts\powershell\chat-update-qoder-template-from-workspace.ps1

.EXAMPLE
    # Preview changes without applying
    .\scripts\powershell\chat-update-qoder-template-from-workspace.ps1 -DryRun

.EXAMPLE
    # Update from a specific project's .qoder/ instead of global
    .\scripts\powershell\chat-update-qoder-template-from-workspace.ps1 -SourcePath "C:\path\to\project\.qoder" -Verbose

.EXAMPLE
    # Override template path
    .\scripts\powershell\chat-update-qoder-template-from-workspace.ps1 `
        -QoderTemplatePath "C:\custom\path\QODER" -DryRun

#>

param(
    [string]$SourcePath = (Join-Path $env:USERPROFILE ".qoder"),
    [string]$QoderTemplatePath = "C:\Users\203715\Documents\Repo\cr-misc-function\cr-misc-function\QODER",
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

# Resolve source .qoder/ path
$WorkspaceQoderPath = $SourcePath

Write-ColorOutput "`n========================================" -Color $Colors.Info
Write-ColorOutput "Update QODER Template from Global" -Color $Colors.Info
Write-ColorOutput "========================================`n" -Color $Colors.Info

# Validate source .qoder/ path
if (-not (Test-Path $WorkspaceQoderPath)) {
    Write-ColorOutput "X Source .qoder/ folder not found: $WorkspaceQoderPath" -Color $Colors.Error
    exit 1
}

Write-ColorOutput "[OK] Found source .qoder/ folder`n" -Color $Colors.Success

# Validate template path
if (-not (Test-Path $QoderTemplatePath)) {
    Write-ColorOutput "X QODER/ template not found: $QoderTemplatePath" -Color $Colors.Error
    exit 1
}

Write-ColorOutput "[OK] Found QODER/ template folder`n" -Color $Colors.Success

Write-VerboseOutput "Source global .qoder/:    $WorkspaceQoderPath"
Write-VerboseOutput "Target template QODER/:   $QoderTemplatePath"

# Guard: don't update the template from itself
$SkipSync = $false
if ((Resolve-Path $WorkspaceQoderPath).Path -eq (Resolve-Path $QoderTemplatePath).Path) {
    Write-ColorOutput "! Source and target are the same folder - skipping sync." -Color $Colors.Warning
    $SkipSync = $true
}

# Initialize stats
$SyncStats = @{
    Updated = 0
    Added   = 0
    Skipped = 0
    Errors  = 0
}

if (-not $SkipSync) {
    # ------------------------------------------
    # 1. QODER.md - check from global to template
    # ------------------------------------------
    Write-ColorOutput "[Processing: root files]" -Color $Colors.Info

    $SourceQoderMd = Join-Path $WorkspaceQoderPath "QODER.md"
    $TemplateQoderMd = Join-Path $QoderTemplatePath "QODER.md"

    if (Test-Path $SourceQoderMd) {
        $FileSizeKB = [math]::Round((Get-Item $SourceQoderMd).Length / 1KB, 1)
        if (Test-Path $TemplateQoderMd) {
            $SourceHash = (Get-FileHash -Path $SourceQoderMd -Algorithm SHA256).Hash
            $TargetHash = (Get-FileHash -Path $TemplateQoderMd -Algorithm SHA256).Hash

            if ($SourceHash -ne $TargetHash) {
                Write-ColorOutput "  [UPDATED] QODER.md ($FileSizeKB KB)" -Color $Colors.Success
                Write-VerboseOutput "Content differs - updating template from global"

                if (-not $DryRun) {
                    try {
                        Copy-Item -Path $SourceQoderMd -Destination $TemplateQoderMd -Force
                        $SyncStats.Updated++
                    } catch {
                        Write-ColorOutput "    [ERROR] Failed to update QODER.md - $($_.Exception.Message)" -Color $Colors.Error
                        $SyncStats.Errors++
                    }
                } else {
                    $SyncStats.Updated++
                }
            } else {
                Write-VerboseOutput "  [SKIP] (unchanged): QODER.md"
                $SyncStats.Skipped++
            }
        } else {
            Write-ColorOutput "  [ADDED] QODER.md ($FileSizeKB KB)" -Color $Colors.Success
            Write-VerboseOutput "New file in global - adding to template"

            if (-not $DryRun) {
                try {
                    Copy-Item -Path $SourceQoderMd -Destination $TemplateQoderMd -Force
                    $SyncStats.Added++
                } catch {
                    Write-ColorOutput "    [ERROR] Failed to add QODER.md - $($_.Exception.Message)" -Color $Colors.Error
                    $SyncStats.Errors++
                }
            } else {
                $SyncStats.Added++
            }
        }
    } else {
        Write-VerboseOutput "QODER.md not in global - skipping"
    }

    # ------------------------------------------
    # 2. skills/ and agents/ - iterate global files, check against template
    # ------------------------------------------
    $FoldersToSync = @("skills", "agents")

    foreach ($Folder in $FoldersToSync) {
        $SourceFolder = Join-Path $WorkspaceQoderPath $Folder
        $TargetFolder = Join-Path $QoderTemplatePath $Folder

        if (-not (Test-Path $SourceFolder)) {
            Write-VerboseOutput "Folder not in global: $Folder/ - skipping"
            continue
        }

        Write-ColorOutput "`n[Processing: $Folder/]" -Color $Colors.Info

        # Iterate global (source) files - discover everything in ~/.qoder/
        $SourceFiles = Get-ChildItem -Path $SourceFolder -File -Recurse

        if ($SourceFiles.Count -eq 0) {
            Write-VerboseOutput "No files found in global $Folder/"
            continue
        }

        foreach ($File in $SourceFiles) {
            $RelativePath = $File.FullName.Substring($SourceFolder.Length + 1)
            $SourceFile   = $File.FullName
            $TargetFile   = Join-Path $TargetFolder $RelativePath
            $FileSizeKB   = [math]::Round($File.Length / 1KB, 1)

            if (Test-Path $TargetFile) {
                $SourceHash = (Get-FileHash -Path $SourceFile -Algorithm SHA256).Hash
                $TargetHash = (Get-FileHash -Path $TargetFile -Algorithm SHA256).Hash

                if ($SourceHash -ne $TargetHash) {
                    Write-ColorOutput "  [UPDATED] $RelativePath ($FileSizeKB KB)" -Color $Colors.Success
                    Write-VerboseOutput "Content differs - updating template from global"

                    if (-not $DryRun) {
                        try {
                            Copy-Item -Path $SourceFile -Destination $TargetFile -Force
                            $SyncStats.Updated++
                        } catch {
                            Write-ColorOutput "    [ERROR] Failed to update $RelativePath - $($_.Exception.Message)" -Color $Colors.Error
                            $SyncStats.Errors++
                        }
                    } else {
                        $SyncStats.Updated++
                    }
                } else {
                    Write-VerboseOutput "  [SKIP] (unchanged): $RelativePath"
                    $SyncStats.Skipped++
                }
            } else {
                Write-ColorOutput "  [ADDED] $RelativePath ($FileSizeKB KB)" -Color $Colors.Success
                Write-VerboseOutput "New file in global - adding to template"

                if (-not $DryRun) {
                    try {
                        $TargetDir = Split-Path -Parent $TargetFile
                        if (-not (Test-Path $TargetDir)) {
                            New-Item -ItemType Directory -Path $TargetDir -Force | Out-Null
                        }
                        Copy-Item -Path $SourceFile -Destination $TargetFile -Force
                        $SyncStats.Added++
                    } catch {
                        Write-ColorOutput "    [ERROR] Failed to add $RelativePath - $($_.Exception.Message)" -Color $Colors.Error
                        $SyncStats.Errors++
                    }
                } else {
                    $SyncStats.Added++
                }
            }
        }
    }
}

# ------------------------------------------
# Summary
# ------------------------------------------
Write-ColorOutput "`n========================================" -Color $Colors.Info
Write-ColorOutput "Update Summary" -Color $Colors.Info
Write-ColorOutput "========================================`n" -Color $Colors.Info

Write-Host "  Added files:   " -NoNewline
Write-ColorOutput "$($SyncStats.Added)" -Color $Colors.Success

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
    Write-ColorOutput "`n[DRY RUN] No files were actually modified" -Color $Colors.Warning
}

$TotalOps = $SyncStats.Added + $SyncStats.Updated + $SyncStats.Skipped
Write-ColorOutput "`n[OK] Update complete: $TotalOps total files processed" -Color $Colors.Success
Write-ColorOutput "  Template QODER/: $QoderTemplatePath`n" -Color $Colors.Info

exit 0
