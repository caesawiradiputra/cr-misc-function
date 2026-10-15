"""Tests for the OKF spec watcher shipped with the okf-writer skill."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

WATCHER = (
    Path(__file__).resolve().parents[1]
    / "CLAUDE/skills/okf-writer/scripts/okf_watch.py"
)


def commit(sha: str, msg: str, date: str = "2026-09-01T00:00:00Z") -> dict[str, str]:
    return {"sha": sha, "date": date, "message": msg}


def snapshot(*commits: dict[str, str], version: str = "0.2") -> dict[str, Any]:
    return {
        "full_name": "org/okf",
        "archived": False,
        "pushed_at": "",
        "spec_version": version,
        "head_sha": commits[0]["sha"],
        "head_date": commits[0]["date"],
        "commits": list(commits),
    }


@pytest.fixture
def watch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    monkeypatch.setenv("OKF_WATCH_STATE", str(tmp_path / "state.json"))
    spec = importlib.util.spec_from_file_location("okf_watch", WATCHER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def use(
    watch: ModuleType, monkeypatch: pytest.MonkeyPatch, snap: dict[str, Any]
) -> None:
    monkeypatch.setattr(watch, "fetch_snapshot", lambda: snap)


def test_spec_version_is_read_from_the_first_lines(watch: ModuleType) -> None:
    assert watch.spec_version("# OKF v0.3 Spec\n") == "0.3"
    assert watch.spec_version("no version here\n") == "unknown"


def test_first_check_has_no_baseline(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    use(watch, monkeypatch, snapshot(commit("a" * 40, "x")))
    assert watch.main(["check"]) == 0
    assert "No reviewed baseline" in capsys.readouterr().out


def test_ack_then_no_change(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    use(watch, monkeypatch, snapshot(commit("a" * 40, "x")))
    assert watch.main(["ack"]) == 0
    assert watch.main(["check"]) == 0
    assert "No SPEC.md changes" in capsys.readouterr().out


def test_new_commits_are_reported_until_acked(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    use(watch, monkeypatch, snapshot(commit("a" * 40, "old")))
    watch.main(["ack"])
    newer = snapshot(
        commit("c" * 40, "add trust field"),
        commit("b" * 40, "fix typo"),
        commit("a" * 40, "old"),
    )
    use(watch, monkeypatch, newer)
    assert watch.main(["check"]) == 10
    out = capsys.readouterr().out
    assert (
        "2 SPEC.md commit(s)" in out and "add trust field" in out and "fix typo" in out
    )
    assert watch.main(["check"]) == 10  # still reported: check never moves the marker
    watch.main(["ack"])
    assert watch.main(["check"]) == 0


def test_version_change_is_flagged(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    use(watch, monkeypatch, snapshot(commit("a" * 40, "old")))
    watch.main(["ack"])
    use(
        watch,
        monkeypatch,
        snapshot(commit("b" * 40, "v0.3"), commit("a" * 40, "old"), version="0.3"),
    )
    assert watch.main(["check"]) == 10
    assert "VERSION CHANGED: reviewed v0.2 -> now v0.3" in capsys.readouterr().out


def test_acked_commit_outside_window_lists_everything(
    watch: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    use(watch, monkeypatch, snapshot(commit("a" * 40, "old")))
    watch.main(["ack"])
    use(watch, monkeypatch, snapshot(commit("c" * 40, "n2"), commit("b" * 40, "n1")))
    assert watch.main(["check"]) == 10
    assert "2 SPEC.md commit(s)" in capsys.readouterr().out


def test_max_age_skips_the_fetch(
    watch: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    use(watch, monkeypatch, snapshot(commit("a" * 40, "x")))
    watch.main(["ack"])

    def boom() -> dict[str, Any]:
        raise AssertionError("must not fetch")

    monkeypatch.setattr(watch, "fetch_snapshot", boom)
    assert watch.main(["check", "--max-age", "14"]) == 0


def test_fetch_failure_keeps_state(
    watch: ModuleType, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    use(watch, monkeypatch, snapshot(commit("a" * 40, "x")))
    watch.main(["ack"])
    before = (tmp_path / "state.json").read_text()

    def fail() -> dict[str, Any]:
        raise OSError("proxy refused")

    monkeypatch.setattr(watch, "fetch_snapshot", fail)
    assert watch.main(["check"]) == 2
    assert (tmp_path / "state.json").read_text() == before
    assert json.loads(before)["acked_sha"] == "a" * 40


def test_status_without_state(
    watch: ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    assert watch.main(["status"]) == 0
    assert "never checked" in capsys.readouterr().out
