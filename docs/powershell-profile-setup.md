# PowerShell Profile Setup: `conda311` / `conda39` Commands

This guide configures your PowerShell profile to expose lazy conda activation aliases (`conda311` and `conda39`) for switching Python runtimes on demand.

---

## Why This Approach

Avoid unconditional conda activation in your PowerShell profile — it slows down every terminal startup (including non-Python terminals, git, VS Code integrated terminals, etc.).

Instead, define wrapper functions that delegate to the existing init scripts, then alias them. Conda activates **only when explicitly called**. VS Code terminal profiles call these init scripts automatically for Python-focused terminals.

---

## Step 1 — Locate Your PowerShell Profile

Open PowerShell and run:

```powershell
$PROFILE
```

This prints the path. For PowerShell 5.1 (default on Windows):

```text
C:\Users\<you>\Documents\WindowsPowerShell\Microsoft.PowerShell_profile.ps1
```

For PowerShell 7+:

```text
C:\Users\<you>\Documents\PowerShell\Microsoft.PowerShell_profile.ps1
```

If the file does not exist yet, create it:

```powershell
New-Item -ItemType File -Path $PROFILE -Force
```

---

## Step 2 — Add the Full Profile Block

Open your profile in an editor:

```powershell
notepad $PROFILE
# or
code $PROFILE
```

Add the following (this is the complete reference profile):

```powershell
# Enhanced PSReadLine (compatible with PowerShell 5.1+)
Set-PSReadLineKeyHandler -Key Tab -Function MenuComplete
Set-PSReadLineKeyHandler -Key UpArrow -Function HistorySearchBackward
Set-PSReadLineKeyHandler -Key DownArrow -Function HistorySearchForward

# Basic options (all versions support these)
Set-PSReadLineOption -BellStyle None
Set-PSReadLineOption -EditMode Windows
Set-PSReadLineOption -HistoryNoDuplicates

# Version-aware: Predictive suggestions only available in PowerShell 7.2+
if ($PSVersionTable.PSVersion -ge [Version]"7.2") {
    Set-PSReadLineOption -PredictionSource HistoryAndPlugin
    Set-PSReadLineOption -PredictionViewStyle ListView
}

# Fast startup: keep Conda activation lazy and opt-in.
function Enable-CondaPy311 {
    & 'C:\Users\203715\Documents\Repo\cr-misc-function\cr-misc-function\scripts\powershell\conda-py311-init-env.ps1'
}

function Enable-CondaPy39 {
    & 'C:\Users\203715\Documents\Repo\cr-misc-function\cr-misc-function\scripts\powershell\conda-py39-init-env.ps1'
}

Set-Alias conda311 Enable-CondaPy311
Set-Alias conda39 Enable-CondaPy39

# Optional auto-activation for users who still want it.
if ($env:POWERSHELL_AUTO_CONDA -eq '1') {
    Enable-CondaPy311
}
```

Save and reload:

```powershell
. $PROFILE
```

---

## Step 3 — Verify

In a new terminal, type:

```powershell
conda311
```

Expected output:

```text
[OK] Conda py311 activated

Python 3.11.x :: Miniconda
```

---

## Step 4 — Configure VS Code Terminal Profile (Per Project)

Add this to `.vscode/settings.json` in your project to auto-activate conda when opening an integrated terminal:

```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/<project>/.venv/Scripts/python.exe",
  "terminal.integrated.profiles.windows": {
    "PowerShell (Conda py311 + uv)": {
      "source": "PowerShell",
      "args": [
        "-NoExit",
        "-Command",
        "& 'C:\\Users\\203715\\Documents\\Repo\\cr-misc-function\\cr-misc-function\\scripts\\powershell\\conda-py311-init-env.ps1' ; cd '.\\<project>\\'"
      ]
    },
    "PowerShell (Conda py39 + uv)": {
      "source": "PowerShell",
      "args": [
        "-NoExit",
        "-Command",
        "& 'C:\\Users\\203715\\Documents\\Repo\\cr-misc-function\\cr-misc-function\\scripts\\powershell\\conda-py39-init-env.ps1' ; cd '.\\<project>\\'"
      ]
    }
  },
  "terminal.integrated.defaultProfile.windows": "PowerShell (Conda py311 + uv)"
}
```

Replace `<project>` with your project folder name (e.g., `da-pricelist-api`).

---

## How It Works

| What | Where | Purpose |
| ------ | ------- | --------- |
| `conda311` / `conda39` aliases | `$PROFILE` | On-demand runtime switch from any terminal |
| `Enable-CondaPy311` / `Enable-CondaPy39` | `$PROFILE` | Wrapper functions delegating to init scripts |
| `conda-py311-init-env.ps1` | `cr-misc-function/scripts/powershell/` | Runs conda hook + activates `py311` environment |
| `conda-py39-init-env.ps1` | `cr-misc-function/scripts/powershell/` | Runs conda hook + activates `py39` environment |
| `.vscode/settings.json` | Your project | Maps terminal profile → init script + working dir |
| `.venv/` | Your project | Managed by uv; Python extension uses this for IntelliSense |

**Key principle:** The Conda environment provides the Python runtime (e.g., `py311`). The `.venv` inside your project holds project dependencies managed by `uv`. The Python extension auto-detects `.venv` — do **not** manually activate `.venv` in the terminal.

**Optional auto-activation:** Set `$env:POWERSHELL_AUTO_CONDA = '1'` in your system environment variables if you want `py311` to activate automatically on every terminal startup (useful on dedicated Python machines). Leave it unset for the lazy default.

---

## Troubleshooting

### **`conda311` not found after reloading profile**

- Confirm which profile file is loaded: `$PROFILE` — PowerShell 5.1 and 7+ use different paths (see Step 1)
- Re-run `. $PROFILE` after editing

### **Init script path not found**

- The functions point to `cr-misc-function/scripts/powershell/`. Adjust the path if this repo is cloned elsewhere.

### **Terminal startup is slow**

- Ensure `Enable-CondaPy311` is **not** called unconditionally at profile top-level
- The `POWERSHELL_AUTO_CONDA` guard keeps auto-activation opt-in only

### **Conda hook path does not exist inside the init script**

- Update the hook path in `conda-py311-init-env.ps1` to match your Miniconda/Anaconda install:

  ```powershell
  Get-ChildItem "$env:USERPROFILE\AppData\Local" -Filter "conda-hook.ps1" -Recurse | Select-Object FullName
  ```

---

## See Also

- `cr-misc-function/scripts/powershell/conda-py311-init-env.ps1` — py311 init script
- `cr-misc-function/scripts/powershell/conda-py39-init-env.ps1` — py39 init script
- `templates/vscode/` — VS Code settings templates
