#!/usr/bin/env python3
"""Work logbook: upsert rows, print a weekly summary, copy the CSV to Windows.

Paths (override for tests with environment variables):
  LOGBOOK_PATH         master CSV (default ~/.claude/logbook/logbook.csv)
  LOGBOOK_WINDOWS_DIR  Windows export folder, e.g. /mnt/c/Users/<you>/Documents/Work/Logbook
                       (fallback: first line of ~/.claude/logbook/windows_dir.txt)
"""

import argparse
import csv
import datetime as dt
import filecmp
import os
import shutil
import sys
import tempfile
from pathlib import Path

LOGBOOK = Path(
    os.environ.get("LOGBOOK_PATH") or Path.home() / ".claude/logbook/logbook.csv"
)
WINDOWS_DIR_FILE = LOGBOOK.parent / "windows_dir.txt"
COLUMNS = [
    "date", "week", "ticket", "repo", "branch", "type",
    "task", "status", "pr_url", "notes",
]  # fmt: skip
TYPES = ["fea", "fix", "chore", "docs", "refactor", "ops"]
STATUSES = [
    "In progress", "PR to dev", "Merged to dev", "Merged to sit",
    "PR to master", "Released", "Done",
]  # fmt: skip


def read_rows() -> list[dict[str, str]]:
    """Read the master CSV, aborting (without writing) if its shape is wrong."""
    if not LOGBOOK.exists():
        return []
    with LOGBOOK.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != COLUMNS:
            sys.exit(
                f"{LOGBOOK}: header {reader.fieldnames} != expected {COLUMNS}. "
                "Fix the file by hand; nothing was changed."
            )
        rows = list(reader)
    for number, row in enumerate(rows, start=2):
        if None in row or None in row.values():
            sys.exit(f"{LOGBOOK}: line {number} has the wrong number of fields.")
    return rows


def write_rows(rows: list[dict[str, str]]) -> None:
    """Write the CSV atomically: temp file in the same folder, then replace."""
    LOGBOOK.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=LOGBOOK.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=COLUMNS)
            writer.writeheader()
            writer.writerows(rows)
        os.replace(tmp, LOGBOOK)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def iso_week(date: str) -> str:
    try:
        year, week, _ = dt.date.fromisoformat(date).isocalendar()
    except ValueError:
        sys.exit(f"Invalid date {date!r}; use YYYY-MM-DD.")
    return f"{year}-W{week:02d}"


def windows_copy_path() -> Path:
    folder = os.environ.get("LOGBOOK_WINDOWS_DIR", "").strip()
    if not folder and WINDOWS_DIR_FILE.exists():
        folder = WINDOWS_DIR_FILE.read_text(encoding="utf-8").strip()
    if not folder:
        sys.exit(
            "No Windows destination. Set LOGBOOK_WINDOWS_DIR or put the folder path "
            f"on the first line of {WINDOWS_DIR_FILE}."
        )
    path = Path(folder)
    if not path.parent.is_dir():
        sys.exit(f"Windows destination parent does not exist: {path.parent}")
    return path / LOGBOOK.name


def cmd_add(args: argparse.Namespace) -> None:
    date = args.date or dt.date.today().isoformat()
    week = iso_week(date)  # also rejects an invalid date before anything is written
    new = {
        "date": date, "week": week, "ticket": args.ticket,
        "repo": args.repo, "branch": args.branch, "type": args.type,
        "task": args.task, "status": args.status, "pr_url": args.pr_url,
        "notes": args.notes,
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
    by_ticket: dict[str, list[dict[str, str]]] = {}
    for row in sorted(read_rows(), key=lambda r: r["date"]):  # stable: ties keep order
        if row["week"] == week:
            by_ticket.setdefault(row["ticket"], []).append(row)
    if not by_ticket:
        print(f"No entries for {week}.")
        return
    print(f"## Weekly report {week}\n")
    for ticket, rows in by_ticket.items():
        last = rows[-1]
        print(f"- **{ticket}** ({last['repo']}, {last['type']}): {last['task']}")
        print(
            f"  - status: {last['status'] or '-'}"
            + (f" | PR: {last['pr_url']}" if last["pr_url"] else "")
        )
        for row in rows:
            if row["notes"]:
                print(f"  - {row['date']}: {row['notes']}")


def cmd_sync(_: argparse.Namespace) -> None:
    if not LOGBOOK.exists():
        sys.exit("No logbook to copy.")
    dest = windows_copy_path()
    if dest.exists() and filecmp.cmp(LOGBOOK, dest, shallow=False):
        print(f"already up to date: {dest}")
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(LOGBOOK, dest)
    print(f"copied to {dest}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(required=True)

    add = sub.add_parser("add", help="Add or update the row for date+ticket")
    for name in ("ticket", "task"):
        add.add_argument(f"--{name}", required=True)
    for name in ("repo", "branch", "pr-url", "notes", "date"):
        add.add_argument(f"--{name}", default="")
    add.add_argument("--type", default="", choices=["", *TYPES])
    add.add_argument("--status", default="", choices=["", *STATUSES])
    add.set_defaults(func=cmd_add)

    week = sub.add_parser("week", help="Print a weekly summary")
    week.add_argument("--week", default="", help="e.g. 2026-W41 (default: current)")
    week.set_defaults(func=cmd_week)

    sync = sub.add_parser(
        "sync", help="Copy the CSV to the Windows folder if it differs"
    )
    sync.set_defaults(func=cmd_sync)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
