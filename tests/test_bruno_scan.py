"""Task 9: the secret scanner never prints a value and never calls a failure clean."""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent / "support"))

from bruno_fixtures import write_app  # noqa: E402
from bruno_loader import load  # noqa: E402

# Fake secrets with unmistakable markers, built by concatenation so that no
# secret-shaped literal sits in the repo.
OPAQUE = "zQx" + "9Kv2" * 9
KEY = "QZXJ" + "W7V9" * 5
PASSWORD = "QZXW" + "pJ9" * 3
JWT = "ey" + "J" + "QZXJWVQZXJWV" + "." + "QZXJWVQZXJWV" + "." + "QZXJWVQZXJ"
CLOUD = "AK" + "IA" + "QZXJWV7K9QZXJWV7"
BEARER = "QZXJWV" + "7K9wQ" * 4
SECRETS = [OPAQUE, KEY, PASSWORD, JWT, CLOUD, BEARER]
PEM_BEGIN = "-----BEGIN " + "RSA PRIVATE KEY" + "-----"

LINE_FORMAT = re.compile(r"^(\S.*):(\d+)  ([a-z-]+)  (\d+)$")


@pytest.fixture()
def scan():
    return load("bruno_scan")


@pytest.fixture()
def cli():
    return load("bruno_collection")


def put(root: Path, rel: str, text: str | bytes) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(text, bytes):
        path.write_bytes(text)
    else:
        with open(path, "w", encoding="utf-8", newline="") as handle:
            handle.write(text)
    return path


def hostile(root: Path) -> None:
    put(
        root,
        "environments/DEV.yml",
        "name: DEV\nvariables:\n"
        f'  - name: apiKey\n    value: "{OPAQUE}"\n'
        f'  - secret: true\n    name: clientSecret\n    value: "{KEY}"\n'
        '  - name: dbPassword\n    value: ""\n'
        '  - name: baseUrl\n    value: "https://<dev-host>"\n',
    )
    put(
        root,
        "orders/Get orders (fixed).yml",
        "info:\n  name: x\nhttp:\n  method: GET\n"
        f'  url: "https://user:{PASSWORD}@host.invalid/x"\n'
        "  headers:\n"
        f'    - name: apikey\n      value: "{OPAQUE}"\n'
        f'    - name: Authorization\n      value: "Bearer {BEARER}"\n',
    )
    put(
        root,
        "notes.md",
        f"token {JWT}\n{PEM_BEGIN}\nkey {CLOUD}\nplain {OPAQUE}\n",
    )


def kinds(report) -> set[str]:
    return {f.kind for f in report.findings}


def test_finds_header_variable_name_jwt_private_key_url_credential_opaque_and_missing_gitignore_rule(
    tmp_path, scan
):
    hostile(tmp_path)
    report = scan.scan(tmp_path)
    assert {
        "header-value",
        "secret-name-plain-value",
        "secret-value-present",
        "secret-not-marked",
        "bearer-token",
        "jwt",
        "private-key",
        "url-credential",
        "cloud-key",
        "opaque-string",
        "missing-env-rule",
    } <= kinds(report)
    assert report.exit_code != 0


def test_report_line_format(tmp_path, scan):
    hostile(tmp_path)
    report = scan.scan(tmp_path)
    finding_lines = [x for x in report.lines if LINE_FORMAT.match(x)]
    assert len(finding_lines) == len(report.findings) > 5
    for line in report.lines:
        if LINE_FORMAT.match(line):
            continue
        assert not re.search(r":\d+  ", line), line


def test_no_value_fragment_in_report_stderr_or_exception(tmp_path, scan, cli, capsys):
    hostile(tmp_path)
    put(tmp_path, f"eyJ{PASSWORD}.yml", f"apikey: {KEY}\n")
    put(tmp_path, f"password={PASSWORD}/inner/{OPAQUE}.yml", "name: x\n")
    put(tmp_path, f"deep/{'d/' * 30}file.yml", f"Authorization: Bearer {BEARER}\n")
    put(tmp_path, "bad.yml", b"\xff\xfe" + PASSWORD.encode() + b"\x00\x01")
    put(tmp_path, "bin.yml", b"\x00" + KEY.encode())
    report = scan.scan(tmp_path)
    code = cli.main(["scan", str(tmp_path)])
    captured = capsys.readouterr()
    text = "\n".join(report.lines) + captured.out + captured.err
    assert code != 0
    for secret in SECRETS:
        for i in range(len(secret) - 2):
            assert secret[i : i + 3] not in text, secret[i : i + 3]
    for line in (
        "info:",
        "http:",
        "  method: GET",
        "name: DEV",
    ):
        assert line not in text.splitlines()


def test_path_redaction(tmp_path, scan):
    put(tmp_path, f"eyJ{PASSWORD}.yml", "apikey: nothing\n")
    put(tmp_path, f"password={PASSWORD}/a.yml", f"apikey: {KEY}\n")
    put(tmp_path, "plain/ok name (fixed).yml", f"apikey: {KEY}\n")
    first = scan.scan(tmp_path)
    second = scan.scan(tmp_path)
    shown = [f.path for f in first.findings]
    assert any(p.startswith("<path-redacted:") for p in shown)
    assert "plain/ok name (fixed).yml" in shown
    assert [f.path for f in second.findings] == shown  # stable
    for p in shown:
        if p.startswith("<path-redacted:"):
            assert re.fullmatch(r"<path-redacted:\d+>", p)


def test_unreadable_malformed_huge_binary_and_out_of_folder_symlink_are_incomplete_and_nonzero(
    tmp_path, scan
):
    root = tmp_path / "c"
    root.mkdir()
    put(root, ".gitignore", ".env*\n")
    put(root, "clean.yml", "name: fine\n")
    assert scan.scan(root).exit_code == 0
    put(root, "binary.yml", b"\x00\x01\x02")
    put(root, "badenc.yml", b"\xff\xfe\xfa")
    with open(root / "huge.yml", "wb") as handle:
        handle.truncate(2 * 1024 * 1024 + 1)
    outside = tmp_path / "outside.yml"
    outside.write_text("apikey: nothing\n", encoding="utf-8")
    (root / "link.yml").symlink_to(outside)
    locked = put(root, "locked.yml", "name: x\n")
    locked.chmod(0)
    try:
        report = scan.scan(root)
    finally:
        locked.chmod(0o600)
    reasons = {i.reason for i in report.incomplete}
    assert {"binary", "encoding", "too-large", "symlink"} <= reasons
    if os.geteuid() != 0:
        assert "unreadable" in reasons
    assert report.exit_code != 0
    assert any("incomplete" in x for x in report.lines)


def test_crlf_and_bom_files_scanned(tmp_path, scan):
    put(tmp_path, ".gitignore", ".env*\n")
    put(
        tmp_path,
        "a.yml",
        ("﻿info:\r\n  name: x\r\napikey: " + KEY + "\r\n").encode("utf-8"),
    )
    report = scan.scan(tmp_path)
    assert [(f.kind, f.line) for f in report.findings] == [("header-value", 3)]
    assert report.findings[0].length == len(KEY)


def test_top_level_error_prints_only_class_and_step(
    tmp_path, scan, cli, capsys, monkeypatch
):
    hostile(tmp_path)

    def boom(*args, **kwargs):
        raise RuntimeError("secret text " + KEY)

    monkeypatch.setattr(scan, "_scan_text", boom)
    code = cli.main(["scan", str(tmp_path)])
    captured = capsys.readouterr()
    text = captured.out + captured.err
    assert code != 0
    assert KEY not in text and "RuntimeError" not in text
    assert "scan incomplete" in text or "scan error" in text


def test_no_verbose_or_debug_flag(tmp_path, cli, capsys):
    for flag in ("--verbose", "--debug", "-v"):
        with pytest.raises(SystemExit) as info:
            cli.main(["scan", str(tmp_path), flag])
        assert info.value.code != 0
    capsys.readouterr()


def test_clean_report_says_not_proof(tmp_path, scan):
    put(tmp_path, ".gitignore", ".env*\n")
    put(tmp_path, "a.yml", "name: fine\n")
    report = scan.scan(tmp_path)
    assert report.exit_code == 0
    assert any("not proof" in x for x in report.lines)


def test_findings_end_with_git_history_reminder(tmp_path, scan):
    hostile(tmp_path)
    report = scan.scan(tmp_path)
    assert any("git history" in x for x in report.lines)


def test_generated_collection_scans_clean(tmp_path, cli, capsys):
    from bruno_fixtures import AUTH_VARIANTS, write_files

    repo = tmp_path / "repo-a"
    repo.mkdir()
    write_files(repo, AUTH_VARIANTS["oauth"])
    write_app(repo)
    out = tmp_path / "out"
    assert (
        cli.main(["generate", str(repo), "--out", str(out), "--model", "claude-code/t"])
        == 0
    )
    text = capsys.readouterr().out
    assert "secret scan: 0 finding(s), 0 incomplete" in text
    assert cli.main(["scan", str(out / "repo-a")]) == 0
