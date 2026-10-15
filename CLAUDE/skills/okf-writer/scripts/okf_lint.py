#!/usr/bin/env python3
"""Lint an Open Knowledge Format (OKF) bundle against the v0.2 rules.

Usage:
    python3 okf_lint.py <bundle_dir> [--strict]

Errors (exit 1): a concept file without parseable frontmatter or a non-empty
`type`, an invalid `status`, a malformed timestamp, `generated` or `verified`
entries without `by`, a reserved file (`index.md`, `log.md`) used as a concept,
or `log.md` dates that are not newest first.

Warnings (exit 0, or 1 with --strict): broken links, concepts missing from every
`index.md`, missing title, description or tags, a `stale_after` in the past, and
footnotes that match no `sources[].id`.

Stdlib only; runs on Python 3.9 and newer. It reads a small YAML subset
(scalars, inline lists, nested maps, block lists) which covers OKF frontmatter.
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from pathlib import Path
from typing import Any

RESERVED = {"index.md", "log.md"}
STATUSES = {"draft", "stable", "deprecated"}
TIMESTAMP = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2}(\.\d+)?)?(Z|[+-]\d{2}:\d{2})$"
)
LINK = re.compile(r"(?<!\!)\[[^\]]*\]\(([^)\s]+)\)")
FOOTNOTE_REF = re.compile(r"\[\^([^\]\s]+)\](?!:)")
FOOTNOTE_DEF = re.compile(r"^\[\^([^\]\s]+)\]:", re.M)
DATE_HEADING = re.compile(r"^##\s+(\d{4}-\d{2}-\d{2})\s*$", re.M)


class Frontmatter(Exception):
    """The frontmatter block is missing or cannot be parsed."""


def scalar(text: str) -> Any:
    text = text.strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "'\"":
        return text[1:-1]
    if text.startswith("[") and text.endswith("]"):
        inner = text[1:-1].strip()
        return [scalar(p) for p in inner.split(",")] if inner else []
    if text in ("~", "null"):
        return None
    return text


def parse_block(lines: list[str], start: int, indent: int) -> tuple[Any, int]:
    """Parse a map or a list whose items sit at `indent`; return (value, next index)."""
    first = lines[start]
    if first.strip().startswith("- "):
        items: list[Any] = []
        i = start
        while i < len(lines) and lines[i].startswith(" " * indent + "- "):
            body = lines[i][indent + 2 :]
            if re.match(r"^[\w.\-]+\s*:", body):  # a map item: "- key: value"
                sub = [" " * (indent + 2) + body]
                i += 1
                while i < len(lines) and (
                    lines[i].startswith(" " * (indent + 2)) and lines[i].strip()
                ):
                    sub.append(lines[i])
                    i += 1
                value, _ = parse_block(sub, 0, indent + 2)
                items.append(value)
            else:
                items.append(scalar(body))
                i += 1
        return items, i
    result: dict[str, Any] = {}
    i = start
    while i < len(lines):
        line = lines[i]
        if not line.strip() or line.lstrip().startswith("#"):
            i += 1
            continue
        cur = len(line) - len(line.lstrip(" "))
        if cur < indent:
            break
        if cur > indent:
            raise Frontmatter(f"unexpected indentation: {line.strip()!r}")
        m = re.match(r"^([\w.\-]+)\s*:\s*(.*)$", line.strip())
        if not m:
            raise Frontmatter(f"cannot parse line: {line.strip()!r}")
        key, rest = m.group(1), m.group(2)
        i += 1
        if rest:
            result[key] = scalar(rest)
        elif (
            i < len(lines)
            and lines[i].strip()
            and (
                len(lines[i]) - len(lines[i].lstrip(" ")) > indent
                or lines[i].lstrip().startswith("- ")
            )
        ):
            child_indent = len(lines[i]) - len(lines[i].lstrip(" "))
            result[key], i = parse_block(lines, i, child_indent)
        else:
            result[key] = None
    return result, i


def split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise Frontmatter("no frontmatter block at the top of the file")
    for end in range(1, len(lines)):
        if lines[end].strip() == "---":
            data, _ = parse_block(lines[1:end], 0, 0) if end > 1 else ({}, 0)
            return (data if isinstance(data, dict) else {}), "\n".join(lines[end + 1 :])
    raise Frontmatter("frontmatter block is not closed with ---")


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, path: Path, msg: str) -> None:
        self.errors.append(f"ERROR {path}: {msg}")

    def warn(self, path: Path, msg: str) -> None:
        self.warnings.append(f"WARN  {path}: {msg}")


def check_timestamp(rep: Report, rel: Path, label: str, value: Any) -> None:
    if not isinstance(value, str) or not TIMESTAMP.match(value):
        rep.error(rel, f"{label} must be ISO 8601 with a UTC offset (got {value!r})")


def check_concept(rep: Report, rel: Path, meta: dict[str, Any], body: str) -> None:
    if not isinstance(meta.get("type"), str) or not meta["type"].strip():
        rep.error(rel, "`type` is required and must be a non-empty string")
    for field in ("title", "description"):
        if not meta.get(field):
            rep.warn(rel, f"`{field}` is recommended")
    if not meta.get("tags"):
        rep.warn(rel, "`tags` is recommended")
    status = meta.get("status")
    if status is not None and status not in STATUSES:
        rep.error(rel, f"`status` must be one of {sorted(STATUSES)} (got {status!r})")
    gen = meta.get("generated")
    if gen is not None:
        if not isinstance(gen, dict) or not gen.get("by"):
            rep.error(rel, "`generated` needs a `by` actor")
        elif gen.get("at") is not None:
            check_timestamp(rep, rel, "generated.at", gen["at"])
    for n, entry in enumerate(as_list(meta.get("verified"))):
        if not isinstance(entry, dict) or not entry.get("by"):
            rep.error(rel, f"verified[{n}] needs a `by` actor")
        elif entry.get("at") is not None:
            check_timestamp(rep, rel, f"verified[{n}].at", entry["at"])
    stale = meta.get("stale_after")
    if stale is not None:
        check_timestamp(rep, rel, "stale_after", stale)
        if isinstance(stale, str) and TIMESTAMP.match(stale):
            parsed = dt.datetime.fromisoformat(stale.replace("Z", "+00:00"))
            if parsed.tzinfo and parsed <= dt.datetime.now(dt.timezone.utc):  # noqa: UP017 (dt.UTC needs Python 3.11, this runs on 3.9)
                rep.warn(rel, f"stale since {stale}")
    ids = {
        s.get("id")
        for s in as_list(meta.get("sources"))
        if isinstance(s, dict) and s.get("id")
    }
    for ref in sorted(set(FOOTNOTE_REF.findall(body))):
        if ref not in ids and ref not in FOOTNOTE_DEF.findall(body):
            rep.warn(rel, f"footnote [^{ref}] matches no `sources[].id` or definition")


def check_log(rep: Report, rel: Path, text: str) -> None:
    dates = DATE_HEADING.findall(text)
    if dates != sorted(dates, reverse=True):
        rep.error(rel, "log.md date headings must be newest first")


def resolve_link(root: Path, source: Path, target: str) -> Path | None:
    target = target.split("#", 1)[0]
    if not target or re.match(r"^[a-z][a-z0-9+.\-]*:", target):
        return None
    if not target.endswith(".md"):
        return None
    base = root if target.startswith("/") else source.parent
    return (base / target.lstrip("/")).resolve()


def lint(root: Path) -> Report:
    rep = Report()
    root = root.resolve()
    files = sorted(p for p in root.rglob("*.md") if ".git" not in p.parts)
    concepts: dict[Path, dict[str, Any]] = {}
    linked_from_index: set[Path] = set()
    for path in files:
        rel = path.relative_to(root)
        text = path.read_text(encoding="utf-8")
        if path.name in RESERVED:
            if path.name == "log.md":
                check_log(rep, rel, text)
            if text.startswith("---"):
                try:
                    meta, _ = split_frontmatter(text)
                except Frontmatter as exc:
                    rep.error(rel, str(exc))
                    meta = {}
                extra = set(meta) - {"okf_version"}
                if extra or (path.name == "log.md" and meta):
                    rep.error(
                        rel,
                        f"reserved file must not carry concept keys: {sorted(extra)}",
                    )
        else:
            try:
                meta, body = split_frontmatter(text)
            except Frontmatter as exc:
                rep.error(rel, str(exc))
                continue
            concepts[path.resolve()] = meta
            check_concept(rep, rel, meta, body)
        for target in LINK.findall(text):
            resolved = resolve_link(root, path, target)
            if resolved is None:
                continue
            if not resolved.exists():
                rep.warn(rel, f"broken link: {target}")
            elif path.name == "index.md":
                linked_from_index.add(resolved)
    for path in concepts:
        if path not in linked_from_index:
            rep.warn(path.relative_to(root), "not linked from any index.md")
    if not concepts and not rep.errors:
        rep.warn(Path("."), "no concept files found")
    return rep


def trust_summary(root: Path) -> str:
    counts = {"unverified": 0, "machine-confirmed": 0, "human-reviewed": 0}
    for path in root.rglob("*.md"):
        if path.name in RESERVED:
            continue
        try:
            meta, _ = split_frontmatter(path.read_text(encoding="utf-8"))
        except Frontmatter:
            continue
        actors = [
            e.get("by", "")
            for e in as_list(meta.get("verified"))
            if isinstance(e, dict)
        ]
        if not actors:
            counts["unverified"] += 1
        elif any(str(a).startswith("human:") for a in actors):
            counts["human-reviewed"] += 1
        else:
            counts["machine-confirmed"] += 1
    return ", ".join(f"{k}: {v}" for k, v in counts.items())


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    ap.add_argument("bundle", type=Path)
    ap.add_argument("--strict", action="store_true", help="treat warnings as errors")
    args = ap.parse_args(argv)
    if not args.bundle.is_dir():
        print(f"error: {args.bundle} is not a directory", file=sys.stderr)
        return 2
    rep = lint(args.bundle)
    for line in rep.errors + rep.warnings:
        print(line)
    print(
        f"{len(rep.errors)} error(s), {len(rep.warnings)} warning(s); "
        f"trust: {trust_summary(args.bundle.resolve())}"
    )
    return 1 if rep.errors or (args.strict and rep.warnings) else 0


if __name__ == "__main__":
    sys.exit(main())
