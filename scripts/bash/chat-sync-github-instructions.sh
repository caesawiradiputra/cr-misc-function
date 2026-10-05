#!/usr/bin/env bash
# Synchronizes .github instructions and prompts with .github.template.
#
# Bash port of chat-sync-github-instructions.ps1 (PowerShell). Compares
# .github/{instructions,prompts,agents,skills} in a target workspace with
# the canonical .github.template/{instructions,prompts,agents,skills} —
# expected to live one level above this repo (the multi-root workspace
# umbrella), shared across every project workspace under it. Adds files
# missing in .github and replaces ones that differ from the template; if
# .github.template doesn't exist here, that's normal (this canonical folder
# is machine-specific) and the script exits cleanly.
set -uo pipefail

usage() {
    cat <<'EOF'
Synchronizes .github instructions/prompts/agents/skills with .github.template.

Usage:
  ./scripts/bash/chat-sync-github-instructions.sh [options]

Options:
  --target-root <dir>   Workspace root where .github/ should be synced.
                         Default: parent directory of cwd.
  --template-path <dir> Path to the canonical .github.template folder.
                         Default: this repo's umbrella dir (one level above
                         the repo root)/.github.template
  --dry-run             Show what would be done without making changes.
  --verbose              Show detailed output of all operations.
  -h, --help             Show this help and exit.

Examples:
  ./scripts/bash/chat-sync-github-instructions.sh
  ./scripts/bash/chat-sync-github-instructions.sh --dry-run
  ./scripts/bash/chat-sync-github-instructions.sh --target-root /path/to/workspace --verbose
EOF
}

target_github_root="$(dirname "$(pwd)")"
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
github_template_path="$(dirname "$repo_root")/.github.template"
dry_run=false
verbose=false

while [ $# -gt 0 ]; do
    case "$1" in
        --target-root) target_github_root="$2"; shift 2 ;;
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

github_path="$target_github_root/.github"

write_color "\n========================================" "$CYAN"
write_color "GitHub Instructions & Prompts Sync" "$CYAN"
write_color "========================================\n" "$CYAN"

if [ ! -d "$target_github_root" ]; then
    write_color "X Target workspace root not found: $target_github_root" "$RED"
    exit 1
fi

write_verbose "Target workspace: $target_github_root"
write_verbose ".github path: $github_path"
write_verbose ".github.template path (reference): $github_template_path"

if [ ! -d "$github_template_path" ]; then
    write_color "O .github.template not found - skipping sync" "$YELLOW"
    write_color "  (This is normal if .github.template doesn't exist in this workspace)\n" "$YELLOW"
    exit 0
fi

write_color "Check Found .github.template folder\n" "$GREEN"

if [ ! -d "$github_path" ]; then
    write_color "Creating .github folder..." "$CYAN"
    [ "$dry_run" = false ] && mkdir -p "$github_path"
fi

added=0; updated=0; skipped=0; errors=0

for folder in instructions prompts agents skills; do
    source_folder="$github_template_path/$folder"
    target_folder="$github_path/$folder"

    [ -d "$source_folder" ] || { write_verbose "Source folder not found: $source_folder"; continue; }
    [ -d "$target_folder" ] || { [ "$dry_run" = false ] && mkdir -p "$target_folder"; }

    write_color "\n[Processing: $folder]" "$CYAN"

    while IFS= read -r -d '' file; do
        relative_path="${file#"$source_folder"/}"
        target_file="$target_folder/$relative_path"
        target_dir="$(dirname "$target_file")"
        [ -d "$target_dir" ] || { [ "$dry_run" = false ] && mkdir -p "$target_dir"; }

        file_name="$(basename "$file")"
        size_kb=$(awk -v b="$(stat -c%s "$file")" 'BEGIN { printf "%.1f", b/1024 }')

        if [ -f "$target_file" ]; then
            source_hash=$(sha256sum "$file" | awk '{print $1}')
            target_hash=$(sha256sum "$target_file" | awk '{print $1}')

            if [ "$source_hash" != "$target_hash" ]; then
                write_color "  Check [UPDATED] $file_name (${size_kb} KB)" "$GREEN"
                write_verbose "  Content differs - updating from template"
                if [ "$dry_run" = false ]; then
                    if cp -f "$file" "$target_file"; then updated=$((updated + 1)); else
                        write_color "    ERROR: Failed to update file" "$RED"; errors=$((errors + 1)); fi
                else
                    updated=$((updated + 1))
                fi
            else
                write_verbose "  Check SKIP (unchanged): $file_name"
                skipped=$((skipped + 1))
            fi
        else
            write_color "  Check [ADDED] $file_name (${size_kb} KB)" "$GREEN"
            write_verbose "  File missing in .github - adding from template"
            if [ "$dry_run" = false ]; then
                if cp -f "$file" "$target_file"; then added=$((added + 1)); else
                    write_color "    ERROR: Failed to add file" "$RED"; errors=$((errors + 1)); fi
            else
                added=$((added + 1))
            fi
        fi
    done < <(find "$source_folder" -type f -print0)
done

write_color "\n========================================" "$CYAN"
write_color "Sync Summary" "$CYAN"
write_color "========================================\n" "$CYAN"

printf '  Added files:  '; write_color "$added" "$GREEN"
printf '  Updated files: '; write_color "$updated" "$YELLOW"
printf '  Skipped files: '; write_color "$skipped" "$GRAY"
printf '  Errors:        '
if [ "$errors" -gt 0 ]; then write_color "$errors" "$RED"; else write_color "$errors" "$GREEN"; fi

if [ "$dry_run" = true ]; then
    write_color "\nDRY RUN - No files were actually modified" "$YELLOW"
fi

total_ops=$((added + updated + skipped))
write_color "\nSync complete: $total_ops total files processed\n" "$GREEN"

exit 0
