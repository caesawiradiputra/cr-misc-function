#!/usr/bin/env python3
"""Preference registry helper: an evidence ledger kept as CSV files.

Files (override the folder with PREF_REGISTRY_DIR, default
~/.claude/preference-registry):

    registry-shared.csv   approved GLOBAL and DOMAIN records
    registry-project.csv  PROJECT records, candidates, unresolved conflicts
    registry-archive.csv  dropped, superseded and retired records

Stdlib only; runs on Python 3.9 and newer. Never hand-edit the CSVs: the helper
keeps the header, quoting, unique IDs and the atomic writes correct.

Commands: find, add, update, promote, report, archive, import-md.
The registry is a ledger. A row is never proof that a rule was written to a
file: Status `saved` is set only together with `--saved-in`.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import os
import re
import sys
import tempfile
from pathlib import Path

COLUMNS = [
    "ID", "Type", "Category", "Preference", "Keywords", "Scope", "Status",
    "Confidence", "First seen", "Last seen", "Seen", "Session IDs", "Repos",
    "Domains", "Evidence", "Explicit evidence", "Intended location", "Saved in",
    "Conflict", "Review trigger",
]  # fmt: skip
SCOPES = ("GLOBAL", "DOMAIN", "PROJECT")
STATUSES = ("candidate", "approved", "saved", "conflict", "dropped", "superseded")
CONFIDENCE = ("High", "Medium", "Low")
LIST_SEP = ";"  # separator inside Keywords, Session IDs, Repos and Domains
FILES = {
    "shared": "registry-shared.csv",
    "project": "registry-project.csv",
    "archive": "registry-archive.csv",
}
STOP = {
    "the", "and", "for", "with", "that", "this", "from", "into", "when", "not",
    "only", "each", "then", "than", "are", "was", "its", "any", "all", "use",
}  # fmt: skip

Row = dict[str, str]


class RegistryError(Exception):
    """A rule of the registry was violated; nothing was written."""


def registry_dir() -> Path:
    return Path(
        os.environ.get("PREF_REGISTRY_DIR")
        or Path.home() / ".claude/preference-registry"
    )


def path_of(which: str) -> Path:
    return registry_dir() / FILES[which]


def today() -> str:
    return dt.date.today().isoformat()


def split_list(value: str) -> list[str]:
    return [v.strip() for v in re.split(r"[;,]", value) if v.strip()]


def join_list(values: list[str]) -> str:
    seen: list[str] = []
    for v in values:
        if v and v not in seen:
            seen.append(v)
    return LIST_SEP.join(seen)


def read(which: str) -> list[Row]:
    path = path_of(which)
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames != COLUMNS:
            raise RegistryError(f"{path}: header does not match the registry columns")
        rows = []
        for r in reader:
            if None in r or any(v is None for v in r.values()):
                raise RegistryError(f"{path}: malformed row {r.get('ID')!r}")
            rows.append({k: str(v) for k, v in r.items()})
        return rows


def write(which: str, rows: list[Row]) -> None:
    path = path_of(which)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=path.name, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=COLUMNS, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def load_all() -> dict[str, list[Row]]:
    return {w: read(w) for w in FILES}


def locate(book: dict[str, list[Row]], pid: str) -> tuple[str, Row]:
    for which, rows in book.items():
        for r in rows:
            if r["ID"] == pid:
                return which, r
    raise RegistryError(f"no record with ID {pid}")


def next_id(book: dict[str, list[Row]]) -> str:
    nums = [
        int(m.group(1))
        for rows in book.values()
        for r in rows
        if (m := re.fullmatch(r"P-(\d+)", r["ID"]))
    ]
    return f"P-{max(nums, default=0) + 1:03d}"


def tokens(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9_\-]{3,}", text.lower()) if w not in STOP}


def similarity(a: str, b: str) -> float:
    ta, tb = tokens(a), tokens(b)
    return len(ta & tb) / len(ta | tb) if ta | tb else 0.0


def score(row: Row, kws: set[str], words: set[str]) -> float:
    row_kws = {k.lower() for k in split_list(row["Keywords"])}
    hay = tokens(row["Preference"] + " " + row["Keywords"] + " " + row["Category"])
    return 3.0 * len(kws & row_kws) + 1.0 * len(words & hay)


def short(row: Row, which: str) -> str:
    return (
        f"{row['ID']} [{which}] {row['Scope']} {row['Status']} seen={row['Seen']} "
        f"conf={row['Confidence']}\n    {row['Preference']}\n"
        f"    saved in: {row['Saved in'] or '-'}"
        + (f"\n    CONFLICT: {row['Conflict']}" if row["Conflict"] else "")
    )


def check_enum(value: str, allowed: tuple[str, ...], name: str) -> str:
    if value not in allowed:
        raise RegistryError(
            f"{name} must be one of {', '.join(allowed)} (got {value!r})"
        )
    return value


def cmd_find(args: argparse.Namespace) -> int:
    book = load_all()
    kws = {k.lower() for k in split_list(args.keywords or "")}
    words = tokens(args.text or "")
    if (
        not kws
        and not words
        and not (args.repo or args.domain or args.status or args.scope)
    ):
        raise RegistryError("give --keywords, --text or a filter")
    hits: list[tuple[float, str, Row]] = []
    for which, rows in book.items():
        if which == "archive" and not args.archive:
            continue
        for r in rows:
            if args.scope and r["Scope"] != args.scope:
                continue
            if args.status and r["Status"] != args.status:
                continue
            if args.repo and args.repo not in split_list(r["Repos"]):
                continue
            if args.domain and args.domain not in split_list(r["Domains"]):
                continue
            s = score(r, kws, words) if (kws or words) else 1.0
            if s > 0:
                # shared records first: a rule that is already global settles the check
                hits.append((s + (0.5 if which == "shared" else 0.0), which, r))
    hits.sort(key=lambda h: -h[0])
    if not hits:
        print("no matching records")
        return 0
    for _, which, r in hits[: args.limit]:
        print(short(r, which))
    return 0


def split_scope(arg_scope: str) -> str:
    return check_enum(arg_scope.upper(), SCOPES, "scope")


def cmd_add(args: argparse.Namespace) -> int:
    book = load_all()
    scope = split_scope(args.scope)
    for which, rows in book.items():
        for r in rows:
            shared_kws = {k.lower() for k in split_list(r["Keywords"])} & {
                k.lower() for k in split_list(args.keywords)
            }
            if (
                similarity(r["Preference"], args.preference) >= 0.45
                or len(shared_kws) >= 3
            ) and not args.force:
                raise RegistryError(
                    f"possible duplicate of {r['ID']} ({which}): {r['Preference']!r}. "
                    "Update that record, or add --force if it is a different rule."
                )
    if not args.session:
        raise RegistryError("--session is required: it is the dedup key for sightings")
    status = check_enum(args.status, STATUSES, "status")
    if status == "saved" and not args.saved_in:
        raise RegistryError("status saved needs --saved-in (what was actually written)")
    date = args.date or today()
    row: Row = dict.fromkeys(COLUMNS, "")
    row.update(
        {
            "ID": next_id(book),
            "Type": args.type,
            "Category": args.category or "",
            "Preference": args.preference,
            "Keywords": join_list([k.lower() for k in split_list(args.keywords)]),
            "Scope": scope,
            "Status": status,
            "Confidence": check_enum(args.confidence, CONFIDENCE, "confidence"),
            "First seen": date,
            "Last seen": date,
            "Seen": "1",
            "Session IDs": args.session,
            "Repos": join_list(split_list(args.repo or "")),
            "Domains": join_list(split_list(args.domain or "")),
            "Evidence": args.evidence or "",
            "Explicit evidence": "yes" if args.explicit else "no",
            "Intended location": args.intended_location or "",
            "Saved in": args.saved_in or "",
        }
    )
    which = (
        "shared"
        if scope in ("GLOBAL", "DOMAIN") and status in ("approved", "saved")
        else "project"
    )
    book[which].append(row)
    write(which, book[which])
    print(f"added {row['ID']} to {which}")
    return 0


def cmd_update(args: argparse.Namespace) -> int:
    book = load_all()
    which, row = locate(book, args.id)
    if args.sighting:
        if not args.session:
            raise RegistryError("--sighting needs --session (counts each session once)")
        sessions = split_list(row["Session IDs"])
        if args.session in sessions:
            print(f"{args.id}: session already counted, Seen stays {row['Seen']}")
        else:
            row["Seen"] = str(int(row["Seen"] or "0") + 1)
            row["Session IDs"] = join_list(sessions + [args.session])
            row["Last seen"] = args.date or today()
        if args.explicit:
            row["Explicit evidence"] = "yes"
    for col, val in (("Repos", args.repo), ("Domains", args.domain)):
        if val:
            row[col] = join_list(split_list(row[col]) + split_list(val))
    if args.keywords:
        row["Keywords"] = join_list(
            split_list(row["Keywords"]) + [k.lower() for k in split_list(args.keywords)]
        )
    if args.preference:
        row["Evidence"] = join_list(
            [row["Evidence"], f"refined {today()}: was {row['Preference']!r}"]
        )
        row["Preference"] = args.preference
    if args.confidence:
        row["Confidence"] = check_enum(args.confidence, CONFIDENCE, "confidence")
    if args.evidence:
        row["Evidence"] = join_list([row["Evidence"], args.evidence])
    for col, val in (
        ("Intended location", args.intended_location),
        ("Saved in", args.saved_in),
        ("Review trigger", args.review_trigger),
    ):
        if val is not None:
            row[col] = val
    if args.conflict is not None:
        row["Conflict"] = args.conflict
        if args.conflict:
            row["Status"] = "conflict"
    if args.status:
        status = check_enum(args.status, STATUSES, "status")
        if status == "saved" and not (args.saved_in or row["Saved in"]):
            raise RegistryError(
                "status saved needs --saved-in (what was actually written)"
            )
        if status in ("dropped", "superseded"):
            raise RegistryError(f"use `archive --status {status}` to retire a record")
        row["Status"] = status
    if args.scope and args.scope.upper() != row["Scope"]:
        raise RegistryError("scope changes go through `promote` (after user approval)")
    write(which, book[which])
    print(f"updated {args.id} in {which}")
    return 0


def cmd_promote(args: argparse.Namespace) -> int:
    book = load_all()
    which, row = locate(book, args.id)
    target = check_enum(args.to.upper(), ("DOMAIN", "GLOBAL"), "--to")
    if which != "project" and not (
        which == "shared" and row["Scope"] == "DOMAIN" and target == "GLOBAL"
    ):
        raise RegistryError(
            f"{args.id} is in {which} with scope {row['Scope']}: nothing to promote"
        )
    if row["Status"] == "conflict":
        raise RegistryError(f"{args.id} is in conflict: resolve it first")
    if row["Status"] not in ("approved", "saved"):
        raise RegistryError(
            f"{args.id} is {row['Status']}: the user must approve it first"
        )
    if not (args.saved_in or row["Saved in"]):
        raise RegistryError(
            "promote needs --saved-in: where the wider rule was written"
        )
    if any(r["ID"] == args.id for r in book["shared"]) and which == "project":
        raise RegistryError(f"{args.id} already exists in shared")
    new = dict(row)
    new["Scope"] = target
    new["Status"] = "saved"
    new["Saved in"] = args.saved_in or row["Saved in"]
    new["Review trigger"] = ""
    dest_rows = [r for r in book["shared"] if r["ID"] != args.id] + [new]
    backup = list(book["shared"])
    try:
        write("shared", dest_rows)
        if which == "project":
            write("project", [r for r in book["project"] if r["ID"] != args.id])
    except BaseException:
        write("shared", backup)  # keep the original rows if the move fails half-way
        raise
    print(f"promoted {args.id} to {target} (shared)")
    return 0


def cmd_archive(args: argparse.Namespace) -> int:
    book = load_all()
    which, row = locate(book, args.id)
    if which == "archive":
        raise RegistryError(f"{args.id} is already archived")
    status = check_enum(
        args.status, ("dropped", "superseded", "saved", "candidate"), "status"
    )
    row["Status"] = status
    row["Evidence"] = join_list([row["Evidence"], f"archived {today()}: {args.reason}"])
    backup = list(book["archive"])
    try:
        write("archive", book["archive"] + [row])
        write(which, [r for r in book[which] if r["ID"] != args.id])
    except BaseException:
        write("archive", backup)
        raise
    print(f"archived {args.id} ({status})")
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    book = load_all()
    live = [(w, r) for w in ("shared", "project") for r in book[w]]
    sections: dict[str, list[str]] = {
        "Conflicts (block promotion)": [],
        "Eligible PROJECT -> DOMAIN (2+ sightings, explicit, 2+ repos)": [],
        "Eligible DOMAIN -> GLOBAL (2+ domains)": [],
        "Needs an explicit confirmation (inferred only)": [],
        "Approved but not written yet": [],
        "Intended scope wider than where it is saved": [],
        "Review trigger set": [],
    }
    for which, r in live:
        n, repos, doms = (
            int(r["Seen"] or "0"),
            split_list(r["Repos"]),
            split_list(r["Domains"]),
        )
        label = f"{r['ID']} {r['Preference'][:90]}"
        if r["Status"] == "conflict":
            sections["Conflicts (block promotion)"].append(label)
        if which == "project" and r["Status"] in ("approved", "saved", "candidate"):
            if (
                r["Scope"] == "PROJECT"
                and n >= 2
                and r["Explicit evidence"] == "yes"
                and len(repos) >= 2
            ):
                sections[
                    "Eligible PROJECT -> DOMAIN (2+ sightings, explicit, 2+ repos)"
                ].append(label)
        if (
            which == "shared"
            and r["Scope"] == "DOMAIN"
            and len(doms) >= 2
            and r["Status"] != "conflict"
        ):
            sections["Eligible DOMAIN -> GLOBAL (2+ domains)"].append(label)
        if r["Explicit evidence"] != "yes" and r["Status"] == "candidate":
            sections["Needs an explicit confirmation (inferred only)"].append(label)
        if r["Status"] == "approved":
            sections["Approved but not written yet"].append(label)
        if (
            which == "project"
            and r["Scope"] in ("GLOBAL", "DOMAIN")
            and r["Status"] == "saved"
        ):
            sections["Intended scope wider than where it is saved"].append(
                f"{label} (saved in: {r['Saved in'][:60]})"
            )
        if r["Review trigger"]:
            sections["Review trigger set"].append(f"{label} -> {r['Review trigger']}")
    print(
        f"# Registry report: {len(book['shared'])} shared, {len(book['project'])} project, {len(book['archive'])} archived"
    )
    for title, items in sections.items():
        print(f"\n## {title}")
        print("\n".join(f"- {i}" for i in items) if items else "- none")
    print("\nEligibility is a proposal only: a scope change needs the user's approval.")
    return 0


def cmd_import_md(args: argparse.Namespace) -> int:
    """One-time import of the old markdown table (legacy rows have no session IDs)."""
    meta = {}
    for line in Path(args.meta).read_text(encoding="utf-8").splitlines():
        if line.strip():
            pid, kw, shared = (line.split("\t") + ["", ""])[:3]
            meta[pid] = (kw, shared == "shared")
    book = load_all()
    if any(book.values()) and not args.force:
        raise RegistryError("registry is not empty: add --force to import anyway")
    out: dict[str, list[Row]] = {
        "shared": [],
        "project": [],
        "archive": book["archive"],
    }
    for line in Path(args.source).read_text(encoding="utf-8").splitlines():
        if not re.match(r"\| P-\d+ \|", line):
            continue
        c = [x.strip() for x in line.strip().strip("|").split(" | ")]
        pid, pref, scope_txt, status, conf, seen, dates, repos, saved = c[:9]
        scope = scope_txt.split(":")[0].split("(")[0].strip().upper()
        detail = re.sub(r"^[A-Z]+\s*[:(]\s*", "", scope_txt).rstrip(")").strip()
        first, _, last = dates.partition(" / ")
        kw, is_shared = meta.get(pid, ("", False))
        repo_list = [
            x.strip()
            for x in re.split(r",", re.sub(r"\(.*?\)", "", repos))
            if x.strip()
        ]
        row: Row = dict.fromkeys(COLUMNS, "")
        row.update(
            {
                "ID": pid, "Type": "positive", "Preference": pref, "Keywords": kw,
                "Scope": scope, "Status": status, "Confidence": conf,
                "First seen": first, "Last seen": last or first, "Seen": seen,
                "Repos": join_list(repo_list),
                "Domains": detail if scope == "DOMAIN" else "",
                "Evidence": f"legacy import {today()}: session IDs were not recorded",
                "Explicit evidence": "yes" if status == "saved" else "no",
                "Saved in": "" if saved.startswith("not saved") else saved,
                "Intended location": "",
            }
        )  # fmt: skip
        out["shared" if is_shared else "project"].append(row)
    for which in ("shared", "project"):
        write(which, out[which])
    write("archive", out["archive"])
    print(f"imported {len(out['shared'])} shared, {len(out['project'])} project")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    f = sub.add_parser("find", help="search by keywords, text and filters")
    f.add_argument("--keywords"), f.add_argument("--text")
    f.add_argument("--scope"), f.add_argument("--repo"), f.add_argument("--domain")
    f.add_argument("--status"), f.add_argument("--limit", type=int, default=8)
    f.add_argument("--archive", action="store_true", help="include the archive")
    f.set_defaults(fn=cmd_find)

    a = sub.add_parser("add", help="create a new record")
    (
        a.add_argument("--preference", required=True),
        a.add_argument("--keywords", required=True),
    )
    a.add_argument("--scope", required=True), a.add_argument("--session")
    (
        a.add_argument("--status", default="candidate"),
        a.add_argument("--confidence", default="Low"),
    )
    a.add_argument("--type", default="positive", choices=("positive", "negative"))
    a.add_argument("--category"), a.add_argument("--repo"), a.add_argument("--domain")
    (
        a.add_argument("--evidence"),
        a.add_argument("--intended-location"),
        a.add_argument("--saved-in"),
    )
    a.add_argument("--date"), a.add_argument("--explicit", action="store_true")
    a.add_argument("--force", action="store_true", help="skip the duplicate check")
    a.set_defaults(fn=cmd_add)

    u = sub.add_parser("update", help="add evidence or change fields of one record")
    u.add_argument("id"), u.add_argument("--sighting", action="store_true")
    (
        u.add_argument("--session"),
        u.add_argument("--date"),
        u.add_argument("--explicit", action="store_true"),
    )
    u.add_argument("--repo"), u.add_argument("--domain"), u.add_argument("--keywords")
    (
        u.add_argument("--preference"),
        u.add_argument("--confidence"),
        u.add_argument("--evidence"),
    )
    u.add_argument("--status"), u.add_argument("--scope"), u.add_argument("--saved-in")
    u.add_argument("--intended-location"), u.add_argument("--review-trigger")
    u.add_argument("--conflict", help="describe the conflict; empty string clears it")
    u.set_defaults(fn=cmd_update)

    pr = sub.add_parser(
        "promote", help="move an approved record to the shared registry"
    )
    (
        pr.add_argument("id"),
        pr.add_argument("--to", required=True),
        pr.add_argument("--saved-in"),
    )
    pr.set_defaults(fn=cmd_promote)

    ar = sub.add_parser("archive", help="move a record to the archive")
    ar.add_argument("id"), ar.add_argument("--reason", required=True)
    ar.add_argument("--status", default="dropped")
    ar.set_defaults(fn=cmd_archive)

    rp = sub.add_parser("report", help="conflicts, promotion eligibility, gaps")
    rp.set_defaults(fn=cmd_report)

    im = sub.add_parser(
        "import-md", help="one-time import of the old markdown registry"
    )
    im.add_argument("--source", required=True), im.add_argument("--meta", required=True)
    im.add_argument("--force", action="store_true")
    im.set_defaults(fn=cmd_import_md)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return int(args.fn(args))
    except RegistryError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
