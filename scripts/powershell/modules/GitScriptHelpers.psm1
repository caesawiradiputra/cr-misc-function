<#
.SYNOPSIS
    Shared helper functions for Git PowerShell scripts.

.DESCRIPTION
    Provides canonical output helpers, confirmation prompts with retry loops,
    and common git utility functions used across all git-*.ps1 scripts.

    Import in scripts:
        Import-Module (Join-Path $PSScriptRoot "modules\GitScriptHelpers.psm1")
#>


# ============================================================================
# OUTPUT HELPERS - Color-coded status messages with consistent formatting
# ============================================================================

function Write-Step {
    <#
    .SYNOPSIS
        Display a step/phase header with a customizable prefix label.
    #>
    param(
        [Parameter(Mandatory)]
        [string]$Message,

        [string]$Prefix = "[STEP]"
    )
    Write-Host "`n$Prefix " -ForegroundColor Cyan -NoNewline
    Write-Host $Message -ForegroundColor White
}

function Write-Info {
    <#
    .SYNOPSIS
        Display an informational message.
    #>
    param([Parameter(Mandatory)][string]$Message)
    Write-Host "[INFO] " -ForegroundColor Cyan -NoNewline
    Write-Host $Message -ForegroundColor White
}

function Write-Warn {
    <#
    .SYNOPSIS
        Display a warning message.
    #>
    param([Parameter(Mandatory)][string]$Message)
    Write-Host "[WARN] " -ForegroundColor Yellow -NoNewline
    Write-Host $Message -ForegroundColor White
}

function Write-Success {
    <#
    .SYNOPSIS
        Display a success/OK message.
    #>
    param([Parameter(Mandatory)][string]$Message)
    Write-Host "[OK] " -ForegroundColor Green -NoNewline
    Write-Host $Message -ForegroundColor White
}

function Write-ErrorMsg {
    <#
    .SYNOPSIS
        Display an error message.
    #>
    param([Parameter(Mandatory)][string]$Message)
    Write-Host "[ERROR] " -ForegroundColor Red -NoNewline
    Write-Host $Message -ForegroundColor White
}


# ============================================================================
# CONFIRMATION PROMPT - Standardized retry loop with two modes
# ============================================================================

function Confirm-Action {
    <#
    .SYNOPSIS
        Prompt the user for confirmation with a retry loop on invalid input.

    .DESCRIPTION
        Two styles:
        - Explicit: User must type 'yes' to proceed. Empty input = cancel.
                    Use for destructive operations (reset, delete).
        - YesNo:    User enters 'y' or 'n'. Empty input re-prompts with [WARN].
                    Use for regular confirmations (push, rebase, sync).

    .PARAMETER Prompt
        The message to display before the input prompt.

    .PARAMETER Style
        'Explicit' (default) or 'YesNo'.

    .PARAMETER CancelMessage
        Message to display when the user cancels. Default: 'Operation cancelled by user'.

    .OUTPUTS
        $true if user confirmed, $false if user cancelled.

    .EXAMPLE
        if (-not (Confirm-Action -Prompt "Type 'yes' to continue" -Style Explicit)) { exit 0 }

    .EXAMPLE
        if (-not (Confirm-Action -Prompt "Push branch to remote? (y/N)" -Style YesNo)) { Write-Info "Skipped" }
    #>
    param(
        [Parameter(Mandatory)]
        [string]$Prompt,

        [ValidateSet("Explicit", "YesNo")]
        [string]$Style = "Explicit",

        [string]$CancelMessage = "Operation cancelled by user"
    )

    while ($true) {
        $input_ = Read-Host $Prompt
        $input_ = $input_.Trim().ToLower()

        if ($Style -eq "Explicit") {
            # 'yes' = confirmed, empty = cancel, anything else = re-prompt
            if ($input_ -eq "yes") { return $true }
            if ($input_ -eq "") {
                Write-Warn $CancelMessage
                return $false
            }
            Write-Warn "Invalid input: '$input_'. Type 'yes' to confirm or press Enter to cancel."
        } else {
            # YesNo style: 'y' = yes, 'n' = no, empty = re-prompt
            if ($input_ -eq "y") { return $true }
            if ($input_ -eq "n") { return $false }
            Write-Warn "Invalid input: '$input_'. Please enter 'y' or 'n'."
        }
    }
}


# ============================================================================
# EXPORTS
# ============================================================================

Export-ModuleMember -Function @(
    "Write-Step",
    "Write-Info",
    "Write-Warn",
    "Write-Success",
    "Write-ErrorMsg",
    "Confirm-Action"
)
