#!/usr/bin/env python3
"""Work logbook: upsert rows, weekly summary, archive old work, render Confluence HTML.

Paths (override for tests with environment variables):
  LOGBOOK_PATH         master CSV (default ~/.claude/logbook/logbook.csv); the archive
                       (logbook-archive.csv) and config.json live next to it
  LOGBOOK_WINDOWS_DIR  Windows export folder, e.g. /mnt/c/Users/<you>/Documents/Work/Logbook
                       (fallback: first line of ~/.claude/logbook/windows_dir.txt)
"""

import argparse
import csv
import datetime as dt
import filecmp
import html
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

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
    "In progress", "PR to dev", "Merged to dev", "Merged to sit",
    "PR to master", "Released", "Done", "Analysis", "Fixing", "Hold",
]  # fmt: skip
## Logbook status -> the status words used on the Confluence weekly page.
PAGE_STATUS = {
    "Analysis": "ANALYST", "In progress": "DEVELOPMENT", "Fixing": "FIXING",
    "PR to dev": "TESTING", "Merged to dev": "TESTING", "Merged to sit": "TESTING",
    "PR to master": "READY FOR RELEASE", "Released": "DONE", "Done": "DONE",
    "Hold": "HOLD",
}  # fmt: skip
FINISHED = {"Released", "Done"}
## Jira workflow status -> page status, for assigned tickets the user has not logged work on.
JIRA_STATUS = {
    "Hold": "HOLD", "Testing": "TESTING", "Ready For Release": "READY FOR RELEASE",
    "In Progress": "DEVELOPMENT", "Data Development": "DEVELOPMENT",
    "Data Analysis": "ANALYST", "Revisi SRF Data": "ANALYST",
    "[BU] Todo": "TODO", "TODO": "TODO", "To Do": "TODO", "Backlog": "TODO",
    "PAT": "DONE", "Done": "DONE",
}  # fmt: skip
## Start-date cell fill once unfinished work gets old: tiers light to strong.
AGING_COLORS = ["#FFFAE6", "#FFF0B3", "#FF8F73"]
AGING_DAYS = [30, 60, 90]  # override with "aging_days" in config.json
NO_AGING = {"DONE", "HOLD"}  # finished, or deliberately paused: never highlighted
## Lozenge colour per page status (Confluence status macro colours).
STATUS_COLOR = {
    "ANALYST": "purple", "DEVELOPMENT": "blue", "FIXING": "red", "TESTING": "yellow",
    "READY FOR RELEASE": "green", "DONE": "green", "HOLD": "neutral", "TODO": "neutral",
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
    if not by_ticket:
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


def load_config() -> dict:
    """Optional config.json: jira_base, pic, projects (repo -> project name)."""
    if not CONFIG_FILE.exists():
        return {}
    try:
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        sys.exit(f"{CONFIG_FILE}: invalid JSON ({exc}).")


def load_cache() -> dict[str, dict[str, str]]:
    """jira-cache.json: ticket -> {created, source, description} for the weekly page."""
    if not CACHE_FILE.exists():
        return {}
    try:
        return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        sys.exit(f"{CACHE_FILE}: invalid JSON ({exc}).")


def save_cache(cache: dict[str, dict[str, str]]) -> None:
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
    for name in ("summary", "jira_status", "updated", "project"):
        if getattr(args, name):
            entry[name] = getattr(args, name)
    if args.updated:
        iso_week(args.updated)  # validates YYYY-MM-DD
    if args.track:
        entry["track"] = args.track == "yes"
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


def group_items(rows: list[dict[str, str]]) -> list[list[dict[str, str]]]:
    """Group rows by ticket, each group in date order (a ticket is one page row)."""
    items: dict[str, list[dict[str, str]]] = {}
    for row in sorted(rows, key=lambda r: r["date"]):  # stable: ties keep order
        items.setdefault(row["ticket"], []).append(row)
    return list(items.values())


def cmd_archive(args: argparse.Namespace) -> None:
    """Move finished tickets whose last activity is older than --days to the archive."""
    cutoff = dt.date.today() - dt.timedelta(days=args.days)
    rows, archived = read_rows(), read_rows(ARCHIVE)
    moving = {
        item[0]["ticket"]
        for item in group_items(rows)
        if item[-1]["status"] in FINISHED
        and dt.date.fromisoformat(item[-1]["date"]) <= cutoff
    }
    if not moving:
        print(f"nothing to archive (finished and last active on/before {cutoff}).")
        return
    print(
        f"{'would archive' if args.dry_run else 'archiving'}: {', '.join(sorted(moving))}"
    )
    if args.dry_run:
        return
    moved = [r for r in rows if r["ticket"] in moving]
    write_rows(
        archived + moved, ARCHIVE
    )  # archive first: a crash duplicates, never loses
    write_rows([r for r in rows if r["ticket"] not in moving])


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


def render_html(
    items: list[list[dict[str, str]]], cfg: dict, cache: dict | None = None
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
    cols = [f'data-colwidth="{w}"' for w in COL_WIDTHS]
    lines = [
        TABLE_OPEN,
        "<thead><tr>"
        + "".join(f"<th {c}><p>{h}</p></th>" for h, c in zip(head, cols, strict=True))
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
        status = PAGE_STATUS.get(last["status"]) or JIRA_STATUS.get(
            info.get("jira_status", ""),
            (last["status"] or info.get("jira_status", "")).upper() or "-",
        )
        color = STATUS_COLOR.get(status, "neutral")
        lozenge = (
            f'<span data-type="status" data-color="{color}" '
            f'data-status-style="bold">{esc(status)}</span>'
        )
        project = (
            cfg.get("projects", {}).get(last["repo"])
            or info.get("project")
            or last["repo"]
        )
        pic = esc(cfg.get("pic", ""))
        if cfg.get("pic_account_id"):
            uid = esc(cfg["pic_account_id"])
            pic = f'<span data-type="mention" data-user-id="{uid}">@{pic}</span>'
        fill = ""
        if status not in NO_AGING:
            age = (dt.date.today() - dt.date.fromisoformat(start)).days
            tiers = cfg.get("aging_days", AGING_DAYS)
            reached = [c for d, c in zip(tiers, AGING_COLORS, strict=False) if age >= d]
            if reached:
                fill = f' data-background="{reached[-1]}" style="background-color: {reached[-1]}"'
        cells = [
            time_tag(start), esc(project), todo, lozenge, pic, link,
            time_tag(last["date"]),
        ]  # fmt: skip
        lines.append(
            "<tr>"
            + "".join(
                f"<td {c}{fill if i == 0 else ''}><p>{v}</p></td>"
                if i != 2
                else f"<td {c}>{v}</td>"
                for i, (v, c) in enumerate(zip(cells, cols, strict=True))
            )
            + "</tr>"
        )
    lines += ["</tbody>", "</table>"]
    return "\n".join(lines)


def cmd_publish(args: argparse.Namespace) -> None:
    """Print Confluence-ready HTML for the main or archive logbook."""
    archive = args.which == "archive"
    if args.empty:
        out = render_html([], {})
        if args.out:
            Path(args.out).write_text(out, encoding="utf-8")
        else:
            print(out)
        return
    items = group_items(read_rows(ARCHIVE if archive else LOGBOOK))
    if not archive:
        items += tracked_only_items(load_cache(), {i[0]["ticket"] for i in items})
    if args.year:
        items = [i for i in items if i[-1]["date"].startswith(f"{args.year}-")]
    if not items:
        sys.exit(
            f"No rows in the {args.which} logbook"
            + (f" for {args.year}." if args.year else ".")
        )
    # Active page: oldest work first. Archive: most recently finished first.
    cache = load_cache()

    def sort_key(item: list[dict[str, str]]) -> str:
        if archive:
            return item[-1]["date"]
        return cache.get(item[0]["ticket"], {}).get("created") or item[0]["date"]

    items.sort(key=sort_key, reverse=archive)
    body = render_html(items, load_config(), load_cache())
    note = f"<p>Generated {dt.date.today().isoformat()} from the local logbook ({args.which}).</p>"
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
    arch.add_argument("--days", type=int, default=14, help="age cut-off (default 14)")
    arch.add_argument("--dry-run", action="store_true")
    arch.set_defaults(func=cmd_archive)

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
        "--track",
        default="",
        choices=["", "yes", "no"],
        help="yes: DA ticket assigned to the user and open, so list it",
    )
    cache.set_defaults(func=cmd_cache)

    pub = sub.add_parser("publish", help="Render Confluence HTML (does not post it)")
    pub.add_argument("which", choices=["main", "archive"])
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
