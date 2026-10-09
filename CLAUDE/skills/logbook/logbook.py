#!/usr/bin/env python3
"""Work logbook: upsert rows, print a weekly summary, copy the CSV to Windows."""

import argparse
import csv
import datetime as dt
import shutil
import sys
from pathlib import Path

LOGBOOK = Path.home() / ".claude" / "logbook" / "logbook.csv"
WINDOWS_COPY = Path(
    "/mnt/c/Users/<WINDOWS_USERNAME>/Documents/Work/Logbook/logbook.csv"
)
COLUMNS = [
    "date", "week", "ticket", "repo", "branch", "type",
    "task", "status", "pr_url", "notes",
]  # fmt: skip


def read_rows() -> list[dict[str, str]]:
    if not LOGBOOK.exists():
        return []
    with LOGBOOK.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_rows(rows: list[dict[str, str]]) -> None:
    LOGBOOK.parent.mkdir(parents=True, exist_ok=True)
    with LOGBOOK.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def iso_week(date: str) -> str:
    year, week, _ = dt.date.fromisoformat(date).isocalendar()
    return f"{year}-W{week:02d}"


def cmd_add(args: argparse.Namespace) -> None:
    date = args.date or dt.date.today().isoformat()
    new = {
        "date": date, "week": iso_week(date), "ticket": args.ticket,
        "repo": args.repo, "branch": args.branch, "type": args.type,
        "task": args.task, "status": args.status, "pr_url": args.pr_url,
        "notes": args.notes,
    }  # fmt: skip
    rows = read_rows()
    for row in rows:
        if row["date"] == date and row["ticket"] == args.ticket:
            row.update({k: v for k, v in new.items() if v})  # keep old values
            action = "updated"
            break
    else:
        rows.append(new)
        action = "added"
    write_rows(rows)
    print(f"{action}: {date} {args.ticket} [{new['status'] or '-'}]")


def cmd_week(args: argparse.Namespace) -> None:
    week = args.week or iso_week(dt.date.today().isoformat())
    by_ticket: dict[str, list[dict[str, str]]] = {}
    for row in read_rows():
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


def cmd_sync(args: argparse.Namespace) -> None:
    if not LOGBOOK.exists():
        sys.exit("No logbook to copy.")
    if args.daily and WINDOWS_COPY.exists():
        copied = dt.date.fromtimestamp(WINDOWS_COPY.stat().st_mtime)
        if copied == dt.date.today():
            print(
                "Already copied today; skipped (use `sync` without --daily to force)."
            )
            return
    WINDOWS_COPY.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(LOGBOOK, WINDOWS_COPY)
    print(f"copied to {WINDOWS_COPY}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(required=True)

    add = sub.add_parser("add", help="Add or update the row for date+ticket")
    for name in ("ticket", "task"):
        add.add_argument(f"--{name}", required=True)
    for name in ("repo", "branch", "type", "status", "pr-url", "notes", "date"):
        add.add_argument(f"--{name}", default="")
    add.set_defaults(func=cmd_add)

    week = sub.add_parser("week", help="Print a weekly summary")
    week.add_argument("--week", default="", help="e.g. 2026-W41 (default: current)")
    week.set_defaults(func=cmd_week)

    sync = sub.add_parser("sync", help="Copy the CSV to the Windows work folder")
    sync.add_argument(
        "--daily", action="store_true", help="Skip if already copied today"
    )
    sync.set_defaults(func=cmd_sync)

    args = parser.parse_args()
    args.pr_url = getattr(args, "pr_url", "")
    args.func(args)


if __name__ == "__main__":
    main()
