<#
.SYNOPSIS
    Updates CLAUDE/ template with changes from a workspace CLAUDE/ folder

.DESCRIPTION
    This script compares a workspace's CLAUDE/ folder with the canonical
    template at cr-misc-function\cr-misc-function\CLAUDE\.

    It will:
    - Update existing files in the template if they differ in the workspace
    - Only update files that already exist in the template (no new files added)
    - Skip files missing from the workspace or unchanged

    Use this to propagate improvements made in another project's CLAUDE/ folder
    back to the canonical template source in cr-misc-function.

    This is the reverse of chat-Sync-ClaudeContext.ps1, which pushes the
    template out to the global ~/.claude folder.

.PARAMETER WorkspaceRoot
    The workspace root where CLAUDE/ folder exists. Defaults to current
    working directory; walks up the tree to find CLAUDE/ automatically.
    Example: C:\Users\203715\Documents\Repo\da-ndf4w-1p5c-monitoring-streamlit

.PARAMETER ClaudeTemplatePath
    Path to the canonical CLAUDE/ template folder. Defaults to the
    cr-misc-function project's CLAUDE/ folder.

.PARAMETER DryRun
    If specified, shows what would be done without making changes.

.PARAMETER Verbose
    Shows detailed output of all operations.

.EXAMPLE
    # Update template from current workspace (auto-detects CLAUDE/ folder)
    .\scripts\powershell\chat-update-claude-template-from-workspace.ps1

.EXAMPLE
    # Preview changes without applying
    .\scripts\powershell\chat-update-claude-template-from-workspace.ps1 -DryRun

.EXAMPLE
    # Update from a specific workspace
    .\scripts\powershell\chat-update-claude-template-from-workspace.ps1 -WorkspaceRoot "C:\path\to\workspace" -Verbose

.EXAMPLE
    # Override template path
    .\scripts\powershell\chat-update-claude-template-from-workspace.ps1 `
        -ClaudeTemplatePath "C:\custom\path\CLAUDE" -DryRun

#>

param(
    [string]$WorkspaceRoot = (Get-Location),
    [string]$ClaudeTemplatePath = "C:\Users\203715\Documents\Repo\cr-misc-function\cr-misc-function\CLAUDE",
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

# Auto-detect workspace CLAUDE/ path by walking up from WorkspaceRoot
$WorkspaceClaudePath = $null
$SearchPath = $WorkspaceRoot

while ($SearchPath -ne (Split-Path -Parent $SearchPath)) {
    $PotentialPath = Join-Path $SearchPath "CLAUDE"
    if (Test-Path $PotentialPath) {
        $WorkspaceClaudePath = $PotentialPath
        break
    }
    $SearchPath = Split-Path -Parent $SearchPath
}

Write-ColorOutput "`n========================================" -Color $Colors.Info
Write-ColorOutput "Update CLAUDE Template from Workspace" -Color $Colors.Info
Write-ColorOutput "========================================`n" -Color $Colors.Info

# Validate workspace CLAUDE path
if (-not $WorkspaceClaudePath) {
    Write-ColorOutput "X CLAUDE/ folder not found in or above: $WorkspaceRoot" -Color $Colors.Error
    exit 1
}

Write-ColorOutput "[OK] Found workspace CLAUDE/ folder`n" -Color $Colors.Success

# Validate template path
if (-not (Test-Path $ClaudeTemplatePath)) {
    Write-ColorOutput "X CLAUDE/ template not found: $ClaudeTemplatePath" -Color $Colors.Error
    exit 1
}

Write-ColorOutput "[OK] Found CLAUDE/ template folder`n" -Color $Colors.Success

Write-VerboseOutput "Source workspace CLAUDE/: $WorkspaceClaudePath"
Write-VerboseOutput "Target template CLAUDE/:  $ClaudeTemplatePath"

# Guard: don't update the template from itself
$SkipSync = $false
if ($WorkspaceClaudePath -eq $ClaudeTemplatePath) {
    Write-ColorOutput "! Source and target are the same folder - skipping sync." -Color $Colors.Warning
    $SkipSync = $true
}

# Initialize stats (no Added — this script never creates new template files)
$SyncStats = @{
    Updated = 0
    Skipped = 0
    Errors  = 0
}

if (-not $SkipSync) {
    # ------------------------------------------
    # 1. Update root CLAUDE.md (only if it already exists in template)
    # ------------------------------------------
    Write-ColorOutput "[Processing: root files]" -Color $Colors.Info

    $TemplateCLAUDEMd = Join-Path $ClaudeTemplatePath "CLAUDE.md"
    $WorkspaceCLAUDEMd = Join-Path $WorkspaceClaudePath "CLAUDE.md"

    if (Test-Path $TemplateCLAUDEMd) {
        if (Test-Path $WorkspaceCLAUDEMd) {
            $SourceHash = (Get-FileHash -Path $WorkspaceCLAUDEMd -Algorithm SHA256).Hash
            $TargetHash = (Get-FileHash -Path $TemplateCLAUDEMd -Algorithm SHA256).Hash

            if ($SourceHash -ne $TargetHash) {
                $FileSizeKB = [math]::Round((Get-Item $WorkspaceCLAUDEMd).Length / 1KB, 1)
                Write-ColorOutput "  [UPDATED] CLAUDE.md ($FileSizeKB KB)" -Color $Colors.Success
                Write-VerboseOutput "Content differs - updating template from workspace"

                if (-not $DryRun) {
                    try {
                        Copy-Item -Path $WorkspaceCLAUDEMd -Destination $TemplateCLAUDEMd -Force
                        $SyncStats.Updated++
                    } catch {
                        Write-ColorOutput "    [ERROR] Failed to update CLAUDE.md - $($_.Exception.Message)" -Color $Colors.Error
                        $SyncStats.Errors++
                    }
                } else {
                    $SyncStats.Updated++
                }
            } else {
                Write-VerboseOutput "  [SKIP] (unchanged): CLAUDE.md"
                $SyncStats.Skipped++
            }
        } else {
            Write-VerboseOutput "  [SKIP] (missing in workspace): CLAUDE.md"
            $SyncStats.Skipped++
        }
    } else {
        Write-VerboseOutput "CLAUDE.md not in template - skipping"
    }

    # ------------------------------------------
    # 2. Update commands/ folder (existing template files only)
    # ------------------------------------------
    $FoldersToSync = @("commands")

    foreach ($Folder in $FoldersToSync) {
        $SourceFolder = Join-Path $WorkspaceClaudePath $Folder
        $TargetFolder = Join-Path $ClaudeTemplatePath $Folder

        if (-not (Test-Path $TargetFolder)) {
            Write-VerboseOutput "Folder not in template: $Folder - skipping"
            continue
        }

        if (-not (Test-Path $SourceFolder)) {
            Write-VerboseOutput "Folder not in workspace: $Folder - skipping"
            continue
        }

        Write-ColorOutput "`n[Processing: $Folder/]" -Color $Colors.Info

        # Iterate template files only — never add new commands from workspace
        $TemplateFiles = Get-ChildItem -Path $TargetFolder -File -Recurse

        if ($TemplateFiles.Count -eq 0) {
            Write-VerboseOutput "No files found in template $Folder/"
            continue
        }

        foreach ($File in $TemplateFiles) {
            $RelativePath  = $File.FullName.Substring($TargetFolder.Length + 1)
            $SourceFile    = Join-Path $SourceFolder $RelativePath
            $TargetFile    = $File.FullName
            $FileSizeKB    = [math]::Round($File.Length / 1KB, 1)

            if (Test-Path $SourceFile) {
                $SourceHash = (Get-FileHash -Path $SourceFile -Algorithm SHA256).Hash
                $TargetHash = (Get-FileHash -Path $TargetFile -Algorithm SHA256).Hash

                if ($SourceHash -ne $TargetHash) {
                    Write-ColorOutput "  [UPDATED] $RelativePath ($FileSizeKB KB)" -Color $Colors.Success
                    Write-VerboseOutput "Content differs - updating template from workspace"

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
                Write-VerboseOutput "  [SKIP] (missing in workspace): $RelativePath"
                $SyncStats.Skipped++
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

$TotalOps = $SyncStats.Updated + $SyncStats.Skipped
Write-ColorOutput "`n[OK] Update complete: $TotalOps total files processed" -Color $Colors.Success
Write-ColorOutput "  Template CLAUDE/: $ClaudeTemplatePath`n" -Color $Colors.Info

# ------------------------------------------
# Global vs Template drift check
# ------------------------------------------
$GlobalCommandsPath = Join-Path $env:USERPROFILE ".claude\commands"

if (Test-Path $GlobalCommandsPath) {
    $TemplateCommandsPath = Join-Path $ClaudeTemplatePath "commands"
    $GlobalFiles = Get-ChildItem -Path $GlobalCommandsPath -File -Recurse
    $OnlyInGlobal = @()

    foreach ($GlobalFile in $GlobalFiles) {
        $RelPath = $GlobalFile.FullName.Substring($GlobalCommandsPath.Length + 1)
        $TemplateEquivalent = Join-Path $TemplateCommandsPath $RelPath
        if (-not (Test-Path $TemplateEquivalent)) {
            $OnlyInGlobal += $RelPath
        }
    }

    if ($OnlyInGlobal.Count -gt 0) {
        Write-ColorOutput "========================================" -Color $Colors.Warning
        Write-ColorOutput "Global-only commands (not in template)" -Color $Colors.Warning
        Write-ColorOutput "========================================`n" -Color $Colors.Warning
        foreach ($Name in $OnlyInGlobal) {
            Write-ColorOutput "  [GLOBAL ONLY] $Name" -Color $Colors.Warning
        }
        Write-ColorOutput "`n  These exist in ~/.claude/commands/ but not in the template." -Color ([ConsoleColor]::Gray)
        Write-ColorOutput "  Copy them to CLAUDE/commands/ if they should be part of the template.`n" -Color ([ConsoleColor]::Gray)
    } else {
        Write-ColorOutput "[OK] Global commands are in sync with template (no drift detected)`n" -Color $Colors.Success
    }
}

exit 0
