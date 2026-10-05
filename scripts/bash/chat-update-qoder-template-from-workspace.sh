#!/usr/bin/env bash
# Updates QODER/ template with changes from the global ~/.qoder/ folder.
#
# Bash port of chat-update-qoder-template-from-workspace.ps1 (PowerShell).
# Compares the global ~/.qoder/ folder (where Qoder actively reads skills,
# agents, and QODER.md) with the canonical template at this repo's own
# QODER/ folder. Unlike chat-update-claude-template-from-workspace.sh, this
# one iterates the SOURCE (global) files and both adds new ones and updates
# existing ones in the template — matching the original .ps1 exactly.
#
# This is the reverse of chat-sync-qoder-context.sh, which pushes the
# template OUT to the global ~/.qoder folder.
set -uo pipefail

usage() {
    cat <<'EOF'
Updates QODER/ template with changes from the global ~/.qoder/ folder.
Adds new files AND updates existing ones (unlike the Claude-template
equivalent, which only updates).

Usage:
  ./scripts/bash/chat-update-qoder-template-from-workspace.sh [options]

Options:
  --source-path <dir>    Path to the source .qoder/ folder.
                          Default: $HOME/.qoder (global). Override to pull
                          from a specific project's .qoder/ folder instead.
  --template-path <dir>  Path to the canonical QODER/ template folder.
                          Default: this repo's own QODER/ folder.
  --dry-run              Show what would be done without making changes.
  --verbose              Show detailed output of all operations.
  -h, --help             Show this help and exit.

Examples:
  ./scripts/bash/chat-update-qoder-template-from-workspace.sh
  ./scripts/bash/chat-update-qoder-template-from-workspace.sh --dry-run
  ./scripts/bash/chat-update-qoder-template-from-workspace.sh --source-path /path/to/project/.qoder --verbose
  ./scripts/bash/chat-update-qoder-template-from-workspace.sh --template-path /custom/path/QODER --dry-run
EOF
}

source_path="$HOME/.qoder"
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
qoder_template_path="$repo_root/QODER"
dry_run=false
verbose=false

while [ $# -gt 0 ]; do
    case "$1" in
        --source-path) source_path="$2"; shift 2 ;;
        --template-path) qoder_template_path="$2"; shift 2 ;;
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

workspace_qoder_path="$source_path"

write_color "\n========================================" "$CYAN"
write_color "Update QODER Template from Global" "$CYAN"
write_color "========================================\n" "$CYAN"

if [ ! -d "$workspace_qoder_path" ]; then
    write_color "X Source .qoder/ folder not found: $workspace_qoder_path" "$RED"
    exit 1
fi

write_color "[OK] Found source .qoder/ folder\n" "$GREEN"

if [ ! -d "$qoder_template_path" ]; then
    write_color "X QODER/ template not found: $qoder_template_path" "$RED"
    exit 1
fi

write_color "[OK] Found QODER/ template folder\n" "$GREEN"

write_verbose "Source global .qoder/:    $workspace_qoder_path"
write_verbose "Target template QODER/:   $qoder_template_path"

skip_sync=false
if [ "$(cd "$workspace_qoder_path" && pwd)" = "$(cd "$qoder_template_path" && pwd)" ]; then
    write_color "! Source and target are the same folder - skipping sync." "$YELLOW"
    skip_sync=true
fi

added=0; updated=0; skipped=0; errors=0

if [ "$skip_sync" = false ]; then
    # ------------------------------------------
    # 1. QODER.md - check from global to template
    # ------------------------------------------
    write_color "[Processing: root files]" "$CYAN"

    source_qoder_md="$workspace_qoder_path/QODER.md"
    template_qoder_md="$qoder_template_path/QODER.md"

    if [ -f "$source_qoder_md" ]; then
        size_kb=$(awk -v b="$(stat -c%s "$source_qoder_md")" 'BEGIN { printf "%.1f", b/1024 }')
        if [ -f "$template_qoder_md" ]; then
            source_hash=$(sha256sum "$source_qoder_md" | awk '{print $1}')
            target_hash=$(sha256sum "$template_qoder_md" | awk '{print $1}')

            if [ "$source_hash" != "$target_hash" ]; then
                write_color "  [UPDATED] QODER.md (${size_kb} KB)" "$GREEN"
                write_verbose "Content differs - updating template from global"
                if [ "$dry_run" = false ]; then
                    if cp -f "$source_qoder_md" "$template_qoder_md"; then updated=$((updated + 1)); else
                        write_color "    [ERROR] Failed to update QODER.md" "$RED"; errors=$((errors + 1)); fi
                else
                    updated=$((updated + 1))
                fi
            else
                write_verbose "  [SKIP] (unchanged): QODER.md"
                skipped=$((skipped + 1))
            fi
        else
            write_color "  [ADDED] QODER.md (${size_kb} KB)" "$GREEN"
            write_verbose "New file in global - adding to template"
            if [ "$dry_run" = false ]; then
                if cp -f "$source_qoder_md" "$template_qoder_md"; then added=$((added + 1)); else
                    write_color "    [ERROR] Failed to add QODER.md" "$RED"; errors=$((errors + 1)); fi
            else
                added=$((added + 1))
            fi
        fi
    else
        write_verbose "QODER.md not in global - skipping"
    fi

    # ------------------------------------------
    # 2. skills/ and agents/ - iterate global files, check against template
    # ------------------------------------------
    for folder in skills agents; do
        source_folder="$workspace_qoder_path/$folder"
        target_folder="$qoder_template_path/$folder"

        [ -d "$source_folder" ] || { write_verbose "Folder not in global: $folder/ - skipping"; continue; }

        write_color "\n[Processing: $folder/]" "$CYAN"

        file_count=$(find "$source_folder" -type f | wc -l)
        if [ "$file_count" -eq 0 ]; then
            write_verbose "No files found in global $folder/"
            continue
        fi

        while IFS= read -r -d '' file; do
            relative_path="${file#"$source_folder"/}"
            target_file="$target_folder/$relative_path"
            size_kb=$(awk -v b="$(stat -c%s "$file")" 'BEGIN { printf "%.1f", b/1024 }')

            if [ -f "$target_file" ]; then
                source_hash=$(sha256sum "$file" | awk '{print $1}')
                target_hash=$(sha256sum "$target_file" | awk '{print $1}')

                if [ "$source_hash" != "$target_hash" ]; then
                    write_color "  [UPDATED] $relative_path (${size_kb} KB)" "$GREEN"
                    write_verbose "Content differs - updating template from global"
                    if [ "$dry_run" = false ]; then
                        if cp -f "$file" "$target_file"; then updated=$((updated + 1)); else
                            write_color "    [ERROR] Failed to update $relative_path" "$RED"; errors=$((errors + 1)); fi
                    else
                        updated=$((updated + 1))
                    fi
                else
                    write_verbose "  [SKIP] (unchanged): $relative_path"
                    skipped=$((skipped + 1))
                fi
            else
                write_color "  [ADDED] $relative_path (${size_kb} KB)" "$GREEN"
                write_verbose "New file in global - adding to template"
                if [ "$dry_run" = false ]; then
                    target_dir="$(dirname "$target_file")"
                    [ -d "$target_dir" ] || mkdir -p "$target_dir"
                    if cp -f "$file" "$target_file"; then added=$((added + 1)); else
                        write_color "    [ERROR] Failed to add $relative_path" "$RED"; errors=$((errors + 1)); fi
                else
                    added=$((added + 1))
                fi
            fi
        done < <(find "$source_folder" -type f -print0)
    done
fi

# ------------------------------------------
# Summary
# ------------------------------------------
write_color "\n========================================" "$CYAN"
write_color "Update Summary" "$CYAN"
write_color "========================================\n" "$CYAN"

printf '  Added files:   '; write_color "$added" "$GREEN"
printf '  Updated files: '; write_color "$updated" "$GREEN"
printf '  Skipped files: '; write_color "$skipped" "$GRAY"
printf '  Errors:        '
if [ "$errors" -gt 0 ]; then write_color "$errors" "$RED"; else write_color "$errors" "$GREEN"; fi

if [ "$dry_run" = true ]; then
    write_color "\n[DRY RUN] No files were actually modified" "$YELLOW"
fi

total_ops=$((added + updated + skipped))
write_color "\n[OK] Update complete: $total_ops total files processed" "$GREEN"
write_color "  Template QODER/: $qoder_template_path\n" "$CYAN"

exit 0
