"""Task 5: endpoint identity, file names, collisions and the add-only plan."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent / "support"))

from bruno_loader import load  # noqa: E402


@pytest.fixture()
def disc():
    return load("bruno_discover")


@pytest.fixture()
def idn():
    return load("bruno_identity")


def make(
    disc, method, path, tags=None, function="handler", params=None, line=1, file="a.py"
):
    return disc.Endpoint(
        method, path, tags or [], function, None, disc.Source(file, line), params or []
    )


def state(idn, files=(), docs=()):
    return idn.ExistingState(set(files), {d.identity: d for d in docs})


def test_identity_drops_converter_and_normalizes_slashes(disc, idn):
    a = make(disc, "GET", "/files/{file_path:path}")
    b = make(disc, "GET", "/files/{file_path}")
    c = make(disc, "GET", "//files//{file_path}/")
    assert (
        idn.identity(a)
        == idn.identity(b)
        == idn.identity(c)
        == "GET /files/{file_path}"
    )
    assert idn.identity(make(disc, "POST", "/api/v1/orders/")) == "POST /api/v1/orders"
    assert idn.identity(make(disc, "GET", "/")) == "GET /"


def test_request_names(disc, idn):
    cases = {
        ("GET", "/api/v1/orders/{order_id}"): "Get orders by id",
        ("POST", "/api/v1/orders/"): "Post orders",
        ("GET", "/health"): "Get health",
        ("DELETE", "/old/{thing_id}"): "Delete old by thing id",
        ("GET", "/files/{file_path:path}"): "Get files by path",
        ("GET", "/"): "Get root",
    }
    for (method, path), expected in cases.items():
        fixed, random_ = idn.request_names(make(disc, method, path))
        assert fixed == f"{expected} (fixed)" and random_ == f"{expected} (random)"


def test_names_are_safe_for_ntfs(disc, idn):
    ep = make(disc, "GET", '/we:ird/na*me?/"x"|<y>', tags=['bad:tag/with"chars'])
    fixed, _ = idn.request_names(ep)
    folder = idn.folder_for(ep)
    for text in (fixed, folder):
        assert not any(ch in text for ch in ':*?"<>|/\\')
        assert text == text.strip() and not text.endswith(".")


def test_folder_is_first_tag_else_first_resource(disc, idn):
    assert (
        idn.folder_for(make(disc, "GET", "/api/v1/orders/x", tags=["orders", "detail"]))
        == "orders"
    )
    assert idn.folder_for(make(disc, "GET", "/api/v1/orders/x")) == "orders"
    assert idn.folder_for(make(disc, "GET", "/")) == "root"


def test_new_endpoints_are_added_with_both_files(disc, idn):
    plan = idn.plan(
        [make(disc, "GET", "/orders/{order_id}", tags=["orders"])], state(idn)
    )
    assert [p.identity for p in plan.add] == ["GET /orders/{order_id}"]
    assert plan.add[0].files == (
        "orders/Get orders by id (fixed).yml",
        "orders/Get orders by id (random).yml",
    )
    assert not (plan.collisions or plan.conflicts or plan.changed or plan.disappeared)


def test_two_identities_one_file_name_write_neither(disc, idn):
    a = make(disc, "GET", "/api/v1/orders/{order_id}", tags=["orders"], line=3)
    b = make(disc, "GET", "/api/v2/orders/{order_id}", tags=["orders"], line=9)
    plan = idn.plan([a, b], state(idn))
    assert plan.add == []
    assert len(plan.collisions) == 1
    collision = plan.collisions[0]
    assert sorted(collision.identities) == sorted([idn.identity(a), idn.identity(b)])
    assert [s.line for s in collision.sources] == [3, 9]
    assert "naming decision" in collision.reason


def test_names_differing_only_in_case_are_a_collision(disc, idn):
    a = make(disc, "GET", "/v1/x", tags=["Orders"])
    b = make(disc, "GET", "/v2/x", tags=["orders"])
    plan = idn.plan([a, b], state(idn))
    assert plan.add == [] and len(plan.collisions) == 1


def test_new_endpoint_whose_file_exists_is_collision_not_overwrite(disc, idn):
    ep = make(disc, "GET", "/orders", tags=["orders"])
    existing = state(idn, files=["orders/Get orders (fixed).yml"])
    plan = idn.plan([ep], existing)
    assert plan.add == []
    assert len(plan.collisions) == 1 and "exists" in plan.collisions[0].reason
    assert plan.collisions[0].files == ["orders/Get orders (fixed).yml"]
    folded = state(idn, files=["ORDERS/get orders (random).yml"])
    assert len(idn.plan([ep], folded).collisions) == 1


def test_same_identity_twice_is_conflict(disc, idn):
    a = make(disc, "GET", "/orders", line=1)
    b = make(disc, "GET", "/orders/", line=7, function="other")
    plan = idn.plan([a, b], state(idn))
    assert plan.add == [] and plan.collisions == []
    assert len(plan.conflicts) == 1
    assert [s.line for s in plan.conflicts[0].sources] == [1, 7]


def test_duplicate_function_names_do_not_matter(disc, idn):
    a = make(disc, "GET", "/orders", function="list_items")
    b = make(disc, "GET", "/products", function="list_items")
    assert len(idn.plan([a, b], state(idn)).add) == 2


def test_known_endpoint_is_left_alone_even_if_its_file_was_renamed(disc, idn):
    ep = make(disc, "GET", "/orders/{order_id}", tags=["orders"], function="get_order")
    doc = idn.DocEntry(
        idn.identity(ep), "get_order", idn.signature(ep), ["orders/My renamed.yml"]
    )
    plan = idn.plan([ep], state(idn, files=["orders/My renamed.yml"], docs=[doc]))
    assert plan.add == [] and plan.collisions == [] and plan.changed == []
    assert plan.unchanged == [idn.identity(ep)]


def test_changed_parameters_are_listed_and_nothing_is_rewritten(disc, idn):
    old = make(disc, "GET", "/orders", params=[disc.Param("q", "query")])
    doc = idn.DocEntry(
        idn.identity(old), "handler", idn.signature(old), ["x/Get orders (fixed).yml"]
    )
    now = make(
        disc,
        "GET",
        "/orders",
        params=[disc.Param("q", "query"), disc.Param("limit", "query")],
    )
    plan = idn.plan([now], state(idn, docs=[doc]))
    assert plan.add == [] and len(plan.changed) == 1
    assert plan.changed[0].identity == "GET /orders"
    assert (
        "limit:query" in plan.changed[0].now
        and "limit:query" not in plan.changed[0].before
    )


def test_changed_path_is_new_plus_disappeared(disc, idn):
    old = make(disc, "GET", "/items", function="list_things")
    doc = idn.DocEntry(
        idn.identity(old), "list_things", [], ["items/Get items (fixed).yml"]
    )
    new = make(disc, "GET", "/products", function="list_things")
    plan = idn.plan([new], state(idn, docs=[doc]))
    assert [p.identity for p in plan.add] == ["GET /products"]
    assert plan.disappeared == ["GET /items"]


def test_changed_method_is_new_plus_disappeared(disc, idn):
    old = make(disc, "GET", "/orders")
    doc = idn.DocEntry(
        idn.identity(old), "handler", [], ["orders/Get orders (fixed).yml"]
    )
    plan = idn.plan([make(disc, "POST", "/orders")], state(idn, docs=[doc]))
    assert [p.identity for p in plan.add] == ["POST /orders"]
    assert plan.disappeared == ["GET /orders"]


def test_possible_rename_is_a_hint_only(disc, idn):
    old = make(
        disc, "GET", "/items", function="list_things", params=[disc.Param("q", "query")]
    )
    doc = idn.DocEntry(
        idn.identity(old),
        "list_things",
        idn.signature(old),
        ["items/Get items (fixed).yml"],
    )
    new = make(
        disc,
        "GET",
        "/products",
        function="list_things",
        params=[disc.Param("q", "query")],
    )
    plan = idn.plan([new], state(idn, docs=[doc]))
    assert plan.possible_renames == [("GET /items", "GET /products")]
    assert [p.identity for p in plan.add] == ["GET /products"]
    assert plan.disappeared == ["GET /items"]


def test_endpoint_in_a_conflict_is_not_reported_as_disappeared(disc, idn):
    a = make(disc, "GET", "/orders")
    doc = idn.DocEntry(idn.identity(a), "handler", [], [])
    plan = idn.plan([a, make(disc, "GET", "/orders/")], state(idn, docs=[doc]))
    assert plan.disappeared == [] and len(plan.conflicts) == 1


# ---- final review fixes


def test_windows_reserved_folder_names_get_a_prefix(disc, idn):
    for tag, expected in (("CON", "_CON"), ("lpt1", "_lpt1"), ("Orders", "Orders")):
        assert idn.folder_for(make(disc, "GET", "/x", tags=[tag])) == expected
    assert idn.folder_for(make(disc, "GET", "/aux/items")) == "_aux"


# ---- review of the action-name change


def test_action_paths_drop_the_method_and_other_paths_keep_it(disc, idn):
    names = {
        ("POST", "/mdt/phone/api/get_by_priority"): "Get phone by priority",
        ("POST", "/phone/search_by_id"): "Search phone by id",
        ("GET", "/orders/{order_id}"): "Get orders by id",
        ("POST", "/orders"): "Post orders",
        ("GET", "/orders/export"): "Export orders",
    }
    for (method, path), expected in names.items():
        assert idn.request_names(make(disc, method, path))[0] == f"{expected} (fixed)"


def test_same_action_path_with_two_methods_is_reported_not_overwritten(disc, idn):
    a = make(disc, "GET", "/orders/export", file="a.py", line=1)
    b = make(disc, "POST", "/orders/export", file="a.py", line=9)
    result = idn.plan([a, b], state(idn))
    assert result.add == [] and len(result.collisions) == 1
    assert set(result.collisions[0].identities) == {
        "GET /orders/export",
        "POST /orders/export",
    }
