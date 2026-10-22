#!/usr/bin/env python3
"""Work logbook: upsert rows, weekly summary, archive old work, render Confluence HTML.

Paths (override for tests with environment variables):
  LOGBOOK_PATH         master CSV (default ~/.claude/logbook/logbook.csv); the archive
                       (logbook-archive.csv) and config.json live next to it
  LOGBOOK_WINDOWS_DIR  Windows export folder, e.g. /mnt/c/Users/<you>/Documents/Work/Logbook
                       (fallback: first line of ~/.claude/logbook/windows_dir.txt)
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import filecmp
import html
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


def _zip_strict(*iterables):
    """zip() that raises on unequal lengths (zip(strict=True) needs Python 3.10)."""
    lists = [list(it) for it in iterables]
    if len({len(x) for x in lists}) > 1:
        raise ValueError("zip() arguments have different lengths")
    return zip(*lists)


LOGBOOK = Path(
    os.environ.get("LOGBOOK_PATH") or Path.home() / ".claude/logbook/logbook.csv"
)
ARCHIVE = LOGBOOK.with_name("logbook-archive.csv")
CONFIG_FILE = LOGBOOK.parent / "config.json"
CACHE_FILE = LOGBOOK.parent / "jira-cache.json"
JIRA_KEY = re.compile(r"[A-Z][A-Z0-9]+-\d+")
WINDOWS_DIR_FILE = LOGBOOK.parent / "windows_dir.txt"
COLUMNS = ["date", "ticket", "repo", "type", "task", "status", "notes"]
TYPES = ["fea", "fix", "chore", "docs", "refactor", "ops"]
STATUSES = [
    "Analysis", "Development", "Testing", "Ready For Release", "Deployment",
    "PAT", "Done", "Fixing", "Hold",
]  # fmt: skip
## Logbook status -> the status words used on the Confluence weekly page.
PAGE_STATUS = {
    "Analysis": "ANALYST", "Development": "DEVELOPMENT", "Testing": "TESTING",
    "Ready For Release": "READY FOR RELEASE", "Deployment": "DEPLOYMENT",
    "PAT": "PAT", "Done": "DONE", "Fixing": "FIXING", "Hold": "HOLD",
}  # fmt: skip
PAGE_TO_LOGBOOK = {word: status for status, word in PAGE_STATUS.items()}
FINISHED = {"Done"}
## Jira workflow status -> page status, for tickets the user has not logged work on and
## for the Jira-wins comparison.
JIRA_STATUS = {
    "Hold": "HOLD", "Testing": "TESTING", "Ready For Release": "READY FOR RELEASE",
    "Deployment": "DEPLOYMENT", "PAT": "PAT",
    "In Progress": "DEVELOPMENT", "Data Development": "DEVELOPMENT",
    "Data Analysis": "ANALYST", "Revisi SRF Data": "ANALYST", "Bug Fixing": "FIXING",
    "[BU] Todo": "TODO", "TODO": "TODO", "To Do": "TODO", "Backlog": "TODO",
    "Done": "DONE", "Cancel": "CANCELLED",
}  # fmt: skip
## Start-date cell fill once unfinished work gets old: tiers light to strong.
AGING_COLORS = ["#FFFAE6", "#FFF0B3", "#FF8F73"]
AGING_DAYS = [30, 60, 90]  # override with "aging_days" in config.json
NO_AGING = {
    "DONE",
    "HOLD",
    "CANCELLED",
}  # finished, or deliberately paused: never highlighted
## Statuses where the ball is in someone else's court. Their age is shown on the LastUpdate
## cell (time since anything moved, i.e. when to follow up) instead of on Start Date.
OTHER_COURT = [
    "TESTING",
    "READY FOR RELEASE",
    "DEPLOYMENT",
    "PAT",
]  # override with "other_court" in config.json
FOLLOWUP_DAYS = [7, 14, 30]  # override with "followup_days" in config.json
## Lozenge colour per page status (Confluence only accepts neutral, purple, blue, red,
## yellow, green).
STATUS_COLOR = {
    "ANALYST": "purple", "DEVELOPMENT": "blue", "FIXING": "red", "TESTING": "yellow",
    "READY FOR RELEASE": "green", "DEPLOYMENT": "blue", "PAT": "purple",
    "DONE": "green", "HOLD": "neutral", "TODO": "neutral", "CANCELLED": "neutral",
}  # fmt: skip


def read_rows(path: Path = LOGBOOK) -> list[dict[str, str]]:
    """Read a logbook CSV, aborting (without writing) if its shape is wrong."""
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != COLUMNS:
            sys.exit(
                f"{path}: header {reader.fieldnames} != expected {COLUMNS}. "
                "Fix the file by hand; nothing was changed."
            )
        rows = list(reader)
    for number, row in enumerate(rows, start=2):
        if None in row or None in row.values():
            sys.exit(f"{path}: line {number} has the wrong number of fields.")
        problem = row_problem(row)
        if problem:
            sys.exit(f"{path}: line {number}: {problem}. Nothing was changed.")
    return rows


def row_problem(row: dict[str, str]) -> str:
    """Return what is wrong with a stored row, or an empty string."""
    for name in ("date", "ticket", "task"):
        if not row[name].strip():
            return f"empty {name}"
    try:
        iso_week(row["date"])
    except SystemExit:
        return f"invalid date {row['date']!r}"
    if row["type"] and row["type"] not in TYPES:
        return f"unknown type {row['type']!r}"
    if row["status"] and row["status"] not in STATUSES:
        return f"unknown status {row['status']!r}"
    return ""


def write_rows(rows: list[dict[str, str]], path: Path = LOGBOOK) -> None:
    """Write a CSV atomically: temp file in the same folder, then replace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=COLUMNS)
            writer.writeheader()
            writer.writerows(rows)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def iso_week(date: str) -> str:
    try:
        year, week, _ = dt.date.fromisoformat(date).isocalendar()
    except ValueError:
        sys.exit(f"Invalid date {date!r}; use YYYY-MM-DD.")
    return f"{year}-W{week:02d}"


def windows_dir() -> Path:
    folder = os.environ.get("LOGBOOK_WINDOWS_DIR", "").strip()
    if not folder and WINDOWS_DIR_FILE.exists():
        folder = WINDOWS_DIR_FILE.read_text(encoding="utf-8").strip()
    if not folder:
        sys.exit(
            "No Windows destination. Set LOGBOOK_WINDOWS_DIR or put the folder path "
            f"on the first line of {WINDOWS_DIR_FILE}."
        )
    path = Path(folder)
    ## Only the last folder is created; a missing parent usually means a typo in a
    ## /mnt/c path, so fail instead of creating a whole stray tree.
    if path.exists() and not path.is_dir():
        sys.exit(f"Windows destination is not a folder: {path}")
    if not path.parent.is_dir():
        sys.exit(f"Windows destination parent does not exist: {path.parent}")
    return path


def cmd_add(args: argparse.Namespace) -> None:
    date = args.date or dt.date.today().isoformat()
    iso_week(date)  # rejects an invalid date before anything is written
    new = {
        "date": date, "ticket": args.ticket, "repo": args.repo, "type": args.type,
        "task": args.task, "status": args.status, "notes": args.notes,
    }  # fmt: skip
    rows = read_rows()
    for row in rows:
        if row["date"] == date and row["ticket"] == args.ticket:
            row.update({k: v for k, v in new.items() if v})  # keep old values
            stored, action = row, "updated"
            break
    else:
        rows.append(new)
        stored, action = new, "added"
    write_rows(rows)
    print(f"{action}: {date} {args.ticket} [{stored['status'] or '-'}]")


def cmd_week(args: argparse.Namespace) -> None:
    week = args.week or iso_week(dt.date.today().isoformat())
    try:
        dt.date.fromisocalendar(int(week[:4]), int(week[6:]), 1)
        valid = week[4:6] == "-W" and len(week) == 8
    except ValueError:
        valid = False
    if not valid:
        sys.exit(f"Invalid week {week!r}; use YYYY-Www, e.g. 2026-W41.")
    by_ticket: dict[str, list[dict[str, str]]] = {}
    for row in sorted(read_rows(), key=lambda r: r["date"]):  # stable: ties keep order
        if iso_week(row["date"]) == week:
            by_ticket.setdefault(row["ticket"], []).append(row)
    cfg = load_config()
    register, _ = load_register_for_run(cfg)
    banner = ""
    if register is not None:
        now, sessions = now_wib(), cab_sessions(cfg)
        if not register_fresh(register, now, sessions):
            banner = stale_banner(now, sessions, register)
    cab_lines = cab_week_lines(week, register, banner)
    if not by_ticket and not cab_lines:
        print(f"No entries for {week}.")
        return
    print(f"## Weekly report {week}\n")
    for ticket, rows in by_ticket.items():
        last = rows[-1]
        print(f"- **{ticket}** ({last['repo']}, {last['type']}): {last['task']}")
        print(f"  - status: {last['status'] or '-'}")
        for row in rows:
            if row["notes"]:
                print(f"  - {row['date']}: {row['notes']}")
    if cab_lines:
        print("\n" + "\n".join(cab_lines))


def cmd_sync(_: argparse.Namespace) -> None:
    if not LOGBOOK.exists():
        sys.exit("No logbook to copy.")
    folder = windows_dir()
    folder.mkdir(exist_ok=True)
    for source in (LOGBOOK, ARCHIVE):
        if not source.exists():
            continue
        dest = folder / source.name
        if dest.exists() and filecmp.cmp(source, dest, shallow=False):
            print(f"already up to date: {dest}")
            continue
        shutil.copyfile(source, dest)
        print(f"copied to {dest}")


def load_config() -> dict[str, Any]:
    """Optional config.json: jira_base, pic, projects (repo -> project name)."""
    if not CONFIG_FILE.exists():
        return {}
    try:
        config: dict[str, Any] = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        return config
    except json.JSONDecodeError as exc:
        sys.exit(f"{CONFIG_FILE}: invalid JSON ({exc}).")


def load_cache() -> dict[str, dict[str, Any]]:
    """jira-cache.json: ticket -> {created, source, description} for the weekly page."""
    if not CACHE_FILE.exists():
        return {}
    try:
        cache: dict[str, dict[str, Any]] = json.loads(
            CACHE_FILE.read_text(encoding="utf-8")
        )
        return cache
    except json.JSONDecodeError as exc:
        sys.exit(f"{CACHE_FILE}: invalid JSON ({exc}).")


def save_cache(cache: dict[str, dict[str, Any]]) -> None:
    fd, tmp = tempfile.mkstemp(dir=CACHE_FILE.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=2, ensure_ascii=False, sort_keys=True)
            f.write("\n")
        os.replace(tmp, CACHE_FILE)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def cmd_cache(args: argparse.Namespace) -> None:
    """Manage the page cache: set one ticket, or list tickets that still lack one."""
    cache = load_cache()
    if args.action == "missing":
        tickets = {r["ticket"] for r in read_rows() + read_rows(ARCHIVE)}
        todo = sorted(t for t in tickets if t not in cache)
        print("\n".join(todo) if todo else "all tickets have a cache entry.")
        return
    if not args.ticket:
        sys.exit("cache set needs --ticket.")
    entry = cache.setdefault(args.ticket, {})
    if args.created:
        iso_week(args.created)  # validates YYYY-MM-DD
        entry["created"] = args.created
    if args.source:
        if not JIRA_KEY.fullmatch(args.source):
            sys.exit(f"--source must be a Jira key like IN-1234, got {args.source!r}.")
        entry["source"] = args.source
    if args.description:
        entry["description"] = args.description
    for name in (
        "summary",
        "jira_status",
        "updated",
        "project",
        "before_hold",
        "hold_since",
        "pat_since",
    ):
        if getattr(args, name):
            entry[name] = getattr(args, name)
    for date in (args.updated, args.hold_since, args.pat_since):
        if date:
            iso_week(date)  # validates YYYY-MM-DD
    if args.track:
        entry["track"] = args.track == "yes"
    if args.jira_status:
        entry["refreshed"] = dt.date.today().isoformat()
    save_cache(cache)
    print(f"cached {args.ticket}: {', '.join(entry)}")


def tracked_only_items(cache: dict, logged: set[str]) -> list[list[dict[str, str]]]:
    """Assigned, open DA tickets with no logbook row yet: one synthetic row each."""
    archived = {r["ticket"] for r in read_rows(ARCHIVE)}
    items = []
    for ticket, info in cache.items():
        if not info.get("track") or ticket in logged or ticket in archived:
            continue
        date = info.get("updated") or info.get("created") or dt.date.today().isoformat()
        items.append([{
            "date": date, "ticket": ticket, "repo": "", "type": "",
            "task": info.get("summary") or ticket, "status": "", "notes": "",
        }])  # fmt: skip
    return items


def cmd_rename(args: argparse.Namespace) -> None:
    """Re-key a ticket (e.g. a slug that later got a Jira key) in rows, archive and cache."""
    if not JIRA_KEY.fullmatch(args.to) and not args.force:
        sys.exit(f"--to {args.to!r} is not a Jira key; pass --force to allow it.")
    moved = 0
    loaded = {path: read_rows(path) for path in (LOGBOOK, ARCHIVE)}
    taken = {(r["date"], r["ticket"]) for rows in loaded.values() for r in rows}
    clash = sorted(
        r["date"] for rows in loaded.values() for r in rows
        if r["ticket"] == args.old and (r["date"], args.to) in taken
    )  # fmt: skip
    if clash:
        sys.exit(
            f"{args.to} already has rows on {', '.join(clash)}; merge those by hand first."
        )
    for path, rows in loaded.items():
        for row in rows:
            if row["ticket"] == args.old:
                row["ticket"] = args.to
                moved += 1
        if rows:
            write_rows(rows, path)
    cache = load_cache()
    if args.old in cache:
        cache.setdefault(args.to, {}).update(cache.pop(args.old))
        save_cache(cache)
    print(
        f"renamed {args.old} -> {args.to}: {moved} row(s), cache {'moved' if args.old in cache or args.to in cache else 'unchanged'}"
    )


## How far along a logbook status is; used to spot a row that lags behind its PR.
## Fixing and Hold sit outside the order and are skipped by the lag check.
STAGE = {
    "": 0, "Analysis": 1, "Development": 2, "Testing": 3, "Ready For Release": 4,
    "Deployment": 5, "PAT": 6, "Done": 7,
}  # fmt: skip
OUTSIDE_ORDER = {"Fixing", "Hold"}
TICKET_RE = re.compile(r"\b[A-Z][A-Z0-9]+-\d+\b|\bbug-\d+\b")


def _run(cmd: list[str], cwd: str) -> str | None:
    try:
        done = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return done.stdout if done.returncode == 0 else None


def pr_stage(pr: dict[str, Any]) -> str:
    """Logbook status a pull request implies. A PR to master implies none."""
    merged, is_open = bool(pr.get("mergedAt")), pr.get("state") == "OPEN"
    base = pr.get("baseRefName")
    if base in ("master", "main"):
        return ""
    if base == "sit":
        return "Development" if (merged or is_open) else ""
    return "Ready For Release" if merged else ("Testing" if is_open else "")


def git_evidence(
    repo_paths: dict[str, str], since: str
) -> tuple[dict[str, dict], list[str]]:
    """ticket -> {stage, last, repos} from local commits and GitHub PRs since a date."""
    evidence: dict[str, dict] = {}
    notes: list[str] = []

    def note(ticket: str, repo: str, date: str, stage: str) -> None:
        ev = evidence.setdefault(
            ticket, {"stage": "", "last": "", "repos": set(), "master": False}
        )
        ev["repos"].add(repo)
        ev["last"] = max(ev["last"], date)
        if STAGE.get(stage, 0) > STAGE.get(ev["stage"], 0):
            ev["stage"] = stage

    for repo, path in repo_paths.items():
        author = (_run(["git", "config", "user.name"], path) or "").strip()
        log = _run(
            ["git", "log", "--all", f"--since={since}", f"--author={author}",
             "--date=short", "--format=%ad|%s"], path
        )  # fmt: skip
        if log is None:
            notes.append(f"{repo}: git log failed at {path}")
            continue
        for line in log.splitlines():
            date, _, subject = line.partition("|")
            keys = TICKET_RE.findall(subject) + [
                f"bug-{n}" for n in re.findall(r"bug #(\d+)", subject)
            ]
            for key in set(keys):
                note(key, repo, date, "")
        prs = _run(
            ["gh", "pr", "list", "--state", "all", "--author", "@me", "--limit", "200",
             "--json", "title,state,baseRefName,headRefName,mergedAt,updatedAt"], path
        )  # fmt: skip
        if prs is None:
            notes.append(f"{repo}: gh pr list unavailable (commits only)")
            continue
        for pr in json.loads(prs):
            when = (pr.get("mergedAt") or pr["updatedAt"])[:10]
            if when < since:
                continue
            is_master_pr = pr.get("baseRefName") in ("master", "main") and (
                pr.get("state") == "OPEN" or pr.get("mergedAt")
            )
            for key in set(TICKET_RE.findall(f"{pr['headRefName']} {pr['title']}")):
                note(key, repo, when, pr_stage(pr))
                if is_master_pr:
                    evidence[key]["master"] = True
    return evidence, notes


def cmd_check(args: argparse.Namespace) -> None:
    """Compare the CSVs with git/PR activity and the Jira cache. Reports only; writes nothing."""
    cfg, cache = load_config(), load_cache()
    since = args.since or (dt.date.today() - dt.timedelta(days=7)).isoformat()
    iso_week(since)
    items = {i[0]["ticket"]: i for i in group_items(read_rows())}
    archived = {r["ticket"] for r in read_rows(ARCHIVE)}
    evidence, notes = git_evidence(cfg.get("repo_paths", {}), since)
    findings: list[str] = []
    for ticket, ev in sorted(evidence.items()):
        item = items.get(ticket)
        where = ", ".join(sorted(ev["repos"]))
        if item is None:
            if ticket not in archived:
                findings.append(
                    f"{ticket}: activity on {ev['last']} in {where}"
                    f"{' (' + ev['stage'] + ')' if ev['stage'] else ''}, but no logbook row"
                )
            continue
        last = item[-1]
        if last["status"] not in OUTSIDE_ORDER and STAGE.get(
            last["status"], 0
        ) < STAGE.get(ev["stage"], 0):
            findings.append(
                f"{ticket}: logbook says '{last['status'] or '-'}' but a PR is at '{ev['stage']}' ({where})"
            )
        if ev["last"] > last["date"]:
            findings.append(
                f"{ticket}: git activity on {ev['last']} is newer than the last logbook row ({last['date']})"
            )
    for ticket, item in sorted(items.items()):
        info = cache.get(ticket, {})
        jira = (
            JIRA_STATUS.get(info.get("jira_status", "")) if jira_fresh(info) else None
        )
        mine = PAGE_STATUS.get(item[-1]["status"], "")
        target = PAGE_TO_LOGBOOK.get(jira or "")
        if jira and mine and jira != mine and target:
            findings.append(
                f"{ticket}: Jira '{info['jira_status']}' ({jira}) vs logbook "
                f"'{item[-1]['status']}' ({mine}, {item[-1]['date']}) -> Jira wins; "
                f'propose: add --ticket {ticket} --status "{target}"'
            )
    register, cab_note = load_register_for_run(cfg)
    if cab_note:
        notes.append(cab_note)
    elif register is not None:
        now, sessions = now_wib(), cab_sessions(cfg)
        if register_fresh(register, now, sessions):
            fixing = fixing_dates_by_ticket(read_rows())
            tracked = {t for t, i in cache.items() if i.get("track")}
            for ticket in sorted(set(items) | tracked):
                info = cache.get(ticket, {})
                word = (
                    JIRA_STATUS.get(info.get("jira_status", ""))
                    if jira_fresh(info)
                    else None
                )
                if not word:
                    continue
                cab = cab_info(register, ticket, fixing.get(ticket, []), now.date())
                cab_found, _ = cab_flags(cab, word, now.date())
                findings += [f"{ticket}: {text} -> {fix}" for text, fix in cab_found]
        else:
            notes.append(stale_banner(now, sessions, register))
    print(f"## Recheck since {since} (CSV vs git/PRs vs Jira cache)\n")
    print(
        "\n".join(f"- {n}" for n in notes) if notes else "", end="\n" if notes else ""
    )
    print("\n".join(f"- {f}" for f in findings) if findings else "Nothing to flag.")
    if findings:
        print("\nFix with `add` after confirming; nothing was changed.")


## One-off migration from the git-step words to the Jira stage words (spec section 7).
LEGACY_MAP = {
    "In progress": "Development", "PR to dev": "Testing", "Merged to sit": "Development",
    "Merged to dev": "Ready For Release", "PR to master": "Ready For Release",
}  # fmt: skip
RECENT_DAYS = 7  # a Released row this young is flagged "check" in the migration report


def read_legacy(path: Path) -> list[dict[str, str]]:
    """Read a CSV without validating statuses: the old words must stay readable here."""
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != COLUMNS:
            sys.exit(f"{path}: header {reader.fieldnames} != expected {COLUMNS}.")
        return list(reader)


def _released_outcome(
    row: dict[str, str], cache: dict, today: dt.date, resolve: dict[str, str]
) -> tuple[str | None, str]:
    """Status for the last Released row of a ticket, or None when the user must decide."""
    ticket = row["ticket"]
    if ticket in resolve:
        return resolve[ticket], "resolved by the user"
    if not JIRA_KEY.fullmatch(ticket):
        return "Done", "non-Jira work: finished"
    jira = cache.get(ticket, {}).get("jira_status", "")
    status = PAGE_TO_LOGBOOK.get(JIRA_STATUS.get(jira, ""))
    if not status:
        return None, f"Jira status {jira or 'unknown'!r} has no logbook status"
    try:
        age = (today - dt.date.fromisoformat(row["date"])).days
    except ValueError:
        return status, f"Jira {jira!r} (check: no usable date)"
    note = f"Jira {jira!r}"
    return status, note + (" (check: recent row)" if age <= RECENT_DAYS else "")


def migrate_rows(
    rows: list[dict[str, str]], cache: dict, today: dt.date, resolve: dict[str, str]
) -> tuple[list[dict[str, str]], list[str], list[tuple[str, str]]]:
    """Return (new rows, report lines, review list of (date, ticket)). Pure; writes nothing."""
    last: dict[str, int] = {}
    for i, r in enumerate(rows):  # last row per ticket by date, ties keep file order
        j = last.get(r["ticket"])
        if j is None or r["date"] >= rows[j]["date"]:
            last[r["ticket"]] = i
    out: list[dict[str, str]] = []
    report: list[str] = []
    review: list[tuple[str, str]] = []
    for i, r in enumerate(rows):
        new, old, note = dict(r), r["status"], ""
        if old in LEGACY_MAP:
            new["status"] = LEGACY_MAP[old]
        elif old == "Released":
            if last[r["ticket"]] != i:
                new["status"], note = "Done", "earlier Released row: history"
            else:
                status, note = _released_outcome(r, cache, today, resolve)
                if status is None:
                    review.append((r["date"], r["ticket"]))
                    report.append(
                        f"{r['date']} {r['ticket']}: Released -> REVIEW ({note})"
                    )
                    out.append(new)
                    continue
                new["status"] = status
        elif old and old not in STATUSES:
            sys.exit(f"Unknown legacy status {old!r} on {r['date']} {r['ticket']}.")
        if new["status"] != old:
            tail = f" [{note}]" if note else ""
            report.append(
                f"{r['date']} {r['ticket']}: {old or '-'} -> {new['status']}{tail}"
            )
        out.append(new)
    return out, report, review


def cmd_migrate(args: argparse.Namespace) -> None:
    """Rewrite old status words in the logbook and archive. --dry-run writes nothing."""
    resolve: dict[str, str] = {}
    for item in args.resolve:
        ticket, _, status = item.partition("=")
        if status not in STATUSES:
            sys.exit(f"--resolve {item!r}: status must be one of {STATUSES}.")
        resolve[ticket] = status
    cache, today = load_cache(), dt.date.today()
    results = []
    blocked = False
    for path in (LOGBOOK, ARCHIVE):
        rows = read_legacy(path)
        new, report, review = migrate_rows(rows, cache, today, resolve)
        before = sorted({r["status"] or "-" for r in rows})
        print(
            f"## {path.name}: {len(rows)} row(s), statuses before: "
            f"{', '.join(before) or '-'}"
        )
        print("\n".join(f"- {line}" for line in report) or "- nothing to change")
        for date, ticket in review:
            print(f"! REVIEW {date} {ticket}: rerun with --resolve {ticket}=<status>")
        blocked = blocked or bool(review)
        results.append((path, rows, new))
    if blocked:
        sys.exit("Rows need a decision; nothing was written.")
    if args.dry_run:
        print("\nDry run: nothing was written.")
        return
    for path, rows, new in results:
        problems = [row_problem(r) for r in new if row_problem(r)]
        if len(new) != len(rows) or problems:
            sys.exit(
                f"{path}: validation failed ({problems[:1]}); nothing was written."
            )
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    for path, _rows, new in results:
        if path.exists():
            shutil.copy2(path, path.with_name(f"{path.name}.pre-migration-{stamp}"))
        write_rows(new, path)
    print("\nMigrated. Backups: *.pre-migration-" + stamp)


## The board (spec 5.1): where every open ticket stands, and what to do next.
BOARD_ORDER = [
    "TODO", "ANALYST", "DEVELOPMENT", "TESTING", "READY FOR RELEASE", "DEPLOYMENT",
    "PAT", "FIXING", "HOLD",
]  # fmt: skip
NEXT_ACTION = {
    "TODO": "start it (jira-ticket-kickoff)",
    "ANALYST": "finish the spec and plan, then move Jira to Data Development",
    "DEVELOPMENT": "finish and test (SIT), then open the PR to dev (/generate-pr-message)",
    "TESTING": "generate the BAST, get UAT approval, merge the PR into dev",
    "READY FOR RELEASE": "update the BAST with the approval, open dev to master, wait for CAB",
    "DEPLOYMENT": "deploy, then move Jira to PAT",
    "PAT": "watch production; Done after 7 days without error",
    "FIXING": "finish the fix, then follow its stage",
}  # fmt: skip
PAT_DONE_DAYS = 7


def board_refreshed(cache: dict) -> str:
    """Latest Jira refresh stamp among the tracked cache entries ('' when none)."""
    stamps = [i.get("refreshed", "") for i in cache.values() if i.get("track")]
    return max(stamps) if stamps else ""


def board_entry(
    ticket: str,
    info: dict,
    item: list[dict[str, str]],
    ev: dict | None,
    today: dt.date,
    live: bool,
    no_git: str = "",
    cab: dict[str, Any] | None = None,
    cab_fresh: bool = False,
    not_registered: bool = False,
) -> dict[str, Any]:
    """One board line. Jira supplies the status; git evidence only raises flags.

    live is per ticket: its Jira status was refreshed today. no_git is what to show as the
    git state when there is no evidence (none / unknown ...).
    """
    last = item[-1] if item else None
    jira_word = JIRA_STATUS.get(info.get("jira_status", ""))
    log_word = PAGE_STATUS.get(last["status"]) if last else None
    word = jira_word or log_word or "TODO"
    flags: list[tuple[str, str]] = []
    entry: dict[str, Any] = {
        "ticket": ticket, "word": word, "jira_status": info.get("jira_status", ""),
        "logbook_status": last["status"] if last else "",
        "repos": sorted(ev["repos"]) if ev else [],
        "git": (ev["stage"] or "commits") if ev else no_git,
        "next": NEXT_ACTION.get(word, ""), "flags": flags,
        "stale": bool(info.get("jira_status")) and not live,
        "propose_done": False, "done_line": "", "cab_line": "",
    }  # fmt: skip
    cab_row = cab["row"] if cab else None
    if cab_row is not None:
        entry["cab_line"] = (
            f"CAB {_iso(cab_row['cab'])} | deploy {_iso(cab_row['real'] or cab_row['plan'])} | "
            f"PAT end {_iso(cab_row['pat_end'])}"
        )
    ## The register decides about PAT only when it says something about it: a planned end,
    ## or a confirmed Status PAT. Otherwise the cached Jira-derived pat_since still applies.
    cab_decides = bool(
        cab_fresh
        and cab
        and cab_row is not None
        and cab["stage"] in ("PAT", "Done")
        and (cab["planned_end"] is not None or cab["pat_confirmed"])
    )
    if ev and last and last.get("repo") and last["repo"] not in ev["repos"]:
        flags.append((
            f"note: logbook repo {last['repo']} differs from PR repo "
            f"{', '.join(sorted(ev['repos']))}",
            "check the repo field of the row",
        ))  # fmt: skip
    if word == "READY FOR RELEASE" and not JIRA_KEY.fullmatch(ticket):
        entry["next"] = (
            "open dev to master; set Done once it is merged (no approval step for this work)"
        )
    if word == "HOLD":
        entry["next"] = f"on hold since {info.get('hold_since') or 'an unknown date'}"
        if ev and (ev["stage"] or ev["master"]):
            flags.append(("note: git activity while on hold", "resolve the hold first"))
        return entry
    if not live:
        return entry
    if ev:
        if ev["stage"] == "Ready For Release" and word == "TESTING":
            flags.append((
                "PR merged into dev but Jira is still Testing",
                "move Jira to Ready For Release",
            ))  # fmt: skip
        if ev["master"] and word == "TESTING":
            flags.append((
                "a dev to master PR exists but Jira is still Testing",
                "move Jira to Ready For Release first",
            ))  # fmt: skip
        if word == "ANALYST" and STAGE.get(ev["stage"], 0) <= STAGE["Development"]:
            flags.append((
                "commits exist but Jira is still Data Analysis",
                "move Jira to Data Development",
            ))  # fmt: skip
    if word == "PAT" and not cab_decides:
        since = info.get("pat_since")
        if not since:
            flags.append((
                "PAT date unknown",
                "read the Jira changelog and run cache set --pat-since",
            ))  # fmt: skip
        elif (today - dt.date.fromisoformat(since)).days >= PAT_DONE_DAYS:
            flags.append((
                f"in PAT since {since} (7 or more days)",
                "propose Done in Jira and the logbook, then /clean-gone",
            ))  # fmt: skip
    target = PAGE_TO_LOGBOOK.get(jira_word or "")
    if target and log_word and jira_word != log_word:
        flags.append((
            f"Jira {jira_word} vs logbook {log_word}",
            f'Jira wins: add --ticket {ticket} --status "{target}"',
        ))  # fmt: skip
    if cab_fresh:
        cab_found, propose = cab_flags(cab, word, today)
        flags.extend(cab_found)
        entry["propose_done"] = propose
        if propose:
            entry["done_line"] = cab_found[0][0]
        if not_registered and word == "READY FOR RELEASE":
            flags.append(
                ("not registered for CAB", "register the BAST in the CAB register")
            )
    return entry


def _no_git(item: list[dict[str, str]], repo_paths: dict[str, str] | None) -> str:
    """What to show as the git state when a ticket has no git evidence."""
    if repo_paths is None:
        return ""
    repo = item[-1].get("repo", "") if item else ""
    if not repo:
        return "unknown (no repo)"
    return "none" if repo in repo_paths else "unknown (repo not tracked)"


def derive_board(
    cache: dict,
    items: list[list[dict[str, str]]],
    evidence: dict[str, dict],
    today: dt.date,
    repo_paths: dict[str, str] | None = None,
    register: dict[str, Any] | None = None,
    now: dt.datetime | None = None,
    sessions: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], bool, str]:
    """Entries for every open ticket, ordered by stage.

    The returned flag drives the banner (newest Jira refresh is today); each entry decides
    its own liveness from its own refresh stamp.
    """
    refreshed = board_refreshed(cache)
    live = refreshed == today.isoformat()
    by_ticket = {i[0]["ticket"]: i for i in items}
    tickets = {t for t, info in cache.items() if info.get("track")}
    tickets |= {t for t, i in by_ticket.items() if i[-1]["status"] not in FINISHED}
    entries = []
    cab_fresh = bool(
        register is not None
        and now is not None
        and sessions is not None
        and register_fresh(register, now, sessions)
    )
    fixing = fixing_dates_by_ticket([r for i in items for r in i])
    grace = cab_grace_days(load_config())
    for ticket in sorted(tickets):
        info = cache.get(ticket, {})
        item = by_ticket.get(ticket, [])
        cab = (
            cab_info(register, ticket, fixing.get(ticket, []), today)
            if register
            else None
        )
        start = rfr_run_start(item)
        not_registered = bool(
            cab_fresh
            and cab is None
            and ticket.startswith("DA-")
            and start is not None
            and (today - start).days >= grace
        )
        e = board_entry(
            ticket,
            info,
            item,
            evidence.get(ticket),
            today,
            info.get("refreshed", "") == today.isoformat(),
            _no_git(item, repo_paths),
            cab,
            cab_fresh,
            not_registered,
        )
        if e["word"] not in ("DONE", "CANCELLED"):
            entries.append(e)
    entries.sort(
        key=lambda e: (
            BOARD_ORDER.index(e["word"]) if e["word"] in BOARD_ORDER else 99,
            e["ticket"],
        )
    )
    return entries, live, refreshed


def render_board(
    entries: list[dict[str, Any]],
    live: bool,
    refreshed: str,
    notes: list[str],
    cab_banner: str = "",
) -> str:
    """Text board grouped by stage; a stale banner when Jira was not refreshed today."""
    lines = [f"# Pipeline board {dt.date.today().isoformat()}"]
    if not live:
        lines += [
            "",
            f"STALE: the Jira cache was last refreshed {refreshed or 'never'}. Statuses "
            "are from the cache and not verified; Jira-dependent flags are hidden. "
            "Refresh it (logbook skill, step 0a) to get the flags.",
        ]
    if cab_banner:
        lines += ["", cab_banner]
    lines += [f"- {n}" for n in notes]
    proposals = [e for e in entries if e.get("propose_done")]
    if proposals:
        lines += ["", f"## PAT done: propose Done ({len(proposals)})"]
        lines += [f"- {e['ticket']}: {e['done_line']}" for e in proposals]
    for word in BOARD_ORDER:
        group = [e for e in entries if e["word"] == word]
        if not group:
            continue
        lines += ["", f"## {word} ({len(group)})"]
        for e in group:
            where = f" [{', '.join(e['repos'])}]" if e["repos"] else ""
            git = f" | git: {e['git']}" if e["git"] else ""
            stale = " (stale)" if e.get("stale") else ""
            lines.append(
                f"- {e['ticket']}{where} | Jira: {e['jira_status'] or '-'}{stale}{git}"
            )
            lines.append(f"  next: {e['next']}")
            if e["cab_line"]:
                lines.append(f"  {e['cab_line']}")
            lines += [f"  ! {text} -> {fix}" for text, fix in e["flags"]]
    if not entries:
        lines += ["", "No open tickets."]
    return "\n".join(lines)


def cmd_pipeline(args: argparse.Namespace) -> None:
    """Print where every open ticket stands. Read-only: writes no file."""
    cfg, cache = load_config(), load_cache()
    since = args.since or (dt.date.today() - dt.timedelta(days=30)).isoformat()
    iso_week(since)
    repo_paths = cfg.get("repo_paths", {})
    evidence, notes = git_evidence(repo_paths, since)
    if not repo_paths:
        notes.append(
            "no repo_paths in config.json: git state is unknown for every ticket"
        )
    register, cab_note = load_register_for_run(cfg)
    now, sessions = now_wib(), cab_sessions(cfg)
    banner = ""
    if cab_note:
        notes.append(cab_note)
    elif register is not None and not register_fresh(register, now, sessions):
        banner = stale_banner(now, sessions, register)
    entries, live, refreshed = derive_board(
        cache,
        group_items(read_rows()),
        evidence,
        dt.date.today(),
        repo_paths,
        register,
        now,
        sessions,
    )
    print(render_board(entries, live, refreshed, notes, banner))


## ---- CAB register (spec 2026-10-15-cab-register-integration-design.md) ----
WIB = dt.timezone(dt.timedelta(hours=7))  # Indonesia (WIB) has no daylight saving
CAB_REQUIRED = [
    "Column 1", "Status", "Tanggal Register CAB", "Nama CAB", "jadwal CAB",
    "Deployed Real Date", "Last PAT Date", "Status PAT",
]  # fmt: skip
CAB_OPTIONAL = ["TYPE CAB", "Kategori", "Deploye Plan Date"]
CAB_COLUMNS = CAB_REQUIRED + CAB_OPTIONAL


def resolve_register_path(cfg: dict[str, Any]) -> Path | None:
    """Where the CAB register CSV is, or None. Never exits (unlike windows_dir())."""
    configured = cfg.get("cab_register")
    if configured:
        return Path(str(configured)).expanduser()
    folder = os.environ.get("LOGBOOK_WINDOWS_DIR", "").strip()
    if not folder and WINDOWS_DIR_FILE.exists():
        try:
            lines = WINDOWS_DIR_FILE.read_text(encoding="utf-8").splitlines()
        except OSError:
            lines = []
        folder = lines[0].strip() if lines else ""
    return Path(folder) / "cab-register.csv" if folder else None


def _norm_header(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def _decode(raw: bytes) -> tuple[str, str]:
    """UTF-8 (BOM allowed), else cp1252 (Excel's 'CSV (comma delimited)')."""
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            return raw.decode(encoding), encoding
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError("cp1252", raw, 0, 1, "neither UTF-8 nor cp1252")


def _detect_delimiter(text: str) -> str:
    first = text.lstrip("\r\n").split("\n", 1)[0]
    counts = {d: first.count(d) for d in (",", ";", "\t")}
    best = max(counts, key=lambda d: counts[d])
    return best if counts[best] else ","


def read_register(path: Path) -> dict[str, Any]:
    """Read the CAB register. Read-only; any failure sets 'off' and never raises."""
    out: dict[str, Any] = {
        "rows": [], "problems": [], "encoding": "", "delimiter": ",",
        "mtime": None, "off": "",
    }  # fmt: skip
    try:
        raw = path.read_bytes()
        mtime = dt.datetime.fromtimestamp(path.stat().st_mtime, WIB)
        text, out["encoding"] = _decode(raw)
    except FileNotFoundError:
        out["off"] = f"no CAB register at {path}"
        return out
    except (OSError, UnicodeDecodeError) as exc:
        out["off"] = f"cannot read the CAB register {path}: {exc}"
        return out
    out["mtime"] = mtime
    out["delimiter"] = _detect_delimiter(text)
    try:
        table = list(
            csv.reader(io.StringIO(text, newline=""), delimiter=out["delimiter"])
        )
    except csv.Error as exc:
        out["off"] = f"cannot parse the CAB register: {exc}"
        return out
    table = [r for r in table if any(c.strip() for c in r)]
    if not table:
        out["off"] = "the CAB register is empty"
        return out
    header, body = table[0], table[1:]
    index: dict[str, int] = {}
    for i, cell in enumerate(header):
        key = _norm_header(cell)
        if key in index:
            out["problems"].append(
                f"duplicate column {cell.strip()!r}: the first one is used"
            )
        else:
            index[key] = i
    missing = [c for c in CAB_REQUIRED if _norm_header(c) not in index]
    if missing:
        out["off"] = "the CAB register lacks column(s): " + ", ".join(missing)
        return out
    for line in body:
        padded = line + [""] * (len(header) - len(line))
        out["rows"].append({
            col: padded[index[_norm_header(col)]].strip() if _norm_header(col) in index else ""
            for col in CAB_COLUMNS
        })  # fmt: skip
    return out


CAB_KEY = re.compile(r"(?<![A-Za-z0-9])DA-?\s?(\d{3,5})(?!\d)", re.IGNORECASE)


def register_max_age(cfg: dict[str, Any]) -> int:
    """cab_max_age_days (default 2): working days the register may go without being saved."""
    try:
        return max(0, int(cfg.get("cab_max_age_days", 2)))
    except (TypeError, ValueError):
        return 2


def register_cfg_lag(cfg: dict[str, Any]) -> int:
    """cab_max_lag_days (default 21), clamped to 26: readings of a cell are >= 27 days apart."""
    try:
        return max(0, min(int(cfg.get("cab_max_lag_days", 21)), 26))
    except (TypeError, ValueError):
        return 21


def _split_date(cell: str) -> tuple[int, int, int] | None:
    m = re.fullmatch(r"\s*(\d{1,2})/(\d{1,2})/(\d{2}|\d{4})\s*", cell)
    if not m:
        return None
    year = int(m[3])
    return int(m[1]), int(m[2]), year + 2000 if year < 100 else year


def _mk(a: int, b: int, year: int, day_first: bool) -> dt.date | None:
    day, month = (a, b) if day_first else (b, a)
    try:
        return dt.date(year, month, day)
    except ValueError:
        return None


def read_dmy(cell: str) -> dt.date | None:
    parts = _split_date(cell)
    return _mk(*parts, True) if parts else None


def register_date(
    cell: str, cab: dt.date | None, max_lag: int
) -> tuple[dt.date | None, str]:
    """The register date: primary M/D, typed D/M only if the primary is not plausible."""
    parts = _split_date(cell)
    if parts is None:
        return None, ""
    primary, swapped = _mk(*parts, False), _mk(*parts, True)
    if swapped == primary:
        swapped = None
    if cab is None:
        chosen = primary or swapped
        return chosen, "unverified" if chosen else ""

    def plausible(d: dt.date | None) -> bool:
        return d is not None and 0 <= (cab - d).days <= max_lag

    if plausible(primary):
        return primary, ""
    if plausible(swapped):
        return swapped, "swapped"
    return None, "unknown"


def _column_number(cell: str) -> int | None:
    m = re.fullmatch(r"(\d+)(?:\.0+)?", cell.strip())
    return int(m[1]) if m else None


def _current_row(rows: list[dict[str, Any]]) -> tuple[dict[str, Any] | None, str]:
    """The ticket's current CAB row by Column 1, or (None, why it is ambiguous)."""
    numbered = [r for r in rows if r["n"] is not None]
    if not numbered:
        return None, "no valid Column 1"
    top = max(r["n"] for r in numbered)
    tops = [r for r in numbered if r["n"] == top]
    if len(tops) > 1:
        return None, f"duplicate Column 1 {top}"
    current = tops[0]
    for r in numbered:
        for field in ("cab", "real"):
            if (
                r is not current
                and r[field]
                and current[field]
                and r[field] > current[field]
            ):
                return None, "a lower Column 1 has a later date"
    return current, ""


def _cell_date(
    rawrow: dict[str, str], column: str, label: str, problems: list[str]
) -> dt.date | None:
    """A D/M date cell; a non-blank cell that is not a date is reported."""
    value = read_dmy(rawrow[column])
    if rawrow[column] and value is None:
        problems.append(f"{label}: {column} is not a date")
    return value


def build_register(
    read: dict[str, Any], cfg: dict[str, Any], today: dt.date
) -> dict[str, Any]:
    """Parsed rows plus a per-ticket index. Pure: no file access."""
    max_lag = register_cfg_lag(cfg)
    problems = list(read["problems"])
    rows: list[dict[str, Any]] = []
    for line, rawrow in enumerate(read["rows"], start=1):
        label = rawrow["Column 1"] or f"row {line}"
        n = _column_number(rawrow["Column 1"])
        if n is None:
            problems.append(f"{label}: Column 1 is not a number")

        cab = _cell_date(rawrow, "jadwal CAB", label, problems)
        reg, note = register_date(rawrow["Tanggal Register CAB"], cab, max_lag)
        if rawrow["Tanggal Register CAB"] and reg is None:
            problems.append(f"{label}: Tanggal Register CAB is unknown")
        plan = _cell_date(rawrow, "Deploye Plan Date", label, problems)
        real = _cell_date(rawrow, "Deployed Real Date", label, problems)
        pat_end = _cell_date(rawrow, "Last PAT Date", label, problems)
        if real is not None and real > today:
            problems.append(f"{label}: Deployed Real Date is in the future")
            real = None
        if reg and cab and cab < reg:
            problems.append(f"{label}: jadwal CAB is before the register date")
            cab = None
        if cab and plan and plan < cab:
            problems.append(f"{label}: Deploye Plan Date is before jadwal CAB")
            plan = None
        if cab and real and real < cab:
            problems.append(f"{label}: Deployed Real Date is before jadwal CAB")
            real = None
        if real and pat_end and pat_end < real:
            problems.append(f"{label}: Last PAT Date is before Deployed Real Date")
            pat_end = None
        keys: list[str] = []
        for m in CAB_KEY.finditer(rawrow["Nama CAB"]):
            key = f"DA-{m[1]}"
            if key not in keys:
                keys.append(key)
        rows.append({
            "n": n, "status": rawrow["Status"], "pat_status": rawrow["Status PAT"],
            "type": rawrow["TYPE CAB"], "kategori": rawrow["Kategori"],
            "name": rawrow["Nama CAB"], "keys": keys, "reg": reg, "reg_note": note,
            "cab": cab, "plan": plan, "real": real, "pat_end": pat_end,
        })  # fmt: skip
    by_ticket: dict[str, dict[str, Any]] = {}
    for row in rows:
        for key in row["keys"]:
            by_ticket.setdefault(key, {"history": []})["history"].append(row)
    for entry in by_ticket.values():
        entry["current"], entry["ambiguous"] = _current_row(entry["history"])
    return {
        "rows": rows, "by_ticket": by_ticket, "problems": problems,
        "unlinked": sum(1 for r in rows if not r["keys"]),
        "encoding": read.get("encoding", ""), "delimiter": read.get("delimiter", ","),
        "mtime": read.get("mtime"),
        "max_age_days": register_max_age(cfg),
    }  # fmt: skip


CAB_STATUS_STAGE = {
    "register cab": "Ready For Release", "pending": "Ready For Release",
    "cab ulang": "Ready For Release", "ok tp perlu rekonfirm": "Ready For Release",
    "done cab and progress deployment": "Deployment",
    "onprogress deployment": "Deployment", "closed": "PAT",
    "rollback": "Rollback", "cancel": "Cancel",
}  # fmt: skip
CAB_ERROR_STATUS = {"rollback", "cab ulang", "cancel"}
CAB_PAT_CONFIRMED = {"closed", "na"}  # Status PAT: Closed, or NA = not applicable
_WEEKDAYS = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}


def now_wib() -> dt.datetime:
    return dt.datetime.now(WIB)


def fixing_dates_by_ticket(rows: list[dict[str, str]]) -> dict[str, list[dt.date]]:
    out: dict[str, list[dt.date]] = {}
    for r in rows:
        if r["status"] == "Fixing":
            out.setdefault(r["ticket"], []).append(dt.date.fromisoformat(r["date"]))
    return out


def cab_info(
    register: dict[str, Any],
    ticket: str,
    fixing_dates: list[dt.date],
    today: dt.date,
) -> dict[str, Any] | None:
    """The CAB view of one ticket: stage, PAT state and error signal (spec sections 4 and 5)."""
    entry = register["by_ticket"].get(ticket)
    if entry is None:
        return None
    row = entry["current"]
    info: dict[str, Any] = {
        "ticket": ticket, "history": entry["history"], "ambiguous": entry["ambiguous"],
        "row": row, "stage": "", "planned_end": None, "pat_confirmed": False,
        "pat_assumed": False, "error_signal": "",
    }  # fmt: skip
    if row is None:
        return info
    status = row["status"].lower()
    stage = CAB_STATUS_STAGE.get(status, "unknown")
    end = row["pat_end"]
    info["planned_end"] = end
    signal = ""
    if status in CAB_ERROR_STATUS:
        signal = f"the register status is {row['status']}"
    else:
        start = row["real"] or row["plan"]
        if start and end and any(start <= d <= end for d in fixing_dates):
            signal = "a Fixing row in the logbook during the PAT window"
    info["error_signal"] = signal
    if stage == "PAT":
        confirmed = row["pat_status"].lower() in CAB_PAT_CONFIRMED
        assumed = not confirmed and not signal and end is not None and today >= end
        info["pat_confirmed"], info["pat_assumed"] = confirmed, assumed
        if confirmed or assumed:
            stage = "Done"
    info["stage"] = stage
    return info


def cab_sessions(cfg: dict[str, Any]) -> dict[str, Any]:
    """cab_sessions from config.json; anything malformed falls back to Mon and Wed, 15:00."""
    default = {"days": ["Mon", "Wed"], "end": "15:00"}
    given = cfg.get("cab_sessions")
    if not isinstance(given, dict):
        return default
    days, end = given.get("days", default["days"]), given.get("end", default["end"])
    valid_days = (
        isinstance(days, list)
        and bool(days)
        and all(isinstance(d, str) and d[:3].lower() in _WEEKDAYS for d in days)
    )
    valid_end = isinstance(end, str) and re.fullmatch(r"([01]?\d|2[0-3]):[0-5]\d", end)
    return {"days": days, "end": end} if valid_days and valid_end else default


def cab_grace_days(cfg: dict[str, Any]) -> int:
    try:
        return max(0, int(cfg.get("cab_grace_days", 3)))
    except (TypeError, ValueError):
        return 3


def last_session_end(now: dt.datetime, sessions: dict[str, Any]) -> dt.datetime:
    days = {_WEEKDAYS[d[:3].lower()] for d in sessions["days"]}
    hour, minute = (int(x) for x in sessions["end"].split(":"))
    for back in range(8):
        day = (now - dt.timedelta(days=back)).date()
        if day.weekday() in days:
            end = dt.datetime(day.year, day.month, day.day, hour, minute, tzinfo=WIB)
            if end <= now:
                return end
    raise ValueError("cab_sessions lists no session day")


def working_days_since(then: dt.datetime, now: dt.datetime) -> int:
    """Mon-Fri days after the day of `then`, up to and including today."""
    days, day = 0, then.date()
    while day < now.date():
        day += dt.timedelta(days=1)
        if day.weekday() < 5:
            days += 1
    return days


def register_aged(register: dict[str, Any], now: dt.datetime) -> bool:
    """True when the file was not saved for more than cab_max_age_days working days."""
    mtime, limit = register.get("mtime"), register.get("max_age_days")
    return (
        mtime is not None
        and limit is not None
        and working_days_since(mtime, now) > limit
    )


def register_fresh(
    register: dict[str, Any], now: dt.datetime, sessions: dict[str, Any]
) -> bool:
    """Fresh = saved at or after the end of the last CAB session, and saved recently.

    Deployments happen any time after CAB, so a file that was current at the session
    end still goes stale when nobody saves it for a few working days.
    """
    mtime = register.get("mtime")
    if mtime is None or mtime < last_session_end(now, sessions):
        return False
    return not register_aged(register, now)


def stale_banner(
    now: dt.datetime, sessions: dict[str, Any], register: dict[str, Any] | None = None
) -> str:
    end = last_session_end(now, sessions)
    if register is not None and register.get("mtime") and register["mtime"] >= end:
        saved = register["mtime"]
        return (
            f"CAB register last saved {saved:%a} {saved.day} {saved:%b}, more than "
            f"{register['max_age_days']} working days ago; CAB flags are hidden."
        )
    return (
        f"CAB register not updated since the {end:%A} {end.day} {end:%b} session; "
        "CAB flags are hidden."
    )


def load_register_for_run(cfg: dict[str, Any]) -> tuple[dict[str, Any] | None, str]:
    """(register, note). Register is None when the feature is off; note says why."""
    path = resolve_register_path(cfg)
    if path is None:
        return None, ""
    read = read_register(path)
    if read["off"]:
        return None, read["off"]
    return build_register(read, cfg, now_wib().date()), ""


def register_quality(register: dict[str, Any]) -> list[str]:
    """Data quality lines for the cab report (counts, not row dumps)."""
    lines = list(register["problems"])
    if register["unlinked"]:
        lines.append(
            f"{register['unlinked']} row(s) without a ticket key (--show-unlinked lists them)"
        )
    for row in register["rows"]:
        if row["status"].lower() not in CAB_STATUS_STAGE:
            lines.append(
                f"Column 1 {row['n'] if row['n'] is not None else '?'}: "
                f"unknown status {row['status']!r}"
            )
        deploying = row["status"].lower() in (
            "onprogress deployment",
            "done cab and progress deployment",
        )
        if deploying and row["pat_status"].lower() == "closed":
            lines.append(
                f"Column 1 {row['n']}: status is {row['status']} but Status PAT is Closed"
            )
        if row["reg_note"] == "unverified":
            lines.append(
                f"Column 1 {row['n']}: register date is unverified (no CAB date)"
            )
        if row["reg_note"] == "swapped":
            lines.append(f"Column 1 {row['n']}: register date read as day/month")
    for key, entry in sorted(register["by_ticket"].items()):
        if entry["ambiguous"]:
            lines.append(f"{key}: ambiguous current row ({entry['ambiguous']})")
        elif len(entry["history"]) > 1:
            lines.append(
                f"{key}: {len(entry['history'])} CAB rows (the highest Column 1 is current)"
            )
    return lines


def _iso(value: dt.date | None) -> str:
    return value.isoformat() if value else "-"


def cmd_cab(args: argparse.Namespace) -> None:
    """Per-ticket view of the CAB register. Read-only."""
    cfg = load_config()
    register, note = load_register_for_run(cfg)
    if register is None:
        print(note or "No CAB register configured (set cab_register in config.json).")
        return
    now, sessions = now_wib(), cab_sessions(cfg)
    fresh = register_fresh(register, now, sessions)
    cache, fixing = load_cache(), fixing_dates_by_ticket(read_rows())
    print(
        f"## CAB register: {len(register['rows'])} row(s), {register['encoding']}, "
        f"delimiter {register['delimiter']!r}, "
        + ("fresh" if fresh else stale_banner(now, sessions, register))
    )
    for ticket in sorted(register["by_ticket"]):
        if args.ticket and ticket != args.ticket:
            continue
        info = cab_info(register, ticket, fixing.get(ticket, []), now.date())
        assert info is not None
        jira = cache.get(ticket, {}).get("jira_status", "")
        if info["row"] is None:
            print(f"- {ticket}: ambiguous ({info['ambiguous']}) | Jira {jira or '-'}")
        else:
            row = info["row"]
            print(
                f"- {ticket}: {info['stage']} | Jira {jira or '-'} | CAB {_iso(row['cab'])} | "
                f"deploy {_iso(row['real'] or row['plan'])} | PAT end {_iso(row['pat_end'])} | "
                f"Status PAT {row['pat_status'] or '-'}"
            )
            jira_stage = PAGE_TO_LOGBOOK.get(JIRA_STATUS.get(jira, ""), "")
            if STAGE.get(jira_stage, 0) > STAGE.get(info["stage"], 0) > 0:
                print("  note: Jira ahead of the register")
        if args.ticket:
            for r in info["history"]:
                print(
                    f"  history: Column 1 {r['n']} | {r['status']} | CAB {_iso(r['cab'])}"
                )
    print("\n## Data quality")
    quality = register_quality(register)
    print(
        "\n".join(f"- {line}" for line in quality) if quality else "- nothing to flag"
    )
    if args.show_unlinked:
        print("\n## Unlinked rows")
        for r in register["rows"]:
            if not r["keys"]:
                print(f"- Column 1 {r['n']}: {r['name']}")


def cab_flags(
    info: dict[str, Any] | None, word: str, today: dt.date
) -> tuple[list[tuple[str, str]], bool]:
    """Board and check flags from the register: (flags, propose_done). Spec 6.2."""
    if info is None or info["row"] is None or word in ("HOLD", "CANCELLED", "TODO"):
        return [], False
    stage, row = info["stage"], info["row"]
    flags: list[tuple[str, str]] = []
    jira_rank = STAGE.get(PAGE_TO_LOGBOOK.get(word, ""), 0)
    if stage == "Done" and word == "PAT":
        kind = "confirmed" if info["pat_confirmed"] else "assumed"
        return [(
            f"PAT done ({kind}): Status PAT {row['pat_status'] or '-'}, planned end "
            f"{_iso(info['planned_end'])}",
            "propose Done in Jira and the logbook",
        )], True  # fmt: skip
    if stage in ("Deployment", "PAT", "Done") and STAGE[stage] > jira_rank > 0:
        target = "PAT" if stage == "Done" else stage
        flags.append(
            (f"register says {stage}, Jira is {word}", f"move Jira to {target}")
        )
    if (
        word == "PAT" and stage == "PAT" and info["error_signal"]
        and info["planned_end"] is not None and today >= info["planned_end"]
    ):  # fmt: skip
        flags.append((
            f"PAT window ended but {info['error_signal']}", "check it before moving to Done"
        ))  # fmt: skip
    if stage == "Rollback" and jira_rank > STAGE["Development"]:
        flags.append((
            f"register says Rollback, Jira is {word}",
            "check the rollback: Jira should be Data Development or Bug Fixing",
        ))  # fmt: skip
    if stage == "Cancel" and word != "CANCELLED":
        flags.append((f"register says Cancel, Jira is {word}", "move Jira to Cancel"))
    return flags, False


def rfr_run_start(item: list[dict[str, str]]) -> dt.date | None:
    """First date of the trailing run of 'Ready For Release' logbook rows, or None."""
    start = None
    for r in reversed(item):
        if r["status"] != "Ready For Release":
            break
        start = dt.date.fromisoformat(r["date"])
    return start


def cab_week_lines(
    week: str, register: dict[str, Any] | None, banner: str = ""
) -> list[str]:
    """The 'CAB this week' block from every valid register row. Empty when nothing happened."""
    if register is None:
        return []

    def in_week(d: dt.date | None) -> bool:
        return d is not None and iso_week(d.isoformat()) == week

    def label(r: dict[str, Any]) -> str:
        return ", ".join(r["keys"]) if r["keys"] else ""

    registered: list[str] = []
    sessions: dict[dt.date, list[str]] = {}
    deployed: list[str] = []
    pat_ends: list[str] = []
    unlinked = 0
    for r in register["rows"]:
        touched = False
        name = label(r)
        if in_week(r["reg"]):
            touched = True
            if name:
                registered.append(
                    name
                    + (" (date unverified)" if r["reg_note"] == "unverified" else "")
                )
        if in_week(r["cab"]):
            touched = True
            if name:
                sessions.setdefault(r["cab"], []).append(name)
        if in_week(r["real"]):
            touched = True
            if name:
                deployed.append(f"{name} ({r['real'].isoformat()})")
        if in_week(r["pat_end"]) and r["status"].lower() == "closed":
            touched = True
            if name:
                pat_ends.append(f"{name} ({r['pat_end'].isoformat()})")
        if touched and not name:
            unlinked += 1
    lines: list[str] = []
    if registered:
        lines.append(f"- Registered: {', '.join(registered)}")
    if sessions:
        parts = [
            f"{d.isoformat()} ({', '.join(names)})"
            for d, names in sorted(sessions.items())
        ]
        lines.append(f"- CAB sessions: {'; '.join(parts)}")
    if deployed:
        lines.append(f"- Deployed: {', '.join(deployed)}")
    if pat_ends:
        lines.append(f"- PAT windows ending: {', '.join(pat_ends)}")
    if unlinked:
        lines.append(f"- Unlinked rows: {unlinked}")
    if not lines:
        return []
    head = [banner, ""] if banner else []
    return head + ["### CAB this week", *lines]


def group_items(rows: list[dict[str, str]]) -> list[list[dict[str, str]]]:
    """Group rows by ticket, each group in date order (a ticket is one page row)."""
    items: dict[str, list[dict[str, str]]] = {}
    for row in sorted(rows, key=lambda r: r["date"]):  # stable: ties keep order
        items.setdefault(row["ticket"], []).append(row)
    return list(items.values())


def done_since(item: list[dict[str, str]]) -> str:
    """Date the ticket's current run of Done rows began, or '' when it is not Done."""
    if item[-1]["status"] not in FINISHED:
        return ""
    start = item[-1]["date"]
    for r in reversed(item):
        if r["status"] not in FINISHED:
            break
        start = r["date"]
    return start


def cmd_archive(args: argparse.Namespace) -> None:
    """Move tickets that have been Done for --days (default 7) to the archive.

    Logged tickets count from the date they became Done (a later note does not restart
    the clock; leaving and returning to Done does). Assigned DA tickets with no logbook
    row count from the Jira updated date once Jira shows them done.
    """
    cutoff = dt.date.today() - dt.timedelta(days=args.days)
    rows, archived, cache = read_rows(), read_rows(ARCHIVE), load_cache()
    moving = {
        item[0]["ticket"]
        for item in group_items(rows)
        if done_since(item) and dt.date.fromisoformat(done_since(item)) <= cutoff
    }
    logged = {r["ticket"] for r in rows}
    jira_done = sorted(
        ticket
        for ticket, info in cache.items()
        if info.get("track")
        and ticket not in logged
        and JIRA_STATUS.get(info.get("jira_status", "")) == "DONE"
        and info.get("updated", "9999-12-31") <= cutoff.isoformat()
    )
    if not moving and not jira_done:
        print(f"nothing to archive (Done on/before {cutoff}).")
        return
    names = sorted(moving) + jira_done
    print(f"{'would archive' if args.dry_run else 'archiving'}: {', '.join(names)}")
    if args.dry_run:
        return
    moved = [r for r in rows if r["ticket"] in moving]
    for ticket in jira_done:
        info = cache[ticket]
        moved.append({
            "date": info["updated"], "ticket": ticket, "repo": "", "type": "",
            "task": info.get("summary") or ticket, "status": "Done", "notes": "",
        })  # fmt: skip
        info["track"] = False
    # Archive first: a crash duplicates, never loses. Skipping keys already archived
    # makes a retry after a partial failure idempotent.
    have = {(r["date"], r["ticket"]) for r in archived}
    write_rows(
        archived + [r for r in moved if (r["date"], r["ticket"]) not in have], ARCHIVE
    )
    write_rows([r for r in rows if r["ticket"] not in moving])
    if jira_done:
        save_cache(cache)


## Table layout the user set on the Confluence page (auto row numbers, fixed widths).
COL_WIDTHS = [120, 140, 600, 130, 119, 218, 126]
TABLE_OPEN = '<table data-layout="center" data-width="1468" data-number-column="true">'


def long_date(date: str) -> str:
    """2026-10-05 -> 'October 5, 2026' (the way Confluence shows a date field)."""
    d = dt.date.fromisoformat(date)
    return f"{d:%B} {d.day}, {d.year}"


def time_tag(date: str) -> str:
    return f'<time datetime="{date}">{long_date(date)}</time>'


def expand(title: str, body: str) -> str:
    """A collapsed nested expand, used to keep table rows compact."""
    return (
        f'<details data-type="nested-expand"><summary>{title}</summary>{body}</details>'
    )


JIRA_FRESH_DAYS = (
    7  # a cached Jira status older than this no longer outranks the logbook
)


def jira_fresh(info: dict, today: dt.date | None = None) -> bool:
    """True when the cache entry was refreshed from Jira within JIRA_FRESH_DAYS."""
    stamp = info.get("refreshed", "")
    if not stamp:
        return False
    try:
        age = ((today or dt.date.today()) - dt.date.fromisoformat(stamp)).days
    except ValueError:
        return False
    return age <= JIRA_FRESH_DAYS


def item_status(last: dict[str, str], info: dict) -> str:
    """Page status word for a ticket: a fresh, mapped Jira status wins, else the logbook."""
    jira = JIRA_STATUS.get(info.get("jira_status", ""))
    if jira and jira_fresh(info):
        return jira
    return (
        PAGE_STATUS.get(last["status"])
        or jira
        or (last["status"] or info.get("jira_status", "")).upper()
        or "-"
    )


def item_project(last: dict[str, str], info: dict, cfg: dict) -> str:
    return (
        cfg.get("projects", {}).get(last["repo"]) or info.get("project") or last["repo"]
    )


def render_html(
    items: list[list[dict[str, str]]],
    cfg: dict,
    cache: dict | None = None,
    hold: bool = False,
) -> str:
    """One table row per ticket, in the layout of the Confluence weekly page.

    Uses native Confluence elements: <time> dates, status lozenges, a mention for the
    PIC (when config has pic_account_id), inline smart-link cards for Jira keys, and
    collapsed expands in the To Do cell: "Task List" (a ticket worked on over several
    days, one dated line per day) and "Update" (dated notes), so rows stay short.
    """
    esc = html.escape
    cache = cache or {}
    head = ["Start Date", "Project", "To Do", "Status", "PIC", "JIRA", "LastUpdate"]
    widths = list(COL_WIDTHS)
    if hold:  # the hold page also shows what the ticket was before it was paused
        head.insert(4, "Before Hold")
        widths = [120, 140, 460, 110, 190, 119, 200, 126]
    cols = [f'data-colwidth="{w}"' for w in widths]
    lines = [
        TABLE_OPEN,
        "<thead><tr>"
        + "".join(f"<th {c}><p>{h}</p></th>" for h, c in _zip_strict(head, cols))
        + "</tr></thead>",
        "<tbody>",
    ]
    for item in items:
        first, last = item[0], item[-1]
        ticket = first["ticket"]
        info = cache.get(ticket, {})
        base = cfg.get("jira_base", "")
        keys = [
            k for k in (info.get("source"), ticket) if k
        ]  # IN key first, like the old page
        links = []
        for key in keys:
            if base and JIRA_KEY.fullmatch(key):
                links.append(
                    f'<a href="{esc(base + key)}" data-card-appearance="inline"></a>'
                )
            else:
                links.append(esc(key))
        link = " ".join(links)
        start = info.get("created") or first["date"]  # Jira created date (IN if linked)
        todo = f"<p><strong>{esc(first['task'])}</strong></p>"
        if info.get("description"):
            todo += expand("Description", f"<p>{esc(info['description'])}</p>")
        if len(item) > 1:
            days = "".join(
                f"<li><p>{time_tag(r['date'])} {esc(r['task'])}</p></li>" for r in item
            )
            todo += expand("Task List", f"<ul>{days}</ul>")
        noted = [r for r in item if r["notes"]]
        if noted:
            entries = "<hr>".join(
                f"<p>{time_tag(r['date'])}</p><ul><li><p>{esc(r['notes'])}</p></li></ul>"
                for r in noted
            )
            todo += expand("Update", entries)
        status = item_status(last, info)
        color = STATUS_COLOR.get(status, "neutral")
        lozenge = (
            f'<span data-type="status" data-color="{color}" '
            f'data-status-style="bold">{esc(status)}</span>'
        )
        project = item_project(last, info, cfg)
        pic = esc(cfg.get("pic", ""))
        if cfg.get("pic_account_id"):
            uid = esc(cfg["pic_account_id"])
            pic = f'<span data-type="mention" data-user-id="{uid}">@{pic}</span>'
        fill, fill_last = "", False
        if status not in NO_AGING:
            fill_last = status in cfg.get("other_court", OTHER_COURT)
            anchor = last["date"] if fill_last else start
            tiers = (
                cfg.get("followup_days", FOLLOWUP_DAYS)
                if fill_last
                else cfg.get("aging_days", AGING_DAYS)
            )
            age = (dt.date.today() - dt.date.fromisoformat(anchor)).days
            reached = [c for d, c in zip(tiers, AGING_COLORS) if age >= d]
            if reached:
                fill = f' data-background="{reached[-1]}" style="background-color: {reached[-1]}"'
        cells = [
            time_tag(start), esc(project), todo, lozenge, pic, link,
            time_tag(last["date"]),
        ]  # fmt: skip
        if hold:
            before = info.get("before_hold", "")
            word = JIRA_STATUS.get(before, before.upper()) or "-"
            since = info.get("hold_since")
            cell = (
                f'<span data-type="status" data-color="{STATUS_COLOR.get(word, "neutral")}" '
                f'data-status-style="bold">{esc(word)}</span>'
                + (f"<br>on hold since {time_tag(since)}" if since else "")
            )
            cells.insert(4, cell)
        lines.append(
            "<tr>"
            + "".join(
                f"<td {c}{fill if i == (len(cells) - 1 if fill_last else 0) else ''}><p>{v}</p></td>"
                if i != 2
                else f"<td {c}>{v}</td>"
                for i, (v, c) in enumerate(_zip_strict(cells, cols))
            )
            + "</tr>"
        )
    lines += ["</tbody>", "</table>"]
    return "\n".join(lines)


def cmd_publish(args: argparse.Namespace) -> None:
    """Print Confluence-ready HTML for the main, hold or archive page."""
    archive = args.which == "archive"
    hold = args.which == "hold"
    if args.empty:
        out = render_html([], {})
        if args.out:
            Path(args.out).write_text(out, encoding="utf-8")
        else:
            print(out)
        return
    items = group_items(read_rows(ARCHIVE if archive else LOGBOOK))
    cache, cfg = load_cache(), load_config()
    if not archive:
        items += tracked_only_items(cache, {i[0]["ticket"] for i in items})
        on_hold = [
            i
            for i in items
            if item_status(i[-1], cache.get(i[0]["ticket"], {})) == "HOLD"
        ]
        items = on_hold if hold else [i for i in items if i not in on_hold]
    if args.year:
        items = [i for i in items if i[-1]["date"].startswith(f"{args.year}-")]
    if not items:
        sys.exit(
            f"No rows in the {args.which} logbook"
            + (f" for {args.year}." if args.year else ".")
        )
    # Orderly: by project (A-Z), then the most recently updated first.
    items.sort(key=lambda item: item[-1]["date"], reverse=True)
    items.sort(
        key=lambda item: item_project(
            item[-1], cache.get(item[0]["ticket"], {}), cfg
        ).lower()
    )
    body = render_html(items, cfg, cache, hold=hold)
    legend = {
        "main": (
            " Ordered by project, then last update. Tickets on hold are in the child page"
            " <strong>Weekly DA Interface - On Hold</strong>. Colour: Start Date = my court"
            " (open too long); LastUpdate = waiting on others (time to follow up)."
        ),
        "hold": " Tickets paused in Jira; <strong>Before Hold</strong> is the status each had when paused.",
    }.get(args.which, "")
    note = f"<p>Generated {dt.date.today().isoformat()} from the local logbook ({args.which}).{legend}</p>"
    out = note + "\n" + body
    if args.out:
        Path(args.out).write_text(out, encoding="utf-8")
        print(f"wrote {len(items)} items to {args.out}")
    else:
        print(out)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(required=True)

    add = sub.add_parser("add", help="Add or update the row for date+ticket")
    for name in ("ticket", "task"):
        add.add_argument(f"--{name}", required=True)
    for name in ("repo", "notes", "date"):
        add.add_argument(f"--{name}", default="")
    add.add_argument("--type", default="", choices=["", *TYPES])
    add.add_argument("--status", default="", choices=["", *STATUSES])
    add.set_defaults(func=cmd_add)

    week = sub.add_parser("week", help="Print a weekly summary")
    week.add_argument("--week", default="", help="e.g. 2026-W41 (default: current)")
    week.set_defaults(func=cmd_week)

    sync = sub.add_parser(
        "sync", help="Copy the CSVs to the Windows folder if they differ"
    )
    sync.set_defaults(func=cmd_sync)

    arch = sub.add_parser("archive", help="Move old finished tickets to the archive")
    arch.add_argument(
        "--days", type=int, default=7, help="idle days before archiving (default 7)"
    )
    arch.add_argument("--dry-run", action="store_true")
    arch.set_defaults(func=cmd_archive)

    check = sub.add_parser(
        "check", help="Compare the CSVs with git/PRs and the Jira cache"
    )
    check.add_argument("--since", default="", help="YYYY-MM-DD (default: 7 days ago)")
    check.set_defaults(func=cmd_check)

    mig = sub.add_parser(
        "migrate-statuses",
        help="One-off: rewrite old status words to the Jira stage words",
    )
    mig.add_argument("--dry-run", action="store_true")
    mig.add_argument(
        "--resolve", action="append", default=[], metavar="TICKET=STATUS",
        help="decide a Released row that needs review (repeatable)",
    )  # fmt: skip
    mig.set_defaults(func=cmd_migrate)

    pipe = sub.add_parser("pipeline", help="Board of open tickets by stage (read-only)")
    pipe.add_argument(
        "--since",
        default="",
        help="YYYY-MM-DD for the git/PR scan (default: 30 days ago)",
    )
    pipe.set_defaults(func=cmd_pipeline)

    rename = sub.add_parser("rename", help="Re-key a ticket in rows, archive and cache")
    rename.add_argument("old")
    rename.add_argument("to")
    rename.add_argument(
        "--force", action="store_true", help="allow a non-Jira target key"
    )
    rename.set_defaults(func=cmd_rename)

    cache = sub.add_parser("cache", help="Per-ticket Jira data for the weekly page")
    cache.add_argument("action", choices=["set", "missing"])
    cache.add_argument("--ticket", default="")
    cache.add_argument("--created", default="", help="Jira created date, YYYY-MM-DD")
    cache.add_argument("--source", default="", help="linked IN/other key, e.g. IN-3247")
    cache.add_argument(
        "--description", default="", help="short SRF/requirement summary"
    )
    cache.add_argument(
        "--summary", default="", help="Jira title (rows with no logbook entry)"
    )
    cache.add_argument("--jira-status", default="", help="Jira workflow status")
    cache.add_argument("--updated", default="", help="Jira updated date, YYYY-MM-DD")
    cache.add_argument("--project", default="", help="project name on the page")
    cache.add_argument(
        "--before-hold", default="", help="Jira status before the ticket went on hold"
    )
    cache.add_argument(
        "--hold-since", default="", help="date it went on hold, YYYY-MM-DD"
    )
    cache.add_argument(
        "--pat-since",
        default="",
        help="date it entered PAT (Jira changelog), YYYY-MM-DD",
    )
    cache.add_argument(
        "--track",
        default="",
        choices=["", "yes", "no"],
        help="yes: DA ticket assigned to the user and open, so list it",
    )
    cache.set_defaults(func=cmd_cache)

    cab = sub.add_parser("cab", help="Per-ticket view of the CAB register (read-only)")
    cab.add_argument("--ticket", default="", help="show one ticket with its history")
    cab.add_argument(
        "--show-unlinked", action="store_true", help="list rows without a ticket key"
    )
    cab.set_defaults(func=cmd_cab)

    pub = sub.add_parser("publish", help="Render Confluence HTML (does not post it)")
    pub.add_argument("which", choices=["main", "hold", "archive"])
    pub.add_argument(
        "--empty", action="store_true", help="header row only (page template)"
    )
    pub.add_argument(
        "--year", type=int, default=0, help="archive only: items last active that year"
    )
    pub.add_argument("--out", default="", help="write to a file instead of stdout")
    pub.set_defaults(func=cmd_publish)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
