"""Fixed sample values and the random-value constraint contract.

Fixed mode takes literal values from the code (docstring example, declared example,
default, enum), never invented ones. Random mode emits Bruno JavaScript that builds
values at send time. A random value either satisfies every constraint this module
supports, or the field gets a visible `TODO` and an `Incomplete` entry: a value that
may violate a declared constraint is never emitted. Python 3.9 and newer, stdlib only.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timezone

from bruno_discover import Endpoint
from bruno_params import UNRESOLVED, FieldSpec, ModelSpec, Param

UTC = timezone.utc  # noqa: UP017 - the helper must also run on Python 3.9
MARKER = "TEST_"
PRELUDE = (
    "const rnd = (a, b) => Math.floor(Math.random() * (b - a + 1)) + a;\n"
    "const pick = (xs) => xs[rnd(0, xs.length - 1)];\n"
    "const chars = (n, set) =>"
    ' Array.from({ length: n }, () => set[rnd(0, set.length - 1)]).join("");\n'
    'const ALNUM = "abcdefghijklmnopqrstuvwxyz0123456789";\n'
)
SIZE_KEYS = ("min_items", "max_items", "min_length", "max_length")
KINDS = {
    "": "str",
    "str": "str",
    "string": "str",
    "int": "int",
    "float": "float",
    "decimal": "float",
    "bool": "bool",
    "uuid": "uuid",
    "date": "date",
    "datetime": "datetime",
    "emailstr": "email",
    "httpurl": "url",
    "anyurl": "url",
    "dict": "dict",
    "any": "str",
}


# ---------------------------------------------------------------------- fixed


@dataclass
class FixedResult:
    value: object
    origin: str  # docstring | example | default | enum | none | todo
    todo: bool = False
    enabled: bool = True
    reason: str = ""


def docstring_examples(doc: str | None) -> dict[str, str]:
    """Read the `Example input parameter` block of a route docstring."""
    if not doc:
        return {}
    lines = doc.splitlines()
    start = next(
        (
            i
            for i, line in enumerate(lines)
            if "example" in line.lower() and "param" in line.lower()
        ),
        None,
    )
    found: dict[str, str] = {}
    for line in lines[start + 1 :] if start is not None else []:
        match = re.match(r"^\s*[-*]?\s*([A-Za-z_][\w.]*)\s*:\s*(.+?)\s*$", line)
        if match:
            found[match.group(1)] = match.group(2)
        elif found:
            break
    return found


def _convert(raw: str, type_name: str) -> object:
    inner = re.fullmatch(r"list\[(.*)\]", type_name)
    if inner:
        return [_convert(part.strip(), inner.group(1)) for part in raw.split(",")]
    try:
        if type_name == "int":
            return int(raw)
        if type_name == "float":
            return float(raw)
    except ValueError:
        return raw
    if type_name == "bool" and raw.lower() in ("true", "false"):
        return raw.lower() == "true"
    return raw


def _known(value: object) -> bool:
    return value is not None and value != UNRESOLVED


def _checked(value: object, origin: str) -> FixedResult:
    if "{{" in json.dumps(value, default=str):
        return FixedResult(
            "TODO",
            "todo",
            True,
            True,
            f"sample value from the {origin} contains '{{{{' which Bruno cannot escape",
        )
    return FixedResult(value, origin)


def fixed_value(
    item: Param | FieldSpec,
    endpoint: Endpoint,
    model_example: dict[str, object] | None = None,
) -> FixedResult:
    """First of: docstring example, declared example, model example, default, enum."""
    raw = docstring_examples(endpoint.docstring).get(item.name)
    if raw is not None:
        return _checked(_convert(raw, item.type_name), "docstring")
    if _known(item.example):
        return _checked(item.example, "example")
    if model_example and _known(model_example.get(item.name)):
        return _checked(model_example[item.name], "model example")
    if _known(item.default):
        return _checked(item.default, "default")
    enum = item.constraints.get("enum")
    if isinstance(enum, list) and enum and _known(enum[0]):
        return _checked(enum[0], "enum")
    if not item.required:
        return FixedResult("", "none", False, enabled=False)
    return FixedResult(
        "TODO", "todo", True, True, "no example, default or enum in the code"
    )


def fixed_body(model: ModelSpec, endpoint: Endpoint) -> tuple[object, list[str]]:
    todos: list[str] = []
    value = _fixed_model(model, endpoint, (), todos)
    return ([value] if model.is_list else value), todos


def _fixed_model(
    model: ModelSpec, endpoint: Endpoint, path: tuple[str, ...], todos: list[str]
) -> dict[str, object]:
    example = model.example if isinstance(model.example, dict) else None
    out: dict[str, object] = {}
    for f in model.fields:
        here = ".".join((*path, f.name))
        if f.children is not None:
            inner = _fixed_model(f.children, endpoint, (*path, f.name), todos)
            out[f.name] = [inner] if f.is_list else inner
        elif f.unexpanded:
            out[f.name] = "TODO"
            todos.append(here)
        else:
            result = fixed_value(f, endpoint, example)
            if result.todo:
                out[f.name] = "TODO"
                todos.append(here)
            elif result.enabled:
                out[f.name] = result.value
    return out


# --------------------------------------------------------------------- random


@dataclass
class Incomplete:
    field: str
    reason: str


@dataclass
class RandomResult:
    script: str
    vars: list[str] = field(default_factory=list)
    incomplete: list[Incomplete] = field(default_factory=list)


def _regex_expr(pattern: str) -> str | None:
    """JS for a string matching `pattern`, for a small safe subset; else None."""
    body = pattern
    if body.startswith("^"):
        body = body[1:]
    if body.endswith("$") and not body.endswith("\\$"):
        body = body[:-1]
    parts: list[str] = []
    i = 0
    while i < len(body):
        ch = body[i]
        if ch == "[":
            end = body.find("]", i + 1)
            if end == -1 or body[i + 1 : i + 2] == "^":
                return None
            charset = _class_chars(body[i + 1 : end])
            i = end + 1
        elif ch == "\\":
            if i + 1 >= len(body):
                return None
            esc = body[i + 1]
            named = {
                "d": "0123456789",
                "w": "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_",
            }.get(esc)
            if named is not None:
                charset = named
            elif esc.isalnum():
                return None
            else:
                charset = esc
            i += 2
        elif ch == ".":
            charset, i = "abcdefghijklmnopqrstuvwxyz0123456789", i + 1
        elif ch in "()|^$*+?{}]":
            return None
        else:
            charset, i = ch, i + 1
        if not charset:
            return None
        quant, i = _quantifier(body, i)
        if quant is None:
            return None
        low, high = quant
        count = str(low) if low == high else f"rnd({low}, {high})"
        parts.append(f"chars({count}, {json.dumps(charset)})")
    return " + ".join(parts) if parts else None


def _class_chars(spec: str) -> str:
    chars: list[str] = []
    i = 0
    while i < len(spec):
        ch = spec[i]
        if ch == "\\" and i + 1 < len(spec):
            esc = spec[i + 1]
            chars.extend("0123456789" if esc == "d" else esc)
            i += 2
        elif i + 2 < len(spec) and spec[i + 1] == "-":
            lo, hi = ord(ch), ord(spec[i + 2])
            if hi < lo or hi - lo > 255:
                return ""
            chars.extend(chr(c) for c in range(lo, hi + 1))
            i += 3
        else:
            chars.append(ch)
            i += 1
    return "".join(dict.fromkeys(chars))


def _quantifier(body: str, i: int) -> tuple[tuple[int, int] | None, int]:
    if i >= len(body):
        return (1, 1), i
    ch = body[i]
    simple = {"*": (0, 5), "+": (1, 5), "?": (0, 1)}
    if ch in simple:
        if body[i + 1 : i + 2] in ("?", "+"):
            return None, i
        return simple[ch], i + 1
    if ch == "{":
        end = body.find("}", i)
        match = (
            re.fullmatch(r"(\d+)(,(\d*))?", body[i + 1 : end]) if end != -1 else None
        )
        if not match:
            return None, i
        low = int(match.group(1))
        high = (
            low
            if match.group(2) is None
            else (int(match.group(3)) if match.group(3) else low + 5)
        )
        return ((low, high) if low <= high <= 50 else None), end + 1
    return (1, 1), i


def _ms(value: object, as_datetime: bool) -> int | None:
    if not isinstance(value, str):
        return None
    try:
        if as_datetime:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=UTC)
            return int(parsed.timestamp() * 1000)
        day = date.fromisoformat(value)
    except ValueError:
        return None
    return int(datetime(day.year, day.month, day.day, tzinfo=UTC).timestamp() * 1000)


class _Gen:
    def __init__(self) -> None:
        self.incomplete: list[Incomplete] = []

    def todo(self, path: str, reason: str) -> str:
        self.incomplete.append(Incomplete(path, reason))
        return '"TODO"'

    def model(self, spec: ModelSpec, prefix: str = "") -> str:
        items = [
            f"{json.dumps(f.name)}: "
            + self.value(
                prefix + f.name,
                f.type_name,
                f.constraints,
                f.is_list,
                f.children,
                f.unexpanded,
            )
            for f in spec.fields
        ]
        return "{ " + ", ".join(items) + " }" if items else "{}"

    def value(
        self,
        path: str,
        type_name: str,
        constraints: dict[str, object],
        is_list: bool = False,
        children: ModelSpec | None = None,
        unexpanded: bool = False,
    ) -> str:
        match = re.fullmatch(r"list\[(.*)\]", type_name)
        if match:
            type_name, is_list = match.group(1), True
        if is_list:
            return self._list(path, type_name, constraints, children, unexpanded)
        return self._item(path, type_name, constraints, children, unexpanded)

    def _list(self, path, type_name, c, children, unexpanded) -> str:
        bad = next((k for k in SIZE_KEYS if k in c and not isinstance(c[k], int)), None)
        if bad:
            return self.todo(path, f"constraint {bad} is not statically resolvable")
        low = c.get("min_items", c.get("min_length", 1))
        high = c.get("max_items", c.get("max_length", int(low) + 2))
        if int(low) > int(high):
            return self.todo(
                path, f"contradictory list size: minimum {low} above maximum {high}"
            )
        item_c = {k: v for k, v in c.items() if k not in SIZE_KEYS}
        if (
            "max_length" in c
            and "max_items" not in c
            and KINDS.get(type_name.lower()) == "str"
        ):
            item_c["max_length"] = c["max_length"]
        item = self._item(path, type_name, item_c, children, unexpanded)
        return f"Array.from({{ length: rnd({low}, {high}) }}, () => ({item}))"

    def _item(self, path, type_name, c, children, unexpanded) -> str:
        if children is not None:
            return self.model(children, path + ".")
        if unexpanded:
            return self.todo(
                path, "model nesting stops here (depth limit or recursion)"
            )
        bad = next((k for k, v in c.items() if v == UNRESOLVED), None)
        if bad:
            return self.todo(path, f"constraint {bad} is not statically resolvable")
        enum = c.get("enum")
        if isinstance(enum, list) and enum:
            if "{{" in json.dumps(enum, default=str):
                return self.todo(
                    path, "an enum member contains '{{' which Bruno cannot escape"
                )
            return f"pick({json.dumps(enum)})"
        kind = KINDS.get(type_name.lower())
        if kind is None:
            return self.todo(path, f"unsupported type {type_name}")
        name = path.rsplit(".", 1)[-1]
        method = getattr(self, f"_{kind}")
        return str(method(path, name, c))

    # -- scalar kinds
    def _str(self, path: str, name: str, c: dict[str, object]) -> str:
        if "pattern" in c:
            if "min_length" in c or "max_length" in c:
                return self.todo(
                    path, "a pattern together with a length limit is not supported"
                )
            expr = _regex_expr(str(c["pattern"]))
            return expr or self.todo(path, f"unsupported pattern {c['pattern']!r}")
        low = c.get("min_length", 1)
        high = c.get("max_length")
        if not isinstance(low, int) or (high is not None and not isinstance(high, int)):
            return self.todo(path, "length limit is not an integer")
        if high is not None and low > high:
            return self.todo(
                path, f"contradictory length: minimum {low} above maximum {high}"
            )
        prefix = MARKER if high is None else MARKER[:high]
        low_len = max(low, len(prefix))
        high_len = high if high is not None else low_len + 8
        count = f"rnd({low_len - len(prefix)}, {high_len - len(prefix)})"
        return f"{json.dumps(prefix)} + chars({count}, ALNUM)"

    def _bounds(
        self, c: dict[str, object]
    ) -> tuple[float | None, float | None, bool, bool] | None:
        """(low, high, low_strict, high_strict), or None if a bound is not a number."""
        keys = [
            "ge"
            if c.get("ge") is not None
            else ("gt" if c.get("gt") is not None else None),
            "le"
            if c.get("le") is not None
            else ("lt" if c.get("lt") is not None else None),
        ]
        numbers: list[float | None] = []
        for key in keys:
            if key is None:
                numbers.append(None)
                continue
            value = c[key]
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                return None
            numbers.append(float(value))
        return numbers[0], numbers[1], keys[0] == "gt", keys[1] == "lt"

    def _int(self, path: str, name: str, c: dict[str, object]) -> str:
        bounds = self._bounds(c)
        if bounds is None:
            return self.todo(path, "bound is not a number")
        low, high, low_strict, high_strict = bounds
        lo = (
            None
            if low is None
            else (math.floor(low) + 1 if low_strict else math.ceil(low))
        )
        hi = (
            None
            if high is None
            else (math.ceil(high) - 1 if high_strict else math.floor(high))
        )
        if lo is None and hi is None:
            idlike = name == "id" or name.endswith("_id")
            lo, hi = (999001, 999999) if idlike else (1, 1000)
        elif lo is None:
            assert hi is not None
            lo = hi - 1000
        elif hi is None:
            hi = lo + 1000
        assert lo is not None and hi is not None
        step = c.get("multiple_of")
        if step is not None:
            if not isinstance(step, int) or step <= 0:
                return self.todo(path, "multiple_of must be a positive integer")
            first, last = math.ceil(lo / step), math.floor(hi / step)
            if first > last:
                return self.todo(path, f"no multiple of {step} between {lo} and {hi}")
            return f"rnd({first}, {last}) * {step}"
        if lo > hi:
            return self.todo(path, f"contradictory bounds: {lo} above {hi}")
        return f"rnd({lo}, {hi})"

    def _float(self, path: str, name: str, c: dict[str, object]) -> str:
        if "multiple_of" in c:
            return self.todo(path, "multiple_of on a float is not supported")
        bounds = self._bounds(c)
        if bounds is None:
            return self.todo(path, "bound is not a number")
        low, high, _, _ = bounds
        if low is None and high is None:
            low, high = 0.0, 1000.0
        elif low is None:
            assert high is not None
            low = high - 1000
        elif high is None:
            high = low + 1000
        assert low is not None and high is not None
        if high - low < 0.2:
            return self.todo(
                path, f"range {low} to {high} is too narrow for a random float"
            )
        return f"Math.round(({low} + ({high} - {low}) * (0.1 + 0.8 * Math.random())) * 100) / 100"

    def _bool(self, path: str, name: str, c: dict[str, object]) -> str:
        return "pick([true, false])"

    def _uuid(self, path: str, name: str, c: dict[str, object]) -> str:
        return '[8, 4, 4, 4, 12].map((n) => chars(n, "0123456789abcdef")).join("-")'

    def _email(self, path: str, name: str, c: dict[str, object]) -> str:
        return '"test_" + chars(rnd(4, 8), ALNUM) + "@example.test"'

    def _url(self, path: str, name: str, c: dict[str, object]) -> str:
        return '"https://example.test/" + chars(rnd(3, 8), ALNUM)'

    def _dict(self, path: str, name: str, c: dict[str, object]) -> str:
        return "{}"

    def _date(
        self, path: str, name: str, c: dict[str, object], full: bool = False
    ) -> str:
        low_key = "ge" if "ge" in c else ("gt" if "gt" in c else None)
        high_key = "le" if "le" in c else ("lt" if "lt" in c else None)
        low_strict, high_strict = low_key == "gt", high_key == "lt"
        day = 0 if full else 86_400_000
        lo = _ms("2020-01-01", full) if low_key is None else _ms(c[low_key], full)
        hi = _ms("2025-12-31", full) if high_key is None else _ms(c[high_key], full)
        if lo is None or hi is None:
            return self.todo(path, "date bound could not be read as an ISO date")
        lo += (1000 if full else day) if low_strict else 0
        hi -= (1000 if full else day) if high_strict else 0
        if lo > hi:
            return self.todo(path, "contradictory date bounds")
        text = "toISOString()" if full else "toISOString().slice(0, 10)"
        return f"new Date(rnd({lo}, {hi})).{text}"

    def _datetime(self, path: str, name: str, c: dict[str, object]) -> str:
        return self._date(path, name, c, full=True)


def _var(prefix: str, name: str) -> str:
    return prefix + re.sub(r"\W", "_", name)


def _wrap(lines: list[str]) -> str:
    return "{\n" + PRELUDE + "\n".join(lines) + "\n}\n"


def random_js(spec: Param | ModelSpec, name_prefix: str = "random_") -> RandomResult:
    """Script for one query/path/header parameter, or for a whole request body."""
    gen = _Gen()
    if isinstance(spec, ModelSpec):
        expr = gen.model(spec)
        if spec.is_list:
            expr = f"Array.from({{ length: rnd(1, 2) }}, () => ({expr}))"
        return RandomResult(_wrap([f"req.setBody({expr});"]), [], gen.incomplete)
    expr = gen.value(spec.name, spec.type_name, spec.constraints)
    var = _var(name_prefix, spec.name)
    return RandomResult(
        _wrap([f"bru.setVar({json.dumps(var)}, {expr});"]), [var], gen.incomplete
    )


def random_request(endpoint: Endpoint, name_prefix: str = "random_") -> RandomResult:
    """One script for the whole request: parameter variables and the body object."""
    gen = _Gen()
    lines: list[str] = []
    names: list[str] = []
    scalars = [p for p in endpoint.params if p.location == "body"]
    for p in endpoint.params:
        if p.location in ("form", "body"):
            continue
        var = _var(name_prefix, p.name)
        lines.append(
            f"bru.setVar({json.dumps(var)}, {gen.value(p.name, p.type_name, p.constraints)});"
        )
        names.append(var)
    if endpoint.body is not None:
        expr = gen.model(endpoint.body)
        if endpoint.body.is_list:
            expr = f"Array.from({{ length: rnd(1, 2) }}, () => ({expr}))"
        lines.append(f"req.setBody({expr});")
        if scalars:
            gen.incomplete.append(
                Incomplete(
                    "body",
                    "embedded body parameters together with a model body are not supported",
                )
            )
    elif scalars:
        items = [
            f"{json.dumps(p.name)}: {gen.value(p.name, p.type_name, p.constraints)}"
            for p in scalars
        ]
        lines.append("req.setBody({ " + ", ".join(items) + " });")
    return RandomResult(_wrap(lines), names, gen.incomplete)
