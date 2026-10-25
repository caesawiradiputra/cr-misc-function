# Windows Side of a WSL Development Laptop: Tools, Support Apps and Tuning

What to install on Windows when your development happens inside WSL 2, what to leave out because WSL already has it, which support tools are worth having, and how to keep Windows light, fast and efficient. The WSL side is in [WSL-MIGRATION.md](WSL-MIGRATION.md).

Rule of thumb: **install development tools inside WSL, and keep Windows for the things only Windows can do**: host WSL, a terminal, an editor, a browser, the VPN and company software. Every extra Windows program is one more thing that starts at login, updates itself and uses memory.

## 1. Measure first

Do not tune from guesses. Run the read-only report (it changes nothing) in PowerShell:

```powershell
.\scripts\powershell\dev-laptop-report.ps1                       # standard report
.\scripts\powershell\dev-laptop-report.ps1 -IncludeFolderSizes   # adds the biggest folders (slow)
```

It writes `windows-report.txt` and CSV files to `Documents\WSL-Migration\windows-report-<date>`: hardware, installed apps, duplicate installs, startup items, logon tasks, running services, the 15 biggest memory users, speed-related settings, WSL status and the proxy Windows hands to WSL. Run it from an **administrator** PowerShell to also list Defender exclusions and Windows optional features; the script says so when it skips them. To compare two laptops, diff the two reports.

No PowerShell? The same facts are in the GUI: **Task Manager** (`Ctrl+Shift+Esc`) > Processes, Startup apps; **Settings > Apps > Installed apps**; **Settings > System > Storage**; **Settings > System > About**.

## 2. Mandatory on Windows

| Tool | Why it must be on Windows | winget id |
| --- | --- | --- |
| Windows 11, fully updated | WSL 2 needs a current build | n/a |
| Virtualization on in the firmware (BIOS or UEFI) | WSL 2 is a lightweight VM; check in Task Manager > Performance > CPU > "Virtualization: Enabled" | n/a |
| WSL (store version) + Ubuntu 24.04 | The development environment itself (`wsl --install -d Ubuntu-24.04`, then `wsl --update`) | `Microsoft.WSL` |
| Windows Terminal | Tabs and profiles for PowerShell and Ubuntu; ships with Windows 11, update it through winget | `Microsoft.WindowsTerminal` |
| Visual Studio Code | The editor that connects into WSL (WSL extension `ms-vscode-remote.remote-wsl`); install on Windows, never inside Ubuntu | `Microsoft.VisualStudioCode` |
| A browser | `gh auth login`, Atlassian and cloud consoles, Claude Code login | company standard |
| Company-managed software | VPN client, security and device-management agents, mail, chat and office suite. IT installs and updates these; never remove or disable them | installed by IT |

One command installs the winget ones:

```powershell
winget import -i templates\windows\winget-core.json --accept-package-agreements --accept-source-agreements
```

`winget-core.json` holds the mandatory tools plus the support tools of section 4.

## 3. Install inside WSL only (skip on Windows)

| Tool | Why skip it on Windows |
| --- | --- |
| Git and the GitHub CLI | VS Code's WSL window uses the Git inside WSL; a second Git on Windows only matters for repos kept on the Windows disk. Keep repos in WSL's filesystem (`~/repo`), which is faster and avoids line-ending trouble |
| Python, `uv`, Node (nvm), `jq`, build tools | Install them once, in WSL. A second Python on Windows invites the wrong interpreter being picked |
| Docker | Use the native engine in WSL (kept off until needed). Docker Desktop autostarts, holds memory, and company policy may block image pulls from it |
| Claude Code | Install and run it inside WSL so it sees the same files and shell as your tools |
| Anaconda or Miniconda | `uv` replaces it; keep it only if a repo still needs a conda environment |
| .NET SDK, Rust, C++ build tools | Only when you build for Windows. For Linux workloads install them in WSL, when a repo asks |
| SQL Server ODBC driver | `pyodbc` in WSL needs the Linux driver (`msodbcsql18` from Microsoft's apt repo), not the Windows one. The Windows driver is for Windows tools such as SSMS |
| Cloud SDKs (for example `gcloud`), `ripgrep` | Install in WSL when a script there needs them |

## 4. Support tools worth having

| Tool | What it is for | winget id |
| --- | --- | --- |
| PowerToys | A set of small utilities. Worth turning on: **Command Palette** (launcher), **FancyZones** (window layouts), **Keyboard Manager**, **Always On Top**, **Text Extractor** (OCR from the screen), **Peek** (preview files), **Awake** (keep the PC awake during a build), **ZoomIt**, **Environment Variables** and **Hosts File Editor**. Turn off the modules you do not use; each adds a background process | `Microsoft.PowerToys` |
| 7-Zip | Archives; Windows' built-in zip handling is slow for large files | `7zip.7zip` |
| Notepad++ | Quick edits of logs and large text files | `Notepad++.Notepad++` |
| Sysinternals Autoruns and Process Explorer | The honest view of what starts at login and what uses memory (official Microsoft tools, from learn.microsoft.com) | download |
| A database client (DBeaver) and an API client (Bruno) | Inspect databases and call APIs from the GUI | `DBeaver.DBeaver.Community`, `Bruno.Bruno` |
| Antigravity IDE or another second editor | Only if you use it | `Google.AntigravityIDE` |
| MobaXterm | SSH and X11 sessions, only if Windows Terminal with the built-in OpenSSH is not enough | `Mobatek.MobaXterm` |

The optional ones are in `templates/windows/winget-optional.json` (adds Git, GitHub Desktop and the Claude desktop app for people who want them on Windows):

```powershell
winget import -i templates\windows\winget-optional.json --accept-package-agreements --accept-source-agreements
```

## 5. Make Windows lighter, faster and more efficient

Work in this order, and re-run the report afterwards to see the change. Everything below is per user and reversible unless it says otherwise.

### 5.1 Startup: the biggest win

**Task Manager > Startup apps**, sorted by **Startup impact**. Turn off (right-click > Disable):

- container and developer tools you start by hand (Docker Desktop, GitHub Desktop, IDE launchers);
- updater and "download assistant" helpers from peripheral vendors (Logitech and similar);
- chat and meeting apps you do not need ready at login (Teams can start on demand);
- browser auto-launch entries and "send to" helpers;
- cloud-sync clients you do not use (leave the one your company requires).

Keep the VPN client (when you need it to reach the network), the security and device-management agents, and Windows Security. Anything you are unsure about: look it up in Autoruns before disabling. Disabling a startup entry only stops the autostart; the program stays installed.

### 5.2 Remove what you do not use

**Duplicates first.** The report lists programs installed more than once (for example the same editor installed once system-wide and once per user). Keep one: `winget uninstall --id <id>` or **Settings > Apps > Installed apps**.

**Consumer apps from Windows 11** (games, news, phone, media and assistant apps) can be removed for your user and reinstalled from the Store. Review the list, then remove only what you recognise as unused:

```powershell
$remove = 'Microsoft.BingNews','Microsoft.BingWeather','Microsoft.MicrosoftSolitaireCollection',
          'Microsoft.MicrosoftJournal','Clipchamp.Clipchamp','Microsoft.WindowsFeedbackHub',
          'Microsoft.GetHelp','Microsoft.YourPhone','Microsoft.ZuneMusic','Microsoft.Todos',
          'Microsoft.Whiteboard','Microsoft.PowerAutomateDesktop','Microsoft.WindowsSoundRecorder',
          'Microsoft.Windows.DevHome','Microsoft.XboxGamingOverlay','Microsoft.XboxSpeechToTextOverlay',
          'Microsoft.Xbox.TCUI','Microsoft.XboxIdentityProvider','Microsoft.GamingApp'
foreach ($name in $remove) { Get-AppxPackage -Name $name | Remove-AppxPackage }
```

Keep Terminal, Notepad, Calculator, Snipping Tool, Photos, Paint, Camera, Store, App Installer, Windows Security and anything IT assigned. Copilot and similar assistants may be controlled by company policy; leave them if they come back after removal.

**Docker Desktop** if you use the native engine in WSL: `winget uninstall --id Docker.DockerDesktop`, then check `wsl -l -v`; the leftover `docker-desktop` distro can be removed with `wsl --unregister docker-desktop` once Docker Desktop is gone and you have confirmed you never stored anything in it.

### 5.3 Settings that cost speed

| Setting | Where | Suggestion |
| --- | --- | --- |
| Power mode | Settings > System > Power & battery > Power mode | Best performance when plugged in, Balanced on battery |
| Transparency | Settings > Personalization > Colors > Transparency effects | Off |
| Animations | Settings > Accessibility > Visual effects > Animation effects | Off |
| Widgets | Settings > Personalization > Taskbar > Widgets | Off |
| Game Mode and capture | Settings > Gaming | Off when you do not play |
| Background apps | Settings > Apps > Installed apps > app > Advanced options > Background apps permissions | Never, for apps you open on demand |
| Notifications and tips | Settings > System > Notifications | Turn off "tips and suggestions" and noisy senders |
| Storage Sense | Settings > System > Storage > Storage Sense | On, to clear temp files |
| Search indexing | Settings > Privacy & security > Searching Windows | "Classic" mode; exclude big work folders you never search from Explorer |
| OneDrive Known Folder Backup | OneDrive settings > Sync and backup | Follow company policy; large synced folders cost disk and CPU |
| Windows Update active hours | Settings > Windows Update > Advanced options | Set to your working hours so restarts do not hit a build |

### 5.4 Browser and WSL memory

- Browsers are usually the largest memory user. Turn on **Memory Saver** (Chrome: Settings > Performance) or **Sleeping tabs** (Edge), close the profiles you do not use, and prefer one browser window per task.
- Cap WSL in `C:\Users\<you>\.wslconfig`: `memory` at about half of the machine's RAM, `autoMemoryReclaim=gradual` and `sparseVhd=true` so WSL gives memory and disk back. `wsl --shutdown` frees everything WSL holds (it also stops running builds and Claude sessions).
- Keep repos in WSL's own filesystem. Reading and writing `/mnt/c` is much slower, and a Windows scan of the repo files slows Git.
- Optional: in `/etc/wsl.conf` add `[interop]` with `appendWindowsPath=false` to keep the long Windows PATH out of Linux shells (faster start-up). Then `code .` and `explorer.exe` are no longer on PATH; call them by full path or add only those folders back.

### 5.5 Do not touch

- Security, encryption, device-management and endpoint agents, and the state of Windows Defender or its exclusions. They are managed by IT, and changing them can break compliance or lock you out. Ask IT for an exclusion for the WSL virtual disk only if builds are slow and IT agrees.
- Third-party "debloat" or "optimizer" scripts and registry cleaners. They change system services and policies in ways that are hard to undo, and a company laptop may re-apply its own settings and break.
- Disabling Windows Update or core services. Delay and schedule updates instead.

## 6. Moving the Windows side to a new laptop

Most of the user folder travels with IT's copy. Save the rest explicitly:

| What | How |
| --- | --- |
| List of installed apps | `winget export -o "$env:USERPROFILE\Documents\WSL-Migration\winget-export.json" --accept-source-agreements`; on the new laptop `winget import -i <file>` after reading it and deleting what you no longer want |
| VS Code and Antigravity settings, keybindings, extensions | Settings Sync (sign in with the same account), or copy `%APPDATA%\Code\User` |
| Windows Terminal | Copy `settings.json` from `%LOCALAPPDATA%\Packages\Microsoft.WindowsTerminal_8wekyb3d8bbwe\LocalState` |
| PowerToys | Settings > General > Backup & restore |
| `.wslconfig` | `C:\Users\<you>\.wslconfig` (also kept in the WSL backup inventory) |
| DBeaver connections | File > Export > DBeaver > Project (passwords are not exported; re-enter them) |
| Bruno collections | They are plain folders: copy them |
| MobaXterm sessions | Settings > Configuration, export the configuration and sessions |
| Browser | Sign in to sync; export saved passwords only if your company allows it |
| VPN profiles and certificates | Issued by IT; ask for new ones rather than copying files |
| Anything under `Documents` or `Downloads` you need | Part of the user folder copy; check it before the old laptop is wiped |

## 7. Setting up the new Windows laptop, in order

1. Run Windows Update until nothing is pending; confirm virtualization is on in the firmware.
2. Sign in to the company software IT installed (VPN first, so everything after can reach the network).
3. Install the core tools: `winget import -i templates\windows\winget-core.json`.
4. Open Terminal, then install WSL and Ubuntu and follow [WSL-MIGRATION.md](WSL-MIGRATION.md).
5. Install the optional tools you actually use (section 4).
6. Restore editor, Terminal and PowerToys settings (section 6).
7. Apply section 5: startup apps first, then duplicates and unused apps, then the settings.
8. Run the report again and keep it as the baseline for the next laptop.

## 8. Verify

- [ ] `wsl --version` shows WSL 3.x (reference 3.0.3.0); `wsl -l -v` shows Ubuntu at VERSION 2.
- [ ] Task Manager > Startup apps: only the VPN, security agents and tools you chose are enabled.
- [ ] No program is installed twice; Docker Desktop and Miniconda are gone unless you need them.
- [ ] Idle memory after login is mostly the browser and WSL; the report's top 15 shows nothing you did not expect.
- [ ] `code .` from WSL opens a WSL window; the extension list matches `templates/vscode/extensions.json`.
- [ ] The new report is saved next to the WSL backup for comparison.
