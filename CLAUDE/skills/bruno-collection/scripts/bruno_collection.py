#!/usr/bin/env python3
"""Command line for the bruno-collection skill.

    bruno_collection.py discover <repo>
    bruno_collection.py generate <repo> [--out ROOT] [--name NAME] [--model M] [--reason R]
    bruno_collection.py add-external <repo> --title T [--method M] [--out ROOT] [--name NAME]
    bruno_collection.py scan <folder>
    bruno_collection.py sync <repo> [--out ROOT] [--name NAME] [--model M] [--reason R]

`discover` only reads and reports. `generate` writes a new collection into
`<ROOT>/<name>/` and never overwrites. The output root comes from `--out` or the
`BRUNO_COLLECTIONS_DIR` environment variable; it is not guessed.
Python 3.9 and newer, stdlib only.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import bruno_scan  # noqa: E402
from bruno_discover import discover  # noqa: E402
from bruno_docs import (
    METHODS,
    DocsError,
    docs_files,
    external_files,
    external_paths,
    lint_summary,
    log_external,
    read_docs,
    sync_docs,
    user_owned,  # noqa: E402
)
from bruno_launch import local_base_url  # noqa: E402
from bruno_render import (  # noqa: E402
    collection_dir_name,
    render_collection,
    write_collection,
)

ENV_OUT = "BRUNO_COLLECTIONS_DIR"


def _repo(arg: str) -> Path | None:
    path = Path(arg).expanduser()
    return path.resolve() if path.is_dir() else None


def cmd_discover(args: argparse.Namespace) -> int:
    repo = _repo(args.repo)
    if repo is None:
        print(f"not a folder: {args.repo}", file=sys.stderr)
        return 2
    result = discover(repo)
    for line in result.outcome_lines():
        print(line)
    for ep in result.endpoints:
        print(f"{ep.method.upper()} {ep.path}  {ep.source.file}:{ep.source.line}")
    return 0


def _common(args: argparse.Namespace) -> tuple[Path, str, Path] | None:
    repo = _repo(args.repo)
    if repo is None:
        print(f"not a folder: {args.repo}", file=sys.stderr)
        return None
    root = args.out or os.environ.get(ENV_OUT)
    if not root:
        print(
            f"give --out or set {ENV_OUT}; the output folder is not guessed",
            file=sys.stderr,
        )
        return None
    name = args.name or repo.name
    return repo, name, Path(root).expanduser() / collection_dir_name(name)


def _finish(out_dir: Path) -> None:
    print(lint_summary(out_dir))
    print(scan_summary(out_dir))


def scan_summary(out_dir: Path) -> str:
    return bruno_scan.summary(out_dir)


def cmd_scan(args: argparse.Namespace) -> int:
    """Read-only; prints findings as kind and length only. No verbose mode."""
    folder = Path(args.folder).expanduser()
    if not folder.is_dir():
        print("scan error: folder not found")
        return 2
    try:
        report = bruno_scan.scan(folder)
    except Exception:  # noqa: BLE001 - only a generic class and step may leave
        print("scan error: step scan; the result is not clean")
        return 3
    for line in report.lines:
        print(line.encode("utf-8", "backslashreplace").decode("utf-8"))
    return report.exit_code


def cmd_generate(args: argparse.Namespace) -> int:
    common = _common(args)
    if common is None:
        return 2
    repo, name, out_dir = common
    print(f"collection folder: {out_dir}")
    if (out_dir / "docs").is_dir():
        print("refused: this collection already exists; use sync to add new endpoints")
        return 1
    rendered = render_collection(discover(repo), name, local_base_url(repo))
    files = dict(rendered.files)
    files.update(docs_files(rendered, name, args.model, args.reason))
    report = write_collection(files, out_dir)
    if report.refused:
        print(f"refused: {report.refused}")
        return 1
    print(f"written: {len(report.written)} file(s)")
    for line in rendered.report_lines():
        print(line)
    _finish(out_dir)
    return 0


def cmd_sync(args: argparse.Namespace) -> int:
    common = _common(args)
    if common is None:
        return 2
    repo, name, out_dir = common
    print(f"collection folder: {out_dir}")
    try:
        existing = read_docs(out_dir)
    except DocsError as exc:
        print(f"refused: {exc}; nothing was written")
        return 1
    # A collection made before the shared helpers has no `globalThis.__lib` definition in
    # its collection script, so new random requests keep their helpers inline.
    try:
        root_text = (out_dir / "opencollection.yml").read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        root_text = ""
    rendered = render_collection(
        discover(repo),
        name,
        local_base_url(repo),
        existing,
        central_helpers="globalThis.__lib" in root_text,
    )
    report = write_collection(rendered.files, out_dir)
    if report.refused:
        print(f"refused: {report.refused}")
        return 1
    docs = sync_docs(rendered, out_dir, args.model, args.reason)
    print(
        f"written: {len(report.written)} request/collection file(s), "
        f"{len(docs)} concept(s); {len(report.skipped_existing)} existing file(s) kept as they were"
    )
    for line in rendered.report_lines():
        print(line)
    for rel in user_owned(out_dir, read_docs(out_dir)):
        print(f"user-owned, kept as it is: {rel}")
    _finish(out_dir)
    return 0


def cmd_add_external(args: argparse.Namespace) -> int:
    common = _common(args)
    if common is None:
        return 2
    _repo_path, _name, out_dir = common
    if str(args.method).upper() not in METHODS:
        print(f"refused: the method must be one of {', '.join(METHODS)}")
        return 2
    try:
        existing = read_docs(out_dir)
    except DocsError as exc:
        print(f"refused: {exc}; nothing was written")
        return 1
    request_path, concept_path, _slug = external_paths(args.title)
    taken = {p.casefold() for p in existing.files}
    if request_path.casefold() in taken or concept_path.casefold() in taken:
        print("refused: it already exists; nothing was changed")
        return 1
    files, ext_slug, request_path = external_files(
        args.title, args.method, args.model, args.reason
    )
    report = write_collection(files, out_dir)
    if report.refused:
        print(f"refused: {report.refused}")
        return 1
    log_external(out_dir, Path(request_path).stem, ext_slug, args.reason)
    print(f"written: {', '.join(report.written)}")
    print(lint_summary(out_dir))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="bruno_collection.py")
    sub = parser.add_subparsers(dest="command", required=True)
    d = sub.add_parser("discover", help="list the endpoints found in a repo")
    d.add_argument("repo")
    d.set_defaults(func=cmd_discover)
    for cmd, func, text in (
        ("generate", cmd_generate, "write a new collection"),
        ("sync", cmd_sync, "add new endpoints to an existing collection"),
    ):
        g = sub.add_parser(cmd, help=text)
        g.add_argument("repo")
        g.add_argument("--out", help="folder that holds the collections")
        g.add_argument("--name", help="collection name (default: the repo folder name)")
        g.add_argument(
            "--model",
            default=os.environ.get("CLAUDE_MODEL", "claude-code"),
            help="written to the docs as generated.by",
        )
        g.add_argument(
            "--reason", default="new endpoint found by the tool", help="log reason"
        )
        g.set_defaults(func=func)
    sc = sub.add_parser("scan", help="read-only scan for plain-text secrets")
    sc.add_argument("folder")
    sc.set_defaults(func=cmd_scan)
    e = sub.add_parser(
        "add-external", help="add a placeholder for a request not in the code"
    )
    e.add_argument("repo")
    e.add_argument("--title", required=True)
    e.add_argument("--method", default="GET")
    e.add_argument("--out", help="folder that holds the collections")
    e.add_argument("--name", help="collection name (default: the repo folder name)")
    e.add_argument("--model", default=os.environ.get("CLAUDE_MODEL", "claude-code"))
    e.add_argument("--reason", default="the user asked for an external request")
    e.set_defaults(func=cmd_add_external)
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
