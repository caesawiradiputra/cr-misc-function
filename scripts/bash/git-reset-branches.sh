#!/usr/bin/env bash
# Reset Git branches (master, dev, sit) to their remote state with backup
# safeguards. Bash port of git-reset-branches.ps1 (PowerShell) — see
# scripts/powershell/RESET_BRANCHES_GUIDE.md for the full usage guide; the
# behavior described there applies unchanged to this script.
#
# 🔴 DESTRUCTIVE: force-resets master/dev/sit to match remote, discarding
# local history on those branches, then force-pushes. Always run
# --dry-run first.
#
# Cascading reset performed:
#   1. Fetch latest changes from origin
#   2. Create backup tags at current remote state (for recovery), unless
#      --no-backup
#   3. Reset master -> origin/master, then dev -> origin/master,
#      then sit -> origin/dev
#   4. Force-push each reset branch back to origin (--force-with-lease)
#
# Usage:
#   ./scripts/bash/git-reset-branches.sh [options]
#
# Options:
#   --dry-run     Preview what would happen; makes no changes.
#   --no-backup   Skip creating backup tags before resetting. Use with caution.
#   --force       Skip the confirmation prompt (for CI/CD). Backups still run
#                 unless --no-backup is also given.
#   --only-dev    Reset only the DEV branch (to master). Skips master and sit.
#                 Mutually exclusive with --only-sit.
#   --only-sit    Reset only the SIT branch (to dev). Skips master and dev.
#                 Mutually exclusive with --only-dev.
#   -h, --help    Show this help and exit.
#
# Examples:
#   ./scripts/bash/git-reset-branches.sh --dry-run
#   ./scripts/bash/git-reset-branches.sh
#   ./scripts/bash/git-reset-branches.sh --only-sit
#   ./scripts/bash/git-reset-branches.sh --no-backup --force
#
# A timestamped log of the full run is written to ./logs/ next to this
# script, mirroring stdout/stderr the way the PowerShell version's
# Start-Transcript does.
set -uo pipefail
# Deliberately NOT using `set -e`: this script mirrors the PowerShell
# original's control flow, which checks $LASTEXITCODE after almost every
# git command and reacts explicitly (custom error message, partial-failure
# bookkeeping, sometimes continuing to the next branch). `set -e` would abort
# on the first non-zero git exit without running that logic, changing
# behavior on a script whose whole point is controlled, recoverable failure
# handling. Every git command below is followed by an explicit exit-status
# check instead.

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$script_dir/modules/git-script-helpers.sh"

usage() {
    cat <<'EOF'
Reset Git branches (master, dev, sit) to their remote state with backup
safeguards.

DESTRUCTIVE: force-resets master/dev/sit to match remote, discarding local
history on those branches, then force-pushes. Always run --dry-run first.
See scripts/powershell/RESET_BRANCHES_GUIDE.md for the full usage guide.

Cascading reset performed:
  1. Fetch latest changes from origin
  2. Create backup tags at current remote state (for recovery), unless
     --no-backup
  3. Reset master -> origin/master, then dev -> origin/master,
     then sit -> origin/dev
  4. Force-push each reset branch back to origin (--force-with-lease)

Usage:
  ./scripts/bash/git-reset-branches.sh [options]

Options:
  --dry-run     Preview what would happen; makes no changes.
  --no-backup   Skip creating backup tags before resetting. Use with caution.
  --force       Skip the confirmation prompt (for CI/CD). Backups still run
                unless --no-backup is also given.
  --only-dev    Reset only the DEV branch (to master). Skips master and sit.
                Mutually exclusive with --only-sit.
  --only-sit    Reset only the SIT branch (to dev). Skips master and dev.
                Mutually exclusive with --only-dev.
  -h, --help    Show this help and exit.

Examples:
  ./scripts/bash/git-reset-branches.sh --dry-run
  ./scripts/bash/git-reset-branches.sh
  ./scripts/bash/git-reset-branches.sh --only-sit
  ./scripts/bash/git-reset-branches.sh --no-backup --force

A timestamped log of the full run is written to ./logs/ next to this
script, mirroring stdout/stderr the way the PowerShell version's
Start-Transcript does.
EOF
}

dry_run=false
no_backup=false
force=false
only_dev=false
only_sit=false

while [ $# -gt 0 ]; do
    case "$1" in
        --dry-run) dry_run=true; shift ;;
        --no-backup) no_backup=true; shift ;;
        --force) force=true; shift ;;
        --only-dev) only_dev=true; shift ;;
        --only-sit) only_sit=true; shift ;;
        -h|--help) usage; exit 0 ;;
        *) echo "Unknown option: $1" >&2; exit 1 ;;
    esac
done

# Determine color support from the REAL terminal now, before stdout gets
# redirected through `tee` for logging below — checking `[ -t 1 ]` after that
# redirection would always say "not a terminal" and silently kill all color,
# unlike the PowerShell version (Start-Transcript logs plain text but leaves
# on-screen host colors untouched).
if [ -t 1 ]; then
    CYAN=$'\033[36m'; GREEN=$'\033[32m'; YELLOW=$'\033[33m'; RED=$'\033[31m'; GRAY=$'\033[90m'; RESET=$'\033[0m'
else
    CYAN=""; GREEN=""; YELLOW=""; RED=""; GRAY=""; RESET=""
fi
write_color() { printf '%b%b%b\n' "$2" "$1" "$RESET"; }

# ============================================================================
# MUTUAL EXCLUSIVITY GUARD (before logging starts, matching the .ps1 order)
# ============================================================================
if [ "$only_dev" = true ] && [ "$only_sit" = true ]; then
    write_error_msg "--only-dev and --only-sit are mutually exclusive. Please choose one."
    exit 1
fi

# ============================================================================
# SETUP LOGGING
# ============================================================================
timestamp="$(date +%Y%m%d-%H%M%S)"
log_dir="$script_dir/logs"
log_file="$log_dir/reset-branches-$timestamp.log"
mkdir -p "$log_dir"

exec > >(tee -a "$log_file") 2>&1

write_color "=============================================================" "$CYAN"
write_color "Branch Reset Utility" "$CYAN"
write_color "=============================================================" "$CYAN"
echo ""

if [ "$dry_run" = true ]; then
    write_color "[DRY RUN MODE] No changes will be made" "$YELLOW"
    echo ""
fi

if [ "$only_dev" = true ]; then
    write_color "[SINGLE BRANCH MODE] Only DEV branch will be reset to master state" "$CYAN"
    echo ""
fi

if [ "$only_sit" = true ]; then
    write_color "[SINGLE BRANCH MODE] Only SIT branch will be reset to dev state" "$CYAN"
    echo ""
fi

if [ "$no_backup" = true ]; then
    write_color "[WARNING] Backup creation is DISABLED" "$YELLOW"
    echo ""
fi

# ============================================================================
# GIT REPOSITORY VALIDATION
# ============================================================================
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    write_error_msg "This script must be run from inside a Git repository"
    exit 1
fi

# ============================================================================
# UNCOMMITTED CHANGES CHECK
# ============================================================================
dirty_files="$(git status --porcelain 2>&1)"
if [ -n "$dirty_files" ]; then
    write_error_msg "Working directory has uncommitted changes:"
    while IFS= read -r line; do
        write_color "  $line" "$RED"
    done <<< "$dirty_files"
    write_color "Please commit or stash changes before running this script." "$YELLOW"
    exit 1
fi

# ============================================================================
# USER CONFIRMATION
# ============================================================================
if [ "$force" = false ]; then
    write_color "[WARNING] This script will FORCE RESET branches!" "$RED"
    if [ "$only_dev" = true ]; then
        write_color "This will:" "$RED"
        write_color "  - Reset DEV branch to master state" "$RED"
        write_color "  - Discard uncommitted changes on DEV" "$RED"
        write_color "  - Force push to origin" "$RED"
    elif [ "$only_sit" = true ]; then
        write_color "This will:" "$RED"
        write_color "  - Reset SIT branch to dev state" "$RED"
        write_color "  - Discard uncommitted changes on SIT" "$RED"
        write_color "  - Force push to origin" "$RED"
    else
        write_color "This will:" "$RED"
        write_color "  - Reset master, dev, and sit branches" "$RED"
        write_color "  - Rewrite branch history" "$RED"
        write_color "  - Force push to origin" "$RED"
    fi
    echo ""

    if [ "$no_backup" = false ]; then
        write_color "[OK] Backup tags WILL be created for recovery" "$GREEN"
    fi

    echo ""

    if ! confirm_action "Type 'yes' to continue" "Explicit"; then
        exit 0
    fi

    echo ""
fi

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

# reset_branch <branch-name> <reset-target> <dry-run true|false>
# Returns 0 on success, 1 on failure (checkout/reset/push failed).
reset_branch() {
    local branch_name="$1" reset_target="$2" is_dry_run="$3"

    write_color "Updating $branch_name branch..." "$CYAN"

    if [ "$is_dry_run" = true ]; then
        write_color "[DRY RUN] git checkout $branch_name" "$GRAY"
        write_color "[DRY RUN] git reset --hard $reset_target" "$GRAY"
        write_color "[DRY RUN] git push origin $branch_name --force-with-lease" "$GRAY"
        write_color "[OK] $branch_name branch would be reset to $reset_target" "$GREEN"
        echo ""
        return 0
    fi

    if ! git checkout "$branch_name" >/dev/null 2>&1; then
        write_error_msg "Failed to checkout $branch_name branch"
        echo ""
        return 1
    fi

    if ! git reset --hard "$reset_target"; then
        write_error_msg "Failed to reset $branch_name branch"
        echo ""
        return 1
    fi

    write_success "$branch_name branch reset to $reset_target"
    write_color "Pushing $branch_name to origin..." "$YELLOW"
    if git push origin "$branch_name" --force-with-lease; then
        write_success "$branch_name branch pushed to origin"
        echo ""
        return 0
    else
        write_error_msg "Failed to push $branch_name branch"
        echo ""
        return 1
    fi
}

# ============================================================================
# FETCH LATEST CHANGES FROM REMOTE
# ============================================================================
write_color "Fetching latest changes from origin..." "$CYAN"
if [ "$dry_run" = true ]; then
    write_color "[DRY RUN] git fetch origin --prune" "$GRAY"
else
    if ! git fetch origin --prune >/dev/null 2>&1; then
        write_error_msg "Failed to fetch from origin"
        exit 1
    fi
fi

write_success "Fetch complete"
echo ""

# Get list of local branches (for later use)
mapfile -t local_branches < <(git branch --format='%(refname:short)')

has_local_branch() {
    local target="$1" b
    for b in "${local_branches[@]:-}"; do
        [ "$b" = "$target" ] && return 0
    done
    return 1
}

# Define protected branches
protected_branches=(master dev sit)

# ============================================================================
# CREATE BACKUP TAGS
# ============================================================================
backup_tags_to_push=()

if [ "$no_backup" = false ]; then
    write_color "Creating backup tags..." "$CYAN"
    backup_created_count=0
    backup_skipped_count=0

    # Determine which branches to backup
    if [ "$only_dev" = true ]; then
        branches_to_backup=(dev)
    elif [ "$only_sit" = true ]; then
        branches_to_backup=(sit)
    else
        branches_to_backup=("${protected_branches[@]}")
    fi

    for branch in "${branches_to_backup[@]}"; do
        remote_id="$(git rev-parse "origin/$branch" 2>&1)"
        rc=$?

        if [ $rc -eq 0 ] && [ -n "$remote_id" ]; then
            if [ "${#remote_id}" -ge 8 ]; then
                remote_short_id="${remote_id:0:8}"
            else
                remote_short_id="$remote_id"
            fi

            existing_tag="$(git tag -l "backup-$branch-$remote_short_id-*" 2>&1)"
            if [ -n "$existing_tag" ]; then
                write_color "  [SKIP] Branch 'origin/$branch' (ID: $remote_short_id) - backup already exists for this commit" "$GRAY"
                backup_skipped_count=$((backup_skipped_count + 1))
                continue
            fi

            tag_name="backup-$branch-$remote_short_id-$timestamp"
            if [ "$dry_run" = true ]; then
                write_color "[DRY RUN] git tag $tag_name origin/$branch" "$GRAY"
            else
                if git tag "$tag_name" "origin/$branch" >/dev/null 2>&1; then
                    write_color "  [OK] Created tag: $tag_name" "$GREEN"
                    backup_created_count=$((backup_created_count + 1))
                    backup_tags_to_push+=("$tag_name")
                else
                    write_error_msg "Failed to create tag for '$branch'"
                fi
            fi
        else
            write_warn "Could not get commit ID for 'origin/$branch'"
        fi
    done

    if [ "$dry_run" = false ]; then
        write_color "Pushing backup tags to origin..." "$CYAN"
        if [ "${#backup_tags_to_push[@]}" -gt 0 ]; then
            if git push origin "${backup_tags_to_push[@]}" >/dev/null 2>&1; then
                write_color "  [OK] Backup tags pushed to origin" "$GREEN"
            else
                write_error_msg "Failed to push backup tags to origin. Aborting to prevent unrecoverable reset."
                exit 1
            fi
        else
            write_color "  [SKIP] No new backup tags to push" "$GRAY"
        fi
        write_color "  Summary: $backup_created_count created, $backup_skipped_count skipped" "$CYAN"
        echo ""
    else
        write_color "[DRY RUN] git push origin <backup-tags>" "$GRAY"
        echo ""
    fi
fi

# ============================================================================
# VERIFY PROTECTED BRANCHES EXIST LOCALLY
# ============================================================================
write_color "Verifying protected branches exist..." "$CYAN"

if [ "$only_dev" = true ]; then
    branches_to_verify=(dev)
elif [ "$only_sit" = true ]; then
    branches_to_verify=(sit)
else
    branches_to_verify=("${protected_branches[@]}")
fi

for branch in "${branches_to_verify[@]}"; do
    if ! has_local_branch "$branch"; then
        write_warn "Branch '$branch' does not exist locally"
    fi
done

echo ""

# ============================================================================
# SAVE ORIGINAL BRANCH
# ============================================================================
original_branch="$(git rev-parse --abbrev-ref HEAD 2>&1)"

# ============================================================================
# RESET PROTECTED BRANCHES
# ============================================================================
reset_failed=false

# Only reset master if not in --only-sit or --only-dev mode
if [ "$only_sit" = false ] && [ "$only_dev" = false ]; then
    # --- MASTER BRANCH: Reset to remote state --- (no local-existence check,
    # matching the .ps1: master is always attempted in full mode)
    if ! reset_branch "master" "origin/master" "$dry_run"; then
        reset_failed=true
    fi

    # --- DEV BRANCH: Reset to match master --- (full reset mode)
    if [ "$reset_failed" = false ]; then
        if has_local_branch "dev"; then
            if ! reset_branch "dev" "origin/master" "$dry_run"; then
                reset_failed=true
            fi
        else
            write_warn "Dev branch does not exist, skipping..."
            echo ""
        fi
    fi
elif [ "$only_dev" = true ]; then
    # --- DEV BRANCH (only-dev mode): Reset to match master ---
    write_info "[SKIPPED] Master branch (--only-dev mode)"
    echo ""
    if has_local_branch "dev"; then
        if ! reset_branch "dev" "origin/master" "$dry_run"; then
            reset_failed=true
        fi
    else
        write_warn "Dev branch does not exist, skipping..."
        echo ""
    fi
else
    write_info "[SKIPPED] Master and dev branches (--only-sit mode)"
    echo ""
fi

# --- SIT BRANCH: Reset to match dev --- (skipped in only-dev mode)
if [ "$reset_failed" = false ]; then
    if [ "$only_dev" = true ]; then
        write_info "[SKIPPED] Sit branch (--only-dev mode)"
        echo ""
    elif has_local_branch "sit"; then
        if ! reset_branch "sit" "origin/dev" "$dry_run"; then
            reset_failed=true
        fi
    else
        write_warn "Sit branch does not exist, skipping..."
        echo ""
    fi
fi

if [ "$reset_failed" = true ]; then
    # Deliberately exits WITHOUT restoring the original branch, matching the
    # .ps1: on a cascade failure it exits here, before the restore step below.
    exit 1
fi

# ============================================================================
# RESTORE ORIGINAL BRANCH
# ============================================================================
if [ "$dry_run" = false ] && [ -n "$original_branch" ]; then
    if git checkout "$original_branch" >/dev/null 2>&1; then
        write_success "Restored original branch: $original_branch"
    else
        write_warn "Could not restore original branch: $original_branch"
    fi
fi

# ============================================================================
# SUMMARY AND CLEANUP
# ============================================================================
write_color "=============================================================" "$CYAN"
if [ "$dry_run" = true ]; then
    if [ "$only_dev" = true ]; then
        write_color "[DRY RUN] DEV branch reset preview complete - no changes made" "$CYAN"
    elif [ "$only_sit" = true ]; then
        write_color "[DRY RUN] SIT branch reset preview complete - no changes made" "$CYAN"
    else
        write_color "[DRY RUN] Branch reset preview complete - no changes made" "$CYAN"
    fi
else
    if [ "$only_dev" = true ]; then
        write_color "[OK] DEV branch has been reset to master state successfully!" "$CYAN"
    elif [ "$only_sit" = true ]; then
        write_color "[OK] SIT branch has been reset to dev state successfully!" "$CYAN"
    else
        write_color "[OK] All branches have been reset successfully!" "$CYAN"
    fi
fi
write_color "=============================================================" "$CYAN"

if [ "$dry_run" = true ]; then
    echo ""
    write_color "[DRY RUN] This was a DRY RUN - no changes were made" "$YELLOW"
    write_color "[DRY RUN] Run without --dry-run to execute" "$YELLOW"
fi

echo ""
write_color "Log saved to: $log_file" "$CYAN"
