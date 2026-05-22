---
description: "Windows PowerShell environment configuration - terminal commands, syntax, and best practices for this machine"
applyTo: "**"
---

# Windows PowerShell Environment Instructions

**Critical:** This machine runs **Windows** with **PowerShell** as the primary shell. Commands executed by Copilot should use PowerShell syntax, or cmd.exe when simpler or PowerShell equivalent doesn't exist. Never use Linux/bash commands.

## Environment Details

- **Operating System**: Windows
- **Terminal/Shell**: PowerShell 5.1+ (primary), cmd.exe (secondary when simpler)
- **Python Environment**: Virtual environment (`.venv/`) in project root
- **Package Manager**: uv (Python project, dependency, and venv management)
- **Git**: Git Bash or native Windows Git

## Critical Rules for Command Execution

### ✅ DO: Use PowerShell Commands

When executing commands via `run_in_terminal`, **always use PowerShell syntax**:

```powershell
# Navigate directories
Set-Location "c:\path\to\folder"
Push-Location "c:\path"
Pop-Location

# List files
Get-ChildItem
Get-ChildItem -Filter "*.py"
Get-ChildItem -Recurse

# Check if file/folder exists
Test-Path "c:\path\to\file"

# Create directories
New-Item -ItemType Directory -Path "c:\path\to\folder" -Force

# Copy files
Copy-Item -Path "source" -Destination "dest" -Recurse

# Remove files/folders
Remove-Item -Path "file.txt"
Remove-Item -Path "folder" -Recurse -Force

# Display file contents
Get-Content "file.txt"
Get-Content "file.txt" | Select-Object -First 20

# Search for text in files
Select-String -Path "*.py" -Pattern "search_term"
Get-ChildItem -Recurse | Select-String -Pattern "search_term"

# Environment variables
$env:PATH
$env:PYTHONPATH
[Environment]::GetEnvironmentVariable("VAR_NAME")
```

### Alternative: Use cmd.exe (Command Prompt)

Use **cmd.exe** when:
- The cmd.exe command is **simpler** than the PowerShell equivalent
- The **PowerShell equivalent doesn't exist** or is overly complex
- You need a **basic, straightforward operation** (file copy, directory navigation)

**cmd.exe commands:**

```cmd
REM Navigate directories
cd C:\path\to\folder
pushd C:\path
popd

REM List files
dir
dir *.py
dir /s

REM Check if file/folder exists
if exist "C:\path\to\file" (echo File exists)

REM Create directories
mkdir C:\path\to\folder

REM Copy files
xcopy source dest /s /e

REM Remove files/folders
del file.txt
rmdir /s /q folder

REM Display file contents
type file.txt

REM Search for text in files
findstr "pattern" file.txt
findstr /s "pattern" *.py

REM Environment variables
echo %PATH%
echo %PYTHONPATH%
set VAR=value
```

**When to use cmd.exe over PowerShell:**
- `dir` is simpler than `Get-ChildItem` for basic file listing
- `cd` is simpler than `Set-Location`
- `type` is simpler than `Get-Content` for viewing files
- Some legacy batch scripts require cmd.exe

**But prefer PowerShell when:**
- Complex piping or object manipulation is needed
- Advanced filtering or transformations are required
- Cross-platform compatibility is important

### ❌ DON'T: Use Linux/Bash Commands

Never use these bash/Linux commands on this Windows machine:

```bash
# ❌ WRONG - Don't use these
cd /path/to/folder          # Use: Set-Location instead
ls -la                      # Use: Get-ChildItem instead
cat file.txt                # Use: Get-Content instead
grep "pattern" file.txt     # Use: Select-String instead
mkdir -p folder/subfolder   # Use: New-Item with -Force instead
rm -rf folder               # Use: Remove-Item -Recurse -Force instead
cp -r source dest           # Use: Copy-Item -Recurse instead
find . -name "*.py"         # Use: Get-ChildItem -Recurse -Filter instead
export VAR=value            # Use: $env:VAR = value instead
which python                # Use: Get-Command python instead
chmod +x script.sh          # Not needed on Windows
./script.sh                 # Use: PowerShell script or .bat instead
```

## Common Command Translations: Bash → PowerShell (or cmd.exe)

| Task | Bash | PowerShell | cmd.exe |
|------|------|-----------|---------|
| **Navigate** | `cd /path/to/dir` | `Set-Location "C:\path\to\dir"` | `cd C:\path\to\dir` |
| **List files** | `ls -la` | `Get-ChildItem -Force` | `dir` |
| **List recursively** | `find . -name "*.py"` | `Get-ChildItem -Recurse -Filter "*.py"` | `dir /s *.py` |
| **Show file** | `cat file.txt` | `Get-Content file.txt` | `type file.txt` |
| **Search text** | `grep "pattern" file.txt` | `Select-String -Path file.txt -Pattern "pattern"` | `findstr "pattern" file.txt` |
| **Check exists** | `test -f file.txt` | `Test-Path "file.txt"` | `if exist "file.txt"` |
| **Create dir** | `mkdir -p a/b/c` | `New-Item -ItemType Directory -Path "a\b\c" -Force` | `mkdir a\b\c` |
| **Copy file** | `cp -r src dest` | `Copy-Item -Path src -Destination dest -Recurse` | `xcopy src dest /s /e` |
| **Delete file** | `rm file.txt` | `Remove-Item -Path file.txt` | `del file.txt` |
| **Delete dir** | `rm -rf folder` | `Remove-Item -Path folder -Recurse -Force` | `rmdir /s /q folder` |
| **Environment var** | `export VAR=value` | `$env:VAR = "value"` | `set VAR=value` |
| **Get env var** | `echo $PATH` | `$env:PATH` | `echo %PATH%` |
| **Which command** | `which python` | `Get-Command python` | `where python` |
| **Current dir** | `pwd` | `Get-Location` or `$PWD` | `cd` (without args) |

## Virtual Environment Activation

To activate the project's Python virtual environment:

**PowerShell (preferred):**
```powershell
# Standard activation (recommended)
& ".\.venv\Scripts\Activate.ps1"

# Alternative (longer form)
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
& ".\.venv\Scripts\Activate.ps1"

# Check if activated
python --version
pip list
```

**cmd.exe (alternative):**
```cmd
REM Activate virtual environment
.venv\Scripts\activate.bat

REM Check if activated
python --version
pip list
```

**Common virtual environment locations:**
- Project root: `.venv/Scripts/Activate.ps1` (PowerShell) or `.venv\Scripts\activate.bat` (cmd.exe)
- Full path: `C:\Users\203715\Documents\Repo\cr-misc-function\cr-misc-function\.venv\Scripts\Activate.ps1`

## uv Commands (Windows PowerShell)

```powershell
# Install dependencies (creates/updates .venv and installs from pyproject.toml)
uv sync

# Add package
uv add package_name

# Add dev dependency
uv add --dev package_name

# Remove package
uv remove package_name

# Run script/command in virtual environment
uv run python script.py
uv run mypy app/

# Update lock file
uv lock
uv sync --upgrade

# Show project info
uv python list
```

## Running Python & Tests (Windows PowerShell)

```powershell
# Run Python directly (when venv activated)
python script.py
python -m module_name

# Run with uv (automatically uses project venv)
uv run python script.py

# Type checking
uv run mypy app/
uv run mypy app/configs/

# Linting
uv run ruff check .
uv run ruff format .

# Run tests (when test suite exists)
uv run pytest tests/
```

## Git Commands (Same on Windows/PowerShell)

Git commands work the same on Windows PowerShell as on bash:

```powershell
git status
git add .
git add -p
git diff --staged
git commit -m "message"
git log --oneline -10
git push origin branch_name
```

## Chaining Commands in PowerShell

Use semicolons (`;`) to chain commands, not `&&`:

```powershell
# ✅ CORRECT - PowerShell
Set-Location C:\project; python --version; uv sync

# ❌ WRONG - Bash syntax
cd /project && python --version && poetry install
```

**Important:** Semicolons work in PowerShell; the `&&` operator exists but behaves differently than bash.

## Path Handling

**Always use backslashes for Windows paths:**

```powershell
# ✅ CORRECT - Windows paths
$path = "C:\Users\203715\Documents\Repo\project"
Set-Location "C:\path\to\folder"
$env:PYTHONPATH = "C:\project\src"

# ❌ WRONG - Unix paths
$path = "/home/user/project"                    # Won't work on Windows
Set-Location "/path/to/folder"                  # Won't work
$env:PYTHONPATH = "/project/src"                # Won't work
```

**Forward slashes (/) work in some contexts but backslashes (\) are the Windows standard.**

## File Reading/Manipulation

```powershell
# Read entire file
$content = Get-Content "file.txt"

# Read file line by line
Get-Content "file.txt" | ForEach-Object { Write-Host $_ }

# Read first N lines
Get-Content "file.txt" | Select-Object -First 20

# Search and replace in file
(Get-Content "file.txt") -replace "old", "new" | Set-Content "file.txt"

# Append to file
Add-Content "file.txt" "new line"

# Get file size
(Get-Item "file.txt").Length
```

## Directory Traversal & Operations

```powershell
# Get all Python files recursively
Get-ChildItem -Path "." -Filter "*.py" -Recurse

# Get all files in a specific folder
Get-ChildItem -Path "app/configs" -Filter "*.py"

# Get file modification time
(Get-Item "file.txt").LastWriteTime

# Get folder size
(Get-ChildItem -Path "folder" -Recurse | Measure-Object -Property Length -Sum).Sum
```

## Important: Set Execution Policy (If Needed)

PowerShell may block script execution. If you see execution errors:

```powershell
# Set for current process only (temporary)
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned

# Then activate venv
& ".\.venv\Scripts\Activate.ps1"
```

## Summary: When Executing Commands

**BEFORE running any command:**

1. ✅ Verify it uses **Windows syntax** (PowerShell **primary**, cmd.exe **when simpler**)
2. ✅ Use **backslashes** for Windows paths (`C:\path\not\C:/path`)
3. ✅ Use **semicolons** in PowerShell (`;`), or **`&`** in cmd.exe to chain commands (not `&&`)
4. ✅ Use **PowerShell cmdlets** or **cmd.exe commands** (never bash/Linux commands)
5. ✅ Use **`uv`** for package/dependency management (not pip directly)
6. ✅ Ensure virtual environment is activated (or use `uv run` for auto-activation)

**Shell Selection Guide:**

| Scenario | Shell | Reason |
|----------|-------|--------|
| **Complex operations** (piping, filtering) | PowerShell | Better for object pipelines |
| **Simple file operations** | Either | `cd` or `type` simpler than PowerShell equivalents |
| **Command doesn't exist in PowerShell** | cmd.exe | Fallback to cmd.exe if no PS equivalent |
| **Building tools/scripts** | PowerShell | Modern syntax, better compatibility |
| **Legacy batch scripts** | cmd.exe | Native .bat support |

**Primary: PowerShell**
- Modern syntax with objects and pipelines
- Better error handling
- Recommended for complex operations

**Secondary: cmd.exe**
- Simpler commands for basic operations (dir, cd, type, xcopy)
- Use when PowerShell equivalent is unnecessarily complex
- Use when PowerShell command doesn't exist

**Consequences of using bash syntax:**
- ❌ Commands will fail with "term not recognized"
- ❌ Path errors (forward slashes not interpreted)
- ❌ Script execution failures

---

**Last Updated:** May 13, 2026
**Status:** Active - Windows shells with PowerShell (preferred) or cmd.exe (alternative)
**Environment:** Windows with PowerShell 5.1+ or cmd.exe
