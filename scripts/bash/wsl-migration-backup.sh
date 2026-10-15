#!/usr/bin/env bash
# Backs up what a WSL distro holds that git and a fresh install cannot bring back,
# so the distro can be destroyed (new laptop, reinstall) and rebuilt.
#
# It saves, into one output folder:
#   - inventory/   OS, tool versions, apt/npm/uv/gh lists, VS Code extensions, WSL config
#   - MANIFEST.tsv every git repo with its remote, branch, HEAD and risk class
#   - repos/       per repo, only what the remote cannot restore:
#                    local-only repo (no remote)  -> full tar.gz of the working tree
#                    repo with unpushed or unsaved work -> git bundle (all refs and local
#                      branches), one patch per stash (a bundle keeps only the newest),
#                      the tracked patch, and a tar.gz of the untracked and ignored
#                      files (size-capped, secrets left out)
#                    clean repo with a pushed branch -> manifest line only (re-clone)
#   - claude/      ~/.claude config, commands, skills, hooks, logbook, registry, state
#                  and per-project memory folders (no credentials, no transcripts)
#   - tools/       copies of the backup and restore scripts and the runbook
#   - secrets.tar.gpg (only with the `secrets` command) .env files and credential files,
#                  encrypted with a passphrase you type; the plain tar never leaves RAM
#
# Nothing is read from or written to a git repo: it only runs read-only git commands.
#
# Usage:
#   ./scripts/bash/wsl-migration-backup.sh <command> --out <dir> [options]
#
# Commands:
#   all        inventory + repos + claude + a copy of these scripts (no secrets). Default.
#   inventory  system, tools and package lists only
#   repos      MANIFEST.tsv and the per-repo artifacts
#   claude     ~/.claude config and memory
#   secrets    encrypted bundle of .env files and credential files (asks for a passphrase)
#   verify     check that every archive and bundle in --out can be read
#
# Options:
#   --out <dir>            Output folder (required). Put it where the new laptop can read it.
#   --repos-root <dir>     Where the repos live. Default: $HOME/repo
#   --claude-dir <dir>     Default: $HOME/.claude
#   --max-ignored-mb <N>   Skip an ignored file or folder larger than N MB per repo. Default: 50
#   --dry-run              Show what would be written, write nothing.
#   -h, --help             Show this help and exit.
#
# Run `secrets` from a normal terminal: gpg asks for the passphrase on the terminal.
set -uo pipefail

usage() { sed -n '2,/^set -uo/p' "$0" | sed '$d' | sed 's/^# \{0,1\}//'; }

cmd="all"
out=""
repos_root="$HOME/repo"
claude_dir="$HOME/.claude"
max_ignored_mb=50
dry_run=false

if [ $# -gt 0 ] && [[ "$1" != -* ]]; then cmd="$1"; shift; fi
while [ $# -gt 0 ]; do
    case "$1" in
        --out) out="$2"; shift 2 ;;
        --repos-root) repos_root="$2"; shift 2 ;;
        --claude-dir) claude_dir="$2"; shift 2 ;;
        --max-ignored-mb) max_ignored_mb="$2"; shift 2 ;;
        --dry-run) dry_run=true; shift ;;
        -h|--help) usage; exit 0 ;;
        *) echo "Unknown option: $1" >&2; exit 1 ;;
    esac
done
case "$cmd" in all|inventory|repos|claude|secrets|verify) ;; *) echo "Unknown command: $cmd" >&2; exit 1 ;; esac
[ -n "$out" ] || { echo "error: --out <dir> is required" >&2; exit 1; }

EXCLUDES=(--exclude=.venv --exclude=venv --exclude=node_modules --exclude=__pycache__
          --exclude=.mypy_cache --exclude=.ruff_cache --exclude=.pytest_cache --exclude=.tox)
HEAVY_RE='(^|/)(\.venv|venv|node_modules|__pycache__|\.mypy_cache|\.ruff_cache|\.pytest_cache|\.tox)(/|$)'
SECRET_RE='token|secret|password|passwd|api[_-]?key|private[_-]?key|BEGIN [A-Z ]*PRIVATE'

log() { printf '%s\n' "$*"; }
# Run an external command with a time limit and no stdin, so a slow or interactive tool cannot hang the backup.
quick() { timeout 20 "$@" </dev/null 2>/dev/null; }
run() { if $dry_run; then log "[dry-run] $*"; else "$@"; fi; }
safe_name() { printf '%s' "$1" | sed 's#/#__#g'; }
kb() { du -sk "$1" 2>/dev/null | cut -f1; }

# Print (NUL-separated) the files under $1 that look like secrets: .env files, keys,
# certificates, service-account and credentials JSON. Example/sample/template files are
# not secrets. These never go into the plain archives, only into the encrypted bundle.
secret_find() {
    find "$1" -regextype posix-extended \( -name node_modules -o -name .venv -o -name venv -o -name .git \) -prune -o \
        -type f -iregex '.*/(\.env(\..*)?|.*\.(pem|key|p12|pfx|jks|tfvars)|id_(rsa|ed25519|ecdsa).*|.*credentials.*\.json|service[-_]?account.*\.json)' \
        ! -iregex '.*\.(example|sample|template)$' -print0 2>/dev/null
}

# Write the secret-looking files under $1, relative to $2, one per line, for tar --exclude-from.
secret_excludes() {
    local base="$1" rel_to="$2" f
    secret_find "$base" | while IFS= read -r -d '' f; do printf '%s\n' "${f#"$rel_to"/}"; done
}

find_repos() {
    find "$repos_root" -maxdepth 4 -name .git \( -type d -o -type f \) -prune 2>/dev/null \
        | sed 's#/\.git$##' | sort
}

do_inventory() {
    log "== inventory"
    local d="$out/inventory"
    run mkdir -p "$d/dotfiles"
    $dry_run && return 0
    {
        echo "# generated $(date -Iseconds)"; lsb_release -ds 2>/dev/null; uname -r
        echo "## /etc/wsl.conf"; cat /etc/wsl.conf 2>/dev/null
    } > "$d/system.txt"
    local win_home=""
    # WSL_MIGRATION_FAST=1 skips the slow probes (Windows interop, version and MCP checks); tests use it.
    if [ "${WSL_MIGRATION_FAST:-}" != 1 ]; then
        win_home=$(wslpath "$(quick cmd.exe /c 'echo %USERPROFILE%' | tr -d '\r')" 2>/dev/null || true)
    fi
    if [ -n "$win_home" ] && [ -f "$win_home/.wslconfig" ]; then cp "$win_home/.wslconfig" "$d/wslconfig.windows.txt"; fi
    [ "${WSL_MIGRATION_FAST:-}" = 1 ] || {
        for c in git gh uv python3 node npm docker claude code jq curl gpg; do
            printf '%s: ' "$c"
            if command -v "$c" >/dev/null 2>&1; then quick "$c" --version | head -1; else echo missing; fi
        done
    } > "$d/tools.txt"
    quick apt-mark showmanual | sort > "$d/apt-manual.txt"
    quick npm ls -g --depth=0 > "$d/npm-global.txt"
    quick uv tool list > "$d/uv-tools.txt"
    quick gh extension list > "$d/gh-extensions.txt"
    # Read the extension folders instead of running `code`, which starts a server and can hang.
    for ext in "$HOME/.vscode-server/extensions" "$HOME/.antigravity-ide-server/extensions"; do
        [ -d "$ext" ] && { echo "# $ext"; ls -1 "$ext" | grep -v '^extensions.json$'; }
    done > "$d/vscode-extensions.txt"
    quick crontab -l > "$d/crontab.txt"
    quick systemctl list-unit-files --state=enabled --no-pager > "$d/systemd-enabled.txt"
    git config --global --list 2>/dev/null | grep -viE 'token|password|credential' > "$d/git-global-config.txt"
    [ "${WSL_MIGRATION_FAST:-}" = 1 ] || quick claude mcp list > "$d/claude-mcp-list.txt"
    for f in .bashrc .profile .bash_aliases .gitconfig; do
        [ -f "$HOME/$f" ] || continue
        if grep -qiE "$SECRET_RE" "$HOME/$f"; then
            echo "$f: looks like it holds a secret, left out (it goes in the secrets bundle)" >> "$d/dotfiles/SKIPPED.txt"
        else
            cp "$HOME/$f" "$d/dotfiles/$f"
        fi
    done
    log "   wrote $d"
}

# Echo the files/dirs of a repo that git ignores or does not track, one NUL-terminated
# path per line, skipping caches and anything larger than the size cap.
extra_files() {
    local repo="$1" skipped="$2"
    local cap=$((max_ignored_mb * 1024))
    {
        git -C "$repo" ls-files -z --others --exclude-standard
        git -C "$repo" ls-files -z --others --ignored --exclude-standard --directory 2>/dev/null
    } | tr '\0' '\n' | sort -u | while IFS= read -r p; do
        [ -n "$p" ] || continue
        if [[ "$p" =~ $HEAVY_RE ]]; then continue; fi
        local sz
        sz=$(kb "$repo/$p"); sz=${sz:-0}
        if [ "$sz" -gt "$cap" ]; then echo "$p (${sz} KB)" >> "$skipped"; continue; fi
        printf '%s\0' "$p"
    done
}

do_repos() {
    log "== repos under $repos_root"
    run mkdir -p "$out/repos"
    local manifest="$out/MANIFEST.tsv"
    $dry_run || printf 'path\tremote\tbranch\thead\tclass\tdirty\tstash\tahead\tlocal_branches\tartifacts\tskipped\n' > "$manifest"
    local repo rel safe remote branch head dirty stash up ahead localbr class art skipped_file skipped
    while IFS= read -r repo; do
        [ -n "$repo" ] || continue
        rel="${repo#"$repos_root"/}"; safe=$(safe_name "$rel")
        remote=$(git -C "$repo" remote get-url origin 2>/dev/null || true)
        branch=$(git -C "$repo" branch --show-current 2>/dev/null || true)
        head=$(git -C "$repo" rev-parse --short HEAD 2>/dev/null || echo none)
        dirty=$(git -C "$repo" status --porcelain 2>/dev/null | wc -l)
        stash=$(git -C "$repo" stash list 2>/dev/null | wc -l)
        up=$(git -C "$repo" rev-parse --abbrev-ref '@{u}' 2>/dev/null || true)
        if [ -n "$up" ]; then ahead=$(git -C "$repo" rev-list --count '@{u}..HEAD' 2>/dev/null || echo 0); else ahead="none"; fi
        localbr=$(git -C "$repo" for-each-ref --format='%(refname:short) %(upstream)' refs/heads 2>/dev/null | awk 'NF==1' | wc -l)
        art=""; skipped=""
        skipped_file=$(mktemp)
        if [ -z "$remote" ]; then
            class="local-only"
            art="repos/$safe.full.tar.gz"
            log "   $rel: local-only -> $art"
            local sec_ex; sec_ex=$(mktemp)
            secret_excludes "$repo" "$repos_root" > "$sec_ex"
            run tar -czf "$out/$art" "${EXCLUDES[@]}" --exclude-from="$sec_ex" -C "$repos_root" "$rel"
            rm -f "$sec_ex"
        else
            local extra_list; extra_list=$(mktemp)
            extra_files "$repo" "$skipped_file" > "$extra_list"
            local has_extra=false; [ -s "$extra_list" ] && has_extra=true
            local unpushed=false
            if [ "$ahead" != "none" ] && [ "${ahead:-0}" != "0" ]; then unpushed=true; fi
            if [ "$dirty" -gt 0 ] || [ "$stash" -gt 0 ] || [ "$localbr" -gt 0 ] || $unpushed || $has_extra; then
                class="at-risk"
                if [ "$stash" -gt 0 ] || [ "$localbr" -gt 0 ] || $unpushed; then
                    art="$art repos/$safe.bundle"
                    run git -C "$repo" bundle create "$out/repos/$safe.bundle" --all >/dev/null 2>&1
                fi
                if [ "$stash" -gt 0 ]; then
                    # A bundle keeps only the newest stash, so every stash is exported as a patch.
                    art="$art repos/$safe.stashes.tsv"
                    if ! $dry_run; then
                        printf 'n\tbase\tmessage\n' > "$out/repos/$safe.stashes.tsv"
                        local n
                        for ((n = 0; n < stash; n++)); do
                            printf '%s\t%s\t%s\n' "$n" "$(git -C "$repo" rev-parse "stash@{$n}^1")" \
                                "$(git -C "$repo" log -1 --format=%s "stash@{$n}")" >> "$out/repos/$safe.stashes.tsv"
                            git -C "$repo" stash show -p -u --binary "stash@{$n}" > "$out/repos/$safe.stash-$n.patch" 2>/dev/null
                        done
                    fi
                    art="$art repos/$safe.stash-*.patch"
                fi
                if [ "$dirty" -gt 0 ]; then
                    art="$art repos/$safe.tracked.patch"
                    $dry_run || git -C "$repo" diff HEAD --binary > "$out/repos/$safe.tracked.patch"
                fi
                if $has_extra; then
                    art="$art repos/$safe.extra.tar.gz"
                    local sec_ex; sec_ex=$(mktemp)
                    secret_excludes "$repo" "$repo" > "$sec_ex"
                    run tar -czf "$out/repos/$safe.extra.tar.gz" --exclude-from="$sec_ex" -C "$repo" --null -T "$extra_list"
                    rm -f "$sec_ex"
                fi
                log "   $rel: at-risk (dirty=$dirty stash=$stash local-branches=$localbr ahead=$ahead extra=$has_extra)"
            else
                class="clean"
            fi
            rm -f "$extra_list"
        fi
        [ -s "$skipped_file" ] && skipped=$(paste -sd';' "$skipped_file")
        rm -f "$skipped_file"
        # An empty field is written as "-": `read` with a tab separator would otherwise merge
        # consecutive tabs and shift every later column.
        $dry_run || printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
            "$rel" "${remote:--}" "${branch:--}" "$head" "$class" "$dirty" "$stash" "$ahead" "$localbr" \
            "${art# }" "${skipped:--}" >> "$manifest"
    done < <(find_repos)
    $dry_run || log "   wrote $manifest ($(($(wc -l < "$manifest") - 1)) repos)"
}

do_claude() {
    log "== claude config from $claude_dir"
    [ -d "$claude_dir" ] || { echo "error: $claude_dir not found" >&2; return 1; }
    run mkdir -p "$out/claude"
    local items=() it
    for it in CLAUDE.md settings.json keybindings.json commands skills hooks logbook preference-registry \
              preference-registry.md state statusline-command.sh plugins/installed_plugins.json \
              plugins/known_marketplaces.json; do
        [ -e "$claude_dir/$it" ] && items+=("$it")
    done
    local mem
    while IFS= read -r mem; do items+=("${mem#"$claude_dir"/}"); done < <(find "$claude_dir/projects" -maxdepth 2 -type d -name memory 2>/dev/null)
    log "   ${#items[@]} entries (credentials, transcripts and caches are not included)"
    run tar -czf "$out/claude/claude-config.tar.gz" --exclude='skills/synced' --exclude=__pycache__ \
        --exclude=.ruff_cache --exclude=.credentials.json -C "$claude_dir" "${items[@]}"
}

do_secrets() {
    log "== secrets (encrypted; gpg will ask for a passphrase)"
    command -v gpg >/dev/null 2>&1 || { echo "error: gpg is not installed" >&2; return 1; }
    local ram="/dev/shm/wsl-secrets-$$"
    umask 077
    $dry_run && { log "[dry-run] would bundle .env files and credential files into $out/secrets.tar.gpg"; return 0; }
    mkdir -p "$ram" "$out"
    local list="$ram/list" names="$out/secrets.manifest.txt"
    : > "$list"
    secret_find "$repos_root" > "$list.env"
    local f
    for f in "$HOME/.aws" "$HOME/.config/gh" "$HOME/.docker/config.json" "$HOME/.npmrc" "$HOME/.netrc" \
             "$HOME/.ssh" "$HOME/.claude.json" "$claude_dir/.credentials.json" "$HOME/.config/uv" \
             "$HOME/.bashrc" "$HOME/.profile"; do
        [ -e "$f" ] && printf '%s\0' "$f" >> "$list.env"
    done
    tr '\0' '\n' < "$list.env" | sed "s#^$HOME/#~/#" | sort > "$names"
    log "   $(wc -l < "$names") paths listed in $names (names only, no contents)"
    tar -cf "$ram/secrets.tar" --null -T "$list.env" 2>/dev/null
    if gpg --symmetric --cipher-algo AES256 --output "$out/secrets.tar.gpg" "$ram/secrets.tar"; then
        log "   wrote $out/secrets.tar.gpg"
    else
        echo "error: gpg failed; no encrypted file was written" >&2
    fi
    shred -u "$ram/secrets.tar" 2>/dev/null || rm -f "$ram/secrets.tar"
    rm -rf "$ram"
    log "   restore later with: gpg --decrypt secrets.tar.gpg | tar -xf - -C /"
}

do_tools() {
    # Copy the backup and restore scripts and the runbook next to the data, so the new
    # machine can run the restore before it can clone this repo.
    log "== tools"
    local here repo_docs
    here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    repo_docs="$here/../../docs/guidelines/WSL-MIGRATION.md"
    run mkdir -p "$out/tools"
    $dry_run && return 0
    cp "$here"/wsl-migration-backup.sh "$here"/wsl-migration-restore.sh "$out/tools/" 2>/dev/null
    [ -f "$repo_docs" ] && cp "$repo_docs" "$out/tools/WSL-MIGRATION.md"
    log "   copied to $out/tools"
}

do_verify() {
    log "== verify $out"
    local bad=0 f
    while IFS= read -r f; do
        if tar -tzf "$f" >/dev/null 2>&1; then log "   ok   ${f#"$out"/}"; else log "   FAIL ${f#"$out"/}"; bad=$((bad + 1)); fi
    done < <(find "$out" -name '*.tar.gz' | sort)
    while IFS= read -r f; do
        if git bundle verify "$f" >/dev/null 2>&1; then log "   ok   ${f#"$out"/}"; else log "   FAIL ${f#"$out"/}"; bad=$((bad + 1)); fi
    done < <(find "$out" -name '*.bundle' | sort)
    [ -f "$out/secrets.tar.gpg" ] && log "   note secrets.tar.gpg is encrypted; test it with: gpg --decrypt secrets.tar.gpg | tar -tf -"
    [ "$bad" -eq 0 ] && log "   all readable" || { log "   $bad unreadable"; return 1; }
}

case "$cmd" in
    all) do_inventory; do_repos; do_claude; do_tools ;;
    inventory) do_inventory ;;
    repos) do_repos ;;
    claude) do_claude ;;
    secrets) do_secrets ;;
    verify) do_verify ;;
esac
