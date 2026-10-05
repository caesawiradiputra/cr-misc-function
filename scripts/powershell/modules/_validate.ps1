$base = "c:\Users\203715\Documents\Repo\cr-misc-function\cr-misc-function\scripts\powershell"
$files = @(
    "$base\modules\GitScriptHelpers.psm1",
    "$base\git-clean-branches.ps1",
    "$base\git-reset-branches.ps1",
    "$base\git-check-sync-set-dev.ps1",
    "$base\git-create-clean-branch.ps1",
    "$base\git-rebase-branch.ps1",
    "$base\git-init-feature.ps1",
    "$base\git-workflow.ps1"
)
$allOk = $true
foreach ($f in $files) {
    $errors = $null
    $tokens = $null
    [void][System.Management.Automation.Language.Parser]::ParseFile($f, [ref]$tokens, [ref]$errors)
    $name = Split-Path $f -Leaf
    if ($errors.Count -eq 0) {
        Write-Host "[OK] $name" -ForegroundColor Green
    } else {
        $allOk = $false
        Write-Host "[FAIL] $name" -ForegroundColor Red
        foreach ($e in $errors) { Write-Host "  Line $($e.Extent.StartLineNumber): $($e.Message)" -ForegroundColor Red }
    }
}
if ($allOk) { Write-Host "`nAll 8 files passed syntax validation." -ForegroundColor Green }
