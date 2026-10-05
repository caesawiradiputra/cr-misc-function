#!/usr/bin/env bash
# Syntax-validate every bash port in this directory (bash -n, no execution).
# Bash port of modules/_validate.ps1 (PowerShell), which parses the .ps1
# files with the PowerShell AST parser instead.
set -uo pipefail

base="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
files=(
    "$base/modules/git-script-helpers.sh"
    "$base/git-clean-branches.sh"
    "$base/git-reset-branches.sh"
    "$base/git-check-sync-set-dev.sh"
    "$base/git-create-clean-branch.sh"
    "$base/git-rebase-branch.sh"
    "$base/git-init-feature.sh"
    "$base/git-workflow.sh"
)

all_ok=true
for f in "${files[@]}"; do
    name="$(basename "$f")"
    if error_output=$(bash -n "$f" 2>&1); then
        echo "[OK] $name"
    else
        all_ok=false
        echo "[FAIL] $name"
        echo "$error_output" | sed 's/^/  /'
    fi
done

if [ "$all_ok" = true ]; then
    echo -e "\nAll ${#files[@]} files passed syntax validation."
else
    exit 1
fi
