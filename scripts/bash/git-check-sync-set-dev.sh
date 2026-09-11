#!/usr/bin/env bash
# Checks if dev branch has the same code changes as master branch
# (diff-based sync check), and if so, activates local dev.
#
# Bash port of git-check-sync-set-dev.ps1 (PowerShell).
#
# - Fetches refs (unless --no-fetch) and validates existence of remote branches.
# - "In sync" means: no code differences between branches (git diff is empty).
#   Compares actual code changes, not commit history/ancestry.
# - If dev is in sync with master, checks out local dev (creating/tracking it
#   if missing) and fast-forwards it.
#
# NOTE: the scripts/powershell/README.md overview table describes this script
# as ancestor-based with -StrictEqual/-Sit options; the actual
# git-check-sync-set-dev.ps1 source (which this file ports) is diff-based
# against master/dev only, with --force instead. This port follows the real
# .ps1 source, not the stale README description.
#
# Usage:
#   ./scripts/bash/git-check-sync-set-dev.sh [options]
#
# Options:
#   --remote <name>    Git remote name. Default: origin
#   --master <name>    Master branch name. Default: master
#   --dev <name>       Dev branch name. Default: dev
#   --no-fetch         Skip fetching remote refs.
#   --force            Skip the confirmation prompt and proceed directly.
#   -h, --help         Show this help and exit.
#
# Exit codes:
#   0  dev is in sync with master and is now the active local branch.
#   1  error (git missing, not a repo, missing remote branch, git command
#      failure). Original branch is restored first when known.
#   2  dev has code differences from master (not in sync). Original branch
#      is restored first.
#   3  user cancelled the confirmation prompt.
set -uo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=modules/git-script-helpers.sh
source "$script_dir/modules/git-script-helpers.sh"

usage() {
    cat <<'EOF'
Checks if dev branch has the same code changes as master (diff-based), and
if so, activates local dev.

Usage:
  ./scripts/bash/git-check-sync-set-dev.sh [options]

Options:
  --remote <name>    Git remote name. Default: origin
  --master <name>    Master branch name. Default: master
  --dev <name>       Dev branch name. Default: dev
  --no-fetch         Skip fetching remote refs.
  --force            Skip the confirmation prompt and proceed directly.
  -h, --help         Show this help and exit.

Exit codes:
  0  dev is in sync with master and is now the active local branch.
  1  error (git missing, not a repo, missing remote branch, git failure).
  2  dev has code differences from master (not in sync).
  3  user cancelled the confirmation prompt.
EOF
}

remote="origin"
master="master"
dev="dev"
no_fetch=false
force=false

while [ $# -gt 0 ]; do
    case "$1" in
        --remote) remote="$2"; shift 2 ;;
        --master) master="$2"; shift 2 ;;
        --dev) dev="$2"; shift 2 ;;
        --no-fetch) no_fetch=true; shift ;;
        --force) force=true; shift ;;
        -h|--help) usage; exit 0 ;;
        *) echo "Unknown option: $1" >&2; exit 1 ;;
    esac
done

original_branch=""

# fail "message" — restore original branch (if known) and exit 1.
fail() {
    write_error_msg "$1"
    [ -n "$original_branch" ] && git checkout "$original_branch" >/dev/null 2>&1
    exit 1
}

assert_git_available() {
    command -v git >/dev/null 2>&1 || fail "Git is not installed or not available in PATH."
}

assert_in_git_repo() {
    git rev-parse --is-inside-work-tree >/dev/null 2>&1 || fail "Current directory is not a Git repository."
}

test_remote_branch_exists() {
    git show-ref --verify --quiet "refs/remotes/$1/$2"
}

# test_master_in_branch <remote> <master> <branch> — true (exit 0) if the
# branch has no code differences from master.
test_master_in_branch() {
    local diff
    diff="$(git diff "$1/$2" "$1/$3" 2>&1)" || fail "git diff between '$1/$2' and '$1/$3' failed."
    [ -z "$diff" ]
}

ensure_local_branch() {
    local branch="$1" remote_name="$2"
    git show-ref --verify --quiet "refs/heads/$branch" && return 0
    write_info "Creating local branch '$branch' tracking '$remote_name/$branch'"
    git checkout -b "$branch" --track "$remote_name/$branch" >/dev/null 2>&1 \
        || fail "Failed to create local branch '$branch'"
}

checkout_and_ff_only() {
    local branch="$1"
    write_info "Checking out local branch '$branch'"
    git checkout "$branch" >/dev/null 2>&1 || fail "Failed to checkout '$branch'"
    write_info "Fast-forwarding '$branch'"
    git pull --ff-only >/dev/null 2>&1 || fail "Failed to fast-forward '$branch'"
}

display_branch_diffs() {
    local remote_name="$1" master_name="$2" dev_name="$3"
    echo ""
    write_color_line "=== BRANCH DIFF SUMMARY ===" cyan
    echo ""
    write_color_line "$remote_name/$master_name <-> $remote_name/$dev_name" cyan
    git diff "$remote_name/$master_name" "$remote_name/$dev_name" --stat
}

update_local_branches() {
    local remote_name="$1" master_name="$2" dev_name="$3"
    write_info "Updating local protected branches from remote..."

    for branch in "$master_name" "$dev_name"; do
        git show-ref --verify --quiet "refs/heads/$branch" || continue

        local current_branch
        current_branch="$(git rev-parse --abbrev-ref HEAD)"

        if [ "$current_branch" != "$branch" ]; then
            if ! git checkout "$branch" >/dev/null 2>&1; then
                write_warn "Failed to checkout '$branch', skipping pull..."
                continue
            fi
        fi

        write_info "Pulling '$branch' from '$remote_name/$branch'"
        git pull --ff-only "$remote_name" >/dev/null 2>&1 \
            || write_warn "Failed to pull '$branch', but continuing..."
    done
}

# Minimal standalone color helper (this script also needs plain cyan/gray
# section lines that don't fit write_step/write_info's fixed "[TAG] " shape).
write_color_line() {
    local message="$1" color="$2"
    local code=""
    case "$color" in
        cyan) code=$'\033[36m' ;;
        gray) code=$'\033[90m' ;;
    esac
    [ -t 1 ] || code=""
    printf '%s%s%s\n' "$code" "$message" "$([ -t 1 ] && printf '\033[0m')"
}

# ============================================================================
# MAIN LOGIC
# ============================================================================

write_color_line "============================================================" cyan
write_color_line "Check Sync and Set Dev Branch" cyan
write_color_line "============================================================" cyan
echo ""

write_info "Validating environment"
assert_git_available
assert_in_git_repo

original_branch="$(git rev-parse --abbrev-ref HEAD)"

if [ "$no_fetch" = false ]; then
    write_info "Fetching '$remote' (with prune)"
    git fetch "$remote" --prune >/dev/null 2>&1 || fail "git fetch failed"
else
    write_warn "Skipping fetch due to --no-fetch"
fi

for b in "$master" "$dev"; do
    test_remote_branch_exists "$remote" "$b" || fail "Remote branch '$remote/$b' does not exist"
done

write_info "Comparing code changes between branches..."
if test_master_in_branch "$remote" "$master" "$dev"; then
    dev_synced=true
    write_success "'$remote/$dev' has NO code differences from '$remote/$master'"
else
    dev_synced=false
    write_warn "'$remote/$dev' HAS code differences from '$remote/$master'"
fi

if [ "$dev_synced" = true ]; then
    write_success "'$dev' is in sync with '$master' (same code)."

    echo ""
    write_color_line "About to:" cyan
    write_color_line "  1. Update local '$master' and '$dev' from remote" gray
    write_color_line "  2. Create/ensure local '$dev' tracking '$remote/$dev'" gray
    write_color_line "  3. Checkout local '$dev'" gray
    write_color_line "  4. Fast-forward '$dev' with latest changes" gray
    echo ""

    if [ "$force" = false ]; then
        if ! confirm_action "Proceed with syncing and activating '$dev'? (y/n)" "YesNo"; then
            write_warn "Sync cancelled by user"
            exit 3
        fi
    else
        write_info "Skipping confirmation (--force)"
    fi

    update_local_branches "$remote" "$master" "$dev"

    write_info "Activating local '$dev'..."
    ensure_local_branch "$dev" "$remote"
    checkout_and_ff_only "$dev"
    write_success "Active branch is now '$dev'. You can create new branches from here."
    exit 0
else
    display_branch_diffs "$remote" "$master" "$dev"

    write_error_msg "Conditions not met: '$dev' must have no code differences from '$master'. Aborting."
    write_color_line "Suggested next steps:" gray
    write_color_line "  - View differences: git diff $remote/$master $remote/$dev" gray
    write_color_line "  - Sync dev with master: git checkout $dev; git merge $remote/$master" gray

    [ -n "$original_branch" ] && git checkout "$original_branch" >/dev/null 2>&1
    exit 2
fi
