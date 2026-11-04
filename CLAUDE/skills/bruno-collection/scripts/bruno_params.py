"""Parameter, model and constraint analysis (AST only) for bruno_discover.

Reads request parameters, Pydantic request models and their constraints from source.
A value that is not a plain literal is recorded as `UNRESOLVED`, never guessed.
Python 3.9 and newer, stdlib only.
"""

from __future__ import annotations

import ast
import re
from collections.abc import Callable
from dataclasses import dataclass, field

UNRESOLVED = "<unresolved>"
DEPTH_LIMIT = 3
CONSTRAINT_KEYS = {
    "min_length",
    "max_length",
    "ge",
    "gt",
    "le",
    "lt",
    "multiple_of",
    "min_items",
    "max_items",
    "pattern",
    "regex",
}
PARAM_FUNCS = {
    "Query": "query",
    "Path": "path",
    "Header": "header",
    "Body": "body",
    "Form": "form",
    "Cookie": "cookie",
    "File": "file",
}
INJECTED = {
    "Request",
    "Response",
    "BackgroundTasks",
    "WebSocket",
    "HTTPConnection",
    "SecurityScopes",
}
LIST_NAMES = {
    "List",
    "list",
    "Sequence",
    "Set",
    "set",
    "FrozenSet",
    "frozenset",
    "Iterable",
    "Tuple",
    "tuple",
}
BARE_NAMES = {"List": "list", "Dict": "dict", "Set": "set", "Tuple": "tuple"}

Lookup = Callable[[object, "list[str]"], "tuple[ast.ClassDef, object] | None"]


@dataclass(frozen=True)
class Source:
    file: str
    line: int


@dataclass
class FieldSpec:
    name: str
    type_name: str = ""
    required: bool = True
    default: object = None
    constraints: dict[str, object] = field(default_factory=dict)
    example: object = None
    children: ModelSpec | None = None
    is_list: bool = False
    enum_values: list[object] | None = None
    unexpanded: bool = False  # a model-typed field that was not expanded


@dataclass
class ModelSpec:
    name: str
    fields: list[FieldSpec]
    source: Source
    example: object = None
    is_list: bool = False


@dataclass
class Param:
    name: str
    location: str  # path | query | header | body | form
    type_name: str = ""
    required: bool = True
    default: object = None
    constraints: dict[str, object] = field(default_factory=dict)
    example: object = None


@dataclass
class _Type:
    name: str
    is_list: bool = False
    optional: bool = False
    enum: list[object] | None = None
    model: tuple[ast.ClassDef, object] | None = None
    constraints: dict[str, object] = field(default_factory=dict)
    metas: list[ast.Call] = field(default_factory=list)


@dataclass
class _Opts:
    has_default: bool = False
    default: object = None
    required: bool = True
    constraints: dict[str, object] = field(default_factory=dict)
    example: object = None


def _flatten(node: ast.AST) -> list[str] | None:
    if isinstance(node, ast.Name):
        return [node.id]
    if isinstance(node, ast.Attribute):
        inner = _flatten(node.value)
        return None if inner is None else [*inner, node.attr]
    return None


def _literal(node: ast.AST) -> object:
    try:
        return ast.literal_eval(node)
    except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError):
        return UNRESOLVED


def _call_name(node: ast.AST) -> str:
    parts = _flatten(node.func) if isinstance(node, ast.Call) else None
    return parts[-1] if parts else ""


def _kw(call: ast.Call, name: str) -> ast.expr | None:
    for kw in call.keywords:
        if kw.arg == name:
            return kw.value
    return None


def _constraints(call: ast.Call) -> dict[str, object]:
    found: dict[str, object] = {}
    for kw in call.keywords:
        if kw.arg in CONSTRAINT_KEYS:
            key = "pattern" if kw.arg == "regex" else str(kw.arg)
            found[key] = _literal(kw.value)
    return found


def _example(call: ast.Call) -> object:
    node = _kw(call, "example")
    if node is not None:
        value = _literal(node)
        return None if value == UNRESOLVED else value
    node = _kw(call, "examples")
    if node is not None:
        value = _literal(node)
        if isinstance(value, list) and value:
            return value[0]
    return None


class Analyzer:
    """Turns route functions and model classes into Param and ModelSpec values."""

    def __init__(self, lookup: Lookup, rel_of: Callable[[object], str]) -> None:
        self.lookup = lookup
        self.rel_of = rel_of

    # ------------------------------------------------------------------ types
    def type_info(self, ann: ast.AST | None, ctx: object) -> _Type:
        if ann is None:
            return _Type("")
        if isinstance(ann, ast.Constant):
            if isinstance(ann.value, str):
                try:
                    return self.type_info(ast.parse(ann.value, mode="eval").body, ctx)
                except SyntaxError:
                    return _Type(ann.value)
            return _Type("None" if ann.value is None else "")
        if isinstance(ann, ast.BinOp) and isinstance(ann.op, ast.BitOr):
            left, right = self.type_info(ann.left, ctx), self.type_info(ann.right, ctx)
            if left.name == "None":
                right.optional = True
                return right
            if right.name == "None":
                left.optional = True
                return left
            return _Type("Union")
        if isinstance(ann, (ast.Name, ast.Attribute)):
            return self._named(ann, ctx)
        if isinstance(ann, ast.Subscript):
            return self._subscript(ann, ctx)
        if isinstance(ann, ast.Call):
            return self._constrained(ann, ctx)
        return _Type("")

    def _named(self, ann: ast.AST, ctx: object) -> _Type:
        parts = _flatten(ann) or [""]
        found = self.lookup(ctx, parts)
        if found:
            cls, cctx = found
            if self.is_enum(cls):
                return _Type(cls.name, enum=list(self.enum_members(cls).values()))
            if self.is_model(cls, cctx):
                return _Type(cls.name, model=(cls, cctx))
        return _Type(BARE_NAMES.get(parts[-1], parts[-1]))

    def _subscript(self, ann: ast.Subscript, ctx: object) -> _Type:
        base = _flatten(ann.value)
        name = base[-1] if base else ""
        inner = ann.slice
        elts = inner.elts if isinstance(inner, ast.Tuple) else [inner]
        if name == "Optional":
            found = self.type_info(elts[0], ctx)
            found.optional = True
            return found
        if name == "Union":
            members = [self.type_info(e, ctx) for e in elts]
            real = [m for m in members if m.name != "None"]
            if len(real) == 1:
                real[0].optional = len(real) != len(members)
                return real[0]
            return _Type("Union")
        if name in LIST_NAMES:
            found = self.type_info(elts[0], ctx)
            found.is_list = True
            return found
        if name == "Literal":
            values = [_literal(e) for e in elts]
            kind = "int" if all(isinstance(v, int) for v in values) else "str"
            return _Type(kind, enum=values)
        if name == "Annotated":
            found = self.type_info(elts[0], ctx)
            found.metas = [e for e in elts[1:] if isinstance(e, ast.Call)]
            return found
        if name in ("Dict", "dict", "Mapping"):
            return _Type("dict")
        return _Type(BARE_NAMES.get(name, name))

    def _constrained(self, call: ast.Call, ctx: object) -> _Type:
        name = _call_name(call)
        kinds = {
            "conint": "int",
            "confloat": "float",
            "constr": "str",
            "conlist": "list",
        }
        if name not in kinds:
            return _Type("")
        found = _Type(kinds[name], constraints=_constraints(call))
        if name == "conlist" and call.args:
            found = self.type_info(call.args[0], ctx)
            found.is_list = True
            found.constraints = _constraints(call)
        return found

    # --------------------------------------------------------------- classes
    def is_enum(self, cls: ast.ClassDef) -> bool:
        return any((_flatten(b) or [""])[-1].endswith("Enum") for b in cls.bases)

    def enum_members(self, cls: ast.ClassDef) -> dict[str, object]:
        members: dict[str, object] = {}
        for stmt in cls.body:
            if (
                isinstance(stmt, ast.Assign)
                and len(stmt.targets) == 1
                and isinstance(stmt.targets[0], ast.Name)
                and isinstance(stmt.value, ast.Constant)
                and not stmt.targets[0].id.startswith("_")
            ):
                members[stmt.targets[0].id] = stmt.value.value
        return members

    def is_model(self, cls: ast.ClassDef, ctx: object, depth: int = 0) -> bool:
        if depth > 8:
            return False
        for base in cls.bases:
            parts = _flatten(base)
            if not parts:
                continue
            if parts[-1] == "BaseModel":
                return True
            found = self.lookup(ctx, parts)
            if found and self.is_model(found[0], found[1], depth + 1):
                return True
        return False

    def _default(self, node: ast.AST, ctx: object) -> object:
        value = _literal(node)
        if value != UNRESOLVED:
            return value
        parts = _flatten(node)
        if parts and len(parts) >= 2:
            found = self.lookup(ctx, parts[:-1])
            if found and self.is_enum(found[0]):
                return self.enum_members(found[0]).get(parts[-1], UNRESOLVED)
        return UNRESOLVED

    def _opts(self, call: ast.Call, ctx: object) -> _Opts:
        node = call.args[0] if call.args else _kw(call, "default")
        opts = _Opts(constraints=_constraints(call), example=_example(call))
        if node is not None:
            if isinstance(node, ast.Constant) and node.value is Ellipsis:
                return opts
            opts.has_default, opts.required = True, False
            opts.default = self._default(node, ctx)
        elif _kw(call, "default_factory") is not None:
            opts.has_default, opts.required, opts.default = True, False, UNRESOLVED
        return opts

    # -------------------------------------------------------------- endpoints
    def endpoint_params(
        self,
        func: ast.FunctionDef | ast.AsyncFunctionDef | None,
        ctx: object,
        path: str,
        notes: list[str],
    ) -> tuple[list[Param], ModelSpec | None]:
        template = re.findall(r"{([^}:]+)", path)
        params: list[Param] = []
        body: ModelSpec | None = None
        if func is not None:
            for arg, default in self._arguments(func):
                result = self._argument(arg, default, ctx, template, notes)
                if isinstance(result, list):
                    params.extend(result)
                elif isinstance(result, ModelSpec):
                    if body is None:
                        body = result
                    else:
                        notes.append(
                            f"more than one body model; {arg.arg} not generated"
                        )
                elif result is not None:
                    params.append(result)
        else:
            notes.append("handler function not found; parameters not read")
        known = {p.name for p in params}
        for name in template:
            if name not in known:
                params.append(Param(name, "path", "str", True))
        return params, body

    @staticmethod
    def _arguments(
        func: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> list[tuple[ast.arg, ast.expr | None]]:
        args = func.args
        positional = [*args.posonlyargs, *args.args]
        defaults: list[ast.expr | None] = [None] * (
            len(positional) - len(args.defaults)
        )
        defaults.extend(args.defaults)
        pairs = list(zip(positional, defaults))
        pairs.extend(zip(args.kwonlyargs, args.kw_defaults))
        return [(a, d) for a, d in pairs if a.arg not in ("self", "cls")]

    def _argument(
        self,
        arg: ast.arg,
        default: ast.expr | None,
        ctx: object,
        template: list[str],
        notes: list[str],
    ) -> Param | ModelSpec | list[Param] | None:
        t = self.type_info(arg.annotation, ctx)
        if t.name in INJECTED:
            return None
        if t.name == "OAuth2PasswordRequestForm":
            return [
                Param("username", "form", "str", True),
                Param("password", "form", "str", True),
            ]
        calls = ([default] if isinstance(default, ast.Call) else []) + t.metas
        for call in calls:
            if _call_name(call) in ("Depends", "Security"):
                target = _flatten(call.args[0]) if call.args else None
                notes.append(
                    f"dependency {'.'.join(target or ['?'])}: its parameters are not read"
                )
                return None
        kind, opts = None, _Opts()
        for call in calls:
            name = _call_name(call)
            if name in PARAM_FUNCS or name == "Field":
                kind = PARAM_FUNCS.get(name)
                opts = self._opts(call, ctx)
                break
        if kind in ("cookie", "file"):
            notes.append(f"parameter {arg.arg}: {kind} parameters are not generated")
            return None
        if kind is None and default is not None and not calls:
            opts = _Opts(True, self._default(default, ctx), False)
        if t.model and kind in (None, "body"):
            spec = self.model_spec(t.model[0], t.model[1], notes, (), 1)
            spec.is_list = t.is_list
            return spec
        location = kind or ("path" if arg.arg in template else "query")
        if location == "path":
            opts.required = True
        elif t.optional and not opts.has_default and kind is None and not calls:
            opts.required = False
        elif default is None and not calls and not t.optional:
            opts.required = True
        constraints = {**t.constraints, **opts.constraints}
        for meta in t.metas:
            constraints.update(_constraints(meta))
        if t.enum is not None:
            constraints["enum"] = t.enum
        type_name = f"list[{t.name}]" if t.is_list else t.name
        required = opts.required and not (
            t.optional and not opts.has_default and kind is None
        )
        return Param(
            arg.arg,
            location,
            type_name,
            required,
            opts.default if opts.has_default else None,
            constraints,
            opts.example,
        )

    # ----------------------------------------------------------------- models
    def model_spec(
        self,
        cls: ast.ClassDef,
        ctx: object,
        notes: list[str],
        stack: tuple[str, ...],
        depth: int,
    ) -> ModelSpec:
        spec = ModelSpec(cls.name, [], Source(self.rel_of(ctx), cls.lineno))
        for base in cls.bases:
            parts = _flatten(base)
            found = self.lookup(ctx, parts) if parts else None
            if found and self.is_model(found[0], found[1]):
                parent = self.model_spec(found[0], found[1], notes, stack, depth)
                spec.fields.extend(parent.fields)
        for stmt in cls.body:
            if (
                isinstance(stmt, ast.AnnAssign)
                and isinstance(stmt.target, ast.Name)
                and not stmt.target.id.startswith("_")
                and "ClassVar" not in ast.dump(stmt.annotation)
                and stmt.target.id != "model_config"
            ):
                spec.fields.append(
                    self._model_field(stmt, cls, ctx, notes, stack, depth)
                )
        spec.example = self._model_example(cls)
        return spec

    def _model_field(
        self,
        stmt: ast.AnnAssign,
        cls: ast.ClassDef,
        ctx: object,
        notes: list[str],
        stack: tuple[str, ...],
        depth: int,
    ) -> FieldSpec:
        assert isinstance(stmt.target, ast.Name)
        name = stmt.target.id
        t = self.type_info(stmt.annotation, ctx)
        opts = _Opts()
        if isinstance(stmt.value, ast.Call) and _call_name(stmt.value) == "Field":
            opts = self._opts(stmt.value, ctx)
        elif stmt.value is not None:
            opts = _Opts(True, self._default(stmt.value, ctx), False)
        elif t.optional:
            opts.required = False
        constraints = {**t.constraints, **opts.constraints}
        if t.enum is not None:
            constraints["enum"] = t.enum
        spec = FieldSpec(
            name,
            f"list[{t.name}]" if t.is_list else t.name,
            opts.required,
            opts.default if opts.has_default else None,
            constraints,
            opts.example,
            None,
            t.is_list,
            t.enum,
        )
        if t.model:
            inner, inner_ctx = t.model
            if inner.name == cls.name or inner.name in stack:
                spec.unexpanded = True
                notes.append(
                    f"recursive model {inner.name} at field {name}; not expanded"
                )
            elif depth >= DEPTH_LIMIT:
                spec.unexpanded = True
                notes.append(
                    f"model nesting deeper than {DEPTH_LIMIT} at field {name} "
                    f"({inner.name}); not expanded"
                )
            else:
                spec.children = self.model_spec(
                    inner, inner_ctx, notes, (*stack, cls.name), depth + 1
                )
        return spec

    @staticmethod
    def _model_example(cls: ast.ClassDef) -> object:
        extra: object = UNRESOLVED
        for stmt in cls.body:
            if isinstance(stmt, ast.ClassDef) and stmt.name == "Config":
                for inner in stmt.body:
                    if (
                        isinstance(inner, ast.Assign)
                        and isinstance(inner.targets[0], ast.Name)
                        and inner.targets[0].id == "schema_extra"
                    ):
                        extra = _literal(inner.value)
            elif (
                isinstance(stmt, ast.Assign)
                and isinstance(stmt.targets[0], ast.Name)
                and stmt.targets[0].id == "model_config"
                and isinstance(stmt.value, ast.Call)
            ):
                node = _kw(stmt.value, "json_schema_extra")
                if node is not None:
                    extra = _literal(node)
        if isinstance(extra, dict):
            if "example" in extra:
                return extra["example"]
            examples = extra.get("examples")
            if isinstance(examples, list) and examples:
                return examples[0]
        return None
