"""Tests for the OKF bundle linter shipped with the okf-writer skill."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[1]
LINTER = ROOT / "CLAUDE/skills/okf-writer/scripts/okf_lint.py"
PILOT = ROOT / "CLAUDE/skills/bast-generator/references-okf"

GOOD = """---
type: Table
title: Orders
description: One row per order.
resource: proj.sales.orders
tags: [sales]
generated:
  by: claude-code/sonnet-5.5
  at: 2026-10-14T10:00:00+07:00
status: draft
sources:
  - id: src1
    resource: /references/ddl.md
---

Holds orders[^src1].

[^src1]: DDL.
"""


@pytest.fixture
def lint() -> ModuleType:
    spec = importlib.util.spec_from_file_location("okf_lint", LINTER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def bundle(tmp_path: Path, concept: str = GOOD, **extra: str) -> Path:
    (tmp_path / "tables").mkdir()
    (tmp_path / "tables/orders.md").write_text(concept)
    (tmp_path / "references").mkdir()
    (tmp_path / "references/ddl.md").write_text(
        "---\ntype: Reference\ntitle: DDL\ndescription: d\ntags: [x]\n---\nddl\n"
    )
    (tmp_path / "index.md").write_text(
        '---\nokf_version: "0.2"\n---\n\n# B\n\n'
        "- [Orders](/tables/orders.md): orders\n- [DDL](/references/ddl.md): ddl\n"
    )
    (tmp_path / "log.md").write_text("# Log\n\n## 2026-10-14\n\n- x\n")
    for name, text in extra.items():
        (tmp_path / name).write_text(text)
    return tmp_path


def messages(lint: ModuleType, path: Path) -> tuple[list[str], list[str]]:
    rep = lint.lint(path)
    return rep.errors, rep.warnings


def test_valid_bundle_is_clean(lint: ModuleType, tmp_path: Path) -> None:
    errors, warnings = messages(lint, bundle(tmp_path))
    assert errors == [] and warnings == []
    assert lint.main([str(tmp_path)]) == 0


def test_missing_type_is_an_error(lint: ModuleType, tmp_path: Path) -> None:
    errors, _ = messages(lint, bundle(tmp_path, GOOD.replace("type: Table\n", "")))
    assert any("`type` is required" in e for e in errors)
    assert lint.main([str(tmp_path)]) == 1


def test_missing_frontmatter_is_an_error(lint: ModuleType, tmp_path: Path) -> None:
    errors, _ = messages(lint, bundle(tmp_path, "no frontmatter here\n"))
    assert any("no frontmatter" in e for e in errors)


def test_bad_status_and_timestamp(lint: ModuleType, tmp_path: Path) -> None:
    bad = GOOD.replace("status: draft", "status: final").replace(
        "2026-10-14T10:00:00+07:00", "2026-10-14 10:00"
    )
    errors, _ = messages(lint, bundle(tmp_path, bad))
    assert any("`status` must be one of" in e for e in errors)
    assert any("generated.at" in e for e in errors)


def test_verified_needs_actor_and_counts_trust(
    lint: ModuleType, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    human = GOOD.replace(
        "status: draft",
        "verified:\n  - by: human:reviewer\n    at: 2026-10-15T09:00:00+07:00\nstatus: draft",
    )
    path = bundle(tmp_path, human)
    assert lint.main([str(path)]) == 0
    assert "human-reviewed: 1" in capsys.readouterr().out
    broken = GOOD.replace(
        "status: draft", "verified:\n  - at: 2026-10-15T09:00:00+07:00\nstatus: draft"
    )
    (path / "tables/orders.md").write_text(broken)
    errors, _ = messages(lint, path)
    assert any("verified[0] needs a `by`" in e for e in errors)


def test_reserved_files_cannot_be_concepts(lint: ModuleType, tmp_path: Path) -> None:
    path = bundle(tmp_path, index_extra="")
    (path / "tables/index.md").write_text(
        "---\ntype: Oops\n---\n- [Orders](/tables/orders.md): o\n"
    )
    errors, _ = messages(lint, path)
    assert any("reserved file must not carry concept keys" in e for e in errors)


def test_log_must_be_newest_first(lint: ModuleType, tmp_path: Path) -> None:
    path = bundle(tmp_path)
    (path / "log.md").write_text(
        "# Log\n\n## 2026-10-01\n\n- a\n\n## 2026-10-14\n\n- b\n"
    )
    errors, _ = messages(lint, path)
    assert any("newest first" in e for e in errors)


def test_warnings_for_broken_link_orphan_and_footnote(
    lint: ModuleType, tmp_path: Path
) -> None:
    path = bundle(tmp_path)
    (path / "tables/orphan.md").write_text(
        "---\ntype: Table\ntitle: T\ndescription: d\ntags: [x]\n---\nSee [x](/tables/missing.md)[^nope].\n"
    )
    errors, warnings = messages(lint, path)
    assert errors == []
    joined = "\n".join(warnings)
    assert "broken link: /tables/missing.md" in joined
    assert "not linked from any index.md" in joined
    assert "footnote [^nope]" in joined
    assert lint.main([str(path)]) == 0
    assert lint.main([str(path), "--strict"]) == 1


def test_stale_after_in_the_past_warns(lint: ModuleType, tmp_path: Path) -> None:
    stale = GOOD.replace(
        "status: draft", "stale_after: 2020-01-01T00:00:00+00:00\nstatus: draft"
    )
    _, warnings = messages(lint, bundle(tmp_path, stale))
    assert any("stale since" in w for w in warnings)


def test_not_a_directory(lint: ModuleType, tmp_path: Path) -> None:
    assert lint.main([str(tmp_path / "missing")]) == 2


def test_existing_pilot_bundle_passes(lint: ModuleType) -> None:
    errors, warnings = messages(lint, PILOT)
    assert errors == [] and warnings == []
