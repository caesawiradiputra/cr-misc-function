# Claude Code Setup in WSL 2

This guide documents installing and configuring the **Claude Code CLI** inside **WSL 2 / Ubuntu**, using **nvm** to manage Node.js. It reflects a real setup session from September 2026 — exact version numbers below (nvm `0.40.3`, Node `v24.21.0`, Claude Code `2.1.273`) are the versions installed *at that time*. Running these commands later will install newer versions; that is expected and does not affect the procedure. Paths below use `<user>` for whichever WSL/Windows username is active on your machine — substitute your own.

> **Which shell am I in?** WSL 2 runs a separate Linux filesystem and home directory (`/home/<user>`) from native Windows (`C:\Users\<user>`) — they are not interchangeable. This guide is entirely bash/WSL-side. See the global `~/.claude/CLAUDE.md` "Environment" section for how to detect which shell a given Claude Code session is actually running in, and `scripts/bash/` vs `scripts/powershell/` in this repo for the dual-shell script convention that follows from it.

## Table of Contents

- [Claude Code Setup in WSL 2](#claude-code-setup-in-wsl-2)
  - [Table of Contents](#table-of-contents)
  - [1. Prerequisites](#1-prerequisites)
  - [2. Verify WSL 2](#2-verify-wsl-2)
  - [3. Open a WSL Shell](#3-open-a-wsl-shell)
  - [4. Install nvm](#4-install-nvm)
  - [5. Install Node.js LTS](#5-install-nodejs-lts)
    - [Fixing an `.npmrc` Conflict Warning](#fixing-an-npmrc-conflict-warning)
  - [6. Verify npm Configuration](#6-verify-npm-configuration)
  - [7. Set Node.js as the Default](#7-set-nodejs-as-the-default)
  - [8. Install Claude Code](#8-install-claude-code)
  - [9. Allow Claude Code's Install Script](#9-allow-claude-codes-install-script)
  - [10. Verify Claude Code](#10-verify-claude-code)
  - [11. Migrating From a Pre-nvm Install](#11-migrating-from-a-pre-nvm-install)
  - [12. Recommended Project Location](#12-recommended-project-location)
  - [13. Recommended Architecture](#13-recommended-architecture)
  - [14. VS Code Integration](#14-vs-code-integration)
  - [15. Final Verification Checklist](#15-final-verification-checklist)
  - [16. Key Commands](#16-key-commands)
  - [17. Troubleshooting](#17-troubleshooting)
    - [`nvm: command not found` after opening a new WSL shell](#nvm-command-not-found-after-opening-a-new-wsl-shell)
    - [npm warns about incompatible `globalconfig`/`prefix` settings](#npm-warns-about-incompatible-globalconfigprefix-settings)
    - [`npm install -g @anthropic-ai/claude-code` succeeds but Claude Code doesn't work](#npm-install--g-anthropic-aiclaude-code-succeeds-but-claude-code-doesnt-work)
    - [`which claude` returns nothing, or resolves to the wrong path](#which-claude-returns-nothing-or-resolves-to-the-wrong-path)
    - [Repository feels slow (git status, file watching, installs)](#repository-feels-slow-git-status-file-watching-installs)
    - [Claude Code / `npm install` hangs or can't reach the network behind a corporate proxy](#claude-code--npm-install-hangs-or-cant-reach-the-network-behind-a-corporate-proxy)
    - [`uv`/`uvx` not found when Claude Code runs shell commands](#uvuvx-not-found-when-claude-code-runs-shell-commands)
  - [18. Companion CLI Tools for Claude Code's Git/GitHub Workflows](#18-companion-cli-tools-for-claude-codes-gitgithub-workflows)
  - [See Also](#see-also)

---

## 1. Prerequisites

- Windows 10/11 with WSL 2 support
- Administrator access on the Windows host (only needed once, to install/enable WSL 2 itself)
- An Anthropic account for the Claude Code authentication flow

---

## 2. Verify WSL 2

From **PowerShell** (native Windows side):

```powershell
wsl --status
wsl -l -v
```

Expected:

```text
NAME      STATE    VERSION
Ubuntu    Running  2
```

If WSL is not installed:

```powershell
wsl --install -d Ubuntu
```

---

## 3. Open a WSL Shell

From **PowerShell**:

```powershell
wsl
```

The prompt should look similar to:

```text
<user>@<hostname>:/mnt/c/Users/<user>$
```

Starting under `/mnt/c` (the Windows filesystem mounted into WSL) is not a problem — nvm and Node.js install under the **Linux home directory** (`/home/<user>`), not under `/mnt/c`. See [Section 12](#12-recommended-project-location) for why project code itself should still live under the Linux filesystem.

---

## 4. Install nvm

```bash
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash
```

This creates `/home/<user>/.nvm` and appends the nvm initialization block to `/home/<user>/.bashrc`.

Reload the shell configuration and verify:

```bash
source ~/.bashrc
nvm --version
```

Expected:

```text
0.40.3
```

---

## 5. Install Node.js LTS

```bash
nvm install --lts
```

In this setup, nvm installed Node.js `v24.21.0` / npm `11.19.0`.

### Fixing an `.npmrc` Conflict Warning

nvm may report:

```text
Your user's .npmrc file (${HOME}/.npmrc)
has a `globalconfig` and/or `prefix` setting, which are incompatible with nvm.
```

Apply the fix nvm suggests, substituting the installed version:

```bash
nvm use --delete-prefix v24.21.0
```

Expected:

```text
Now using node v24.21.0 (npm v11.19.0)
```

---

## 6. Verify npm Configuration

```bash
npm config get prefix
npm config get globalconfig
which node
which npm
cat ~/.npmrc
```

Expected:

```text
/home/<user>/.nvm/versions/node/v24.21.0
/home/<user>/.nvm/versions/node/v24.21.0/etc/npmrc
/home/<user>/.nvm/versions/node/v24.21.0/bin/node
/home/<user>/.nvm/versions/node/v24.21.0/bin/npm
cat: /home/<user>/.npmrc: No such file or directory
```

No user-level `.npmrc` is expected at this point — its earlier absence is exactly what let `nvm use --delete-prefix` fully correct the `prefix`/`globalconfig` settings in step 5.

---

## 7. Set Node.js as the Default

Make this version the default across future WSL sessions:

```bash
nvm alias default v24.21.0
nvm use default
node --version
npm --version
```

Expected:

```text
v24.21.0
11.19.0
```

---

## 8. Install Claude Code

> **Recommended instead: the native installer.** Anthropic now recommends
> `curl -fsSL https://claude.ai/install.sh | bash`. It needs no Node.js,
> installs to `~/.local/bin/claude`, and auto-updates. If you use it, skip
> sections 4–7 and 9 (nvm, Node.js, npm config, npm install scripts). The
> end-to-end new-machine checklist is
> [dev-machine-setup.md](dev-machine-setup.md). The npm route below still
> works and is kept for machines that already manage Claude Code through nvm.

```bash
npm install -g @anthropic-ai/claude-code
```

npm 11 may block the package's `postinstall` script:

```text
npm warn install-scripts 1 package has install scripts not yet covered by allowScripts:
npm warn install-scripts   @anthropic-ai/claude-code@2.1.273 (postinstall: node install.cjs)
```

The package installs, but the `postinstall` script Claude Code needs to finish setting itself up does **not** run yet — continue to the next step.

---

## 9. Allow Claude Code's Install Script

Allow this specific package's install script at the user level, then reinstall:

```bash
npm config set allow-scripts=@anthropic-ai/claude-code --location=user
npm install -g @anthropic-ai/claude-code
```

This lets `postinstall: node install.cjs` run normally for `@anthropic-ai/claude-code@2.1.273`.

---

## 10. Verify Claude Code

```bash
which claude
claude --version
```

Expected:

```text
/home/<user>/.nvm/versions/node/v24.21.0/bin/claude
2.1.273
```

Launch it:

```bash
claude
```

This starts the Claude Code CLI and its authentication flow.

---

## 11. Migrating From a Pre-nvm Install

Before nvm was set up, Claude Code may already exist under a system-level npm prefix, e.g.:

```text
/home/<user>/.npm-global/lib
└── @anthropic-ai/claude-code@2.1.273
```

After switching to nvm, that old install drops off the active `PATH`:

```bash
which -a claude
```

An empty result here is expected and desirable — Claude Code now resolves exclusively from the nvm-managed environment:

```text
/home/<user>/.nvm/versions/node/v24.21.0/
└── bin/
    ├── node
    ├── npm
    └── claude
```

The old `~/.npm-global` install can be left in place (harmless, just unused) or removed once the nvm-managed install is confirmed working.

---

## 12. Recommended Project Location

A fresh WSL shell typically starts under the Windows-mounted filesystem:

```text
/mnt/c/Users/<user>
```

For Git/Node-heavy development, keep repositories on the **native WSL filesystem** instead:

```bash
mkdir -p ~/projects
cd ~/projects
git clone <repository-url>
cd <repository>
claude
```

Avoid working out of `/mnt/c` when possible — filesystem operations crossing the Windows/WSL boundary are slower, and the effect compounds for repositories with many small files (`node_modules/`, `.git/`, build artifacts).

---

## 13. Recommended Architecture

```text
Windows
│
├── VS Code
│     └── Remote - WSL
│               │
│               ▼
│          Ubuntu / WSL 2
│               │
│               ├── Git
│               ├── nvm
│               │    └── Node.js v24.21.0
│               ├── npm
│               ├── Claude Code
│               └── ~/projects/
│
└── Browser
      └── Claude authentication
```

Resulting WSL filesystem layout:

```text
/home/<user>/
├── .nvm/
│   └── versions/
│       └── node/
│           └── v24.21.0/
│               └── bin/
│                   ├── node
│                   ├── npm
│                   └── claude
│
└── projects/
    ├── project-a/
    ├── project-b/
    └── ...
```

Windows files remain reachable from WSL through `/mnt/c/` when needed.

---

## 14. VS Code Integration

1. Install the **WSL** extension in VS Code (on the Windows side).
2. From WSL, navigate to a project and open it in VS Code:

   ```bash
   cd ~/projects/<repository>
   code .
   ```

   VS Code opens in WSL Remote mode, using the WSL environment for the whole project.

3. In the VS Code integrated terminal (now a WSL shell), run:

   ```bash
   claude
   ```

   Claude Code then operates directly against the WSL filesystem, Git repositories, Node.js, Python, other Linux CLI tools, and the project's own build/test commands — no Windows/WSL boundary crossing during the session.

---

## 15. Final Verification Checklist

```bash
nvm --version
nvm current
node --version
npm --version
npm config get prefix
which node
which npm
which claude
claude --version
```

| Check | Expected value |
| --- | --- |
| nvm | `0.40.3` |
| Node.js | `v24.21.0` |
| npm | `v11.19.0` |
| npm prefix | `/home/<user>/.nvm/versions/node/v24.21.0` |
| `node` resolves to | `/home/<user>/.nvm/versions/node/v24.21.0/bin/node` |
| `npm` resolves to | `/home/<user>/.nvm/versions/node/v24.21.0/bin/npm` |
| `claude` resolves to | `/home/<user>/.nvm/versions/node/v24.21.0/bin/claude` |
| Claude Code | `2.1.273` |

---

## 16. Key Commands

| Task | Command |
| --- | --- |
| Start WSL | `wsl` |
| Activate default Node version | `nvm use default` |
| Start Claude Code | `claude` |
| Open a project in VS Code | `cd ~/projects/<repository> && code .` |
| Check Claude installation | `which claude && claude --version` |
| Check Node installation | `which node && node --version` |
| Check npm configuration | `npm config get prefix` / `npm config get globalconfig` |
| Resume the most recent conversation | `claude --resume` |
| Resume a specific past conversation | `claude --resume <session-id>` |
| Reattach to a running/background session | `claude attach <session-id>` |

---

## 17. Troubleshooting

### `nvm: command not found` after opening a new WSL shell

- Confirm the nvm init block was appended to `~/.bashrc` by the installer (step 4), and that the active shell actually sources `~/.bashrc` (login vs. non-login shells can skip it).
- Re-run `source ~/.bashrc` to pick it up without restarting the shell.

### npm warns about incompatible `globalconfig`/`prefix` settings

- This is the `.npmrc` conflict from [Section 5](#5-install-nodejs-lts). Run the exact command nvm suggests (`nvm use --delete-prefix <version>`) rather than manually editing `.npmrc`.

### `npm install -g @anthropic-ai/claude-code` succeeds but Claude Code doesn't work

- Check for the `install-scripts`/`allowScripts` warning from [Section 8](#8-install-claude-code) — npm 11 blocks `postinstall` scripts by default. Apply [Section 9](#9-allow-claude-codes-install-script) and reinstall.

### `which claude` returns nothing, or resolves to the wrong path

- Run `which -a claude` to list every match on `PATH`. A leftover pre-nvm install (e.g. `~/.npm-global/lib`) can shadow the nvm-managed one if `PATH` ordering is wrong — see [Section 11](#11-migrating-from-a-pre-nvm-install).
- Confirm the active Node version with `nvm current`; a different active version has its own separate `bin/claude`.

### Repository feels slow (git status, file watching, installs)

- Confirm the repository lives under `/home/<user>/...`, not `/mnt/c/...` — see [Section 12](#12-recommended-project-location). Moving it is usually a plain `git clone` into `~/projects/` followed by re-pointing VS Code's WSL Remote window at the new path.

### Claude Code / `npm install` hangs or can't reach the network behind a corporate proxy

On a corporate/VPN-managed machine, WSL can inherit a proxy configuration that either misroutes or fully blocks requests to Anthropic's endpoints and the npm registry, causing `npm install -g @anthropic-ai/claude-code` to hang and `claude` itself to fail to authenticate or reach the API. Track down where the proxy is being set before changing anything:

```bash
env | grep -i proxy
cat ~/.claude/settings.json 2>/dev/null   # rule out a proxy set inside Claude Code's own config
grep -rniE "http_proxy|https_proxy" /etc/environment /etc/profile /etc/profile.d/ /etc/bash.bashrc ~/.bashrc ~/.profile ~/.bash_profile 2>/dev/null
echo "WSLENV=$WSLENV"                     # WSL selectively imports Windows env vars named here
cmd.exe /c set 2>/dev/null | grep -i proxy
systemctl --user show-environment 2>/dev/null | grep -i proxy
cat /etc/wsl.conf
ls ~/.config/environment.d/ 2>/dev/null
```

If a proxy is genuinely required for other traffic but is blocking or mishandling Claude Code and npm, add an exception list instead of removing the proxy outright:

```bash
export NO_PROXY="api.anthropic.com,claude.ai,claude.com,platform.claude.com,downloads.claude.ai,registry.npmjs.org"
```

Add that line to `~/.bashrc` to make it persist across shells. If no proxy is actually needed for this network, clear it for the current shell instead:

```bash
unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY
```

### `uv`/`uvx` not found when Claude Code runs shell commands

This repository's own `CLAUDE.md` has Claude Code run `uv sync`, `uv run`, etc. as its normal workflow. The official `uv` installer (`curl -LsSf https://astral.sh/uv/install.sh | sh`) places `uv`/`uvx` in `~/.local/bin`, which an interactive login shell picks up via `~/.bashrc`/`~/.profile` — but not every process Claude Code or its tools spawn is guaranteed to inherit that (elevated `sudo` contexts and remote-extension-host-style processes are the same class of gotcha documented for `~/.local/bin` in the global `~/.claude/CLAUDE.md`). If a `uv`/`uvx` command fails with "command not found" only in some contexts but works in an interactive shell, symlink both binaries into a directory that's unconditionally on `PATH`:

```bash
sudo ln -s ~/.local/bin/uv /usr/local/bin/uv
sudo ln -s ~/.local/bin/uvx /usr/local/bin/uvx
```

Verify with `uv --version` from a fresh shell.

---

## 18. Companion CLI Tools for Claude Code's Git/GitHub Workflows

Claude Code drives essentially all GitHub-related work (creating/reviewing PRs, checking CI, commenting on issues) through the `gh` CLI, and signs commits it makes on your behalf using standard `git` identity configuration. Install and configure these once per machine:

```bash
sudo apt update && sudo apt install -y git-lfs gh
git lfs install
gh auth login          # choose GitHub.com → HTTPS or SSH → browser login
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
git config --global core.autocrlf input
```

- `gh auth login` is a one-time interactive, browser-based login; without it, any Claude Code workflow that shells out to `gh` (PR creation, `/generate-pr-message`, CI checks) fails.
- `git lfs install` is only needed if any repository you clone uses Git LFS.
- `core.autocrlf input` avoids CRLF/LF line-ending churn in diffs for repositories that were originally authored on Windows but are now cloned into WSL's native Linux filesystem.

---

## See Also

- Global `~/.claude/CLAUDE.md` — "Environment: Windows/PowerShell OR Linux/WSL/bash" section (shell detection rules that apply to every session on this machine, not just this repo)
- [`scripts/bash/README.md`](../scripts/bash/README.md) / [`scripts/powershell/README.md`](../scripts/powershell/README.md) — this repo's parallel bash/PowerShell dev-script sets
- [nvm](https://github.com/nvm-sh/nvm) — Node Version Manager
- [Claude Code documentation](https://docs.claude.com/en/docs/claude-code)
