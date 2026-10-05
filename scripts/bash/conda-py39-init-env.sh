#!/usr/bin/env bash
# Initialize terminal with Conda py39 Python runtime.
#
# Bash port of conda-py39-init-env.ps1 (PowerShell) — for when Claude Code
# + your editor's integrated terminal actually run on the Linux/WSL side of
# the machine, where conda is installed under $HOME (e.g. $HOME/miniconda3)
# rather than the native-Windows path the .ps1 version hardcodes
# (C:\Users\<user>\AppData\Local\miniconda3\...).
#
# This script:
#   1. Activates the conda `py39` environment (Python runtime only)
#   2. Does NOT activate .venv — the Python extension handles that automatically
#
# IMPORTANT: `conda activate` only affects the *current* shell, so this must
# be sourced, not executed as a subprocess:
#   source ./scripts/bash/conda-py39-init-env.sh
#
# Setup (VS Code terminal profile, .vscode/settings.json):
#   "python.defaultInterpreterPath": "${workspaceFolder}/<project>/.venv/bin/python",
#   "terminal.integrated.profiles.linux": {
#       "bash (Conda + uv)": {
#           "path": "bash",
#           "args": ["-c", "source '/home/<you>/repo/cr-misc-function/cr-misc-function/scripts/bash/conda-py39-init-env.sh'; cd './<project>/'; exec bash"]
#       }
#   },
#   "terminal.integrated.defaultProfile.linux": "bash (Conda + uv)"
#
#   Replace <project> with your actual project directory name.
#   - .venv dependencies available via the Python extension's IntelliSense, linting, debugging
#   - Terminal has conda for CLI tools
#   - Do NOT manually activate .venv in the terminal — the Python extension manages it

# Locate conda's shell hook: prefer an already-initialized `conda` on PATH,
# else fall back to the common install locations.
if command -v conda >/dev/null 2>&1; then
    conda_base="$(conda info --base 2>/dev/null)"
else
    conda_base=""
    for candidate in "$HOME/miniconda3" "$HOME/anaconda3" "/opt/conda"; do
        if [ -f "$candidate/etc/profile.d/conda.sh" ]; then
            conda_base="$candidate"
            break
        fi
    done
fi

if [ -z "$conda_base" ] || [ ! -f "$conda_base/etc/profile.d/conda.sh" ]; then
    echo "[ERROR] Could not find a conda installation (checked PATH, \$HOME/miniconda3, \$HOME/anaconda3, /opt/conda)." >&2
    return 1 2>/dev/null || exit 1
fi

# shellcheck disable=SC1091
source "$conda_base/etc/profile.d/conda.sh"
conda activate py39

# Python extension will auto-detect and use .venv from this terminal context

# Confirm status
echo ""
if [ -t 1 ]; then
    printf '\033[32m[OK] Conda py39 activated\033[0m\n'
else
    echo "[OK] Conda py39 activated"
fi
echo ""
python --version
