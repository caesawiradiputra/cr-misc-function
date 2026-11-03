"""Task 3: auth and token-endpoint discovery for the bruno-collection skill."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent / "support"))

import bruno_fixtures as fx  # noqa: E402
from bruno_loader import load  # noqa: E402


@pytest.fixture()
def run(tmp_path):
    disc = load("bruno_discover")

    def _run(variant: str):
        root = tmp_path / variant
        fx.write_files(root, fx.AUTH_VARIANTS[variant])
        return disc.discover(root)

    return _run


@pytest.mark.parametrize(
    ("variant", "kind", "header"),
    [
        ("oauth", "oauth2_password", None),
        ("apikey_header", "api_key_header", "X-API-Key"),
        ("apikey_query", "api_key_query", "key"),
        ("bearer", "bearer", None),
        ("basic", "basic", None),
        ("middleware", "api_key_header", "apikey"),
    ],
)
def test_auth_kind_and_header(run, variant, kind, header):
    auth = run(variant).auth
    assert auth is not None and auth.kind == kind and auth.header_name == header
    assert auth.source is not None and auth.source.file.startswith("svc/")


def test_middleware_header_source_line_and_ignored_headers(run):
    auth = run("middleware").auth
    assert auth.source.file == "svc/guard.py" and auth.source.line == 8
    assert auth.header_name != "user-agent"


def test_nothing_recognized_is_not_proof(run):
    result = run("none")
    assert result.auth.kind == "none_recognized" and result.auth.source is None
    text = " ".join(result.outcome_lines())
    assert "no auth pattern recognized, check middleware" in text
    assert "not proof" in text


def test_auth_line_in_report_names_file_and_line(run):
    text = " ".join(run("apikey_header").outcome_lines())
    assert "auth found: api_key_header" in text and "svc/main.py:5" in text


def test_token_endpoint_inputs_and_field_oauth_form(run):
    result = run("oauth")
    token = result.token
    assert token is not None and token.path == "/api/auth/login"
    assert token.grant_inputs == ["username", "password"]
    assert token.token_field == "access_token"
    assert token.source.file == "svc/main.py"


def test_token_endpoint_relative_url_and_client_credentials(run):
    token = run("form_token").token
    assert token.path == "/token"
    assert token.grant_inputs == ["client_id", "client_secret"]
    assert token.token_field == "jwt_token"


def test_token_field_defaults_to_access_token(run):
    token = run("default_field").token
    assert token.token_field == "access_token"
    assert token.grant_inputs == ["username", "password"]


def test_token_url_without_matching_route_is_listed(run):
    result = run("missing_route")
    assert result.token is None
    reasons = [s.reason for s in result.skipped]
    assert any("/missing" in r and "token" in r for r in reasons)


def test_no_token_for_other_schemes(run):
    for variant in ("apikey_header", "bearer", "basic", "middleware", "none"):
        assert run(variant).token is None
