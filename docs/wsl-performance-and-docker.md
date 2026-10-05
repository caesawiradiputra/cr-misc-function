# WSL 2 Performance Tuning & Docker Setup

Companion to [claude-code-wsl-setup.md](claude-code-wsl-setup.md) (installing
Claude Code itself) and [dev-machine-setup.md](dev-machine-setup.md) (the
full new-machine checklist). This guide covers making an already-working
WSL 2 / Ubuntu install **faster and more resource-efficient**, and setting up
**Docker inside WSL** the way this repo's workflows expect it — native
engine, off by default, capped builds.

Paths below use `<user>` for whichever WSL/Windows username is active on
your machine — substitute your own.

---

## Table of Contents

- [1. Tune `.wslconfig`](#1-tune-wslconfig)
- [2. Docker: Native Engine, Not Docker Desktop](#2-docker-native-engine-not-docker-desktop)
- [3. Keep Docker's Footprint Small](#3-keep-dockers-footprint-small)
- [4. Capped, Backgrounded Builds](#4-capped-backgrounded-builds)
- [5. Diagnosing "WSL Feels Slower Than Windows"](#5-diagnosing-wsl-feels-slower-than-windows)
- [See Also](#see-also)

---

## 1. Tune `.wslconfig`

`.wslconfig` is a **Windows-side** file, not a WSL one — it lives at
`C:\Users\<user>\.wslconfig` and applies to every WSL distro on the machine.
A ready-to-copy version with inline comments is at
[`templates/wsl/.wslconfig`](../templates/wsl/.wslconfig); copy it in from
PowerShell:

```powershell
Copy-Item .\templates\wsl\.wslconfig "$env:UserProfile\.wslconfig" -Force
```

What it sets, and why:

| Setting | Purpose |
| --- | --- |
| `memory` / `processors` / `swap` | Caps WSL's host resource usage instead of letting it claim everything, so Windows itself stays responsive. Size to roughly 50-75% of total RAM and most-but-not-all cores — the template's `16GB`/`8`/`8GB` assumes a 32GB+/8-core+ host; adjust for your own machine. |
| `autoProxy` | Mirrors the Windows host's proxy configuration into WSL automatically. Fixes WSL-side downloads being throttled or misrouted relative to the same transfer on Windows, without hardcoding a proxy address — portable across networks and machines. |
| `sparseVhd` (experimental) | WSL's virtual disk shrinks back down instead of only ever growing. |
| `autoMemoryReclaim` (experimental) | Idle memory inside WSL is handed back to Windows instead of being held onto up to the `memory=` cap. |
| `networkingMode=mirrored` / `dnsTunneling` (commented out) | Fallback for Windows 11 22H2+ if `autoProxy=true` alone doesn't fix a WSL network that's genuinely slower than Windows — see [section 5](#5-diagnosing-wsl-feels-slower-than-windows) before turning these on; they're a bigger networking-mode change than `autoProxy`. |

**Changes only take effect after a full restart of the WSL VM:**

```powershell
wsl --shutdown
```

This kills **every** running WSL process across **every** distro — any
in-progress Docker build, running server, or open Claude Code session dies
with it. Never run it while one of those is in flight; finish or stop it
first.

---

## 2. Docker: Native Engine, Not Docker Desktop

Inside WSL, install Docker as a native Linux engine rather than relying on
Docker Desktop's Windows-side CLI reached through interop:

```bash
sudo apt-get update
sudo apt-get install -y docker.io docker-buildx
sudo usermod -aG docker "$USER"   # then log out/in (or restart the WSL session) for the group to apply
```

Why native instead of Docker Desktop:

- If Docker Desktop's WSL integration is off (or isn't installed at all),
  `docker` on `PATH` inside WSL resolves to nothing, or to the Windows CLI
  via interop, which fails with "could not be found in this WSL distro" the
  moment integration is off.
- Docker Desktop's background VM and its own resource management stack on
  top of WSL can compound with `.wslconfig`'s own caps and crash WSL,
  especially on an already resource-constrained machine.
- Some corporate security policies block pulling images through Docker
  Desktop on Windows specifically, while a native `apt`-installed engine
  inside WSL is unaffected.

---

## 3. Keep Docker's Footprint Small

Don't leave the Docker daemon running all the time if you only need it
occasionally for build tests — it holds memory and CPU even idle:

```bash
sudo systemctl disable docker.service docker.socket   # don't auto-start on boot
sudo systemctl start docker                            # start only when you need it
# ... do your build/test ...
sudo systemctl stop docker.service docker.socket        # stop it when done
```

Before assuming it's off, check — don't guess:

```bash
systemctl is-active docker
```

`sudo` prompts for a password interactively and can't be driven from an
automated/agent session — run these `sudo systemctl ...` commands yourself
in a real terminal rather than asking an agent to run them for you.

---

## 4. Capped, Backgrounded Builds

Cap build memory explicitly instead of letting a build consume up to
`.wslconfig`'s full `memory=` allowance (which starves everything else,
Windows included, while it runs):

```bash
docker build --memory=6g --memory-swap=6g -t my-image .
```

Leave headroom below `.wslconfig`'s cap — e.g. `--memory=6g` against a
`memory=16GB` WSL cap, not `--memory=16g`.

A base-image pull plus package installs (`apt-get`, ODBC drivers, etc.) can
take many minutes, especially over a slow connection — run the build in the
background with output captured to a log file rather than blocking a
terminal on it:

```bash
nohup docker build --memory=6g --memory-swap=6g -t my-image . > build.log 2>&1 &
tail -f build.log   # watch progress; Ctrl+C to stop watching without stopping the build
```

---

## 5. Diagnosing "WSL Feels Slower Than Windows"

Work through these in order before concluding WSL's networking itself is at
fault:

1. **Confirm the config actually changed.** Check
   `C:\Users\<user>\.wslconfig` has the values you expect, and that you ran
   `wsl --shutdown` *after* editing it (section 1) — a stale VM still running
   the old config is the single most common cause of "I changed it and
   nothing happened."
2. **Compare the identical transfer, back-to-back, more than once.** A
   single slow run proves nothing — network conditions vary run to run.
   Download the exact same file by size by both routes and compare:

   ```bash
   # inside WSL
   curl -o /dev/null -s -w 'wsl: %{speed_download} bytes/sec | %{time_total}s\n' \
     --max-time 60 "https://speed.cloudflare.com/__down?bytes=25000000"
   ```

   ```powershell
   # native Windows PowerShell (not via WSL interop — a genuinely separate run)
   curl.exe -o NUL -s -w "windows: %{speed_download} bytes/sec | %{time_total}s`n" `
     --max-time 60 "https://speed.cloudflare.com/__down?bytes=25000000"
   ```

   Run each two or three times. `curl.exe` reached *through WSL interop*
   (i.e. typed into a WSL shell) is a genuine native Windows process using
   Windows' own network stack — if it's also slower than the same command
   typed directly into a native PowerShell window, the gap isn't about WSL's
   virtualized networking at all, since the interop-launched copy never
   touched WSL's NAT path either.
3. **Rule out the underlying connection itself.** If *both* WSL and native
   Windows are slow at the same time, check an independent speed test
   (e.g. speedtest.net) before chasing a WSL-specific cause — a weak or
   congested uplink (mobile/cellular connections especially, which often show
   fine idle ping but high latency under load — bufferbloat) will bottleneck
   every path identically and looks identical to a WSL networking bug if you
   only ever test from inside WSL.
4. **Only then reach for `.wslconfig`'s network fallbacks** —
   `networkingMode=mirrored` + `dnsTunneling=true` (Windows 11 22H2+), or a
   lower MTU (e.g. `1400`) if on a VPN — and re-run the same back-to-back
   comparison from step 2 afterward to confirm it actually helped, rather
   than assuming it did.

---

## See Also

- [`templates/wsl/.wslconfig`](../templates/wsl/.wslconfig) — copyable config with inline comments
- [claude-code-wsl-setup.md](claude-code-wsl-setup.md) — installing Claude Code itself inside WSL, nvm/npm route, corporate proxy troubleshooting for Claude Code/npm specifically
- [dev-machine-setup.md](dev-machine-setup.md) — full new-machine checklist this guide is a companion to
- [WSL `.wslconfig` reference (Microsoft Learn)](https://learn.microsoft.com/en-us/windows/wsl/wsl-config)
- [Docker Engine install docs (Ubuntu)](https://docs.docker.com/engine/install/ubuntu/)
