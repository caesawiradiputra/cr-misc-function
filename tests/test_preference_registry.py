"""Tests for the preference registry helper shipped with the preferences skill."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest

HELPER = (
    Path(__file__).resolve().parents[1]
    / "CLAUDE/skills/extract-session-preferences-core/registry.py"
)


@pytest.fixture
def reg(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    monkeypatch.setenv("PREF_REGISTRY_DIR", str(tmp_path))
    spec = importlib.util.spec_from_file_location("pref_registry", HELPER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run(reg: ModuleType, *argv: str) -> int:
    return int(reg.main(list(argv)))


def add(reg: ModuleType, pref: str, kw: str, **extra: str) -> int:
    argv = ["add", "--preference", pref, "--keywords", kw]
    argv += ["--scope", extra.pop("scope", "PROJECT")]
    argv += ["--session", extra.pop("session", "s1")]
    for key, val in extra.items():
        argv += [f"--{key.replace('_', '-')}", val]
    return run(reg, *argv)


def test_add_creates_unique_ids_and_routes_by_scope(reg: ModuleType) -> None:
    assert add(reg, "Keep dt as plain yyyymmdd", "dt;partition") == 0
    assert (
        add(
            reg,
            "Never overwrite pages the user is editing",
            "confluence;edit-safety",
            scope="DOMAIN",
            status="saved",
            saved_in="skill",
        )
        == 0
    )
    assert [r["ID"] for r in reg.read("project")] == ["P-001"]
    assert [r["ID"] for r in reg.read("shared")] == ["P-002"]


def test_add_refuses_near_duplicate_without_force(
    reg: ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    add(reg, "Keep technical terms in English in Bahasa docs", "bahasa;english;docs")
    code = add(
        reg,
        "Keep technical terms in English inside Bahasa docs",
        "bahasa;english;docs",
        session="s2",
    )
    assert code == 2
    assert "possible duplicate of P-001" in capsys.readouterr().err
    assert len(reg.read("project")) == 1


def test_saved_status_needs_saved_in(reg: ModuleType) -> None:
    assert add(reg, "Some rule about widgets", "widgets", status="saved") == 2
    assert reg.read("project") == []


def test_sighting_counts_each_session_once(reg: ModuleType) -> None:
    add(reg, "Some rule about widgets", "widgets;parts")
    run(reg, "update", "P-001", "--sighting", "--session", "s1")
    run(reg, "update", "P-001", "--sighting", "--session", "s2", "--repo", "repo-b")
    run(reg, "update", "P-001", "--sighting", "--session", "s2", "--repo", "repo-b")
    row = reg.read("project")[0]
    assert row["Seen"] == "2"
    assert row["Session IDs"] == "s1;s2"
    assert row["First seen"] == row["First seen"]
    assert row["Repos"] == "repo-b"


def test_sighting_without_session_is_refused(reg: ModuleType) -> None:
    add(reg, "Some rule about widgets", "widgets;parts")
    assert run(reg, "update", "P-001", "--sighting") == 2


def test_scope_change_only_through_promote(reg: ModuleType) -> None:
    add(reg, "Some rule about widgets", "widgets;parts")
    assert run(reg, "update", "P-001", "--scope", "GLOBAL") == 2
    assert reg.read("project")[0]["Scope"] == "PROJECT"


def test_promote_moves_row_and_keeps_history(reg: ModuleType) -> None:
    add(reg, "Some rule about widgets", "widgets;parts", status="approved")
    run(reg, "update", "P-001", "--sighting", "--session", "s2", "--repo", "r2")
    assert run(reg, "promote", "P-001", "--to", "DOMAIN", "--saved-in", "skill X") == 0
    assert reg.read("project") == []
    row = reg.read("shared")[0]
    assert (row["ID"], row["Scope"], row["Status"], row["Seen"]) == (
        "P-001",
        "DOMAIN",
        "saved",
        "2",
    )


def test_promote_requires_approval_and_blocks_conflicts(reg: ModuleType) -> None:
    add(reg, "Some rule about widgets", "widgets;parts")
    assert run(reg, "promote", "P-001", "--to", "DOMAIN", "--saved-in", "x") == 2
    run(reg, "update", "P-001", "--status", "approved")
    run(reg, "update", "P-001", "--conflict", "user said the opposite in repo B")
    assert reg.read("project")[0]["Status"] == "conflict"
    assert run(reg, "promote", "P-001", "--to", "DOMAIN", "--saved-in", "x") == 2
    assert len(reg.read("project")) == 1


def test_failed_promote_keeps_original_row(
    reg: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    add(reg, "Some rule about widgets", "widgets;parts", status="approved")
    original_write = reg.write

    def flaky(which: str, rows: list[dict[str, str]]) -> None:
        if which == "project":
            raise OSError("disk full")
        original_write(which, rows)

    monkeypatch.setattr(reg, "write", flaky)
    with pytest.raises(OSError):
        run(reg, "promote", "P-001", "--to", "DOMAIN", "--saved-in", "x")
    monkeypatch.setattr(reg, "write", original_write)
    assert [r["ID"] for r in reg.read("project")] == ["P-001"]
    assert reg.read("shared") == []


def test_archive_never_reuses_id(reg: ModuleType) -> None:
    add(reg, "Some rule about widgets", "widgets;parts")
    assert run(reg, "archive", "P-001", "--reason", "user rejected it") == 0
    assert reg.read("project") == []
    assert reg.read("archive")[0]["Status"] == "dropped"
    add(reg, "A different rule about gadgets and tools", "gadgets;tools")
    assert reg.read("project")[0]["ID"] == "P-002"


def test_find_ranks_shared_first_and_hides_archive(
    reg: ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    add(
        reg,
        "Never overwrite pages the user is editing",
        "confluence;edit-safety",
        scope="DOMAIN",
        status="saved",
        saved_in="skill",
    )
    add(reg, "Label appended BAST rows", "confluence;bast", session="s2")
    run(reg, "find", "--keywords", "confluence")
    out = capsys.readouterr().out
    assert out.index("P-001") < out.index("P-002")
    run(reg, "archive", "P-002", "--reason", "x")
    capsys.readouterr()
    run(reg, "find", "--keywords", "bast")
    assert "no matching records" in capsys.readouterr().out
    run(reg, "find", "--keywords", "bast", "--archive")
    assert "P-002" in capsys.readouterr().out


def test_report_flags_cross_repo_eligibility(
    reg: ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    add(reg, "Some rule about widgets", "widgets;parts", status="approved")
    run(
        reg,
        "update",
        "P-001",
        "--sighting",
        "--session",
        "s2",
        "--repo",
        "a",
        "--explicit",
    )
    run(reg, "update", "P-001", "--repo", "b")
    capsys.readouterr()
    run(reg, "report")
    out = capsys.readouterr().out
    eligible = out.split("## Eligible PROJECT -> DOMAIN")[1].split("\n## ")[0]
    assert "P-001" in eligible


def test_malformed_header_is_refused(reg: ModuleType, tmp_path: Path) -> None:
    (tmp_path / "registry-project.csv").write_text("wrong,header\n1,2\n")
    with pytest.raises(reg.RegistryError):
        reg.read("project")
