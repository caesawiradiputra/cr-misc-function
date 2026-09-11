# SessionStart hook: resolve which git repo(s) and which uv-managed .venv(s)
# apply to the session's starting directory, so this doesn't need to be
# re-discovered by asking or running git/uv commands every session.
#
# In a multi-root workspace opened via a .code-workspace file, the session's
# cwd is pinned to the FIRST folder in `folders[]` for the whole session
# (VS Code doesn't start one session per root) -- so an umbrella root with no
# git repo / pyproject.toml of its own needs a fallback: scan its immediate
# subdirectories for sibling repos/projects instead of reporting nothing.
#
# See also: user-prompt-repo-focus.ps1, which re-reports a specific sibling
# root's status the first time it's @-mentioned in a message this session.

. (Join-Path $PSScriptRoot "_repo-context-lib.ps1")

$cwd = (Get-Location).Path
$lines = @()

# --- Git repo detection: nearest repo at or above cwd ---
$gitTop = $null
try {
    $gitTop = (git rev-parse --show-toplevel 2>$null)
} catch {}

if ($LASTEXITCODE -eq 0 -and $gitTop) {
    $gitTop = ($gitTop.Trim() -replace '/', '\')
    $lines += Get-GitRepoInfo -RepoPath $gitTop
} else {
    # Fallback for a non-git umbrella/workspace root: list sibling repos one
    # level down instead of reporting nothing.
    $siblingRepos = Get-SiblingRepos -Cwd $cwd
    if ($siblingRepos) {
        $lines += "No git repo at '$cwd' itself -- likely a multi-root workspace umbrella. Sibling repos found:"
        foreach ($repo in $siblingRepos) {
            $lines += (Get-GitRepoInfo -RepoPath $repo.FullName) -replace "`n", "`n  "
        }
    } else {
        $lines += "No git repo found at or below '$cwd' -- likely a non-git umbrella/workspace root."
    }
}

# --- uv-managed venv detection: nearest pyproject.toml at or above cwd ---
$searchDir = $cwd
$pyproject = $null
for ($i = 0; $i -lt 8 -and $searchDir; $i++) {
    $candidate = Join-Path $searchDir "pyproject.toml"
    if (Test-Path $candidate) {
        $pyproject = $candidate
        break
    }
    $parent = Split-Path $searchDir -Parent
    if (-not $parent -or $parent -eq $searchDir) { break }
    $searchDir = $parent
}

if ($pyproject) {
    $lines += Get-UvProjectInfo -ProjRoot (Split-Path $pyproject -Parent)
} else {
    # Fallback: scan immediate subdirectories for sibling Python projects.
    $siblingProjects = Get-ChildItem -Path $cwd -Directory -ErrorAction SilentlyContinue |
        Where-Object { Test-Path (Join-Path $_.FullName "pyproject.toml") }
    if ($siblingProjects) {
        $lines += "No pyproject.toml at '$cwd' itself -- sibling uv projects found:"
        foreach ($proj in $siblingProjects) {
            $lines += "  " + (Get-UvProjectInfo -ProjRoot $proj.FullName)
        }
    } else {
        $lines += "uv: no pyproject.toml found at, above, or immediately below '$cwd'."
    }
}

$context = "Session root context (cwd: $cwd):`n" + ($lines -join "`n")

$payload = @{
    hookSpecificOutput = @{
        hookEventName   = "SessionStart"
        additionalContext = $context
    }
}
$payload | ConvertTo-Json -Compress -Depth 5
exit 0
