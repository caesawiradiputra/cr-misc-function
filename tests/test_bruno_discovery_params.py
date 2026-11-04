"""Task 2: parameters, models and constraints for the bruno-collection skill."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent / "support"))

import bruno_fixtures as fx  # noqa: E402
from bruno_loader import load  # noqa: E402


@pytest.fixture()
def disc():
    return load("bruno_discover")


@pytest.fixture()
def eps(disc, tmp_path):
    root = tmp_path / "shop_repo"
    fx.write_files(root, fx.PARAMS_APP_FILES)
    return {(e.method, e.path): e for e in disc.discover(root).endpoints}


def param(ep, name):
    return next(p for p in ep.params if p.name == name)


def field(model, name):
    return next(f for f in model.fields if f.name == name)


def test_query_required_and_optional(eps):
    ep = eps[("GET", "/items/{item_id}")]
    assert param(ep, "q").location == "query" and param(ep, "q").required is True
    limit = param(ep, "limit")
    assert limit.required is False and limit.default == 10
    tag = param(ep, "tag")
    assert tag.required is False and tag.type_name == "str" and tag.default is None
    assert param(ep, "maybe").required is False
    assert param(ep, "x_token").location == "header"
    assert param(ep, "x_token").required is False
    names = {p.name for p in ep.params}
    assert "request" not in names and "db" not in names
    assert any("get_db" in note and "not read" in note for note in ep.notes)


def test_constraints_read(eps):
    ep = eps[("GET", "/items/{item_id}")]
    assert param(ep, "item_id").constraints == {"ge": 1, "le": 999}
    assert param(ep, "item_id").example == 42
    assert param(ep, "q").constraints == {
        "min_length": 2,
        "max_length": 10,
        "pattern": "^[a-z]+$",
    }
    assert param(ep, "limit").constraints == {"gt": 0, "lt": 100, "multiple_of": 5}
    assert param(ep, "tags").type_name == "list[str]"
    assert param(ep, "tags").constraints == {"max_length": 5}
    assert param(ep, "n").constraints == {"ge": 1} and param(ep, "n").type_name == "int"
    assert param(ep, "size").constraints == {"ge": 1, "le": 10}
    assert param(ep, "size").type_name == "int"
    unresolved = param(ep, "z").constraints["max_length"]
    assert unresolved == "<unresolved>"


def test_enum_and_literal(eps):
    ep = eps[("GET", "/items/{item_id}")]
    color = param(ep, "color")
    assert color.constraints["enum"] == ["red", "blue"] and color.default == "red"
    mode = param(ep, "mode")
    assert mode.constraints["enum"] == ["fast", "slow"] and mode.type_name == "str"
    assert mode.default == "fast"


def test_pydantic_v1_and_v2_models_parse(eps):
    v1 = eps[("POST", "/customers")].body
    assert v1.name == "Customer"
    assert field(v1, "name").constraints == {"max_length": 30}
    assert field(v1, "name").example == "Ann"
    age = field(v1, "age")
    assert age.required is False and age.default == 18
    assert age.constraints == {"ge": 0, "le": 120}
    nick = field(v1, "nickname")
    assert nick.required is False and nick.default is None
    assert v1.example == {"name": "Ann", "age": 30}
    v2 = eps[("POST", "/v2")].body
    assert field(v2, "name").required is True
    assert field(v2, "name").example == "Bob"
    assert v2.example == {"name": "Bob"}


def test_nested_model_and_list(eps):
    body = eps[("POST", "/customers")].body
    address = field(body, "address")
    assert address.children is not None and address.children.name == "Address"
    assert field(address.children, "city").constraints == {
        "min_length": 1,
        "max_length": 20,
    }
    previous = field(body, "previous")
    assert previous.is_list is True and previous.children.name == "Address"
    bulk = eps[("POST", "/bulk")].body
    assert bulk.name == "Customer" and bulk.is_list is True


def test_path_converter(eps):
    ep = eps[("GET", "/files/{file_path:path}")]
    fp = param(ep, "file_path")
    assert fp.location == "path" and fp.type_name == "str" and fp.required is True


def test_scalar_body_param(eps):
    ep = eps[("PUT", "/scalar-body")]
    note = param(ep, "note")
    assert note.location == "body" and note.constraints == {"max_length": 50}
    assert ep.body is None


def test_recursive_model_stops_and_is_reported(eps):
    ep = eps[("POST", "/nodes")]
    child = field(ep.body, "child")
    assert child.children is None
    assert any("recursive" in n and "Node" in n for n in ep.notes)


def test_nesting_deeper_than_3_stops_and_is_reported(eps):
    ep = eps[("POST", "/deep")]
    l3 = field(field(ep.body, "l2").children, "l3").children
    assert l3.name == "L3"
    assert field(l3, "l4").children is None
    assert any("deeper than 3" in n for n in ep.notes)
