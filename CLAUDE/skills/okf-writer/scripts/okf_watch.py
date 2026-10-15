#!/usr/bin/env python3
"""Watch the Open Knowledge Format spec repository for changes.

OKF is young and still changing, and the upstream repository publishes no
releases or tags. The signal is the commit history of `SPEC.md` plus the version
named in its first lines. This script compares the repository head with the last
commit you reviewed and lists what changed since.

Usage:
    python3 okf_watch.py status           # age of the last check, no network
    python3 okf_watch.py check            # fetch, report changes since the last ack
    python3 okf_watch.py ack              # record the current head as reviewed
    python3 okf_watch.py check --max-age 14   # skip the fetch if checked within 14 days

`check` never moves the reviewed marker, so a change keeps being reported until you
have updated the skill, the guide and the linter and run `ack`.

State: ~/.claude/state/okf-watch.json (override with OKF_WATCH_STATE).
Uses `gh api` when available, else the unauthenticated GitHub API. Stdlib only;
runs on Python 3.9 and newer. Exit codes: 0 no change or fresh enough, 10 changes
since the last ack, 2 fetch failed.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path
from typing import Any

REPO = "GoogleCloudPlatform/open-knowledge-format"
API = "https://api.github.com"
UTC = dt.timezone.utc  # noqa: UP017 (dt.UTC needs Python 3.11; this runs on 3.9)


def state_path() -> Path:
    return Path(
        os.environ.get("OKF_WATCH_STATE")
        or Path.home() / ".claude/state/okf-watch.json"
    )


def load_state() -> dict[str, Any]:
    path = state_path()
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def save_state(state: dict[str, Any]) -> None:
    path = state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def now() -> str:
    return dt.datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def api_get(path: str, raw: bool = False) -> Any:
    """GET a GitHub API path; JSON by default, raw text for file contents."""
    if shutil.which("gh"):
        cmd = ["gh", "api", path]
        if raw:
            cmd += ["-H", "Accept: application/vnd.github.raw"]
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if out.returncode == 0:
            return out.stdout if raw else json.loads(out.stdout)
    headers = {
        "Accept": "application/vnd.github.raw" if raw else "application/vnd.github+json"
    }
    req = urllib.request.Request(f"{API}/{path.lstrip('/')}", headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310 (fixed https host)
        body = resp.read().decode("utf-8")
    return body if raw else json.loads(body)


def spec_version(spec_text: str) -> str:
    for line in spec_text.splitlines()[:12]:
        m = re.search(r"\bv?(\d+\.\d+)\b", line)
        if m:
            return m.group(1)
    return "unknown"


def fetch_snapshot() -> dict[str, Any]:
    repo = api_get(f"repos/{REPO}")
    commits = api_get(f"repos/{REPO}/commits?path=SPEC.md&per_page=30")
    spec = api_get(f"repos/{REPO}/contents/SPEC.md", raw=True)
    return {
        "full_name": repo.get("full_name", REPO),
        "archived": bool(repo.get("archived")),
        "pushed_at": repo.get("pushed_at", ""),
        "spec_version": spec_version(spec),
        "head_sha": commits[0]["sha"] if commits else "",
        "head_date": commits[0]["commit"]["committer"]["date"] if commits else "",
        "commits": [
            {
                "sha": c["sha"],
                "date": c["commit"]["committer"]["date"],
                "message": c["commit"]["message"].split("\n", 1)[0],
            }
            for c in commits
        ],
    }


def age_days(stamp: str) -> float | None:
    if not stamp:
        return None
    then = dt.datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    return (dt.datetime.now(UTC) - then).total_seconds() / 86400


def cmd_status(_: argparse.Namespace) -> int:
    state = load_state()
    days = age_days(state.get("last_checked", ""))
    if days is None:
        print("never checked; run `check`, then `ack` once the skill matches the spec")
    else:
        print(
            f"last checked {state['last_checked']} ({days:.0f} days ago); "
            f"reviewed head {state.get('acked_sha', '-')[:7]} "
            f"(spec v{state.get('acked_version', '?')})"
        )
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    state = load_state()
    days = age_days(state.get("last_checked", ""))
    if args.max_age is not None and days is not None and days < args.max_age:
        print(f"checked {days:.0f} days ago (limit {args.max_age}); skipping the fetch")
        return 10 if state.get("pending") else 0
    try:
        snap = fetch_snapshot()
    except Exception as exc:  # network, proxy, rate limit, missing gh
        print(f"error: could not reach GitHub: {exc}", file=sys.stderr)
        return 2
    acked = state.get("acked_sha", "")
    new = []
    for c in snap["commits"]:
        if c["sha"] == acked:
            break
        new.append(c)
    else:
        if acked:
            new = snap["commits"]  # reviewed commit is older than the window we fetched
    changed = bool(acked) and bool(new)
    state.update(
        {"last_checked": now(), "head_sha": snap["head_sha"], "pending": changed}
    )
    save_state(state)
    print(f"OKF spec repo: {snap['full_name']} (archived: {snap['archived']})")
    print(
        f"Spec version in SPEC.md: v{snap['spec_version']}; head {snap['head_sha'][:7]} on {snap['head_date']}"
    )
    if not acked:
        print(
            "No reviewed baseline yet. Compare the skill with the spec, then run `ack`."
        )
        return 0
    if snap["spec_version"] != state.get("acked_version"):
        print(
            f"VERSION CHANGED: reviewed v{state.get('acked_version')} -> now v{snap['spec_version']}"
        )
    if not new:
        print("No SPEC.md changes since the last review.")
        return 0
    print(f"{len(new)} SPEC.md commit(s) since the reviewed head {acked[:7]}:")
    for c in new[:20]:
        print(f"  {c['sha'][:7]} {c['date'][:10]} {c['message']}")
    print(
        f"Diff: https://github.com/{REPO}/compare/{acked[:12]}...{snap['head_sha'][:12]}"
    )
    print(
        "Then update references/okf-v0.2-summary.md, okf_lint.py, the guide, and run `ack`."
    )
    return 10


def cmd_ack(_: argparse.Namespace) -> int:
    try:
        snap = fetch_snapshot()
    except Exception as exc:
        print(f"error: could not reach GitHub: {exc}", file=sys.stderr)
        return 2
    state = load_state()
    state.update(
        {
            "acked_sha": snap["head_sha"],
            "acked_version": snap["spec_version"],
            "acked_at": now(),
            "last_checked": now(),
            "head_sha": snap["head_sha"],
            "pending": False,
        }
    )
    save_state(state)
    print(f"reviewed head set to {snap['head_sha'][:7]} (spec v{snap['spec_version']})")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status").set_defaults(fn=cmd_status)
    ck = sub.add_parser("check")
    ck.add_argument(
        "--max-age", type=float, help="skip the fetch if checked within this many days"
    )
    ck.set_defaults(fn=cmd_check)
    sub.add_parser("ack").set_defaults(fn=cmd_ack)
    args = ap.parse_args(argv)
    return int(args.fn(args))


if __name__ == "__main__":
    sys.exit(main())
