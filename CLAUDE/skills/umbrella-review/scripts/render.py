#!/usr/bin/env python3
"""Render the collect.py JSON as a ranked Markdown report and keep review state.

Stdlib only, Python 3.9 and newer.

    render.py render <collect.json> [--out-dir DIR]   write the report, update state
    render.py decide <state-dir> <repo> <branch> <waiting|cancelled|unknown> [note]
    render.py status <state-dir>

The report goes to <umbrella>/knowledge/reviews/YYYY-MM-DD.md. The script
refuses to write inside a git work tree (so a report can never land in a
public repo); in that case it falls back to ~/.claude/umbrella-review/<name>/.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

STATUSES = ("waiting", "cancelled", "unknown")
TODAY = dt.date.today().isoformat()


def inside_git(path: Path) -> bool:
    probe = path
    while not probe.exists() and probe != probe.parent:
        probe = probe.parent
    try:
        res = subprocess.run(
            ["git", "-C", str(probe), "rev-parse", "--is-inside-work-tree"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return res.returncode == 0 and res.stdout.strip() == "true"


def pick_out_dir(umbrella: Path, override: str | None) -> Path:
    if override:
        chosen = Path(override).expanduser()
    else:
        chosen = umbrella / "knowledge"
    if inside_git(chosen):
        fallback = Path.home() / ".claude" / "umbrella-review" / umbrella.name
        print(
            f"note: {chosen} is inside a git work tree; writing to {fallback} instead",
            file=sys.stderr,
        )
        return fallback
    return chosen


def load_state(state_dir: Path) -> dict[str, Any]:
    try:
        state: dict[str, Any] = json.loads(
            (state_dir / "state.json").read_text(encoding="utf-8")
        )
        return state
    except (OSError, ValueError):
        return {"last_run": None, "decisions": {}, "seen": {}}


def save_state(state_dir: Path, state: dict[str, Any]) -> None:
    state_dir.mkdir(parents=True, exist_ok=True)
    (state_dir / "state.json").write_text(json.dumps(state, indent=2), encoding="utf-8")


def md_table(headers: list[str], rows: list[list[str]]) -> str:
    if not rows:
        return "_None._\n"
    out = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    out += ["| " + " | ".join(c.replace("|", "/") for c in r) + " |" for r in rows]
    return "\n".join(out) + "\n"


def tick(name: str) -> str:
    return f"`{name}`"


def render(doc: dict[str, Any], state: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    decisions = state.get("decisions", {})
    prev_seen = state.get("seen", {})
    seen: dict[str, str] = {}
    stalled: list[list[str]] = []
    drift: list[list[str]] = []
    hygiene: list[list[str]] = []
    snap: list[str] = []
    notes: list[str] = []
    changes: list[str] = []
    for r in doc["repos"]:
        name = r["name"]
        if r.get("duplicate_of"):
            notes.append(
                "{} is a clone or worktree of {}; skipped.".format(
                    tick(name), tick(r["duplicate_of"])
                )
            )
            continue
        for e in r.get("errors", []):
            notes.append(f"{tick(name)}: {e} (not checked, not 'none')")
        if r.get("pr_truncated"):
            notes.append(
                f"{tick(name)}: the PR list hit its limit; older PRs were not checked."
            )
        if r.get("fetch_age_days") is not None and r["fetch_age_days"] > 14:
            notes.append(
                f"{tick(name)}: last fetch was {r['fetch_age_days']} days ago; "
                "remote state may be stale (no fetch was run)."
            )
        others = 0
        for b in r.get("branches", []):
            if b["name"] == "__others__":
                others = b["count"]
                continue
            key = "{}::{}".format(name, b["name"])
            seen[key] = b["class"]
            if (
                prev_seen
                and key not in prev_seen
                and b["class"] not in ("merged", "no_unique_commits")
            ):
                changes.append(
                    "new open item: {} {} ({})".format(
                        tick(name), tick(b["name"]), b["class"]
                    )
                )
            elif prev_seen.get(key) not in (None, b["class"]):
                changes.append(
                    "{} {}: {} -> {}".format(
                        tick(name), tick(b["name"]), prev_seen[key], b["class"]
                    )
                )
            if b["band"] in ("done", "active"):
                continue
            dec = decisions.get(key)
            pr = b.get("pr")
            lb = b.get("logbook")
            stalled.append(
                [
                    {
                        "stalled": "STALLED",
                        "chase": "CHASE",
                        "stale": "STALE",
                        "watch": "WATCH",
                    }[b["band"]],
                    tick(name),
                    tick(b["name"]),
                    b["class"]
                    + (
                        ""
                        if b["confidence"] == "high"
                        else " ({} conf.)".format(b["confidence"])
                    ),
                    f"{b['age_days']}d",
                    (f"PR #{pr['number']} {pr['state'].lower()}") if pr else "no PR",
                    (f"{lb['status']}, {lb['days_since'] or 0}d ago")
                    if lb
                    else "no logbook row",
                    (
                        "{} ({})".format(dec["status"], dec.get("date", ""))
                        if dec
                        else "ASK"
                    ),
                ]
            )
            d = b.get("docs_on_branch") or {}
            if d.get("checked") and not (d["readme"] and d["claude_md"]):
                missing = [
                    n
                    for n, ok in (
                        ("README.md", d["readme"]),
                        ("CLAUDE.md", d["claude_md"]),
                    )
                    if not ok
                ]
                drift.append(
                    [
                        "branch",
                        tick(name),
                        tick(b["name"]),
                        "not changed since split from {}: {}".format(
                            r["roles"]["integration"], ", ".join(missing)
                        ),
                    ]
                )
        docs = r.get("docs", {})
        for rel in docs.get("releases", [])[:2]:
            if (dt.date.today() - dt.date.fromisoformat(rel["date"][:10])).days > 90:
                continue  # old releases are history, not a to-do
            if not (rel["readme"] and rel["claude_md"]):
                missing = [
                    n
                    for n, ok in (
                        ("README.md", rel["readme"]),
                        ("CLAUDE.md", rel["claude_md"]),
                    )
                    if not ok
                ]
                drift.append(
                    [
                        "release",
                        tick(name),
                        rel["sha"],
                        "{} ({}): {} not in that change".format(
                            rel["subject"][:50], rel["date"][:10], ", ".join(missing)
                        ),
                    ]
                )
        man = r.get("manifests", {})
        ver = (man.get("python") or {}).get("version") or (man.get("node") or {}).get(
            "version"
        )
        for fname, f in docs.get("files", {}).items():
            if not f["exists"]:
                drift.append(["missing", tick(name), fname, "file does not exist"])
                continue
            if f["version_line"] is None:
                drift.append(
                    [
                        "no version line",
                        tick(name),
                        fname,
                        "add `Version: x.y.z` (global convention)",
                    ]
                )
            elif ver and f["version_line"] != ver:
                drift.append(
                    [
                        "version mismatch",
                        tick(name),
                        fname,
                        "doc says {}, manifest says {}".format(f["version_line"], ver),
                    ]
                )
        last_rel = (docs.get("releases") or [{}])[0].get("date")
        if last_rel:
            for fname, f in docs.get("files", {}).items():
                if (
                    f["exists"]
                    and f["last_commit"]
                    and f["last_commit"][:10] < last_rel[:10]
                ):
                    drift.append(
                        [
                            "older than release",
                            tick(name),
                            fname,
                            "last edit {}, latest release {}".format(
                                f["last_commit"][:10], last_rel[:10]
                            ),
                        ]
                    )
        dirty = r.get("dirty", {})
        if dirty.get("count"):
            hygiene.append(
                [
                    "uncommitted",
                    tick(name),
                    f"{dirty['count']} paths",
                    ", ".join(dirty["paths"][:3]),
                ]
            )
        for s in r.get("stashes", []):
            hygiene.append(["stash", tick(name), s["date"][:10], s["subject"]])
        pend = r.get("pending", {})
        for d in pend.get("release_dirs_without_changelog", []):
            hygiene.append(
                ["release without changelog", tick(name), f"release/{d}", ""]
            )
        for p in pend.get("provide_markers", []):
            hygiene.append(
                ["PROVIDE_ marker", tick(name), p, "user still has to provide this"]
            )
        for m in r.get("logbook_mismatches", []):
            hygiene.append(["logbook mismatch", tick(name), m, ""])
        last = r.get("last_commits", [])
        snap.append(f"### {tick(name)}\n")
        snap.append(
            "- Branch: {}{}; last commit {} days ago; roles: {}".format(
                tick((r.get("head") or {}).get("branch") or "detached"),
                " (worktree)" if r.get("is_worktree") else "",
                r.get("last_commit_days"),
                ", ".join(f"{k}={v}" for k, v in (r.get("roles") or {}).items() if v)
                or "none detected",
            )
        )
        for c in last[:3]:
            snap.append(
                "- {} {} {}".format(c["date"][:10], tick(c["sha"]), c["subject"])
            )
        if others:
            snap.append(f"- {others} branch(es) by other authors were not listed.")
        if "template_sync" in r:
            snap.append("- template-sync: " + " / ".join(r["template_sync"][-3:]))
        snap.append("")
    unmapped = [n for n, ok in (doc.get("logbook_repo_mapped") or {}).items() if not ok]
    if unmapped:
        notes.append(
            "Not in the logbook `repo_paths`: {}.".format(
                ", ".join(tick(n) for n in unmapped)
            )
        )
    if doc.get("non_git_children"):
        notes.append(
            "Not git repos: {}.".format(
                ", ".join(tick(n) for n in doc["non_git_children"])
            )
        )
    order = {"STALLED": 0, "CHASE": 1, "STALE": 2, "WATCH": 3}
    stalled.sort(key=lambda row: order.get(row[0], 9))
    out = [
        f"# Umbrella review {TODAY}\n",
        "Umbrella: {}. Generated {}. Read-only run, no fetch.".format(
            tick(doc["umbrella"]), doc["generated_at"][:16]
        ),
        f"Files opened: {len(doc.get('files_opened', []))} (allow-listed names only).\n",
        "## 1. Testing and merge status (needs a decision)\n",
        md_table(
            ["Band", "Repo", "Branch", "Class", "Age", "PR", "Logbook", "Decision"],
            stalled,
        ),
    ]
    if changes:
        out += (
            [
                "## 2. Changed since the last review ({})\n".format(
                    (state.get("last_run") or "first run")[:10]
                )
            ]
            + ["- " + c for c in changes]
            + [""]
        )
    out += [
        "## 3. Documentation drift\n",
        md_table(["Kind", "Repo", "Where", "Detail"], drift),
        "## 4. Hygiene and pending\n",
        md_table(["Kind", "Repo", "Item", "Detail"], hygiene),
        "## 5. Repo snapshots\n",
    ] + snap
    if notes:
        out += ["## 6. Not checked or skipped\n"] + ["- " + n for n in notes] + [""]
    new_state = dict(state)
    new_state["last_run"] = doc["generated_at"]
    new_state["seen"] = seen
    return "\n".join(out), new_state


def cmd_render(args: argparse.Namespace) -> int:
    doc = json.loads(Path(args.json).read_text(encoding="utf-8"))
    umbrella = Path(doc["umbrella"])
    out_dir = pick_out_dir(umbrella, args.out_dir)
    state_dir = out_dir
    report, new_state = render(doc, load_state(state_dir))
    reviews = out_dir / "reviews"
    reviews.mkdir(parents=True, exist_ok=True)
    target = reviews / (f"{TODAY}.md")
    target.write_text(report, encoding="utf-8")
    save_state(state_dir, new_state)
    index = reviews / "index.md"
    line = f"- [{TODAY}]({TODAY}.md)"
    existing = (
        index.read_text(encoding="utf-8")
        if index.exists()
        else "# Umbrella reviews\n\n"
    )
    if line not in existing:
        index.write_text(existing.rstrip("\n") + "\n" + line + "\n", encoding="utf-8")
    print(report)
    print(f"\nsaved: {target}", file=sys.stderr)
    return 0


def cmd_decide(args: argparse.Namespace) -> int:
    if args.status not in STATUSES:
        print("status must be one of {}".format(", ".join(STATUSES)), file=sys.stderr)
        return 2
    state_dir = Path(args.state_dir).expanduser()
    state = load_state(state_dir)
    state.setdefault("decisions", {})[f"{args.repo}::{args.branch}"] = {
        "status": args.status,
        "note": args.note or "",
        "date": TODAY,
    }
    save_state(state_dir, state)
    print(f"recorded {args.repo}::{args.branch} = {args.status}")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    state = load_state(Path(args.state_dir).expanduser())
    print("last run: {}".format(state.get("last_run")))
    for key, d in sorted(state.get("decisions", {}).items()):
        print(f"{key:<60} {d['status']:<10} {d.get('date', '')} {d.get('note', '')}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("render")
    p.add_argument("json")
    p.add_argument("--out-dir")
    p.set_defaults(fn=cmd_render)
    p = sub.add_parser("decide")
    p.add_argument("state_dir")
    p.add_argument("repo")
    p.add_argument("branch")
    p.add_argument("status")
    p.add_argument("note", nargs="?")
    p.set_defaults(fn=cmd_decide)
    p = sub.add_parser("status")
    p.add_argument("state_dir")
    p.set_defaults(fn=cmd_status)
    args = ap.parse_args()
    return int(args.fn(args))


if __name__ == "__main__":
    sys.exit(main())
