"""Tests of the log redaction helpers and the loguru patcher that applies them."""

from __future__ import annotations

from loguru import logger as demo_logger

from app.configs.log_config import _make_redaction_patcher
from app.configs.log_redaction import MASK, collect_secret_values, redact

ENV = {
    "DATABASE_PASSWORD": "Hunter2-pass",
    "OSS_ACCESS_SECRET": "oss-secret-value",
    "OSS_ACCESS_KEY": "AKIDEXAMPLE123",
    "SOME_TOKEN": "tok",  # too short to mask
    "DATABASE_HOST": "db.internal.example",  # not a secret
    "DEBUG": "true",
}


def test_collects_only_secret_values() -> None:
    values = collect_secret_values(ENV)
    assert {"Hunter2-pass", "oss-secret-value", "AKIDEXAMPLE123"} <= set(values)
    assert "tok" not in values
    assert "db.internal.example" not in values
    assert values == sorted(values, key=len, reverse=True)


def test_masks_values_anywhere_in_the_text() -> None:
    secrets = collect_secret_values(ENV)
    text = (
        "cfg={'password': 'Hunter2-pass', 'host': 'db.internal.example'} AKIDEXAMPLE123"
    )
    out = redact(text, secrets)
    assert "Hunter2-pass" not in out and "AKIDEXAMPLE123" not in out
    assert "db.internal.example" in out


def test_masks_url_userinfo_and_pairs_not_in_the_environment() -> None:
    out = redact("postgresql://svc_user:pa55w0rd@host:5432/db", [])
    assert "pa55w0rd" not in out and "svc_user" in out
    out = redact("connect(password=abc12345, user=x)", [])
    assert "abc12345" not in out and "user=x" in out
    out = redact("{'token': 'xyz-789', 'name': 'ok'}", [])
    assert "xyz-789" not in out and "'name': 'ok'" in out


def test_plain_text_is_unchanged() -> None:
    text = "Processing 123 rows for 2025-12-05"
    assert redact(text, collect_secret_values(ENV)) == text
    assert MASK == "***"


def test_patcher_masks_message_extra_and_traceback_in_every_sink() -> None:
    secrets = collect_secret_values(ENV)
    captured: list[str] = []

    demo_logger.remove()
    demo_logger.configure(patcher=_make_redaction_patcher(secrets))
    demo_logger.add(captured.append, format="{message}|{extra}", colorize=False)
    try:
        try:
            raise ValueError("login failed with oss-secret-value")
        except ValueError:
            demo_logger.bind(note="key AKIDEXAMPLE123").exception(
                "connect to postgresql://u:Hunter2-pass@h/db"
            )
    finally:
        demo_logger.remove()

    output = "".join(captured)
    for secret in ("Hunter2-pass", "oss-secret-value", "AKIDEXAMPLE123"):
        assert secret not in output
    assert "ValueError" in output and MASK in output
