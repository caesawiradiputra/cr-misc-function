"""Task 6: render the collection files and write them add-only."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent / "support"))

from bruno_fixtures import write_app  # noqa: E402
from bruno_loader import load  # noqa: E402


@pytest.fixture()
def disc():
    return load("bruno_discover")


@pytest.fixture()
def ren():
    return load("bruno_render")


@pytest.fixture()
def launch():
    return load("bruno_launch")


def ep(disc, method="GET", path="/items", params=None, body=None, doc=None, tags=None):
    return disc.Endpoint(
        method,
        path,
        tags or [],
        "handler",
        doc,
        disc.Source("app/x.py", 3),
        params or [],
        body,
    )


def result(disc, endpoints, auth=None, token=None, skipped=None):
    return disc.DiscoveryResult(True, endpoints, skipped or [], auth, token)


def local(launch, url="http://localhost:5000"):
    return launch.LaunchResult(url, None, [])


def scalar(text, key):
    """Value of the first `key: "..."` line, decoded from its JSON-style quoting."""
    for line in text.splitlines():
        stripped = line.strip().lstrip("- ")
        if stripped.startswith(key + ": "):
            return json.loads(stripped[len(key) + 2 :])
    raise AssertionError(f"{key} not found in:\n{text}")


def app_result(tmp_path, disc):
    write_app(tmp_path)
    return disc.discover(tmp_path)


def test_layout_matches_spec(tmp_path, disc, ren, launch):
    r = ren.render_collection(app_result(tmp_path, disc), "orders", local(launch))
    files = r.files
    assert {"opencollection.yml", ".gitignore"} <= set(files)
    assert {f"environments/{e}.yml" for e in ("LOCAL", "DEV", "PROD")} <= set(files)
    assert "orders/folder.yml" in files
    assert "orders/Get orders by id (fixed).yml" in files
    assert "orders/Get orders by id (random).yml" in files
    assert not any(p.startswith("auth/") for p in files)
    root = files["opencollection.yml"]
    assert "- docs" in root and "- node_modules" in root and "- .git" in root
    ignore = files[".gitignore"].splitlines()
    assert ".env*" in ignore and "node_modules/" in ignore and ".DS_Store" in ignore


def test_environments_identical_variable_names_secrets_empty(disc, ren, launch):
    auth = disc.AuthFinding("api_key_header", "apikey", disc.Source("m.py", 1))
    r = ren.render_collection(result(disc, [ep(disc)], auth), "svc", local(launch))
    names = {}
    for env in ("LOCAL", "DEV", "PROD"):
        text = r.files[f"environments/{env}.yml"]
        lines = [x.strip() for x in text.splitlines()]
        names[env] = [x for x in lines if x.startswith(("- name:", "name:"))][1:]
        assert "- secret: true" in lines
        secret_block = text.split("- secret: true")[1].split("- name:")[0]
        assert "value:" not in secret_block
    assert names["LOCAL"] == names["DEV"] == names["PROD"]
    assert any("apiKey" in n for n in names["DEV"])


def test_local_base_url_comes_from_launch_settings_and_dev_prod_are_placeholders(
    disc, ren, launch
):
    r = ren.render_collection(
        result(disc, [ep(disc)]), "svc", local(launch, "http://localhost:5123")
    )
    assert scalar(r.files["environments/LOCAL.yml"], "value") == (
        "http://localhost:5123"
    )
    assert scalar(r.files["environments/DEV.yml"], "value") == "https://<dev-host>"
    assert scalar(r.files["environments/PROD.yml"], "value") == "https://<prod-host>"
    joined = " ".join(r.placeholders)
    assert "DEV" in joined and "PROD" in joined


def test_base_url_description_mentions_proxy_prefix(disc, ren, launch):
    r = ren.render_collection(result(disc, [ep(disc)]), "svc", local(launch))
    for env in ("DEV", "PROD"):
        text = r.files[f"environments/{env}.yml"].lower()
        assert "proxy" in text and "prefix" in text
    assert any("proxy" in p.lower() for p in r.placeholders)


def test_request_urls_use_baseUrl_and_prefix(tmp_path, disc, ren, launch):
    r = ren.render_collection(app_result(tmp_path, disc), "orders", local(launch))
    text = r.files["orders/Get orders by id (fixed).yml"]
    assert scalar(text, "url") == "{{baseUrl}}/api/v1/orders/:order_id"
    assert "type: path" in text


def test_fixed_has_no_script_random_has_before_request_script(disc, ren, launch):
    p = disc.Param("limit", "query", "int", True, None, {"ge": 1, "le": 5})
    r = ren.render_collection(
        result(disc, [ep(disc, params=[p], doc="Example input parameter:\nlimit: 3")]),
        "svc",
        local(launch),
    )
    fixed = next(t for k, t in r.files.items() if k.endswith("(fixed).yml"))
    rand = next(t for k, t in r.files.items() if k.endswith("(random).yml"))
    assert "scripts" not in fixed
    assert "type: before-request" in rand
    assert 'bru.setVar("random_limit"' in rand
    assert "{{random_limit}}" in rand
    assert '"3"' in fixed


def test_auth_header_value_is_a_variable(disc, ren, launch):
    auth = disc.AuthFinding("api_key_header", "apikey", disc.Source("m.py", 1))
    r = ren.render_collection(result(disc, [ep(disc)], auth), "svc", local(launch))
    for key, text in r.files.items():
        if key.startswith("items/") and key.endswith(").yml"):
            assert "name: apikey" in text
            assert 'value: "{{apiKey}}"' in text
    bearer = disc.AuthFinding("bearer", None, disc.Source("m.py", 1))
    r2 = ren.render_collection(result(disc, [ep(disc)], bearer), "svc", local(launch))
    text = next(t for k, t in r2.files.items() if k.endswith("(fixed).yml"))
    assert "name: Authorization" in text
    assert 'value: "Bearer {{bearerToken}}"' in text
    assert "token:" not in text
    assert "bearerToken" in r2.files["environments/DEV.yml"]


def test_api_key_query_adds_a_query_parameter(disc, ren, launch):
    auth = disc.AuthFinding("api_key_query", "api_key", disc.Source("m.py", 1))
    r = ren.render_collection(result(disc, [ep(disc)], auth), "svc", local(launch))
    text = next(t for k, t in r.files.items() if k.endswith("(fixed).yml"))
    assert "name: api_key" in text and 'value: "{{apiKey}}"' in text
    assert "?api_key={{apiKey}}" in scalar(text, "url")


@pytest.mark.parametrize(
    "sample",
    ["a: b", 'say "hi"', "line1\nline2", "# not a comment", "- leading dash", "x #y"],
)
def test_yaml_unsafe_sample_values_quoted(sample, disc, ren, launch):
    p = disc.Param("q", "query", "str", True, sample)
    r = ren.render_collection(
        result(disc, [ep(disc, params=[p])]), "svc", local(launch)
    )
    text = next(t for k, t in r.files.items() if k.endswith("(fixed).yml"))
    assert scalar(text.split("params:")[1], "value") == sample


def test_double_brace_sample_becomes_todo_and_is_reported(disc, ren, launch):
    p = disc.Param("q", "query", "str", True, "{{secret}}")
    r = ren.render_collection(
        result(disc, [ep(disc, params=[p])]), "svc", local(launch)
    )
    text = next(t for k, t in r.files.items() if k.endswith("(fixed).yml"))
    assert "{{secret}}" not in text
    assert scalar(text.split("params:")[1], "value") == "TODO"
    assert any("q" in t for t in r.todos)


def test_name_safety(tmp_path, disc, ren, launch):
    for bad in ("my repo", "..", "a/b", 'x:y*z?"<>|', "con", ""):
        name = ren.collection_dir_name(bad)
        assert name and "/" not in name and "\\" not in name
        assert not set('<>:"|?*').intersection(name)
        assert name not in {".", ".."} and name.upper() != "CON"
        assert (tmp_path / name).resolve().parent == tmp_path.resolve()
    r = ren.render_collection(result(disc, [ep(disc)]), 'we"ird: name', local(launch))
    assert scalar(r.files["opencollection.yml"], "name") == 'we"ird: name'


def test_optional_param_without_example_disabled_in_fixed_filled_in_random(
    disc, ren, launch
):
    p = disc.Param("tag", "query", "str", False, None, {})
    r = ren.render_collection(
        result(disc, [ep(disc, params=[p])]), "svc", local(launch)
    )
    fixed = next(t for k, t in r.files.items() if k.endswith("(fixed).yml"))
    rand = next(t for k, t in r.files.items() if k.endswith("(random).yml"))
    block = fixed.split("name: tag")[1].split("auth:")[0]
    assert "disabled: true" in block
    assert "disabled" not in rand
    assert "{{random_tag}}" in rand
    assert "tag=" not in scalar(fixed, "url")


def test_json_body_fixed_and_random(disc, ren, launch):
    f = disc.FieldSpec("name", "str", True, "Ann")
    model = disc.ModelSpec("C", [f], disc.Source("m.py", 1))
    r = ren.render_collection(
        result(disc, [ep(disc, "POST", "/c", body=model)]), "svc", local(launch)
    )
    fixed = next(t for k, t in r.files.items() if k.endswith("(fixed).yml"))
    rand = next(t for k, t in r.files.items() if k.endswith("(random).yml"))
    assert "type: json" in fixed and '"name": "Ann"' in fixed
    assert "req.setBody(" in rand and "type: json" in rand


def test_form_params_become_form_body(disc, ren, launch):
    p = disc.Param("user", "form", "str", True, "ann")
    r = ren.render_collection(
        result(disc, [ep(disc, "POST", "/f", params=[p])]), "svc", local(launch)
    )
    fixed = next(t for k, t in r.files.items() if k.endswith("(fixed).yml"))
    rand = next(t for k, t in r.files.items() if k.endswith("(random).yml"))
    assert "type: form-urlencoded" in fixed
    assert "{{random_user}}" in rand and 'bru.setVar("random_user"' in rand


def test_settings_defaults_and_flat_layout(disc, ren, launch):
    r = ren.render_collection(result(disc, [ep(disc)]), "svc", local(launch))
    text = next(t for k, t in r.files.items() if k.endswith("(fixed).yml"))
    for line in (
        "timeout: 0",
        "followRedirects: true",
        "maxRedirects: 5",
        "forwardAuthorizationHeader: true",
        "auth: inherit",
        "type: http",
    ):
        assert line in text
    assert "\n  bearer:" not in text


def test_generate_refuses_nonempty_folder_without_docs(tmp_path, disc, ren, launch):
    out = tmp_path / "out"
    out.mkdir()
    (out / "mine.txt").write_text("keep", encoding="utf-8")
    r = ren.render_collection(result(disc, [ep(disc)]), "svc", local(launch))
    rep = ren.write_collection(r.files, out)
    assert rep.refused and not rep.written
    assert (out / "mine.txt").read_text(encoding="utf-8") == "keep"
    assert [p.name for p in out.iterdir()] == ["mine.txt"]


def test_write_never_overwrites(tmp_path, disc, ren, launch):
    out = tmp_path / "out"
    r = ren.render_collection(result(disc, [ep(disc)]), "svc", local(launch))
    first = ren.write_collection(r.files, out)
    assert first.written and not first.refused
    target = out / "items" / "Get items (fixed).yml"
    target.write_text("EDITED by the user", encoding="utf-8")
    (out / "docs").mkdir()
    again = ren.write_collection(r.files, out)
    assert not again.refused
    assert target.read_text(encoding="utf-8") == "EDITED by the user"
    assert "items/Get items (fixed).yml" in again.skipped_existing


def test_write_never_leaves_the_output_root(tmp_path, ren):
    out = tmp_path / "out"
    rep = ren.write_collection({"../escape.yml": "x", "ok.yml": "y"}, out)
    assert not (tmp_path / "escape.yml").exists()
    assert rep.refused


def test_case_only_difference_is_not_overwritten(tmp_path, ren):
    out = tmp_path / "out"
    out.mkdir()
    (out / "docs").mkdir()
    (out / "Items.yml").write_text("user", encoding="utf-8")
    rep = ren.write_collection({"items.yml": "generated"}, out)
    assert (out / "Items.yml").read_text(encoding="utf-8") == "user"
    assert "items.yml" in rep.skipped_existing


def test_report_lists_found_written_skipped_todos_auth_placeholders(
    tmp_path, disc, ren, launch
):
    write_app(tmp_path)
    found = disc.discover(tmp_path)
    r = ren.render_collection(found, "orders", local(launch))
    text = "\n".join(r.report_lines())
    assert "endpoint(s) found" in text
    assert "requests to write" in text
    assert "not mounted" in text or "unmounted" in text
    assert "TODO" in text
    assert "auth" in text
    assert "baseUrl" in text and "DEV" in text and "PROD" in text
