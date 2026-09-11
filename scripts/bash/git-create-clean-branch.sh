#!/usr/bin/env bash
# Creates a clean branch by cherry-picking commits filtered by file paths.
#
# Bash port of git-create-clean-branch.ps1 (PowerShell). Shows commits from
# the feature branch that affected specific files or directories, then asks
# for confirmation. If confirmed, creates a new branch (with -clean suffix)
# from the base branch and cherry-picks those commits, oldest to newest.
# After cherry-picking, offers to push the new clean branch to the remote.
#
# CONFLICT HANDLING: if cherry-pick fails mid-process, the script exits with
# instructions. The clean branch keeps the commits picked so far. You cannot
# re-run the script as-is because the -clean branch already exists. Options:
#   1. Resolve manually: fix conflicts, git add <files>, git cherry-pick --continue
#   2. Start fresh (recommended): git cherry-pick --abort; git checkout <feature-branch>;
#      git branch -D <feature-branch-clean>; re-run
#   3. Abort and clean up: git cherry-pick --abort; git checkout <feature-branch>;
#      git branch -D <feature-branch-clean>
#
# Usage:
#   ./scripts/bash/git-create-clean-branch.sh [options] <file-or-dir-path> [more-paths...]
#
# Options:
#   --feature-branch <name>   Feature branch to analyze. Default: current branch.
#   --base-branch <name>      Base branch to compare against. Default: master.
#   --last-n <N>               Only cherry-pick the last N filtered commits.
#                               If omitted, prompts interactively (all vs. last N).
#   --skip-fetch                Skip 'git fetch origin'. Useful if you just fetched.
#   -h, --help                  Show this help and exit.
#
# Any remaining (non-option) arguments are the file/directory paths to filter
# commits by — only commits that touched these paths are shown/picked. This
# is the bash equivalent of the PowerShell version's positional -FilePaths
# array (which captures all trailing positional args); named options here
# always come first, then the path list.
#
# Examples:
#   ./scripts/bash/git-create-clean-branch.sh app/connections/ README.md
#   ./scripts/bash/git-create-clean-branch.sh \
#       --feature-branch feature/new-api --base-branch dev app/api/
set -uo pipefail

usage() {
    sed -n '2,33p' "$0" | sed 's/^# \{0,1\}//'
}

feature_branch=""
base_branch="master"
last_n=0
skip_fetch=false
file_paths=()

while [ $# -gt 0 ]; do
    case "$1" in
        --feature-branch) feature_branch="$2"; shift 2 ;;
        --base-branch) base_branch="$2"; shift 2 ;;
        --last-n) last_n="$2"; shift 2 ;;
        --skip-fetch) skip_fetch=true; shift ;;
        -h|--help) usage; exit 0 ;;
        --) shift; file_paths+=("$@"); break ;;
        -*) echo "Unknown option: $1" >&2; exit 1 ;;
        *) file_paths+=("$1"); shift ;;
    esac
done

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=modules/git-script-helpers.sh
source "$script_dir/modules/git-script-helpers.sh"

if [ "${#file_paths[@]}" -eq 0 ]; then
    write_error_msg "At least one file/directory path is required. See --help."
    exit 1
fi

# Step 1: Validate we're in a git repository
write_step "Checking git repository" "[CHECK]"
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    write_error_msg "Not a git repository. Please run this script from inside a git repo."
    exit 1
fi
write_success "Valid git repository"

# Step 2: Determine feature branch
if [ -z "$feature_branch" ]; then
    feature_branch="$(git rev-parse --abbrev-ref HEAD)"
    if [ "$feature_branch" = "HEAD" ]; then
        write_error_msg "You are in detached HEAD state. Please specify --feature-branch explicitly."
        exit 1
    fi
    write_info "Using current branch: $feature_branch"
else
    write_info "Analyzing branch: $feature_branch"
fi

# Step 3: Fetch latest from origin (unless skipped)
if [ "$skip_fetch" = false ]; then
    write_step "Fetching latest changes" "[FETCH]"
    if ! git fetch origin >/dev/null 2>&1; then
        write_error_msg "Failed to fetch from origin"
        exit 1
    fi
    write_success "Fetched latest from origin"
else
    write_info "Skipped fetch (--skip-fetch specified)"
fi

# Step 4: Validate branches exist
write_step "Validating branches" "[VALIDATE]"

if ! git rev-parse --verify "$feature_branch" >/dev/null 2>&1; then
    write_error_msg "Branch '$feature_branch' does not exist"
    exit 1
fi

if ! git rev-parse --verify "origin/$base_branch" >/dev/null 2>&1; then
    write_error_msg "Remote branch 'origin/$base_branch' does not exist"
    exit 1
fi

write_success "Both branches validated"

# Step 5: Build and execute commit list command
write_step "Finding commits that touched specified paths" "[SEARCH]"

commit_count=$(git rev-list --count "origin/$base_branch..$feature_branch" -- "${file_paths[@]}")

if [ "$commit_count" -eq 0 ]; then
    write_info "No commits found that modified the specified file paths."
    printf '\nFiltered by paths:\n'
    for p in "${file_paths[@]}"; do printf '  - %s\n' "$p"; done
    exit 0
fi

printf '\n%s commit(s) from %s that touched specified files:\n\n' "$commit_count" "$feature_branch"
printf 'Clean branch will be created as: %s-clean from origin/%s\n\n' "$feature_branch" "$base_branch"
printf 'Filtered by paths:\n'
for p in "${file_paths[@]}"; do printf '  - %s\n' "$p"; done
printf '\nNo. | Commit Hash | Author | Message\n'
printf -- '-------------------------------------------------------------\n'

mapfile -t commits < <(git log --reverse --oneline \
    --pretty=format:'%h | %an | %s' \
    "origin/$base_branch..$feature_branch" -- "${file_paths[@]}")

total_shown=${#commits[@]}
for i in "${!commits[@]}"; do
    num=$((total_shown - i))
    printf '%s. %s\n' "$num" "${commits[$i]}"
done

printf '\n\n'

# Step 6: Ask whether to cherry-pick all or last N commits
commits_to_cherry="$commit_count"
if [ "$last_n" -gt 0 ] 2>/dev/null; then
    if [ "$last_n" -gt "$commit_count" ]; then
        write_error_msg "last-n ($last_n) is greater than total filtered commits ($commit_count)"
        exit 1
    fi
    commits_to_cherry="$last_n"
    printf 'Using last %s commit(s) from filtered results\n' "$last_n"
else
    printf 'Total filtered commits: %s\n\n' "$commit_count"
    printf 'Options:\n'
    printf '  [a] Cherry-pick all %s commit(s)\n' "$commit_count"
    printf '  [n] Cherry-pick last N commit(s) only\n\n'
    while true; do
        read -r -p "Select option (a/n) " cherry_choice
        case "$cherry_choice" in
            n|N)
                read -r -p "How many last commit(s) to cherry-pick? (1-$commit_count) " last_n_input
                if ! [[ "$last_n_input" =~ ^[0-9]+$ ]]; then
                    write_error_msg "Invalid number entered: $last_n_input"
                    exit 1
                fi
                if [ "$last_n_input" -lt 1 ] || [ "$last_n_input" -gt "$commit_count" ]; then
                    write_error_msg "Number must be between 1 and $commit_count"
                    exit 1
                fi
                commits_to_cherry="$last_n_input"
                printf '\nWill cherry-pick last %s commit(s)\n' "$commits_to_cherry"
                break
                ;;
            a|A) break ;;
            *) write_warn "Invalid option: '$cherry_choice'. Please enter 'a' or 'n'." ;;
        esac
    done
fi

printf '\n'

# Step 7: Confirm before creating branch and cherry-picking
clean_branch_name="${feature_branch}-clean"
printf "This will create branch '%s' and cherry-pick %s commit(s)\n\n" "$clean_branch_name" "$commits_to_cherry"
if ! confirm_action "Continue? (y/N)" "YesNo"; then
    write_info "Operation cancelled. No changes made."
    exit 0
fi

# Step 7b: Check for uncommitted changes
dirty_files="$(git status --porcelain)"
if [ -n "$dirty_files" ]; then
    write_error_msg "You have uncommitted changes. Please commit or stash them first."
    printf '\nUncommitted files:\n%s\n' "$dirty_files"
    exit 1
fi

# Step 8: Create clean branch
write_step "Creating clean branch: $clean_branch_name" "[CREATE]"

if git rev-parse --verify "$clean_branch_name" >/dev/null 2>&1; then
    write_error_msg "Branch '$clean_branch_name' already exists locally. Please delete it first or use a different name."
    exit 1
fi

if [ -n "$(git ls-remote --heads origin "$clean_branch_name")" ]; then
    write_error_msg "Branch '$clean_branch_name' already exists on remote. Please delete it first or use a different name."
    write_info "To delete remote branch: git push origin --delete $clean_branch_name"
    exit 1
fi

original_branch="$(git rev-parse --abbrev-ref HEAD)"
if ! git checkout -b "$clean_branch_name" "origin/$base_branch" >/dev/null 2>&1; then
    write_error_msg "Failed to create branch '$clean_branch_name'"
    exit 1
fi

git branch --unset-upstream >/dev/null 2>&1 || true
write_success "Created and checked out branch: $clean_branch_name"

# Step 9: Get commit hashes and cherry-pick them
write_step "Cherry-picking commits" "[PICK]"

mapfile -t commit_hashes < <(git rev-list --reverse "origin/$base_branch..$feature_branch" -- "${file_paths[@]}")
total_hashes=${#commit_hashes[@]}

start_index=0
if [ "$commits_to_cherry" -lt "$total_hashes" ]; then
    start_index=$((total_hashes - commits_to_cherry))
    write_info "Skipping first $start_index commit(s), cherry-picking last $commits_to_cherry"
fi

success_count=0

for ((i = start_index; i < total_hashes; i++)); do
    hash="${commit_hashes[$i]}"
    printf 'Cherry-picking %s...\n' "$hash"
    if git cherry-pick "$hash" >/dev/null 2>&1; then
        success_count=$((success_count + 1))
        printf '  [OK] Successfully picked %s\n' "$hash"
    else
        printf '  [ERROR] Failed to pick %s\n' "$hash"
        printf '  Conflict detected. Resolve conflicts and run:\n'
        printf '    git cherry-pick --continue\n'
        printf '  Or skip this commit:\n'
        printf '    git cherry-pick --skip\n'
        printf '  Or abort and clean up:\n'
        printf '    git cherry-pick --abort\n'
        printf '    git checkout %s\n' "$original_branch"
        printf '    git branch -D %s\n' "$clean_branch_name"
        write_info "Successfully picked $success_count of $((total_hashes - start_index)) commits before failure."
        exit 1
    fi
done

printf '\n'
write_success "Cherry-pick complete: $success_count commit(s) picked"
write_success "New clean branch created: $clean_branch_name"
printf '\n'

# Step 10: Push clean branch to remote
write_step "Pushing clean branch to remote" "[PUSH]"
printf '\n'
printf "This will push '%s' to origin and set up tracking.\n" "$clean_branch_name"
printf "IMPORTANT: This creates a NEW branch on remote, does NOT push to %s\n\n" "$base_branch"
if confirm_action "Push branch to remote? (y/N)" "YesNo"; then
    if git push origin "$clean_branch_name" >/dev/null 2>&1; then
        write_success "Branch pushed to remote"
        printf '\n'
        write_info "Next step: Create Pull Request on GitHub/GitLab"
        write_info "  From: $clean_branch_name"
        write_info "  To: $base_branch"
    else
        write_error_msg "Failed to push branch to remote"
        write_info "You can push manually later: git push -u origin $clean_branch_name"
    fi
else
    write_info "Skipped push. You can push manually later:"
    printf '  git push -u origin %s\n' "$clean_branch_name"
fi

printf '\n'
write_info "You are now on branch: $clean_branch_name"
