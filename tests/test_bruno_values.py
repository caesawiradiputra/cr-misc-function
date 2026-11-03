"""Task 4: fixed values and the random constraint contract."""

from __future__ import annotations

import importlib
import json
import re
import shutil
import subprocess
import sys
import types
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent / "support"))

import bruno_fixtures as fx  # noqa: E402
from bruno_loader import load  # noqa: E402

MOCK = Path(__file__).parent / "support" / "bru_mock.js"
needs_node = pytest.mark.skipif(
    shutil.which("node") is None, reason="node is not installed"
)


@pytest.fixture()
def disc():
    return load("bruno_discover")


@pytest.fixture()
def vals():
    return load("bruno_values")


def endpoint(disc, doc=None, params=None, body=None):
    return disc.Endpoint(
        "GET", "/x", [], "f", doc, disc.Source("a.py", 1), params or [], body
    )


# --------------------------------------------------------------------- fixed


DOC = """## Example input parameter
- asset_code             : MTRK.ATHLETE.125
- manufacturing_year     : 2011
- region                 : Bandung
"""


def test_fixed_order(disc, vals):
    P = disc.Param
    ep = endpoint(disc, DOC)
    doc_wins = P("asset_code", "query", "str", True, "dflt", {}, "ex")
    assert vals.fixed_value(doc_wins, ep).value == "MTRK.ATHLETE.125"
    assert vals.fixed_value(doc_wins, ep).origin == "docstring"
    year = vals.fixed_value(P("manufacturing_year", "query", "int", False), ep)
    assert year.value == 2011 and isinstance(year.value, int)
    only_example = vals.fixed_value(P("a", "query", "str", True, None, {}, "EX"), ep)
    assert (only_example.value, only_example.origin) == ("EX", "example")
    dflt = vals.fixed_value(P("b", "query", "int", False, 5), ep)
    assert (dflt.value, dflt.origin) == (5, "default")
    enum = vals.fixed_value(
        P("c", "query", "str", True, None, {"enum": ["red", "blue"]}), ep
    )
    assert (enum.value, enum.origin) == ("red", "enum")
    todo = vals.fixed_value(P("d", "query", "str", True), ep)
    assert todo.value == "TODO" and todo.todo is True and todo.enabled is True
    unresolved = vals.fixed_value(P("e", "query", "str", True, "<unresolved>"), ep)
    assert unresolved.todo is True


def test_optional_without_value_is_added_disabled(disc, vals):
    result = vals.fixed_value(disc.Param("opt", "query", "str", False), endpoint(disc))
    assert result.enabled is False and result.todo is False


def test_value_with_double_braces_becomes_todo(disc, vals):
    P = disc.Param
    ep = endpoint(disc, "Example input parameter\n- note : hello {{secret}}\n")
    from_doc = vals.fixed_value(P("note", "query", "str", True), ep)
    assert from_doc.value == "TODO" and from_doc.todo and "{{" in from_doc.reason
    from_example = vals.fixed_value(
        P("x", "query", "str", True, None, {}, "a {{b}}"), ep
    )
    assert from_example.todo is True


def test_fixed_body_nested_and_todos(disc, vals):
    F, M = disc.FieldSpec, disc.ModelSpec
    inner = M(
        "Inner", [F("city", "str", True, None, {}, "Jakarta")], disc.Source("m.py", 1)
    )
    model = M(
        "Body",
        [
            F("name", "str", True),
            F("age", "int", False, 18),
            F("nick", "str", False),
            F("addr", "Inner", True, children=inner),
            F("prev", "list[Inner]", False, children=inner, is_list=True),
            F("kind", "str", True, constraints={"enum": ["a", "b"]}),
        ],
        disc.Source("m.py", 1),
        example={"name": "Ann"},
    )
    value, todos = vals.fixed_body(model, endpoint(disc))
    assert value == {
        "name": "Ann",
        "age": 18,
        "addr": {"city": "Jakarta"},
        "prev": [{"city": "Jakarta"}],
        "kind": "a",
    }
    assert todos == []
    missing = M("B2", [F("must", "str", True)], disc.Source("m.py", 1))
    value2, todos2 = vals.fixed_body(missing, endpoint(disc))
    assert value2 == {"must": "TODO"} and todos2 == ["must"]


# -------------------------------------------------------------------- random

MODELS = """
from datetime import date, datetime
from enum import Enum
from typing import List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class Color(str, Enum):
    red = "red"
    blue = "blue"


class Inner(BaseModel):
    code: str = Field(..., min_length=3, max_length=3)
    score: float = Field(..., ge=0, le=1)


class Other(BaseModel):
    code: str = Field(..., min_length=6, max_length=6)


class Payload(BaseModel):
    name: str = Field(..., min_length=2, max_length=4)
    short: str = Field(..., min_length=1, max_length=2)
    tiny: str = Field(..., max_length=1)
    free: str
    count: int = Field(..., ge=5, le=9)
    step: int = Field(..., ge=10, le=100, multiple_of=10)
    above: int = Field(..., gt=0, lt=3)
    ratio: float = Field(..., gt=0, lt=1)
    flag: bool
    color: Color
    mode: Literal["a", "b"]
    when: date
    stamp: datetime
    ident: UUID
    tags: List[str] = Field(..., @LMIN@=2, @LMAX@=3)
    inner: Inner
    inners: List[Inner] = []
    other: Other
    plate: str = Field(..., @PAT@="^[A-Z]{2}[0-9]{3}$")
    opt: Optional[int] = Field(None, ge=1, le=2)
"""

BAD = """
from pydantic import BaseModel, Field


class Bad(BaseModel):
    a: str = Field(..., min_length=5, max_length=2)
    b: str = Field(..., @PAT@="(a|b)+")
    c: int = Field(..., ge=5, le=1)
    d: int = Field(..., ge=1, le=9, multiple_of=20)
    e: float = Field(..., ge=0, le=100, multiple_of=0.5)
    f: str = Field(..., @PAT@="^[a-z]+$", max_length=3)
    g: str = Field(..., @PAT@="[^a]")
    ok: int = Field(..., ge=1, le=3)
"""

RX = """
from pydantic import BaseModel, Field


class Rx(BaseModel):
    plate: str = Field(..., @PAT@="^[A-Z]{2}[0-9]{3}$")
    month: str = Field(..., @PAT@="^\\\\d{4}-\\\\d{2}$")
    word: str = Field(..., @PAT@="^[a-z]+$")
    mixed: str = Field(..., @PAT@="^ab?c*d{2,3}$")
"""

APP = """
from fastapi import FastAPI

from pkg.models import {model}

app = FastAPI()


@app.post("/p")
def p(body: {model}):
    return {{}}
"""


def pydantic_mod(variant: str):
    try:
        mod = importlib.import_module("pydantic.v1" if variant == "v1" else "pydantic")
    except Exception:
        pytest.skip(f"pydantic {variant} is not importable here")
    if variant == "v2" and not hasattr(mod, "model_validator"):
        pytest.skip("pydantic v2 is not installed")
    return mod


def render(src: str, variant: str) -> str:
    v1 = variant == "v1"
    return (
        src.replace("@PAT@", "regex" if v1 else "pattern")
        .replace("@LMIN@", "min_items" if v1 else "min_length")
        .replace("@LMAX@", "max_items" if v1 else "max_length")
    )


def discover_model(disc, tmp_path, src: str, model: str, variant: str):
    root = tmp_path / f"repo_{variant}_{model}"
    text = render(src, variant)
    fx.write_files(
        root,
        {
            "pkg/__init__.py": "",
            "pkg/models.py": text,
            "pkg/main.py": APP.format(model=model),
        },
    )
    ep = disc.discover(root).endpoints[0]
    return ep, text


def run_js(script: str, iterations: int = 1, env: str = "DEV"):
    payload = json.dumps({"script": script, "iterations": iterations, "env": env})
    done = subprocess.run(
        ["node", str(MOCK)], input=payload, capture_output=True, text=True, timeout=60
    )
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout)


def bodies(result, runs: int = 1):
    """Request bodies as Bruno sends them: the Body tab text with each `{{var}}` replaced by
    the variable the before-request script set (raw insertion, no escaping), or the
    `req.setBody` value for list bodies."""
    out = []
    for run in run_js(result.script, runs):
        if result.body_template is None:
            out.append(run["body"])
        else:
            values: dict[str, object] = run["vars"]

            def fill(m: re.Match[str], values: dict[str, object] = values) -> str:
                return str(values[m.group(1)])

            out.append(json.loads(re.sub(r"\{\{(\w+)\}\}", fill, result.body_template)))
    return out


def validator(variant: str, text: str, model: str):
    mod = pydantic_mod(variant)
    text = text.replace("from pydantic import", f"from {mod.__name__} import")
    module = types.ModuleType(f"bruno_models_{variant}_{model}")
    sys.modules[module.__name__] = module
    exec(compile(text, module.__name__, "exec"), module.__dict__)  # noqa: S102 - test-only fixture source
    cls = getattr(module, model)
    return cls.parse_obj if variant == "v1" else cls.model_validate


@needs_node
@pytest.mark.parametrize("variant", ["v2", "v1"])
def test_supported_constraints_hold(disc, vals, tmp_path, variant):
    ep, text = discover_model(disc, tmp_path, MODELS, "Payload", variant)
    check = validator(variant, text, "Payload")
    result = vals.random_request(ep)
    assert result.incomplete == [], result.incomplete
    all_bodies = bodies(result, 400)
    for body in all_bodies:
        check(body)
        assert body["short"] and len(body["short"]) <= 2
        assert len(body["tiny"]) == 1
        assert 2 <= len(body["name"]) <= 4
        assert body["step"] % 10 == 0
    assert any(b["inners"] for b in all_bodies)
    assert {b["count"] for b in all_bodies} == {5, 6, 7, 8, 9}


@needs_node
@pytest.mark.parametrize("variant", ["v2", "v1"])
def test_regex_subset_supported(disc, vals, tmp_path, variant):
    ep, text = discover_model(disc, tmp_path, RX, "Rx", variant)
    check = validator(variant, text, "Rx")
    result = vals.random_request(ep)
    assert result.incomplete == [], result.incomplete
    for body in bodies(result, 200):
        check(body)


@needs_node
@pytest.mark.parametrize("variant", ["v2"])
def test_unsupported_or_contradictory_gives_todo_and_incomplete(
    disc, vals, tmp_path, variant
):
    ep, _ = discover_model(disc, tmp_path, BAD, "Bad", variant)
    result = vals.random_request(ep)
    assert {i.field for i in result.incomplete} == {"a", "b", "c", "d", "e", "f", "g"}
    assert all(i.reason for i in result.incomplete)
    body = bodies(result, 5)[0]
    assert all(body[k] == "TODO" for k in "abcdefg")
    assert body["ok"] in (1, 2, 3)


@needs_node
def test_marker_prefix_and_no_real_looking_pii(disc, vals):
    P = disc.Param
    free = vals.random_js(P("note", "query", "str", True))
    ident = vals.random_js(P("order_id", "query", "int", True))
    ranged = vals.random_js(P("n", "query", "int", True, None, {"ge": 1, "le": 3}))
    out = run_js(free.script + ident.script + ranged.script, 50)
    assert all(r["vars"]["random_note"].startswith("TEST_") for r in out)
    assert all(999000 <= r["vars"]["random_order_id"] <= 999999 for r in out)
    assert all(r["vars"]["random_n"] in (1, 2, 3) for r in out)
    assert free.vars == ["random_note"]


@needs_node
def test_query_params_use_one_variable_each(disc, vals):
    ep = endpoint(
        disc,
        params=[
            disc.Param(
                "q", "query", "str", True, None, {"min_length": 3, "max_length": 8}
            ),
            disc.Param("tags", "query", "list[str]", True, None, {"max_items": 2}),
        ],
    )
    result = vals.random_request(ep)
    assert result.vars == ["random_q", "random_tags"]
    for run in run_js(result.script, 100):
        assert 3 <= len(run["vars"]["random_q"]) <= 8
        assert 1 <= len(run["vars"]["random_tags"]) <= 2
        assert run["body"] is None


@needs_node
def test_depth_limit_gives_todo(disc, vals, tmp_path):
    root = tmp_path / "deep"
    fx.write_files(root, fx.PARAMS_APP_FILES)
    eps = {(e.method, e.path): e for e in disc.discover(root).endpoints}
    result = vals.random_request(eps[("POST", "/deep")])
    assert [i.field for i in result.incomplete] == ["l2.l3.l4"]
    body = bodies(result, 3)[0]
    assert body["l2"]["l3"]["l4"] == "TODO"


@needs_node
def test_object_body_is_written_with_variables_and_a_list_body_uses_set_body(
    disc, vals, tmp_path
):
    root = tmp_path / "bodyobj"
    fx.write_files(root, fx.PARAMS_APP_FILES)
    eps = {(e.method, e.path): e for e in disc.discover(root).endpoints}
    result = vals.random_request(eps[("POST", "/customers")])
    assert (
        result.body_template is not None and "{{random_name}}" in result.body_template
    )
    assert "req.setBody" not in result.script
    body = bodies(result, 20)[0]
    assert isinstance(body["address"], dict) and isinstance(body["previous"], list)
    assert 1 <= len(body["name"]) <= 30
    bulk = vals.random_request(eps[("POST", "/bulk")])
    assert bulk.body_template is None and "req.setBody" in bulk.script
    assert isinstance(bodies(bulk, 1)[0], list)


@needs_node
def test_same_field_name_in_two_models_no_collision(disc, vals, tmp_path):
    ep, _ = discover_model(disc, tmp_path, MODELS, "Payload", "v2")
    runs = bodies(vals.random_request(ep), 100)
    assert all(len(b["inner"]["code"]) == 3 for b in runs)
    assert all(len(b["other"]["code"]) == 6 for b in runs)


@needs_node
def test_date_and_datetime_bounds_are_respected(disc, vals):
    P = disc.Param
    day = vals.random_js(
        P("d", "query", "date", True, None, {"ge": "2024-03-01", "lt": "2024-03-05"})
    )
    stamp = vals.random_js(
        P(
            "t",
            "query",
            "datetime",
            True,
            None,
            {"gt": "2024-03-01T00:00:00Z", "le": "2024-03-01T00:00:10Z"},
        )
    )
    assert day.incomplete == [] and stamp.incomplete == []
    for run in run_js(day.script + stamp.script, 200):
        assert "2024-03-01" <= run["vars"]["random_d"] <= "2024-03-04"
        assert (
            "2024-03-01T00:00:01"
            <= run["vars"]["random_t"]
            <= "2024-03-01T00:00:10.999Z"
        )
    bad = vals.random_js(P("x", "query", "date", True, None, {"ge": "not-a-date"}))
    assert [i.field for i in bad.incomplete] == ["x"]


# ---- final review fixes


def test_enum_member_with_double_brace_is_todo_in_random_mode():
    val = load("bruno_values")
    disc = load("bruno_discover")
    p = disc.Param("sel", "query", "str", True, None, {"enum": ["ok", "{{enumEvil}}"]})
    ep = disc.Endpoint("GET", "/x", [], "h", None, disc.Source("a.py", 1), [p])
    res = val.random_request(ep)
    assert "{{" not in res.script
    assert any(i.field == "sel" for i in res.incomplete)


# ---- review of the body-in-the-Body-tab change


@needs_node
def test_body_field_never_shares_a_variable_with_a_query_parameter(disc, vals):
    f = disc.FieldSpec("limit", "str", True, None, {"max_length": 3})
    model = disc.ModelSpec("B", [f], disc.Source("a.py", 1))
    q = disc.Param("limit", "query", "int", True, None, {"ge": 1, "le": 5})
    ep = disc.Endpoint("POST", "/x", [], "h", None, disc.Source("a.py", 2), [q], model)
    result = vals.random_request(ep)
    assert len(result.vars) == len(set(result.vars)) == 2
    run = run_js(result.script, 50)
    assert all(1 <= r["vars"]["random_limit"] <= 5 for r in run)
    assert all(len(b["limit"]) <= 3 for b in bodies(result, 50))


def test_enum_value_with_double_brace_in_a_body_field_is_todo(disc, vals):
    f = disc.FieldSpec("kind", "str", True, None, {"enum": ["ok", "{{evil}}"]})
    model = disc.ModelSpec("B", [f], disc.Source("a.py", 1))
    ep = disc.Endpoint("POST", "/x", [], "h", None, disc.Source("a.py", 2), [], model)
    result = vals.random_request(ep)
    assert "{{evil}}" not in result.script and "{{evil}}" not in (
        result.body_template or ""
    )
    assert [i.field for i in result.incomplete] == ["kind"]


# ---- shared helpers through globalThis (probe in Bruno 4.3.0, 2026-11-03)


@needs_node
def test_shared_helpers_script_and_central_request_script_work_together(disc, vals):
    p = disc.Param("n", "query", "int", True, None, {"ge": 1, "le": 3})
    ep = endpoint(disc, params=[p])
    central = vals.random_request(ep, central=True)
    assert "globalThis.__lib" in central.script and "const rnd" not in central.script
    inline = vals.random_request(ep)
    assert "const rnd" in inline.script and "globalThis" not in inline.script
    # the collection script and the request script are separate scripts that share globalThis
    first = (
        f"new Function('bru', 'req', {json.dumps(vals.HELPERS_SCRIPT)})(bru, req);\n"
    )
    runs = run_js(first + central.script, 30)
    assert all(r["vars"]["random_n"] in (1, 2, 3) for r in runs)
