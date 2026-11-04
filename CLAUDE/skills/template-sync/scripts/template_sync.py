#!/usr/bin/env python3
"""Check whether a repo applies the standard templates, and at which version.

    template_sync.py list   [--source DIR]
    template_sync.py check  <repo> [--source DIR] [--only ID]
    template_sync.py diff   <id> <repo> [--source DIR]
    template_sync.py stamp  <id> <repo> [--source DIR]
    template_sync.py verify [--source DIR]
    template_sync.py bump   <id> [--source DIR]

The registry is `templates/manifest.json` in the template source repository
(`cr-misc-function`). Each template has an integer `version`, a `digest` of its files and
one primary file that carries a marker line (`# template: <id>@<version>`, or `//` in JSON
with comments). `check` and `diff` only read. `stamp` writes the marker line of one repo
file and nothing else. `verify` and `bump` are for the person changing a template.
Python 3.9 and newer, stdlib only.
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ENV_SOURCE = "TEMPLATE_SOURCE"
DEFAULT_SOURCE = "~/repo/cr-misc-function/cr-misc-function"
MANIFEST = "templates/manifest.json"
MARKER = re.compile(r"^\s*(?:#|//)\s*template:\s*([A-Za-z0-9_-]+)@(\d+)\s*$")
MARKER_LINES = 5  # the marker must sit in the first lines of the file
LIKELY_SAME = 0.6  # similarity above which an unmarked file is taken for an old copy
SOURCE_BRANCHES = ("dev", "master", "main")


class TemplateError(Exception):
    """A problem the user can fix; the message is printed as it is."""


def find_source(arg: str | None) -> Path:
    """Locate the template source repository (flag, then env, then the usual place)."""
    raw = arg or os.environ.get(ENV_SOURCE) or DEFAULT_SOURCE
    path = Path(raw).expanduser()
    if not (path / MANIFEST).is_file():
        raise TemplateError(
            f"no {MANIFEST} in {path}; pass --source or set {ENV_SOURCE} to the "
            "cr-misc-function checkout"
        )
    return path


def load_manifest(source: Path) -> dict[str, Any]:
    try:
        data = json.loads((source / MANIFEST).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise TemplateError(f"cannot read {MANIFEST}: {exc}") from exc
    if not isinstance(data.get("templates"), list):
        raise TemplateError(f"{MANIFEST} has no templates list")
    result: dict[str, Any] = data
    return result


def get(manifest: dict[str, Any], tid: str) -> dict[str, Any]:
    for item in manifest["templates"]:
        if item["id"] == tid:
            found: dict[str, Any] = item
            return found
    ids = ", ".join(t["id"] for t in manifest["templates"])
    raise TemplateError(f"unknown template '{tid}'; known: {ids}")


def comment_for(path: str) -> str:
    return "//" if path.endswith(".json") else "#"


def marker_line(tid: str, version: int, dest: str) -> str:
    return f"{comment_for(dest)} template: {tid}@{version}"


def split_marker(text: str) -> tuple[tuple[str, int] | None, list[str]]:
    """Return the marker (id, version) found in the first lines, and the other lines."""
    lines = text.replace("\r\n", "\n").split("\n")
    for i, line in enumerate(lines[:MARKER_LINES]):
        found = MARKER.match(line)
        if found:
            return (found.group(1), int(found.group(2))), lines[:i] + lines[i + 1 :]
    return None, lines


def digest(source: Path, template: dict[str, Any]) -> str:
    """Hash of the template's files without their marker line."""
    h = hashlib.sha256()
    for f in template["files"]:
        text = (source / f["src"]).read_text(encoding="utf-8")
        _, body = split_marker(text)
        h.update(f["src"].encode() + b"\0" + "\n".join(body).encode() + b"\0")
    return h.hexdigest()


def primary(template: dict[str, Any]) -> dict[str, Any]:
    return next(f for f in template["files"] if f.get("marker"))


def source_info(source: Path) -> list[str]:
    """Where "latest" comes from, with a warning when the checkout may not be current."""

    def git(*args: str) -> str:
        done = subprocess.run(
            ["git", "-C", str(source), *args], capture_output=True, text=True
        )
        return done.stdout.strip() if done.returncode == 0 else ""

    branch, sha = (
        git("rev-parse", "--abbrev-ref", "HEAD"),
        git("rev-parse", "--short", "HEAD"),
    )
    lines = [
        f"template source: {source} ({branch or 'not a git checkout'} {sha})".rstrip()
    ]
    if branch and branch not in SOURCE_BRANCHES:
        lines.append(
            f"warning: the source is on '{branch}', not {'/'.join(SOURCE_BRANCHES)}; "
            "its versions may not be the released ones"
        )
    if git("status", "--porcelain", "--", "templates"):
        lines.append("warning: the source has uncommitted changes under templates/")
    return lines


# ---------------------------------------------------------------- check


def compare(
    source: Path, repo: Path, template: dict[str, Any]
) -> tuple[str, list[str]]:
    """Status of one template in a repo, with detail lines.

    Statuses: current, stale, ahead, unmarked, not-applied.
    """
    tid, latest = template["id"], int(template["version"])
    main = primary(template)
    dest = repo / main["dest"]
    details: list[str] = []
    if not dest.is_file():
        return "not-applied", [f"{main['dest']} is missing"]
    text = dest.read_text(encoding="utf-8", errors="replace")
    found, body = split_marker(text)
    src_text = (source / main["src"]).read_text(encoding="utf-8")
    _, src_body = split_marker(src_text)
    if found is None:
        ratio = difflib.SequenceMatcher(None, src_body, body).ratio()
        if ratio >= LIKELY_SAME:
            status = "unmarked"
            details.append(
                f"{main['dest']} has no marker but is {ratio:.0%} like the template: "
                "an older copy; treat as stale"
            )
        else:
            status = "unmarked"
            details.append(
                f"{main['dest']} exists, has no marker and is only {ratio:.0%} like the "
                "template: a different file; decide whether to replace it"
            )
    elif found[0] != tid:
        status = "unmarked"
        details.append(f"{main['dest']} is stamped for '{found[0]}', not '{tid}'")
    elif found[1] < latest:
        status = "stale"
        details.append(f"{main['dest']} is on v{found[1]}, latest is v{latest}")
    elif found[1] > latest:
        status = "ahead"
        details.append(
            f"{main['dest']} is on v{found[1]}, newer than the source (v{latest}): "
            "update the source checkout"
        )
    else:
        status = "current"
        changed = sum(
            1
            for line in difflib.unified_diff(src_body, body, lineterm="", n=0)
            if line[:1] in "+-" and line[:3] not in ("+++", "---")
        )
        if changed:
            details.append(
                f"{main['dest']} is on v{latest}; {changed} line(s) differ "
                "(usually repo values; run diff to see)"
            )
    for f in template["files"]:
        if f is main:
            continue
        other = repo / f["dest"]
        if not other.is_file():
            status = "stale" if status == "current" else status
            details.append(f"{f['dest']} is missing")
        else:
            _, a = split_marker((source / f["src"]).read_text(encoding="utf-8"))
            _, b = split_marker(other.read_text(encoding="utf-8", errors="replace"))
            if a != b:
                if status == "current":
                    status = "stale"
                details.append(f"{f['dest']} differs from the template")
    return status, details


def cmd_list(args: argparse.Namespace) -> int:
    source = find_source(args.source)
    manifest = load_manifest(source)
    for line in source_info(source):
        print(line)
    for t in manifest["templates"]:
        print(f"{t['id']}  v{t['version']}  {t['title']}")
        print(
            f"    standard: {t.get('standard', '-')}; files: "
            + ", ".join(f["dest"] for f in t["files"])
        )
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    source = find_source(args.source)
    repo = Path(args.repo).expanduser().resolve()
    if not repo.is_dir():
        raise TemplateError(f"not a folder: {args.repo}")
    manifest = load_manifest(source)
    templates = [get(manifest, args.only)] if args.only else manifest["templates"]
    for line in source_info(source):
        print(line)
    print(f"repo: {repo}")
    bad = 0
    for t in templates:
        status, details = compare(source, repo, t)
        print(f"{status.upper():<11} {t['id']} (latest v{t['version']})")
        for d in details:
            print(f"    {d}")
        if status in ("stale", "unmarked", "ahead"):
            bad += 1
        elif status == "not-applied":
            print(f"    {t['title']}: add it only if this repo needs it")
    print(f"{bad} template(s) need attention" if bad else "nothing to update")
    return 1 if bad else 0


def cmd_diff(args: argparse.Namespace) -> int:
    source = find_source(args.source)
    repo = Path(args.repo).expanduser().resolve()
    template = get(load_manifest(source), args.id)
    for f in template["files"]:
        target = repo / f["dest"]
        _, a = split_marker((source / f["src"]).read_text(encoding="utf-8"))
        if not target.is_file():
            print(f"--- {f['dest']}: missing in the repo")
            continue
        _, b = split_marker(target.read_text(encoding="utf-8", errors="replace"))
        out = list(
            difflib.unified_diff(
                b, a, f"repo/{f['dest']}", f"template/{f['src']}", lineterm="", n=2
            )
        )
        print("\n".join(out) if out else f"--- {f['dest']}: same as the template")
    return 0


# ---------------------------------------------------------------- stamp


def cmd_stamp(args: argparse.Namespace) -> int:
    """Write the marker line of the primary file; nothing else in the file changes."""
    source = find_source(args.source)
    repo = Path(args.repo).expanduser().resolve()
    template = get(load_manifest(source), args.id)
    main = primary(template)
    target = repo / main["dest"]
    if not target.is_file():
        raise TemplateError(f"{main['dest']} does not exist in the repo")
    text = target.read_bytes().decode("utf-8")  # read_text would hide the CRLF
    crlf = "\r\n" in text
    _, rest = split_marker(text)
    line = marker_line(template["id"], int(template["version"]), main["dest"])
    new = "\n".join([line, *rest])
    target.write_text(
        new.replace("\n", "\r\n") if crlf else new, encoding="utf-8", newline=""
    )
    print(f"stamped {main['dest']} with: {line}")
    return 0


# ---------------------------------------------------------------- maintainers


def problems(source: Path, manifest: dict[str, Any]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for t in manifest["templates"]:
        tid = t["id"]
        if tid in seen:
            out.append(f"{tid}: listed twice")
        seen.add(tid)
        if sum(1 for f in t["files"] if f.get("marker")) != 1:
            out.append(f'{tid}: exactly one file must have "marker": true')
            continue
        for f in t["files"]:
            if not (source / f["src"]).is_file():
                out.append(f"{tid}: {f['src']} does not exist")
        if out and out[-1].startswith(f"{tid}: ") and "does not exist" in out[-1]:
            continue
        found, _ = split_marker(
            (source / primary(t)["src"]).read_text(encoding="utf-8")
        )
        if found != (tid, int(t["version"])):
            out.append(
                f"{tid}: the marker in {primary(t)['src']} is {found}, the manifest says v{t['version']}"
            )
        if digest(source, t) != t.get("digest"):
            out.append(
                f"{tid}: the files changed without a version bump (run: template_sync.py bump {tid})"
            )
    return out


def cmd_verify(args: argparse.Namespace) -> int:
    source = find_source(args.source)
    found = problems(source, load_manifest(source))
    for p in found:
        print(p)
    print(
        f"{len(found)} problem(s)" if found else "manifest, markers and digests agree"
    )
    return 1 if found else 0


def cmd_bump(args: argparse.Namespace) -> int:
    source = find_source(args.source)
    manifest = load_manifest(source)
    template = get(manifest, args.id)
    if digest(source, template) == template.get("digest") and not args.force:
        print("the files did not change since the last version; nothing to bump")
        return 1
    template["version"] = int(template["version"]) + 1
    main = primary(template)
    path = source / main["src"]
    _, rest = split_marker(path.read_text(encoding="utf-8"))
    line = marker_line(template["id"], template["version"], main["dest"])
    path.write_text("\n".join([line, *rest]), encoding="utf-8", newline="")
    template["digest"] = digest(source, template)
    (source / MANIFEST).write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(
        f"{args.id} is now v{template['version']}; note the change in the commit message"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="template_sync.py")
    sub = parser.add_subparsers(dest="command", required=True)

    def add(
        name: str, func: Any, help_text: str, *positional: str
    ) -> argparse.ArgumentParser:
        p = sub.add_parser(name, help=help_text)
        for pos in positional:
            p.add_argument(pos)
        p.add_argument(
            "--source", help=f"cr-misc-function checkout (or set {ENV_SOURCE})"
        )
        p.set_defaults(func=func)
        return p

    add("list", cmd_list, "list the templates and their latest versions")
    add("check", cmd_check, "compare a repo with the templates", "repo").add_argument(
        "--only", help="check one template id"
    )
    add("diff", cmd_diff, "show how a repo differs from one template", "id", "repo")
    add("stamp", cmd_stamp, "write the version marker after an update", "id", "repo")
    add("verify", cmd_verify, "(maintainers) check manifest, markers and digests")
    add(
        "bump", cmd_bump, "(maintainers) raise a template's version", "id"
    ).add_argument(
        "--force", action="store_true", help="bump even if the files did not change"
    )
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except TemplateError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
