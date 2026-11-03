"""Static discovery of FastAPI routes for the bruno-collection skill.

Reads Python source with `ast` only. It never imports or runs the target repo and
never opens a file that is not `*.py`. Anything it cannot resolve is listed as
skipped with file and line, never guessed. Python 3.9 and newer, stdlib only.
"""

from __future__ import annotations

import ast
import os
from dataclasses import dataclass, field, replace
from pathlib import Path

from bruno_params import (
    UNRESOLVED,
    Analyzer,
    FieldSpec,
    ModelSpec,
    Param,
    Source,
)

__all__ = [
    "UNRESOLVED",
    "AuthFinding",
    "DiscoveryResult",
    "Endpoint",
    "FieldSpec",
    "ModelSpec",
    "Param",
    "Skipped",
    "Source",
    "TokenEndpoint",
    "discover",
]

IGNORED_DIRS = {
    "legacy",
    "tests",
    "test",
    "node_modules",
    "site-packages",
    "dist",
    "build",
    "__pycache__",
}
HTTP_METHODS = {"get", "post", "put", "patch", "delete"}
MAX_FILE_BYTES = 2 * 1024 * 1024
SECURITY = {
    "OAuth2PasswordBearer": "oauth2_password",
    "APIKeyHeader": "api_key_header",
    "APIKeyQuery": "api_key_query",
    "HTTPBearer": "bearer",
    "HTTPBasic": "basic",
}
PRIORITY = ["oauth2_password", "api_key_header", "api_key_query", "bearer", "basic"]
AUTH_HINTS = ("key", "token", "auth", "secret")
DYNAMIC = "registered dynamically or conditionally (inside if/for/try/with/function)"


@dataclass
class Endpoint:
    method: str
    path: str
    tags: list[str]
    function: str
    docstring: str | None
    source: Source
    params: list[Param] = field(default_factory=list)
    body: ModelSpec | None = None
    notes: list[str] = field(default_factory=list)
    response_fields: list[str] = field(default_factory=list)
    return_keys: list[str] = field(
        default_factory=list
    )  # keys of a literal `return {...}`


@dataclass
class Skipped:
    source: Source
    reason: str
    kind: str = "unresolved"  # unresolved | not_read | unmounted


@dataclass
class AuthFinding:
    kind: str
    header_name: str | None = None
    source: Source | None = None


@dataclass
class TokenEndpoint:
    path: str
    grant_inputs: list[str]
    token_field: str
    source: Source


@dataclass
class DiscoveryResult:
    app_found: bool
    endpoints: list[Endpoint]
    skipped: list[Skipped]
    auth: AuthFinding | None = None
    token: TokenEndpoint | None = None

    def outcome_lines(self) -> list[str]:
        """Three separate outcomes; one never stands for another."""
        lines: list[str] = []
        if self.endpoints:
            lines.append(f"{len(self.endpoints)} endpoint(s) found and resolved")
        labels = {
            "unresolved": "found but not statically resolvable",
            "unmounted": "found but not mounted on any app",
            "not_read": "not read",
        }
        for s in self.skipped:
            label = labels.get(s.kind, s.kind)
            lines.append(f"{label}: {s.source.file}:{s.source.line} {s.reason}")
        if self.auth is not None:
            if self.auth.kind == "none_recognized":
                lines.append(
                    "no auth pattern recognized, check middleware "
                    "(this is not proof that the API has no auth)"
                )
            else:
                where = (
                    f" at {self.auth.source.file}:{self.auth.source.line}"
                    if self.auth.source
                    else ""
                )
                header = (
                    f" header {self.auth.header_name}" if self.auth.header_name else ""
                )
                lines.append(f"auth found: {self.auth.kind}{header}{where}")
        if self.token is not None:
            lines.append(
                f"token endpoint found: POST {self.token.path} "
                f"({self.token.source.file}:{self.token.source.line})"
            )
        if not self.app_found and not self.endpoints:
            lines.append(
                "no route discovered (the reader found no FastAPI app; "
                "this is not proof that the repo has no routes)"
            )
        return lines


# ----------------------------------------------------------------- internals


@dataclass
class _Route:
    methods: list[str]
    path: str | None
    tags: list[str]
    function: str
    docstring: str | None
    source: Source
    func: ast.FunctionDef | ast.AsyncFunctionDef | None = None
    fmod: _Module | None = None
    response: ast.expr | None = None


@dataclass
class _Include:
    target: ast.expr
    prefix: str | None
    tags: list[str]
    source: Source
    mod: _Module
    resolved: _Router | None = None


@dataclass
class _Router:
    mod: _Module
    name: str
    kind: str  # app | router
    prefix: str | None
    tags: list[str]
    source: Source
    routes: list[_Route] = field(default_factory=list)
    includes: list[_Include] = field(default_factory=list)


@dataclass
class _Module:
    rel: str
    dotted: str
    package: list[str]
    tree: ast.Module
    imports: dict[str, tuple[str, str | None]] = field(default_factory=dict)
    consts: dict[str, str] = field(default_factory=dict)
    routers: dict[str, _Router] = field(default_factory=dict)
    classes: dict[str, ast.ClassDef] = field(default_factory=dict)
    functions: dict[str, ast.FunctionDef | ast.AsyncFunctionDef] = field(
        default_factory=dict
    )


def _rel_of(ctx: object) -> str:
    assert isinstance(ctx, _Module)
    return ctx.rel


def _inside(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _collect(root: Path, skipped: list[Skipped]) -> list[Path]:
    root_resolved = root.resolve()
    found: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        here = Path(dirpath)
        keep: list[str] = []
        for name in sorted(dirnames):
            path = here / name
            if path.is_symlink():
                rel = path.relative_to(root).as_posix()
                skipped.append(
                    Skipped(
                        Source(rel, 1),
                        "symlink to a folder is not followed",
                        "not_read",
                    )
                )
            elif name not in IGNORED_DIRS and not name.startswith("."):
                keep.append(name)
        dirnames[:] = keep
        for name in sorted(filenames):
            if not name.endswith(".py"):
                continue
            path = here / name
            rel = path.relative_to(root).as_posix()
            try:
                if path.is_symlink() and not _inside(path.resolve(), root_resolved):
                    skipped.append(
                        Skipped(
                            Source(rel, 1),
                            "symlink leaves the repo, not read",
                            "not_read",
                        )
                    )
                    continue
                if path.stat().st_size > MAX_FILE_BYTES:
                    skipped.append(
                        Skipped(Source(rel, 1), "file too large, not read", "not_read")
                    )
                    continue
            except OSError:
                skipped.append(
                    Skipped(Source(rel, 1), "symlink or file not readable", "not_read")
                )
                continue
            found.append(path)
    return found


def _dotted(rel: str) -> tuple[str, list[str]]:
    parts = list(Path(rel).with_suffix("").parts)
    package = parts[:-1]
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts), package


def _flatten(node: ast.AST) -> list[str] | None:
    if isinstance(node, ast.Name):
        return [node.id]
    if isinstance(node, ast.Attribute):
        inner = _flatten(node.value)
        return None if inner is None else [*inner, node.attr]
    return None


def _const_str(mod: _Module, node: ast.AST | None) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Name):
        return mod.consts.get(node.id)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left, right = _const_str(mod, node.left), _const_str(mod, node.right)
        return None if left is None or right is None else left + right
    return None


def _str_list(node: ast.AST | None) -> list[str]:
    if isinstance(node, (ast.List, ast.Tuple)):
        return [
            e.value
            for e in node.elts
            if isinstance(e, ast.Constant) and isinstance(e.value, str)
        ]
    return []


def _kw(call: ast.Call, name: str) -> ast.expr | None:
    for kw in call.keywords:
        if kw.arg == name:
            return kw.value
    return None


def _arg(call: ast.Call, index: int, name: str) -> ast.expr | None:
    if len(call.args) > index:
        return call.args[index]
    return _kw(call, name)


def _child_blocks(stmt: ast.stmt) -> list[list[ast.stmt]]:
    blocks: list[list[ast.stmt]] = []
    for attr in ("body", "orelse", "finalbody"):
        block = getattr(stmt, attr, None)
        if isinstance(block, list):
            blocks.append(block)
    for handler in getattr(stmt, "handlers", []):
        blocks.append(handler.body)
    return blocks


class _Discovery:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.skipped: list[Skipped] = []
        self.registry: dict[str, _Module] = {}
        self.modules: list[_Module] = []
        self._seen_skips: set[tuple[str, int, str]] = set()
        # Mounts made inside functions that are called with a router (see _follow_call).
        self._handled: set[tuple[str, int]] = set()
        self._deferred: list[tuple[Source, str]] = []
        self.analyzer = Analyzer(self.lookup_class, _rel_of)

    def skip(self, source: Source, reason: str, kind: str = "unresolved") -> None:
        key = (source.file, source.line, reason)
        if key not in self._seen_skips:
            self._seen_skips.add(key)
            self.skipped.append(Skipped(source, reason, kind))

    # -- phase 1: parse, imports, constants, routers
    def load(self) -> None:
        for path in _collect(self.root, self.skipped):
            rel = path.relative_to(self.root).as_posix()
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"), filename=rel)
            except SyntaxError as exc:
                self.skip(
                    Source(rel, exc.lineno or 1),
                    "syntax error or syntax this interpreter cannot parse",
                    "not_read",
                )
                continue
            except (
                UnicodeDecodeError,
                ValueError,
                RecursionError,
                MemoryError,
                OSError,
            ):
                self.skip(
                    Source(rel, 1), "file could not be read or parsed", "not_read"
                )
                continue
            dotted, package = _dotted(rel)
            mod = _Module(rel, dotted, package, tree)
            self.modules.append(mod)
            self.registry[dotted] = mod
            if dotted.startswith("src."):
                self.registry.setdefault(dotted[4:], mod)
        for mod in self.modules:
            self._collect_module(mod)

    def _collect_module(self, mod: _Module) -> None:
        for stmt in mod.tree.body:
            if isinstance(stmt, ast.Import):
                for alias in stmt.names:
                    if alias.asname:
                        mod.imports[alias.asname] = (alias.name, None)
                    else:
                        mod.imports[alias.name.split(".")[0]] = (
                            alias.name.split(".")[0],
                            None,
                        )
            elif isinstance(stmt, ast.ImportFrom):
                base = self._import_base(mod, stmt)
                for alias in stmt.names:
                    mod.imports[alias.asname or alias.name] = (base, alias.name)
            elif isinstance(stmt, ast.ClassDef):
                mod.classes[stmt.name] = stmt
            elif isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                mod.functions[stmt.name] = stmt
            elif isinstance(stmt, ast.Assign) and len(stmt.targets) == 1:
                target = stmt.targets[0]
                if not isinstance(target, ast.Name):
                    continue
                value = _const_str(mod, stmt.value)
                if value is not None:
                    mod.consts[target.id] = value
                elif isinstance(stmt.value, ast.Call):
                    self._maybe_router(mod, target.id, stmt.value, stmt.lineno)

    @staticmethod
    def _import_base(mod: _Module, stmt: ast.ImportFrom) -> str:
        if stmt.level == 0:
            return stmt.module or ""
        base = mod.package[: len(mod.package) - (stmt.level - 1)]
        if stmt.module:
            base = [*base, *stmt.module.split(".")]
        return ".".join(base)

    @staticmethod
    def _maybe_router(mod: _Module, name: str, call: ast.Call, line: int) -> None:
        parts = _flatten(call.func)
        if not parts or parts[-1] not in ("FastAPI", "APIRouter"):
            return
        kind = "app" if parts[-1] == "FastAPI" else "router"
        prefix: str | None = ""
        if kind == "router" and _kw(call, "prefix") is not None:
            prefix = _const_str(mod, _kw(call, "prefix"))
        tags = _str_list(_kw(call, "tags")) if kind == "router" else []
        mod.routers[name] = _Router(
            mod, name, kind, prefix, tags, Source(mod.rel, line)
        )

    # -- reference resolution across modules
    def _follow(self, mod: _Module | None, name: str, depth: int = 0) -> _Router | None:
        if mod is None or depth > 5:
            return None
        if name in mod.routers:
            return mod.routers[name]
        if name in mod.imports:
            base, attr = mod.imports[name]
            if attr is not None:
                return self._follow(self.registry.get(base), attr, depth + 1)
        return None

    def _target_module(self, mod: _Module, parts: list[str]) -> _Module | None:
        """The module that an attribute chain like `pkg.sub.name` points into."""
        head = parts[0]
        if head not in mod.imports:
            return None
        base, attr = mod.imports[head]
        module_path = base.split(".") if attr is None else [*base.split("."), attr]
        return self.registry.get(".".join([*module_path, *parts[1:-1]]))

    def resolve(self, mod: _Module, expr: ast.AST) -> _Router | None:
        parts = _flatten(expr)
        if not parts:
            return None
        if len(parts) == 1:
            return self._follow(mod, parts[0])
        return self._follow(self._target_module(mod, parts), parts[-1])

    def _follow_def(
        self, mod: _Module | None, name: str, table: str, depth: int = 0
    ) -> tuple[ast.AST, _Module] | None:
        if mod is None or depth > 5:
            return None
        found = getattr(mod, table).get(name)
        if found is not None:
            return found, mod
        if name in mod.imports and mod.imports[name][1] is not None:
            base, attr = mod.imports[name]
            return self._follow_def(
                self.registry.get(base), str(attr), table, depth + 1
            )
        return None

    def lookup_class(
        self, ctx: object, parts: list[str]
    ) -> tuple[ast.ClassDef, object] | None:
        assert isinstance(ctx, _Module)
        if len(parts) == 1:
            found = self._follow_def(ctx, parts[0], "classes")
        else:
            found = self._follow_def(
                self._target_module(ctx, parts), parts[-1], "classes"
            )
        if found is None or not isinstance(found[0], ast.ClassDef):
            return None
        return found[0], found[1]

    def _find_function(
        self, mod: _Module, expr: ast.AST | None
    ) -> tuple[ast.FunctionDef | ast.AsyncFunctionDef, _Module] | None:
        parts = _flatten(expr) if expr is not None else None
        if not parts:
            return None
        if len(parts) == 1:
            found = self._follow_def(mod, parts[0], "functions")
        else:
            found = self._follow_def(
                self._target_module(mod, parts), parts[-1], "functions"
            )
        if found is None or not isinstance(
            found[0], (ast.FunctionDef, ast.AsyncFunctionDef)
        ):
            return None
        return found[0], found[1]

    # -- phase 2: routes and includes
    def scan(self) -> None:
        for mod in self.modules:
            self._scan_block(mod, mod.tree.body, nested=False)

    def _scan_block(self, mod: _Module, block: list[ast.stmt], nested: bool) -> None:
        for stmt in block:
            if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self._decorators(mod, stmt, nested)
                self._scan_block(mod, stmt.body, True)
            elif isinstance(stmt, ast.ClassDef):
                self._scan_block(mod, stmt.body, True)
            elif isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
                self._call(mod, stmt.value, nested)
                if not nested:
                    self._follow_call(mod, stmt.value, {}, (), 0)
            else:
                for sub in _child_blocks(stmt):
                    self._scan_block(mod, sub, True)

    def _decorators(
        self, mod: _Module, func: ast.FunctionDef | ast.AsyncFunctionDef, nested: bool
    ) -> None:
        for dec in func.decorator_list:
            if not isinstance(dec, ast.Call) or not isinstance(dec.func, ast.Attribute):
                continue
            attr = dec.func.attr
            if attr not in HTTP_METHODS and attr != "api_route":
                continue
            router = self.resolve(mod, dec.func.value)
            if router is None:
                continue
            source = Source(mod.rel, dec.lineno)
            if nested:
                self.skip(source, DYNAMIC)
                continue
            methods = (
                [attr.upper()]
                if attr in HTTP_METHODS
                else [m.upper() for m in _str_list(_kw(dec, "methods"))]
            )
            path_node = _arg(dec, 0, "path")
            router.routes.append(
                _Route(
                    methods,
                    _const_str(mod, path_node),
                    _str_list(_kw(dec, "tags")),
                    func.name,
                    ast.get_docstring(func),
                    source,
                    func,
                    mod,
                    _kw(dec, "response_model") or func.returns,
                )
            )

    def _call(self, mod: _Module, call: ast.Call, nested: bool) -> None:
        if not isinstance(call.func, ast.Attribute):
            return
        attr = call.func.attr
        if attr not in ("include_router", "add_api_route"):
            return
        router = self.resolve(mod, call.func.value)
        if router is None:
            return
        source = Source(mod.rel, call.lineno)
        if nested:
            # Reported at the end, unless a followed function call mounted it.
            self._deferred.append((source, DYNAMIC))
            return
        if attr == "include_router":
            target = _arg(call, 0, "router")
            if target is None:
                return
            prefix = (
                ""
                if _kw(call, "prefix") is None
                else _const_str(mod, _kw(call, "prefix"))
            )
            router.includes.append(
                _Include(target, prefix, _str_list(_kw(call, "tags")), source, mod)
            )
            return
        endpoint = _arg(call, 1, "endpoint")
        names = _flatten(endpoint) if endpoint is not None else None
        handler = self._find_function(mod, endpoint)
        methods = [m.upper() for m in _str_list(_kw(call, "methods"))] or ["GET"]
        router.routes.append(
            _Route(
                methods,
                _const_str(mod, _arg(call, 0, "path")),
                [],
                names[-1] if names else "",
                ast.get_docstring(handler[0]) if handler else None,
                source,
                handler[0] if handler else None,
                handler[1] if handler else None,
                _kw(call, "response_model")
                or (handler[0].returns if handler else None),
            )
        )

    # -- mounts made inside a function that the app module calls
    def _follow_call(
        self,
        mod: _Module,
        call: ast.Call,
        bindings: dict[str, _Router],
        stack: tuple[int, ...],
        depth: int,
    ) -> None:
        """Follow `init(app)` into the function body, binding its parameters.

        Only a plain function called by name, with straight-line statements, is
        followed (no if/for/try/with, no decorated function, depth <= 4). A
        function-local `from x import y` is honoured. Anything else keeps the
        existing "registered dynamically" skip.
        """
        if (
            depth >= 4
            or isinstance(call.func, ast.Attribute)
            and call.func.attr
            in (
                "include_router",
                "add_api_route",
            )
        ):
            return
        found = self._find_function(mod, call.func)
        if found is None:
            return
        func, fmod = found
        if (
            not isinstance(func, ast.FunctionDef)
            or func.decorator_list
            or id(func) in stack
        ):
            return
        params = [a.arg for a in [*func.args.posonlyargs, *func.args.args]]
        params += [a.arg for a in func.args.kwonlyargs]
        inner: dict[str, _Router] = {}
        for name, arg in zip(params, call.args):
            router = self._resolve_scoped(mod, bindings, arg)
            if router is not None:
                inner[name] = router
        for kw in call.keywords:
            router = self._resolve_scoped(mod, bindings, kw.value)
            if kw.arg in params and router is not None:
                inner[kw.arg] = router
        scoped = replace(fmod, imports=dict(fmod.imports))
        for stmt in func.body:
            if isinstance(stmt, ast.ImportFrom):
                base = self._import_base(fmod, stmt)
                for alias in stmt.names:
                    scoped.imports[alias.asname or alias.name] = (base, alias.name)
            elif isinstance(stmt, ast.Import):
                for alias in stmt.names:
                    if alias.asname:
                        scoped.imports[alias.asname] = (alias.name, None)
                    else:
                        head = alias.name.split(".")[0]
                        scoped.imports[head] = (head, None)
            elif isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
                self._mount(scoped, stmt.value, inner)
                self._follow_call(
                    scoped, stmt.value, inner, (*stack, id(func)), depth + 1
                )
            elif not isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for node in ast.walk(stmt):
                    if (
                        isinstance(node, ast.Call)
                        and isinstance(node.func, ast.Attribute)
                        and node.func.attr in ("include_router", "add_api_route")
                    ):
                        self.skip(Source(fmod.rel, node.lineno), DYNAMIC)

    def _resolve_scoped(
        self, mod: _Module, bindings: dict[str, _Router], expr: ast.AST
    ) -> _Router | None:
        if isinstance(expr, ast.Name) and expr.id in bindings:
            return bindings[expr.id]
        return self.resolve(mod, expr)

    def _mount(
        self, mod: _Module, call: ast.Call, bindings: dict[str, _Router]
    ) -> None:
        if not isinstance(call.func, ast.Attribute):
            return
        if call.func.attr != "include_router":
            return
        router = self._resolve_scoped(mod, bindings, call.func.value)
        target = _arg(call, 0, "router")
        if router is None or target is None:
            return
        prefix = (
            "" if _kw(call, "prefix") is None else _const_str(mod, _kw(call, "prefix"))
        )
        self._handled.add((mod.rel, call.lineno))
        router.includes.append(
            _Include(
                target,
                prefix,
                _str_list(_kw(call, "tags")),
                Source(mod.rel, call.lineno),
                mod,
                self._resolve_scoped(mod, bindings, target),
            )
        )

    # -- phase 3: walk from each app
    def endpoints(self) -> tuple[list[Endpoint], bool]:
        for source, reason in self._deferred:
            if (source.file, source.line) not in self._handled:
                self.skip(source, reason)
        self._deferred = []
        apps = [r for m in self.modules for r in m.routers.values() if r.kind == "app"]
        reached: set[tuple[str, str]] = set()
        out: list[Endpoint] = []
        for app in apps:
            self._walk(app, "", [], (), reached, out)
        for mod in self.modules:
            for router in mod.routers.values():
                if (
                    router.kind == "router"
                    and router.routes
                    and (mod.rel, router.name) not in reached
                ):
                    self.skip(
                        router.source,
                        "router is not included in any app; no requests generated",
                        "unmounted",
                    )
        out.sort(key=lambda e: (e.path, e.method, e.source.file, e.source.line))
        return out, bool(apps)

    def _walk(
        self,
        router: _Router,
        prefix: str,
        tags: list[str],
        stack: tuple[tuple[str, str], ...],
        reached: set[tuple[str, str]],
        out: list[Endpoint],
    ) -> None:
        key = (router.mod.rel, router.name)
        if key in stack:
            return
        reached.add(key)
        for route in router.routes:
            if route.path is None:
                self.skip(route.source, "route path is not a literal string")
                continue
            full_path = prefix + route.path
            for method in route.methods:
                notes: list[str] = []
                params, body = self.analyzer.endpoint_params(
                    route.func, route.fmod, full_path, notes
                )
                out.append(
                    Endpoint(
                        method,
                        full_path,
                        _dedupe([*tags, *route.tags]),
                        route.function,
                        route.docstring,
                        route.source,
                        params,
                        body,
                        notes,
                        self._response_fields(route),
                        self._return_keys(route),
                    )
                )
        for inc in router.includes:
            child = inc.resolved or self.resolve(inc.mod, inc.target)
            if child is None:
                self.skip(
                    inc.source, "include_router target is not statically resolvable"
                )
            elif inc.prefix is None or child.prefix is None:
                self.skip(inc.source, "router prefix is not a literal string")
            else:
                self._walk(
                    child,
                    prefix + inc.prefix + child.prefix,
                    [*tags, *inc.tags, *child.tags],
                    (*stack, key),
                    reached,
                    out,
                )

    @staticmethod
    def _return_keys(route: _Route) -> list[str]:
        """String keys of the handler's own first `return {...}` literal.

        A nested function, lambda or class is not searched: its `return` is not
        the handler's response.
        """
        if route.func is None:
            return []
        pending: list[ast.AST] = list(route.func.body)
        while pending:
            node = pending.pop(0)
            if isinstance(
                node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)
            ):
                continue
            if isinstance(node, ast.Return) and isinstance(node.value, ast.Dict):
                return [
                    k.value
                    for k in node.value.keys
                    if isinstance(k, ast.Constant) and isinstance(k.value, str)
                ]
            pending[:0] = list(ast.iter_child_nodes(node))
        return []

    def _response_fields(self, route: _Route) -> list[str]:
        if route.response is None or route.fmod is None:
            return []
        found = self.analyzer.type_info(route.response, route.fmod)
        if not found.model:
            return []
        spec = self.analyzer.model_spec(found.model[0], found.model[1], [], (), 1)
        return [f.name for f in spec.fields]

    # -- phase 4: authentication and the token endpoint
    def auth(
        self, endpoints: list[Endpoint]
    ) -> tuple[AuthFinding, TokenEndpoint | None]:
        found: list[tuple[str, str | None, Source]] = []
        for mod in self.modules:
            for node in ast.walk(mod.tree):
                if isinstance(node, ast.Call):
                    name = (_flatten(node.func) or [""])[-1]
                    if name in SECURITY:
                        first = node.args[0] if node.args else None
                        key = "tokenUrl" if name == "OAuth2PasswordBearer" else "name"
                        value = _const_str(mod, first or _kw(node, key))
                        found.append(
                            (SECURITY[name], value, Source(mod.rel, node.lineno))
                        )
                    elif (
                        isinstance(node.func, ast.Attribute)
                        and node.func.attr == "get"
                        and isinstance(node.func.value, ast.Attribute)
                        and node.func.value.attr == "headers"
                        and node.args
                    ):
                        self._header_read(mod, node.args[0], node.lineno, found)
                elif (
                    isinstance(node, ast.Subscript)
                    and isinstance(node.value, ast.Attribute)
                    and node.value.attr == "headers"
                ):
                    self._header_read(mod, node.slice, node.lineno, found)
        if not found:
            return AuthFinding("none_recognized"), None
        found.sort(key=lambda f: (PRIORITY.index(f[0]), f[2].file, f[2].line))
        kind, value, source = found[0]
        if kind == "oauth2_password":
            return AuthFinding(kind, None, source), self._token(
                endpoints, value, source
            )
        return AuthFinding(kind, value, source), None

    @staticmethod
    def _header_read(
        mod: _Module,
        node: ast.AST,
        line: int,
        found: list[tuple[str, str | None, Source]],
    ) -> None:
        name = _const_str(mod, node)
        if name and any(hint in name.lower() for hint in AUTH_HINTS):
            kind = "bearer" if name.lower() == "authorization" else "api_key_header"
            found.append((kind, name, Source(mod.rel, line)))

    def _token(
        self, endpoints: list[Endpoint], url: str | None, source: Source
    ) -> TokenEndpoint | None:
        wanted = "/" + (url or "").lstrip("/")
        posts = [e for e in endpoints if e.method == "POST"]
        hits = [e for e in posts if e.path == wanted] or [
            e for e in posts if e.path.endswith(wanted)
        ]
        if url is None or len(hits) != 1:
            self.skip(
                source,
                f"tokenUrl {wanted}: no single matching POST route found; no token request generated",
            )
            return None
        ep = hits[0]
        inputs = [p.name for p in ep.params if p.location == "form"]
        if not inputs and ep.body is not None:
            inputs = [f.name for f in ep.body.fields]
        if not inputs:
            inputs = [p.name for p in ep.params if p.location == "query"]
        field = "access_token"
        if "access_token" not in ep.response_fields:
            field = next((f for f in ep.response_fields if "token" in f.lower()), field)
        return TokenEndpoint(ep.path, inputs, field, ep.source)


def _dedupe(items: list[str]) -> list[str]:
    seen: list[str] = []
    for item in items:
        if item not in seen:
            seen.append(item)
    return seen


def discover(root: Path) -> DiscoveryResult:
    """Discover FastAPI endpoints under `root` without importing or running it."""
    root = Path(root)
    disc = _Discovery(root)
    disc.load()
    disc.scan()
    endpoints, app_found = disc.endpoints()
    auth, token = disc.auth(endpoints) if app_found else (None, None)
    return DiscoveryResult(app_found, endpoints, disc.skipped, auth, token)
