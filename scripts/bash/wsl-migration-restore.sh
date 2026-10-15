#!/usr/bin/env bash
# Restores what wsl-migration-backup.sh saved, on a fresh WSL distro.
#
# Order on the new machine (see docs/guidelines/WSL-MIGRATION.md for the whole runbook):
#   1. Install the tools and sign in to GitHub (`gh auth login`), so clones work.
#   2. ./wsl-migration-restore.sh plan   --from <dir>     # read-only summary
#   3. ./wsl-migration-restore.sh claude --from <dir>     # ~/.claude config, logbook, memory
#   4. ./wsl-migration-restore.sh secrets --from <dir>    # asks for the passphrase
#   5. ./wsl-migration-restore.sh repos  --from <dir>     # clone, then re-apply saved work
#
# What `repos` does for each line of MANIFEST.tsv:
#   local-only   unpack repos/<name>.full.tar.gz (the repo had no remote)
#   others       git clone <remote> (skipped with --no-clone), check out the saved branch,
#                then re-apply the saved extras:
#                  bundle    local branches missing on the remote are created; a branch whose
#                            tip differs from the remote's is kept as restored/<name>
#                  stashes   each stash becomes a branch restored/stash-<n> on its old base
#                            commit (inspect it, then cherry-pick or discard)
#                  patch     uncommitted tracked changes are applied to the working tree
#                  extra     untracked and ignored files are unpacked (existing files are kept)
# A repo is marked done in .git/wsl-restore.done and skipped on a re-run unless --force.
#
# Usage:
#   ./scripts/bash/wsl-migration-restore.sh <command> --from <dir> [options]
#
# Commands: plan (default), repos, claude, secrets, all (claude + repos; not secrets)
#
# Options:
#   --from <dir>         Folder written by wsl-migration-backup.sh (required)
#   --repos-root <dir>   Where to restore repos. Default: $HOME/repo
#   --claude-dir <dir>   Default: $HOME/.claude
#   --no-clone           Do not clone; only handle local-only repos and repos already present
#   --force              Overwrite an existing ~/.claude config, and re-run finished repos
#   --dry-run            Show what would happen, change nothing
#   -h, --help           Show this help and exit
set -uo pipefail

usage() { sed -n '2,/^set -uo/p' "$0" | sed '$d' | sed 's/^# \{0,1\}//'; }

cmd="plan"
from=""
repos_root="$HOME/repo"
claude_dir="$HOME/.claude"
no_clone=false
force=false
dry_run=false

if [ $# -gt 0 ] && [[ "$1" != -* ]]; then cmd="$1"; shift; fi
while [ $# -gt 0 ]; do
    case "$1" in
        --from) from="$2"; shift 2 ;;
        --repos-root) repos_root="$2"; shift 2 ;;
        --claude-dir) claude_dir="$2"; shift 2 ;;
        --no-clone) no_clone=true; shift ;;
        --force) force=true; shift ;;
        --dry-run) dry_run=true; shift ;;
        -h|--help) usage; exit 0 ;;
        *) echo "Unknown option: $1" >&2; exit 1 ;;
    esac
done
case "$cmd" in plan|repos|claude|secrets|all) ;; *) echo "Unknown command: $cmd" >&2; exit 1 ;; esac
[ -n "$from" ] || { echo "error: --from <dir> is required" >&2; exit 1; }
[ -d "$from" ] || { echo "error: $from is not a folder" >&2; exit 1; }
manifest="$from/MANIFEST.tsv"

log() { printf '%s\n' "$*"; }
run() { if $dry_run; then log "[dry-run] $*"; else "$@"; fi; }
safe_name() { printf '%s' "$1" | sed 's#/#__#g'; }

do_plan() {
    [ -f "$manifest" ] || { echo "error: $manifest not found" >&2; return 1; }
    log "== plan from $from"
    log "   repos: $(($(wc -l < "$manifest") - 1)) in the manifest"
    awk -F'\t' 'NR>1 {c[$5]++} END {for (k in c) printf "   %-11s %d\n", k, c[k]}' "$manifest" | sort
    log "   local-only repos (restored from their own archive):"
    awk -F'\t' 'NR>1 && $5=="local-only" {print "     " $1}' "$manifest"
    log "   repos with saved work to re-apply:"
    awk -F'\t' 'NR>1 && $5=="at-risk" {print "     " $1 "  [" $10 "]"}' "$manifest"
    log "   repos with ignored files skipped for size (re-create by hand):"
    awk -F'\t' 'NR>1 && $11!="-" {print "     " $1 ": " $11}' "$manifest"
    [ -f "$from/claude/claude-config.tar.gz" ] && log "   claude: claude/claude-config.tar.gz" || log "   claude: not in the backup"
    [ -f "$from/secrets.tar.gpg" ] && log "   secrets: secrets.tar.gpg ($(wc -l < "$from/secrets.manifest.txt" 2>/dev/null || echo ?) paths)" || log "   secrets: not in the backup"
    log "   inventory: $(ls "$from/inventory" 2>/dev/null | wc -l) files (tools, apt, npm, VS Code extensions)"
}

restore_bundle() {
    local dir="$1" bundle="$2" ref name sha cur
    while read -r sha ref; do
        case "$ref" in refs/heads/*) ;; *) continue ;; esac
        name="${ref#refs/heads/}"
        if git -C "$dir" show-ref --verify --quiet "refs/heads/$name"; then
            cur=$(git -C "$dir" rev-parse "refs/heads/$name")
            [ "$cur" = "$sha" ] && continue
            git -C "$dir" fetch --quiet "$bundle" "$ref:refs/heads/restored/$name" 2>/dev/null \
                && log "      branch $name differs from the remote: kept as restored/$name"
        else
            git -C "$dir" fetch --quiet "$bundle" "$ref:refs/heads/$name" 2>/dev/null \
                && log "      branch $name restored from the bundle"
        fi
    done < <(git bundle list-heads "$bundle" 2>/dev/null)
}

restore_stashes() {
    local dir="$1" tsv="$2" patch_base="$3" n base msg tmp
    while IFS=$'\t' read -r n base msg; do
        [ "$n" = "n" ] && continue
        [ -s "$patch_base.stash-$n.patch" ] || continue
        tmp=$(mktemp -d)
        if ! git -C "$dir" cat-file -e "$base^{commit}" 2>/dev/null; then base="HEAD"; log "      stash $n: base commit missing, using HEAD"; fi
        if git -C "$dir" worktree add --quiet -b "restored/stash-$n" "$tmp/wt" "$base" 2>/dev/null \
            && git -C "$tmp/wt" apply --index "$patch_base.stash-$n.patch" 2>/dev/null \
            && git -C "$tmp/wt" -c user.name=restore -c user.email=restore@localhost commit -q -m "restored stash $n: $msg"; then
            log "      stash $n restored as branch restored/stash-$n ($msg)"
        else
            log "      stash $n: could not be re-created; the patch is $patch_base.stash-$n.patch"
        fi
        git -C "$dir" worktree remove --force "$tmp/wt" 2>/dev/null
        rm -rf "$tmp"
    done < "$tsv"
}

do_repos() {
    [ -f "$manifest" ] || { echo "error: $manifest not found" >&2; return 1; }
    log "== repos into $repos_root"
    local failed=0 path remote branch head class dirty stash ahead localbr art skipped target safe
    while IFS=$'\t' read -r path remote branch head class dirty stash ahead localbr art skipped; do
        [ "$path" = "path" ] && continue
        # "-" marks an empty field in the manifest (see the backup script).
        [ "$remote" = "-" ] && remote=""; [ "$branch" = "-" ] && branch=""
        target="$repos_root/$path"; safe=$(safe_name "$path")
        if [ -f "$target/.git/wsl-restore.done" ] && ! $force; then log "   $path: already restored"; continue; fi
        if [ "$class" = "local-only" ]; then
            if [ -e "$target" ] && ! $force; then log "   $path: exists, skipped (use --force)"; continue; fi
            log "   $path: unpacking the local-only repo"
            run mkdir -p "$repos_root"
            run tar -xzf "$from/repos/$safe.full.tar.gz" -C "$repos_root" || failed=$((failed + 1))
            $dry_run || touch "$target/.git/wsl-restore.done" 2>/dev/null
            continue
        fi
        if [ ! -d "$target/.git" ]; then
            if $no_clone; then log "   $path: not present, --no-clone (remote: $remote)"; continue; fi
            log "   $path: cloning $remote"
            run mkdir -p "$(dirname "$target")"
            if ! run git clone --quiet "$remote" "$target"; then log "      CLONE FAILED (sign in with gh auth login, then re-run)"; failed=$((failed + 1)); continue; fi
        fi
        $dry_run && continue
        [ -n "$branch" ] && [ "$(git -C "$target" branch --show-current)" != "$branch" ] \
            && git -C "$target" checkout --quiet "$branch" 2>/dev/null
        [ -f "$from/repos/$safe.bundle" ] && restore_bundle "$target" "$from/repos/$safe.bundle"
        [ -f "$from/repos/$safe.stashes.tsv" ] && restore_stashes "$target" "$from/repos/$safe.stashes.tsv" "$from/repos/$safe"
        if [ -s "$from/repos/$safe.tracked.patch" ]; then
            if git -C "$target" apply --reverse --check "$from/repos/$safe.tracked.patch" 2>/dev/null; then
                log "      uncommitted changes already present (the repo was unpacked with an outer repo)"
            elif git -C "$target" apply "$from/repos/$safe.tracked.patch" 2>/dev/null; then
                log "      uncommitted changes re-applied"
            else
                log "      could not apply the uncommitted changes cleanly; the patch is $from/repos/$safe.tracked.patch"
                failed=$((failed + 1))
            fi
        fi
        if [ -f "$from/repos/$safe.extra.tar.gz" ]; then
            tar -xzf "$from/repos/$safe.extra.tar.gz" --keep-old-files -C "$target" 2>/dev/null
            log "      untracked and ignored files unpacked"
        fi
        touch "$target/.git/wsl-restore.done"
    done < "$manifest"
    [ "$failed" -eq 0 ] && log "   done" || { log "   $failed problem(s); see the lines above"; return 1; }
}

do_claude() {
    local tarball="$from/claude/claude-config.tar.gz"
    [ -f "$tarball" ] || { echo "error: $tarball not found" >&2; return 1; }
    log "== claude config into $claude_dir"
    if [ -f "$claude_dir/CLAUDE.md" ] && ! $force; then
        echo "error: $claude_dir/CLAUDE.md already exists; use --force to overwrite" >&2
        return 1
    fi
    run mkdir -p "$claude_dir"
    run tar -xzf "$tarball" -C "$claude_dir"
    log "   restored. Reinstall the plugins listed in plugins/installed_plugins.json and run /mcp to reconnect."
}

do_secrets() {
    local enc="$from/secrets.tar.gpg"
    [ -f "$enc" ] || { echo "error: $enc not found" >&2; return 1; }
    command -v gpg >/dev/null 2>&1 || { echo "error: gpg is not installed" >&2; return 1; }
    log "== secrets (gpg asks for the passphrase)"
    $dry_run && { log "[dry-run] gpg --decrypt $enc | tar -xf - -C /"; return 0; }
    gpg --decrypt "$enc" | tar -xf - -C / && log "   restored (paths are listed in secrets.manifest.txt)"
}

case "$cmd" in
    plan) do_plan ;;
    repos) do_repos ;;
    claude) do_claude ;;
    secrets) do_secrets ;;
    all) do_claude; do_repos ;;
esac
