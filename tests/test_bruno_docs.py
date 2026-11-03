"""Task 8: the OKF docs bundle and `sync`."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent / "support"))

from bruno_fixtures import AUTH_VARIANTS, write_app, write_files  # noqa: E402
from bruno_loader import SCRIPTS, load  # noqa: E402

LINT = SCRIPTS.parent.parent / "okf-writer" / "scripts" / "okf_lint.py"
MODEL = "claude-code/test-model"


@pytest.fixture()
def cli():
    return load("bruno_collection")


@pytest.fixture()
def docs_mod():
    return load("bruno_docs")


class World:
    def __init__(self, tmp_path: Path, cli, variant: str | None = None):
        self.cli = cli
        self.repo = tmp_path / "orders-repo"
        self.repo.mkdir()
        if variant:
            write_files(self.repo, AUTH_VARIANTS[variant])
        else:
            write_app(self.repo)
        self.out = tmp_path / "out"
        self.col = self.out / "orders-repo"

    def run(self, command: str, reason: str = "initial generation") -> int:
        code: int = self.cli.main(
            [
                command,
                str(self.repo),
                "--out",
                str(self.out),
                "--model",
                MODEL,
                "--reason",
                reason,
            ]
        )
        return code

    def snapshot(self) -> dict[str, str]:
        return {
            p.relative_to(self.col).as_posix(): hashlib.sha256(
                p.read_bytes()
            ).hexdigest()
            for p in sorted(self.col.rglob("*"))
            if p.is_file()
        }

    def concept(self, fragment: str) -> Path:
        return next(
            p for p in (self.col / "docs" / "requests").iterdir() if fragment in p.name
        )


@pytest.fixture()
def world(tmp_path, cli):
    w = World(tmp_path, cli)
    assert w.run("generate") == 0
    return w


def lint(path: Path, strict: bool = True) -> subprocess.CompletedProcess:
    args = [sys.executable, str(LINT), str(path)]
    if strict:
        args.append("--strict")
    return subprocess.run(args, capture_output=True, text=True)


def test_bundle_passes_okf_lint(world):
    done = lint(world.col / "docs")
    assert done.returncode == 0, done.stdout
    assert "0 error(s), 0 warning(s)" in done.stdout


def test_frontmatter_generated_by_and_draft_no_verified(world):
    for path in (world.col / "docs").rglob("*.md"):
        if path.name in ("index.md", "log.md"):
            continue
        text = path.read_text(encoding="utf-8")
        head = text.split("---")[1]
        assert f"by: {MODEL}" in head, path
        assert "status: draft" in head
        assert "verified" not in head


def test_log_newest_first_with_reason_and_source(world, docs_mod, monkeypatch):
    days = iter([dt.datetime(2026, 11, 5, 9, 0, tzinfo=dt.timezone.utc)])  # noqa: UP017 (dt.UTC needs 3.11; this also runs on 3.9)
    monkeypatch.setattr(docs_mod, "_now", lambda: next(days))
    with open(world.repo / "app" / "main.py", "a", encoding="utf-8") as f:
        f.write('\n\n@app.get("/extra")\ndef extra():\n    return 1\n')
    assert world.run("sync", reason="the user asked for the extra route") == 0
    log = (world.col / "docs" / "log.md").read_text(encoding="utf-8")
    dates = re.findall(r"^## (\d{4}-\d{2}-\d{2})$", log, re.M)
    assert dates == sorted(dates, reverse=True) and len(dates) == 2
    assert "the user asked for the extra route" in log
    assert "initial generation" in log
    assert "app/main.py" in log
    assert "Unverified" in log


def test_environments_doc_has_no_values(world):
    text = (world.col / "docs" / "environments.md").read_text(encoding="utf-8")
    assert "baseUrl" in text
    assert "localhost" not in text and "http" not in text.lower().replace(
        "https://<", ""
    )
    assert "<dev-host>" not in text or "placeholder" in text.lower()


def test_environments_doc_has_proxy_note_for_dev_and_prod(world):
    text = (world.col / "docs" / "environments.md").read_text(encoding="utf-8")
    assert text.count("nginx") >= 1 and "Apigee" in text
    assert "DEV" in text and "PROD" in text


def test_sync_adds_only_new_endpoints_and_logs_needs_a_decision(world):
    before = world.snapshot()
    main = world.repo / "app" / "main.py"
    with open(main, "a", encoding="utf-8") as f:
        f.write('\n\n@app.get("/extra")\ndef extra():\n    return 1\n')
        f.write('\n\n@app.get("/health/")\ndef health_again():\n    return 1\n')
    orders = world.repo / "app" / "api" / "endpoints" / "orders.py"
    orders.write_text(
        orders.read_text(encoding="utf-8").replace(
            "def get_order(order_id: int):",
            "def get_order(order_id: int, verbose: bool = False):",
        ),
        encoding="utf-8",
    )
    assert world.run("sync", reason="new endpoints found by sync") == 0
    after = world.snapshot()
    added = set(after) - set(before)
    assert any("Get extra (fixed)" in p for p in added)
    assert any(p.startswith("docs/requests/get-extra") for p in added)
    log = (world.col / "docs" / "log.md").read_text(encoding="utf-8")
    assert "needs a decision" in log.lower()
    assert "GET /health" in log and "GET /api/v1/orders/{order_id}" in log
    assert not any("health" in p.lower() and "again" in p.lower() for p in added)


def test_sync_never_modifies_existing_files(world):
    before = world.snapshot()
    old_log = (world.col / "docs" / "log.md").read_text(encoding="utf-8")
    with open(world.repo / "app" / "main.py", "a", encoding="utf-8") as f:
        f.write('\n\n@app.get("/extra")\ndef extra():\n    return 1\n')
    assert world.run("sync", reason="more") == 0
    after = world.snapshot()
    for rel, digest in before.items():
        if rel in ("docs/index.md", "docs/log.md"):
            continue
        assert after[rel] == digest, rel
    new_log = (world.col / "docs" / "log.md").read_text(encoding="utf-8")
    for line in old_log.splitlines():
        if line.strip():
            assert line in new_log
    index = (world.col / "docs" / "index.md").read_text(encoding="utf-8")
    assert "get-extra" in index and "get-health" in index


def test_sync_with_missing_docs_refuses_and_writes_nothing(world, tmp_path, capsys):
    import shutil

    shutil.rmtree(world.col / "docs")
    before = world.snapshot()
    assert world.run("sync") == 1
    assert world.snapshot() == before
    assert "docs" in capsys.readouterr().out


def test_sync_with_corrupt_concept_refuses(world):
    concept = world.concept("get-health")
    concept.write_text("not a concept at all", encoding="utf-8")
    with open(world.repo / "app" / "main.py", "a", encoding="utf-8") as f:
        f.write('\n\n@app.get("/extra")\ndef extra():\n    return 1\n')
    before = world.snapshot()
    assert world.run("sync") == 1
    assert world.snapshot() == before


def test_generate_refuses_when_the_collection_already_exists(world):
    before = world.snapshot()
    assert world.run("generate") == 1
    assert world.snapshot() == before


def test_pinned_bruno_version_recorded(world):
    index = (world.col / "docs" / "index.md").read_text(encoding="utf-8")
    assert "Bruno 4.3.0" in index


def test_request_concept_stores_original_sample_and_schema(world):
    text = world.concept("get-api-v1-orders-order-id").read_text(encoding="utf-8")
    assert 'resource: "GET /api/v1/orders/{order_id}"' in text
    state = json.loads(
        text.split("# State", 1)[1].split("```json", 1)[1].split("```", 1)[0]
    )
    assert state["identity"] == "GET /api/v1/orders/{order_id}"
    assert state["original"]["params"]["order_id"]["in"] == "path"
    assert "value" in state["original"]["params"]["order_id"]
    schema = {p["name"]: p for p in state["schema"]["params"]}
    assert (
        schema["order_id"]["type"] == "int" and schema["order_id"]["required"] is True
    )
    assert len(state["files"]) == 2


def test_request_concept_body_sample_and_schema(tmp_path, cli):
    w = World(tmp_path, cli)
    write_files(
        w.repo,
        {
            "svc/main.py": (
                "from fastapi import FastAPI\nfrom pydantic import BaseModel\n\n"
                "app = FastAPI()\n\n\n"
                "class Customer(BaseModel):\n    name: str = 'Ann'\n    age: int = 3\n\n\n"
                "@app.post('/customers')\ndef create(c: Customer):\n    return c\n"
            )
        },
    )
    assert w.run("generate") == 0
    text = w.concept("post-customers").read_text(encoding="utf-8")
    state = json.loads(
        text.split("# State", 1)[1].split("```json", 1)[1].split("```", 1)[0]
    )
    assert state["original"]["body"] == {"name": "Ann", "age": 3}
    assert [f["name"] for f in state["schema"]["body"]["fields"]] == ["name", "age"]


def test_token_doc_only_with_token_endpoint_and_has_no_token_values(tmp_path, cli):
    plain = World(tmp_path / "a", cli) if (tmp_path / "a").mkdir() is None else None
    assert plain is not None and plain.run("generate") == 0
    assert not (plain.col / "docs" / "auth" / "token.md").exists()
    other = tmp_path / "b"
    other.mkdir()
    w = World(other, cli, "oauth")
    assert w.run("generate") == 0
    text = (w.col / "docs" / "auth" / "token.md").read_text(encoding="utf-8")
    assert "access_token_dev" in text and "access_token_prod" in text
    assert "Authorization" in text
    assert lint(w.col / "docs").returncode == 0


def test_generate_and_sync_report_end_with_lint_and_scan_summary(tmp_path, cli, capsys):
    w = World(tmp_path, cli)
    assert w.run("generate") == 0
    out = capsys.readouterr().out.strip().splitlines()
    assert out[-2].startswith("OKF lint:") and out[-1].startswith("secret scan:")
    assert w.run("sync") == 0
    out = capsys.readouterr().out.strip().splitlines()
    assert out[-2].startswith("OKF lint:") and out[-1].startswith("secret scan:")


def test_add_external_creates_placeholder_concept_and_log(world):
    code = world.cli.main(
        [
            "add-external",
            str(world.repo),
            "--out",
            str(world.out),
            "--title",
            "Get exchange rate",
            "--method",
            "GET",
            "--model",
            MODEL,
            "--reason",
            "the user asked for a placeholder",
        ]
    )
    assert code == 0
    req = (world.col / "external" / "Get exchange rate.yml").read_text(encoding="utf-8")
    assert 'url: "TODO"' in req and "method: GET" in req
    assert (world.col / "external" / "folder.yml").is_file()
    concept = (world.col / "docs" / "external" / "get-exchange-rate.md").read_text(
        encoding="utf-8"
    )
    assert "type: External Request" in concept and f"by: {MODEL}" in concept
    log = (world.col / "docs" / "log.md").read_text(encoding="utf-8")
    assert "the user asked for a placeholder" in log
    assert "get-exchange-rate" in (world.col / "docs" / "index.md").read_text(
        encoding="utf-8"
    )
    assert lint(world.col / "docs").returncode == 0
    # a second call must not overwrite what the user may have edited
    req_path = world.col / "external" / "Get exchange rate.yml"
    req_path.write_text("EDITED", encoding="utf-8")
    assert (
        world.cli.main(
            ["add-external", str(world.repo), "--out", str(world.out),
             "--title", "Get exchange rate"]
        )
        == 1
    )  # fmt: skip
    assert req_path.read_text(encoding="utf-8") == "EDITED"


def test_user_owned_requests_are_kept_and_reported(world, docs_mod, capsys):
    mine = world.col / "mine" / "My call.yml"
    mine.parent.mkdir()
    mine.write_text("info:\n  name: mine\n", encoding="utf-8")
    world.cli.main(
        ["add-external", str(world.repo), "--out", str(world.out), "--title", "Probe"]
    )
    owned = docs_mod.user_owned(world.col, docs_mod.read_docs(world.col))
    assert sorted(owned) == ["external/Probe.yml", "mine/My call.yml"]
    before = world.snapshot()
    capsys.readouterr()
    assert world.run("sync") == 0
    out = capsys.readouterr().out
    assert world.snapshot() == before
    assert "user-owned" in out and "mine/My call.yml" in out
