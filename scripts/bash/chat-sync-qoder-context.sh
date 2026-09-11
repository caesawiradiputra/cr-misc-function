#!/usr/bin/env bash
# Synchronizes project QODER/ context (skills, agents, QODER.md) with the
# global ~/.qoder folder.
#
# Bash port of chat-Sync-QoderContext.ps1 (PowerShell) — for when Qoder
# actually reads global config from the Linux/WSL side of the machine
# ($HOME/.qoder there) rather than native Windows
# (C:\Users\<you>\.qoder, handled by the .ps1 version). Pick whichever
# matches where the IDE process actually runs — see the repo's CLAUDE.md.
#
# It will:
#   - Add missing skills, agents, and config from project QODER/ to global
#   - Update files that differ from project QODER/ (SHA256 compare)
#   - Skip unchanged files
#   - Preserve folder structure (skills/skill-name/SKILL.md, agents/*.md, etc.)
#   - Never touch IDE-managed dirs (cache, extensions, projects, memories, etc.)
set -uo pipefail

usage() {
    cat <<'EOF'
Synchronizes project QODER/ context with the global ~/.qoder folder.

Usage:
  ./scripts/bash/chat-sync-qoder-context.sh [options]

Options:
  --project-path <dir>   Path to the project's QODER folder.
                          Default: auto-detected by walking up from cwd,
                          falling back to this repo's own QODER/.
  --global-path <dir>    Path to the global Qoder config folder.
                          Default: $HOME/.qoder
  --dry-run              Show what would be done without making changes.
  --verbose              Show detailed output of all operations.
  -h, --help             Show this help and exit.

Examples:
  ./scripts/bash/chat-sync-qoder-context.sh
  ./scripts/bash/chat-sync-qoder-context.sh --dry-run
  ./scripts/bash/chat-sync-qoder-context.sh --verbose
  ./scripts/bash/chat-sync-qoder-context.sh \
      --project-path /path/to/project/QODER --global-path "$HOME/.qoder"
EOF
}

project_qoder_path=""
global_qoder_path="$HOME/.qoder"
dry_run=false
verbose=false

while [ $# -gt 0 ]; do
    case "$1" in
        --project-path) project_qoder_path="$2"; shift 2 ;;
        --global-path) global_qoder_path="$2"; shift 2 ;;
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

sync_single_file() {
    local source_file="$1" target_file="$2" display_name="$3"
    local size_kb
    size_kb=$(awk -v b="$(stat -c%s "$source_file")" 'BEGIN { printf "%.1f", b/1024 }')

    if [ -f "$target_file" ]; then
        local source_hash target_hash
        source_hash=$(sha256sum "$source_file" | awk '{print $1}')
        target_hash=$(sha256sum "$target_file" | awk '{print $1}')

        if [ "$source_hash" != "$target_hash" ]; then
            write_color "  [UPDATED] $display_name (${size_kb} KB)" "$GREEN"
            write_verbose "Content differs - updating"
            if [ "$dry_run" = false ]; then
                if cp -f "$source_file" "$target_file"; then echo "Updated"; else write_color "    [ERROR] Failed to update" "$RED"; echo "Error"; fi
            else
                echo "Updated"
            fi
        else
            write_verbose "[SKIP] (unchanged): $display_name"
            echo "Skipped"
        fi
    else
        write_color "  [ADDED] $display_name (${size_kb} KB)" "$GREEN"
        write_verbose "File missing in global - adding"
        if [ "$dry_run" = false ]; then
            if cp -f "$source_file" "$target_file"; then echo "Added"; else write_color "    [ERROR] Failed to add" "$RED"; echo "Error"; fi
        else
            echo "Added"
        fi
    fi
}

# Auto-detect project QODER path if not provided: walk up from cwd.
if [ -z "$project_qoder_path" ]; then
    search_path="$(pwd)"
    while [ "$search_path" != "$(dirname "$search_path")" ]; do
        if [ -d "$search_path/QODER" ]; then
            project_qoder_path="$search_path/QODER"
            break
        fi
        search_path="$(dirname "$search_path")"
    done
fi

# Fall back to this repo's own QODER/ (this script lives at
# <repo>/scripts/bash/, so two levels up is the repo root) — a portable
# stand-in for the .ps1's hardcoded personal Windows path fallback.
if [ -z "$project_qoder_path" ]; then
    repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
    project_qoder_path="$repo_root/QODER"
fi

write_color "\n========================================" "$CYAN"
write_color "Qoder Context Sync" "$CYAN"
write_color "========================================\n" "$CYAN"

if [ ! -d "$project_qoder_path" ]; then
    write_color "X Project QODER/ folder not found: $project_qoder_path" "$RED"
    exit 1
fi

write_verbose "Project QODER/: $project_qoder_path"
write_verbose "Global ~/.qoder/: $global_qoder_path"

if [ ! -d "$global_qoder_path" ]; then
    write_color "Creating global .qoder folder..." "$CYAN"
    [ "$dry_run" = false ] && mkdir -p "$global_qoder_path"
fi

write_color "[OK] Found project QODER/ folder\n" "$GREEN"

added=0; updated=0; skipped=0; errors=0

# ------------------------------------------
# 1. Sync root files (QODER.md)
# ------------------------------------------
write_color "[Processing: root files]" "$CYAN"

source_qoder_md="$project_qoder_path/QODER.md"
target_qoder_md="$global_qoder_path/QODER.md"

if [ -f "$source_qoder_md" ]; then
    result=$(sync_single_file "$source_qoder_md" "$target_qoder_md" "QODER.md" | tail -n1)
    case "$result" in
        Added) added=$((added + 1)) ;;
        Updated) updated=$((updated + 1)) ;;
        Skipped) skipped=$((skipped + 1)) ;;
        Error) errors=$((errors + 1)) ;;
    esac
else
    write_verbose "QODER.md not found in project QODER/ - skipping"
fi

# ------------------------------------------
# 2. Sync folders (skills/, agents/)
# ------------------------------------------
for folder in skills agents; do
    source_folder="$project_qoder_path/$folder"
    target_folder="$global_qoder_path/$folder"

    [ -d "$source_folder" ] || { write_verbose "Source folder not found: $source_folder"; continue; }
    [ -d "$target_folder" ] || { [ "$dry_run" = false ] && mkdir -p "$target_folder"; }

    write_color "[Processing: $folder/]" "$CYAN"

    file_count=$(find "$source_folder" -type f | wc -l)
    if [ "$file_count" -eq 0 ]; then
        write_verbose "No files found in $folder/"
        continue
    fi

    while IFS= read -r -d '' file; do
        relative_path="${file#"$source_folder"/}"
        target_file="$target_folder/$relative_path"
        target_dir="$(dirname "$target_file")"
        [ -d "$target_dir" ] || { [ "$dry_run" = false ] && mkdir -p "$target_dir"; }

        result=$(sync_single_file "$file" "$target_file" "$folder/$relative_path" | tail -n1)
        case "$result" in
            Added) added=$((added + 1)) ;;
            Updated) updated=$((updated + 1)) ;;
            Skipped) skipped=$((skipped + 1)) ;;
            Error) errors=$((errors + 1)) ;;
        esac
    done < <(find "$source_folder" -type f -print0)
done

# ------------------------------------------
# Summary
# ------------------------------------------
write_color "\n========================================" "$CYAN"
write_color "Sync Summary" "$CYAN"
write_color "========================================\n" "$CYAN"

printf '  Added files:   '; write_color "$added" "$GREEN"
printf '  Updated files: '; write_color "$updated" "$YELLOW"
printf '  Skipped files: '; write_color "$skipped" "$GRAY"
printf '  Errors:        '
if [ "$errors" -gt 0 ]; then write_color "$errors" "$RED"; else write_color "$errors" "$GREEN"; fi

if [ "$dry_run" = true ]; then
    write_color "\n[DRY RUN] No files were actually modified" "$YELLOW"
fi

total_ops=$((added + updated + skipped))
write_color "\n[OK] Sync complete: $total_ops total files processed" "$GREEN"
write_color "  Global ~/.qoder/: $global_qoder_path\n" "$CYAN"

exit 0
