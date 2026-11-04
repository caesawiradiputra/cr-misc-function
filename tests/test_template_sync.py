"""Tests of the template registry and the template_sync helper (CLAUDE/skills/template-sync)."""

from __future__ import annotations

import importlib.util
import json
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "CLAUDE/skills/template-sync/scripts/template_sync.py"

spec = importlib.util.spec_from_file_location("template_sync", SCRIPT)
assert spec and spec.loader
ts = importlib.util.module_from_spec(spec)
sys.modules["template_sync"] = ts  # dataclasses look the module up here
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
    sources = ts.find_sources([str(source)])
    src, template = ts.get(sources, tid)
    return str(ts.compare(src, repo, template)[0])


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
    sources = ts.find_sources([str(ROOT)])
    assert ts.problems(sources) == []
    ids = {t["id"] for _, t in ts.entries(sources)}
    assert ids >= {"docker-image", "airflow-dag-sync"}


# ---- layout checks, deviations and several sources


@pytest.fixture()
def py_source(tmp_path: Path) -> Path:
    """A second source: a layout template tied to rule ids, plus one rule heading."""
    src = tmp_path / "pysource"
    (src / "docs/standards/common").mkdir(parents=True)
    (src / "docs/standards/common/layout.md").write_text(
        "## C-LAYOUT-01 App folder\n\nRule text.\n\n## C-CFG-01 One settings module\n",
        encoding="utf-8",
    )
    manifest = {
        "schema": 1,
        "templates": [
            {
                "id": "python-layout",
                "title": "Python layout",
                "kind": "layout",
                "version": 0,
                "expect": [
                    {"path": "app/main.py", "rule": "C-LAYOUT-01"},
                    {"path": "app/configs/config.py", "rule": "C-CFG-01"},
                    {"path": "tests/test_*.py", "rule": "C-TEST-02"},
                    {"path": "src", "rule": "C-LAYOUT-01", "absent": True},
                ],
            }
        ],
    }
    (src / "docs/standards/template-manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )
    assert ts.main(["bump", "python-layout", "--source", str(src), "--force"]) == 0
    return src


def layout(py_source: Path, repo: Path) -> list[tuple[str, str]]:
    sources = ts.find_sources([str(py_source)])
    _, template = ts.get(sources, "python-layout")
    deviations, _ = ts.read_deviations(repo)
    return list(ts.compare_layout(repo, template, deviations))


def test_layout_reports_missing_and_forbidden_paths(
    py_source: Path, repo: Path
) -> None:
    (repo / "app/configs").mkdir(parents=True)
    (repo / "app/main.py").write_text("", encoding="utf-8")
    (repo / "src").mkdir()
    states = {line.split(" ")[0]: state for state, line in layout(py_source, repo)}
    assert states["app/main.py"] == "ok"
    assert states["app/configs/config.py"] == "drift"
    assert states["tests/test_*.py"] == "drift"
    assert states["src"] == "drift"


def test_a_recorded_deviation_makes_drift_deliberate(
    py_source: Path, repo: Path
) -> None:
    assert (
        ts.main(
            [
                "accept",
                "C-LAYOUT-01",
                str(repo),
                "--reason",
                "installable library",
                "--source",
                str(py_source),
            ]
        )
        == 0
    )
    (repo / "src").mkdir()
    results = layout(py_source, repo)
    src = next(line for state, line in results if line.startswith("src"))
    assert ("deliberate", src) in results and "installable library" in src
    missing_main = next(
        (s for s, line in results if line.startswith("app/main.py")), ""
    )
    assert missing_main == "deliberate"  # the same rule covers the missing app/main.py


def test_accept_refuses_unknown_ids_empty_reasons_and_duplicates(
    py_source: Path, repo: Path
) -> None:
    base = ["--source", str(py_source)]
    assert ts.main(["accept", "C-NOPE-99", str(repo), "--reason", "x", *base]) == 2
    assert ts.main(["accept", "C-CFG-01", str(repo), "--reason", "  ", *base]) == 2
    assert (
        ts.main(["accept", "C-CFG-01", str(repo), "--reason", "own loader", *base]) == 0
    )
    assert ts.main(["accept", "C-CFG-01", str(repo), "--reason", "again", *base]) == 1
    text = (repo / "docs/standards-deviations.md").read_text()
    assert text.startswith("# Deviations from the standards")
    assert text.count("`C-CFG-01`") == 1


def test_malformed_bullets_are_invalid_not_deliberate(
    py_source: Path, repo: Path
) -> None:
    path = repo / "docs/standards-deviations.md"
    path.parent.mkdir(parents=True)
    path.write_text(
        "- `C-CFG-01` no date or colon\n- `C-LAYOUT-01`: ok reason (2026-11-04)\n",
        encoding="utf-8",
    )
    found, invalid = ts.read_deviations(repo)
    assert list(found) == ["C-LAYOUT-01"] and len(invalid) == 1
    assert ts.main(["deviations", str(repo), "--source", str(py_source)]) == 1


def test_a_deviation_on_a_template_id_downgrades_stale_to_deliberate(
    source: Path, repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    apply(source, repo)
    (repo / ".github/a.yml").write_text(
        "name: a\nvalue: 1\n", encoding="utf-8"
    )  # unmarked
    assert (
        ts.main(["check", str(repo), "--source", str(source), "--only", "tpl-a"]) == 1
    )
    ts.main(
        [
            "accept",
            "tpl-a",
            str(repo),
            "--reason",
            "custom pipeline",
            "--source",
            str(source),
        ]
    )
    capsys.readouterr()
    assert (
        ts.main(["check", str(repo), "--source", str(source), "--only", "tpl-a"]) == 0
    )
    assert "DELIBERATE" in capsys.readouterr().out


def test_two_sources_are_read_together_and_duplicate_ids_are_refused(
    source: Path, py_source: Path, repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    both = ["--source", str(source), "--source", str(py_source)]
    assert ts.main(["list", *both]) == 0
    out = capsys.readouterr().out
    assert "tpl-a" in out and "python-layout" in out
    assert ts.main(["verify", *both]) == 0
    assert ts.main(["list", "--source", str(source), "--source", str(source)]) == 2


def test_layout_digest_changes_force_a_bump(py_source: Path) -> None:
    manifest_path = py_source / "docs/standards/template-manifest.json"
    data = json.loads(manifest_path.read_text())
    data["templates"][0]["expect"].append({"path": "Dockerfile", "rule": "C-DOCKER-01"})
    manifest_path.write_text(json.dumps(data), encoding="utf-8")
    assert ts.main(["verify", "--source", str(py_source)]) == 1
    assert ts.main(["bump", "python-layout", "--source", str(py_source)]) == 0
    assert ts.main(["verify", "--source", str(py_source)]) == 0
