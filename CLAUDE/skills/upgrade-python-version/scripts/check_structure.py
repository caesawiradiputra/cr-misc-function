#!/usr/bin/env python3
"""Verify a syntax upgrade did not change code structure (vs. a git revision).

For every .py file changed since <rev> (default HEAD), parses the old and new
source and compares:

  1. The definition inventory: every class / function / method, with its
     qualified name and parameter names/kinds. Any added, removed, renamed or
     re-parameterized definition is a STRUCTURE change.
  2. Each definition's body with type annotations and import statements
     stripped. Annotation rewrites (Optional[X] -> X | None, List -> list) and
     import cleanups vanish here; anything left is a non-annotation code
     change that must be justified (e.g. ruff UP004 `class A(object)` ->
     `class A`, UP024 `IOError` -> `OSError`: equivalent, but visible here).

Usage:
    python check_structure.py [--rev HEAD] [--path .]

Exit code: 0 = only annotation/import changes, 1 = code changes to review,
2 = structure changes (definitions added/removed/re-signatured) or parse errors.
"""

from __future__ import annotations

import argparse
import ast
import subprocess
import sys


class _Strip(ast.NodeTransformer):
    """Drop annotations and imports so only executable structure remains."""

    def visit_Import(self, node):  # noqa: N802
        return None

    visit_ImportFrom = visit_Import  # noqa: N815

    def visit_arg(self, node):  # noqa: N802
        node.annotation = None
        return node

    def visit_FunctionDef(self, node):  # noqa: N802
        node.returns = None
        self.generic_visit(node)
        return node

    visit_AsyncFunctionDef = visit_FunctionDef  # noqa: N815

    def visit_AnnAssign(self, node):  # noqa: N802
        ## `x: T = v` -> keep the assignment; a bare `x: T` has no runtime effect
        ## in a function body, but in a class body it declares a field.
        node.annotation = ast.Constant(value="<annotation>")
        self.generic_visit(node)
        return node


def definitions(tree: ast.AST) -> dict[str, tuple[str, tuple[str, str, str]]]:
    """qualname -> (signature, (stripped body, decorators, bases))."""
    out: dict[str, tuple[str, tuple[str, str, str]]] = {}

    def walk(node: ast.AST, prefix: str) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                q = f"{prefix}{child.name}"
                if isinstance(child, ast.ClassDef):
                    sig = "class"
                else:
                    a = child.args
                    sig = (
                        "def("
                        + ", ".join(
                            [f"/{p.arg}" for p in a.posonlyargs]
                            + [p.arg for p in a.args]
                            + ([f"*{a.vararg.arg}"] if a.vararg else [])
                            + [f"kw:{p.arg}" for p in a.kwonlyargs]
                            + ([f"**{a.kwarg.arg}"] if a.kwarg else [])
                        )
                        + ")"
                    )
                body = ast.Module(
                    body=[
                        s
                        for s in child.body
                        if not isinstance(
                            s, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
                        )
                    ],
                    type_ignores=[],
                )
                head = ast.dump(_Strip().visit(ast.parse(ast.unparse(body))))
                deco = [ast.dump(d) for d in child.decorator_list]
                bases = [ast.dump(b) for b in getattr(child, "bases", [])]
                out[q] = (sig, (head, str(deco), str(bases)))
                walk(child, q + ".")

    walk(tree, "")
    module_level = ast.Module(
        body=[
            s
            for s in tree.body
            if not isinstance(s, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        ],
        type_ignores=[],
    )
    out["<module>"] = (
        "module",
        (ast.dump(_Strip().visit(ast.parse(ast.unparse(module_level)))), "", ""),
    )
    return out


def git(*args: str, cwd: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, check=True
    ).stdout


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--rev", default="HEAD")
    ap.add_argument("--path", default=".")
    args = ap.parse_args()

    changed = [
        f
        for f in git(
            "diff",
            "--name-only",
            "--diff-filter=M",
            args.rev,
            "--",
            "*.py",
            cwd=args.path,
        ).splitlines()
        if f
    ]
    structure, code, errors = [], [], []
    for rel in changed:
        try:
            old = ast.parse(git("show", f"{args.rev}:{rel}", cwd=args.path))
            with open(f"{args.path}/{rel}", encoding="utf-8") as f:
                new = ast.parse(f.read())
        except SyntaxError as e:
            errors.append(f"{rel}: {e}")
            continue
        a, b = definitions(old), definitions(new)
        for q in sorted(set(a) | set(b)):
            if q not in a:
                structure.append(f"{rel}: added `{q}`")
            elif q not in b:
                structure.append(f"{rel}: removed `{q}`")
            elif a[q][0] != b[q][0]:
                structure.append(f"{rel}: signature of `{q}` {a[q][0]} -> {b[q][0]}")
            elif a[q][1] != b[q][1]:
                parts = [
                    label
                    for label, x, y in zip(
                        ("body", "decorators", "bases"), a[q][1], b[q][1]
                    )
                    if x != y
                ]
                code.append(f"{rel}: `{q}` ({', '.join(parts)})")

    print(f"## Structure check vs {args.rev} ({len(changed)} changed .py files)\n")
    for title, items in (
        ("Parse errors", errors),
        ("Structure changes", structure),
        ("Non-annotation code changes to justify", code),
    ):
        if items:
            print(f"### {title}\n")
            print("\n".join(f"- {i}" for i in items) + "\n")
    if not (errors or structure or code):
        print(
            "Only annotations and imports changed: structure and executable code identical."
        )
    sys.exit(2 if errors or structure else 1 if code else 0)


if __name__ == "__main__":
    main()
