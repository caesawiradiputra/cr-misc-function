#!/usr/bin/env bash
# Rebase a feature branch onto a base branch and prepare for a clean merge.
#
# Bash port of git-rebase-branch.ps1 (PowerShell). Guides you through
# rebasing a feature branch onto a base branch (default: master), creating a
# clean commit history. Creates a timestamped backup branch before rebasing
# and offers to delete it once you've confirmed the result.
#
# Usage:
#   ./scripts/bash/git-rebase-branch.sh [feature-branch] [base-branch] [options]
#
# Positional args:
#   feature-branch   Branch to rebase. Default: current branch.
#   base-branch      Branch to rebase onto. Default: master.
#
# Options:
#   --skip-fetch     Skip fetching from origin (use existing remote refs).
#   -h, --help       Show this help and exit.
#
# Examples:
#   ./scripts/bash/git-rebase-branch.sh feature/foo
#   ./scripts/bash/git-rebase-branch.sh fix/DA-1234 dev
#   ./scripts/bash/git-rebase-branch.sh
set -uo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=modules/git-script-helpers.sh
source "$script_dir/modules/git-script-helpers.sh"

usage() {
    cat <<'EOF'
Rebase a feature branch onto a base branch and prepare for a clean merge.

Usage:
  ./scripts/bash/git-rebase-branch.sh [feature-branch] [base-branch] [options]

Positional args:
  feature-branch   Branch to rebase. Default: current branch.
  base-branch      Branch to rebase onto. Default: master.

Options:
  --skip-fetch     Skip fetching from origin (use existing remote refs).
  -h, --help       Show this help and exit.

Examples:
  ./scripts/bash/git-rebase-branch.sh feature/foo
  ./scripts/bash/git-rebase-branch.sh fix/DA-1234 dev
  ./scripts/bash/git-rebase-branch.sh
EOF
}

feature_branch=""
base_branch="master"
skip_fetch=false
positional=()

while [ $# -gt 0 ]; do
    case "$1" in
        --skip-fetch) skip_fetch=true; shift ;;
        -h|--help) usage; exit 0 ;;
        *) positional+=("$1"); shift ;;
    esac
done
[ "${#positional[@]}" -ge 1 ] && feature_branch="${positional[0]}"
[ "${#positional[@]}" -ge 2 ] && base_branch="${positional[1]}"

CYAN=$'\033[36m'; GREEN=$'\033[32m'; YELLOW=$'\033[33m'; RED=$'\033[31m'; RESET=$'\033[0m'
[ -t 1 ] || { CYAN=""; GREEN=""; YELLOW=""; RED=""; RESET=""; }
color() { printf '%b%b%b\n' "$2" "$1" "$RESET"; }

backup_branch_name=""

# Runs on any exit (success, error, or Ctrl+C) — mirrors the PowerShell
# `finally` block that detects a rebase left mid-flight.
on_exit() {
    local git_dir
    git_dir="$(git rev-parse --git-dir 2>/dev/null)" || return 0
    if [ -d "$git_dir/rebase-merge" ] || [ -d "$git_dir/rebase-apply" ]; then
        color "\n[WARNING] A rebase is still in progress." "$RED"
        color "  To continue:  fix conflicts, git add <files>, then git rebase --continue" "$YELLOW"
        color "  To abort:     git rebase --abort" "$YELLOW"
        if [ -n "$backup_branch_name" ]; then
            color "  To hard-reset: git reset --hard $backup_branch_name" "$YELLOW"
        fi
    fi
}
trap on_exit EXIT

fail() {
    printf '\n'
    write_error_msg "Script failed: $1"
    exit 1
}

test_git_repository() { git rev-parse --git-dir >/dev/null 2>&1; }
get_current_branch() { git branch --show-current 2>/dev/null || fail "Failed to get current branch"; }
test_branch_exists() { git rev-parse --verify "$1" >/dev/null 2>&1; }
test_remote_branch_exists() { git ls-remote --heads origin "$1" >/dev/null 2>&1 && [ -n "$(git ls-remote --heads origin "$1")" ]; }
has_uncommitted_changes() { [ -n "$(git status --porcelain 2>/dev/null)" ]; }

# git-rebase-branch.ps1's two prompts are bespoke inline loops (NOT the
# shared module's Confirm-Action): 'y'/'n' or empty defaults to 'n'
# (decline) immediately, rather than re-prompting on empty like
# confirm_action's YesNo style does. Ported as its own helper to preserve
# that exact, slightly different behavior.
confirm_yn_default_no() {
    local prompt="$1" answer
    while true; do
        read -r -p "$prompt " answer
        answer="$(printf '%s' "$answer" | tr '[:upper:]' '[:lower:]' | xargs)"
        [ -z "$answer" ] && answer="n"
        case "$answer" in
            y) return 0 ;;
            n) return 1 ;;
            *) write_warn "Invalid input: '$answer'. Please enter 'y' or 'n'." ;;
        esac
    done
}

# ============================================================================
# MAIN LOGIC
# ============================================================================

printf '\n'
color "============================================================" "$CYAN"
color "Git Rebase Branch - Clean Merge Helper" "$CYAN"
color "============================================================" "$CYAN"

write_step "Verifying git repository" "[CHECK]"
test_git_repository || fail "Not a git repository. Please run this script from within a git repository."
write_success "Git repository verified"

if [ -z "$feature_branch" ]; then
    feature_branch="$(get_current_branch)"
    write_info "Using current branch: $feature_branch"
fi

if [ "$feature_branch" = "$base_branch" ]; then
    write_error_msg "Feature branch '$feature_branch' is the same as base branch '$base_branch'. Nothing to rebase."
    exit 1
fi

write_step "Checking for uncommitted changes" "[FILES]"
if has_uncommitted_changes; then
    write_error_msg "You have uncommitted changes. Please commit or stash them first."
    printf '\nRun one of these commands:\n'
    color "  git add . && git commit -m 'Your message'" "$YELLOW"
    color "  git stash" "$YELLOW"
    exit 1
fi
write_success "Working directory is clean"

if [ "$skip_fetch" = false ]; then
    write_step "Fetching latest changes from origin" "[FETCH]"
    git fetch origin --prune >/dev/null 2>&1 || fail "Failed to fetch from origin"
    write_success "Fetched latest changes"
else
    write_info "Skipping fetch (using existing remote refs)"
fi

write_step "Verifying branches" "[CHECK]"
test_remote_branch_exists "$base_branch" || fail "Base branch 'origin/$base_branch' does not exist"
write_success "Base branch 'origin/$base_branch' exists"
test_branch_exists "$feature_branch" || fail "Feature branch '$feature_branch' does not exist locally"
write_success "Feature branch '$feature_branch' exists"

current_branch="$(get_current_branch)"
if [ "$current_branch" != "$feature_branch" ]; then
    write_step "Checking out feature branch: $feature_branch" "[SWITCH]"
    git checkout "$feature_branch" >/dev/null 2>&1 || fail "Failed to checkout branch '$feature_branch'"
    write_success "Checked out '$feature_branch'"
else
    write_info "Already on branch '$feature_branch'"
fi

write_step "Commits to be rebased" "[COMMITS]"
commit_count="$(git rev-list --count "origin/$base_branch..$feature_branch")"

if [ "$commit_count" -eq 0 ]; then
    write_info "No commits to rebase. $feature_branch is up to date with origin/$base_branch"
    exit 0
fi

printf '\n'
color "$commit_count commit(s) from $feature_branch will be replayed onto origin/$base_branch :" "$CYAN"
printf '\n'
color "Commit Hash | Author | Message" "$YELLOW"
color "-------------------------------------------------------------" "$YELLOW"
git log --reverse --oneline --pretty=format:"%C(yellow)%h%C(reset) | %C(cyan)%an%C(reset) | %s" "origin/$base_branch..$feature_branch"
printf '\n\n'

color "This will:" "$YELLOW"
color "  1. Replay your feature commits on top of origin/$base_branch" "$YELLOW"
color "  2. Drop any commits that came from other branches" "$YELLOW"
color "  3. May cause conflicts that you'll need to resolve" "$YELLOW"
printf '\n'

if ! confirm_yn_default_no "Continue with rebase? (y/N)"; then
    write_info "Rebase cancelled by user"
    exit 0
fi

write_step "Creating safety backup branch" "[BACKUP]"
backup_branch_name="backup/$feature_branch-$(date +%Y%m%d-%H%M%S)"
git branch "$backup_branch_name" >/dev/null 2>&1 || fail "Failed to create backup branch '$backup_branch_name'"
write_success "Backup created: $backup_branch_name"
write_info "If rebase fails, restore with: git reset --hard $backup_branch_name"

write_step "Rebasing $feature_branch onto origin/$base_branch" "[REBASE]"
rebase_output="$(git rebase "origin/$base_branch" 2>&1)"
rebase_status=$?

if [ "$rebase_status" -ne 0 ]; then
    write_error_msg "Rebase encountered conflicts!"
    echo "$rebase_output" | while IFS= read -r line; do color "  $line" "$RED"; done
    printf '\n[HELP] To resolve conflicts:\n'
    color "  1. Fix conflicts in the listed files" "$YELLOW"
    color "  2. Run: git add <resolved-files>" "$YELLOW"
    color "  3. Run: git rebase --continue" "$YELLOW"

    color "\n[INFO] Understanding Current vs Incoming:" "$CYAN"
    echo "  Current  = $base_branch (base branch being rebased onto)"
    echo "  Incoming = $feature_branch (your feature commits being replayed)"
    color "  Tip: Usually keep 'Incoming' to preserve your feature changes" "$YELLOW"

    color "\n[WARNING] To abort rebase: git rebase --abort" "$RED"
    exit 1
fi

write_success "Rebase completed successfully!"

write_step "Verifying rebased commits" "[VERIFY]"
rebased_count="$(git rev-list --count "origin/$base_branch..HEAD")"

printf '\n'
color "$rebased_count commit(s) ready to merge into $base_branch :" "$GREEN"
printf '\n'
color "Commit Hash | Author | Message" "$YELLOW"
color "-------------------------------------------------------------" "$YELLOW"
git log --pretty=format:"%C(yellow)%h%C(reset) | %C(cyan)%an%C(reset) | %s" "origin/$base_branch..HEAD"
printf '\n\n'
write_success "Only your feature commits are present ($rebased_count commit(s))"

printf '\n'
if confirm_yn_default_no "Rebase verified. Delete backup branch '$backup_branch_name'? (y/N)"; then
    git branch -D "$backup_branch_name" >/dev/null 2>&1
    write_success "Backup branch deleted"
else
    write_info "Backup retained. Clean up later with: git branch -D $backup_branch_name"
fi

printf '\n'
color "============================================================" "$GREEN"
color "[SUCCESS] Rebase Complete - Next Steps" "$GREEN"
color "============================================================" "$GREEN"
printf '\n'
color "Your backup branch is: $backup_branch_name" "$CYAN"
printf '\n'
color "Option A: Direct merge to $base_branch" "$CYAN"
echo "  git checkout $base_branch"
echo "  git merge $feature_branch"
echo "  git push origin $base_branch"
printf '\n'
color "Option B: Create Pull Request (Recommended)" "$CYAN"
echo "  git push --force-with-lease origin $feature_branch"
echo "  Then create PR on GitHub/GitLab with Squash and Merge"
printf '\n'
color "[NOTE] Use --force-with-lease to update remote branch after rebase" "$YELLOW"
printf '\n'
