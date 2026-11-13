#!/usr/bin/env python3
"""Collect read-only facts about every child git repo of an umbrella folder.

Stdlib only, Python 3.9 and newer. Writes one JSON document; the model reads
that JSON instead of the repositories, which keeps the sensitive-file
guarantee mechanical:

* git runs only through ``git()``, which allows a fixed set of sub-commands
  and refuses anything that can print file contents (``-p``, ``show``, ...).
* files are opened only through ``read_allowed()``, which allows a fixed set
  of base names (manifests, README.md, CLAUDE.md) and logs each open in
  ``files_opened``.
* it never runs ``git fetch``; it reports how old the last fetch is.

Usage:
    collect.py <umbrella> --out <file.json> [--with-templates]
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

# ---- safety: allow-lists --------------------------------------------------

ALLOWED_GIT = {
    "rev-parse",
    "log",
    "for-each-ref",
    "status",
    "stash",
    "remote",
    "config",
    "merge-base",
    "rev-list",
    "symbolic-ref",
    "diff",
    "ls-files",
    "grep",
    "tag",
    "worktree",
}
# Any of these anywhere in the argv would print file or diff content.
FORBIDDEN_ARGS = {
    "-p",
    "--patch",
    "-u",
    "--cc",
    "--textconv",
    "show",
    "--stat-patch",
    "--ext-diff",
}
ALLOWED_READ = {
    "pyproject.toml",
    "package.json",
    "README.md",
    "CLAUDE.md",
    "uv.lock",
    "requirements.txt",
    "environment.yml",
}
SKIP_DIRS = {
    ".git",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "__pycache__",
    ".tox",
    ".mypy_cache",
    ".ruff_cache",
    "site-packages",
    "dist",
    "build",
    ".idea",
    ".vscode",
}
SECRET_NAME_RE = re.compile(
    r"(\.env($|\.)|service[_-]?account.*\.json|credentials.*\.json|token.*\.json"
    r"|.*\.pem$|.*\.key$|.*\.p12$|.*\.pfx$|id_rsa|\.netrc|secret)",
    re.IGNORECASE,
)
# Pathspec excludes for `git grep -c` so secret-looking tracked files are never read.
GREP_EXCLUDES = [
    ":!.env*",
    ":!*.env",
    ":!*.pem",
    ":!*.key",
    ":!*secret*",
    ":!*credential*",
    ":!*token*.json",
    ":!*.lock",
    ":!node_modules",
    ":!.venv",
    ":!venv",
    ":!legacy",
    ":!scratch",
]

FILES_OPENED: list[str] = []
TICKET_RE = re.compile(r"[A-Z][A-Z0-9]+-\d+")
VERSION_RE = re.compile(
    r"^[*_> ]*version[*_]*\s*[:=][*_`\s]*v?(\d+(?:\.\d+){1,3}\S*?)[*_`]*(?:\s|$|[·|(])",
    re.IGNORECASE | re.MULTILINE,
)
UPDATED_RE = re.compile(
    r"(?:updated|last updated)[*_]*\s*[:=]\s*[*_`]*(\d{4}-\d{2}-\d{2})", re.IGNORECASE
)
NOW = dt.datetime.now(dt.timezone.utc)  # noqa: UP017 (datetime.UTC needs 3.11, scripts run on 3.9)


def git(repo: Path, *args: str, timeout: int = 30) -> str | None:
    """Run an allow-listed read-only git command; None on failure."""
    if not args or args[0] not in ALLOWED_GIT:
        raise ValueError(f"git sub-command not allowed: {args[:1]!r}")
    if any(a in FORBIDDEN_ARGS for a in args):
        raise ValueError(f"git argument not allowed: {args!r}")
    if args[0] == "diff" and "--name-only" not in args and "--name-status" not in args:
        raise ValueError("git diff is only allowed with --name-only/--name-status")
    if args[0] == "stash" and args[1:2] != ("list",):
        raise ValueError("only `git stash list` is allowed")
    try:
        res = subprocess.run(
            ["git", "-C", str(repo), "-c", "core.quotepath=off"] + list(args),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if res.returncode != 0:
        return None
    return res.stdout


def read_allowed(path: Path) -> str | None:
    """Read a file only when its base name is on the allow-list."""
    if path.name not in ALLOWED_READ or any(p in SKIP_DIRS for p in path.parts):
        return None
    try:
        text = path.read_text(encoding="utf-8", errors="replace")[:200_000]
    except OSError:
        return None
    FILES_OPENED.append(str(path))
    return text


def days_since(iso: str | None) -> int | None:
    if not iso:
        return None
    try:
        when = dt.datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except ValueError:
        return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=dt.timezone.utc)  # noqa: UP017 (datetime.UTC needs 3.11, scripts run on 3.9)
    return max(0, (NOW - when).days)


def lines(text: str | None) -> list[str]:
    return [ln for ln in (text or "").splitlines() if ln.strip()]


# ---- discovery ------------------------------------------------------------


def find_children(umbrella: Path) -> tuple[list[Path], list[str], bool]:
    """Return (git children, non-git child names, umbrella_is_repo)."""
    is_repo = (umbrella / ".git").exists()
    kids: list[Path] = []
    other: list[str] = []
    try:
        entries = sorted(umbrella.iterdir())
    except OSError:
        return [], [], is_repo
    for entry in entries:
        if not entry.is_dir() or entry.name.startswith(".") or entry.name in SKIP_DIRS:
            continue
        if (entry / ".git").exists():
            kids.append(entry)
        else:
            other.append(entry.name)
    if is_repo and not kids:
        kids = [umbrella]
    return kids, other, is_repo


def git_email(repo: Path) -> str:
    return (git(repo, "config", "user.email") or "").strip().lower()


# ---- per-repo collection --------------------------------------------------


def ref_exists(repo: Path, ref: str) -> bool:
    return git(repo, "rev-parse", "--verify", "--quiet", ref + "^{commit}") is not None


def detect_roles(repo: Path) -> dict[str, str | None]:
    head = (
        git(repo, "symbolic-ref", "--quiet", "refs/remotes/origin/HEAD") or ""
    ).strip()
    prod = head.rsplit("/", 1)[-1] if head else None
    candidates = [prod] if prod else []
    candidates += ["master", "main"]
    roles: dict[str, str | None] = {"prod": None, "integration": None, "sit": None}
    for name in candidates:
        if name and (ref_exists(repo, "origin/" + name) or ref_exists(repo, name)):
            roles["prod"] = name
            break
    for name in ("dev", "develop"):
        if ref_exists(repo, "origin/" + name) or ref_exists(repo, name):
            roles["integration"] = name
            break
    for name in ("sit",):
        if ref_exists(repo, "origin/" + name) or ref_exists(repo, name):
            roles["sit"] = name
    return roles


def best_ref(repo: Path, name: str | None) -> str | None:
    """Prefer the remote-tracking ref (what is actually integrated)."""
    if not name:
        return None
    if ref_exists(repo, "origin/" + name):
        return "origin/" + name
    return name if ref_exists(repo, name) else None


def gh_prs(repo: Path) -> tuple[str, list[dict[str, Any]], bool, str]:
    """Return (source, prs, truncated, error). Only the user's own PRs."""
    limit = 200
    try:
        res = subprocess.run(
            [
                "gh",
                "pr",
                "list",
                "--state",
                "all",
                "--author",
                "@me",
                "--limit",
                str(limit),
                "--json",
                "number,headRefName,baseRefName,state,updatedAt,mergedAt,title,isDraft",
            ],
            cwd=str(repo),
            capture_output=True,
            text=True,
            timeout=45,
            check=False,
        )
    except FileNotFoundError:
        return "none", [], False, "gh not installed"
    except subprocess.TimeoutExpired:
        return "error", [], False, "gh timed out"
    if res.returncode != 0:
        return (
            "error",
            [],
            False,
            (res.stderr or "gh failed").strip().splitlines()[0][:140],
        )
    try:
        prs = json.loads(res.stdout or "[]")
    except ValueError:
        return "error", [], False, "gh returned invalid JSON"
    for pr in prs:
        pr["title"] = (pr.get("title") or "")[:100]
    return "gh", prs, len(prs) >= limit, ""


def logbook_index() -> tuple[dict[str, list[dict[str, str]]], dict[str, Any]]:
    base = Path.home() / ".claude" / "logbook"
    by_ticket: dict[str, list[dict[str, str]]] = {}
    cfg: dict[str, Any] = {}
    try:
        cfg = json.loads((base / "config.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        cfg = {}
    try:
        with open(base / "logbook.csv", newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                by_ticket.setdefault((row.get("ticket") or "").strip(), []).append(row)
    except OSError:
        pass
    return by_ticket, cfg


def logbook_state(rows: list[dict[str, str]]) -> dict[str, Any]:
    rows = sorted(rows, key=lambda r: r.get("date", ""))
    last = rows[-1]
    return {
        "status": last.get("status", ""),
        "last_date": last.get("date", ""),
        "days_since": days_since(last.get("date", "") + "T00:00:00+00:00"),
        "task": (last.get("task") or "")[:120],
    }


def classify(
    branch: dict[str, Any],
    roles: dict[str, str | None],
    pr_source: str,
    lb: dict[str, Any] | None,
    followup: list[int],
    other_court: set[str],
) -> None:
    pr = branch.get("pr")
    age = branch["age_days"]
    state = pr["state"] if pr else None
    base = pr["base"] if pr else None
    if state == "MERGED" and base in (roles["integration"], roles["prod"]):
        cls, conf = "merged", "high"
    elif state == "MERGED" and base == roles["sit"]:
        cls, conf = "in_sit_only", "high"
    elif branch.get("ancestor_of_integration") or branch.get("ancestor_of_prod"):
        cls, conf = "merged", ("medium" if pr_source == "gh" else "low")
    elif state == "OPEN":
        cls, conf = "open_pr", "high"
    elif state == "CLOSED":
        cls, conf = "closed_unmerged", "high"
    elif branch["ahead"] == 0:
        cls, conf = "no_unique_commits", "medium"
    elif branch["pushed"]:
        cls, conf = "pushed_no_pr", "high" if pr_source == "gh" else "low"
    else:
        cls, conf = "local_only", "high" if pr_source == "gh" else "medium"
    branch["class"] = cls
    branch["confidence"] = conf
    if cls in ("merged", "no_unique_commits"):
        branch["band"] = "done"
        return
    lb_status = (lb or {}).get("status", "").upper()
    if lb and lb_status in other_court:
        w, c, s = followup[0], followup[1], followup[2]
        ref = min(
            age, lb.get("days_since") if lb.get("days_since") is not None else age
        )
        branch["band"] = (
            "stalled"
            if ref >= s
            else "chase"
            if ref >= c
            else "watch"
            if ref >= w
            else "active"
        )
        branch["band_basis"] = "logbook {} followup {}".format(lb["status"], followup)
    else:
        branch["band"] = "stalled" if age >= 56 else "stale" if age >= 14 else "active"
        branch["band_basis"] = "branch age 14/56 days"


def collect_branches(
    repo: Path,
    roles: dict[str, str | None],
    me: str,
    prs: list[dict[str, Any]],
    pr_source: str,
    lb_by_ticket: dict[str, list[dict[str, str]]],
    followup: list[int],
    other_court: set[str],
) -> list[dict[str, Any]]:
    fmt = "%(refname)|%(committerdate:iso-strict)|%(authoremail)|%(objectname:short)"
    raw = (
        git(
            repo, "for-each-ref", "--format=" + fmt, "refs/heads", "refs/remotes/origin"
        )
        or ""
    )
    role_names = {n for n in roles.values() if n}
    integ = best_ref(repo, roles["integration"])
    prod = best_ref(repo, roles["prod"])
    pr_by_head: dict[str, dict[str, Any]] = {}
    for item in sorted(prs, key=lambda p: p.get("updatedAt", "")):
        pr_by_head[item["headRefName"]] = {
            "number": item["number"],
            "state": item["state"],
            "base": item["baseRefName"],
            "updatedAt": item.get("updatedAt"),
            "mergedAt": item.get("mergedAt"),
            "title": item["title"],
            "draft": item.get("isDraft", False),
        }
    seen: dict[str, dict[str, Any]] = {}
    for ln in raw.splitlines():
        parts = ln.split("|")
        if len(parts) < 4:
            continue
        ref, date, email, sha = (
            parts[0],
            parts[1],
            parts[2].strip("<>").lower(),
            parts[3],
        )
        if ref.startswith("refs/heads/"):
            name, local = ref[len("refs/heads/") :], True
        else:
            name, local = ref[len("refs/remotes/origin/") :], False
        if name == "HEAD" or name in role_names:
            continue
        entry = seen.setdefault(
            name,
            {
                "name": name,
                "local": False,
                "remote": False,
                "tip_email": email,
                "tip_date": date,
                "sha": sha,
            },
        )
        entry["local" if local else "remote"] = True
        if date > entry["tip_date"]:
            entry.update(tip_date=date, tip_email=email, sha=sha)
    out: list[dict[str, Any]] = []
    others = 0
    for name, e in sorted(seen.items()):
        pr = pr_by_head.get(name)
        if not (pr or (me and e["tip_email"] == me)):
            others += 1
            continue
        ref = name if e["local"] else "origin/" + name
        ahead = 0
        anc_i = anc_p = False
        if integ:
            ahead = int(
                (git(repo, "rev-list", "--count", f"{integ}..{ref}") or "0").strip()
                or 0
            )
            anc_i = git(repo, "merge-base", "--is-ancestor", ref, integ) is not None
        if prod:
            anc_p = git(repo, "merge-base", "--is-ancestor", ref, prod) is not None
        tick = TICKET_RE.search(name)
        ticket = tick.group(0) if tick else ""
        lb = logbook_state(lb_by_ticket[ticket]) if ticket in lb_by_ticket else None
        ages = [days_since(e["tip_date"])]
        if pr and pr.get("updatedAt"):
            ages.append(days_since(pr["updatedAt"]))
        age = (
            min(a for a in ages if a is not None)
            if any(a is not None for a in ages)
            else 0
        )
        b: dict[str, Any] = {
            "name": name,
            "ticket": ticket,
            "local": e["local"],
            "pushed": e["remote"],
            "last_commit": e["tip_date"],
            "age_days": age,
            "ahead": ahead,
            "ancestor_of_integration": anc_i,
            "ancestor_of_prod": anc_p,
            "pr": pr,
            "logbook": lb,
        }
        classify(b, roles, pr_source, lb, followup, other_court)
        if b["class"] not in ("merged", "no_unique_commits"):
            b["docs_on_branch"] = docs_on_range(repo, integ, ref)
        out.append(b)
    if others:
        out.append({"name": "__others__", "count": others})
    return out


def docs_on_range(repo: Path, base: str | None, ref: str) -> dict[str, Any]:
    if not base:
        return {"checked": False}
    mb = (git(repo, "merge-base", base, ref) or "").strip()
    if not mb:
        return {"checked": False}
    names = lines(git(repo, "diff", "--name-only", f"{mb}..{ref}"))
    return {
        "checked": True,
        "readme": "README.md" in names,
        "claude_md": "CLAUDE.md" in names,
        "changelog": any(re.match(r"release/[^/]+/CHANGELOG\.md$", n) for n in names),
        "files_changed": len(names),
    }


def doc_info(repo: Path, prod: str | None) -> dict[str, Any]:
    info: dict[str, Any] = {"files": {}, "releases": []}
    for fname in ("README.md", "CLAUDE.md"):
        last = (git(repo, "log", "-1", "--format=%cI", "--", fname) or "").strip()
        text = read_allowed(repo / fname)
        ver = VERSION_RE.search(text or "")
        upd = UPDATED_RE.search(text or "")
        info["files"][fname] = {
            "exists": text is not None,
            "last_commit": last or None,
            "days_since_edit": days_since(last),
            "version_line": ver.group(1) if ver else None,
            "updated_line": upd.group(1) if upd else None,
        }
    if prod:
        fmt = "%h|%cI|%s"
        raw = (
            git(repo, "log", "--first-parent", "-n", "4", "--format=" + fmt, prod) or ""
        )
        for ln in raw.splitlines():
            sha, date, subj = (ln.split("|", 2) + ["", ""])[:3]
            names = lines(git(repo, "diff", "--name-only", sha + "^", sha))
            info["releases"].append(
                {
                    "sha": sha,
                    "date": date,
                    "subject": subj[:100],
                    "readme": "README.md" in names,
                    "claude_md": "CLAUDE.md" in names,
                }
            )
    tags = lines(git(repo, "tag", "--sort=-creatordate"))
    info["latest_tag"] = tags[0] if tags else None
    info["tag_count"] = len(tags)
    return info


def manifests(repo: Path) -> dict[str, Any]:
    out: dict[str, Any] = {}
    text = read_allowed(repo / "pyproject.toml")
    if text is not None:

        def grab(pattern: str) -> str | None:
            m = re.search(pattern, text, re.MULTILINE)
            return m.group(1) if m else None

        out["python"] = {
            "name": grab(r'^name\s*=\s*"([^"]+)"'),
            "version": grab(r'^version\s*=\s*"([^"]+)"'),
            "requires_python": grab(r'^requires-python\s*=\s*"([^"]+)"'),
        }
    pkg = read_allowed(repo / "package.json")
    if pkg is not None:
        try:
            data = json.loads(pkg)
            out["node"] = {"name": data.get("name"), "version": data.get("version")}
        except ValueError:
            out["node"] = {"error": "invalid package.json"}
    out["has_uv_lock"] = (repo / "uv.lock").exists()
    out["has_requirements"] = any(
        p.name.startswith("requirements") and p.suffix == ".txt"
        for p in repo.glob("requirements*.txt")
    )
    return out


def pending(repo: Path) -> dict[str, Any]:
    tracked = lines(git(repo, "ls-files", "release"))
    dirs: dict[str, bool] = {}
    for p in tracked:
        parts = p.split("/")
        if len(parts) >= 2:
            dirs.setdefault(parts[1], False)
            if len(parts) == 3 and parts[2] == "CHANGELOG.md":
                dirs[parts[1]] = True
    todo_raw = (
        git(
            repo,
            "grep",
            "-c",
            "-I",
            "-E",
            r"(TODO|FIXME|XXX)\b",
            "--",
            ".",
            *GREP_EXCLUDES,
        )
        or ""
    )
    todos: dict[str, int] = {}
    for ln in todo_raw.splitlines():
        path, _, cnt = ln.rpartition(":")
        if path and cnt.isdigit():
            todos[path] = int(cnt)
    provide: list[str] = []
    scratch = repo / "scratch"
    if scratch.is_dir():
        for dirpath, dirnames, filenames in os.walk(scratch):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            provide += [
                os.path.relpath(os.path.join(dirpath, f), repo)
                for f in filenames
                if f.startswith("PROVIDE_")
            ]
    return {
        "release_dirs": sorted(dirs),
        "release_dirs_without_changelog": sorted(
            [d for d, ok in dirs.items() if not ok]
        ),
        "provide_markers": sorted(provide)[:20],
        "todo_total": sum(todos.values()),
        "todo_top": sorted(todos.items(), key=lambda kv: -kv[1])[:5],
    }


def dirty(repo: Path) -> dict[str, Any]:
    raw = lines(git(repo, "status", "--porcelain=v1", "-uall"))
    safe = [r for r in raw if not SECRET_NAME_RE.search(Path(r[3:]).name)]
    return {
        "count": len(raw),
        "paths": [r[:140] for r in safe[:15]],
        "hidden_secret_like": len(raw) - len(safe),
    }


def collect_repo(
    repo: Path,
    umbrella: Path,
    lb_by_ticket: dict,
    lb_cfg: dict,
    with_templates: bool,
    seen_remotes: dict[str, str],
) -> dict[str, Any]:
    r: dict[str, Any] = {"name": repo.name, "path": str(repo), "errors": []}
    remote = (git(repo, "remote", "get-url", "origin") or "").strip()
    # strip any credentials embedded in the URL
    r["remote_url"] = re.sub(r"//[^/@]+@", "//", remote) if remote else None
    git_dir = (git(repo, "rev-parse", "--git-dir") or "").strip()
    common = (git(repo, "rev-parse", "--git-common-dir") or "").strip()
    r["is_worktree"] = bool(
        git_dir
        and common
        and os.path.realpath(os.path.join(str(repo), git_dir))
        != os.path.realpath(os.path.join(str(repo), common))
    )
    key = r["remote_url"] or (
        "local:"
        + os.path.realpath(os.path.join(str(repo), common or git_dir or ".git"))
    )
    if key in seen_remotes and key != "":
        r["duplicate_of"] = seen_remotes[key]
        return r
    seen_remotes[key] = repo.name
    fetch_head = (
        Path(os.path.realpath(os.path.join(str(repo), common or git_dir or ".git")))
        / "FETCH_HEAD"
    )
    try:
        r["fetch_age_days"] = max(
            0, int((NOW.timestamp() - fetch_head.stat().st_mtime) // 86400)
        )
    except OSError:
        r["fetch_age_days"] = None
    head = (git(repo, "symbolic-ref", "--quiet", "--short", "HEAD") or "").strip()
    r["head"] = {"branch": head or None, "detached": not head}
    roles = detect_roles(repo)
    r["roles"] = roles
    r["dirty"] = dirty(repo)
    stashes = lines(git(repo, "stash", "list", "--format=%cI|%gs"))
    r["stashes"] = [
        {"date": s.split("|", 1)[0], "subject": s.split("|", 1)[-1][:100]}
        for s in stashes[:10]
    ]
    fmt = "%h|%cI|%s"
    commits = lines(git(repo, "log", "-n", "5", "--format=" + fmt))
    r["last_commits"] = [
        dict(zip(("sha", "date", "subject"), (c.split("|", 2) + ["", ""])[:3]))
        for c in commits
    ]
    r["last_commit_days"] = (
        days_since(r["last_commits"][0]["date"]) if r["last_commits"] else None
    )
    me = git_email(repo)
    pr_source, prs, truncated, err = (
        ("none", [], False, "no GitHub remote") if not remote else gh_prs(repo)
    )
    r.update(pr_source=pr_source, pr_truncated=truncated)
    if err:
        r["errors"].append("pr: " + err)
    if not roles["integration"]:
        r["errors"].append(
            "no dev/develop branch found: integration checks are low confidence"
        )
    followup = [int(x) for x in (lb_cfg.get("followup_days") or [7, 14, 30])][:3]
    while len(followup) < 3:
        followup.append(followup[-1] * 2)
    other_court = {
        s.upper()
        for s in lb_cfg.get(
            "other_court", ["TESTING", "READY FOR RELEASE", "DEPLOYMENT", "PAT"]
        )
    }
    r["branches"] = collect_branches(
        repo, roles, me, prs, pr_source, lb_by_ticket, followup, other_court
    )
    r["docs"] = doc_info(repo, best_ref(repo, roles["prod"]))
    r["manifests"] = manifests(repo)
    r["pending"] = pending(repo)
    # logbook mismatches: Done in the logbook but the branch never reached dev/prod
    mism: list[str] = []
    for b in r["branches"]:
        lb = b.get("logbook")
        if not lb:
            continue
        if lb["status"].lower() == "done" and b["class"] not in (
            "merged",
            "no_unique_commits",
        ):
            mism.append(
                "{}: logbook says Done but branch is {}".format(b["name"], b["class"])
            )
        if (
            lb["status"].lower() in ("analysis", "development", "testing")
            and b["class"] == "merged"
        ):
            mism.append(
                "{}: branch merged but logbook still {}".format(b["name"], lb["status"])
            )
    r["logbook_mismatches"] = mism
    if with_templates:
        helper = (
            Path.home()
            / ".claude"
            / "skills"
            / "template-sync"
            / "scripts"
            / "template_sync.py"
        )
        try:
            res = subprocess.run(
                [sys.executable, "-I", str(helper), "check", str(repo)],
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
            r["template_sync"] = lines(res.stdout)[-30:]
        except (OSError, subprocess.TimeoutExpired):
            r["errors"].append("template-sync check failed or timed out")
    return r


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("umbrella")
    ap.add_argument("--out", required=True)
    ap.add_argument("--with-templates", action="store_true")
    args = ap.parse_args()
    umbrella = Path(args.umbrella).expanduser().resolve()
    kids, other, is_repo = find_children(umbrella)
    lb_by_ticket, lb_cfg = logbook_index()
    seen: dict[str, str] = {}
    repos = [
        collect_repo(k, umbrella, lb_by_ticket, lb_cfg, args.with_templates, seen)
        for k in kids
    ]
    doc = {
        "generated_at": NOW.isoformat(),
        "umbrella": str(umbrella),
        "umbrella_is_repo": is_repo,
        "non_git_children": other,
        "logbook_repo_mapped": {
            n: (n in (lb_cfg.get("repo_paths") or {})) for n in (k.name for k in kids)
        },
        "repos": repos,
        "files_opened": sorted(set(FILES_OPENED)),
        "safety": {
            "fetch_run": False,
            "git_subcommands": sorted(ALLOWED_GIT),
            "read_allowlist": sorted(ALLOWED_READ),
        },
    }
    Path(args.out).write_text(json.dumps(doc, indent=2), encoding="utf-8")
    print(f"wrote {args.out} ({len(repos)} repos)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
