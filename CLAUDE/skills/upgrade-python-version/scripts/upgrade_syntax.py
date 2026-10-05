#!/usr/bin/env python3
"""Apply syntax-only modernization for a target Python version via ruff's UP rules.

Runs ruff's pyupgrade rule family (UP) in isolated mode (ignores the project's
own ruff config, so only these rules run), pinned to the target version, and
applies SAFE fixes only. Rules that are not pure syntax — ones that change
runtime behavior, delete code branches, or restructure definitions — are
excluded and only reported, never auto-applied.

Usage:
    python upgrade_syntax.py --target 3.11 [--path .] [--dry-run]
        [--include-string-format] [--runtime-annotation-files GLOB ...]

Prints a Markdown summary (per-rule counts applied / left for review) to stdout.
Exit code 0 on success, 2 if ruff is unavailable or fails.
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import shutil
import subprocess
import sys
from collections import Counter

## Never auto-applied: not behavior-/structure-preserving in general.
EXCLUDED_RULES = {
    "UP013": "TypedDict functional -> class syntax (restructures a definition)",
    "UP014": "NamedTuple functional -> class syntax (restructures a definition)",
    "UP028": "for-yield loop -> `yield from` (differs for send()/throw())",
    "UP036": "outdated sys.version_info blocks (deletes code branches)",
    "UP038": "isinstance tuple -> X | Y (deprecated rule, slower at runtime)",
    "UP040": "PEP 695 `type` alias (creates TypeAliasType, changes runtime object)",
    "UP042": "(str, Enum) -> StrEnum (changes str()/format() output)",
    "UP046": "PEP 695 generic class syntax (changes runtime objects)",
    "UP047": "PEP 695 generic function syntax (changes runtime objects)",
    "UP049": "private PEP 695 type parameter rename",
}
## Opt-in: behavior-preserving but rewrite many lines of string formatting.
STRING_FORMAT_RULES = {
    "UP030": "implicit positional indexes in str.format",
    "UP031": "printf-style % formatting -> str.format / f-string",
    "UP032": "str.format -> f-string",
}
## Rewrite annotations that frameworks evaluate at runtime (pydantic, FastAPI,
## dataclasses + get_type_hints, typer...). Skippable per file when the pinned
## framework version predates PEP 585/604 support.
RUNTIME_ANNOTATION_RULES = ["UP006", "UP007", "UP037", "UP045"]
DEFAULT_EXCLUDES = ["legacy", ".venv", "venv", "build", "dist", "node_modules"]


def ruff_cmd() -> list[str]:
    if shutil.which("ruff"):
        return ["ruff"]
    if shutil.which("uvx"):
        return ["uvx", "--quiet", "ruff"]
    sys.exit("ruff not found: install uv (for uvx) or ruff")


def run_ruff(base: list[str], extra: list[str]) -> list[dict]:
    proc = subprocess.run(
        base + extra + ["--output-format", "json", "--exit-zero"],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        sys.stderr.write(proc.stderr)
        sys.exit(2)
    return json.loads(proc.stdout or "[]")


def _typing_usage(tree: ast.AST) -> tuple[list[ast.ImportFrom], set[str]]:
    imports = [n for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)
               and n.module in ("typing", "typing_extensions") and n.col_offset == 0]
    used = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    used |= {n.value.id for n in ast.walk(tree)
             if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name)}
    ## A string that parses as an expression may be a string annotation
    ## ("List[int]") or an __all__ entry, so its names count as used. Prose such
    ## as "Asset List" does not parse and is ignored.
    for n in ast.walk(tree):
        if isinstance(n, ast.Constant) and isinstance(n.value, str) and len(n.value) < 200:
            try:
                expr = ast.parse(n.value.strip(), mode="eval")
            except SyntaxError:
                continue
            used |= {m.id for m in ast.walk(expr) if isinstance(m, ast.Name)}
    return imports, used


def prune_typing_imports(path: str, before_src: str) -> int:
    """Drop `from typing import X` names the rewrite left unused.

    Only names that WERE used before the fix and are unused now are removed,
    so pre-existing unused imports stay untouched. typing imports have no side
    effects, so removing them cannot change behavior.
    """
    with open(path, encoding="utf-8") as f:
        src = f.read()
    tree = ast.parse(src)
    imports, used_now = _typing_usage(tree)
    _, used_before = _typing_usage(ast.parse(before_src))
    lines = src.splitlines(keepends=True)
    removed = 0
    for node in sorted(imports, key=lambda n: n.lineno, reverse=True):
        keep = [a for a in node.names
                if (a.asname or a.name) in used_now or (a.asname or a.name) not in used_before]
        if len(keep) == len(node.names):
            continue
        removed += len(node.names) - len(keep)
        new = ""
        if keep:
            names = ", ".join(a.name + (f" as {a.asname}" if a.asname else "") for a in keep)
            new = f"from {node.module} import {names}\n"
        lines[node.lineno - 1:node.end_lineno] = [new]
    if removed:
        with open(path, "w", encoding="utf-8") as f:
            f.write("".join(lines))
    return removed


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--target", required=True, help="target Python version, e.g. 3.11")
    ap.add_argument("--path", default=".", help="project root (default: .)")
    ap.add_argument("--dry-run", action="store_true", help="report only, change nothing")
    ap.add_argument("--include-string-format", action="store_true",
                    help="also apply UP030/UP031/UP032 string-formatting rewrites")
    ap.add_argument("--runtime-annotation-files", nargs="*", default=[],
                    help="globs whose runtime-evaluated annotations must NOT be rewritten")
    ap.add_argument("--extend-exclude", nargs="*", default=[], help="extra paths to skip")
    args = ap.parse_args()

    major, minor = args.target.split(".")[:2]
    ignore = dict(EXCLUDED_RULES)
    if not args.include_string_format:
        ignore.update(STRING_FORMAT_RULES)

    base = ruff_cmd() + [
        "check", "--isolated", "--select", "UP",
        "--ignore", ",".join(sorted(ignore)),
        "--target-version", f"py{major}{minor}",
        "--extend-exclude", ",".join(DEFAULT_EXCLUDES + args.extend_exclude),
    ]
    if args.runtime_annotation_files:
        pfi = ", ".join(f'"{g}" = {json.dumps(RUNTIME_ANNOTATION_RULES)}'
                        for g in args.runtime_annotation_files)
        base += ["--config", f"lint.per-file-ignores = {{{pfi}}}"]
    base.append(args.path)

    before = run_ruff(base, [])
    names = {d["code"]: d["message"] for d in before}
    fixable = Counter(d["code"] for d in before
                      if d.get("fix") and d["fix"].get("applicability") == "safe")
    fixed_files = sorted({d["filename"] for d in before
                          if d.get("fix") and d["fix"].get("applicability") == "safe"})
    pruned = 0
    if not args.dry_run and fixable:
        sources = {}
        for fn in fixed_files:
            with open(fn, encoding="utf-8") as f:
                sources[fn] = f.read()
        run_ruff(base, ["--fix"])
        pruned = sum(prune_typing_imports(fn, sources[fn]) for fn in fixed_files)
    if args.dry_run:
        after = [d for d in before
                 if not (d.get("fix") and d["fix"].get("applicability") == "safe")]
    else:
        after = run_ruff(base, [])
    remaining = Counter(d["code"] for d in after)
    applied = Counter(
        {c: n - remaining.get(c, 0) for c, n in Counter(d["code"] for d in before).items()}
    )
    files = fixed_files

    verb = "Would apply" if args.dry_run else "Applied"
    print(f"## Syntax modernization (ruff UP rules, target py{major}{minor})\n")
    print(f"{verb} **{sum(v for v in applied.values() if v > 0)}** safe fixes "
          f"in **{len(files)}** files.\n")
    if pruned:
        print(f"Removed **{pruned}** `typing` import names left unused by the rewrite.\n")
    print("| Rule | Example message | Fixed | Left for review |")
    print("| --- | --- | --- | --- |")
    for code in sorted(set(applied) | set(remaining)):
        fixed = max(applied.get(code, 0), 0)
        print(f"| {code} | {names.get(code, '')[:70]} | {fixed} | {remaining.get(code, 0)} |")
    if after:
        print("\n### Left for manual review (no safe automatic fix)\n")
        for d in after[:200]:
            loc = d["location"]
            rel = os.path.relpath(d["filename"], args.path)
            print(f"- `{rel}:{loc['row']}` {d['code']}: {d['message']}")
    print("\n### Rules deliberately not applied\n")
    for code, why in sorted(ignore.items()):
        print(f"- {code}: {why}")
    if args.runtime_annotation_files:
        print("\nAnnotation rewrites skipped for: "
              + ", ".join(f"`{g}`" for g in args.runtime_annotation_files))


if __name__ == "__main__":
    main()
