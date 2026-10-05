#!/usr/bin/env bash
# Updates .github.template with changes from a workspace .github folder.
#
# Bash port of chat-update-template-from-workspace.ps1 (PowerShell). Reverse
# of chat-sync-github-instructions.sh: compares workspace .github/{instructions,
# prompts} against the canonical .github.template (one level above this
# repo). Only UPDATES files that already exist in the template — never adds
# new ones, and never touches agents/prompts... note: unlike the forward
# sync script, this only covers instructions/ and prompts/ (not agents/ or
# skills/), matching the original .ps1 exactly.
set -uo pipefail

usage() {
    cat <<'EOF'
Updates .github.template with changes from a workspace .github folder.
Only updates files already present in the template — never adds new ones.

Usage:
  ./scripts/bash/chat-update-template-from-workspace.sh [options]

Options:
  --workspace-root <dir>  Workspace root where .github/ folder exists.
                           Default: current working directory.
  --template-path <dir>   Path to the canonical .github.template folder.
                           Default: this repo's umbrella dir (one level above
                           the repo root)/.github.template
  --dry-run               Show what would be done without making changes.
  --verbose               Show detailed output of all operations.
  -h, --help              Show this help and exit.

Examples:
  ./scripts/bash/chat-update-template-from-workspace.sh
  ./scripts/bash/chat-update-template-from-workspace.sh --dry-run
  ./scripts/bash/chat-update-template-from-workspace.sh --workspace-root /path/to/workspace --verbose
EOF
}

workspace_root="$(pwd)"
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
github_template_path="$(dirname "$repo_root")/.github.template"
dry_run=false
verbose=false

while [ $# -gt 0 ]; do
    case "$1" in
        --workspace-root) workspace_root="$2"; shift 2 ;;
        --template-path) github_template_path="$2"; shift 2 ;;
        --dry-run) dry_run=true; shift ;;
        --verbose) verbose=true; shift ;;
        -h|--help) usage; exit 0 ;;
        *) echo "Unknown option: $1" >&2; exit 1 ;;
    esac
done

CYAN=$'\033[36m'; GREEN=$'\033[32m'; YELLOW=$'\033[33m'; RED=$'\033[31m'; GRAY=$'\033[90m'; RESET=$'\033[0m'
[ -t 1 ] || { CYAN=""; GREEN=""; YELLOW=""; RED=""; GRAY=""; RESET=""; }

write_color() { printf '%b%b%b\n' "$2" "$1" "$RESET"; }
write_verbose() { [ "$verbose" = true ] && printf '%s  -> %s%s\n' "$GRAY" "$1" "$RESET"; return 0; }

source_github_path="$workspace_root/.github"

write_color "\n========================================" "$CYAN"
write_color "Update .github.template from Workspace" "$CYAN"
write_color "========================================\n" "$CYAN"

if [ ! -d "$workspace_root" ]; then
    write_color "X Workspace root not found: $workspace_root" "$RED"
    exit 1
fi

write_verbose "Source workspace: $workspace_root"
write_verbose ".github path: $source_github_path"
write_verbose ".github.template path (target): $github_template_path"

if [ ! -d "$source_github_path" ]; then
    write_color "X .github folder not found in workspace: $source_github_path" "$RED"
    exit 1
fi

write_color "Check Found .github folder in workspace\n" "$GREEN"

if [ ! -d "$github_template_path" ]; then
    write_color "X .github.template not found: $github_template_path" "$RED"
    exit 1
fi

write_color "Check Found .github.template folder\n" "$GREEN"

updated=0; skipped=0; errors=0

for folder in instructions prompts; do
    source_folder="$source_github_path/$folder"
    target_folder="$github_template_path/$folder"

    [ -d "$source_folder" ] || { write_verbose "Source folder not found in workspace: $source_folder"; continue; }
    [ -d "$target_folder" ] || { write_verbose "Target folder not found in template: $target_folder"; continue; }

    write_color "\n[Processing: $folder]" "$CYAN"

    # Only iterate TEMPLATE files (non-recursive, matching Get-ChildItem
    # without -Recurse in the original) — never add new files.
    while IFS= read -r -d '' target_file; do
        file_name="$(basename "$target_file")"
        source_file="$source_folder/$file_name"
        size_kb=$(awk -v b="$(stat -c%s "$target_file")" 'BEGIN { printf "%.1f", b/1024 }')

        if [ -f "$source_file" ]; then
            source_hash=$(sha256sum "$source_file" | awk '{print $1}')
            target_hash=$(sha256sum "$target_file" | awk '{print $1}')

            if [ "$source_hash" != "$target_hash" ]; then
                write_color "  Check [UPDATED] $file_name (${size_kb} KB)" "$GREEN"
                write_verbose "  Content differs - updating template from workspace"
                if [ "$dry_run" = false ]; then
                    if cp -f "$source_file" "$target_file"; then updated=$((updated + 1)); else
                        write_color "    ERROR: Failed to update file" "$RED"; errors=$((errors + 1)); fi
                else
                    updated=$((updated + 1))
                fi
            else
                write_verbose "  Check SKIP (unchanged): $file_name"
                skipped=$((skipped + 1))
            fi
        else
            write_verbose "  Check SKIP (missing in workspace): $file_name"
            skipped=$((skipped + 1))
        fi
    done < <(find "$target_folder" -maxdepth 1 -type f -print0)
done

write_color "\n========================================" "$CYAN"
write_color "Update Summary" "$CYAN"
write_color "========================================\n" "$CYAN"

printf '  Updated files: '; write_color "$updated" "$GREEN"
printf '  Skipped files: '; write_color "$skipped" "$GRAY"
printf '  Errors:        '
if [ "$errors" -gt 0 ]; then write_color "$errors" "$RED"; else write_color "$errors" "$GREEN"; fi

if [ "$dry_run" = true ]; then
    write_color "\nDRY RUN - No files were actually modified" "$YELLOW"
fi

total_ops=$((updated + skipped))
write_color "\nUpdate complete: $total_ops total files processed\n" "$GREEN"

exit 0
