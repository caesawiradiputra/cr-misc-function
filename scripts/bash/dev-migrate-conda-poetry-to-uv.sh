#!/usr/bin/env bash
# Validate and prepare environment for Poetry + Conda -> uv migration.
#
# Bash port of dev-migrate-conda-poetry-to-uv.ps1 (PowerShell) — for when
# Claude Code + your editor actually run on the Linux/WSL side of the
# machine. Two adaptations from the .ps1 version beyond syntax:
#   - Template paths (templates/README_LEGACY.template.md and
#     README_MIGRATION.template.md) are resolved relative to this script's
#     own location instead of the .ps1's hardcoded
#     C:\Users\203715\Documents\Repo\cr-misc-function\cr-misc-function\templates\...
#   - The Conda-export step now actually runs: the .ps1 guards it with
#     `if ($CondaCommand -and $CondaPrefix)`, but $CondaCommand is never
#     assigned anywhere in that script, so that condition is always false
#     and the block is dead code. This port uses the evidently-intended
#     check instead: `command -v conda` + a non-empty $CONDA_PREFIX.
#
# Requires: python3 (only for the same regex-based dependency-list
# extraction the .ps1 does via `-match` with a DOTALL-style pattern — no
# TOML library is used, this mirrors the original regex approach exactly).
#
# This script performs pre-migration checks and creates a safe rollback
# archive for migrating from Poetry/Conda to the uv package manager.
#
# It:
#   1. Validates pyproject.toml exists and parses the Python version requirement
#   2. Checks Conda environment status
#   3. Creates backup archives in legacy/ (poetry.lock, pyproject.toml, Conda exports)
#   4. Extracts dependencies from pyproject.toml for uv add commands
#   5. Generates a migration guide (legacy/README_MIGRATION.md) and a
#      rollback guide (legacy/README_LEGACY.md)
#   6. Optionally removes Poetry artifacts (poetry.lock and pyproject.toml)
#
# Output files in legacy/:
#   - poetry.lock, *.lock (backups of previous lock files, except uv.lock)
#   - pyproject.poetry.toml (backup of original pyproject.toml)
#   - requirements.txt, Dockerfile (backups, if present)
#   - conda-env.yml, conda-explicit-lock.txt (Conda environment export, if active)
#   - README_LEGACY.md (rollback guide)
#   - README_MIGRATION.md (step-by-step migration guide with uv add commands)
#
# Usage:
#   ./scripts/bash/dev-migrate-conda-poetry-to-uv.sh [options]
#
# Options:
#   --force                          Overwrite existing backup files without prompting.
#   --remove-poetry-artifacts        Delete poetry.lock and pyproject.toml (after
#                                    backing them up to legacy/). Permanent — backups
#                                    are created first, so restore from legacy/ if needed.
#   --generate-migration-guide-only  Only (re)generate legacy/README_MIGRATION.md,
#                                    skipping validation/backup. Does not require
#                                    pyproject.toml or an active Conda environment.
#   --project-root <path>            Path to project root containing pyproject.toml.
#                                    Default: current working directory.
#   -h, --help                       Show this help and exit.
#
# Examples:
#   ./scripts/bash/dev-migrate-conda-poetry-to-uv.sh
#   ./scripts/bash/dev-migrate-conda-poetry-to-uv.sh --force
#   ./scripts/bash/dev-migrate-conda-poetry-to-uv.sh --remove-poetry-artifacts
#   ./scripts/bash/dev-migrate-conda-poetry-to-uv.sh --remove-poetry-artifacts --force
#   ./scripts/bash/dev-migrate-conda-poetry-to-uv.sh --generate-migration-guide-only
#   ./scripts/bash/dev-migrate-conda-poetry-to-uv.sh --project-root /projects/other-app
#
# After running this script, follow the migration guide in legacy/README_MIGRATION.md:
#   1. Activate Conda (py311 or py39)
#   2. Run: uv init && uv venv
#   3. Run: uv add [dependencies] (auto-generated commands in the guide)
#   4. Update .vscode/settings.json (template in the guide)
#   5. Verify: python --version & uv --version
set -uo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/../.." && pwd)"

usage() {
    sed -n '2,58p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
}

CYAN=$'\033[36m'; GREEN=$'\033[32m'; YELLOW=$'\033[33m'; RED=$'\033[31m'; RESET=$'\033[0m'
[ -t 1 ] || { CYAN=""; GREEN=""; YELLOW=""; RED=""; RESET=""; }

write_section() {
    echo ""
    printf '%s===============================================%s\n' "$CYAN" "$RESET"
    printf '%s%s%s\n' "$CYAN" "$1" "$RESET"
    printf '%s===============================================%s\n' "$CYAN" "$RESET"
}

fail() {
    printf '%s[ERROR] %s%s\n' "$RED" "$1" "$RESET" >&2
    exit 1
}

# ----------------------------------------------------------------------------
# ARGUMENT PARSING
# ----------------------------------------------------------------------------
force=false
remove_poetry_artifacts=false
generate_migration_guide_only=false
project_root=""

while [ $# -gt 0 ]; do
    case "$1" in
        --force) force=true; shift ;;
        --remove-poetry-artifacts) remove_poetry_artifacts=true; shift ;;
        --generate-migration-guide-only) generate_migration_guide_only=true; shift ;;
        --project-root) project_root="$2"; shift 2 ;;
        -h|--help) usage; exit 0 ;;
        *) fail "Unknown option: $1" ;;
    esac
done

# ----------------------------------------------------------------------------
# DEPENDENCY-STRING FORMATTING
#   Input:  pandas (==2.2.3)  or  xgboost>=3.0.5,<4.0.0  or  pandas==2.2.3
#   Output: pandas==2.2.3     or  'xgboost>=3.0.5,<4.0.0' (quoted if it has a comma/space)
# ----------------------------------------------------------------------------
format_dependency() {
    local dep="$1"
    dep="${dep//\"/}"
    dep="${dep//\'/}"
    # shellcheck disable=SC2001  # trim via sed for portability of leading/trailing spaces
    dep="$(printf '%s' "$dep" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"

    if [[ "$dep" =~ ^([a-zA-Z0-9._-]+)[[:space:]]*\((.+)\)$ ]]; then
        local pkg_name="${BASH_REMATCH[1]}"
        local version_spec="${BASH_REMATCH[2]}"
        version_spec="$(printf '%s' "$version_spec" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"
        if [[ "$version_spec" =~ [,[:space:]] ]]; then
            printf "'%s%s'" "$pkg_name" "$version_spec"
        else
            printf '%s%s' "$pkg_name" "$version_spec"
        fi
    elif [[ "$dep" =~ ^([a-zA-Z0-9._-]+)([\<\>=!].*)$ ]]; then
        local pkg_name="${BASH_REMATCH[1]}"
        local version_spec="${BASH_REMATCH[2]}"
        if [[ "$version_spec" == *,* ]]; then
            printf "'%s%s'" "$pkg_name" "$version_spec"
        else
            printf '%s%s' "$pkg_name" "$version_spec"
        fi
    else
        printf '%s' "$dep"
    fi
}

# extract_toml_list_section <pyproject-file> <mode: deps|dev-deps>
# Prints one raw dependency entry per line (quotes stripped, trimmed), mirroring
# the PowerShell regex extraction (same two patterns, same comma-before-newline
# split so a version spec like ">=3.0.5,<4.0.0" isn't split mid-spec).
extract_toml_list_section() {
    local file="$1" mode="$2"
    python3 - "$file" "$mode" <<'PY'
import re
import sys

path, mode = sys.argv[1], sys.argv[2]
with open(path, encoding="utf-8") as f:
    content = f.read()

if mode == "deps":
    m = re.search(r"dependencies\s*=\s*\[(.*?)\]", content, re.DOTALL)
else:
    m = re.search(
        r"\[project\.optional-dependencies\].*?dev\s*=\s*\[(.*?)\]", content, re.DOTALL
    )

if not m:
    sys.exit(0)

for entry in re.split(r",\s*\n", m.group(1)):
    dep = entry.replace('"', "").replace("'", "").strip()
    if dep:
        print(dep)
PY
}

# ----------------------------------------------------------------------------
# README GENERATION
# ----------------------------------------------------------------------------

# generate_legacy_readme <legacy-readme-path> <project-name>
generate_legacy_readme() {
    local legacy_readme_path="$1" project_name="$2"
    local template_file="$repo_root/templates/README_LEGACY.template.md"

    if [ ! -f "$template_file" ]; then
        printf '%s[!] Template not found: %s%s\n' "$YELLOW" "$template_file" "$RESET"
        return 0
    fi

    local timestamp
    timestamp="$(date '+%Y-%m-%d %H:%M:%S')"
    sed -e "s/{ProjectName}/$project_name/g" -e "s/{Timestamp}/$timestamp/g" \
        "$template_file" > "$legacy_readme_path"
}

# generate_migration_readme <project-folder-name> <migration-readme-path> <deps-file> <dev-deps-file>
# deps-file/dev-deps-file: one dependency string per line (may be empty files).
generate_migration_readme() {
    local project_folder_name="$1" migration_readme_path="$2" deps_file="$3" dev_deps_file="$4"
    local template_file="$repo_root/templates/README_MIGRATION.template.md"

    if [ ! -f "$template_file" ]; then
        printf '%s[!] Template not found: %s%s\n' "$YELLOW" "$template_file" "$RESET"
        return 0
    fi

    local uv_add_lines=()

    if [ -s "$deps_file" ]; then
        local formatted_deps=()
        while IFS= read -r dep; do
            [ -n "$dep" ] && formatted_deps+=("$(format_dependency "$dep")")
        done < "$deps_file"
        if [ "${#formatted_deps[@]}" -gt 0 ]; then
            uv_add_lines+=("uv add $(IFS=' '; echo "${formatted_deps[*]}")")
        fi
    fi

    # Always include mypy and ruff in dev tools (deduplicated, order-preserving).
    local all_dev_deps=()
    declare -A seen_dev=()
    if [ -f "$dev_deps_file" ]; then
        while IFS= read -r dep; do
            [ -n "$dep" ] || continue
            if [ -z "${seen_dev[$dep]:-}" ]; then
                all_dev_deps+=("$dep")
                seen_dev[$dep]=1
            fi
        done < "$dev_deps_file"
    fi
    for extra in mypy ruff; do
        if [ -z "${seen_dev[$extra]:-}" ]; then
            all_dev_deps+=("$extra")
            seen_dev[$extra]=1
        fi
    done

    if [ "${#all_dev_deps[@]}" -gt 0 ]; then
        local formatted_dev_deps=()
        for dep in "${all_dev_deps[@]}"; do
            formatted_dev_deps+=("$(format_dependency "$dep")")
        done
        uv_add_lines+=("uv add --dev $(IFS=' '; echo "${formatted_dev_deps[*]}")")
    fi

    local uv_add_section=""
    if [ "${#uv_add_lines[@]}" -gt 0 ]; then
        uv_add_section=$(
            printf '\nRun these commands (or adjust versions as needed):\n\n```bash\n'
            printf '%s\n' "${uv_add_lines[@]}"
            printf '```\n\n> **Config files:** Copy `mypy.ini` and `ruff.toml` from the shared templates folder into your project root.\n> Template source: `cr-misc-function/templates/mypy.ini` and `cr-misc-function/templates/ruff.toml`\n'
        )
    fi

    local timestamp
    timestamp="$(date '+%Y-%m-%d %H:%M:%S')"

    # Substitute placeholders. {UvAddDependencies} may contain '&' and
    # newlines, so it's swapped in via a temp file + awk rather than sed.
    local tmp_content
    tmp_content="$(sed -e "s/{ProjectName}/$project_folder_name/g" -e "s/{Timestamp}/$timestamp/g" "$template_file")"
    awk -v repl="$uv_add_section" '{ gsub(/\{UvAddDependencies\}/, repl); print }' <<<"$tmp_content" > "$migration_readme_path"
}

# backup_file <source> <destination>
backup_file() {
    local source="$1" destination="$2"
    [ -f "$source" ] || return 0

    if [ -f "$destination" ] && [ "$force" = false ]; then
        printf '  [~] Skipped existing: %s\n' "$(basename "$destination")"
        return 0
    fi

    cp -f "$source" "$destination"
    printf '  [+] Backed up: %s\n' "$(basename "$destination")"
}

# ----------------------------------------------------------------------------
# RESOLVE PROJECT ROOT
# ----------------------------------------------------------------------------
if [ -z "$project_root" ]; then
    project_root="$(pwd)"
fi

[ -d "$project_root" ] || fail "Project root does not exist: $project_root"
project_root="$(cd "$project_root" && pwd)"
cd "$project_root"

write_section "Migration Utility - Poetry + Conda -> uv"
echo "Project root: $project_root"

# ----------------------------------------------------------------------------
# DETECT PROJECT FOLDER NAME
# ----------------------------------------------------------------------------
project_folder_name="$(basename "$project_root")"
echo "[+] Detected project folder: $project_folder_name"

# ----------------------------------------------------------------------------
# MIGRATION GUIDE GENERATION ONLY MODE
# ----------------------------------------------------------------------------
if [ "$generate_migration_guide_only" = true ]; then
    echo ""
    printf '%s[*] Generating migration guide only...%s\n' "$CYAN" "$RESET"

    pyproject_path="$project_root/pyproject.toml"
    pyproject_backup_path="$project_root/legacy/pyproject.poetry.toml"

    source_toml=""
    if [ -f "$pyproject_path" ]; then
        source_toml="$pyproject_path"
    elif [ -f "$pyproject_backup_path" ]; then
        printf '%s[~] Using backed-up pyproject.toml from legacy/%s\n' "$YELLOW" "$RESET"
        source_toml="$pyproject_backup_path"
    else
        printf '%s[!] pyproject.toml not found - will generate guide with placeholder%s\n' "$YELLOW" "$RESET"
    fi

    deps_file="$(mktemp)"
    dev_deps_file="$(mktemp)"
    trap 'rm -f "$deps_file" "$dev_deps_file"' EXIT

    if [ -n "$source_toml" ]; then
        if ! extract_toml_list_section "$source_toml" deps > "$deps_file"; then
            printf '%s[!] Warning: Could not parse dependencies from pyproject.toml%s\n' "$YELLOW" "$RESET"
        fi
        extract_toml_list_section "$source_toml" dev-deps > "$dev_deps_file" || true
    fi

    legacy_path="$project_root/legacy"
    mkdir -p "$legacy_path"

    migration_guide_path="$legacy_path/README_MIGRATION.md"
    generate_migration_readme "$project_folder_name" "$migration_guide_path" "$deps_file" "$dev_deps_file"

    printf '%s[+] Generated migration guide: README_MIGRATION.md%s\n' "$GREEN" "$RESET"
    echo ""
    printf '%sNext: Open legacy/README_MIGRATION.md and follow the steps%s\n' "$GREEN" "$RESET"
    exit 0
fi

# ----------------------------------------------------------------------------
# VALIDATE PYPROJECT.TOML
# ----------------------------------------------------------------------------
pyproject_path="$project_root/pyproject.toml"

if [ ! -f "$pyproject_path" ]; then
    printf '%s[!] pyproject.toml not found in project root - skipping dependency parsing%s\n' "$YELLOW" "$RESET"
else
    echo "[+] Found pyproject.toml"

    requires_python="$(grep -oP '(?<=requires-python\s=\s")[^"]*' "$pyproject_path" 2>/dev/null | head -n1 || true)"
    if [ -n "$requires_python" ]; then
        echo "[+] requires-python: $requires_python"
    else
        printf '%s[!] requires-python not found in pyproject.toml%s\n' "$YELLOW" "$RESET"
    fi

    if grep -q "poetry.core" "$pyproject_path"; then
        printf '%s[!] Poetry backend detected.%s\n' "$YELLOW" "$RESET"
    fi
fi

# ----------------------------------------------------------------------------
# BACKUP TO LEGACY/ (STEP 1)
# ----------------------------------------------------------------------------
write_section "Creating Legacy Backup"

legacy_path="$project_root/legacy"

if [ ! -d "$legacy_path" ]; then
    mkdir -p "$legacy_path"
    echo "[+] Created legacy folder"
fi

backup_file "$project_root/pyproject.toml" "$legacy_path/pyproject.poetry.toml"

requirements_path="$project_root/requirements.txt"
[ -f "$requirements_path" ] && backup_file "$requirements_path" "$legacy_path/requirements.txt"

# Backup any *.lock files except uv.lock (poetry.lock, etc.)
while IFS= read -r -d '' lock_file; do
    lock_name="$(basename "$lock_file")"
    [ "$lock_name" = "uv.lock" ] && continue
    backup_file "$lock_file" "$legacy_path/$lock_name"
done < <(find "$project_root" -maxdepth 1 -type f -name "*.lock" -print0)

dockerfile_path="$project_root/Dockerfile"
[ -f "$dockerfile_path" ] && backup_file "$dockerfile_path" "$legacy_path/Dockerfile"

# Export Conda environment (if active). The .ps1 guards this with
# `$CondaCommand -and $CondaPrefix`, but $CondaCommand is never assigned in
# that script so the block is unreachable dead code there — this port uses
# the evidently-intended check instead.
if command -v conda >/dev/null 2>&1 && [ -n "${CONDA_PREFIX:-}" ]; then
    echo ""
    echo "Exporting Conda environment..."

    history_file="$legacy_path/conda-env.yml"
    explicit_file="$legacy_path/conda-explicit-lock.txt"

    if [ ! -f "$history_file" ] || [ "$force" = true ]; then
        if conda env export --from-history > "$history_file" 2>/dev/null; then
            echo "  [+] Exported: conda-env.yml"
        else
            printf '%s  [!] Failed to export conda-env%s\n' "$YELLOW" "$RESET"
            rm -f "$history_file"
        fi
    else
        echo "  [~] Skipped existing: conda-env.yml"
    fi

    if [ ! -f "$explicit_file" ] || [ "$force" = true ]; then
        if conda list --explicit > "$explicit_file" 2>/dev/null; then
            echo "  [+] Exported: conda-explicit-lock.txt"
        else
            printf '%s  [!] Failed to export conda lock%s\n' "$YELLOW" "$RESET"
            rm -f "$explicit_file"
        fi
    else
        echo "  [~] Skipped existing: conda-explicit-lock.txt"
    fi
fi

# ----------------------------------------------------------------------------
# GENERATE README FILES (STEP 2 & 3)
# ----------------------------------------------------------------------------
write_section "Generating README Files"

# --- STEP 2: Generate README_LEGACY.md (Restoration & Rollback) ---
legacy_readme_path="$legacy_path/README_LEGACY.md"
generate_legacy_readme "$legacy_readme_path" "$project_folder_name"
echo "[+] Created legacy/README_LEGACY.md"

# --- STEP 3: Parse dependencies from the BACKED-UP pyproject.toml and generate the migration readme ---
pyproject_backup_path="$legacy_path/pyproject.poetry.toml"

deps_file="$(mktemp)"
dev_deps_file="$(mktemp)"
trap 'rm -f "$deps_file" "$dev_deps_file"' EXIT

if [ -f "$pyproject_backup_path" ]; then
    if ! extract_toml_list_section "$pyproject_backup_path" deps > "$deps_file"; then
        printf '%s[!] Warning: Could not parse dependencies from backed-up pyproject.toml%s\n' "$YELLOW" "$RESET"
    fi
    extract_toml_list_section "$pyproject_backup_path" dev-deps > "$dev_deps_file" || true
else
    printf '%s[!] Backed-up pyproject.toml not found - migration guide will have placeholder%s\n' "$YELLOW" "$RESET"
fi

migration_readme_path="$legacy_path/README_MIGRATION.md"
generate_migration_readme "$project_folder_name" "$migration_readme_path" "$deps_file" "$dev_deps_file"
echo "[+] Created legacy/README_MIGRATION.md"

write_section "Migration Check Complete"

echo "Archive created at: $legacy_path"
echo ""
printf '%s[DOCS] Documentation files:%s\n' "$CYAN" "$RESET"
echo "   - legacy/README_LEGACY.md        - Rollback & restoration instructions"
echo "   - legacy/README_MIGRATION.md     - Step-by-step migration guide"
echo ""
printf '%sNext steps:%s\n' "$GREEN" "$RESET"
echo "  1. Open: legacy/README_MIGRATION.md"
echo "  2. Follow the 7-step migration walkthrough"
echo "  3. Copy config templates to your project root (if not already present):"
printf '%s       cr-misc-function/templates/mypy.ini  -> <project>/mypy.ini%s\n' "$YELLOW" "$RESET"
printf '%s       cr-misc-function/templates/ruff.toml -> <project>/ruff.toml%s\n' "$YELLOW" "$RESET"
echo "  4. When done, commit your changes:"
echo "     git add pyproject.toml uv.lock .vscode/settings.json mypy.ini ruff.toml"
echo 'git commit -m "chore: migrate from Poetry to uv"'
echo ""

if [ "$remove_poetry_artifacts" = true ]; then
    printf '%s[BACKUP] Backups created (in legacy/):%s\n' "$YELLOW" "$RESET"
    echo "     - poetry.lock -> Backed up automatically"
    echo "     - pyproject.toml -> Backed up as pyproject.poetry.toml"
    echo ""
    printf '%sUse README_LEGACY.md to restore if needed%s\n' "$YELLOW" "$RESET"
    echo ""
fi
