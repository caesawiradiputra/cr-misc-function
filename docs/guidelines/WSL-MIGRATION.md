# Moving to a New Laptop: WSL Backup, Rebuild and Restore

The end-to-end runbook for leaving one WSL 2 / Ubuntu machine and rebuilding the same working setup on another: what to save, how to install WSL from nothing, how to set up the network, tools and Claude Code, and how to restore repos, memory and secrets. Work top to bottom.

It builds on two existing guides and links to them instead of repeating them: [dev-machine-setup.md](../dev-machine-setup.md) (tools, Claude config, IDEs) and [wsl-performance-and-docker.md](../wsl-performance-and-docker.md) (`.wslconfig`, Docker). Values in angle brackets (`<PAC_URL>`, `<WINDOWS_USERNAME>`) are yours to fill in; this repo is public. The Windows side (tools, support apps, tuning, moving it) is in [WINDOWS-DEV-LAPTOP.md](WINDOWS-DEV-LAPTOP.md).

## 1. What survives and how

| What | Where it comes back from |
| --- | --- |
| Repos with a pushed branch | `git clone` from the remote |
| Uncommitted changes, stashes, local-only branches, ignored `scratch/` and `release/` folders | The backup archive (`wsl-migration-backup.sh repos`) |
| Repos with no remote | Their own full archive in the backup |
| Skills, commands, hooks, rules, settings (Claude Code) | This repo's `CLAUDE/` template, or the exact copy in the backup |
| Logbook, preference registry, state, per-project memory | The backup (`claude/claude-config.tar.gz`); never in this public repo |
| `.env` files and credentials | The encrypted `secrets.tar.gpg` in the backup, or re-issued by logging in again |
| Installed packages and tools | Re-installed from the lists in `inventory/` and sections 5 to 7 |
| Session transcripts | Not saved by default (large, may hold secrets) |

Anything you are happy to rebuild from scratch (settings tuned long ago, plugins you no longer use) does not need to be restored: the template is the clean baseline, the backup is the exact copy.

## 2. On the old laptop, before you leave

### 2.1 Push what can be pushed

Work that is on a pushed branch is safe. List what is not:

```bash
./scripts/bash/wsl-migration-backup.sh repos --out /tmp/preview --dry-run | grep -E "local-only|at-risk"
```

Commit and push finished work on its branch. Leave genuinely half-done work as it is: the backup keeps uncommitted changes and stashes.

### 2.2 Run the backup

Pick an output folder that survives the switch: your Windows user folder (IT copies it to the new laptop), a network drive, or cloud storage you can reach from the new laptop.

```bash
OUT=/mnt/c/Users/<WINDOWS_USERNAME>/Documents/WSL-Migration/$(date +%F)
./scripts/bash/wsl-migration-backup.sh all --out "$OUT"       # inventory, repos, Claude config (no secrets)
./scripts/bash/wsl-migration-backup.sh verify --out "$OUT"    # every archive and bundle is readable
```

Then, in a normal terminal (gpg asks for a passphrase on the terminal):

```bash
./scripts/bash/wsl-migration-backup.sh secrets --out "$OUT"
```

This writes `secrets.tar.gpg` (`.env` files, cloud and GitHub credentials, `~/.claude.json`, shell dotfiles that mention secrets). Remember the passphrase: without it the file is useless, and nothing else can recover it. `secrets.manifest.txt` lists the paths, never the contents.

What the output folder holds:

```text
MANIFEST.tsv        every repo: remote, branch, HEAD, class (clean | at-risk | local-only), artifacts
inventory/          OS, tool versions, apt and npm lists, VS Code extensions, WSL config
repos/              per repo: .full.tar.gz | .bundle, .stash-N.patch, .tracked.patch, .extra.tar.gz
claude/             claude-config.tar.gz
secrets.tar.gpg     encrypted (only after the `secrets` command)
```

### 2.3 Windows-side items the script does not copy

- `C:\Users\<WINDOWS_USERNAME>\.wslconfig` (a copy is in `inventory/wslconfig.windows.txt`).
- VS Code and Antigravity user settings and keybindings (turn on Settings Sync, or copy the `User` folder).
- Windows Terminal profile, Git Credential Manager sign-ins, browser sign-ins used by `gh auth login`.
- Anything you keep under `/mnt/c` is already on Windows and moves with the user folder.

### 2.4 Last check

- `wsl-migration-backup.sh verify` printed `all readable`.
- The output folder is on storage the new laptop can read, and you have opened one archive from there.
- The passphrase is stored somewhere other than the old laptop.
- Do not wipe the old laptop until section 9 passes on the new one.

## 3. New laptop: install WSL

On Windows, with virtualization enabled in the firmware (BIOS or UEFI), in an **admin** PowerShell:

```powershell
wsl --install -d Ubuntu-24.04     # enables the needed Windows features and installs the distro
```

Restart when asked, then finish the first start: Ubuntu asks for a Linux username and password. Use the same username as before if you want the restored paths (`/home/<user>/...`) to match without edits.

Then update WSL itself and confirm the version:

```powershell
wsl --update
wsl --set-default-version 2
wsl --version        # reference setup: WSL 2.5.10.0, kernel 6.6.87.2-1
wsl -l -v            # the distro must show VERSION 2
```

## 4. Configure WSL

### 4.1 `.wslconfig` (Windows side, `C:\Users\<WINDOWS_USERNAME>\.wslconfig`)

```ini
[wsl2]
memory=16GB
processors=8
swap=8GB
autoProxy=true
# networkingMode=mirrored
# dnsTunneling=true

[experimental]
sparseVhd=true
autoMemoryReclaim=gradual
```

Size `memory` and `processors` to the new machine (the reference machine gave WSL the whole host: 16 GB, 8 CPUs). `autoProxy=true` is the network fix described in section 5. A change takes effect only after `wsl --shutdown`, which stops every WSL process, including running builds and Claude sessions.

### 4.2 `/etc/wsl.conf` (inside Ubuntu)

Systemd on (needed for Docker and other services) and the default user:

```bash
sudo tee /etc/wsl.conf >/dev/null <<'EOF'
[boot]
systemd=true

[user]
default=<linux-user>
EOF
```

Apply with `wsl --shutdown` from PowerShell, then open Ubuntu again.

### 4.3 Update the system and install base packages

```bash
sudo apt update && sudo apt full-upgrade -y
sudo apt install -y git curl wget jq gnupg ca-certificates unzip build-essential unixodbc-dev
```

`unixodbc-dev` is needed by `pyodbc`; `unzip` is not installed by default. Add other system libraries a repo asks for when its dependencies fail to build.

## 5. Network: proxy bypass and download speed

On a corporate network the symptoms are slow downloads from WSL (far below Windows), `ERR_PROXY_TUNNEL`, or tools that cannot reach the internet at all.

1. **Let WSL use the Windows proxy.** `autoProxy=true` in `.wslconfig` (section 4.1) makes WSL follow the proxy and PAC settings Windows uses (the PAC address shows up as `WSL_PAC_URL`). This was the whole fix on the reference machine: a base-image pull went from about 0.1 MB/s to the same 0.5 to 1.3 MB/s that Windows gets. `networkingMode=mirrored` and `dnsTunneling=true` were not needed. Do not export `http_proxy` by hand unless a tool still fails; `autoProxy` does not set those variables, and their absence is not a sign it is off.
2. **Measure against Windows, not against a feeling.** Download the same file from both sides and compare:

   ```bash
   curl -o /dev/null -sS -w '%{speed_download} bytes/s\n' <URL-OF-A-25MB-FILE>      # WSL
   ```

   ```powershell
   curl.exe -o NUL -sS -w '%{speed_download} bytes/s\n' <URL-OF-A-25MB-FILE>        # Windows
   ```

   Similar numbers mean WSL is not the bottleneck. Mobile or shared uplinks vary 2 to 3 times between runs; check an independent speed test before chasing a WSL cause.
3. **Keep Claude Code's own hosts off the proxy.** A long-running or resumed session can fail with `ERR_PROXY_TUNNEL` while a fresh `claude` works. In `~/.claude/settings.json`:

   ```json
   "env": {
     "NO_PROXY": "api.anthropic.com,claude.ai,claude.com,platform.claude.com,.anthropic.com,.claude.ai,.claude.com,mcp.context7.com"
   }
   ```

   This is scoped to Claude Code only; `apt`, `pip` and `git` keep using the proxy. Verify each host returns a real HTTP status with `curl -sS -o /dev/null -w '%{http_code}\n' https://<host>` (not `000`) before relying on it, and restart sessions after changing it. The `CLAUDE/linux-wsl/settings.json` template already contains it.
4. **If `apt` or a tool still cannot connect**, check `curl -I https://example.com` first, then `wsl --shutdown` and retry (a stale tunnel from before a restart is the usual cause). Only then set a proxy for that one tool, with your PAC-derived proxy address: `Acquire::http::Proxy "<CORP_PROXY>";` in `/etc/apt/apt.conf.d/95proxy` for apt, or `HTTPS_PROXY` for a single command.
5. **Certificate errors** (`unable to get local issuer certificate`) mean the proxy re-signs traffic. Install the company root certificate: copy it to `/usr/local/share/ca-certificates/<name>.crt`, run `sudo update-ca-certificates`, and for Node tools export `NODE_EXTRA_CA_CERTS=/etc/ssl/certs/ca-certificates.crt`. This was not needed on the reference machine; it is here as the standard remedy.
6. **Off the office network** the proxy host may be unreachable (VPN off). Tools then time out on the proxy address; reconnect to the VPN or office network rather than changing configuration.

More on speed diagnosis and Docker: [wsl-performance-and-docker.md](../wsl-performance-and-docker.md).

## 6. Install the tools

```bash
# uv (Python package manager; also installs Python versions on demand)
curl -LsSf https://astral.sh/uv/install.sh | sh

# GitHub CLI (Ubuntu package; the official apt repo in dev-machine-setup.md gives a newer one)
sudo apt install -y gh

# Node via nvm (reference: Node 24.x LTS line)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash   # use the current nvm release
. "$HOME/.nvm/nvm.sh"
nvm install --lts && nvm alias default 'lts/*'

# Claude Code (native installer; run it inside WSL, not from PowerShell)
curl -fsSL https://claude.ai/install.sh | bash
```

Make sure `~/.local/bin` is on `PATH` (a new login shell does it; `uv` and `claude` live there). Check:

```bash
git --version && gh --version && jq --version && uv --version && node --version && claude --version
```

Docker is optional and intentionally off by default (a native engine, not Docker Desktop): `sudo apt install -y docker.io docker-buildx`, then `sudo systemctl disable docker.service docker.socket` and start it only for build tests. Add yourself to the `docker` group with `sudo usermod -aG docker $USER` and start a new login. Build with a memory cap and in the background; see [wsl-performance-and-docker.md](../wsl-performance-and-docker.md).

Git identity and GitHub sign-in:

```bash
git config --global user.name  "<Your Name>"
git config --global user.email "<you@example.com>"
gh auth login && gh auth setup-git
```

## 7. Restore Claude Code, secrets and repos

Copy the backup folder to the new machine (for example from the Windows user folder: `/mnt/c/Users/<WINDOWS_USERNAME>/Documents/WSL-Migration/<date>`) and set `FROM` to it. Get the scripts by cloning this repo first (`git clone https://github.com/<owner>/cr-misc-function.git`, public). The backup also holds copies in its `tools/` folder, which you can run before GitHub works.

```bash
FROM=/mnt/c/Users/<WINDOWS_USERNAME>/Documents/WSL-Migration/<date>
./scripts/bash/wsl-migration-restore.sh plan --from "$FROM"          # read-only summary
```

### 7.1 Claude Code: two ways, pick one

| | A. Exact restore (recommended) | B. Rebuild from the template |
| --- | --- | --- |
| Command | `wsl-migration-restore.sh claude --from "$FROM"` | follow [dev-machine-setup.md](../dev-machine-setup.md) section 4 |
| You get | The same `CLAUDE.md`, rules, skills (with real ids), commands, hooks, logbook, registry, state and memory as before | The clean baseline from `CLAUDE/`; placeholders to fill; no memory or logbook data |
| Use when | You want the setup exactly as it was | You want to re-initiate outdated config and keep only the template |

You can combine them: restore (A), then diff against the template and keep what you prefer. After either path:

- Reinstall the plugins named in `plugins/installed_plugins.json` (`/plugin`), then run `/mcp` and log in to each MCP server again.
- Run `claude doctor`; the settings must validate.
- The exact restore refuses to overwrite an existing `~/.claude/CLAUDE.md` unless you pass `--force`.

### 7.2 Secrets

```bash
./scripts/bash/wsl-migration-restore.sh secrets --from "$FROM"      # asks for the passphrase
```

This puts `.env` files back in their repos and credentials in `~/.aws`, `~/.config/gh` and the like. If you chose not to keep secrets, the paths are in `secrets.manifest.txt`: re-issue each key or token instead.

### 7.3 Repos

Sign in first (`gh auth login`), then:

```bash
./scripts/bash/wsl-migration-restore.sh repos --from "$FROM"
```

For each repo it clones the remote, checks out the saved branch, and re-applies the saved work:

- local-only repos are unpacked from their own archive;
- local branches missing on the remote are recreated; a branch whose tip differs is kept as `restored/<name>`;
- each stash becomes a branch `restored/stash-<n>` on its old base commit (inspect, cherry-pick or delete);
- uncommitted changes are applied as a patch; untracked and ignored files (such as `scratch/`) are unpacked, existing files are kept.

A repo is marked done in `.git/wsl-restore.done`, so a re-run skips it unless you pass `--force`. If a clone fails, sign in and re-run. `.env` files come from the secrets step, not from here.

## 8. Editors

Install VS Code on **Windows** (not inside Ubuntu) and the **WSL** extension (`ms-vscode-remote.remote-wsl`), then open a repo with `code .` from the WSL shell. Install the recommended extensions from `templates/vscode/extensions.json` inside the WSL window. Antigravity and other IDEs follow [dev-machine-setup.md](../dev-machine-setup.md) sections 5 and 6.

Known editor problems and fixes:

- **Blank Markdown preview with "unexpected error occurred while restoring"**: a saved preview tab is stale. Close all preview tabs, run `Developer: Reload Window`, open a fresh preview. Close previews before you quit VS Code.
- **Python extension error mentioning `pet`** on a WSL-remote Antigravity or VS Code window: the installed `ms-python.python` build is missing its native locator binary; the fix is in the global `CLAUDE.md` ("On a WSL-remote Antigravity/VS Code session...").
- **`uv` not found by the extension host**: it does not inherit `~/.local/bin`; see [claude-code-wsl-setup.md](../claude-code-wsl-setup.md).

## 9. Verify the new machine

- [ ] `wsl --version` shows WSL 2.x and `wsl -l -v` shows VERSION 2.
- [ ] `curl` speed from WSL is in the same range as `curl.exe` on Windows.
- [ ] `git`, `gh`, `jq`, `uv`, `node`, `claude` all print versions; `gh auth status` is signed in.
- [ ] `claude doctor` passes; the status line shows; `/` lists the commands; `/plugin` and `/mcp` look right.
- [ ] The first prompt in a repo shows the SessionStart repo context.
- [ ] `wsl-migration-restore.sh plan` and a `git status` in three repos match what you expect (branch, uncommitted work, stashes as `restored/stash-*`).
- [ ] The logbook works: `python3 ~/.claude/skills/logbook/logbook.py week`.
- [ ] `uv run pytest` passes in this repo.
- [ ] Only now: wipe or hand back the old laptop.

## 10. Re-run the backup later

The scripts are repeatable. Running the backup again into a new dated folder gives a fresh snapshot; the restore side is safe to rehearse into a scratch folder first:

```bash
./scripts/bash/wsl-migration-restore.sh repos --from "$FROM" --repos-root /tmp/rehearsal --no-clone
./scripts/bash/wsl-migration-restore.sh claude --from "$FROM" --claude-dir /tmp/rehearsal/.claude
```
