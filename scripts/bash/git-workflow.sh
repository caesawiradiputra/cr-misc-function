#!/usr/bin/env bash
# Git workflow orchestrator - chains git utility scripts for common workflows.
#
# Bash port of git-workflow.ps1 (PowerShell).
#
# Workflow map:
#   git-clean-branches  -->  git-check-sync-set-dev  -->  git-init-feature
#       (prune stale)         (sync dev, activate)         (create branch)
#                                                             |
#                                                             v
#   git-reset-branches  <--  git-rebase-branch  <--  git-create-clean-branch
#       (emergency)          (rebase onto base)       (cherry-pick filtered)
#
# Requires all git-*.sh scripts to be in the same directory.
set -uo pipefail

usage() {
    cat <<'EOF'
Git workflow orchestrator - chains git utility scripts for common workflows.

Usage:
  ./scripts/bash/git-workflow.sh <action> [options]

Actions:
  prepare  - Clean stale branches, then sync dev with master
  start    - Sync dev with master, then create a new feature branch
  finish   - Rebase feature branch onto base for clean merge
  recover  - Reset all branches to remote state (emergency recovery)
  status   - Show current git state (branch, dirty files, remote sync)

Options:
  --force     Pass --force to underlying scripts (skip confirmation prompts).
  --dry-run   Pass --dry-run to underlying scripts where applicable.
  -h, --help  Show this help and exit.

Examples:
  ./scripts/bash/git-workflow.sh prepare
  ./scripts/bash/git-workflow.sh start --force
  ./scripts/bash/git-workflow.sh recover --dry-run
EOF
}

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/modules/git-script-helpers.sh"
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

action=""
force=false
dry_run=false

while [ $# -gt 0 ]; do
    case "$1" in
        --force) force=true; shift ;;
        --dry-run) dry_run=true; shift ;;
        -h|--help) usage; exit 0 ;;
        prepare|start|finish|recover|status) action="$1"; shift ;;
        *) echo "Unknown argument: $1" >&2; usage; exit 1 ;;
    esac
done

if [ -z "$action" ]; then
    write_error_msg "Action is required (prepare|start|finish|recover|status)"
    usage
    exit 1
fi

CYAN=$'\033[36m'; DARKCYAN=$'\033[36m'; GREEN=$'\033[32m'; YELLOW=$'\033[33m'; WHITE=$'\033[37m'; RED=$'\033[31m'; GRAY=$'\033[90m'; RESET=$'\033[0m'
[ -t 1 ] || { CYAN=""; DARKCYAN=""; GREEN=""; YELLOW=""; WHITE=""; RED=""; GRAY=""; RESET=""; }
color_line() { printf '%b%b%b\n' "$2" "$1" "$RESET"; }

# invoke_script <script-name> [extra args...]
# Runs a sibling git-*.sh script, forwarding --force/--dry-run when set.
# Returns the sibling script's own exit code.
invoke_script() {
    local script_name="$1"; shift
    local script_path="$script_dir/$script_name"

    if [ ! -f "$script_path" ]; then
        write_error_msg "Script not found: $script_path"
        return 1
    fi

    local args=()
    [ "$force" = true ] && args+=(--force)
    [ "$dry_run" = true ] && args+=(--dry-run)
    args+=("$@")

    echo ""
    color_line "=============================================================" "$DARKCYAN"
    color_line "  Running: $script_name ${args[*]}" "$DARKCYAN"
    color_line "=============================================================" "$DARKCYAN"
    echo ""

    "$script_path" "${args[@]}"
    local exit_code=$?

    if [ "$exit_code" -ne 0 ]; then
        write_error_msg "$script_name exited with code $exit_code. Aborting workflow."
        return 1
    fi
    return 0
}

echo ""
color_line "=============================================================" "$CYAN"
color_line "Git Workflow Orchestrator" "$CYAN"
color_line "=============================================================" "$CYAN"
echo ""

case "$action" in

    prepare)
        # Clean stale branches, then sync dev with master
        write_info "Workflow: PREPARE (clean + sync)"
        color_line "  1. Clean stale local branches" "$WHITE"
        color_line "  2. Sync dev with master" "$WHITE"
        echo ""

        invoke_script "git-clean-branches.sh" || exit 1
        invoke_script "git-check-sync-set-dev.sh" || exit 1

        write_success "PREPARE workflow complete"
        ;;

    start)
        # Sync dev with master, then create feature branch
        write_info "Workflow: START (sync + create feature branch)"
        color_line "  1. Sync dev with master" "$WHITE"
        color_line "  2. Create new feature branch" "$WHITE"
        echo ""

        invoke_script "git-check-sync-set-dev.sh" || exit 1
        invoke_script "git-init-feature.sh" || exit 1

        write_success "START workflow complete"
        ;;

    finish)
        # Rebase feature branch onto base
        write_info "Workflow: FINISH (rebase feature branch)"
        color_line "  1. Rebase current feature branch onto master" "$WHITE"
        echo ""

        invoke_script "git-rebase-branch.sh" || exit 1

        write_success "FINISH workflow complete"
        echo ""
        write_info "Next steps:"
        color_line "  - Push rebased branch: git push --force-with-lease origin <branch>" "$WHITE"
        color_line "  - Create PR on GitHub/GitLab" "$WHITE"
        ;;

    recover)
        # Reset all branches to remote state
        write_info "Workflow: RECOVER (reset branches to remote state)"
        color_line "  WARNING: This is a DESTRUCTIVE operation" "$RED"
        color_line "  All local changes on master/dev/sit will be lost" "$RED"
        echo ""

        invoke_script "git-reset-branches.sh" || exit 1

        write_success "RECOVER workflow complete"
        ;;

    status)
        # Show current git state summary
        write_info "Current Git State"
        echo ""

        current_branch="$(git rev-parse --abbrev-ref HEAD 2>&1)"
        color_line "  Branch:  $current_branch" "$WHITE"

        dirty="$(git status --porcelain 2>&1)"
        if [ -n "$dirty" ]; then
            count=$(printf '%s\n' "$dirty" | grep -c .)
            color_line "  Status:  $count uncommitted change(s)" "$YELLOW"
        else
            color_line "  Status:  Clean working directory" "$GREEN"
        fi

        if upstream="$(git rev-parse --abbrev-ref '@{upstream}' 2>/dev/null)" && [ -n "$upstream" ]; then
            color_line "  Tracking: $upstream" "$WHITE"

            ahead=$(git rev-list --count "$upstream..HEAD" 2>&1)
            behind=$(git rev-list --count "HEAD..$upstream" 2>&1)

            if [ "$ahead" -gt 0 ] && [ "$behind" -gt 0 ]; then
                color_line "  Ahead:   $ahead commit(s), Behind: $behind commit(s)" "$YELLOW"
            elif [ "$ahead" -gt 0 ]; then
                color_line "  Ahead:   $ahead commit(s) (needs push)" "$YELLOW"
            elif [ "$behind" -gt 0 ]; then
                color_line "  Behind:  $behind commit(s) (needs pull)" "$YELLOW"
            else
                color_line "  Sync:    Up to date with remote" "$GREEN"
            fi
        else
            color_line "  Tracking: No upstream set" "$GRAY"
        fi

        echo ""
        dev_master_diff="$(git diff origin/master origin/dev --stat 2>&1)"
        if [ -z "$dev_master_diff" ]; then
            write_info "Dev is in sync with master (no code differences)"
        else
            write_warn "Dev has code differences from master"
        fi
        ;;
esac

echo ""
