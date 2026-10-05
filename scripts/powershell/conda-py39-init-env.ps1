<#
.SYNOPSIS
    Initialize terminal with Conda py39 Python runtime

.DESCRIPTION
    This script:
    1. Activates Conda py39 environment (Python runtime only)
    2. Does NOT activate .venv - Python extension handles that automatically
    3. Provides Node.js (npm, node CLI tools)

.USAGE
    Called automatically by VS Code terminal profile in .vscode/settings.json
    Manual: & './scripts/powershell/conda-py39-init-env.ps1'

.SETUP
    Add to .vscode/settings.json:

    "python.defaultInterpreterPath": "${workspaceFolder}/<project>/.venv/Scripts/python.exe",
    "terminal.integrated.profiles.windows": {
        "PowerShell (Conda + uv)": {
            "source": "PowerShell",
            "args": ["-NoExit", "-Command", "& 'C:\\Users\\203715\\Documents\\Repo\\cr-misc-function\\cr-misc-function\\scripts\\powershell\\conda-py39-init-env.ps1' ; cd '.\\<project>\\'"]
        }
    },
    "terminal.integrated.defaultProfile.windows": "PowerShell (Conda + uv)"

    Replace <project> with your actual project directory name.
    - .venv dependencies available via Python extension's IntelliSense, linting, debugging
    - Terminal has conda + Node.js for CLI tools (npm, node, etc.)
    - Do NOT manually activate .venv in terminal - Python extension manages it
#>

# Activate conda runtime
(C:\Users\203715\AppData\Local\miniconda3\shell\condabin\conda-hook.ps1) ; (conda activate py39)

# Python extension will auto-detect and use .venv from this terminal context

# Confirm status
Write-Host ""
Write-Host "[OK] Conda py39 activated" -ForegroundColor Green
Write-Host ""
python --version
