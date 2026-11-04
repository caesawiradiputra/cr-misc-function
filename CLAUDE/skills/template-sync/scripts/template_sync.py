#!/usr/bin/env python3
"""Check whether a repo applies the standard templates and the Python layout standard.

    template_sync.py list       [--source DIR ...]
    template_sync.py check      <repo> [--source DIR ...] [--only ID]
    template_sync.py diff       <id> <repo> [--source DIR ...]
    template_sync.py stamp      <id> <repo> [--source DIR ...]
    template_sync.py deviations <repo> [--source DIR ...]
    template_sync.py accept     <id-or-rule> <repo> --reason TEXT [--source DIR ...]
    template_sync.py verify     [--source DIR ...]
    template_sync.py bump       <id> [--source DIR ...] [--force]

Registries ("sources"): each source repository holds a manifest, `templates/manifest.json`
or `docs/standards/template-manifest.json`. A `files` template has an integer `version`, a
`digest` of its files and one primary file that carries a marker line
(`# template: <id>@<version>`, `//` in JSON). A `layout` template lists paths a repo is
expected to have (or not to have), each tied to a rule id of the Python standards.

A repo records a difference it keeps on purpose in `docs/standards-deviations.md`
(`accept`); `check` then shows `DELIBERATE` instead of a problem. `check`, `diff`, `list`
and `deviations` only read. `stamp` writes one marker line; `accept` appends one bullet.
`verify` and `bump` are for the person changing a template. Python 3.9 and newer, stdlib only.
"""

from __future__ import annotations

import argparse
import datetime as dt
import difflib
import hashlib
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ENV_SOURCES = "TEMPLATE_SOURCES"  # folders separated by the OS path separator
DEFAULT_SOURCES = (
    "~/repo/cr-misc-function/cr-misc-function",
    "~/repo/cr-misc-function/da-template-python-repo",
)
MANIFESTS = ("templates/manifest.json", "docs/standards/template-manifest.json")
DEVIATIONS = "docs/standards-deviations.md"
DEVIATIONS_HEADING = "# Deviations from the standards"
MARKER = re.compile(r"^\s*(?:#|//)\s*template:\s*([A-Za-z0-9_-]+)@(\d+)\s*$")
MARKER_LINES = 5  # the marker must sit in the first lines of the file
LIKELY_SAME = 0.6  # similarity above which an unmarked file is taken for an old copy
SOURCE_BRANCHES = ("dev", "master", "main")
BULLET = re.compile(
    r"^\s*[-*]\s+`([A-Za-z0-9_-]+)`\s*[:—-]\s*(.*?)\s*\((\d{4}-\d{2}-\d{2})\)\s*$"
)
RULE_HEADING = re.compile(r"^##\s+([A-Z]+-[A-Z0-9]+-\d+)\b", re.MULTILINE)


class TemplateError(Exception):
    """A problem the user can fix; the message is printed as it is."""


@dataclass
class Source:
    path: Path
    manifest_path: Path
    manifest: dict[str, Any]


def _load(path: Path) -> Source | None:
    for rel in MANIFESTS:
        candidate = path / rel
        if candidate.is_file():
            try:
                data = json.loads(candidate.read_text(encoding="utf-8"))
            except (OSError, ValueError) as exc:
                raise TemplateError(f"cannot read {candidate}: {exc}") from exc
            if not isinstance(data.get("templates"), list):
                raise TemplateError(f"{candidate} has no templates list")
            return Source(path, candidate, data)
    return None


def find_sources(args_sources: list[str] | None) -> list[Source]:
    """Sources from the flags, then the environment, then the usual places."""
    explicit = list(args_sources or [])
    if not explicit and os.environ.get(ENV_SOURCES):
        explicit = [p for p in os.environ[ENV_SOURCES].split(os.pathsep) if p]
    found: list[Source] = []
    for raw in explicit or list(DEFAULT_SOURCES):
        path = Path(raw).expanduser()
        source = _load(path)
        if source is None:
            if explicit:
                raise TemplateError(f"no manifest ({' or '.join(MANIFESTS)}) in {path}")
            continue  # a default source that is not checked out is skipped
        found.append(source)
    if not found:
        raise TemplateError(
            f"no template source found; pass --source or set {ENV_SOURCES} to the "
            "cr-misc-function and da-template-python-repo checkouts"
        )
    seen: dict[str, Path] = {}
    for src in found:
        for t in src.manifest["templates"]:
            if t["id"] in seen:
                raise TemplateError(
                    f"template id '{t['id']}' is in both {seen[t['id']]} and {src.path}"
                )
            seen[t["id"]] = src.path
    return found


def entries(sources: list[Source]) -> list[tuple[Source, dict[str, Any]]]:
    return [(s, t) for s in sources for t in s.manifest["templates"]]


def get(sources: list[Source], tid: str) -> tuple[Source, dict[str, Any]]:
    for source, template in entries(sources):
        if template["id"] == tid:
            return source, template
    ids = ", ".join(t["id"] for _, t in entries(sources))
    raise TemplateError(f"unknown template '{tid}'; known: {ids}")


def kind(template: dict[str, Any]) -> str:
    return str(template.get("kind", "files"))


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


def digest(source: Source, template: dict[str, Any]) -> str:
    """Hash of the template's files (without the marker line) or of its layout list."""
    h = hashlib.sha256()
    if kind(template) == "layout":
        h.update(json.dumps(template["expect"], sort_keys=True).encode())
        return h.hexdigest()
    for f in template["files"]:
        text = (source.path / f["src"]).read_text(encoding="utf-8")
        _, body = split_marker(text)
        h.update(f["src"].encode() + b"\0" + "\n".join(body).encode() + b"\0")
    return h.hexdigest()


def primary(template: dict[str, Any]) -> dict[str, Any]:
    return next(f for f in template["files"] if f.get("marker"))


def source_info(source: Source) -> list[str]:
    """Where "latest" comes from, with a warning when the checkout may not be current."""

    def git(*args: str) -> str:
        done = subprocess.run(
            ["git", "-C", str(source.path), *args], capture_output=True, text=True
        )
        return done.stdout.strip() if done.returncode == 0 else ""

    branch = git("rev-parse", "--abbrev-ref", "HEAD")
    sha = git("rev-parse", "--short", "HEAD")
    lines = [
        f"template source: {source.path} ({branch or 'not a git checkout'} {sha})".rstrip()
    ]
    if branch and branch not in SOURCE_BRANCHES:
        lines.append(
            f"warning: this source is on '{branch}', not {'/'.join(SOURCE_BRANCHES)}; "
            "its versions may not be the released ones"
        )
    if git("status", "--porcelain"):
        lines.append("warning: this source has uncommitted changes")
    return lines


# ---------------------------------------------------------------- deviations


def read_deviations(repo: Path) -> tuple[dict[str, tuple[str, str]], list[str]]:
    """Deviations a repo keeps on purpose: id -> (reason, date), and the invalid lines."""
    path = repo / DEVIATIONS
    found: dict[str, tuple[str, str]] = {}
    invalid: list[str] = []
    if not path.is_file():
        return found, invalid
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not re.match(r"^\s*[-*]\s+`", line):
            continue
        m = BULLET.match(line)
        if m and m.group(2).strip():
            found[m.group(1)] = (m.group(2).strip(), m.group(3))
        else:
            invalid.append(
                f"{DEVIATIONS}:{number} needs the form - `ID`: reason (YYYY-MM-DD)"
            )
    return found, invalid


def known_ids(sources: list[Source]) -> set[str]:
    """Template ids and the rule ids found in the sources' standards."""
    ids = {t["id"] for _, t in entries(sources)}
    for source in sources:
        standards = source.path / "docs/standards"
        if standards.is_dir():
            for md in standards.rglob("*.md"):
                ids.update(RULE_HEADING.findall(md.read_text(encoding="utf-8")))
    return ids


# ---------------------------------------------------------------- compare


def compare(
    source: Source, repo: Path, template: dict[str, Any]
) -> tuple[str, list[str]]:
    """Status of one `files` template in a repo, with detail lines.

    Statuses: current, stale, ahead, unmarked, not-applied.
    """
    tid, latest = template["id"], int(template["version"])
    main = primary(template)
    dest = repo / main["dest"]
    details: list[str] = []
    if not dest.is_file():
        return "not-applied", [f"{main['dest']} is missing"]
    text = dest.read_bytes().decode("utf-8", errors="replace")
    found, body = split_marker(text)
    src_text = (source.path / main["src"]).read_text(encoding="utf-8")
    _, src_body = split_marker(src_text)
    if found is None:
        ratio = difflib.SequenceMatcher(None, src_body, body).ratio()
        status = "unmarked"
        if ratio >= LIKELY_SAME:
            details.append(
                f"{main['dest']} has no marker but is {ratio:.0%} like the template: "
                "an older copy; treat as stale"
            )
        else:
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
            _, a = split_marker((source.path / f["src"]).read_text(encoding="utf-8"))
            _, b = split_marker(other.read_text(encoding="utf-8", errors="replace"))
            if a != b:
                if status == "current":
                    status = "stale"
                details.append(f"{f['dest']} differs from the template")
    return status, details


def compare_layout(
    repo: Path, template: dict[str, Any], deviations: dict[str, tuple[str, str]]
) -> list[tuple[str, str]]:
    """Layout results as (state, line): state is ok, drift or deliberate."""
    out: list[tuple[str, str]] = []
    for item in template["expect"]:
        pattern, rule = item["path"], item.get("rule", "")
        matches = [p for p in repo.glob(pattern.rstrip("/")) if p.exists()]
        absent = bool(item.get("absent"))
        good = not matches if absent else bool(matches)
        if good:
            out.append(("ok", pattern))
            continue
        problem = f"{pattern} exists" if absent else f"{pattern} is missing"
        why = item.get("note", "")
        line = f"{problem} ({rule}{': ' + why if why else ''})"
        if rule in deviations:
            out.append(("deliberate", f"{line}; on purpose: {deviations[rule][0]}"))
        else:
            out.append(("drift", line))
    return out


def cmd_list(args: argparse.Namespace) -> int:
    sources = find_sources(args.source)
    for source in sources:
        for line in source_info(source):
            print(line)
    for _, t in entries(sources):
        files = (
            ", ".join(i["path"] for i in t["expect"])
            if kind(t) == "layout"
            else ", ".join(f["dest"] for f in t["files"])
        )
        print(f"{t['id']}  v{t['version']}  [{kind(t)}]  {t['title']}")
        print(f"    standard: {t.get('standard', '-')}; {files}")
    return 0


def _repo(arg: str) -> Path:
    repo = Path(arg).expanduser().resolve()
    if not repo.is_dir():
        raise TemplateError(f"not a folder: {arg}")
    return repo


def cmd_check(args: argparse.Namespace) -> int:
    sources = find_sources(args.source)
    repo = _repo(args.repo)
    chosen = [get(sources, args.only)] if args.only else entries(sources)
    for source in sources:
        for line in source_info(source):
            print(line)
    print(f"repo: {repo}")
    deviations, invalid = read_deviations(repo)
    bad = 0
    for source, t in chosen:
        if kind(t) == "layout":
            results = compare_layout(repo, t, deviations)
            drift = [r for r in results if r[0] == "drift"]
            label = "DRIFT" if drift else "OK"
            if not drift and any(r[0] == "deliberate" for r in results):
                label = "DELIBERATE"
            print(
                f"{label:<11} {t['id']} (latest v{t['version']}, {len(results)} checks)"
            )
            for state, line in results:
                if state != "ok":
                    print(f"    {state.upper()}: {line}")
            bad += 1 if drift else 0
            continue
        status, details = compare(source, repo, t)
        label = status.upper()
        if status in ("stale", "unmarked", "ahead") and t["id"] in deviations:
            label = "DELIBERATE"
            details.append(
                f"on purpose: {deviations[t['id']][0]} ({deviations[t['id']][1]})"
            )
        print(f"{label:<11} {t['id']} (latest v{t['version']})")
        for d in details:
            print(f"    {d}")
        if label in ("STALE", "UNMARKED", "AHEAD"):
            bad += 1
        elif status == "not-applied":
            print(f"    {t['title']}: add it only if this repo needs it")
    for line in invalid:
        print(f"INVALID     {line}")
    if deviations:
        known = known_ids(sources)
        for did in deviations:
            if did not in known:
                print(
                    f"UNKNOWN     deviation `{did}` is not a template id or a rule id"
                )
    print(f"{bad} item(s) need attention" if bad else "nothing to update")
    return 1 if bad else 0


def cmd_diff(args: argparse.Namespace) -> int:
    source, template = get(find_sources(args.source), args.id)
    if kind(template) == "layout":
        raise TemplateError("a layout template has no files to diff; use check")
    repo = _repo(args.repo)
    for f in template["files"]:
        target = repo / f["dest"]
        _, a = split_marker((source.path / f["src"]).read_text(encoding="utf-8"))
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


# ---------------------------------------------------------------- stamp, accept


def cmd_stamp(args: argparse.Namespace) -> int:
    """Write the marker line of the primary file; nothing else in the file changes."""
    _, template = get(find_sources(args.source), args.id)
    if kind(template) == "layout":
        raise TemplateError("a layout template has no marker to stamp")
    repo = _repo(args.repo)
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


def cmd_accept(args: argparse.Namespace) -> int:
    """Record a deviation the user decided to keep. Only on the user's say-so."""
    sources = find_sources(args.source)
    repo = _repo(args.repo)
    reason = " ".join(args.reason.split())
    if not reason:
        raise TemplateError("--reason is required")
    if args.id not in known_ids(sources):
        raise TemplateError(f"'{args.id}' is not a template id or a rule id")
    existing, _ = read_deviations(repo)
    if args.id in existing:
        print(
            f"already recorded: `{args.id}`: {existing[args.id][0]} ({existing[args.id][1]})"
        )
        return 1
    path = repo / DEVIATIONS
    today = dt.date.today().isoformat()
    bullet = f"- `{args.id}`: {reason} ({today})\n"
    if path.is_file():
        text = path.read_bytes().decode("utf-8")
        if text and not text.endswith("\n"):
            text += "\n"
        path.write_bytes((text + bullet).encode("utf-8"))
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        intro = (
            f"{DEVIATIONS_HEADING}\n\n"
            "Differences from the templates and Python standards that this repo keeps on\n"
            "purpose. One bullet per item: the template id or rule id, the reason, the date.\n\n"
        )
        path.write_text(intro + bullet, encoding="utf-8")
    print(f"recorded in {DEVIATIONS}: {bullet.strip()}")
    return 0


def cmd_deviations(args: argparse.Namespace) -> int:
    sources = find_sources(args.source)
    repo = _repo(args.repo)
    found, invalid = read_deviations(repo)
    known = known_ids(sources)
    for did, (reason, date) in found.items():
        flag = "" if did in known else "  [unknown id]"
        print(f"{did}: {reason} ({date}){flag}")
    for line in invalid:
        print(f"INVALID {line}")
    if not found and not invalid:
        print(f"no deviations recorded ({DEVIATIONS})")
    return 1 if invalid else 0


# ---------------------------------------------------------------- maintainers


def problems(sources: list[Source]) -> list[str]:
    out: list[str] = []
    for source, t in entries(sources):
        tid = t["id"]
        if kind(t) == "files":
            if sum(1 for f in t["files"] if f.get("marker")) != 1:
                out.append(f'{tid}: exactly one file must have "marker": true')
                continue
            missing = [
                f["src"] for f in t["files"] if not (source.path / f["src"]).is_file()
            ]
            if missing:
                out.extend(f"{tid}: {m} does not exist" for m in missing)
                continue
            found, _ = split_marker(
                (source.path / primary(t)["src"]).read_text(encoding="utf-8")
            )
            if found != (tid, int(t["version"])):
                out.append(
                    f"{tid}: the marker in {primary(t)['src']} is {found}, "
                    f"the manifest says v{t['version']}"
                )
        if digest(source, t) != t.get("digest"):
            out.append(
                f"{tid}: it changed without a version bump (run: template_sync.py bump {tid})"
            )
    return out


def cmd_verify(args: argparse.Namespace) -> int:
    found = problems(find_sources(args.source))
    for p in found:
        print(p)
    print(
        f"{len(found)} problem(s)" if found else "manifest, markers and digests agree"
    )
    return 1 if found else 0


def cmd_bump(args: argparse.Namespace) -> int:
    source, template = get(find_sources(args.source), args.id)
    if digest(source, template) == template.get("digest") and not args.force:
        print("it did not change since the last version; nothing to bump")
        return 1
    template["version"] = int(template["version"]) + 1
    if kind(template) == "files":
        main = primary(template)
        path = source.path / main["src"]
        _, rest = split_marker(path.read_bytes().decode("utf-8"))
        line = marker_line(template["id"], template["version"], main["dest"])
        path.write_bytes("\n".join([line, *rest]).encode("utf-8"))
    template["digest"] = digest(source, template)
    source.manifest_path.write_text(
        json.dumps(source.manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
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
            "--source",
            action="append",
            help=f"a template source checkout; repeat for several (or set {ENV_SOURCES})",
        )
        p.set_defaults(func=func)
        return p

    add("list", cmd_list, "list the templates and their latest versions")
    add("check", cmd_check, "compare a repo with the templates", "repo").add_argument(
        "--only", help="check one template id"
    )
    add("diff", cmd_diff, "show how a repo differs from one template", "id", "repo")
    add("stamp", cmd_stamp, "write the version marker after an update", "id", "repo")
    add(
        "deviations",
        cmd_deviations,
        "list and validate a repo's recorded deviations",
        "repo",
    )
    add(
        "accept",
        cmd_accept,
        "record a deviation the repo keeps on purpose",
        "id",
        "repo",
    ).add_argument("--reason", required=True)
    add("verify", cmd_verify, "(maintainers) check manifests, markers and digests")
    add(
        "bump", cmd_bump, "(maintainers) raise a template's version", "id"
    ).add_argument("--force", action="store_true", help="bump even if nothing changed")
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except TemplateError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
