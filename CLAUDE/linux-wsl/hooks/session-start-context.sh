#!/usr/bin/env bash
# SessionStart hook: resolve which git repo(s) and which uv-managed .venv(s)
# apply to the session's starting directory, so this doesn't need to be
# re-discovered by asking or running git/uv commands every session.
#
# In a multi-root workspace opened via a .code-workspace file, the session's
# cwd is pinned to the FIRST folder in `folders[]` for the whole session --
# so an umbrella root with no git repo / pyproject.toml of its own needs a
# fallback: scan its immediate subdirectories for sibling repos/projects
# instead of reporting nothing.
#
# Bash port of session-start-context.ps1 (see also user-prompt-repo-focus.sh).
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_repo-context-lib.sh
source "$SCRIPT_DIR/_repo-context-lib.sh"

cwd="$(pwd)"
lines=()

git_top=$(git rev-parse --show-toplevel 2>/dev/null || true)
if [ -n "$git_top" ]; then
    lines+=("$(get_git_repo_info "$git_top")")
else
    sibling_repos=$(get_sibling_repos "$cwd")
    if [ -n "$sibling_repos" ]; then
        lines+=("No git repo at '$cwd' itself -- likely a multi-root workspace umbrella. Sibling repos found:")
        while IFS= read -r repo; do
            info=$(get_git_repo_info "$repo")
            lines+=("  ${info//$'\n'/$'\n'  }")
        done <<< "$sibling_repos"
    else
        lines+=("No git repo found at or below '$cwd' -- likely a non-git umbrella/workspace root.")
    fi
fi

# --- uv-managed venv detection: nearest pyproject.toml at or above cwd ---
search_dir="$cwd"
pyproject=""
for _ in 1 2 3 4 5 6 7 8; do
    if [ -f "$search_dir/pyproject.toml" ]; then
        pyproject="$search_dir/pyproject.toml"
        break
    fi
    parent=$(dirname "$search_dir")
    [ "$parent" = "$search_dir" ] && break
    search_dir="$parent"
done

if [ -n "$pyproject" ]; then
    lines+=("$(get_uv_project_info "$(dirname "$pyproject")")")
else
    sibling_found=0
    for d in "$cwd"/*/; do
        [ -f "${d}pyproject.toml" ] || continue
        if [ "$sibling_found" -eq 0 ]; then
            lines+=("No pyproject.toml at '$cwd' itself -- sibling uv projects found:")
            sibling_found=1
        fi
        lines+=("  $(get_uv_project_info "${d%/}")")
    done
    if [ "$sibling_found" -eq 0 ]; then
        lines+=("uv: no pyproject.toml found at, above, or immediately below '$cwd'.")
    fi
fi

context="Session root context (cwd: $cwd):
$(printf '%s\n' "${lines[@]}")"

jq -n --arg ctx "$context" '{hookSpecificOutput: {hookEventName: "SessionStart", additionalContext: $ctx}}'
exit 0
