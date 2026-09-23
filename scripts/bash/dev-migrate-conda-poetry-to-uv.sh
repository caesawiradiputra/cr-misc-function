#!/usr/bin/env bash
# Validate and prepare environment for Poetry (+ optional Conda) -> uv migration.
#
# Bash port of dev-migrate-conda-poetry-to-uv.ps1 (PowerShell) — for when
# Claude Code + your editor actually run on the Linux/WSL side of the
# machine. Adaptations from the .ps1 version beyond syntax:
#   - Conda is NOT assumed. A WSL checkout usually has no Conda at all, so the
#     generated guides use Linux-specific templates
#     (templates/README_MIGRATION.linux.template.md and
#     README_LEGACY.linux.template.md) where uv installs and manages the
#     Python interpreter itself (`uv python install`). The shared
#     README_*.template.md files stay Windows/Conda-oriented for the .ps1.
#   - Template paths are resolved relative to this script's own location
#     instead of the .ps1's hardcoded C:\Users\203715\... path.
#   - pyproject.toml is parsed with tomllib, not regex, so both PEP 621
#     `dependencies = [...]` lists and classic Poetry
#     `[tool.poetry.dependencies]` tables (caret/tilde constraints converted
#     to PEP 440) produce `uv add` commands. The target Python version is
#     taken from requires-python / tool.poetry.dependencies.python.
#   - The Conda-export step runs whenever Conda is actually active
#     (`command -v conda` + non-empty $CONDA_PREFIX); the .ps1's equivalent
#     guard checks a never-assigned $CondaCommand and is dead code. Without
#     Conda it is skipped and README_LEGACY.md describes a uv-based rollback.
#
# Requires: python3 with tomllib (3.11+). If the system python3 is older
# (e.g. Ubuntu 22.04 ships 3.10), the script falls back to running the
# parser through `uv run --python 3.11`.
#
# It:
#   1. Validates pyproject.toml exists and detects the target Python version
#   2. Creates backup archives in legacy/ (pyproject.toml, *.lock, requirements.txt,
#      Dockerfile, and a Conda export only if Conda is active)
#   3. Extracts dependencies from pyproject.toml for uv add commands
#   4. Generates a migration guide (legacy/README_MIGRATION.md) and a
#      rollback guide (legacy/README_LEGACY.md)
#   5. Optionally removes the Poetry artifacts (poetry.lock and pyproject.toml)
#
# Output files in legacy/:
#   - poetry.lock, *.lock (backups of previous lock files, except uv.lock)
#   - pyproject.poetry.toml (backup of original pyproject.toml)
#   - requirements.txt, Dockerfile (backups, if present)
#   - conda-env.yml, conda-explicit-lock.txt (only if a Conda env was active)
#   - README_LEGACY.md (rollback guide)
#   - README_MIGRATION.md (step-by-step migration guide with uv add commands)
#
# Usage:
#   ./scripts/bash/dev-migrate-conda-poetry-to-uv.sh [options]
#
# Options:
#   --force                          Overwrite existing backup files without prompting.
#   --remove-poetry-artifacts        After backing up, delete poetry.lock and the Poetry
#                                    pyproject.toml from the project root (asks for 'yes'
#                                    unless --force). A file is only deleted when its
#                                    legacy/ backup is byte-identical. Otherwise the guide's
#                                    Step 2 removes them before `uv init`.
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
#   ./scripts/bash/dev-migrate-conda-poetry-to-uv.sh --project-root ~/repo/other-app/other-app
#
# After running this script, follow the migration guide in legacy/README_MIGRATION.md:
#   1. uv python install <version>
#   2. Remove the Poetry pyproject.toml/poetry.lock, then: uv init --bare && uv venv
#   3. uv add [dependencies] (auto-generated commands in the guide)
#   4. Copy ruff.toml / mypy.ini (targets set to <version>), update
#      .vscode/settings.json (.venv/bin/python)
#   5. Verify: uv run python --version, then commit
set -uo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/../.." && pwd)"

## Print the leading comment block (everything after the shebang up to the
## first non-comment line), so --help never drifts from the header.
usage() {
    awk 'NR == 1 { next } /^#/ { sub(/^# ?/, ""); print; next } { exit }' "${BASH_SOURCE[0]}"
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
        --project-root)
            [ $# -ge 2 ] || fail "--project-root requires a path"
            project_root="$2"; shift 2 ;;
        -h|--help) usage; exit 0 ;;
        *) fail "Unknown option: $1" ;;
    esac
done

# ----------------------------------------------------------------------------
# PYTHON HELPER (pyproject parsing + template rendering)
# ----------------------------------------------------------------------------

## tomllib is stdlib only from Python 3.11; fall back to a uv-managed 3.11.
py_cmd=()
if command -v python3 >/dev/null 2>&1 && python3 -c 'import tomllib' 2>/dev/null; then
    py_cmd=(python3)
elif command -v uv >/dev/null 2>&1; then
    py_cmd=(uv run --quiet --no-project --python 3.11 python)
else
    fail "Need python3 >= 3.11 (for tomllib) or uv on PATH to parse pyproject.toml"
fi

# py_helper <command> [args...]
#   python-version <pyproject|"">       -> prints X.Y (defaults to 3.11)
#   uv-add-section <pyproject|"">       -> prints the Markdown for guide Step 3
#   render <template> <output> <flags>  -> substitutes PH_* env vars into
#                                          {Placeholders} and keeps only the
#                                          <!-- IF:flag --> blocks listed in
#                                          <flags> (comma-separated)
py_helper() {
    "${py_cmd[@]}" - "$@" <<'PY'
import os
import re
import sys
import tomllib

DEFAULT_PYTHON = "3.11"
DEFAULT_DEV_TOOLS = ["mypy", "ruff"]
_VERSION = re.compile(r"(\d+)(?:\.(\d+))?(?:\.(\d+))?")
_PEP621_PAREN = re.compile(r"^([A-Za-z0-9._-]+(?:\[[^\]]*\])?)\s*\((.+)\)\s*(;.*)?$")
_NAME = re.compile(r"^([A-Za-z0-9._-]+)")


def load(path):
    if not path or not os.path.isfile(path):
        return None
    with open(path, "rb") as f:
        return tomllib.load(f)


def poetry_table(data, *keys):
    node = data.get("tool", {}).get("poetry", {})
    for key in keys:
        node = node.get(key, {}) if isinstance(node, dict) else {}
    return node if isinstance(node, dict) else {}


def python_version(data):
    """Lowest X.Y allowed by requires-python (or Poetry's python constraint)."""
    spec = None
    if data:
        spec = data.get("project", {}).get("requires-python") or poetry_table(
            data, "dependencies"
        ).get("python")
    if isinstance(spec, str):
        for part in spec.replace("||", ",").split(","):
            part = part.strip()
            if part.startswith(("<", "!")):
                continue
            m = _VERSION.search(part)
            if m and m.group(2) is not None:
                return f"{m.group(1)}.{m.group(2)}"
    return DEFAULT_PYTHON


def _bump(version, level):
    """Upper bound for a caret/tilde range: increment component `level`."""
    m = _VERSION.fullmatch(version)
    if not m:
        return None
    parts = [int(p) for p in m.groups() if p is not None]
    upper = parts[: level + 1]
    upper[-1] += 1
    return f">={version},<{'.'.join(map(str, upper))}"


def poetry_constraint(spec):
    """Convert a Poetry constraint (^, ~, bare version, *) to PEP 440."""
    out = []
    for part in spec.split(","):
        part = part.strip()
        if part in ("", "*"):
            continue
        if part.startswith("^"):
            v = part[1:].strip()
            m = _VERSION.fullmatch(v)
            nums = [int(p) for p in m.groups() if p is not None] if m else []
            level = next((i for i, n in enumerate(nums) if n != 0), len(nums) - 1)
            out.append(_bump(v, level) or part)
        elif part.startswith("~") and not part.startswith("~="):
            v = part[1:].strip()
            m = _VERSION.fullmatch(v)
            level = 0 if m and m.group(2) is None else 1
            out.append(_bump(v, level) or part)
        elif part[0].isdigit():
            out.append("==" + part)
        else:
            out.append(part)
    return ",".join(out)


def from_table(table, manual):
    deps = []
    for name, value in table.items():
        if name == "python":
            continue
        if isinstance(value, str):
            deps.append(name + poetry_constraint(value))
        elif isinstance(value, dict) and "version" in value:
            extras = value.get("extras") or []
            extra = f"[{','.join(extras)}]" if extras else ""
            deps.append(name + extra + poetry_constraint(str(value["version"])))
        else:
            ## git/path/url sources and multiple-constraint lists need a human.
            manual.append(f"{name} = {value!r}")
    return deps


def from_pep621(entries):
    deps = []
    for entry in entries:
        entry = entry.strip()
        m = _PEP621_PAREN.match(entry)
        if m:
            entry = m.group(1) + m.group(2).strip() + (m.group(3) or "")
        deps.append(entry)
    return deps


def collect(data):
    manual = []
    project = data.get("project", {})
    if project.get("dependencies"):
        main = from_pep621(project["dependencies"])
    else:
        main = from_table(poetry_table(data, "dependencies"), manual)

    groups = data.get("dependency-groups", {})
    optional = project.get("optional-dependencies", {})
    if isinstance(groups.get("dev"), list) and groups["dev"]:
        dev = from_pep621(g for g in groups["dev"] if isinstance(g, str))
    elif optional.get("dev"):
        dev = from_pep621(optional["dev"])
    elif poetry_table(data, "group", "dev", "dependencies"):
        dev = from_table(poetry_table(data, "group", "dev", "dependencies"), manual)
    else:
        dev = from_table(poetry_table(data, "dev-dependencies"), manual)

    ## Always include mypy and ruff in dev tools (deduplicated by package name).
    names = {_NAME.match(d).group(1).lower() for d in dev if _NAME.match(d)}
    dev += [tool for tool in DEFAULT_DEV_TOOLS if tool not in names]
    return main, dev, manual


def shell_quote(dep):
    ## Anything beyond a bare name contains shell syntax (<, >, [, *, ;, ...).
    return dep if re.fullmatch(r"[A-Za-z0-9._-]+", dep) else "'" + dep.replace("'", "") + "'"


def uv_add_section(data):
    if not data:
        return (
            "> pyproject.toml was not found, so no dependencies could be extracted.\n"
            "> Add them manually with `uv add <package>` and `uv add --dev <package>`."
        )
    main, dev, manual = collect(data)
    lines = []
    if main:
        lines.append("uv add " + " ".join(shell_quote(d) for d in main))
    lines.append("uv add --dev " + " ".join(shell_quote(d) for d in dev))
    text = (
        "Run these commands (adjust versions as needed):\n\n```bash\n"
        + "\n".join(lines)
        + "\n```"
    )
    if manual:
        text += (
            "\n\n> **Manual:** these dependencies use a git/path/url source or a"
            " multi-constraint list and were not converted. Add each one yourself:\n>\n"
            + "\n".join(f"> - `{m}`" for m in manual)
        )
    return text


def render(template, output, flags):
    with open(template, encoding="utf-8") as f:
        content = f.read()
    enabled = {f for f in flags.split(",") if f}
    content = re.sub(
        r"<!-- IF:([\w-]+) -->\n?(.*?)<!-- ENDIF:\1 -->\n?",
        lambda m: m.group(2) if m.group(1) in enabled else "",
        content,
        flags=re.DOTALL,
    )
    for key, value in os.environ.items():
        if key.startswith("PH_"):
            content = content.replace("{" + key[3:] + "}", value)
    with open(output, "w", encoding="utf-8") as f:
        f.write(content)


cmd, args = sys.argv[1], sys.argv[2:]
if cmd == "python-version":
    print(python_version(load(args[0])))
elif cmd == "uv-add-section":
    print(uv_add_section(load(args[0])))
elif cmd == "render":
    render(*args)
else:
    sys.exit(f"unknown helper command: {cmd}")
PY
}

# ----------------------------------------------------------------------------
# README GENERATION
# ----------------------------------------------------------------------------

# generate_legacy_readme <legacy-readme-path> <project-name> <python-version>
generate_legacy_readme() {
    local legacy_readme_path="$1" project_name="$2" python_version="$3"
    local template_file="$repo_root/templates/README_LEGACY.linux.template.md"
    local legacy_dir flags="no-conda"

    if [ ! -f "$template_file" ]; then
        printf '%s[!] Template not found: %s%s\n' "$YELLOW" "$template_file" "$RESET"
        return 1
    fi

    legacy_dir="$(dirname "$legacy_readme_path")"
    if [ -f "$legacy_dir/conda-env.yml" ] || [ -f "$legacy_dir/conda-explicit-lock.txt" ]; then
        flags="conda"
    fi

    PH_ProjectName="$project_name" \
    PH_Timestamp="$(date '+%Y-%m-%d %H:%M:%S')" \
    PH_PythonVersion="$python_version" \
        py_helper render "$template_file" "$legacy_readme_path" "$flags"
}

# generate_migration_readme <project-folder-name> <migration-readme-path> <pyproject-or-empty> <python-version>
generate_migration_readme() {
    local project_folder_name="$1" migration_readme_path="$2" source_toml="$3" python_version="$4"
    local template_file="$repo_root/templates/README_MIGRATION.linux.template.md"
    local uv_add_section flags=""

    ## mypy 2.x runs on / type-checks Python >= 3.10 only; flag older targets
    ## so the guide explains why `uv add --dev mypy` resolves an old mypy.
    if [ "${python_version%%.*}" -eq 3 ] && [ "${python_version#*.}" -lt 10 ]; then
        flags="old-mypy"
    fi

    if [ ! -f "$template_file" ]; then
        printf '%s[!] Template not found: %s%s\n' "$YELLOW" "$template_file" "$RESET"
        return 1
    fi

    if ! uv_add_section="$(py_helper uv-add-section "$source_toml")"; then
        printf '%s[!] Warning: Could not parse dependencies from %s%s\n' "$YELLOW" "$source_toml" "$RESET"
        uv_add_section="> Dependency parsing failed — add them manually with \`uv add <package>\`."
    fi

    PH_ProjectName="$project_folder_name" \
    PH_Timestamp="$(date '+%Y-%m-%d %H:%M:%S')" \
    PH_PythonVersion="$python_version" \
    PH_UvAddDependencies="$uv_add_section" \
    PH_TemplatesDir="$repo_root/templates" \
    PH_RuffTarget="py${python_version//./}" \
        py_helper render "$template_file" "$migration_readme_path" "$flags"
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
cd "$project_root" || fail "Cannot enter project root: $project_root"

write_section "Migration Utility - Poetry (+ Conda) -> uv"
echo "Project root: $project_root"

# ----------------------------------------------------------------------------
# DETECT PROJECT FOLDER NAME + SOURCE PYPROJECT + TARGET PYTHON
# ----------------------------------------------------------------------------
project_folder_name="$(basename "$project_root")"
echo "[+] Detected project folder: $project_folder_name"

legacy_path="$project_root/legacy"
pyproject_path="$project_root/pyproject.toml"
pyproject_backup_path="$legacy_path/pyproject.poetry.toml"

## Prefer the live pyproject.toml; fall back to the legacy/ backup when the
## Poetry file was already removed (e.g. re-running after guide Step 2).
source_toml=""
if [ -f "$pyproject_path" ]; then
    source_toml="$pyproject_path"
elif [ -f "$pyproject_backup_path" ]; then
    printf '%s[~] pyproject.toml not in project root - using legacy/pyproject.poetry.toml%s\n' "$YELLOW" "$RESET"
    source_toml="$pyproject_backup_path"
else
    printf '%s[!] pyproject.toml not found - guide will have a placeholder for dependencies%s\n' "$YELLOW" "$RESET"
fi

python_version="$(py_helper python-version "$source_toml")" || python_version="3.11"
echo "[+] Target Python version: $python_version"

if [ -n "$source_toml" ] && grep -q "poetry" "$source_toml"; then
    printf '%s[!] Poetry configuration detected.%s\n' "$YELLOW" "$RESET"
fi

# ----------------------------------------------------------------------------
# MIGRATION GUIDE GENERATION ONLY MODE
# ----------------------------------------------------------------------------
if [ "$generate_migration_guide_only" = true ]; then
    echo ""
    printf '%s[*] Generating migration guide only...%s\n' "$CYAN" "$RESET"

    mkdir -p "$legacy_path"
    generate_migration_readme "$project_folder_name" "$legacy_path/README_MIGRATION.md" "$source_toml" "$python_version" \
        || fail "Could not generate README_MIGRATION.md"

    printf '%s[+] Generated migration guide: legacy/README_MIGRATION.md%s\n' "$GREEN" "$RESET"
    echo ""
    printf '%sNext: Open legacy/README_MIGRATION.md and follow the steps%s\n' "$GREEN" "$RESET"
    exit 0
fi

# ----------------------------------------------------------------------------
# BACKUP TO LEGACY/ (STEP 1)
# ----------------------------------------------------------------------------
write_section "Creating Legacy Backup"

if [ ! -d "$legacy_path" ]; then
    mkdir -p "$legacy_path"
    echo "[+] Created legacy folder"
fi

## Only a Poetry pyproject.toml is backed up: re-running with --force after
## `uv init` must not overwrite the Poetry backup with the new uv file.
if [ -f "$pyproject_path" ] && ! grep -q "poetry" "$pyproject_path"; then
    echo "  [~] Skipped pyproject.toml: no Poetry configuration (already migrated?)"
else
    backup_file "$pyproject_path" "$pyproject_backup_path"
fi

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

# Export Conda environment only if one is actually active. On a typical WSL
# checkout there is no Conda, and the uv-based guides don't need it.
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
else
    echo "  [~] No active Conda environment - skipping Conda export (uv manages Python)"
fi

# ----------------------------------------------------------------------------
# GENERATE README FILES (STEP 2 & 3)
# ----------------------------------------------------------------------------
write_section "Generating README Files"

# --- STEP 2: Generate README_LEGACY.md (Restoration & Rollback) ---
generate_legacy_readme "$legacy_path/README_LEGACY.md" "$project_folder_name" "$python_version" \
    && echo "[+] Created legacy/README_LEGACY.md"

# --- STEP 3: Parse dependencies from the BACKED-UP pyproject.toml and generate the migration readme ---
[ -f "$pyproject_backup_path" ] || printf '%s[!] Backed-up pyproject.toml not found - migration guide will have placeholder%s\n' "$YELLOW" "$RESET"
backup_toml=""
[ -f "$pyproject_backup_path" ] && backup_toml="$pyproject_backup_path"
generate_migration_readme "$project_folder_name" "$legacy_path/README_MIGRATION.md" "$backup_toml" "$python_version" \
    && echo "[+] Created legacy/README_MIGRATION.md"

write_section "Migration Check Complete"

echo "Archive created at: $legacy_path"
echo ""
printf '%s[DOCS] Documentation files:%s\n' "$CYAN" "$RESET"
echo "   - legacy/README_LEGACY.md        - Rollback & restoration instructions"
echo "   - legacy/README_MIGRATION.md     - Step-by-step migration guide"
echo ""
printf '%sNext steps:%s\n' "$GREEN" "$RESET"
echo "  1. Open: legacy/README_MIGRATION.md"
echo "  2. Follow the 8-step migration walkthrough (uv installs Python $python_version - no Conda needed)"
echo "  3. When done, commit your changes:"
echo "     git add pyproject.toml uv.lock ruff.toml mypy.ini && git add -f .python-version"
echo '     git commit -m "chore: migrate from Poetry to uv"'
echo ""

# ----------------------------------------------------------------------------
# REMOVE POETRY ARTIFACTS (optional, --remove-poetry-artifacts)
# ----------------------------------------------------------------------------

# remove_poetry_artifact <file> <backup>
## Deletes <file> only when <backup> is byte-identical to it. backup_file keeps
## an existing backup unless --force, so a stale backup must never become the
## only copy of a file that changed since.
remove_poetry_artifact() {
    local file="$1" backup="$2"
    local name
    name="$(basename "$file")"

    if [ ! -f "$file" ]; then
        echo "  [~] Not present: $name"
        return 0
    fi
    if ! cmp -s "$file" "$backup"; then
        printf '%s  [!] Kept %s: legacy/%s is missing or differs (re-run with --force to refresh the backup)%s\n' \
            "$YELLOW" "$name" "$(basename "$backup")" "$RESET"
        return 1
    fi
    rm -f "$file"
    echo "  [-] Removed: $name (backup: legacy/$(basename "$backup"))"
}

if [ "$remove_poetry_artifacts" = true ]; then
    write_section "Removing Poetry Artifacts"

    proceed=true
    if [ "$force" = false ]; then
        if [ -t 0 ]; then
            read -r -p "Delete pyproject.toml and poetry.lock from $project_root? Type 'yes' to confirm (Enter cancels): " answer
            [ "$answer" = "yes" ] || proceed=false
        else
            printf '%s[!] No terminal to confirm on - pass --force to remove without a prompt%s\n' "$YELLOW" "$RESET"
            proceed=false
        fi
    fi

    if [ "$proceed" = true ]; then
        if [ -f "$pyproject_path" ] && ! grep -q "poetry" "$pyproject_path"; then
            printf '%s  [!] Kept pyproject.toml: it has no Poetry configuration (already migrated?)%s\n' "$YELLOW" "$RESET"
        else
            remove_poetry_artifact "$pyproject_path" "$pyproject_backup_path"
        fi
        remove_poetry_artifact "$project_root/poetry.lock" "$legacy_path/poetry.lock"
        echo ""
        printf '%sUse legacy/README_LEGACY.md to restore if needed%s\n' "$YELLOW" "$RESET"
    else
        echo "[~] Removal cancelled - Poetry files left in place"
    fi
    echo ""
fi
