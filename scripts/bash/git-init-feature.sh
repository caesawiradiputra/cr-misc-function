#!/usr/bin/env bash
# Initialize a new feature branch from a base branch (default: dev).
#
# Bash port of git-init-feature.ps1 (PowerShell). Creates a new feature
# branch following the naming convention fea/<TICKET>-<description>.
# Validates the working tree is clean, fetches latest from origin, and
# optionally verifies dev is synced with master before creating the branch.
#
# Workflow position: runs after git-check-sync-set-dev.sh and before
# development work.
set -uo pipefail

usage() {
    cat <<'EOF'
Initialize a new feature branch from a base branch (default: dev).

Usage:
  ./scripts/bash/git-init-feature.sh [branch-name] [base-branch] [options]

Positional:
  branch-name        Full branch name (e.g. fea/DA-1234-add-caching).
                      If omitted, prompts interactively.
  base-branch        Base branch to create from. Default: dev.

Options:
  --skip-fetch        Skip fetching from origin. Useful if you just fetched.
  --skip-sync-check   Skip checking if dev is in sync with master.
  --force             Skip confirmation prompts.
  -h, --help          Show this help and exit.

Examples:
  ./scripts/bash/git-init-feature.sh "fea/DA-1234-add-caching"
  ./scripts/bash/git-init-feature.sh
  ./scripts/bash/git-init-feature.sh "" master --skip-sync-check

Naming convention: fea/<TICKET>-<description> (e.g. fea/DA-1234-add-caching)
EOF
}

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/modules/git-script-helpers.sh"

branch_name=""
base_branch="dev"
skip_fetch=false
skip_sync_check=false
force=false
positional=()

while [ $# -gt 0 ]; do
    case "$1" in
        --skip-fetch) skip_fetch=true; shift ;;
        --skip-sync-check) skip_sync_check=true; shift ;;
        --force) force=true; shift ;;
        -h|--help) usage; exit 0 ;;
        --) shift; while [ $# -gt 0 ]; do positional+=("$1"); shift; done ;;
        -*) echo "Unknown option: $1" >&2; exit 1 ;;
        *) positional+=("$1"); shift ;;
    esac
done

[ "${#positional[@]}" -ge 1 ] && branch_name="${positional[0]}"
[ "${#positional[@]}" -ge 2 ] && base_branch="${positional[1]}"

CYAN=$'\033[36m'; GREEN=$'\033[32m'; YELLOW=$'\033[33m'; WHITE=$'\033[37m'; GRAY=$'\033[90m'; RED=$'\033[31m'; RESET=$'\033[0m'
[ -t 1 ] || { CYAN=""; GREEN=""; YELLOW=""; WHITE=""; GRAY=""; RED=""; RESET=""; }
color_line() { printf '%b%b%b\n' "$2" "$1" "$RESET"; }

echo ""
color_line "=============================================================" "$CYAN"
color_line "Initialize Feature Branch" "$CYAN"
color_line "=============================================================" "$CYAN"
echo ""

# Step 1: Validate git repository
write_step "Verifying git repository" "[CHECK]"
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    write_error_msg "Not inside a Git repository. Please run from within a Git working directory."
    exit 1
fi
write_success "Git repository verified"

# Step 2: Check for uncommitted changes
write_step "Checking working directory" "[CHECK]"
dirty_files="$(git status --porcelain 2>&1)"
if [ -n "$dirty_files" ]; then
    write_error_msg "Working directory has uncommitted changes. Please commit or stash first."
    echo "$dirty_files" | while IFS= read -r line; do color_line "  $line" "$RED"; done
    exit 1
fi
write_success "Working directory is clean"

# Step 3: Fetch latest from origin
if [ "$skip_fetch" = false ]; then
    write_step "Fetching latest changes" "[FETCH]"
    if ! git fetch origin --prune >/dev/null 2>&1; then
        write_error_msg "Failed to fetch from origin"
        exit 1
    fi
    write_success "Fetched latest from origin"
else
    write_info "Skipped fetch (--skip-fetch specified)"
fi

# Step 4: Verify base branch exists
write_step "Verifying base branch" "[CHECK]"
if ! git rev-parse --verify "origin/$base_branch" >/dev/null 2>&1; then
    write_error_msg "Remote branch 'origin/$base_branch' does not exist"
    exit 1
fi
write_success "Base branch 'origin/$base_branch' verified"

# Step 5: Optional sync check (dev vs master)
if [ "$skip_sync_check" = false ] && [ "$base_branch" = "dev" ]; then
    write_step "Checking dev-master sync" "[SYNC]"
    diff_output="$(git diff origin/master origin/dev 2>&1)"
    if [ -n "$diff_output" ]; then
        write_warn "origin/dev has code differences from origin/master"
        color_line "  Run git-check-sync-set-dev.sh first to sync dev with master" "$YELLOW"
        echo ""
        if ! confirm_action "Continue anyway? (y/n)" "YesNo"; then
            write_info "Aborted. Run git-check-sync-set-dev.sh to sync first."
            exit 1
        fi
    else
        write_success "origin/dev is in sync with origin/master"
    fi
fi

# Step 6: Get branch name (prompt if not provided)
if [ -z "$branch_name" ]; then
    write_step "Branch name" "[INPUT]"
    color_line "Naming convention: fea/<TICKET>-<description>" "$YELLOW"
    color_line "Example: fea/DA-1234-add-caching" "$YELLOW"
    echo ""

    while true; do
        read -r -p "Enter branch name: " branch_name
        branch_name="$(printf '%s' "$branch_name" | xargs)"

        if [ -z "$branch_name" ]; then
            write_warn "Branch name cannot be empty. Please enter a name."
            continue
        fi

        # Validate naming convention (warn but don't block)
        if [[ ! "$branch_name" =~ ^(fea|fix|hotfix|chore|refactor)/[A-Z]+-[0-9]+ ]]; then
            write_warn "Branch name doesn't follow convention: fea/<TICKET>-<description>"
            if ! confirm_action "Use this name anyway? (y/n)" "YesNo"; then
                branch_name=""
                continue
            fi
        fi
        break
    done
fi

# Step 7: Check branch doesn't already exist
write_step "Validating branch name" "[CHECK]"

if git rev-parse --verify "$branch_name" >/dev/null 2>&1; then
    write_error_msg "Branch '$branch_name' already exists locally"
    exit 1
fi

remote_exists="$(git ls-remote --heads origin "$branch_name" 2>&1)"
if [ -n "$remote_exists" ]; then
    write_error_msg "Branch '$branch_name' already exists on remote"
    exit 1
fi
write_success "Branch name '$branch_name' is available"

# Step 8: Confirm and create
echo ""
color_line "This will:" "$YELLOW"
color_line "  - Create branch '$branch_name' from origin/$base_branch" "$YELLOW"
color_line "  - Check out the new branch" "$YELLOW"
color_line "  - Push to origin with tracking" "$YELLOW"
echo ""

if [ "$force" = false ]; then
    if ! confirm_action "Create feature branch? (y/n)" "YesNo"; then
        write_info "Operation cancelled"
        exit 0
    fi
fi

# Step 9: Create branch
write_step "Creating branch" "[CREATE]"
original_branch="$(git rev-parse --abbrev-ref HEAD 2>&1)"

if ! git checkout -b "$branch_name" "origin/$base_branch" >/dev/null 2>&1; then
    write_error_msg "Failed to create branch '$branch_name'"
    exit 1
fi
write_success "Created and checked out branch: $branch_name"

# Step 10: Push to remote
write_step "Pushing to remote" "[PUSH]"
if ! git push -u origin "$branch_name" >/dev/null 2>&1; then
    write_warn "Failed to push to remote. You can push manually later:"
    color_line "  git push -u origin $branch_name" "$CYAN"
else
    write_success "Branch pushed to origin with tracking"
fi

# Summary
echo ""
color_line "=============================================================" "$GREEN"
color_line "[SUCCESS] Feature branch ready" "$GREEN"
color_line "=============================================================" "$GREEN"
echo ""
color_line "  Branch: $branch_name" "$WHITE"
color_line "  Base:   origin/$base_branch" "$WHITE"
color_line "  Previous branch: $original_branch" "$GRAY"
echo ""
color_line "Start working on your feature. When ready:" "$CYAN"
color_line "  - Commit changes: /commit" "$WHITE"
color_line "  - Rebase onto base: ./git-rebase-branch.sh" "$WHITE"
color_line "  - Create PR on GitHub/GitLab" "$WHITE"
