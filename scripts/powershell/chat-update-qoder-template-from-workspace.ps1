<#
.SYNOPSIS
    Updates QODER/ template with changes from a workspace .qoder/ folder

.DESCRIPTION
    This script compares a workspace's .qoder/ folder with the canonical
    template at cr-misc-function\cr-misc-function\QODER\.

    It will:
    - Update existing files in the template if they differ in the workspace
    - Only update files that already exist in the template (no new files added)
    - Skip files missing from the workspace or unchanged

    Use this to propagate improvements made in another project's .qoder/ folder
    back to the canonical template source in cr-misc-function.

    This is the reverse of chat-Sync-QoderContext.ps1, which pushes the
    template out to the global ~/.qoder folder.

.PARAMETER WorkspaceRoot
    The workspace root where .qoder/ folder exists. Defaults to current
    working directory; walks up the tree to find .qoder/ automatically.
    Example: C:\Users\203715\Documents\Repo\da-ndf4w-1p5c-monitoring-streamlit

.PARAMETER QoderTemplatePath
    Path to the canonical QODER/ template folder. Defaults to the
    cr-misc-function project's QODER/ folder.

.PARAMETER DryRun
    If specified, shows what would be done without making changes.

.PARAMETER Verbose
    Shows detailed output of all operations.

.EXAMPLE
    # Update template from current workspace (auto-detects .qoder/ folder)
    .\scripts\powershell\chat-update-qoder-template-from-workspace.ps1

.EXAMPLE
    # Preview changes without applying
    .\scripts\powershell\chat-update-qoder-template-from-workspace.ps1 -DryRun

.EXAMPLE
    # Update from a specific workspace
    .\scripts\powershell\chat-update-qoder-template-from-workspace.ps1 -WorkspaceRoot "C:\path\to\workspace" -Verbose

.EXAMPLE
    # Override template path
    .\scripts\powershell\chat-update-qoder-template-from-workspace.ps1 `
        -QoderTemplatePath "C:\custom\path\QODER" -DryRun

#>

param(
    [string]$WorkspaceRoot = (Get-Location),
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

# Auto-detect workspace .qoder/ path by walking up from WorkspaceRoot
$WorkspaceQoderPath = $null
$SearchPath = $WorkspaceRoot

while ($SearchPath -ne (Split-Path -Parent $SearchPath)) {
    $PotentialPath = Join-Path $SearchPath ".qoder"
    if (Test-Path $PotentialPath) {
        $WorkspaceQoderPath = $PotentialPath
        break
    }
    $SearchPath = Split-Path -Parent $SearchPath
}

Write-ColorOutput "`n========================================" -Color $Colors.Info
Write-ColorOutput "Update QODER Template from Workspace" -Color $Colors.Info
Write-ColorOutput "========================================`n" -Color $Colors.Info

# Validate workspace .qoder/ path
if (-not $WorkspaceQoderPath) {
    Write-ColorOutput "X .qoder/ folder not found in or above: $WorkspaceRoot" -Color $Colors.Error
    exit 1
}

Write-ColorOutput "[OK] Found workspace .qoder/ folder`n" -Color $Colors.Success

# Validate template path
if (-not (Test-Path $QoderTemplatePath)) {
    Write-ColorOutput "X QODER/ template not found: $QoderTemplatePath" -Color $Colors.Error
    exit 1
}

Write-ColorOutput "[OK] Found QODER/ template folder`n" -Color $Colors.Success

Write-VerboseOutput "Source workspace .qoder/: $WorkspaceQoderPath"
Write-VerboseOutput "Target template QODER/:   $QoderTemplatePath"

# Guard: don't update the template from itself
$SkipSync = $false
if ((Resolve-Path $WorkspaceQoderPath).Path -eq (Resolve-Path $QoderTemplatePath).Path) {
    Write-ColorOutput "! Source and target are the same folder - skipping sync." -Color $Colors.Warning
    $SkipSync = $true
}

# Initialize stats (no Added - this script never creates new template files)
$SyncStats = @{
    Updated = 0
    Skipped = 0
    Errors  = 0
}

if (-not $SkipSync) {
    # ------------------------------------------
    # 1. Update root QODER.md (only if it already exists in template)
    # ------------------------------------------
    Write-ColorOutput "[Processing: root files]" -Color $Colors.Info

    $TemplateQoderMd = Join-Path $QoderTemplatePath "QODER.md"
    $WorkspaceQoderMd = Join-Path $WorkspaceQoderPath "QODER.md"

    if (Test-Path $TemplateQoderMd) {
        if (Test-Path $WorkspaceQoderMd) {
            $SourceHash = (Get-FileHash -Path $WorkspaceQoderMd -Algorithm SHA256).Hash
            $TargetHash = (Get-FileHash -Path $TemplateQoderMd -Algorithm SHA256).Hash

            if ($SourceHash -ne $TargetHash) {
                $FileSizeKB = [math]::Round((Get-Item $WorkspaceQoderMd).Length / 1KB, 1)
                Write-ColorOutput "  [UPDATED] QODER.md ($FileSizeKB KB)" -Color $Colors.Success
                Write-VerboseOutput "Content differs - updating template from workspace"

                if (-not $DryRun) {
                    try {
                        Copy-Item -Path $WorkspaceQoderMd -Destination $TemplateQoderMd -Force
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
            Write-VerboseOutput "  [SKIP] (missing in workspace): QODER.md"
            $SyncStats.Skipped++
        }
    } else {
        Write-VerboseOutput "QODER.md not in template - skipping"
    }

    # ------------------------------------------
    # 2. Update skills/ and agents/ folders (existing template files only)
    # ------------------------------------------
    $FoldersToSync = @("skills", "agents")

    foreach ($Folder in $FoldersToSync) {
        $SourceFolder = Join-Path $WorkspaceQoderPath $Folder
        $TargetFolder = Join-Path $QoderTemplatePath $Folder

        if (-not (Test-Path $TargetFolder)) {
            Write-VerboseOutput "Folder not in template: $Folder/ - skipping"
            continue
        }

        if (-not (Test-Path $SourceFolder)) {
            Write-VerboseOutput "Folder not in workspace: $Folder/ - skipping"
            continue
        }

        Write-ColorOutput "`n[Processing: $Folder/]" -Color $Colors.Info

        # Iterate template files only - never add new files from workspace
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
Write-ColorOutput "  Template QODER/: $QoderTemplatePath`n" -Color $Colors.Info

# ------------------------------------------
# Global vs Template drift check
# ------------------------------------------
$GlobalSkillsPath = Join-Path $env:USERPROFILE ".qoder\skills"

if (Test-Path $GlobalSkillsPath) {
    $TemplateSkillsPath = Join-Path $QoderTemplatePath "skills"
    $GlobalSkillDirs = Get-ChildItem -Path $GlobalSkillsPath -Directory

    if (Test-Path $TemplateSkillsPath) {
        $TemplateSkillDirs = Get-ChildItem -Path $TemplateSkillsPath -Directory
        $OnlyInGlobal = @()

        foreach ($GlobalDir in $GlobalSkillDirs) {
            $TemplateName = $GlobalDir.Name
            $TemplateEquivalent = Join-Path $TemplateSkillsPath $TemplateName
            if (-not (Test-Path $TemplateEquivalent)) {
                $OnlyInGlobal += $TemplateName
            }
        }

        if ($OnlyInGlobal.Count -gt 0) {
            Write-ColorOutput "========================================" -Color $Colors.Warning
            Write-ColorOutput "Global-only skills (not in template)" -Color $Colors.Warning
            Write-ColorOutput "========================================`n" -Color $Colors.Warning
            foreach ($Name in $OnlyInGlobal) {
                Write-ColorOutput "  [GLOBAL ONLY] $Name" -Color $Colors.Warning
            }
            Write-ColorOutput "`n  These exist in ~/.qoder/skills/ but not in the template." -Color ([ConsoleColor]::Gray)
            Write-ColorOutput "  Copy them to QODER/skills/ if they should be part of the template.`n" -Color ([ConsoleColor]::Gray)
        } else {
            Write-ColorOutput "[OK] Global skills are in sync with template (no drift detected)`n" -Color $Colors.Success
        }
    }
}

exit 0
