#!/usr/bin/env bash
# Updates CLAUDE/ template with changes from a workspace CLAUDE/ folder.
#
# Bash port of chat-update-claude-template-from-workspace.ps1 (PowerShell).
# Compares a workspace's CLAUDE/ folder with the canonical template at this
# repo's own CLAUDE/ folder. Only updates existing template files (never
# adds new ones) and skips files missing from the workspace or unchanged.
#
# Use this to propagate improvements made in another project's CLAUDE/
# folder back to the canonical template source in this repo. This is the
# reverse of chat-sync-claude-context.sh, which pushes the template OUT to
# the global ~/.claude folder.
set -uo pipefail

usage() {
    cat <<'EOF'
Updates CLAUDE/ template with changes from a workspace CLAUDE/ folder.
Only updates files already present in the template — never adds new ones.

Usage:
  ./scripts/bash/chat-update-claude-template-from-workspace.sh [options]

Options:
  --workspace-root <dir>  Workspace root where CLAUDE/ folder exists (or is
                           found by walking up from it). Default: cwd.
  --template-path <dir>   Path to the canonical CLAUDE/ template folder.
                           Default: this repo's own CLAUDE/ folder.
  --dry-run               Show what would be done without making changes.
  --verbose               Show detailed output of all operations.
  -h, --help              Show this help and exit.

Examples:
  ./scripts/bash/chat-update-claude-template-from-workspace.sh
  ./scripts/bash/chat-update-claude-template-from-workspace.sh --dry-run
  ./scripts/bash/chat-update-claude-template-from-workspace.sh --workspace-root /path/to/workspace --verbose
  ./scripts/bash/chat-update-claude-template-from-workspace.sh --template-path /custom/path/CLAUDE --dry-run
EOF
}

workspace_root="$(pwd)"
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
claude_template_path="$repo_root/CLAUDE"
global_commands_path="$HOME/.claude/commands"
dry_run=false
verbose=false

while [ $# -gt 0 ]; do
    case "$1" in
        --workspace-root) workspace_root="$2"; shift 2 ;;
        --template-path) claude_template_path="$2"; shift 2 ;;
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

# Auto-detect workspace CLAUDE/ path by walking up from workspace_root.
workspace_claude_path=""
search_path="$workspace_root"
while [ "$search_path" != "$(dirname "$search_path")" ]; do
    if [ -d "$search_path/CLAUDE" ]; then
        workspace_claude_path="$search_path/CLAUDE"
        break
    fi
    search_path="$(dirname "$search_path")"
done

write_color "\n========================================" "$CYAN"
write_color "Update CLAUDE Template from Workspace" "$CYAN"
write_color "========================================\n" "$CYAN"

if [ -z "$workspace_claude_path" ]; then
    write_color "X CLAUDE/ folder not found in or above: $workspace_root" "$RED"
    exit 1
fi

write_color "[OK] Found workspace CLAUDE/ folder\n" "$GREEN"

if [ ! -d "$claude_template_path" ]; then
    write_color "X CLAUDE/ template not found: $claude_template_path" "$RED"
    exit 1
fi

write_color "[OK] Found CLAUDE/ template folder\n" "$GREEN"

write_verbose "Source workspace CLAUDE/: $workspace_claude_path"
write_verbose "Target template CLAUDE/:  $claude_template_path"

skip_sync=false
if [ "$(cd "$workspace_claude_path" && pwd)" = "$(cd "$claude_template_path" && pwd)" ]; then
    write_color "! Source and target are the same folder - skipping sync." "$YELLOW"
    skip_sync=true
fi

updated=0; skipped=0; errors=0

if [ "$skip_sync" = false ]; then
    # ------------------------------------------
    # 1. Update root CLAUDE.md (only if it already exists in template)
    # ------------------------------------------
    write_color "[Processing: root files]" "$CYAN"

    template_claude_md="$claude_template_path/CLAUDE.md"
    workspace_claude_md="$workspace_claude_path/CLAUDE.md"

    if [ -f "$template_claude_md" ]; then
        if [ -f "$workspace_claude_md" ]; then
            source_hash=$(sha256sum "$workspace_claude_md" | awk '{print $1}')
            target_hash=$(sha256sum "$template_claude_md" | awk '{print $1}')

            if [ "$source_hash" != "$target_hash" ]; then
                size_kb=$(awk -v b="$(stat -c%s "$workspace_claude_md")" 'BEGIN { printf "%.1f", b/1024 }')
                write_color "  [UPDATED] CLAUDE.md (${size_kb} KB)" "$GREEN"
                write_verbose "Content differs - updating template from workspace"
                if [ "$dry_run" = false ]; then
                    if cp -f "$workspace_claude_md" "$template_claude_md"; then updated=$((updated + 1)); else
                        write_color "    [ERROR] Failed to update CLAUDE.md" "$RED"; errors=$((errors + 1)); fi
                else
                    updated=$((updated + 1))
                fi
            else
                write_verbose "  [SKIP] (unchanged): CLAUDE.md"
                skipped=$((skipped + 1))
            fi
        else
            write_verbose "  [SKIP] (missing in workspace): CLAUDE.md"
            skipped=$((skipped + 1))
        fi
    else
        write_verbose "CLAUDE.md not in template - skipping"
    fi

    # ------------------------------------------
    # 2. Update commands/ folder (existing template files only)
    # ------------------------------------------
    source_folder="$workspace_claude_path/commands"
    target_folder="$claude_template_path/commands"

    if [ -d "$target_folder" ] && [ -d "$source_folder" ]; then
        write_color "\n[Processing: commands/]" "$CYAN"

        file_count=$(find "$target_folder" -type f | wc -l)
        if [ "$file_count" -eq 0 ]; then
            write_verbose "No files found in template commands/"
        else
            while IFS= read -r -d '' target_file; do
                relative_path="${target_file#"$target_folder"/}"
                source_file="$source_folder/$relative_path"
                size_kb=$(awk -v b="$(stat -c%s "$target_file")" 'BEGIN { printf "%.1f", b/1024 }')

                if [ -f "$source_file" ]; then
                    source_hash=$(sha256sum "$source_file" | awk '{print $1}')
                    target_hash=$(sha256sum "$target_file" | awk '{print $1}')

                    if [ "$source_hash" != "$target_hash" ]; then
                        write_color "  [UPDATED] $relative_path (${size_kb} KB)" "$GREEN"
                        write_verbose "Content differs - updating template from workspace"
                        if [ "$dry_run" = false ]; then
                            if cp -f "$source_file" "$target_file"; then updated=$((updated + 1)); else
                                write_color "    [ERROR] Failed to update $relative_path" "$RED"; errors=$((errors + 1)); fi
                        else
                            updated=$((updated + 1))
                        fi
                    else
                        write_verbose "  [SKIP] (unchanged): $relative_path"
                        skipped=$((skipped + 1))
                    fi
                else
                    write_verbose "  [SKIP] (missing in workspace): $relative_path"
                    skipped=$((skipped + 1))
                fi
            done < <(find "$target_folder" -type f -print0)
        fi
    elif [ ! -d "$target_folder" ]; then
        write_verbose "Folder not in template: commands - skipping"
    else
        write_verbose "Folder not in workspace: commands - skipping"
    fi
fi

# ------------------------------------------
# Summary
# ------------------------------------------
write_color "\n========================================" "$CYAN"
write_color "Update Summary" "$CYAN"
write_color "========================================\n" "$CYAN"

printf '  Updated files: '; write_color "$updated" "$GREEN"
printf '  Skipped files: '; write_color "$skipped" "$GRAY"
printf '  Errors:        '
if [ "$errors" -gt 0 ]; then write_color "$errors" "$RED"; else write_color "$errors" "$GREEN"; fi

if [ "$dry_run" = true ]; then
    write_color "\n[DRY RUN] No files were actually modified" "$YELLOW"
fi

total_ops=$((updated + skipped))
write_color "\n[OK] Update complete: $total_ops total files processed" "$GREEN"
write_color "  Template CLAUDE/: $claude_template_path\n" "$CYAN"

# ------------------------------------------
# Global vs Template drift check
# ------------------------------------------
if [ -d "$global_commands_path" ]; then
    template_commands_path="$claude_template_path/commands"
    only_in_global=()

    while IFS= read -r -d '' global_file; do
        rel_path="${global_file#"$global_commands_path"/}"
        if [ ! -f "$template_commands_path/$rel_path" ]; then
            only_in_global+=("$rel_path")
        fi
    done < <(find "$global_commands_path" -type f -print0)

    if [ "${#only_in_global[@]}" -gt 0 ]; then
        write_color "========================================" "$YELLOW"
        write_color "Global-only commands (not in template)" "$YELLOW"
        write_color "========================================\n" "$YELLOW"
        for name in "${only_in_global[@]}"; do
            write_color "  [GLOBAL ONLY] $name" "$YELLOW"
        done
        write_color "\n  These exist in ~/.claude/commands/ but not in the template." "$GRAY"
        write_color "  Copy them to CLAUDE/commands/ if they should be part of the template.\n" "$GRAY"
    else
        write_color "[OK] Global commands are in sync with template (no drift detected)\n" "$GREEN"
    fi
fi

exit 0
