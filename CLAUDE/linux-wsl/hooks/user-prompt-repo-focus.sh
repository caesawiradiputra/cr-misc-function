#!/usr/bin/env bash
# UserPromptSubmit hook: when a message @-mentions one of cwd's sibling git
# repos (relevant for a multi-root umbrella session, where SessionStart can
# only report "everything available", not which one you'll actually use),
# report that specific repo's fresh git/uv status -- once per repo per
# session, not on every message.
#
# Bash port of user-prompt-repo-focus.ps1.
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_repo-context-lib.sh
source "$SCRIPT_DIR/_repo-context-lib.sh"

raw="$(cat)"
cwd="$(pwd)"
session_id=$(printf '%s' "$raw" | jq -r '.session_id // "unknown"' 2>/dev/null)
[ -z "$session_id" ] && session_id="unknown"

sibling_repos=$(get_sibling_repos "$cwd")
[ -z "$sibling_repos" ] && exit 0

state_dir="${TMPDIR:-/tmp}/claude-repo-focus-hook"
mkdir -p "$state_dir"
state_file="$state_dir/$session_id.json"

reported="[]"
[ -f "$state_file" ] && reported=$(cat "$state_file")

new_lines=()
newly_reported=()
while IFS= read -r repo; do
    [ -z "$repo" ] && continue
    name=$(basename "$repo")
    already=$(printf '%s' "$reported" | jq --arg n "$name" 'index($n) != null' 2>/dev/null)
    [ "$already" = "true" ] && continue
    if printf '%s' "$raw" | grep -qP "@\\Q${name}\\E(?![\\w-])"; then
        new_lines+=("$(get_git_repo_info "$repo")")
        [ -f "$repo/pyproject.toml" ] && new_lines+=("$(get_uv_project_info "$repo")")
        newly_reported+=("$name")
    fi
done <<< "$sibling_repos"

if [ "${#newly_reported[@]}" -gt 0 ]; then
    add_json=$(printf '%s\n' "${newly_reported[@]}" | jq -R . | jq -s .)
    updated=$(printf '%s' "$reported" | jq -c --argjson add "$add_json" '. + $add')
    printf '%s' "$updated" > "$state_file"
fi

[ "${#new_lines[@]}" -eq 0 ] && exit 0

focus_names=$(IFS=,; echo "${newly_reported[*]}")
directive="Active focus root resolved from @-mention: $focus_names. Treat this as the working root for file/code lookups for the rest of the session -- do not re-search sibling roots or the umbrella ($cwd) for files that should be under it unless the user explicitly asks about a different root or the file genuinely isn't found here."

body="$directive
"
for l in "${new_lines[@]}"; do
    body="$body
$l"
done

jq -n --arg ctx "$body" '{hookSpecificOutput: {hookEventName: "UserPromptSubmit", additionalContext: $ctx}}'
exit 0
