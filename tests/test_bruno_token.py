"""Task 7: token request, environment isolation and the two verbatim scripts."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent / "support"))

from bruno_fixtures import AUTH_VARIANTS, write_app, write_files  # noqa: E402
from bruno_loader import load  # noqa: E402

SESSION = Path(__file__).parent / "support" / "bru_session.js"
needs_node = pytest.mark.skipif(
    shutil.which("node") is None, reason="node is not installed"
)

SET_TOKEN = 'bru.setVar("access_token_" + bru.getEnvName().toLowerCase(), res.body.access_token);'
USE_TOKEN = 'bru.setVar("access_token", bru.getVar("access_token_" + bru.getEnvName().toLowerCase()));'


@pytest.fixture()
def disc():
    return load("bruno_discover")


@pytest.fixture()
def ren():
    return load("bruno_render")


@pytest.fixture()
def rendered(tmp_path, disc, ren):
    def go(variant="oauth"):
        write_files(tmp_path, AUTH_VARIANTS[variant])
        result = disc.discover(tmp_path)
        launch = load("bruno_launch").LaunchResult("http://localhost:8000", None, [])
        return ren.render_collection(result, "svc", launch)

    return go


def script_of(text: str) -> str:
    lines = text.splitlines()
    start = next(i for i, x in enumerate(lines) if x.strip().endswith("code: |-"))
    body = []
    for line in lines[start + 1 :]:
        if line and not line.startswith("        "):
            break
        body.append(line[8:])
    return "\n".join(body).strip()


def test_token_files_only_with_token_endpoint(tmp_path, disc, ren, rendered):
    r = rendered("oauth")
    assert "auth/Get token.yml" in r.files and "auth/folder.yml" in r.files
    assert "before-request" in r.files["opencollection.yml"]
    write_app(tmp_path / "plain")
    plain = ren.render_collection(
        disc.discover(tmp_path / "plain"),
        "svc",
        load("bruno_launch").LaunchResult("http://localhost:8000", None, []),
    )
    assert not any(p.startswith("auth/") for p in plain.files)
    assert "before-request" not in plain.files["opencollection.yml"]
    assert "access_token" not in "".join(plain.files.values())


def test_token_request_has_no_random_pair_and_inputs_are_secret_env_vars(rendered):
    r = rendered("form_token")
    assert not any("Get token (" in p or "token (" in p.lower() for p in r.files)
    assert not any(p.startswith("token/") for p in r.files)
    text = r.files["auth/Get token.yml"]
    assert "method: POST" in text and "type: form-urlencoded" in text
    assert '"{{clientId}}"' in text and '"{{clientSecret}}"' in text
    assert "random" not in text
    for env in ("LOCAL", "DEV", "PROD"):
        e = r.files[f"environments/{env}.yml"]
        for name in ("clientId", "clientSecret"):
            block = e.split(f"name: {name}")[0].rsplit("- ", 1)[1]
            assert "secret: true" in block
            assert "value" not in e.split(f"name: {name}")[1].split("- ")[0]


def test_other_requests_send_the_token_variable_without_their_own_script(rendered):
    r = rendered("oauth")
    me = (
        r.files["root/Get me (fixed).yml"]
        if "root/Get me (fixed).yml" in r.files
        else next(t for p, t in r.files.items() if p.endswith("Get me (fixed).yml"))
    )
    assert 'value: "Bearer {{access_token}}"' in me
    assert "scripts" not in me
    assert "name: Authorization" in me
    token = r.files["auth/Get token.yml"]
    assert "name: Authorization" not in token


def test_scripts_verbatim(rendered):
    r = rendered("oauth")
    assert script_of(r.files["auth/Get token.yml"]) == SET_TOKEN
    assert script_of(r.files["opencollection.yml"]) == USE_TOKEN
    everything = "".join(r.files.values())
    assert "setEnvVar" not in everything and "setCollectionVar" not in everything


def test_token_field_from_the_response_model(rendered):
    r = rendered("form_token")
    assert "res.body.jwt_token" in script_of(r.files["auth/Get token.yml"])


def run_session(collection: str, steps: list[dict]) -> list[dict]:
    done = subprocess.run(
        ["node", str(SESSION)],
        input=json.dumps({"collection": collection, "steps": steps}),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert done.returncode == 0, done.stderr
    out: list[dict] = json.loads(done.stdout)
    return out


@needs_node
def test_isolation_sequence_in_node(rendered):
    r = rendered("oauth")
    token_script = script_of(r.files["auth/Get token.yml"])
    collection = script_of(r.files["opencollection.yml"])

    def tok(env, value):
        return {
            "kind": "token",
            "env": env,
            "script": token_script,
            "body": {"access_token": value},
        }

    def req(env):
        return {"kind": "request", "env": env}

    out = run_session(
        collection,
        [
            tok("DEV", "dev-1"), req("DEV"),
            tok("PROD", "prod-1"), req("PROD"),
            req("DEV"),
            tok("LOCAL", "local-1"), req("LOCAL"),
            req("DEV"), req("PROD"),
        ],
    )  # fmt: skip
    got = [x["authorization"] for x in out]
    assert got == [
        "Bearer dev-1",
        "Bearer prod-1",
        "Bearer dev-1",
        "Bearer local-1",
        "Bearer dev-1",
        "Bearer prod-1",
    ]


@needs_node
def test_environment_without_token_never_carries_another_environments_token(rendered):
    r = rendered("oauth")
    token_script = script_of(r.files["auth/Get token.yml"])
    collection = script_of(r.files["opencollection.yml"])
    out = run_session(
        collection,
        [
            {"kind": "token", "env": "DEV", "script": token_script, "body": {"access_token": "dev-1"}},
            {"kind": "request", "env": "DEV"},
            {"kind": "request", "env": "PROD"},
            {"kind": "request", "env": "LOCAL"},
        ],
    )  # fmt: skip
    assert [x["authorization"] for x in out] == [
        "Bearer dev-1",
        "Bearer {{access_token}}",
        "Bearer {{access_token}}",
    ]


def test_rendered_files_hold_no_token_value(rendered):
    r = rendered("oauth")
    for text in r.files.values():
        assert "dev-1" not in text and "prod-1" not in text
