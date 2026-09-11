#!/usr/bin/env bash
# Shared helper functions for Git bash scripts.
#
# Provides canonical output helpers, confirmation prompts with retry loops,
# and common git utility functions used across all git-*.sh scripts.
#
# Source in scripts:
#   source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/modules/git-script-helpers.sh"
#
# Bash port of modules/GitScriptHelpers.psm1 (PowerShell) — keep the two in
# sync: same function names (snake_case here vs PascalCase there), same
# messages, same Confirm-Action / confirm_action styles.

# ============================================================================
# OUTPUT HELPERS - Color-coded status messages with consistent formatting
# ============================================================================

# Colors are only emitted when stdout is a terminal, so piping/redirecting
# output (e.g. in CI logs) doesn't leave raw escape codes behind.
if [ -t 1 ]; then
    _GSH_CYAN=$'\033[36m'
    _GSH_WHITE=$'\033[37m'
    _GSH_YELLOW=$'\033[33m'
    _GSH_GREEN=$'\033[32m'
    _GSH_RED=$'\033[31m'
    _GSH_RESET=$'\033[0m'
else
    _GSH_CYAN=""; _GSH_WHITE=""; _GSH_YELLOW=""; _GSH_GREEN=""; _GSH_RED=""; _GSH_RESET=""
fi

# write_step "Message" ["[STEP]"]
write_step() {
    local message="$1"
    local prefix="${2:-[STEP]}"
    printf '\n%s%s %s%s%s\n' "$_GSH_CYAN" "$prefix" "$_GSH_WHITE" "$message" "$_GSH_RESET"
}

# write_info "Message"
write_info() {
    printf '%s[INFO] %s%s%s\n' "$_GSH_CYAN" "$_GSH_WHITE" "$1" "$_GSH_RESET"
}

# write_warn "Message"
write_warn() {
    printf '%s[WARN] %s%s%s\n' "$_GSH_YELLOW" "$_GSH_WHITE" "$1" "$_GSH_RESET"
}

# write_success "Message"
write_success() {
    printf '%s[OK] %s%s%s\n' "$_GSH_GREEN" "$_GSH_WHITE" "$1" "$_GSH_RESET"
}

# write_error_msg "Message"
write_error_msg() {
    printf '%s[ERROR] %s%s%s\n' "$_GSH_RED" "$_GSH_WHITE" "$1" "$_GSH_RESET"
}

# ============================================================================
# CONFIRMATION PROMPT - Standardized retry loop with two modes
# ============================================================================

# confirm_action "Prompt" ["Explicit"|"YesNo"] ["Cancel message"]
#
# Two styles:
#   Explicit (default): user must type 'yes' to proceed. Empty input = cancel.
#                        Use for destructive operations (reset, delete).
#   YesNo:               user enters 'y' or 'n'. Empty input re-prompts.
#                        Use for regular confirmations (push, rebase, sync).
#
# Returns 0 (success/true) if confirmed, 1 (false) if cancelled — matches
# bash's exit-code convention, so call sites use:
#   if ! confirm_action "Type 'yes' to continue" "Explicit"; then exit 0; fi
confirm_action() {
    local prompt="$1"
    local style="${2:-Explicit}"
    local cancel_message="${3:-Operation cancelled by user}"
    local input

    while true; do
        read -r -p "$prompt " input
        input="$(printf '%s' "$input" | tr '[:upper:]' '[:lower:]' | xargs)"

        if [ "$style" = "Explicit" ]; then
            if [ "$input" = "yes" ]; then
                return 0
            fi
            if [ -z "$input" ]; then
                write_warn "$cancel_message"
                return 1
            fi
            write_warn "Invalid input: '$input'. Type 'yes' to confirm or press Enter to cancel."
        else
            if [ "$input" = "y" ]; then
                return 0
            fi
            if [ "$input" = "n" ]; then
                return 1
            fi
            write_warn "Invalid input: '$input'. Please enter 'y' or 'n'."
        fi
    done
}
