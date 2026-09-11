#!/usr/bin/env bash
# Display the command to remove base-only utility packages from the conda
# environment. Bash port of dev-remove-base-only-packages.ps1 (PowerShell).
#
# Analyzes the current conda environment and displays the command to remove
# packages that are typically only needed in the base conda environment but
# not required for project-specific work. You decide when to run the command.
#
# Base-only packages identified:
#   - poetry, poetry-core: Dependency and package management
#   - pipdeptree: Dependency tree visualization
#   - pip-audit: Pip package security auditing
#   - jupyter, jupyterlab: Notebook environments (optional, --include-jupyter)
#   - ipython: Interactive Python shell (optional, --include-ipython)
#
# Requires: conda, jq (for JSON parsing — conda's own --json output).
#
# Usage:
#   ./scripts/bash/dev-remove-base-only-packages.sh [options]
#
# Options:
#   --include-jupyter   Also identify jupyter and jupyterlab packages for removal.
#   --include-ipython    Also identify ipython package for removal.
#   -h, --help            Show this help and exit.
#
# Examples:
#   ./scripts/bash/dev-remove-base-only-packages.sh
#   ./scripts/bash/dev-remove-base-only-packages.sh --include-jupyter --include-ipython
set -uo pipefail

usage() {
    cat <<'EOF'
Display the command to remove base-only utility packages from the conda environment.

Usage:
  ./scripts/bash/dev-remove-base-only-packages.sh [options]

Options:
  --include-jupyter   Also identify jupyter and jupyterlab packages for removal.
  --include-ipython    Also identify ipython package for removal.
  -h, --help            Show this help and exit.

Examples:
  ./scripts/bash/dev-remove-base-only-packages.sh
  ./scripts/bash/dev-remove-base-only-packages.sh --include-jupyter --include-ipython
EOF
}

include_jupyter=false
include_ipython=false

while [ $# -gt 0 ]; do
    case "$1" in
        --include-jupyter) include_jupyter=true; shift ;;
        --include-ipython) include_ipython=true; shift ;;
        -h|--help) usage; exit 0 ;;
        *) echo "Unknown option: $1" >&2; exit 1 ;;
    esac
done

CYAN=$'\033[36m'; GREEN=$'\033[32m'; YELLOW=$'\033[33m'; RED=$'\033[31m'; GRAY=$'\033[90m'; RESET=$'\033[0m'
[ -t 1 ] || { CYAN=""; GREEN=""; YELLOW=""; RED=""; GRAY=""; RESET=""; }

write_step() { printf '\n%s%s %s%s\n' "$CYAN" "${2:-[*]}" "$1" "$RESET"; }
write_success() { printf '%s[OK] %s%s\n' "$GREEN" "$1" "$RESET"; }
write_warning_custom() { printf '%s[WARN] %s%s\n' "$YELLOW" "$1" "$RESET"; }
write_error_custom() { printf '%s[ERROR] %s%s\n' "$RED" "$1" "$RESET" >&2; }
write_info() { printf '%s[INFO] %s%s\n' "$GRAY" "$1" "$RESET"; }

# get_installed_packages: prints one package name per line, sorted+unique.
get_installed_packages() {
    if ! conda list --json 2>/dev/null | jq -r '.[].name' | sort -u; then
        write_error_custom "Failed to retrieve installed packages"
        return 1
    fi
}

echo ""
printf '%s=================================================%s\n' "$CYAN" "$RESET"
printf '%s     Remove Base-Only Packages%s\n' "$CYAN" "$RESET"
printf '%s=================================================%s\n' "$CYAN" "$RESET"
echo ""

if ! command -v jq >/dev/null 2>&1; then
    write_error_custom "jq is required to parse 'conda --json' output but was not found on PATH"
    exit 1
fi

# Step 1: Check conda is available
write_step "Checking conda environment" "[CHECK]"

conda_info_json="$(conda info --json 2>/dev/null || true)"
if [ -z "$conda_info_json" ]; then
    write_error_custom "Conda not found or not accessible"
    write_info "Ensure conda is installed and available in PATH"
    exit 1
fi
active_env="$(printf '%s' "$conda_info_json" | jq -r '.active_prefix' | xargs -I{} basename "{}")"
write_success "Active environment: $active_env"

# Step 2: Define packages to remove
write_step "Identifying packages to remove" "[LIST]"

base_only_packages=(poetry poetry-core pipdeptree pip-audit)

if [ "$include_jupyter" = true ]; then
    base_only_packages+=(jupyter jupyterlab)
fi

if [ "$include_ipython" = true ]; then
    base_only_packages+=(ipython)
fi

joined=$(IFS=', '; echo "${base_only_packages[*]}")
write_info "Target packages: $joined"

# Step 3: Check which packages are installed
write_step "Checking installed packages" "[SCAN]"

installed_packages="$(get_installed_packages)" || exit 1

packages_to_remove=()
for package in "${base_only_packages[@]}"; do
    if grep -qxF "$package" <<<"$installed_packages"; then
        packages_to_remove+=("$package")
    fi
done

if [ "${#packages_to_remove[@]}" -eq 0 ]; then
    write_warning_custom "No base-only packages are currently installed"
    write_info "Nothing to do!"
    exit 0
fi

write_success "Found ${#packages_to_remove[@]} package(s) to remove:"
for pkg in "${packages_to_remove[@]}"; do
    printf '%s  - %s%s\n' "$YELLOW" "$pkg" "$RESET"
done

# Step 4: Display the command to run
write_step "Command to execute" "[COMMAND]"

remove_joined=$(IFS=' '; echo "${packages_to_remove[*]}")
remove_command="conda remove --yes --quiet $remove_joined"
echo ""
printf '%s%s%s\n' "$CYAN" "$remove_command" "$RESET"
echo ""

# Step 5: Summary
printf '%s=================================================%s\n' "$GREEN" "$RESET"
printf '%s     Ready to Run%s\n' "$GREEN" "$RESET"
printf '%s=================================================%s\n' "$GREEN" "$RESET"
echo ""
write_success "Copy and run the command above when ready"
write_info "This will remove ${#packages_to_remove[@]} package(s) from your environment"
echo ""
