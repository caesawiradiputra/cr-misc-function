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


def render_html(items: list[list[dict[str, str]]], cfg: dict) -> str:
    """One table row per ticket, in the column layout of the Confluence weekly page."""
    esc = html.escape
    head = [
        "#",
        "Start Date",
        "Project",
        "To Do",
        "Status",
        "PIC",
        "JIRA",
        "LastUpdate",
    ]
    lines = [
        "<table><tbody>",
        "<tr>" + "".join(f"<th>{h}</th>" for h in head) + "</tr>",
    ]
    for number, item in enumerate(items, start=1):
        first, last = item[0], item[-1]
        ticket = first["ticket"]
        link = esc(ticket)
        base = cfg.get("jira_base", "")
        if base and re.fullmatch(r"[A-Z][A-Z0-9]+-\d+", ticket):
            link = f'<a href="{esc(base + ticket)}">{esc(ticket)}</a>'
        notes = "".join(
            f"<li>{esc(r['date'])}: {esc(r['notes'])}</li>" for r in item if r["notes"]
        )
        todo = f"<p><strong>{esc(last['task'])}</strong></p>" + (
            f"<ul>{notes}</ul>" if notes else ""
        )
        status = PAGE_STATUS.get(last["status"], last["status"].upper() or "-")
        project = cfg.get("projects", {}).get(last["repo"], last["repo"])
        cells = [
            str(number), first["date"], esc(project), todo,
            f"<strong>{esc(status)}</strong>", esc(cfg.get("pic", "")), link,
            last["date"],
        ]  # fmt: skip
        lines.append("<tr>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>")
    lines.append("</tbody></table>")
    return "\n".join(lines)


def cmd_publish(args: argparse.Namespace) -> None:
    """Print Confluence-ready HTML for the main or archive logbook."""
    archive = args.which == "archive"
    items = group_items(read_rows(ARCHIVE if archive else LOGBOOK))
    if not items:
        sys.exit(f"No rows in the {args.which} logbook.")
    # Active page: oldest work first. Archive: most recently finished first.
    items.sort(
        key=lambda item: item[-1]["date"] if archive else item[0]["date"],
        reverse=archive,
    )
    body = render_html(items, load_config())
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

    pub = sub.add_parser("publish", help="Render Confluence HTML (does not post it)")
    pub.add_argument("which", choices=["main", "archive"])
    pub.add_argument("--out", default="", help="write to a file instead of stdout")
    pub.set_defaults(func=cmd_publish)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
