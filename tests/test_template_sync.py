"""Tests of the template registry and the template_sync helper (CLAUDE/skills/template-sync)."""

from __future__ import annotations

import importlib.util
import json
import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "CLAUDE/skills/template-sync/scripts/template_sync.py"

spec = importlib.util.spec_from_file_location("template_sync", SCRIPT)
assert spec and spec.loader
ts = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ts)


@pytest.fixture()
def source(tmp_path: Path) -> Path:
    """A throwaway template source with two templates (one of them has two files)."""
    src = tmp_path / "source"
    (src / "templates").mkdir(parents=True)
    (src / "templates/a.yml").write_text("name: a\nvalue: TODO\n", encoding="utf-8")
    (src / "templates/b.sh").write_text("echo b\n", encoding="utf-8")
    (src / "templates/c.json").write_text('{\n  "k": 1\n}\n', encoding="utf-8")
    manifest = {
        "schema": 1,
        "templates": [
            {
                "id": "tpl-a",
                "title": "A",
                "version": 0,
                "files": [
                    {"src": "templates/a.yml", "dest": ".github/a.yml", "marker": True},
                    {"src": "templates/b.sh", "dest": "scripts/b.sh"},
                ],
            },
            {
                "id": "tpl-c",
                "title": "C",
                "version": 0,
                "files": [
                    {"src": "templates/c.json", "dest": "c.json", "marker": True}
                ],
            },
        ],
    }
    (src / "templates/manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    for tid in ("tpl-a", "tpl-c"):
        assert ts.main(["bump", tid, "--source", str(src), "--force"]) == 0
    return src


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    path = tmp_path / "repo"
    path.mkdir()
    return path


def apply(source: Path, repo: Path) -> None:
    """Copy the templates the way a user would, then stamp them."""
    (repo / ".github").mkdir(exist_ok=True)
    (repo / "scripts").mkdir(exist_ok=True)
    shutil.copy(source / "templates/a.yml", repo / ".github/a.yml")
    shutil.copy(source / "templates/b.sh", repo / "scripts/b.sh")
    shutil.copy(source / "templates/c.json", repo / "c.json")


def status(source: Path, repo: Path, tid: str) -> str:
    manifest = ts.load_manifest(source)
    return ts.compare(source, repo, ts.get(manifest, tid))[0]  # type: ignore[no-any-return]


def test_bump_writes_marker_and_digest_that_verify_accepts(source: Path) -> None:
    assert (source / "templates/a.yml").read_text().startswith("# template: tpl-a@1\n")
    assert (
        (source / "templates/c.json").read_text().startswith("// template: tpl-c@1\n")
    )
    assert ts.main(["verify", "--source", str(source)]) == 0


def test_verify_fails_when_a_template_changes_without_a_bump(source: Path) -> None:
    path = source / "templates/a.yml"
    path.write_text(path.read_text() + "extra: 1\n", encoding="utf-8")
    assert ts.main(["verify", "--source", str(source)]) == 1
    assert ts.main(["bump", "tpl-a", "--source", str(source)]) == 0
    assert ts.main(["verify", "--source", str(source)]) == 0
    assert "tpl-a@2" in path.read_text().splitlines()[0]


def test_bump_refuses_when_nothing_changed(source: Path) -> None:
    assert ts.main(["bump", "tpl-a", "--source", str(source)]) == 1


def test_a_missing_file_is_not_applied(source: Path, repo: Path) -> None:
    assert status(source, repo, "tpl-a") == "not-applied"


def test_a_copy_without_marker_is_unmarked(source: Path, repo: Path) -> None:
    apply(source, repo)
    (repo / ".github/a.yml").write_text("name: a\nvalue: 1\n", encoding="utf-8")
    assert status(source, repo, "tpl-a") == "unmarked"


def test_stamp_makes_it_current_and_keeps_repo_values(source: Path, repo: Path) -> None:
    apply(source, repo)
    (repo / ".github/a.yml").write_text("name: a\nvalue: 1\n", encoding="utf-8")
    assert ts.main(["stamp", "tpl-a", str(repo), "--source", str(source)]) == 0
    text = (repo / ".github/a.yml").read_text()
    assert text == "# template: tpl-a@1\nname: a\nvalue: 1\n"
    assert status(source, repo, "tpl-a") == "current"


def test_stamp_twice_keeps_a_single_marker(source: Path, repo: Path) -> None:
    apply(source, repo)
    for _ in range(2):
        ts.main(["stamp", "tpl-a", str(repo), "--source", str(source)])
    assert (repo / ".github/a.yml").read_text().count("template:") == 1


def test_a_lower_version_is_stale_and_a_higher_one_is_ahead(
    source: Path, repo: Path
) -> None:
    apply(source, repo)
    ts.main(["stamp", "tpl-a", str(repo), "--source", str(source)])
    path = source / "templates/a.yml"
    path.write_text(path.read_text() + "extra: 1\n", encoding="utf-8")
    ts.main(["bump", "tpl-a", "--source", str(source)])
    assert status(source, repo, "tpl-a") == "stale"
    target = repo / ".github/a.yml"
    target.write_text(
        target.read_text().replace("tpl-a@1", "tpl-a@9"), encoding="utf-8"
    )
    assert status(source, repo, "tpl-a") == "ahead"


def test_a_second_file_that_differs_makes_a_current_template_stale(
    source: Path, repo: Path
) -> None:
    apply(source, repo)
    ts.main(["stamp", "tpl-a", str(repo), "--source", str(source)])
    assert status(source, repo, "tpl-a") == "current"
    (repo / "scripts/b.sh").write_text("echo old\n", encoding="utf-8")
    assert status(source, repo, "tpl-a") == "stale"
    (repo / "scripts/b.sh").unlink()
    assert status(source, repo, "tpl-a") == "stale"


def test_check_exit_code_and_json_marker_comment(
    source: Path, repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    apply(source, repo)  # a plain copy of the templates carries their markers
    assert (repo / "c.json").read_text().startswith("// template: tpl-c@1\n")
    assert ts.main(["check", str(repo), "--source", str(source)]) == 0
    assert "nothing to update" in capsys.readouterr().out
    (repo / "c.json").write_text(
        '{"k": 2}\n', encoding="utf-8"
    )  # an old copy, no marker
    assert ts.main(["check", str(repo), "--source", str(source)]) == 1
    assert ts.main(["stamp", "tpl-c", str(repo), "--source", str(source)]) == 0
    assert ts.main(["check", str(repo), "--source", str(source)]) == 0


def test_crlf_files_keep_their_line_endings_when_stamped(
    source: Path, repo: Path
) -> None:
    apply(source, repo)
    (repo / "c.json").write_bytes(b'{\r\n  "k": 1\r\n}\r\n')
    ts.main(["stamp", "tpl-c", str(repo), "--source", str(source)])
    assert (
        repo / "c.json"
    ).read_bytes() == b'// template: tpl-c@1\r\n{\r\n  "k": 1\r\n}\r\n'
    assert status(source, repo, "tpl-c") == "current"


def test_unknown_template_and_missing_source_are_reported(
    source: Path, repo: Path, tmp_path: Path
) -> None:
    assert ts.main(["diff", "nope", str(repo), "--source", str(source)]) == 2
    assert ts.main(["list", "--source", str(tmp_path / "missing")]) == 2


def test_the_real_registry_is_consistent() -> None:
    """A template file changed without `bump` fails here, so the version is always honest."""
    manifest = ts.load_manifest(ROOT)
    assert ts.problems(ROOT, manifest) == []
    assert {t["id"] for t in manifest["templates"]} >= {
        "docker-image",
        "airflow-dag-sync",
    }
