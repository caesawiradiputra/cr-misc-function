# New Device Setup: Claude Code + VS Code / Antigravity

Set up a fresh **Windows** or **WSL 2 / Ubuntu** machine with Claude Code, this
repo's global Claude configuration, and VS Code or Antigravity IDE. Work top to
bottom; each section says which path it applies to.

> **Deeper WSL details** (nvm, npm config, proxies) are in
> [claude-code-wsl-setup.md](claude-code-wsl-setup.md). This guide is the
> end-to-end checklist; that one is the WSL troubleshooting reference.

---

## Table of Contents

- [0. Choose Your Path](#0-choose-your-path)
- [1. Base Tools](#1-base-tools)
- [2. Install Claude Code](#2-install-claude-code)
- [3. Clone This Repo](#3-clone-this-repo)
- [4. Install the Global Claude Config](#4-install-the-global-claude-config)
- [5. IDE: VS Code](#5-ide-vs-code)
- [6. IDE: Antigravity](#6-ide-antigravity)
- [7. Python Projects](#7-python-projects)
- [8. Verification Checklist](#8-verification-checklist)
- [9. Troubleshooting](#9-troubleshooting)

---

## 0. Choose Your Path

| | Native Windows | WSL 2 / Ubuntu |
| --- | --- | --- |
| Shell Claude Code runs | PowerShell (Bash tool via Git for Windows) | bash |
| Global config folder | `C:\Users\<you>\.claude` | `/home/<you>/.claude` |
| Repo location | `C:\Users\<you>\Documents\Repo\<umbrella>\<repo>` | `~/repo/<umbrella>/<repo>` |
| Settings template | `CLAUDE/windows/` | `CLAUDE/linux-wsl/` |
| Scripts | `scripts/powershell/*.ps1` | `scripts/bash/*.sh` |
| Sandboxing | Not supported | Supported |

**The two sides are separate machines as far as Claude Code is concerned.**
WSL has its own home folder, its own `~/.claude`, its own tools, and its own
checkout of each repo. If you use both, set up both, and don't point one side
at the other's files (`/mnt/c/...` is slow and has different line endings).

**Repo layout used everywhere:** an *umbrella* folder per project group
holding the real git repo one level down, e.g.
`~/repo/cr-misc-function/cr-misc-function/`. The global hooks (section 4)
rely on this layout to report sibling repos.

---

## 1. Base Tools

The hooks and status line need **`jq`** and **git** on both paths; uv is the
Python package manager for every repo.

### Windows (PowerShell, no admin needed for most)

```powershell
winget install --id Git.Git -e          # Git for Windows: git + Git Bash (Bash tool, status line `sh`)
winget install --id GitHub.cli -e       # gh
winget install --id jqlang.jq -e        # jq: hooks + status line
winget install --id astral-sh.uv -e     # uv (manages Python too)
```

Open a **new** terminal afterwards so `PATH` picks them up, then check:

```powershell
git --version; gh --version; jq --version; uv --version
```

### WSL 2 / Ubuntu

From an **admin** PowerShell on Windows, if WSL isn't installed yet:

```powershell
wsl --install -d Ubuntu
```

Then inside the Ubuntu shell:

```bash
sudo apt update && sudo apt install -y git curl jq build-essential
curl -LsSf https://astral.sh/uv/install.sh | sh      # installs uv/uvx into ~/.local/bin
```

GitHub CLI (official apt repo):

```bash
(type -p wget >/dev/null || sudo apt install -y wget) \
  && sudo mkdir -p -m 755 /etc/apt/keyrings \
  && wget -qO- https://cli.github.com/packages/githubcli-archive-keyring.gpg \
     | sudo tee /etc/apt/keyrings/githubcli-archive-keyring.gpg >/dev/null \
  && sudo chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg \
  && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
     | sudo tee /etc/apt/sources.list.d/github-cli.list >/dev/null \
  && sudo apt update && sudo apt install -y gh
```

Open a new shell and check:

```bash
git --version && gh --version && jq --version && uv --version
```

Some Python drivers build from source on Linux and need system libraries that
Conda used to provide, e.g. `sudo apt install unixodbc-dev` for `pyodbc`
(see [section 7](#7-python-projects)).

### Both: git identity and GitHub login

```bash
git config --global user.name  "Your Name"
git config --global user.email "you@example.com"
gh auth login          # HTTPS, log in with a browser
gh auth setup-git      # lets git use gh's credentials
```

---

## 2. Install Claude Code

Use the **native installer** (recommended by Anthropic; it auto-updates). npm
still works but is the fallback.

| Path | Command |
| --- | --- |
| Windows PowerShell | `irm https://claude.ai/install.ps1 \| iex` |
| WSL / Ubuntu | `curl -fsSL https://claude.ai/install.sh \| bash` |

On WSL, install and run `claude` **inside the WSL shell**, not from
PowerShell. The installer puts the launcher in `~/.local/bin`, so make sure
that folder is on `PATH` (a new login shell usually does this).

Verify and log in:

```bash
claude --version     # prints e.g. 2.1.x (Claude Code)
claude doctor        # install health + settings validation, no session started
claude               # first run opens the browser login
```

---

## 3. Clone This Repo

Windows:

```powershell
New-Item -ItemType Directory -Path "$env:USERPROFILE\Documents\Repo\cr-misc-function" -Force
Set-Location "$env:USERPROFILE\Documents\Repo\cr-misc-function"
git clone https://github.com/caesawiradiputra/cr-misc-function.git
```

WSL:

```bash
mkdir -p ~/repo/cr-misc-function && cd ~/repo/cr-misc-function
git clone https://github.com/caesawiradiputra/cr-misc-function.git
```

All commands below run from the repo root
(`.../cr-misc-function/cr-misc-function`).

---

## 4. Install the Global Claude Config

The `CLAUDE/` folder is a snapshot of the global `~/.claude` config. See
[CLAUDE/README.md](../CLAUDE/README.md) for what each file does and which
placeholders it contains.

### 4.1 `CLAUDE.md` + slash commands (sync script)

Windows (pass the global path explicitly; the script's default is the
original machine's account):

```powershell
.\scripts\powershell\chat-Sync-ClaudeContext.ps1 -GlobalClaudePath "$env:USERPROFILE\.claude"
```

WSL:

```bash
./scripts/bash/chat-sync-claude-context.sh
```

Re-run it whenever `CLAUDE/CLAUDE.md` or `CLAUDE/commands/` change.

### 4.2 Settings, hooks, status line

These are copied once by hand. **Check first whether `~/.claude/settings.json`
already exists** (e.g. from an earlier login); if it does, merge instead of
overwriting.

Windows:

```powershell
$C = "$env:USERPROFILE\.claude"
New-Item -ItemType Directory -Path "$C\hooks" -Force | Out-Null
$json = (Get-Content .\CLAUDE\windows\settings.json -Raw) -replace '<WINDOWS_USERNAME>', $env:USERNAME
[IO.File]::WriteAllText("$C\settings.json", $json)   # UTF-8 without BOM (PS 5.1's -Encoding utf8 adds one)
Copy-Item .\CLAUDE\windows\hooks\* "$C\hooks\" -Force
Copy-Item .\CLAUDE\statusline-command.sh "$C\" -Force
```

WSL:

```bash
mkdir -p ~/.claude/hooks
cp CLAUDE/linux-wsl/settings.json ~/.claude/settings.json
cp CLAUDE/linux-wsl/hooks/* ~/.claude/hooks/
cp CLAUDE/statusline-command.sh ~/.claude/
```

What you get: deny rules for secrets (`.env`, keys, `*.tfstate`, ...), a
`SessionStart` hook that reports the umbrella's sibling repos, a
`UserPromptSubmit` hook that resolves `@repo/` mentions, a ruff format/lint
hook after Python edits, the status line, and the enabled plugins.

### 4.3 Skills

```powershell
# Windows
Copy-Item .\CLAUDE\skills\* "$env:USERPROFILE\.claude\skills\" -Recurse -Force
```

```bash
# WSL
mkdir -p ~/.claude/skills && cp -r CLAUDE/skills/. ~/.claude/skills/
```

Then replace the placeholders in the copied skills (this repo is public, so
the template doesn't carry the real values). The table is in
[CLAUDE/README.md](../CLAUDE/README.md#folder-structure): at minimum
`<WINDOWS_USERNAME>` and `<ATLASSIAN_SITE>` in `jira-ticket-kickoff`, and
`<ATLASSIAN_SITE>` / `<BAST_TEMPLATE_PAGE_ID>` in `bast-*`. Find them with:

```bash
grep -rn "<WINDOWS_USERNAME>\|<ATLASSIAN_SITE>\|<BAST_TEMPLATE_PAGE_ID>\|<COMPANY>" ~/.claude/skills
```

### 4.4 Plugins and MCP servers

Start `claude` and run `/plugin`. The settings file enables these plugins from
the built-in `claude-plugins-official` marketplace; install any that are
listed as missing:

```text
/plugin install superpowers@claude-plugins-official
/plugin install feature-dev@claude-plugins-official
/plugin install skill-creator@claude-plugins-official
/plugin install claude-md-management@claude-plugins-official
/plugin install claude-code-setup@claude-plugins-official
/plugin install code-simplifier@claude-plugins-official
/plugin install atlassian@claude-plugins-official
```

Add the MCP server from `CLAUDE/mcp-servers.json` (user scope, all projects):

```bash
claude mcp add --transport http --scope user context7 https://mcp.context7.com/mcp
```

The Atlassian plugin asks you to log in to your Atlassian site the first time
a Jira/Confluence tool is used.

### 4.5 Auto mode rules (per machine)

`autoMode` is read **only** from `~/.claude/settings.json` (or managed
settings), never from a project, and the template deliberately ships without
your environment block. If you use auto mode, add an `autoMode.environment`
list describing your orgs, trusted repos, protected branches, and sensitive
data, **workspace-wide, not for one repo** (see the note in
[CLAUDE/README.md](../CLAUDE/README.md)).

### 4.6 Check it

```bash
claude doctor        # settings.json must validate with no errors
```

In a session: the status line shows at the bottom, `/` lists the commands
(`/commit`, `/generate-pr-message`, ...), `/plugin` shows the plugins enabled,
`/mcp` shows `context7` connected, and the first prompt in a repo under the
umbrella layout shows the SessionStart repo context.

---

## 5. IDE: VS Code

### 5.1 Install

- Windows: `winget install --id Microsoft.VisualStudioCode -e`
- WSL: install VS Code **on Windows** (above), not inside Ubuntu. It connects
  to WSL through the **WSL** extension (`ms-vscode-remote.remote-wsl`).

### 5.2 Extensions

The recommended set is in `templates/vscode/extensions.json`. Install them all
from a terminal where `code` is on `PATH`:

```powershell
# Windows
(Get-Content .\templates\vscode\extensions.json -Raw) -replace '//.*','' |
    ConvertFrom-Json | Select-Object -ExpandProperty recommendations |
    ForEach-Object { code --install-extension $_ }
```

```bash
# WSL (run inside a VS Code WSL window's terminal, so they install on the WSL side)
sed 's://.*$::' templates/vscode/extensions.json | jq -r '.recommendations[]' \
  | xargs -n1 code --install-extension
```

Also install **Claude Code for VS Code** (`anthropic.claude-code`, VS Code
1.94+). In a WSL window, install it *in WSL* (the Extensions view shows an
"Install in WSL: Ubuntu" button), because it must run where the CLI and
the repo live.

### 5.3 Settings

Open **Preferences: Open User Settings (JSON)** and merge in
`templates/vscode/settings.json`. It configures ruff as the formatter, uv
environments, rulers, and file watcher excludes. Per project, point the
interpreter at the repo's `.venv`:

```jsonc
{
  "python.defaultInterpreterPath": "${workspaceFolder}/<repo>/.venv/bin/python"   // Windows: .venv/Scripts/python.exe
}
```

### 5.4 Open a project

- Windows: `code C:\Users\<you>\Documents\Repo\<umbrella>`.
- WSL: from the Ubuntu shell, `cd ~/repo/<umbrella> && code .`. The
  bottom-left indicator shows `WSL: Ubuntu`.

Open the **umbrella** folder (or its `.code-workspace`); the hooks and the
multi-root rules in `CLAUDE.md` expect it.

---

## 6. IDE: Antigravity

Antigravity is Google's VS Code fork. It installs extensions from
**Open VSX**, not the Microsoft marketplace, so a few Microsoft-only
extensions are unavailable.

### 6.1 Install and extensions

1. Install Antigravity on **Windows** from its official site (for WSL
   projects, the Windows install connects to WSL remotely, like VS Code).
2. Install the extensions from `templates/antigravity ide/extensions.json`
   through the Extensions view (search each ID). It swaps Microsoft-only
   pieces for Open VSX equivalents: `meta.pyrefly` for type checking instead
   of Pylance, and includes `anthropic.claude-code`.

### 6.2 Settings

Merge `templates/antigravity ide/user.settings.json` into the user settings
JSON. Keep `"python.languageServer": "Default"`: Pylance can't run in a
non-Microsoft fork, and pyrefly provides the type checking.

### 6.3 WSL projects

Connect the window to WSL from the remote indicator (bottom-left) and open
`~/repo/<umbrella>`. Antigravity installs its server under
`~/.antigravity-ide-server` in WSL. Two known problems on that setup, both
covered in `CLAUDE.md`:

- **Python extension error mentioning `pet`** (`spawn .../pet ENOENT`): the
  installed `ms-python.python` is the `universal` build without its native
  binary. The fix is in `CLAUDE.md` (download the `linux-x64` VSIX, copy the
  `pet` binary in); disable auto-update for that extension so it sticks.
- **`uv` not found by the Python extension:** the remote server doesn't
  inherit `~/.local/bin` on `PATH`. Symlink uv into `/usr/local/bin`
  ([section 9](#9-troubleshooting)).

---

## 7. Python Projects

Per repo:

```bash
uv sync                   # creates .venv from pyproject.toml + uv.lock
uv run ruff check .
uv run mypy .
```

For repos that aren't on uv yet, or need a newer Python:

| Situation | Tool |
| --- | --- |
| Poetry/Conda project, migrate to uv | `scripts/bash/dev-migrate-conda-poetry-to-uv.sh` (WSL, no Conda needed) or `scripts/powershell/dev-migrate-conda-poetry-to-uv.ps1`, then follow the generated `legacy/README_MIGRATION.md`. The `migrate-to-uv` skill automates the whole flow. |
| Move a project to a newer Python (e.g. 3.8 → 3.11) | The `upgrade-python-version` skill: dependency bumps, syntax-only rewrites, upgrade guide |
| Missing lint config | Copy `templates/ruff.toml` and `templates/mypy.ini`, and set `target-version` / `python_version` to the project's Python |

---

## 8. Verification Checklist

- [ ] `git`, `gh`, `jq`, `uv` all print versions in a **new** terminal
- [ ] `gh auth status` shows you logged in
- [ ] `claude --version` works and `claude doctor` shows no settings errors
- [ ] `~/.claude/` has `CLAUDE.md`, `commands/`, `skills/`, `hooks/`, `settings.json`, `statusline-command.sh`
- [ ] No `<WINDOWS_USERNAME>` / `<ATLASSIAN_SITE>` placeholders left in `~/.claude`
- [ ] In a session: status line visible, `/commit` listed, `/plugin` and `/mcp` healthy
- [ ] Opening a repo under the umbrella shows the SessionStart repo context
- [ ] IDE: Claude Code panel opens; on WSL it runs in the WSL window
- [ ] `uv sync` works in one real project and the IDE picks up its `.venv`

---

## 9. Troubleshooting

**Status line empty, or hooks fail with `jq: command not found`.**
Install jq (section 1) and restart Claude Code.

**Windows: status line or Bash tool can't find `sh`/`bash`.**
Install Git for Windows. If Claude Code still can't find it, set
`"env": { "CLAUDE_CODE_GIT_BASH_PATH": "C:\\Program Files\\Git\\bin\\bash.exe" }`
in `~/.claude/settings.json`.

**`claude`, `uv` or `uvx` not found in some contexts (IDE server, sudo, hooks).**
They live in `~/.local/bin`, which non-login processes may not have on `PATH`.
Symlink them somewhere that always is:

```bash
sudo ln -sf ~/.local/bin/uv  /usr/local/bin/uv
sudo ln -sf ~/.local/bin/uvx /usr/local/bin/uvx
```

**Hooks don't fire.** Run `/hooks` in a session to see what loaded. On
Windows, check that the hook paths in `settings.json` point at your account
(placeholder replaced), and on WSL that `~/.claude/hooks/*.sh` exist.

**Corporate proxy / network errors during install or `uv sync`.**
See the proxy section of [claude-code-wsl-setup.md](claude-code-wsl-setup.md#17-troubleshooting).

**The sync script copied into the wrong `~/.claude`.**
On Windows, pass `-GlobalClaudePath "$env:USERPROFILE\.claude"`; on WSL the
default `$HOME/.claude` is correct. Never sync the Windows side from WSL
through `/mnt/c` without meaning to.

---

## See Also

- [CLAUDE/README.md](../CLAUDE/README.md): what each global config file does, placeholders, exclusions
- [claude-code-wsl-setup.md](claude-code-wsl-setup.md): WSL deep-dive (nvm/npm route, proxies)
- [scripts/bash/README.md](../scripts/bash/README.md) / [scripts/powershell/README.md](../scripts/powershell/README.md): script reference
- Official docs: [Claude Code setup](https://code.claude.com/docs/en/setup), [VS Code extension](https://code.claude.com/docs/en/vs-code)
