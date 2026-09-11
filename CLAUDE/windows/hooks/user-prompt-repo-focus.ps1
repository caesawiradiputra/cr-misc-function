# UserPromptSubmit hook: when a message @-mentions one of cwd's sibling git
# repos (relevant for a multi-root umbrella session, where SessionStart can
# only report "everything available", not which one you'll actually use),
# report that specific repo's fresh git/uv status -- once per repo per
# session, not on every message.

. (Join-Path $PSScriptRoot "_repo-context-lib.ps1")

$raw = [Console]::In.ReadToEnd()
$cwd = (Get-Location).Path

$sessionId = "unknown"
try {
    $parsed = $raw | ConvertFrom-Json -ErrorAction Stop
    if ($parsed.session_id) { $sessionId = $parsed.session_id }
} catch {}

$siblingRepos = Get-SiblingRepos -Cwd $cwd
if (-not $siblingRepos) {
    exit 0
}

$stateDir = Join-Path $env:TEMP "claude-repo-focus-hook"
if (-not (Test-Path $stateDir)) {
    New-Item -ItemType Directory -Path $stateDir -Force | Out-Null
}
$stateFile = Join-Path $stateDir "$sessionId.json"

$reported = @()
if (Test-Path $stateFile) {
    try {
        $reported = @(Get-Content $stateFile -Raw | ConvertFrom-Json -ErrorAction Stop)
    } catch { $reported = @() }
}

$newLines = @()
$newlyReported = @()
foreach ($repo in $siblingRepos) {
    $name = $repo.Name
    if ($reported -contains $name) { continue }

    $pattern = "@" + [regex]::Escape($name) + '(?![\w-])'
    if ($raw -notmatch $pattern) { continue }

    $newLines += Get-GitRepoInfo -RepoPath $repo.FullName
    $pyproject = Join-Path $repo.FullName "pyproject.toml"
    if (Test-Path $pyproject) {
        $newLines += Get-UvProjectInfo -ProjRoot $repo.FullName
    }
    $newlyReported += $name
}

if ($newlyReported.Count -gt 0) {
    $reported = @($reported) + $newlyReported
    ($reported | ConvertTo-Json -Compress) | Set-Content -Path $stateFile -Encoding utf8
}

if ($newLines.Count -eq 0) {
    exit 0
}

$focusNames = $newlyReported -join ", "
$directive = "Active focus root resolved from @-mention: $focusNames. " +
    "Treat this as the working root for file/code lookups for the rest of the session -- " +
    "do not re-search sibling roots or the umbrella ($cwd) for files that should be under it " +
    "unless the user explicitly asks about a different root or the file genuinely isn't found here."
$context = "$directive`n`n" + ($newLines -join "`n")
$payload = @{
    hookSpecificOutput = @{
        hookEventName      = "UserPromptSubmit"
        additionalContext  = $context
    }
}
$payload | ConvertTo-Json -Compress -Depth 5
exit 0
