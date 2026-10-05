#!/usr/bin/env python3
"""Scan a project for stdlib removals / behavior changes between two Python versions.

Static AST scan (never modifies files). Reports every place the code touches
something that was removed, now raises, or silently behaves differently in a
version in (from, to]. These are NOT syntax changes — each needs a human
decision, so the skill reports them in the guide instead of auto-fixing.

Usage:
    python scan_upgrade_risks.py --from 3.8 --to 3.11 [--path .]

Prints a Markdown table to stdout. Exit code is always 0 (report only).
"""

from __future__ import annotations

import argparse
import ast
import os
import re
import sys

## (version, severity, kind, target, message, fix)
##   severity: breaks = ImportError/AttributeError/TypeError at runtime
##             behavior = runs, but output/semantics differ
##             deprecated = warns now, removed in a later version
##   kind: module (imported), attr (dotted name), method (any obj.<name>(...)),
##         kwarg (call to dotted name with keyword), special (custom check)
_ABCS = ("Awaitable Coroutine AsyncIterable AsyncIterator AsyncGenerator Hashable "
         "Iterable Iterator Generator Reversible Sized Container Callable Collection "
         "Set MutableSet Mapping MutableMapping MappingView KeysView ItemsView "
         "ValuesView Sequence MutableSequence ByteString").split()
_ASYNCIO_LOOP_APIS = ("sleep gather wait wait_for shield as_completed open_connection "
                      "start_server open_unix_connection start_unix_server Queue "
                      "LifoQueue PriorityQueue Lock Event Condition Semaphore "
                      "BoundedSemaphore create_subprocess_exec create_subprocess_shell").split()

RULES: list[tuple] = [
    ("3.9", "breaks", "attr", "base64.encodestring", "removed", "use base64.encodebytes"),
    ("3.9", "breaks", "attr", "base64.decodestring", "removed", "use base64.decodebytes"),
    ("3.9", "breaks", "method", "isAlive", "Thread.isAlive() removed", "use is_alive()"),
    ("3.9", "breaks", "method", "getchildren", "Element.getchildren() removed", "use list(elem)"),
    ("3.9", "breaks", "method", "getiterator", "Element.getiterator() removed", "use elem.iter()"),
    ("3.9", "breaks", "attr", "sys.setcheckinterval", "removed", "use sys.setswitchinterval"),
    ("3.9", "breaks", "attr", "plistlib.readPlist", "removed", "use plistlib.load"),
    ("3.9", "breaks", "kwarg", "json.loads:encoding", "encoding= argument removed", "drop the argument"),
    ("3.10", "breaks", "module", "parser", "module removed", "use ast"),
    ("3.10", "breaks", "module", "formatter", "module removed", "vendor or drop"),
    *[("3.10", "breaks", "attr", f"collections.{n}", "ABC alias removed from collections",
       f"use collections.abc.{n} (identical class)") for n in _ABCS],
    *[("3.10", "breaks", "kwarg", f"asyncio.{n}:loop", "loop= parameter removed",
       "drop loop=; uses the running loop") for n in _ASYNCIO_LOOP_APIS],
    ("3.10", "deprecated", "module", "distutils", "deprecated (removed in 3.12)",
     "use setuptools / packaging / shutil"),
    ("3.10", "deprecated", "attr", "asyncio.get_event_loop",
     "warns when no loop is running (errors in 3.14)", "use asyncio.run / get_running_loop"),
    ("3.11", "breaks", "attr", "asyncio.coroutine", "@asyncio.coroutine removed", "use async def"),
    ("3.11", "breaks", "attr", "inspect.getargspec", "removed", "use inspect.signature/getfullargspec"),
    ("3.11", "breaks", "attr", "inspect.formatargspec", "removed", "use inspect.signature"),
    ("3.11", "breaks", "attr", "binascii.b2a_hqx", "removed", "no replacement"),
    ("3.11", "breaks", "attr", "binascii.a2b_hqx", "removed", "no replacement"),
    ("3.11", "breaks", "attr", "gettext.lgettext", "l*gettext() removed", "use gettext()"),
    ("3.11", "breaks", "kwarg", "random.shuffle:random", "random= parameter removed",
     "use random.Random(seed).shuffle"),
    ("3.11", "breaks", "special", "random.sample:set", "random.sample() rejects sets",
     "pass sorted(s) / list(s) (list(s) keeps the old, order-dependent result)"),
    ("3.11", "breaks", "special", "re:inline-flag", "global inline flag not at pattern start is an error",
     "move (?i)/(?s)/... to the very start of the pattern"),
    ("3.11", "behavior", "special", "enum:mixin",
     "format()/f-string of (str/int, Enum) members now gives 'Cls.MEMBER', not the value",
     "use member.value explicitly where the value is formatted"),
    ("3.11", "behavior", "special", "int:str-limit",
     "int <-> str conversion of >4300 digits raises ValueError", "only if huge ints are parsed"),
    ("3.11", "deprecated", "attr", "locale.getdefaultlocale", "deprecated", "use locale.getlocale"),
    ("3.12", "breaks", "module", "distutils", "module removed", "use setuptools / packaging"),
    ("3.12", "breaks", "module", "imp", "module removed", "use importlib"),
    ("3.12", "breaks", "module", "asynchat", "module removed", "use asyncio"),
    ("3.12", "breaks", "module", "asyncore", "module removed", "use asyncio"),
    ("3.12", "breaks", "module", "smtpd", "module removed", "use aiosmtpd"),
    ("3.12", "breaks", "module", "pkg_resources",
     "setuptools no longer preinstalled in venvs", "use importlib.metadata/resources"),
    ("3.12", "breaks", "attr", "configparser.SafeConfigParser", "removed", "use ConfigParser"),
    ("3.12", "breaks", "method", "readfp", "ConfigParser.readfp() removed", "use read_file()"),
    ("3.12", "breaks", "attr", "ssl.wrap_socket", "removed", "use SSLContext.wrap_socket"),
    ("3.12", "breaks", "attr", "locale.format", "removed", "use locale.format_string"),
    *[("3.12", "breaks", "method", m, "unittest alias removed", f"use {n}") for m, n in [
        ("assertEquals", "assertEqual"), ("assertNotEquals", "assertNotEqual"),
        ("assert_", "assertTrue"), ("failUnless", "assertTrue"), ("failIf", "assertFalse"),
        ("assertRegexpMatches", "assertRegex"), ("assertRaisesRegexp", "assertRaisesRegex"),
        ("assertDictContainsSubset", "explicit dict comparison")]],
    ("3.12", "deprecated", "attr", "datetime.datetime.utcnow", "deprecated",
     "datetime.now(timezone.utc) (returns an AWARE datetime - not a drop-in)"),
    *[("3.13", "breaks", "module", m, "module removed (PEP 594)", "use a PyPI replacement")
      for m in ("cgi cgitb crypt telnetlib pipes nntplib imghdr sndhdr audioop chunk "
                "mailcap msilib nis ossaudiodev spwd sunau uu xdrlib lib2to3").split()],
    ("3.13", "breaks", "attr", "locale.resetlocale", "removed", "use locale.setlocale"),
]

_INLINE_FLAG = re.compile(r"\(\?[aiLmsux]+\)")
_RE_FUNCS = {"compile", "match", "search", "fullmatch", "findall", "finditer", "sub",
             "subn", "split"}


def vtuple(v: str) -> tuple[int, int]:
    a, b = v.split(".")[:2]
    return int(a), int(b)


class Scanner(ast.NodeVisitor):
    def __init__(self, rules: list[tuple]) -> None:
        self.rules = rules
        self.aliases: dict[str, str] = {}  # local name -> dotted origin
        self.hits: list[tuple[int, tuple, str]] = []

    def hit(self, node: ast.AST, rule: tuple, detail: str = "") -> None:
        self.hits.append((getattr(node, "lineno", 0), rule, detail))

    def dotted(self, node: ast.AST) -> str | None:
        parts = []
        while isinstance(node, ast.Attribute):
            parts.append(node.attr)
            node = node.value
        if not isinstance(node, ast.Name):
            return None
        parts.append(self.aliases.get(node.id, node.id))
        return ".".join(reversed(parts))

    def visit_Import(self, node: ast.Import) -> None:
        for a in node.names:
            self.aliases[(a.asname or a.name).split(".")[0]] = (
                a.name if a.asname else a.name.split(".")[0])
            self._check_module(node, a.name)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        mod = node.module or ""
        self._check_module(node, mod)
        for a in node.names:
            full = f"{mod}.{a.name}"
            self.aliases[a.asname or a.name] = full
            self._check_attr(node, full)

    def _check_module(self, node: ast.AST, mod: str) -> None:
        for r in self.rules:
            if r[2] == "module" and (mod == r[3] or mod.startswith(r[3] + ".")):
                self.hit(node, r, mod)

    def _check_attr(self, node: ast.AST, name: str) -> None:
        for r in self.rules:
            if r[2] == "attr" and name == r[3]:
                self.hit(node, r, name)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        name = self.dotted(node)
        if name:
            self._check_attr(node, name)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        func = self.dotted(node.func) or ""
        kwargs = {k.arg for k in node.keywords if k.arg}
        for r in self.rules:
            if r[2] == "kwarg":
                target, kw = r[3].split(":")
                if func == target and kw in kwargs:
                    self.hit(node, r, f"{func}({kw}=...)")
            elif r[2] == "method" and isinstance(node.func, ast.Attribute) \
                    and node.func.attr == r[3]:
                self.hit(node, r, f".{r[3]}()")
            elif r[3] == "random.sample:set" and func == "random.sample" and node.args:
                a = node.args[0]
                if isinstance(a, (ast.Set, ast.SetComp)) or (
                        isinstance(a, ast.Call) and isinstance(a.func, ast.Name)
                        and a.func.id in ("set", "frozenset")):
                    self.hit(node, r, "random.sample(<set>)")
            elif r[3] == "re:inline-flag" and func.startswith("re.") \
                    and func[3:] in _RE_FUNCS and node.args:
                p = node.args[0]
                if isinstance(p, ast.Constant) and isinstance(p.value, str):
                    m = _INLINE_FLAG.search(p.value)
                    if m and m.start() > 0:
                        self.hit(node, r, f"pattern {p.value[:40]!r}")
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        bases = {(self.dotted(b) or "").rsplit(".", 1)[-1] for b in node.bases}
        for r in self.rules:
            if r[3] == "enum:mixin" and bases & {"Enum", "Flag"} and bases & {"str", "int"}:
                self.hit(node, r, f"class {node.name}({', '.join(sorted(bases))})")
        self.generic_visit(node)


def iter_py(root: str):
    skip = {".git", ".venv", "venv", "legacy", "build", "dist", "node_modules", "__pycache__"}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in skip and not d.startswith(".")]
        for f in filenames:
            if f.endswith(".py"):
                yield os.path.join(dirpath, f)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--from", dest="src", required=True)
    ap.add_argument("--to", dest="dst", required=True)
    ap.add_argument("--path", default=".")
    args = ap.parse_args()

    lo, hi = vtuple(args.src), vtuple(args.dst)
    rules = [r for r in RULES if lo < vtuple(r[0]) <= hi]
    rows, errors = [], []
    for path in iter_py(args.path):
        try:
            with open(path, encoding="utf-8") as f:
                tree = ast.parse(f.read(), filename=path)
        except (SyntaxError, UnicodeDecodeError) as e:
            errors.append(f"{os.path.relpath(path, args.path)}: {e}")
            continue
        sc = Scanner(rules)
        sc.visit(tree)
        rel = os.path.relpath(path, args.path)
        for line, r, detail in sc.hits:
            rows.append((r[1], r[0], f"{rel}:{line}", detail, r[4], r[5], rel, line))

    order = {"breaks": 0, "behavior": 1, "deprecated": 2}
    rows = sorted(set(rows), key=lambda x: (order[x[0]], x[6], x[7]))
    print(f"## Stdlib / behavior risks, Python {args.src} -> {args.dst}\n")
    if not rows:
        print("No known removals or behavior changes found in the scanned code.\n")
    else:
        print("| Severity | Since | Location | Found | Change | Suggested fix |")
        print("| --- | --- | --- | --- | --- | --- |")
        for sev, ver, loc, detail, msg, fix, _, _ in rows:
            print(f"| {sev} | {ver} | `{loc}` | `{detail}` | {msg} | {fix} |")
    always = [r for r in rules if r[3] == "int:str-limit"]
    if always:
        print(f"\n> Not detectable statically ({always[0][0]}): {always[0][4]}.")
    if errors:
        print("\n### Files that failed to parse\n")
        for e in errors:
            print(f"- {e}")
    sys.exit(0)


if __name__ == "__main__":
    main()
