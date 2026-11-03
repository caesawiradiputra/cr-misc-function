#!/usr/bin/env python3
"""Command line for the bruno-collection skill.

    bruno_collection.py discover <repo>
    bruno_collection.py generate <repo> [--out ROOT] [--name NAME]

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

from bruno_discover import discover  # noqa: E402
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


def cmd_generate(args: argparse.Namespace) -> int:
    repo = _repo(args.repo)
    if repo is None:
        print(f"not a folder: {args.repo}", file=sys.stderr)
        return 2
    root = args.out or os.environ.get(ENV_OUT)
    if not root:
        print(
            f"give --out or set {ENV_OUT}; the output folder is not guessed",
            file=sys.stderr,
        )
        return 2
    name = args.name or repo.name
    result = discover(repo)
    rendered = render_collection(result, name, local_base_url(repo))
    out_dir = Path(root).expanduser() / collection_dir_name(name)
    report = write_collection(rendered.files, out_dir)
    print(f"collection folder: {out_dir}")
    if report.refused:
        print(f"refused: {report.refused}")
        return 1
    print(
        f"written: {len(report.written)} file(s); kept as they were: {len(report.skipped_existing)}"
    )
    for line in rendered.report_lines():
        print(line)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="bruno_collection.py")
    sub = parser.add_subparsers(dest="command", required=True)
    d = sub.add_parser("discover", help="list the endpoints found in a repo")
    d.add_argument("repo")
    d.set_defaults(func=cmd_discover)
    g = sub.add_parser("generate", help="write a new collection")
    g.add_argument("repo")
    g.add_argument("--out", help="folder that holds the collections")
    g.add_argument("--name", help="collection name (default: the repo folder name)")
    g.set_defaults(func=cmd_generate)
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
