"""Task 1: FastAPI route and prefix discovery for the bruno-collection skill."""

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
def app_root(tmp_path: Path) -> Path:
    fx.write_app(tmp_path / "repo")
    return tmp_path / "repo"


def by_key(result):
    return {(e.method, e.path): e for e in result.endpoints}


def test_prefix_chain_combined(disc, app_root):
    eps = by_key(disc.discover(app_root))
    assert ("GET", "/api/v1/orders/{order_id}") in eps
    assert ("POST", "/api/v1/orders/") in eps
    assert ("DELETE", "/old/{thing_id}") in eps
    assert ("GET", "/health") in eps


def test_methods_and_tags(disc, app_root):
    eps = by_key(disc.discover(app_root))
    assert eps[("GET", "/api/v1/orders/{order_id}")].tags == ["orders", "detail"]
    assert eps[("GET", "/health")].tags == ["ops"]
    assert eps[("GET", "/api/v1/orders/{order_id}")].function == "get_order"
    assert eps[("GET", "/api/v1/orders/{order_id}")].docstring == "Get one order."


def test_add_api_route_found(disc, app_root):
    eps = by_key(disc.discover(app_root))
    assert ("GET", "/api/v1/orders/export") in eps
    assert ("POST", "/api/v1/orders/export") in eps
    assert eps[("GET", "/api/v1/orders/export")].function == "export_orders"


def test_source_is_relative_file_and_line(disc, app_root):
    ep = by_key(disc.discover(app_root))[("GET", "/api/v1/orders/{order_id}")]
    assert ep.source.file == "app/api/endpoints/orders.py"
    assert ep.source.line == 6  # the decorator line


def test_dynamic_route_listed_as_skipped_with_file_and_line(disc, app_root):
    result = disc.discover(app_root)
    skipped = [s for s in result.skipped if s.source.file.endswith("orders.py")]
    assert len(skipped) == 1
    assert skipped[0].source.line == 24
    assert "dynamic" in skipped[0].reason or "conditional" in skipped[0].reason
    assert ("GET", "/api/v1/orders/a") not in by_key(result)


def test_router_not_included_is_listed(disc, app_root):
    result = disc.discover(app_root)
    reasons = [s.reason for s in result.skipped if s.source.file == "app/unused.py"]
    assert reasons and "not included" in reasons[0]
    assert ("GET", "/never-mounted") not in by_key(result)


def test_syntax_error_module_skipped_not_crash(disc, app_root, tmp_path):
    fx.write_hostile(app_root, tmp_path / "outside")
    result = disc.discover(app_root)
    broken = [s for s in result.skipped if s.source.file == "app/broken.py"]
    assert broken and broken[0].source.line == 1
    assert ("GET", "/health") in by_key(result)


def test_ignored_folders_not_read(disc, app_root, tmp_path):
    fx.write_hostile(app_root, tmp_path / "outside")
    paths = {e.path for e in disc.discover(app_root).endpoints}
    assert "/vendored" not in paths and "/legacy" not in paths


def test_symlink_leaving_repo_not_followed(disc, app_root, tmp_path):
    fx.write_hostile(app_root, tmp_path / "outside")
    result = disc.discover(app_root)
    assert "/outside" not in {e.path for e in result.endpoints}
    skipped_files = {s.source.file for s in result.skipped}
    assert "linked_file.py" in skipped_files
    assert "linked_dir" in skipped_files
    assert all(
        "symlink" in s.reason
        for s in result.skipped
        if s.source.file in ("linked_file.py", "linked_dir")
    )


def test_relative_imports_and_reexport(disc, tmp_path):
    root = tmp_path / "rel"
    fx.write_files(root, fx.RELATIVE_APP_FILES)
    eps = by_key(disc.discover(root))
    assert ("GET", "/shop/items") in eps
    assert eps[("GET", "/shop/items")].tags == ["items"]


def test_three_outcomes(disc, app_root, tmp_path):
    result = disc.discover(app_root)
    lines = result.outcome_lines()
    assert any("found and resolved" in line for line in lines)
    assert any(
        "not statically resolvable" in line and "orders.py:24" in line for line in lines
    )
    empty = tmp_path / "empty"
    empty.mkdir()
    none = disc.discover(empty)
    assert none.app_found is False and none.endpoints == []
    text = " ".join(none.outcome_lines())
    assert "no route discovered" in text and "not proof" in text
    assert "no routes exist" not in text


def test_results_are_deterministic(disc, app_root):
    first = [(e.method, e.path) for e in disc.discover(app_root).endpoints]
    second = [(e.method, e.path) for e in disc.discover(app_root).endpoints]
    assert first == second
    assert first == sorted(first, key=lambda mp: (mp[1], mp[0]))


# ---- review: mounts made inside functions the app module calls, and return keys

FOLLOW_FILES = {
    "svc/__init__.py": "",
    "svc/main.py": (
        "from fastapi import FastAPI\nfrom svc.setup import init\n\n"
        "app = FastAPI()\ninit(app)\n"
    ),
    "svc/setup.py": (
        "def init(app):\n    init_routers(app)\n\n\n"
        "def init_routers(app):\n    from svc.routes import router\n"
        '    app.include_router(router, prefix="/api")\n'
    ),
    "svc/routes.py": (
        "from fastapi import APIRouter\n\nrouter = APIRouter()\n\n\n"
        '@router.post("/phone/get_by_priority")\n'
        "def get_phone_by_priority():\n"
        '    def helper():\n        return {"wrong": 1}\n'
        '    return {"result": 1, "total_rows": 2}\n'
    ),
}


def test_mount_inside_a_followed_function_is_found_and_not_reported(tmp_path):
    disc = load("bruno_discover")
    fx.write_files(tmp_path, FOLLOW_FILES)
    result = disc.discover(tmp_path)
    assert [(e.method, e.path) for e in result.endpoints] == [
        ("POST", "/api/phone/get_by_priority")
    ]
    assert not any("dynamically" in s.reason for s in result.skipped)
    assert result.endpoints[0].return_keys == ["result", "total_rows"]


def test_mount_under_a_condition_or_a_recursive_call_is_still_reported(tmp_path):
    disc = load("bruno_discover")
    files = dict(FOLLOW_FILES)
    files["svc/setup.py"] = (
        "def init(app):\n    init(app)\n    init_routers(app)\n\n\n"
        "def init_routers(app):\n    from svc.routes import router\n"
        '    if True:\n        app.include_router(router, prefix="/api")\n'
    )
    fx.write_files(tmp_path, files)
    result = disc.discover(tmp_path)
    assert result.endpoints == []
    assert any("dynamically" in s.reason for s in result.skipped)
