"""Task 6: the `discover` and `generate` commands."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent / "support"))

from bruno_fixtures import write_app  # noqa: E402
from bruno_loader import load  # noqa: E402


@pytest.fixture()
def cli():
    return load("bruno_collection")


def test_discover_lists_endpoints(tmp_path, cli, capsys):
    write_app(tmp_path)
    assert cli.main(["discover", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "GET /api/v1/orders/{order_id}" in out


def test_generate_writes_collection_then_refuses_a_second_run(
    tmp_path, cli, capsys, monkeypatch
):
    repo = tmp_path / "my repo"
    repo.mkdir()
    write_app(repo)
    out = tmp_path / "out"
    assert cli.main(["generate", str(repo), "--out", str(out)]) == 0
    text = capsys.readouterr().out
    assert "written:" in text and "TODO placeholder" in text
    assert (out / "my repo" / "environments" / "LOCAL.yml").is_file()
    # no docs/ yet (Task 8), so a second run is refused and nothing changes
    before = sorted(p.relative_to(out) for p in out.rglob("*") if p.is_file())
    assert cli.main(["generate", str(repo), "--out", str(out)]) == 1
    after = sorted(p.relative_to(out) for p in out.rglob("*") if p.is_file())
    assert before == after


def test_generate_needs_an_output_root(tmp_path, cli, capsys, monkeypatch):
    monkeypatch.delenv("BRUNO_COLLECTIONS_DIR", raising=False)
    write_app(tmp_path)
    assert cli.main(["generate", str(tmp_path)]) == 2
    assert "BRUNO_COLLECTIONS_DIR" in capsys.readouterr().err
