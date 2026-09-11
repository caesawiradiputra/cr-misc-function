#!/usr/bin/env bash
# Scans all non-protected remote branches and reports which are safe to
# delete (already fully merged into a base branch).
#
# Bash port of git-check-branch-merged.ps1 (PowerShell).
#
# For every branch on the remote (excluding the base branch and protected
# branches), determines whether it is already fully merged into the base
# branch (default: dev).
#
# The comparison is diff-based (code content), not commit-history-based. A
# commit-ancestry check (e.g. rev-list ahead/behind) does not work here
# because merges to the base branch are typically done via squash merge - a
# feature branch's individual commits are never reachable from the base, so
# it would always look "ahead" even when fully merged.
#
# A plain full-tree `git diff origin/<base> origin/<branch>` isn't reliable
# either: once OTHER feature branches are squash-merged into the base
# afterward, the base moves ahead with unrelated changes, and a full-tree
# diff would flag an old (already-merged) branch as "different" for that
# reason alone. To avoid that false positive, the check is scoped to only
# the files each branch itself touched since it diverged from the base
# (`git diff <merge-base> origin/<branch>` for the file list, then `git diff
# origin/<base> origin/<branch> -- <those files>`). If that scoped diff is
# empty, the base's current version of every file the branch touched
# already matches the branch, regardless of what else has landed on the
# base since.
#
# This script only REPORTS - it never deletes, checks out, or otherwise
# mutates anything. Only remote-tracking refs are read; local branch/
# working-tree state is not touched.
#
# Intended workflow:
#   1. Run this script to see which remote branches are safe to delete.
#   2. Delete those branches yourself (e.g. on GitHub's web UI).
#   3. Run git-clean-branches.sh to prune local branches whose remote was
#      deleted.
#
# Exit codes:
#   0 - Scan completed (see output for per-branch results; nothing deleted)
#   1 - Error (not a repo, fetch failed, missing base branch, git failure)
set -uo pipefail

usage() {
    cat <<'EOF'
Scan remote branches and report which are safe to delete (already fully
merged into a base branch, by content diff — not commit ancestry).

Usage:
  ./scripts/bash/git-check-branch-merged.sh [options]

Options:
  --base-branch <name>        Base branch to compare against. Default: dev.
  --remote <name>              Git remote name. Default: origin.
  --no-fetch                    Skip fetching remote refs before comparing.
  --protected-branches <csv>   Comma-separated branches excluded from the
                               scan. Default: main,master,dev,sit.
  -h, --help                    Show this help and exit.

Examples:
  ./scripts/bash/git-check-branch-merged.sh
  ./scripts/bash/git-check-branch-merged.sh --base-branch master --no-fetch
EOF
}

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/modules/git-script-helpers.sh"

base_branch="dev"
remote="origin"
no_fetch=false
protected_branches_csv="main,master,dev,sit"

while [ $# -gt 0 ]; do
    case "$1" in
        --base-branch) base_branch="$2"; shift 2 ;;
        --remote) remote="$2"; shift 2 ;;
        --no-fetch) no_fetch=true; shift ;;
        --protected-branches) protected_branches_csv="$2"; shift 2 ;;
        -h|--help) usage; exit 0 ;;
        *) echo "Unknown option: $1" >&2; exit 1 ;;
    esac
done

IFS=',' read -r -a protected_branches <<< "$protected_branches_csv"

CYAN=$'\033[36m'; GREEN=$'\033[32m'; YELLOW=$'\033[33m'; DARKYELLOW=$'\033[33m'; RED=$'\033[31m'; DARKRED=$'\033[31m'; WHITE=$'\033[37m'; RESET=$'\033[0m'
[ -t 1 ] || { CYAN=""; GREEN=""; YELLOW=""; DARKYELLOW=""; RED=""; DARKRED=""; WHITE=""; RESET=""; }
color() { printf '%b%b%b' "$2" "$1" "$RESET"; }
color_line() { printf '%b%b%b\n' "$2" "$1" "$RESET"; }

is_protected() {
    local branch="$1" p
    for p in "${protected_branches[@]}"; do
        [ "$branch" = "$p" ] && return 0
    done
    return 1
}

assert_git_available() {
    command -v git >/dev/null 2>&1 || { write_error_msg "Git is not installed or not available in PATH."; exit 1; }
}

assert_in_git_repo() {
    git rev-parse --is-inside-work-tree >/dev/null 2>&1 || { write_error_msg "Current directory is not a Git repository."; exit 1; }
}

test_remote_ref_exists() {
    git show-ref --verify --quiet "refs/remotes/$1/$2"
}

test_local_ref_exists() {
    git show-ref --verify --quiet "refs/heads/$1"
}

# test_branch_merged_into_base <remote> <base-branch> <branch>
# Prints "<status>|<detail>" on stdout. status is Safe|HasChanges|Error.
test_branch_merged_into_base() {
    local remote="$1" base_branch="$2" branch="$3"
    local merge_base diff_output touched_count
    local -a touched_files_arr

    merge_base="$(git merge-base "$remote/$base_branch" "$remote/$branch" 2>/dev/null)"
    if [ -z "$merge_base" ]; then
        echo "Error|No common ancestor with base branch"
        return
    fi

    if ! mapfile -t touched_files_arr < <(git diff --name-only "$merge_base" "$remote/$branch" 2>/dev/null); then
        echo "Error|git diff --name-only failed"
        return
    fi

    if [ "${#touched_files_arr[@]}" -eq 0 ]; then
        echo "Safe|No file changes since diverging from base"
        return
    fi
    touched_count="${#touched_files_arr[@]}"

    diff_output="$(git diff "$remote/$base_branch" "$remote/$branch" -- "${touched_files_arr[@]}" 2>/dev/null)"
    if [ $? -ne 0 ]; then
        echo "Error|git diff failed"
        return
    fi

    if [ -n "$diff_output" ]; then
        echo "HasChanges|${touched_count} file(s) touched; differs from base on at least one"
        return
    fi

    echo "Safe|${touched_count} file(s) touched; base already matches"
}

echo ""
color_line "=============================================================" "$CYAN"
color_line "Scan Branches - Safe to Delete Report" "$CYAN"
color_line "=============================================================" "$CYAN"
echo ""

# Step 1: Validate environment
write_step "Validating environment" "[CHECK]"
assert_git_available
assert_in_git_repo
write_success "Git repository verified"

# Step 2: Fetch latest remote refs
if [ "$no_fetch" = false ]; then
    write_step "Fetching latest changes" "[FETCH]"
    if ! git fetch "$remote" --prune >/dev/null 2>&1; then
        write_error_msg "Failed to fetch from '$remote'"
        exit 1
    fi
    write_success "Fetched latest from '$remote'"
else
    write_info "Skipped fetch (--no-fetch specified)"
fi

# Step 3: Verify base branch exists on remote
write_step "Verifying base branch" "[CHECK]"
if ! test_remote_ref_exists "$remote" "$base_branch"; then
    write_error_msg "Remote branch '$remote/$base_branch' does not exist"
    exit 1
fi
write_success "'$remote/$base_branch' verified"

# Step 4: Enumerate candidate remote branches (exclude base + protected)
write_step "Enumerating remote branches" "[SCAN]"
mapfile -t remote_branches < <(
    git branch -r --format='%(refname:short)' 2>/dev/null \
        | sed "s#^$remote/##" \
        | while IFS= read -r b; do
            b="$(printf '%s' "$b" | xargs)"
            [ "$b" = "HEAD" ] && continue
            [ "$b" = "$remote" ] && continue
            [ "$b" = "$base_branch" ] && continue
            is_protected "$b" && continue
            echo "$b"
          done
)

if [ "${#remote_branches[@]}" -eq 0 ]; then
    write_info "No candidate branches to scan (everything is protected or the base branch)"
    exit 0
fi
write_success "Found ${#remote_branches[@]} candidate branch(es) to scan"
echo ""

# Step 5: Compare each candidate against the base branch
safe=()
has_changes=()
errored=()

for branch in "${remote_branches[@]}"; do
    result="$(test_branch_merged_into_base "$remote" "$base_branch" "$branch")"
    status="${result%%|*}"
    detail="${result#*|}"

    local_note=""
    test_local_ref_exists "$branch" && local_note=" [local copy exists]"

    case "$status" in
        Safe)
            color "  [SAFE]        " "$GREEN"
            color_line "$branch$local_note" "$WHITE"
            safe+=("$branch")
            ;;
        HasChanges)
            color "  [HAS CHANGES] " "$YELLOW"
            color "$branch$local_note " "$WHITE"
            color_line "($detail)" "$DARKYELLOW"
            has_changes+=("$branch")
            ;;
        Error)
            color "  [ERROR]       " "$RED"
            color "$branch$local_note " "$WHITE"
            color_line "($detail)" "$DARKRED"
            errored+=("$branch")
            ;;
    esac
done

# ============================================================================
# SUMMARY
# ============================================================================
echo ""
color_line "=============================================================" "$CYAN"
color_line "Summary" "$CYAN"
color_line "=============================================================" "$CYAN"
color_line "  Safe to delete: ${#safe[@]}" "$GREEN"
color_line "  Has changes:    ${#has_changes[@]}" "$YELLOW"
color_line "  Errors:         ${#errored[@]}" "$RED"
echo ""

if [ "${#safe[@]}" -gt 0 ]; then
    color_line "Safe to delete (no code differences from '$base_branch'):" "$GREEN"
    for b in "${safe[@]}"; do color_line "  - $b" "$GREEN"; done
    echo ""
    write_info "Nothing was deleted. Delete these on GitHub, then run git-clean-branches.sh to prune local copies."
else
    write_info "No branches are currently safe to delete."
fi

exit 0
