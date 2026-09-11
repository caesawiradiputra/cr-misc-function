#!/usr/bin/env bash
# Cleans up local Git branches that have been deleted on the remote.
#
# Bash port of git-clean-branches.ps1 (PowerShell) — ⚠️ Caution: deletes local
# branches. Removes local branches that no longer exist on the remote
# repository. Can optionally update protected branches first, and remove
# backup tags created by git-reset-branches.sh.
#
# Usage:
#   ./scripts/bash/git-clean-branches.sh [options]
#
# Options:
#   --dry-run                  Preview changes without deleting branches.
#   --no-update                 Skip updating protected branches from remote.
#   --force                     Skip the user confirmation prompt.
#   --purge-only                 Only delete orphaned branches; skip protected
#                                 branch updates.
#   --cleanup-backup-tags        Remove backup tags created by git-reset-branches.sh.
#   --protected-branches <csv>  Comma-separated branches that are never deleted.
#                                 Default: main,master,dev,sit
#   -h, --help                   Show this help and exit.
set -uo pipefail

usage() {
    sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'
}

dry_run=false
no_update=false
force=false
purge_only=false
cleanup_backup_tags=false
protected_branches_csv="main,master,dev,sit"

while [ $# -gt 0 ]; do
    case "$1" in
        --dry-run) dry_run=true; shift ;;
        --no-update) no_update=true; shift ;;
        --force) force=true; shift ;;
        --purge-only) purge_only=true; shift ;;
        --cleanup-backup-tags) cleanup_backup_tags=true; shift ;;
        --protected-branches) protected_branches_csv="$2"; shift 2 ;;
        -h|--help) usage; exit 0 ;;
        *) echo "Unknown option: $1" >&2; exit 1 ;;
    esac
done

IFS=',' read -r -a protected_branches <<< "$protected_branches_csv"

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=modules/git-script-helpers.sh
source "$script_dir/modules/git-script-helpers.sh"

contains() {
    local needle="$1"; shift
    for x in "$@"; do [ "$x" = "$needle" ] && return 0; done
    return 1
}

# ============================================================================
# SETUP & INITIALIZATION
# ============================================================================

timestamp="$(date +%Y%m%d-%H%M%S)"
log_dir="$script_dir/logs"
log_file="$log_dir/clean-branches-$timestamp.log"

deleted_count=0
kept_count=0
protected_count=0
updated_count=0
failed_count=0
backup_tags_deleted_count=0
branches_to_delete=()
backup_tags_to_delete=()

printf '=============================================================\n'
printf 'Branch Cleanup Utility\n'
printf '=============================================================\n\n'

[ "$purge_only" = true ] && { write_info "PURGE ONLY MODE - Will only delete orphaned branches"; printf '\n'; }
[ "$cleanup_backup_tags" = true ] && { write_info "BACKUP TAG CLEANUP - Will remove backup tags created by reset-branches"; printf '\n'; }
[ "$dry_run" = true ] && { write_info "DRY RUN MODE - No branches will be deleted"; printf '\n'; }
[ "$no_update" = true ] && { write_warn "Protected branch updates are DISABLED"; printf '\n'; }

# Validate we are inside a Git repository
if ! repo_root="$(git rev-parse --show-toplevel 2>&1)"; then
    write_error_msg "Not inside a Git repository. Please run from within a Git working directory."
    exit 1
fi
write_info "Repository: $repo_root"
printf '\n'

# User confirmation checkpoint - Require explicit 'yes' to proceed (unless --force)
if [ "$force" = false ]; then
    printf '[WARNING] This script will DELETE local branches!\n'
    printf 'This will:\n'
    if [ "$purge_only" = false ]; then
        printf '  - Update protected branches (%s)\n' "$(IFS=', '; echo "${protected_branches[*]}")"
    fi
    printf '  - Delete branches not on remote\n'
    [ "$cleanup_backup_tags" = true ] && printf '  - Delete backup tags created by reset-branches\n'
    printf '  - Protect: %s\n\n' "$(IFS=', '; echo "${protected_branches[*]}")"

    if ! confirm_action "Type 'yes' to continue" "Explicit"; then
        exit 0
    fi
    printf '\n'
fi

# Start logging after confirmation (avoids orphan log files on cancellation)
mkdir -p "$log_dir"
exec > >(tee -a "$log_file") 2>&1

# ============================================================================
# PHASE 1: SYNC WITH REMOTE
# ============================================================================

write_info "Fetching latest changes from origin (with prune)"
if [ "$dry_run" = true ]; then
    printf '[DRY RUN] git fetch origin --prune\n'
else
    if ! git fetch origin --prune >/dev/null 2>&1; then
        write_error_msg "Failed to fetch from origin"
        exit 1
    fi
fi
write_success "Fetch complete"
printf '\n'

# Gather current branch state
write_info "Gathering branch information"
mapfile -t local_branches < <(git branch --format='%(refname:short)')

mapfile -t remote_branches < <(git branch -r --format='%(refname:short)' \
    | sed 's#^origin/##' | grep -v '^HEAD$')

# Guard: abort if no remote branches found (prevents accidental deletion of all local branches)
if [ "${#remote_branches[@]}" -eq 0 ]; then
    write_error_msg "No remote branches found. Aborting to prevent accidental deletion of all local branches."
    exit 1
fi

# ============================================================================
# PHASE 2: UPDATE PROTECTED BRANCHES (optional)
# ============================================================================

if [ "$no_update" = false ] && [ "$purge_only" = false ]; then
    write_info "Updating protected branches"

    original_branch="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || git branch --show-current)"
    branch_changed=false

    for branch in "${protected_branches[@]}"; do
        if contains "$branch" "${local_branches[@]}"; then
            printf "  Updating '%s'...\n" "$branch"

            if [ "$dry_run" = true ]; then
                printf '    [DRY RUN] git checkout %s; git pull origin %s\n' "$branch" "$branch"
            else
                if git checkout "$branch" >/dev/null 2>&1; then
                    branch_changed=true
                    if git pull origin "$branch" >/dev/null 2>&1; then
                        write_success "  Updated '$branch'"
                        updated_count=$((updated_count + 1))
                    else
                        write_warn "  Failed to pull '$branch'"
                        failed_count=$((failed_count + 1))
                    fi
                else
                    write_warn "  Failed to checkout '$branch' (may be in use by a worktree)"
                    failed_count=$((failed_count + 1))
                fi
            fi
        else
            write_info "  Skipping '$branch' (not found locally)"
        fi
    done

    if [ "$branch_changed" = true ] && [ -n "$original_branch" ] && [ "$dry_run" = false ]; then
        if git checkout "$original_branch" >/dev/null 2>&1; then
            write_info "  Restored to original branch '$original_branch'"
        else
            write_warn "  Could not restore to '$original_branch'"
        fi
    fi

    printf '\n'
fi

# ============================================================================
# PHASE 3: IDENTIFY ORPHANED BRANCHES
# ============================================================================

write_info "Checking local branches for cleanup"

for branch in "${local_branches[@]}"; do
    if contains "$branch" "${protected_branches[@]}"; then
        printf "  [PROTECTED] '%s'\n" "$branch"
        protected_count=$((protected_count + 1))
        continue
    fi

    if ! contains "$branch" "${remote_branches[@]}"; then
        printf "  [DELETE] '%s' (not on remote)\n" "$branch"
        branches_to_delete+=("$branch")
    else
        printf "  [KEEP] '%s'\n" "$branch"
        kept_count=$((kept_count + 1))
    fi
done

printf '\n'

# ============================================================================
# PHASE 4: DELETE ORPHANED BRANCHES
# ============================================================================

if [ "${#branches_to_delete[@]}" -gt 0 ]; then
    printf 'Branches to be deleted (%s):\n' "${#branches_to_delete[@]}"
    for branch in "${branches_to_delete[@]}"; do printf '  - %s\n' "$branch"; done
    printf '\n'
fi

if [ "${#branches_to_delete[@]}" -gt 0 ]; then
    if [ "$dry_run" = true ]; then
        write_info "DRY RUN: Would delete the following branches"
        for branch in "${branches_to_delete[@]}"; do printf '  [DRY RUN] git branch -D %s\n' "$branch"; done
        deleted_count=${#branches_to_delete[@]}
    else
        write_info "Deleting branches"
        current_branch="$(git branch --show-current)"
        if contains "$current_branch" "${branches_to_delete[@]}"; then
            safe_branch=""
            for candidate in "${protected_branches[@]}"; do
                if contains "$candidate" "${local_branches[@]}" && [ "$candidate" != "$current_branch" ]; then
                    safe_branch="$candidate"
                    break
                fi
            done
            if [ -n "$safe_branch" ]; then
                write_warn "Current branch '$current_branch' is marked for deletion. Switching to '$safe_branch' first."
                git checkout "$safe_branch" >/dev/null 2>&1
            fi
        fi

        for branch in "${branches_to_delete[@]}"; do
            if git branch -D "$branch" >/dev/null 2>&1; then
                write_success "  Deleted '$branch'"
                deleted_count=$((deleted_count + 1))
            else
                write_error_msg "  Failed to delete '$branch'"
                failed_count=$((failed_count + 1))
            fi
        done
    fi
else
    write_info "No branches to delete"
fi

printf '\n'

# ============================================================================
# PHASE 5: CLEANUP BACKUP TAGS (optional)
# ============================================================================

if [ "$cleanup_backup_tags" = true ]; then
    write_info "Checking for backup tags to cleanup"

    mapfile -t all_tags < <(git tag --list "backup-*")

    if [ "${#all_tags[@]}" -eq 0 ]; then
        write_info "No backup tags found"
    else
        printf 'Found %s backup tag(s):\n' "${#all_tags[@]}"
        for tag in "${all_tags[@]}"; do
            printf "  [DELETE] '%s'\n" "$tag"
            backup_tags_to_delete+=("$tag")
        done
        printf '\n'

        if [ "$dry_run" = true ]; then
            write_info "DRY RUN: Would delete the following backup tags"
            for tag in "${backup_tags_to_delete[@]}"; do
                printf '  [DRY RUN] git tag -d %s (local)\n' "$tag"
                printf '  [DRY RUN] git push origin :refs/tags/%s (remote)\n' "$tag"
            done
            backup_tags_deleted_count=${#backup_tags_to_delete[@]}
        else
            write_info "Deleting backup tags"
            for tag in "${backup_tags_to_delete[@]}"; do
                if git tag -d "$tag" >/dev/null 2>&1; then
                    if git push origin ":refs/tags/$tag" >/dev/null 2>&1; then
                        write_success "  Deleted tag '$tag' (local and remote)"
                        backup_tags_deleted_count=$((backup_tags_deleted_count + 1))
                    else
                        write_warn "  Failed to delete remote tag '$tag' (local deleted)"
                        failed_count=$((failed_count + 1))
                    fi
                else
                    write_error_msg "  Failed to delete tag '$tag'"
                    failed_count=$((failed_count + 1))
                fi
            done
        fi
        printf '\n'
    fi
fi

printf '\n'

# ============================================================================
# EXECUTION SUMMARY
# ============================================================================

printf 'Summary:\n'
printf '  Deleted:  %s\n' "$deleted_count"
printf '  Kept:     %s\n' "$kept_count"
printf '  Protected: %s\n' "$protected_count"
if [ "$no_update" = false ] && [ "$purge_only" = false ]; then
    printf '  Updated:  %s\n' "$updated_count"
fi
[ "$backup_tags_deleted_count" -gt 0 ] && printf '  Backup Tags Deleted: %s\n' "$backup_tags_deleted_count"
[ "$failed_count" -gt 0 ] && printf '  Failed:   %s\n' "$failed_count"
printf '=============================================================\n'

if [ "$dry_run" = true ]; then
    printf '\n'
    write_info "This was a DRY RUN - no branches were deleted"
    printf 'Run without --dry-run to execute\n'
fi

printf '\nLog saved to: %s\n' "$log_file"
printf '============================================================\n'
