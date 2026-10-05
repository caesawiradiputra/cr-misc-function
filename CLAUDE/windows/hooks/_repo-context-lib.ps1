# Shared helpers for the session-start-context.ps1 and user-prompt-repo-focus.ps1
# hooks. Dot-sourced, not invoked directly.

function Get-GitRepoInfo {
    param([string]$RepoPath)
    $branch = (git -C $RepoPath branch --show-current 2>$null)
    $branch = if ($branch) { $branch.Trim() } else { $null }
    $remote = (git -C $RepoPath config --get remote.origin.url 2>$null)
    $remote = if ($remote) { $remote.Trim() } else { $null }
    $name = Split-Path -Leaf $RepoPath
    "Git repo: $name ($RepoPath)`nBranch: $(if ($branch) { $branch } else { '(detached or no commits yet)' })`nRemote (origin): $(if ($remote) { $remote } else { '(none configured)' })"
}

function Get-UvProjectInfo {
    param([string]$ProjRoot)
    $venvPath = Join-Path $ProjRoot ".venv"
    $lockPath = Join-Path $ProjRoot "uv.lock"
    $pyvenvCfg = Join-Path $venvPath "pyvenv.cfg"
    $name = Split-Path -Leaf $ProjRoot

    if (-not (Test-Path $venvPath)) {
        return "uv ($name): pyproject.toml found but .venv is missing -- run 'uv sync' at $ProjRoot."
    } elseif ((Test-Path $lockPath) -and (Test-Path $pyvenvCfg)) {
        $lockTime = (Get-Item $lockPath).LastWriteTimeUtc
        $venvTime = (Get-Item $pyvenvCfg).LastWriteTimeUtc
        if ($lockTime -gt $venvTime) {
            return "uv ($name): uv.lock is newer than .venv -- 'uv sync' may be needed at $ProjRoot."
        } else {
            return "uv ($name): .venv looks in sync with uv.lock at $ProjRoot."
        }
    } else {
        return "uv ($name): .venv exists at $ProjRoot (no uv.lock/pyvenv.cfg to compare timestamps)."
    }
}

function Get-SiblingRepos {
    param([string]$Cwd)
    Get-ChildItem -Path $Cwd -Directory -ErrorAction SilentlyContinue |
        Where-Object { Test-Path (Join-Path $_.FullName ".git") }
}
