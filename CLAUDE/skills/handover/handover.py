#!/usr/bin/env python3
"""Ticket handover inventory: where a ticket's work lives, for whoever takes over.

Two files per ticket, both under the repository:
  release/<TICKET>/docs/HANDOVER.md        committed: branch, object table, notes
  scratch/<TICKET>/handover.state.json     ignored: posting bookkeeping and links

The helper is local and never talks to Jira or to any platform. The model posts the Jira
comment with the Atlassian tools after the user's OK (see the skill text).
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

PLATFORMS = [
    "DataWorks", "Hologres", "Hive", "MaxCompute", "Postgres", "MySQL", "Trino",
    "Flink", "OSS", "Airflow", "Kafka", "Other",
]  # fmt: skip
ENVS = ["dev", "sit", "uat", "prod"]
STATES = ["planned", "touched"]
COLUMNS = ["Platform", "Locator", "Object", "Env", "State", "Plan", "Source"]
TICKET_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")
SECRET_RE = re.compile(
    r"(?i)\b(?:password|passwd|pwd|token|secret|api[_-]?key|access[_-]?key)\b\s*[=:]\s*\S+"
    r"|://[^/\s:@]+:[^@\s]+@"
)
HEADER_LINE = "| " + " | ".join(COLUMNS) + " |"
SEPARATOR_LINE = "| " + " | ".join("---" for _ in COLUMNS) + " |"
TEMPLATE = (
    "# Handover: {ticket}\n\n- Branch: `{branch}`\n\n## Objects\n\n"
    + HEADER_LINE
    + "\n"
    + SEPARATOR_LINE
    + "\n\n## Notes\n\n"
)


class HandoverError(Exception):
    """A user-facing error: bad input, a refused transition, a missing file."""


def validate_ticket(ticket: str) -> str:
    if not TICKET_RE.fullmatch(ticket) or ".." in ticket:
        raise HandoverError(
            f"invalid ticket id {ticket!r}: use letters, digits, dot, underscore and hyphen"
        )
    return ticket


def find_repo(repo: str | None = None) -> Path:
    """The repository top level for --repo, or for the current directory."""
    start = Path(repo).expanduser() if repo else Path.cwd()
    try:
        done = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=start, capture_output=True, text=True, timeout=30,
        )  # fmt: skip
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise HandoverError(f"cannot run git in {start}: {exc}") from exc
    if done.returncode != 0:
        raise HandoverError(f"{start} is not inside a git repository")
    return Path(done.stdout.strip())


def inventory_path(repo: Path, ticket: str) -> Path:
    return repo / "release" / validate_ticket(ticket) / "docs" / "HANDOVER.md"


def state_path(repo: Path, ticket: str) -> Path:
    return repo / "scratch" / validate_ticket(ticket) / "handover.state.json"


def check_value(value: str, field: str, allow_secret_like: bool = False) -> str:
    """A single-line value that does not look like a credential."""
    if "\n" in value or "\r" in value:
        raise HandoverError(f"{field} must be a single line")
    if not allow_secret_like and SECRET_RE.search(value):
        raise HandoverError(
            f"{field} looks like a credential; remove it or pass --allow-secret-like"
        )
    return value.strip()


def write_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(text.encode("utf-8"))
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def split_row(line: str) -> list[str]:
    text = line.strip()
    if text.startswith("|"):
        text = text[1:]
    if text.endswith("|") and not text.endswith("\\|"):
        text = text[:-1]
    return [cell.replace("\\|", "|").strip() for cell in re.split(r"(?<!\\)\|", text)]


def join_row(cells: list[str]) -> str:
    return "| " + " | ".join(cell.replace("|", "\\|") for cell in cells) + " |"


class Inventory:
    """The text of HANDOVER.md as a list of lines; edits touch only the lines they own."""

    def __init__(self, text: str) -> None:
        self.eol = "\r\n" if "\r\n" in text else "\n"
        self.lines = text.replace("\r\n", "\n").split("\n")

    def dump(self) -> str:
        return self.eol.join(self.lines)

    def heading(self, name: str) -> int | None:
        for i, line in enumerate(self.lines):
            if line.strip().lower() == f"## {name}".lower():
                return i
        return None

    def table_span(self) -> tuple[int, int] | None:
        """(index of the first data row, index after the last table line)."""
        start = self.heading("Objects")
        if start is None:
            return None
        i = start + 1
        while i < len(self.lines) and not self.lines[i].lstrip().startswith("|"):
            if self.lines[i].startswith("## "):
                return None
            i += 1
        if i + 1 >= len(self.lines) or not self.lines[i + 1].lstrip().startswith(
            "| ---"
        ):
            return None
        first = i + 2
        end = first
        while end < len(self.lines) and self.lines[end].lstrip().startswith("|"):
            end += 1
        return first, end

    def rows(self) -> tuple[list[tuple[int, list[str]]], list[str]]:
        """Valid rows as (line index, cells) and a problem per malformed row."""
        span = self.table_span()
        if span is None:
            raise HandoverError(
                "no Objects table in the handover file; run init or fix the file"
            )
        rows: list[tuple[int, list[str]]] = []
        problems: list[str] = []
        for idx in range(span[0], span[1]):
            cells = split_row(self.lines[idx])
            if len(cells) == len(COLUMNS):
                rows.append((idx, cells))
            else:
                problems.append(
                    f"line {idx + 1}: malformed table row ({len(cells)} cells)"
                )
        return rows, problems

    def branch(self) -> str:
        for line in self.lines:
            if line.startswith("- Branch:"):
                return line.split(":", 1)[1].strip().strip("`")
        return "-"

    def notes(self) -> list[str]:
        start = self.heading("Notes")
        if start is None:
            return []
        out: list[str] = []
        for line in self.lines[start + 1 :]:
            if line.startswith("## "):
                break
            if line.strip().startswith("- "):
                out.append(line.strip())
        return out


def cmd_init(repo: Path, ticket: str, branch: str) -> Path:
    path = inventory_path(repo, ticket)
    if path.exists():
        raise HandoverError(f"{path} already exists")
    branch = check_value(branch, "branch", allow_secret_like=True)
    write_atomic(path, TEMPLATE.format(ticket=ticket, branch=branch))
    return path


def norm(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def row_key(cells: list[str]) -> tuple[str, str, str, str]:
    return (
        cells[0].lower(),
        norm(cells[1]).lower(),
        norm(cells[2]).lower(),
        cells[3].lower(),
    )


def split_list(cell: str) -> list[str]:
    parts = [p.strip().strip("`").strip() for p in cell.split(";")]
    return [p for p in parts if p and p != "-"]


def join_list(items: list[str]) -> str:
    return "; ".join(f"`{i}`" for i in items) if items else "-"


def normalise_path(repo: Path, value: str) -> str:
    """A repository-relative path with forward slashes; refuses anything outside the repo."""
    text = value.strip().replace("\\", "/")
    if not text:
        raise HandoverError("empty path")
    if Path(text).is_absolute():
        try:
            text = Path(text).resolve().relative_to(repo.resolve()).as_posix()
        except ValueError:
            raise HandoverError(f"path {value!r} is outside the repository") from None
    parts: list[str] = []
    for part in text.split("/"):
        if part in ("", "."):
            continue
        if part == "..":
            if not parts:
                raise HandoverError(f"path {value!r} escapes the repository")
            parts.pop()
            continue
        parts.append(part)
    if not parts:
        raise HandoverError(f"path {value!r} is empty after normalising")
    return "/".join(parts)


def canon_platform(value: str) -> str:
    for name in PLATFORMS:
        if name.lower() == value.strip().lower():
            return name
    raise HandoverError(
        f"unknown platform {value!r}; use one of {', '.join(PLATFORMS)}"
    )


def canon_env(value: str) -> str:
    env = value.strip().lower()
    if env not in ENVS:
        raise HandoverError(
            f"unknown environment {value!r}; use one of {', '.join(ENVS)}"
        )
    return env


def load_inventory(repo: Path, ticket: str) -> Inventory:
    path = inventory_path(repo, ticket)
    if not path.exists():
        raise HandoverError(f"no handover file at {path}; run init")
    return Inventory(path.read_bytes().decode("utf-8"))


def save_inventory(repo: Path, ticket: str, inv: Inventory) -> None:
    write_atomic(inventory_path(repo, ticket), inv.dump())


def _clean_cells(
    platform: str, locator: str, obj: str, env: str, allow_secret_like: bool
) -> tuple[str, str, str, str]:
    plat = canon_platform(platform)
    e = canon_env(env)
    loc = norm(check_value(locator, "locator", allow_secret_like))
    name = norm(check_value(obj, "object", allow_secret_like))
    if not loc or not name:
        raise HandoverError("locator and object must not be empty")
    return plat, loc, name, e


def cmd_add(
    repo: Path,
    ticket: str,
    platform: str,
    locator: str,
    obj: str,
    env: str,
    state: str,
    source: str | None = None,
    allow_secret_like: bool = False,
) -> str:
    if state not in STATES:
        raise HandoverError(f"unknown state {state!r}; use planned or touched")
    plat, loc, name, e = _clean_cells(platform, locator, obj, env, allow_secret_like)
    src = normalise_path(repo, check_value(source, "source", True)) if source else None
    inv = load_inventory(repo, ticket)
    rows, _ = inv.rows()
    key = (plat.lower(), loc.lower(), name.lower(), e)
    for idx, cells in rows:
        if row_key(cells) == key:
            if state == "touched":
                cells[4] = "touched"
            if src and src not in split_list(cells[6]):
                cells[6] = join_list([*split_list(cells[6]), src])
            inv.lines[idx] = join_row(cells)
            save_inventory(repo, ticket, inv)
            return "updated"
    span = inv.table_span()
    assert span is not None
    inv.lines.insert(
        span[1],
        join_row([plat, loc, name, e, state, "-", join_list([src] if src else [])]),
    )
    save_inventory(repo, ticket, inv)
    return "added"


def cmd_remove(
    repo: Path, ticket: str, platform: str, locator: str, obj: str, env: str
) -> bool:
    plat, loc, name, e = _clean_cells(platform, locator, obj, env, True)
    inv = load_inventory(repo, ticket)
    rows, _ = inv.rows()
    key = (plat.lower(), loc.lower(), name.lower(), e)
    for idx, cells in rows:
        if row_key(cells) == key:
            del inv.lines[idx]
            save_inventory(repo, ticket, inv)
            return True
    return False


def cmd_note(
    repo: Path, ticket: str, text: str, allow_secret_like: bool = False
) -> None:
    line = check_value(text, "note", allow_secret_like)
    if not line:
        raise HandoverError("empty note")
    inv = load_inventory(repo, ticket)
    start = inv.heading("Notes")
    if start is None:
        inv.lines += ["", "## Notes", ""]
        start = len(inv.lines) - 2
    end = len(inv.lines)
    for i in range(start + 1, len(inv.lines)):
        if inv.lines[i].startswith("## "):
            end = i
            break
    pos = end
    while pos - 1 > start and inv.lines[pos - 1].strip() == "":
        pos -= 1
    if pos == start + 1:
        inv.lines[pos:pos] = ["", f"- {line}"]
    else:
        inv.lines.insert(pos, f"- {line}")
    save_inventory(repo, ticket, inv)


def cmd_set_branch(repo: Path, ticket: str, branch: str) -> None:
    branch = check_value(branch, "branch", True)
    inv = load_inventory(repo, ticket)
    for i, line in enumerate(inv.lines):
        if line.startswith("- Branch:"):
            inv.lines[i] = f"- Branch: `{branch}`"
            break
    else:
        inv.lines[2:2] = [f"- Branch: `{branch}`", ""]
    save_inventory(repo, ticket, inv)


def cmd_show(repo: Path, ticket: str) -> str:
    return load_inventory(repo, ticket).dump()


def load_objects_file(path: Path) -> list[dict[str, str]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HandoverError(f"cannot read the objects file {path}: {exc}") from exc
    if not isinstance(data, list):
        raise HandoverError("the objects file must be a JSON list of objects")
    return data


def cmd_plan_sync(
    repo: Path,
    ticket: str,
    source: str,
    objects: list[Any],
    allow_empty: bool = False,
) -> dict[str, int]:
    """Reconcile one plan source: add what it names, drop planned rows it no longer names."""
    src = normalise_path(repo, source)
    if not objects and not allow_empty:
        raise HandoverError(
            "the objects list is empty; pass --allow-empty to remove its rows"
        )
    listed: dict[tuple[str, str, str, str], tuple[str, str, str, str]] = {}
    for entry in objects:
        if not isinstance(entry, dict) or not all(
            isinstance(entry.get(k), str)
            for k in ("platform", "locator", "object", "env")
        ):
            raise HandoverError(f"invalid object entry {entry!r}")
        plat, loc, name, env = _clean_cells(
            entry["platform"], entry["locator"], entry["object"], entry["env"], False
        )
        key = (plat.lower(), loc.lower(), name.lower(), env)
        if key in listed:
            raise HandoverError(f"duplicate object in the list: {name} ({loc}, {env})")
        listed[key] = (plat, loc, name, env)
    inv = load_inventory(repo, ticket)
    rows, _ = inv.rows()
    counts = {"added": 0, "kept": 0, "removed": 0}
    deletions: list[int] = []
    seen: set[tuple[str, str, str, str]] = set()
    for idx, cells in rows:
        key = row_key(cells)
        plans = split_list(cells[5])
        if key in listed:
            seen.add(key)
            if src not in plans:
                cells[5] = join_list([*plans, src])
                inv.lines[idx] = join_row(cells)
            counts["kept"] += 1
        elif src in plans:
            plans.remove(src)
            if cells[4] == "planned" and not plans:
                deletions.append(idx)
                counts["removed"] += 1
            else:
                cells[5] = join_list(plans)
                inv.lines[idx] = join_row(cells)
    for idx in sorted(deletions, reverse=True):
        del inv.lines[idx]
    span = inv.table_span()
    assert span is not None
    new_rows = [
        join_row([p, loc, name, env, "planned", join_list([src]), "-"])
        for key, (p, loc, name, env) in listed.items()
        if key not in seen
    ]
    inv.lines[span[1] : span[1]] = new_rows
    counts["added"] = len(new_rows)
    save_inventory(repo, ticket, inv)
    return counts


COMPACT_LIMIT = 25
DEFAULT_STATE: dict[str, Any] = {
    "comment_id": "", "posted_fingerprint": "", "posted_date": "",
    "posting": {"state": "idle"}, "closed": False, "pr": "", "bast": "",
}  # fmt: skip


def load_state(repo: Path, ticket: str) -> dict[str, Any] | None:
    path = state_path(repo, ticket)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HandoverError(f"cannot read {path}: {exc}") from exc
    merged = {**DEFAULT_STATE, **data}
    merged["posting"] = data.get("posting") or {"state": "idle"}
    return merged


def save_state(repo: Path, ticket: str, state: dict[str, Any]) -> None:
    write_atomic(
        state_path(repo, ticket), json.dumps(state, indent=2, sort_keys=True) + "\n"
    )


def _state_or_default(repo: Path, ticket: str) -> dict[str, Any]:
    return load_state(repo, ticket) or {**DEFAULT_STATE, "posting": {"state": "idle"}}


def stable_lines(inv: Inventory, state: dict[str, Any], ticket: str) -> list[str]:
    """The published body without the volatile date, status and footer lines."""
    rows = sorted(
        (cells for _, cells in inv.rows()[0]),
        key=lambda c: (c[0].lower(), norm(c[1]).lower(), norm(c[2]).lower(), c[3]),
    )
    lines = [f"Handover inventory for {ticket} (edited in place)"]
    if len(rows) > COMPACT_LIMIT:
        counts: dict[str, int] = {}
        for cells in rows:
            counts[cells[0]] = counts.get(cells[0], 0) + 1
        lines += ["", f"Objects: {len(rows)} (compact)"]
        lines += [f"- {name}: {counts[name]}" for name in sorted(counts)]
    else:
        current = None
        for cells in rows:
            if cells[0] != current:
                current = cells[0]
                lines += ["", current]
            lines.append(f"- {cells[2]} | {cells[1]} | {cells[3]} | {cells[4]}")
    lines += [
        "", f"Branch: {inv.branch()}",
        f"PR: {state['pr'] or '-'}", f"BAST: {state['bast'] or '-'}",
    ]  # fmt: skip
    notes = inv.notes()
    if notes:
        lines += ["", "Notes:", *notes]
    lines += ["", f"Details: release/{ticket}/docs/HANDOVER.md"]
    return lines


def fingerprint(inv: Inventory, state: dict[str, Any], ticket: str) -> str:
    return hashlib.sha256(
        "\n".join(stable_lines(inv, state, ticket)).encode("utf-8")
    ).hexdigest()


def render(repo: Path, ticket: str, jira_status: str, date: str) -> str:
    inv = load_inventory(repo, ticket)
    state = _state_or_default(repo, ticket)
    stable = stable_lines(inv, state, ticket)
    rows = inv.rows()[0]
    planned = sum(1 for _, c in rows if c[4] == "planned")
    touched = sum(1 for _, c in rows if c[4] == "touched")
    fp = hashlib.sha256("\n".join(stable).encode("utf-8")).hexdigest()
    body = [
        stable[0], f"Updated: {date}",
        f"Status: {jira_status} | planned: {planned} | touched: {touched}",
        *stable[1:], "", f"Fingerprint: {fp[:12]}",
    ]  # fmt: skip
    return "\n".join(body) + "\n"


def fp_equal(a: str, b: str) -> bool:
    return bool(a) and bool(b) and a[:12] == b[:12]


def _has_content(inv: Inventory) -> bool:
    return bool(inv.rows()[0]) or bool(inv.notes())


def cmd_set_links(
    repo: Path, ticket: str, pr: str | None = None, bast: str | None = None
) -> None:
    state = _state_or_default(repo, ticket)
    if pr is not None:
        state["pr"] = check_value(pr, "pr", True)
    if bast is not None:
        state["bast"] = check_value(bast, "bast", True)
    save_state(repo, ticket, state)


def cmd_changed(repo: Path, ticket: str, jira_status: str | None = None) -> str:
    state = load_state(repo, ticket)
    if state is None:
        return "no-state"
    if state["posting"].get("state") == "pending":
        return "pending"
    if state["closed"]:
        if jira_status is not None and jira_status != "Done":
            state["closed"] = False
            save_state(repo, ticket, state)
        else:
            return "closed"
    inv = load_inventory(repo, ticket)
    if not state["posted_fingerprint"]:
        return "changed" if _has_content(inv) else ""
    current = fingerprint(inv, state, ticket)
    return "" if fp_equal(current, state["posted_fingerprint"]) else "changed"


def cmd_begin_post(repo: Path, ticket: str) -> None:
    state = _state_or_default(repo, ticket)
    if state["posting"].get("state") == "pending":
        raise HandoverError("a post is already pending; recover it or run abort-post")
    inv = load_inventory(repo, ticket)
    state["posting"] = {
        "state": "pending",
        "approved": fingerprint(inv, state, ticket),
        "since": dt.date.today().isoformat(),
    }
    save_state(repo, ticket, state)


def cmd_abort_post(repo: Path, ticket: str) -> None:
    state = _state_or_default(repo, ticket)
    state["posting"] = {"state": "idle"}
    save_state(repo, ticket, state)


def cmd_mark_posted(
    repo: Path, ticket: str, comment_id: str, date: str | None = None
) -> None:
    state = _state_or_default(repo, ticket)
    if state["posting"].get("state") != "pending":
        raise HandoverError("no post is pending; run begin-post first")
    state["comment_id"] = check_value(str(comment_id), "comment id", True)
    state["posted_fingerprint"] = state["posting"]["approved"]
    state["posted_date"] = date or dt.date.today().isoformat()
    state["posting"] = {"state": "idle"}
    save_state(repo, ticket, state)


def cmd_adopt(repo: Path, ticket: str, comment_id: str, fp: str) -> None:
    state = _state_or_default(repo, ticket)
    state["comment_id"] = check_value(str(comment_id), "comment id", True)
    state["posted_fingerprint"] = check_value(fp, "fingerprint", True)
    state["posting"] = {"state": "idle"}
    save_state(repo, ticket, state)


def cmd_close(repo: Path, ticket: str) -> None:
    state = _state_or_default(repo, ticket)
    if state["posting"].get("state") == "pending":
        raise HandoverError("a post is pending; recover it before closing")
    inv = load_inventory(repo, ticket)
    published = fp_equal(fingerprint(inv, state, ticket), state["posted_fingerprint"])
    if not published and _has_content(inv):
        raise HandoverError("unpublished changes remain; post them before closing")
    state["closed"] = True
    save_state(repo, ticket, state)


def cmd_reopen(repo: Path, ticket: str) -> None:
    state = _state_or_default(repo, ticket)
    state["closed"] = False
    save_state(repo, ticket, state)


CHECK_SKIP_NAMES = {"CONTEXT.md", "handover.state.json"}


def cmd_check(repo: Path, ticket: str) -> tuple[list[str], list[str]]:
    """Files outside git (or the ticket's change folders) with no Source in the inventory."""
    validate_ticket(ticket)
    sources: set[str] = set()
    for _, cells in load_inventory(repo, ticket).rows()[0]:
        sources.update(split_list(cells[6]))
    dirs = [f"release/{ticket}/{d}" for d in ("ddl", "flink", "config", "data")]
    dirs.append(f"scratch/{ticket}")
    scanned: list[str] = []
    unmatched: list[str] = []
    for d in dirs:
        base = repo / d
        if not base.is_dir():
            continue
        scanned.append(d)
        for path in sorted(base.rglob("*")):
            if not path.is_file() or path.name in CHECK_SKIP_NAMES:
                continue
            rel = path.relative_to(repo).as_posix()
            if rel.startswith(f"scratch/{ticket}/docs/"):
                continue
            if any(rel == s or rel.startswith(s + "/") for s in sources):
                continue
            unmatched.append(rel)
    return scanned, unmatched


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    def command(name: str, *, ticket: bool = True) -> argparse.ArgumentParser:
        p = sub.add_parser(name)
        p.add_argument(
            "--repo", default=None, help="repository (default: the current one)"
        )
        if ticket:
            p.add_argument("--ticket", required=True)
        return p

    p = command("init")
    p.add_argument("--branch", required=True)
    p = command("add")
    for opt in ("platform", "locator", "object", "env"):
        p.add_argument(f"--{opt}", required=True)
    p.add_argument("--state", required=True, choices=STATES)
    p.add_argument("--source", default=None)
    p.add_argument("--allow-secret-like", action="store_true")
    p = command("remove")
    for opt in ("platform", "locator", "object", "env"):
        p.add_argument(f"--{opt}", required=True)
    p = command("plan-sync")
    p.add_argument("--source", required=True)
    p.add_argument("--objects-file", required=True)
    p.add_argument("--allow-empty", action="store_true")
    p = command("note")
    p.add_argument("--text", required=True)
    p.add_argument("--allow-secret-like", action="store_true")
    p = command("set")
    p.add_argument("--branch", default=None)
    p.add_argument("--pr", default=None)
    p.add_argument("--bast", default=None)
    command("show")
    command("check")
    p = command("render")
    p.add_argument("--jira-status", required=True)
    p.add_argument("--date", required=True)
    p = command("changed")
    p.add_argument("--jira-status", default=None)
    command("begin-post")
    command("abort-post")
    p = command("mark-posted")
    p.add_argument("--comment-id", required=True)
    p.add_argument("--date", default=None)
    p = command("adopt")
    p.add_argument("--comment-id", required=True)
    p.add_argument("--fingerprint", required=True)
    command("close")
    command("reopen")
    return parser


def run(args: argparse.Namespace) -> int:
    repo = find_repo(args.repo)
    t = args.ticket
    name = args.command
    if name == "init":
        print(f"created {cmd_init(repo, t, args.branch)}")
    elif name == "add":
        print(
            cmd_add(
                repo,
                t,
                args.platform,
                args.locator,
                args.object,
                args.env,
                args.state,
                args.source,
                args.allow_secret_like,
            )  # fmt: skip
        )
    elif name == "remove":
        if cmd_remove(repo, t, args.platform, args.locator, args.object, args.env):
            print("removed")
        else:
            print("no such row")
            return 1
    elif name == "plan-sync":
        counts = cmd_plan_sync(
            repo,
            t,
            args.source,
            load_objects_file(Path(args.objects_file)),
            args.allow_empty,
        )
        print(
            f"added {counts['added']}, kept {counts['kept']}, removed {counts['removed']}"
        )
    elif name == "note":
        cmd_note(repo, t, args.text, args.allow_secret_like)
        print("noted")
    elif name == "set":
        if args.branch is not None:
            cmd_set_branch(repo, t, args.branch)
        if args.pr is not None or args.bast is not None:
            cmd_set_links(repo, t, args.pr, args.bast)
        print("set")
    elif name == "show":
        print(cmd_show(repo, t), end="")
    elif name == "check":
        scanned, unmatched = cmd_check(repo, t)
        print("scanned: " + (", ".join(scanned) if scanned else "(no folders)"))
        print(
            "\n".join(f"no inventory line: {p}" for p in unmatched)
            if unmatched
            else "all files have an inventory line"
        )
    elif name == "render":
        print(render(repo, t, args.jira_status, args.date), end="")
    elif name == "changed":
        word = cmd_changed(repo, t, args.jira_status)
        if word:
            print(word)
    elif name == "begin-post":
        cmd_begin_post(repo, t)
        print("pending")
    elif name == "abort-post":
        cmd_abort_post(repo, t)
        print("idle")
    elif name == "mark-posted":
        cmd_mark_posted(repo, t, args.comment_id, args.date)
        print("posted")
    elif name == "adopt":
        cmd_adopt(repo, t, args.comment_id, args.fingerprint)
        print("adopted")
    elif name == "close":
        cmd_close(repo, t)
        print("closed")
    elif name == "reopen":
        cmd_reopen(repo, t)
        print("reopened")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return run(args)
    except HandoverError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
