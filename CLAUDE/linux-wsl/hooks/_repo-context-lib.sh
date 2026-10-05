#!/usr/bin/env bash
# Shared helpers for session-start-context.sh and user-prompt-repo-focus.sh.
# Sourced, not invoked directly. Bash port of the original _repo-context-lib.ps1.

get_git_repo_info() {
    local repo_path="$1" branch remote name
    branch=$(git -C "$repo_path" branch --show-current 2>/dev/null)
    remote=$(git -C "$repo_path" config --get remote.origin.url 2>/dev/null)
    name=$(basename "$repo_path")
    printf 'Git repo: %s (%s)\nBranch: %s\nRemote (origin): %s\n' \
        "$name" "$repo_path" \
        "${branch:-(detached or no commits yet)}" \
        "${remote:-(none configured)}"
}

get_uv_project_info() {
    local proj_root="$1" name venv_path lock_path pyvenv_cfg
    name=$(basename "$proj_root")
    venv_path="$proj_root/.venv"
    lock_path="$proj_root/uv.lock"
    pyvenv_cfg="$venv_path/pyvenv.cfg"

    if [ ! -d "$venv_path" ]; then
        echo "uv ($name): pyproject.toml found but .venv is missing -- run 'uv sync' at $proj_root."
    elif [ -f "$lock_path" ] && [ -f "$pyvenv_cfg" ]; then
        if [ "$lock_path" -nt "$pyvenv_cfg" ]; then
            echo "uv ($name): uv.lock is newer than .venv -- 'uv sync' may be needed at $proj_root."
        else
            echo "uv ($name): .venv looks in sync with uv.lock at $proj_root."
        fi
    else
        echo "uv ($name): .venv exists at $proj_root (no uv.lock/pyvenv.cfg to compare timestamps)."
    fi
}

# Prints one sibling git-repo path per line.
get_sibling_repos() {
    local cwd="$1" d
    for d in "$cwd"/*/; do
        [ -d "${d}.git" ] && echo "${d%/}"
    done
}
