"""Tests for the logbook helper (CLAUDE/skills/logbook/logbook.py)."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import importlib.util
import json
import os
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "CLAUDE/skills/logbook/logbook.py"
COLUMNS = ["date", "ticket", "repo", "type", "task", "status", "notes"]
VALID_COLOURS = {"neutral", "purple", "blue", "red", "yellow", "green"}


@pytest.fixture
def lb(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    """Load a fresh copy of the helper whose paths all live in tmp_path."""
    monkeypatch.setenv("LOGBOOK_PATH", str(tmp_path / "logbook.csv"))
    spec = importlib.util.spec_from_file_location("logbook_under_test", SRC)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    """Write rows with plain csv, bypassing the helper's status validation."""
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({c: row.get(c, "") for c in COLUMNS})


def row(date: str, ticket: str, status: str, **extra: str) -> dict[str, str]:
    return {"date": date, "ticket": ticket, "task": f"task {ticket}",
            "status": status, **extra}  # fmt: skip


def test_statuses_follow_the_jira_stages(lb: ModuleType) -> None:
    assert lb.STATUSES == [
        "Analysis", "Development", "Testing", "Ready For Release",
        "Deployment", "PAT", "Done", "Fixing", "Hold",
    ]  # fmt: skip


def test_page_words_and_inverse(lb: ModuleType) -> None:
    assert lb.PAGE_STATUS["Ready For Release"] == "READY FOR RELEASE"
    assert lb.PAGE_STATUS["Deployment"] == "DEPLOYMENT"
    assert lb.PAGE_TO_LOGBOOK["PAT"] == "PAT"
    assert set(lb.PAGE_TO_LOGBOOK.values()) == set(lb.STATUSES)


def test_jira_status_knows_deployment_and_pat(lb: ModuleType) -> None:
    assert lb.JIRA_STATUS["Deployment"] == "DEPLOYMENT"
    assert lb.JIRA_STATUS["PAT"] == "PAT"
    assert lb.JIRA_STATUS["Data Development"] == "DEVELOPMENT"
    assert lb.JIRA_STATUS["Done"] == "DONE"


def test_only_done_is_finished_and_waiting_stages_are_other_court(
    lb: ModuleType,
) -> None:
    assert lb.FINISHED == {"Done"}
    assert lb.OTHER_COURT == ["TESTING", "READY FOR RELEASE", "DEPLOYMENT", "PAT"]


def test_every_page_word_has_a_valid_lozenge_colour(lb: ModuleType) -> None:
    for word in lb.PAGE_STATUS.values():
        assert lb.STATUS_COLOR[word] in VALID_COLOURS
    assert lb.STATUS_COLOR["DEPLOYMENT"] == "blue"
    assert lb.STATUS_COLOR["PAT"] == "purple"


def test_read_rows_rejects_an_old_status_word(lb: ModuleType) -> None:
    write_csv(lb.LOGBOOK, [row("2026-10-01", "DA-1", "PR to dev")])
    with pytest.raises(SystemExit):
        lb.read_rows()


@pytest.mark.parametrize(
    ("pr", "expected"),
    [
        ({"baseRefName": "master", "mergedAt": "2026-10-01T00:00:00Z", "state": "MERGED"}, ""),
        ({"baseRefName": "master", "state": "OPEN"}, ""),
        ({"baseRefName": "main", "state": "OPEN"}, ""),
        ({"baseRefName": "sit", "mergedAt": "2026-10-01T00:00:00Z", "state": "MERGED"}, "Development"),
        ({"baseRefName": "sit", "state": "OPEN"}, "Development"),
        ({"baseRefName": "dev", "state": "OPEN"}, "Testing"),
        ({"baseRefName": "dev", "mergedAt": "2026-10-01T00:00:00Z", "state": "MERGED"}, "Ready For Release"),
        ({"baseRefName": "dev", "state": "CLOSED"}, ""),
    ],
)  # fmt: skip
def test_pr_stage_maps_git_events_to_logbook_statuses(
    lb: ModuleType, pr: dict, expected: str
) -> None:
    assert lb.pr_stage(pr) == expected


def test_stage_ranks_follow_the_jira_order(lb: ModuleType) -> None:
    order = [
        "Analysis", "Development", "Testing", "Ready For Release",
        "Deployment", "PAT", "Done",
    ]  # fmt: skip
    ranks = [lb.STAGE[s] for s in order]
    assert ranks == sorted(ranks) and len(set(ranks)) == len(ranks)
    assert lb.OUTSIDE_ORDER == {"Fixing", "Hold"}


def fake_run_factory(prs: list[dict]):
    def fake_run(cmd: list[str], cwd: str) -> str | None:
        if cmd[:2] == ["git", "config"]:
            return "me\n"
        if cmd[:2] == ["git", "log"]:
            return "2026-10-14|DA-1 work\n"
        if cmd[:3] == ["gh", "pr", "list"]:
            return json.dumps(prs)
        return None

    return fake_run


def test_git_evidence_flags_a_master_pr_without_a_stage(
    lb: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    prs = [{"title": "DA-1 release", "headRefName": "dev", "baseRefName": "master",
            "state": "OPEN", "mergedAt": None, "updatedAt": "2026-10-14T00:00:00Z"}]  # fmt: skip
    monkeypatch.setattr(lb, "_run", fake_run_factory(prs))
    evidence, _ = lb.git_evidence({"r": "/x"}, "2026-10-01")
    assert evidence["DA-1"]["master"] is True
    assert evidence["DA-1"]["stage"] == ""


def make_check_env(
    lb: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    status: str,
    jira: str,
    prs: list[dict],
    refreshed: str | None = None,
) -> None:
    stamp = refreshed or dt.date.today().isoformat()
    write_csv(lb.LOGBOOK, [row("2026-10-10", "DA-1", status)])
    (tmp_path / "config.json").write_text(
        json.dumps({"repo_paths": {"r": str(tmp_path)}})
    )
    (tmp_path / "jira-cache.json").write_text(
        json.dumps(
            {"DA-1": {"jira_status": jira, "updated": "2026-10-12", "refreshed": stamp}}
        )
    )
    monkeypatch.setattr(lb, "_run", fake_run_factory(prs))


def run_check(lb: ModuleType, capsys: pytest.CaptureFixture[str]) -> str:
    lb.cmd_check(argparse.Namespace(since="2026-10-01"))
    return capsys.readouterr().out


MERGED_DEV_PR = [
    {"title": "DA-1 x", "headRefName": "fea/DA-1", "baseRefName": "dev",
     "state": "MERGED", "mergedAt": "2026-10-13T00:00:00Z",
     "updatedAt": "2026-10-13T00:00:00Z"}
]  # fmt: skip


def test_check_says_jira_wins_and_proposes_the_add_command(
    lb, tmp_path, monkeypatch, capsys
) -> None:
    make_check_env(lb, tmp_path, monkeypatch, "Testing", "Ready For Release", [])
    out = run_check(lb, capsys)
    assert "Jira wins" in out
    assert 'add --ticket DA-1 --status "Ready For Release"' in out


def test_check_flags_a_row_behind_a_merged_dev_pr(
    lb, tmp_path, monkeypatch, capsys
) -> None:
    make_check_env(lb, tmp_path, monkeypatch, "Testing", "Testing", MERGED_DEV_PR)
    assert "but a PR is at 'Ready For Release'" in run_check(lb, capsys)


def test_check_ignores_pr_lag_for_hold_and_fixing(
    lb, tmp_path, monkeypatch, capsys
) -> None:
    make_check_env(lb, tmp_path, monkeypatch, "Hold", "Hold", MERGED_DEV_PR)
    assert "a PR is at" not in run_check(lb, capsys)


def cache_args(**kw: str) -> argparse.Namespace:
    base = {"action": "set", "ticket": "DA-1", "created": "", "source": "",
            "description": "", "summary": "", "jira_status": "", "updated": "",
            "project": "", "before_hold": "", "hold_since": "", "pat_since": "",
            "track": ""}  # fmt: skip
    return argparse.Namespace(**{**base, **kw})


def test_cache_set_stamps_refreshed_when_a_jira_status_is_stored(
    lb: ModuleType,
) -> None:
    lb.cmd_cache(cache_args(jira_status="PAT", pat_since="2026-10-10"))
    entry = lb.load_cache()["DA-1"]
    assert entry["jira_status"] == "PAT"
    assert entry["pat_since"] == "2026-10-10"
    assert entry["refreshed"] == dt.date.today().isoformat()


def test_cache_set_rejects_a_bad_pat_since(lb: ModuleType) -> None:
    with pytest.raises(SystemExit):
        lb.cmd_cache(cache_args(pat_since="10/10/2026"))


def test_jira_fresh_window(lb: ModuleType) -> None:
    today = dt.date(2026, 10, 15)
    assert lb.jira_fresh({"refreshed": "2026-10-08"}, today) is True
    assert lb.jira_fresh({"refreshed": "2026-10-07"}, today) is False
    assert lb.jira_fresh({}, today) is False


def test_item_status_prefers_fresh_jira_over_the_logbook(lb: ModuleType) -> None:
    last = {"status": "Testing"}
    fresh = {
        "jira_status": "Ready For Release",
        "refreshed": dt.date.today().isoformat(),
    }
    assert lb.item_status(last, fresh) == "READY FOR RELEASE"


def test_item_status_falls_back_to_the_logbook_when_stale_or_unmapped(
    lb: ModuleType,
) -> None:
    last = {"status": "Testing"}
    stale = {"jira_status": "PAT", "refreshed": "2020-01-01"}
    assert lb.item_status(last, stale) == "TESTING"
    today = dt.date.today().isoformat()
    assert (
        lb.item_status(last, {"jira_status": "Weird", "refreshed": today}) == "TESTING"
    )
    assert lb.item_status({"status": ""}, {"jira_status": "Weird"}) == "WEIRD"


TODAY = dt.date(2026, 10, 15)


def migrate(lb: ModuleType, rows, cache=None, resolve=None):
    return lb.migrate_rows(rows, cache or {}, TODAY, resolve or {})


def test_legacy_words_map_and_new_words_pass_through(lb: ModuleType) -> None:
    rows = [
        row("2026-09-01", "DA-1", "In progress"), row("2026-09-01", "DA-2", "PR to dev"),
        row("2026-09-01", "DA-3", "Merged to sit"), row("2026-09-01", "D", "Merged to dev"),
        row("2026-09-01", "E", "PR to master"), row("2026-09-01", "F", "Analysis"),
        row("2026-09-01", "G", "Fixing"), row("2026-09-01", "H", "Hold"),
        row("2026-09-01", "I", "Done"), row("2026-09-01", "J", ""),
    ]  # fmt: skip
    new, _, review = migrate(lb, rows)
    assert [r["status"] for r in new] == [
        "Development", "Testing", "Development", "Ready For Release",
        "Ready For Release", "Analysis", "Fixing", "Hold", "Done", "",
    ]  # fmt: skip
    assert review == []


@pytest.mark.parametrize(
    ("jira", "expected"),
    [
        ("Hold", "Hold"), ("Testing", "Testing"),
        ("Ready For Release", "Ready For Release"),
        ("Deployment", "Deployment"), ("PAT", "PAT"), ("Done", "Done"),
    ],
)  # fmt: skip
def test_released_takes_the_known_jira_status(lb, jira, expected) -> None:
    rows = [row("2026-08-01", "DA-1", "Released")]
    new, _, review = migrate(lb, rows, {"DA-1": {"jira_status": jira}})
    assert new[0]["status"] == expected and review == []


@pytest.mark.parametrize(
    "cache",
    [
        {},
        {"DA-1": {}},
        {"DA-1": {"jira_status": "Weird"}},
        {"DA-1": {"jira_status": "To Do"}},
    ],
)
def test_released_with_unknown_or_unmapped_jira_status_goes_to_review(
    lb, cache
) -> None:
    new, _, review = migrate(lb, [row("2026-08-01", "DA-1", "Released")], cache)
    assert review == [("2026-08-01", "DA-1")]
    assert new[0]["status"] == "Released"  # nothing guessed, nothing written as Done


def test_recent_boundary_is_flagged_but_keeps_the_jira_status(lb: ModuleType) -> None:
    cache = {"DA-1": {"jira_status": "Hold"}, "DA-2": {"jira_status": "Hold"}}
    rows = [
        row("2026-10-08", "DA-1", "Released"),
        row("2026-10-07", "DA-2", "Released"),
    ]
    new, report, review = migrate(lb, rows, cache)  # 7 and 8 days old
    assert [r["status"] for r in new] == ["Hold", "Hold"] and review == []
    flagged = [line for line in report if "check" in line]
    assert len(flagged) == 1 and " DA-1:" in flagged[0]


def test_only_the_last_released_row_takes_the_jira_status(lb: ModuleType) -> None:
    rows = [
        row("2026-08-01", "DA-1", "Released"),
        row("2026-09-01", "DA-1", "Released"),
    ]
    new, _, _ = migrate(lb, rows, {"DA-1": {"jira_status": "PAT"}})
    assert [r["status"] for r in new] == ["Done", "PAT"]


def test_resolve_decides_a_reviewed_row(lb: ModuleType) -> None:
    rows = [row("2026-08-01", "DA-1", "Released")]
    new, _, review = migrate(lb, rows, resolve={"DA-1": "PAT"})
    assert new[0]["status"] == "PAT" and review == []


def test_unknown_legacy_word_aborts(lb: ModuleType) -> None:
    with pytest.raises(SystemExit):
        migrate(lb, [row("2026-08-01", "DA-1", "Mystery")])


def test_every_released_row_has_exactly_one_outcome(lb: ModuleType) -> None:
    rows = [row("2026-08-01", t, "Released") for t in ("DA-1", "DA-2", "DA-3")]
    cache = {"DA-1": {"jira_status": "Done"}, "DA-2": {"jira_status": "Weird"}}
    new, _, review = migrate(lb, rows, cache)
    resolved = [r for r in new if r["status"] in lb.STATUSES]
    assert len(resolved) + len(review) == len(rows)


def run_migrate(lb: ModuleType, *, dry_run: bool, resolve=None) -> None:
    lb.cmd_migrate(argparse.Namespace(dry_run=dry_run, resolve=resolve or []))


def test_old_csv_is_unreadable_by_read_rows_but_migrates(
    lb: ModuleType, tmp_path: Path
) -> None:
    write_csv(
        lb.LOGBOOK,
        [row("2026-09-01", "DA-1", "PR to dev"), row("2026-09-02", "DA-1", "Released")],
    )
    (tmp_path / "jira-cache.json").write_text('{"DA-1": {"jira_status": "Done"}}')
    with pytest.raises(SystemExit):
        lb.read_rows()
    run_migrate(lb, dry_run=False)
    assert [r["status"] for r in lb.read_rows()] == ["Testing", "Done"]
    assert list(tmp_path.glob("logbook.csv.pre-migration-*"))


def test_dry_run_writes_nothing(lb: ModuleType, tmp_path: Path) -> None:
    write_csv(lb.LOGBOOK, [row("2026-09-01", "DA-1", "PR to dev")])
    before = lb.LOGBOOK.read_text()
    run_migrate(lb, dry_run=True)
    assert lb.LOGBOOK.read_text() == before
    assert not list(tmp_path.glob("*.pre-migration-*"))


def test_unresolved_review_blocks_the_write(lb: ModuleType) -> None:
    write_csv(lb.LOGBOOK, [row("2026-09-01", "DA-1", "Released")])
    before = lb.LOGBOOK.read_text()
    with pytest.raises(SystemExit):
        run_migrate(lb, dry_run=False)
    assert lb.LOGBOOK.read_text() == before


def test_archive_file_is_migrated_too(lb: ModuleType, tmp_path: Path) -> None:
    write_csv(lb.LOGBOOK, [row("2026-09-01", "DA-1", "In progress")])
    write_csv(lb.ARCHIVE, [row("2026-06-01", "DA-26", "Released")])
    (tmp_path / "jira-cache.json").write_text('{"DA-26": {"jira_status": "Done"}}')
    run_migrate(lb, dry_run=False)
    assert lb.read_rows(lb.ARCHIVE)[0]["status"] == "Done"


def test_non_jira_work_released_becomes_done_without_review(lb: ModuleType) -> None:
    rows = [
        row("2026-10-01", "bug-12", "Released"),
        row("2026-10-02", "some-slug", "Released"),
    ]
    new, _, review = migrate(lb, rows)
    assert [r["status"] for r in new] == ["Done", "Done"] and review == []


OLD_WORDS = [
    "`In progress`", "`PR to dev`", "`Merged to dev`", "`Merged to sit`",
    "`PR to master`", "`Released`", "Ready to Release",
]  # fmt: skip
SWEPT = [
    "CLAUDE/CLAUDE.md",
    "CLAUDE/commands/generate-pr-message.md",
    "CLAUDE/skills/jira-ticket-kickoff/SKILL.md",
    "CLAUDE/skills/bast-generator/SKILL.md",
    "CLAUDE/skills/logbook/SKILL.md",
    "docs/guidelines/DEV-WORKFLOW.md",
]


@pytest.mark.parametrize("name", SWEPT)
def test_instruction_files_use_only_the_new_status_words(name: str) -> None:
    text = (ROOT / name).read_text(encoding="utf-8")
    assert [w for w in OLD_WORDS if w in text] == []


def test_config_example_lists_the_four_waiting_stages() -> None:
    path = ROOT / "CLAUDE/skills/logbook/config.example.json"
    cfg = json.loads(path.read_text())
    assert cfg["other_court"] == ["TESTING", "READY FOR RELEASE", "DEPLOYMENT", "PAT"]


def ev(
    stage: str = "",
    last: str = "2026-10-14",
    master: bool = False,
    repos: tuple[str, ...] = ("r",),
) -> dict:
    return {"stage": stage, "last": last, "repos": set(repos), "master": master}


def entry(
    lb, status="", jira="", info_extra=None, evidence=None, live=True, today=TODAY
):
    info = {"jira_status": jira, **(info_extra or {})}
    item = [row("2026-10-10", "DA-1", status)] if status else []
    return lb.board_entry("DA-1", info, item, evidence, today, live)


def flag_texts(e: dict) -> list[str]:
    return [text for text, _ in e["flags"]]


def test_word_comes_from_jira_then_logbook(lb: ModuleType) -> None:
    assert entry(lb, "Testing", "Ready For Release")["word"] == "READY FOR RELEASE"
    assert entry(lb, "Testing", "")["word"] == "TESTING"
    assert entry(lb, "", "")["word"] == "TODO"


def test_merged_dev_pr_with_jira_still_testing_is_flagged(lb: ModuleType) -> None:
    e = entry(lb, "Testing", "Testing", evidence=ev("Ready For Release"))
    assert any("merged into dev" in t for t in flag_texts(e))


def test_master_pr_while_jira_testing_is_flagged_but_not_at_ready_for_release(
    lb: ModuleType,
) -> None:
    assert entry(lb, "", "Testing", evidence=ev(master=True))["flags"]
    assert entry(lb, "", "Ready For Release", evidence=ev(master=True))["flags"] == []


def test_commits_while_jira_is_still_analysis_are_flagged(lb: ModuleType) -> None:
    e = entry(lb, "", "Data Analysis", evidence=ev("Development"))
    assert any("Data Analysis" in t for t in flag_texts(e))


def test_pat_age_flag_boundary_and_unknown_date(lb: ModuleType) -> None:
    old = entry(lb, "", "PAT", {"pat_since": "2026-10-08"})  # 7 days
    young = entry(lb, "", "PAT", {"pat_since": "2026-10-09"})  # 6 days
    unknown = entry(lb, "", "PAT")
    assert any("Done" in fix for _, fix in old["flags"])
    assert not any("Done" in fix for _, fix in young["flags"])
    assert any("PAT date unknown" in t for t in flag_texts(unknown))
    assert not any("Done" in fix for _, fix in unknown["flags"])


def test_hold_wins_over_workflow_flags(lb: ModuleType) -> None:
    e = entry(
        lb, "Testing", "Hold", {"hold_since": "2026-10-01"},
        evidence=ev("Ready For Release", master=True),
    )  # fmt: skip
    assert e["word"] == "HOLD"
    assert "on hold since 2026-10-01" in e["next"]
    assert all(t.startswith("note:") for t in flag_texts(e))


def test_degraded_mode_suppresses_jira_dependent_flags(lb: ModuleType) -> None:
    e = entry(lb, "Testing", "Testing", evidence=ev("Ready For Release"), live=False)
    assert e["flags"] == []


def test_jira_and_logbook_difference_proposes_the_add_command(lb: ModuleType) -> None:
    e = entry(lb, "Testing", "Deployment")
    assert any('--status "Deployment"' in fix for _, fix in e["flags"])


def test_derive_board_orders_by_stage_and_detects_live_mode(lb: ModuleType) -> None:
    today = TODAY.isoformat()
    cache = {
        "DA-2": {"track": True, "jira_status": "Testing", "refreshed": today},
        "DA-1": {"track": True, "jira_status": "Data Development", "refreshed": today},
    }
    entries, live, refreshed = lb.derive_board(cache, [], {}, TODAY)
    assert [e["ticket"] for e in entries] == ["DA-1", "DA-2"]
    assert live is True and refreshed == today
    cache["DA-1"]["refreshed"] = cache["DA-2"]["refreshed"] = "2026-10-01"
    _, live, refreshed = lb.derive_board(cache, [], {}, TODAY)
    assert live is False and refreshed == "2026-10-01"


def test_derive_board_skips_finished_tickets(lb: ModuleType) -> None:
    items = [[row("2026-10-01", "DA-9", "Done")]]
    entries, _, _ = lb.derive_board({}, items, {}, TODAY)
    assert entries == []


def test_render_board_groups_by_stage_and_shows_flags(lb: ModuleType) -> None:
    e = entry(lb, "Testing", "Testing", evidence=ev("Ready For Release"))
    text = lb.render_board([e], True, TODAY.isoformat(), [])
    assert "## TESTING (1)" in text
    assert "DA-1" in text and "next:" in text
    assert "PR merged into dev but Jira is still Testing" in text
    assert "STALE" not in text


def test_render_board_shows_the_stale_banner_in_degraded_mode(lb: ModuleType) -> None:
    notes = ["r: gh pr list unavailable (commits only)"]
    text = lb.render_board(
        [entry(lb, "Testing", "Testing")], False, "2026-10-01", notes
    )
    assert "STALE" in text and "2026-10-01" in text
    assert "gh pr list unavailable" in text


def test_pipeline_command_prints_and_writes_nothing(
    lb: ModuleType, tmp_path: Path, monkeypatch, capsys
) -> None:
    write_csv(lb.LOGBOOK, [row("2026-10-10", "DA-1", "Testing")])
    (tmp_path / "config.json").write_text(
        json.dumps({"repo_paths": {"r": str(tmp_path)}})
    )
    cache = {"DA-1": {"track": True, "jira_status": "Testing",
                      "refreshed": dt.date.today().isoformat()}}  # fmt: skip
    (tmp_path / "jira-cache.json").write_text(json.dumps(cache))
    monkeypatch.setattr(lb, "_run", fake_run_factory([]))
    before = lb.LOGBOOK.read_text()
    lb.cmd_pipeline(argparse.Namespace(since=""))
    assert "## TESTING (1)" in capsys.readouterr().out
    assert lb.LOGBOOK.read_text() == before


def test_pipeline_works_without_gh(
    lb: ModuleType, tmp_path: Path, monkeypatch, capsys
) -> None:
    (tmp_path / "config.json").write_text(
        json.dumps({"repo_paths": {"r": str(tmp_path)}})
    )
    cache = {"DA-1": {"track": True, "jira_status": "Data Development",
                      "refreshed": dt.date.today().isoformat()}}  # fmt: skip
    (tmp_path / "jira-cache.json").write_text(json.dumps(cache))

    def no_gh(cmd: list[str], cwd: str) -> str | None:
        if cmd[:2] == ["git", "config"]:
            return "me\n"
        if cmd[:2] == ["git", "log"]:
            return ""
        return None

    monkeypatch.setattr(lb, "_run", no_gh)
    lb.cmd_pipeline(argparse.Namespace(since=""))
    out = capsys.readouterr().out
    assert "gh pr list unavailable" in out and "DA-1" in out


def test_pipeline_command_file_exists_and_calls_the_helper() -> None:
    text = (ROOT / "CLAUDE/commands/pipeline.md").read_text(encoding="utf-8")
    assert text.startswith("---\ndescription:")
    assert "logbook.py pipeline" in text and "pat-since" in text


def test_check_ignores_a_stale_jira_cache(lb, tmp_path, monkeypatch, capsys) -> None:
    make_check_env(lb, tmp_path, monkeypatch, "Done", "PAT", [], refreshed="2020-01-01")
    assert "Jira wins" not in run_check(lb, capsys)


def test_board_live_is_decided_per_ticket(lb: ModuleType) -> None:
    today = TODAY.isoformat()
    cache = {
        "DA-1": {"track": True, "jira_status": "Testing", "refreshed": today},
        "DA-2": {"track": True, "jira_status": "Testing", "refreshed": "2026-09-25"},
    }
    evidence = {"DA-1": ev("Ready For Release"), "DA-2": ev("Ready For Release")}
    entries, live, _ = lb.derive_board(cache, [], evidence, TODAY)
    by = {e["ticket"]: e for e in entries}
    assert live is True  # the newest refresh is today, so the banner stays off
    assert by["DA-1"]["flags"] and by["DA-1"]["stale"] is False
    assert by["DA-2"]["flags"] == [] and by["DA-2"]["stale"] is True


def test_board_says_unknown_when_the_repo_is_not_scanned(lb: ModuleType) -> None:
    today = TODAY.isoformat()
    cache = {"DA-1": {"track": True, "jira_status": "Testing", "refreshed": today}}
    items = [[row("2026-10-10", "DA-1", "Testing", repo="other")]]
    entries, _, _ = lb.derive_board(cache, items, {}, TODAY, {"r": "/x"})
    assert entries[0]["git"] == "unknown (repo not tracked)"
    items = [[row("2026-10-10", "DA-1", "Testing", repo="r")]]
    entries, _, _ = lb.derive_board(cache, items, {}, TODAY, {"r": "/x"})
    assert entries[0]["git"] == "none"
    items = [[row("2026-10-10", "DA-1", "Testing")]]
    entries, _, _ = lb.derive_board(cache, items, {}, TODAY, {"r": "/x"})
    assert entries[0]["git"] == "unknown (no repo)"


def test_board_notes_a_repo_mismatch(lb: ModuleType) -> None:
    item = [row("2026-10-10", "DA-1", "Testing", repo="old-repo")]
    e = lb.board_entry(
        "DA-1",
        {"jira_status": "Testing"},
        item,
        ev("Testing", repos=("new-repo",)),
        TODAY,
        True,
    )
    assert any(t.startswith("note:") and "old-repo" in t for t in flag_texts(e))


def test_render_marks_a_stale_ticket(lb: ModuleType) -> None:
    e = entry(lb, "Testing", "Testing")
    e["stale"] = True
    assert "(stale)" in lb.render_board([e], True, TODAY.isoformat(), [])


def test_trigger_prompts_are_in_the_skills() -> None:
    def text(name: str) -> str:
        return (ROOT / name).read_text(encoding="utf-8")

    assert "offer to start the ticket" in text("CLAUDE/skills/jira-in-da-sync/SKILL.md")
    assert "`Data Development`" in text("CLAUDE/skills/jira-ticket-kickoff/SKILL.md")
    assert "UAT" in text("CLAUDE/skills/bast-generator/SKILL.md")
    assert "CAB approval" in text("CLAUDE/commands/generate-pr-message.md")


def test_non_jira_work_next_step_skips_cab(lb: ModuleType) -> None:
    item = [row("2026-10-10", "dev-workflow", "Ready For Release")]
    e = lb.board_entry("dev-workflow", {}, item, None, TODAY, False)
    assert "CAB" not in e["next"] and "Done" in e["next"]
    jira_e = lb.board_entry(
        "DA-1", {}, [row("2026-10-10", "DA-1", "Ready For Release")], None, TODAY, False
    )
    assert "CAB" in jira_e["next"]


def run_archive(lb: ModuleType, capsys: pytest.CaptureFixture[str]) -> str:
    lb.cmd_archive(argparse.Namespace(days=7, dry_run=True))
    return capsys.readouterr().out


def archive_env(
    lb: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    rows: list[dict[str, str]],
    today: dt.date,
) -> None:
    write_csv(lb.LOGBOOK, rows)
    real = dt.date

    class FixedDate(real):  # type: ignore[valid-type, misc]
        @classmethod
        def today(cls) -> dt.date:
            return today

    monkeypatch.setattr(lb, "dt", SimpleNamespace(**{**vars(dt), "date": FixedDate}))


def test_archive_counts_seven_days_from_done_not_from_last_activity(
    lb: ModuleType, monkeypatch, capsys
) -> None:
    rows = [
        row("2026-10-01", "DA-1", "Done"),
        row("2026-10-14", "DA-1", "Done"),  # a later note must not reset the clock
    ]
    archive_env(lb, monkeypatch, rows, dt.date(2026, 10, 15))
    assert "would archive: DA-1" in run_archive(lb, capsys)


def test_archive_waits_until_seven_days_after_done(
    lb: ModuleType, monkeypatch, capsys
) -> None:
    archive_env(
        lb, monkeypatch, [row("2026-10-10", "DA-1", "Done")], dt.date(2026, 10, 15)
    )
    assert "nothing to archive" in run_archive(lb, capsys)


def test_archive_boundary_is_exactly_seven_days(
    lb: ModuleType, monkeypatch, capsys
) -> None:
    archive_env(
        lb, monkeypatch, [row("2026-10-08", "DA-1", "Done")], dt.date(2026, 10, 15)
    )
    assert "would archive: DA-1" in run_archive(lb, capsys)


def test_archive_restarts_the_clock_when_a_ticket_leaves_and_returns_to_done(
    lb: ModuleType, monkeypatch, capsys
) -> None:
    rows = [
        row("2026-10-01", "DA-1", "Done"),
        row("2026-10-05", "DA-1", "Testing"),
        row("2026-10-12", "DA-1", "Done"),
    ]
    archive_env(lb, monkeypatch, rows, dt.date(2026, 10, 15))
    assert "nothing to archive" in run_archive(lb, capsys)


REG_COLUMNS = [
    "Column 1", "Status", "TYPE CAB", "Type", "IN / Project", "Kategori",
    "Tanggal \nRegister CAB", "Nama CAB", "Link ", "Requester \nPIC CAB",
    "User Requester", "jadwal CAB", "PIC Deploy Ops", "PIC Deploy Dev",
    "Last PAT Date", "Status PAT", "Deploye Plan Date", "Deploy Plan Time",
    "Deployed Real Date", "Closed Date", "Approval By", "Column 2",
]  # fmt: skip
_REG_ALIAS = {
    "n": "Column 1", "status": "Status", "reg": "Tanggal \nRegister CAB",
    "name": "Nama CAB", "cab": "jadwal CAB", "pat_end": "Last PAT Date",
    "pat_status": "Status PAT", "plan": "Deploye Plan Date",
    "real": "Deployed Real Date", "dev": "PIC Deploy Dev",
    "requester": "Requester \nPIC CAB",
}  # fmt: skip


def reg_line(**kw: str) -> list[str]:
    """One register row aligned with REG_COLUMNS (aliases above, defaults blank)."""
    cells = dict.fromkeys(REG_COLUMNS, "")
    cells["Status"] = "Closed"
    cells["Nama CAB"] = "[BAST] DA-1234 - x"
    for key, value in kw.items():
        cells[_REG_ALIAS[key]] = value
    return [cells[c] for c in REG_COLUMNS]


def write_register(
    path: Path,
    lines: list[list[str]],
    *,
    delimiter: str = ",",
    encoding: str = "utf-8-sig",
    terminator: str = "\n",
    header: list[str] | None = None,
) -> None:
    with path.open("w", newline="", encoding=encoding) as f:
        writer = csv.writer(f, delimiter=delimiter, lineterminator=terminator)
        writer.writerow(header or REG_COLUMNS)
        writer.writerows(lines)


def test_read_register_matches_wrapped_headers(lb: ModuleType, tmp_path: Path) -> None:
    path = tmp_path / "reg.csv"
    write_register(path, [reg_line(n="7", reg="10/12/2026", cab="14/10/26")])
    out = lb.read_register(path)
    assert out["off"] == "" and out["encoding"] == "utf-8-sig"
    row = out["rows"][0]
    assert row["Column 1"] == "7" and row["Tanggal Register CAB"] == "10/12/2026"
    assert row["jadwal CAB"] == "14/10/26" and row["Nama CAB"] == "[BAST] DA-1234 - x"
    assert out["mtime"].utcoffset() == dt.timedelta(hours=7)


@pytest.mark.parametrize("terminator", ["\n", "\r\n"])
def test_read_register_handles_bom_and_crlf(lb, tmp_path, terminator) -> None:
    path = tmp_path / "reg.csv"
    write_register(path, [reg_line(n="1")], terminator=terminator)
    assert lb.read_register(path)["rows"][0]["Column 1"] == "1"


def test_read_register_detects_semicolon_and_tab(lb, tmp_path) -> None:
    for delimiter in (";", "\t"):
        path = tmp_path / "reg.csv"
        write_register(path, [reg_line(n="5")], delimiter=delimiter)
        out = lb.read_register(path)
        assert out["delimiter"] == delimiter and out["rows"][0]["Column 1"] == "5"


def test_read_register_falls_back_to_cp1252(lb, tmp_path) -> None:
    path = tmp_path / "reg.csv"
    write_register(path, [reg_line(name="SRF – DA-1234")], encoding="cp1252")
    out = lb.read_register(path)
    assert out["encoding"] == "cp1252" and "–" in out["rows"][0]["Nama CAB"]


def test_read_register_accepts_no_for_column_1(lb, tmp_path) -> None:
    path = tmp_path / "cab-register.csv"
    header = ["No" if c == "Column 1" else c for c in REG_COLUMNS]
    write_register(path, [reg_line(n="7")], header=header)
    assert lb.read_register(path)["rows"][0]["Column 1"] == "7"


def test_read_register_decodes_a_file_mixing_utf8_and_cp1252(lb, tmp_path) -> None:
    path = tmp_path / "cab-register.csv"
    write_register(path, [reg_line(n="1", name="DA-1 \u201cx\u201d")], encoding="utf-8")
    with path.open("ab") as f:  # a second tool appended a cp1252 row
        f.write(b"2,Closed,,,,,,DA-2 Can\x92t,,,,,,,,,,,,,,\n")
    out = lb.read_register(path)
    assert out["encoding"] == "mixed utf-8/cp1252"
    names = [r["Nama CAB"] for r in out["rows"]]
    assert names == ["DA-1 \u201cx\u201d", "DA-2 Can\u2019t"]


def test_read_register_reads_the_real_export_shape(lb, tmp_path) -> None:
    """Semicolons, cp1252 and the 'No' header together, as in the Excel export."""
    path = tmp_path / "cab-register.csv"
    header = ["No" if c == "Column 1" else c for c in REG_COLUMNS]
    write_register(
        path,
        [reg_line(n="3", name="SRF \u2013 DA-1234")],
        delimiter=";",
        encoding="cp1252",
        header=header,
    )
    out = lb.read_register(path)
    assert out["delimiter"] == ";" and not out["off"]
    assert out["rows"][0]["Column 1"] == "3" and "\u2013" in out["rows"][0]["Nama CAB"]


def test_own_register_rows_keeps_owner_rows_and_drops_duplicates(lb) -> None:
    def full(**kw: str) -> dict[str, str]:
        return dict(zip(lb.CAB_COLUMNS, reg_line(**kw), strict=False))

    mine = {**dict.fromkeys(lb.CAB_COLUMNS, ""), "PIC Deploy Dev": "Caesa, Fandi"}
    asked = {
        **dict.fromkeys(lb.CAB_COLUMNS, ""),
        "Requester PIC CAB": "caesa",
        "Nama CAB": "b",
    }
    other = {
        **dict.fromkeys(lb.CAB_COLUMNS, ""),
        "PIC Deploy Dev": "Rizal",
        "Nama CAB": "c",
    }
    cfg = {"pic": "Caesa Ram"}
    assert lb.own_register_rows([mine, mine, asked, other], cfg) == [mine, asked]
    assert lb.own_register_rows([other], {"cab_owner": "rizal"}) == [other]
    assert lb.own_register_rows([other], {}) == [other]  # no owner: keep every row
    assert full(dev="x")  # the alias used by the helper above exists


def test_read_register_pads_short_rows_and_skips_blank_rows(lb, tmp_path) -> None:
    path = tmp_path / "reg.csv"
    write_register(path, [reg_line(n="1")[:3], [""] * 22, ["", "", ""]])
    out = lb.read_register(path)
    assert len(out["rows"]) == 1 and out["rows"][0]["Nama CAB"] == ""


def test_read_register_turns_the_feature_off_instead_of_crashing(
    lb: ModuleType, tmp_path: Path
) -> None:
    missing = lb.read_register(tmp_path / "nope.csv")
    assert missing["off"] and missing["rows"] == []
    assert lb.read_register(tmp_path)["off"]  # a directory is unreadable
    empty = tmp_path / "empty.csv"
    empty.write_text("")
    assert lb.read_register(empty)["off"]
    header_only = tmp_path / "h.csv"
    write_register(header_only, [])
    out = lb.read_register(header_only)
    assert out["off"] == "" and out["rows"] == []


def test_read_register_names_a_missing_required_column(lb, tmp_path) -> None:
    path = tmp_path / "reg.csv"
    header = [c for c in REG_COLUMNS if c != "Last PAT Date"]
    write_register(path, [], header=header)
    assert "Last PAT Date" in lb.read_register(path)["off"]


def test_read_register_reports_a_duplicate_column_and_keeps_the_first(
    lb, tmp_path
) -> None:
    path = tmp_path / "reg.csv"
    header = [*REG_COLUMNS, "Status"]
    write_register(path, [[*reg_line(status="Closed"), "Pending"]], header=header)
    out = lb.read_register(path)
    assert out["rows"][0]["Status"] == "Closed"
    assert any("duplicate" in p for p in out["problems"])


def test_read_register_ignores_extra_columns(lb, tmp_path) -> None:
    path = tmp_path / "reg.csv"
    write_register(path, [[*reg_line(n="3"), "x"]], header=[*REG_COLUMNS, "Extra"])
    assert lb.read_register(path)["rows"][0]["Column 1"] == "3"


def test_resolve_register_path_never_exits(lb, tmp_path, monkeypatch) -> None:
    assert lb.resolve_register_path({"cab_register": "~/x.csv"}).name == "x.csv"
    monkeypatch.delenv("LOGBOOK_WINDOWS_DIR", raising=False)
    monkeypatch.setattr(lb, "WINDOWS_DIR_FILE", tmp_path / "missing.txt")
    assert lb.resolve_register_path({}) is None
    monkeypatch.setenv("LOGBOOK_WINDOWS_DIR", str(tmp_path / "win"))
    assert lb.resolve_register_path({}) == tmp_path / "win" / "cab-register.csv"


def raw(**kw: str) -> dict[str, str]:
    """A row as read_register returns it, with synthetic defaults."""
    base = dict.fromkeys(
        ["Column 1", "Status", "Tanggal Register CAB", "Nama CAB", "jadwal CAB",
         "Deployed Real Date", "Last PAT Date", "Status PAT", "TYPE CAB",
         "Kategori", "Deploye Plan Date"], ""
    )  # fmt: skip
    base.update({"Column 1": "1", "Status": "Closed", "Nama CAB": "[BAST] DA-1234 - x"})
    alias = {"n": "Column 1", "status": "Status", "reg": "Tanggal Register CAB",
             "name": "Nama CAB", "cab": "jadwal CAB", "real": "Deployed Real Date",
             "pat_end": "Last PAT Date", "pat_status": "Status PAT",
             "plan": "Deploye Plan Date"}  # fmt: skip
    base.update({alias[k]: v for k, v in kw.items()})
    return base


def build(
    lb: ModuleType, rows: list[dict[str, str]], cfg=None, today=dt.date(2026, 10, 15)
):
    read = {"rows": rows, "problems": [], "encoding": "utf-8-sig",
            "delimiter": ",", "mtime": None, "off": ""}  # fmt: skip
    return lb.build_register(read, cfg or {}, today)


@pytest.mark.parametrize(
    ("name", "keys"),
    [
        ("[BAST] DA-1234 - x", ["DA-1234"]),
        ("DA1234 - x", ["DA-1234"]),
        ("DA 1234 - x", ["DA-1234"]),
        ("da-1234 and DA-5678", ["DA-1234", "DA-5678"]),
        ("DA-1234 / DA-1234", ["DA-1234"]),
        ("soda 1234 is not a key", []),
        ("BAST Master Data", []),
    ],
)
def test_ticket_keys_are_extracted(lb, name, keys) -> None:
    assert build(lb, [raw(name=name)])["rows"][0]["keys"] == keys


def test_fixed_formats_two_digit_years_and_clock_times(lb: ModuleType) -> None:
    reg = build(lb, [raw(reg="10/12/2026", cab="14/10/26", plan="15/10/26",
                         real="15/10/2026", pat_end="22/10/26")])  # fmt: skip
    row = reg["rows"][0]
    assert row["reg"] == dt.date(2026, 10, 12) and row["cab"] == dt.date(2026, 10, 14)
    assert row["plan"] == dt.date(2026, 10, 15) and row["real"] == dt.date(2026, 10, 15)
    assert row["pat_end"] == dt.date(2026, 10, 22)
    assert not any("Closed Date" in p for p in reg["problems"])


def test_mixed_register_column_uses_the_lag_window(lb: ModuleType) -> None:
    read = lambda reg, cab: lb.register_date(reg, cab, 21)  # noqa: E731
    cab = dt.date(2026, 1, 7)
    assert read("6/1/2026", cab) == (dt.date(2026, 1, 6), "swapped")  # typed 6 Jan
    assert read("1/6/2026", cab) == (dt.date(2026, 1, 6), "")  # M/D already plausible
    assert read("12/31/2025", dt.date(2026, 1, 2)) == (dt.date(2025, 12, 31), "")
    assert read("17/6/2026", dt.date(2026, 6, 17)) == (dt.date(2026, 6, 17), "swapped")
    assert read("5/5/2026", dt.date(2026, 5, 6)) == (dt.date(2026, 5, 5), "")
    assert read("7/27/2026", dt.date(2026, 10, 1)) == (None, "unknown")


def test_register_date_without_a_cab_date_is_unverified(lb: ModuleType) -> None:
    assert lb.register_date("7/27/2026", None, 21) == (
        dt.date(2026, 7, 27),
        "unverified",
    )
    assert lb.register_date("27/7/2026", None, 21) == (
        dt.date(2026, 7, 27),
        "unverified",
    )
    assert lb.register_date("", None, 21) == (None, "")


def test_two_readings_of_a_cell_are_at_least_27_days_apart(lb: ModuleType) -> None:
    closest = 999
    for year in (2026, 2028):
        for a in range(1, 13):
            for b in range(1, 13):
                if a == b:
                    continue
                first = dt.date(year, a, b)  # month a, day b
                second = dt.date(year, b, a)
                closest = min(closest, abs((first - second).days))
    assert closest >= 27
    assert lb.register_cfg_lag({"cab_max_lag_days": 99}) == 26
    assert lb.register_cfg_lag({}) == 21


def test_order_violations_make_only_the_later_field_unknown(lb: ModuleType) -> None:
    reg = build(
        lb, [raw(reg="10/12/2026", cab="14/10/26", real="10/10/26", pat_end="22/10/26")]
    )
    row = reg["rows"][0]
    assert row["real"] is None and row["pat_end"] == dt.date(2026, 10, 22)
    assert any("Deployed Real Date" in p for p in reg["problems"])


def test_future_real_deploy_and_unparsable_dates_are_unknown_and_reported(lb) -> None:
    reg = build(lb, [raw(real="20/10/26", pat_end="soon")], today=dt.date(2026, 10, 15))
    row = reg["rows"][0]
    assert row["real"] is None and row["pat_end"] is None
    assert (
        len(
            [p for p in reg["problems"] if "Deployed Real Date" in p or "Last PAT" in p]
        )
        == 2
    )


def test_current_row_is_the_highest_column_1(lb: ModuleType) -> None:
    rows = [
        raw(n="12", status="Closed"),
        raw(n="3", status="Pending"),
        raw(n="7", status="Cancel"),
    ]
    entry = build(lb, rows)["by_ticket"]["DA-1234"]
    assert entry["current"]["status"] == "Closed" and entry["ambiguous"] == ""
    assert len(entry["history"]) == 3


@pytest.mark.parametrize(
    ("numbers", "expect_ambiguous"),
    [
        (["5", "5"], True),
        (["", "x"], True),
        (["32.0", "31"], False),
        ([" 8 ", "2"], False),
    ],
)
def test_ambiguous_current_row(lb, numbers, expect_ambiguous) -> None:
    rows = [raw(n=n) for n in numbers]
    entry = build(lb, rows)["by_ticket"]["DA-1234"]
    assert bool(entry["ambiguous"]) is expect_ambiguous
    assert (entry["current"] is None) is expect_ambiguous
    assert len(entry["history"]) == len(numbers)


def test_invalid_number_rows_are_history_only(lb: ModuleType) -> None:
    rows = [raw(n="x", status="Cancel"), raw(n="4", status="Closed")]
    entry = build(lb, rows)["by_ticket"]["DA-1234"]
    assert entry["current"]["n"] == 4 and entry["ambiguous"] == ""


def test_a_lower_number_with_a_later_date_makes_the_ticket_ambiguous(lb) -> None:
    rows = [
        raw(n="10", cab="2/10/26", real="2/10/26"),
        raw(n="9", cab="5/10/26", real="6/10/26"),
    ]
    entry = build(lb, rows)["by_ticket"]["DA-1234"]
    assert entry["current"] is None and "later date" in entry["ambiguous"]


def test_multi_key_rows_link_to_each_ticket_and_unlinked_rows_are_counted(lb) -> None:
    reg = build(
        lb,
        [raw(n="1", name="DA-1111 and DA-2222"), raw(n="2", name="BAST Master Data")],
    )
    assert set(reg["by_ticket"]) == {"DA-1111", "DA-2222"} and reg["unlinked"] == 1


def info_for(lb, rows, fixing=(), today=dt.date(2026, 10, 15)):
    return lb.cab_info(build(lb, rows, today=today), "DA-1234", list(fixing), today)


@pytest.mark.parametrize(
    ("status", "stage"),
    [
        ("Register CAB", "Ready For Release"), ("Pending", "Ready For Release"),
        ("CAB Ulang", "Ready For Release"), ("OK tp Perlu Rekonfirm", "Ready For Release"),
        ("Done CAB And Progress Deployment", "Deployment"),
        ("Onprogress Deployment", "Deployment"), ("Rollback", "Rollback"),
        ("Cancel", "Cancel"), ("Whatever", "unknown"),
    ],
)  # fmt: skip
def test_register_status_maps_to_a_stage(lb, status, stage) -> None:
    assert info_for(lb, [raw(status=status)])["stage"] == stage


def test_closed_means_deployed_and_pat_decides_the_rest(lb: ModuleType) -> None:
    open_pat = info_for(
        lb, [raw(real="12/10/26", pat_end="19/10/26", pat_status="Open")]
    )
    assert open_pat["stage"] == "PAT" and not open_pat["pat_assumed"]
    for pat_status in ("Closed", "NA", "closed"):
        done = info_for(lb, [raw(pat_status=pat_status)])
        assert done["stage"] == "Done" and done["pat_confirmed"]


@pytest.mark.parametrize(
    ("today", "stage"),
    [
        (dt.date(2026, 10, 18), "PAT"),
        (dt.date(2026, 10, 19), "Done"),
        (dt.date(2026, 10, 20), "Done"),
    ],
)
def test_pat_is_assumed_done_on_the_planned_end_date(lb, today, stage) -> None:
    rows = [raw(real="12/10/26", pat_end="19/10/26", pat_status="Open")]
    info = info_for(lb, rows, today=today)
    assert info["stage"] == stage and info["pat_assumed"] is (stage == "Done")


def test_a_missing_or_invalid_planned_end_never_assumes_done(lb: ModuleType) -> None:
    for pat_end in ("", "soon"):
        info = info_for(
            lb,
            [raw(real="12/10/26", pat_end=pat_end, pat_status="")],
            today=dt.date(2030, 1, 1),
        )
        assert info["stage"] == "PAT" and not info["pat_assumed"]


def test_a_fixing_row_inside_the_window_withholds_the_assumption(
    lb: ModuleType,
) -> None:
    rows = [raw(real="12/10/26", pat_end="19/10/26", pat_status="")]
    today = dt.date(2026, 10, 20)
    blocked = info_for(lb, rows, fixing=[dt.date(2026, 10, 15)], today=today)
    assert blocked["stage"] == "PAT" and "Fixing" in blocked["error_signal"]
    late = info_for(lb, rows, fixing=[dt.date(2026, 10, 25)], today=today)
    assert late["stage"] == "Done" and late["error_signal"] == ""
    early = info_for(lb, rows, fixing=[dt.date(2026, 10, 11)], today=today)
    assert early["stage"] == "Done"
    no_deploy = info_for(
        lb, [raw(pat_end="19/10/26")], fixing=[dt.date(2026, 10, 15)], today=today
    )
    assert (
        no_deploy["stage"] == "Done"
    )  # no deploy date known: only the status signals apply


def test_confirmed_pat_ignores_error_signals(lb: ModuleType) -> None:
    rows = [raw(real="12/10/26", pat_end="19/10/26", pat_status="Closed")]
    info = info_for(lb, rows, fixing=[dt.date(2026, 10, 15)])
    assert info["stage"] == "Done" and info["pat_confirmed"]


def test_rollback_and_cab_ulang_are_error_statuses(lb: ModuleType) -> None:
    for status in ("Rollback", "CAB Ulang", "Cancel"):
        assert status in info_for(lb, [raw(status=status)])["error_signal"]


def test_an_ambiguous_ticket_has_no_stage(lb: ModuleType) -> None:
    info = info_for(lb, [raw(n="5"), raw(n="5")])
    assert info["row"] is None and info["stage"] == "" and info["ambiguous"]
    assert lb.cab_info(build(lb, [raw()]), "DA-9999", [], dt.date(2026, 10, 15)) is None


def test_fixing_dates_come_from_logbook_rows(lb: ModuleType) -> None:
    rows = [row("2026-10-15", "DA-1", "Fixing"), row("2026-10-16", "DA-1", "Testing")]
    assert lb.fixing_dates_by_ticket(rows) == {"DA-1": [dt.date(2026, 10, 15)]}


WED_1500 = dt.datetime(2026, 10, 14, 15, 0, tzinfo=dt.timezone(dt.timedelta(hours=7)))


def test_last_session_end_for_monday_and_wednesday_sessions(lb: ModuleType) -> None:
    wib = dt.timezone(dt.timedelta(hours=7))
    sessions = lb.cab_sessions({})
    assert sessions == {"days": ["Mon", "Wed"], "end": "15:00"}
    thursday = dt.datetime(2026, 10, 15, 9, 0, tzinfo=wib)
    assert lb.last_session_end(thursday, sessions) == WED_1500
    wed_before = dt.datetime(2026, 10, 14, 14, 59, tzinfo=wib)
    assert lb.last_session_end(wed_before, sessions) == dt.datetime(
        2026, 10, 12, 15, 0, tzinfo=wib
    )
    saturday = dt.datetime(2026, 10, 17, 9, 0, tzinfo=wib)
    assert lb.last_session_end(saturday, sessions) == WED_1500
    monday = dt.datetime(2026, 10, 19, 16, 0, tzinfo=wib)
    assert lb.last_session_end(monday, sessions) == dt.datetime(
        2026, 10, 19, 15, 0, tzinfo=wib
    )


@pytest.mark.parametrize(("minutes", "fresh"), [(-1, False), (0, True), (1, True)])
def test_register_is_fresh_at_or_after_the_session_end(lb, minutes, fresh) -> None:
    sessions = lb.cab_sessions({})
    now = dt.datetime(2026, 10, 15, 9, 0, tzinfo=WED_1500.tzinfo)
    register = {"mtime": WED_1500 + dt.timedelta(minutes=minutes)}
    assert lb.register_fresh(register, now, sessions) is fresh
    assert lb.register_fresh({"mtime": None}, now, sessions) is False


def test_stale_banner_names_the_session(lb: ModuleType) -> None:
    now = dt.datetime(2026, 10, 15, 9, 0, tzinfo=WED_1500.tzinfo)
    text = lb.stale_banner(now, lb.cab_sessions({}))
    assert "Wednesday" in text and "14 Oct" in text


def test_load_register_for_run_reports_why_it_is_off(lb, tmp_path) -> None:
    register, note = lb.load_register_for_run(
        {"cab_register": str(tmp_path / "nope.csv")}
    )
    assert register is None and "no CAB register" in note
    path = tmp_path / "reg.csv"
    write_register(path, [reg_line(n="1")])
    register, note = lb.load_register_for_run({"cab_register": str(path)})
    assert note == "" and "DA-1234" in register["by_ticket"]


def run_cab(lb, capsys, **kw):
    lb.cmd_cab(
        argparse.Namespace(
            ticket=kw.get("ticket", ""), show_unlinked=kw.get("show_unlinked", False)
        )
    )
    return capsys.readouterr().out


def cab_env(lb, tmp_path, rows):
    path = tmp_path / "reg.csv"
    write_register(path, rows)
    (tmp_path / "config.json").write_text(json.dumps({"cab_register": str(path)}))
    return path


def test_cab_report_lists_tickets_dates_and_quality(lb, tmp_path, capsys) -> None:
    cab_env(
        lb,
        tmp_path,
        [
            reg_line(
                n="1",
                reg="10/12/2026",
                cab="14/10/26",
                real="15/10/26",
                pat_end="22/10/26",
                pat_status="",
            ),
            reg_line(n="2", name="BAST Master Data"),
            reg_line(
                n="3",
                status="Onprogress Deployment",
                name="DA-5678 - y",
                pat_status="Closed",
            ),
        ],
    )
    (tmp_path / "jira-cache.json").write_text(
        json.dumps({"DA-1234": {"jira_status": "Deployment"}})
    )
    out = run_cab(lb, capsys)
    assert "DA-1234" in out and "2026-10-15" in out and "2026-10-22" in out
    assert "Jira Deployment" in out
    assert "1 row(s) without a ticket key" in out
    assert "Onprogress Deployment" in out and "Status PAT is Closed" in out
    assert "BAST Master Data" not in out


def test_cab_show_unlinked_lists_them(lb, tmp_path, capsys) -> None:
    cab_env(lb, tmp_path, [reg_line(n="2", name="BAST Master Data")])
    assert "BAST Master Data" in run_cab(lb, capsys, show_unlinked=True)


def test_cab_single_ticket_shows_history_and_notes_jira_ahead(
    lb, tmp_path, capsys
) -> None:
    cab_env(
        lb,
        tmp_path,
        [reg_line(n="1", status="Register CAB"), reg_line(n="2", status="Pending")],
    )
    (tmp_path / "jira-cache.json").write_text(
        json.dumps({"DA-1234": {"jira_status": "Deployment"}})
    )
    out = run_cab(lb, capsys, ticket="DA-1234")
    assert "history" in out.lower() and out.count("Register CAB") >= 1
    assert "Jira ahead of the register" in out


def test_cab_reports_why_it_is_off(lb, tmp_path, capsys) -> None:
    (tmp_path / "config.json").write_text(
        json.dumps({"cab_register": str(tmp_path / "nope.csv")})
    )
    assert "no CAB register" in run_cab(lb, capsys)


def test_cab_reports_ambiguous_tickets(lb, tmp_path, capsys) -> None:
    # identical rows are one download duplicate; differing rows with the same number conflict
    cab_env(lb, tmp_path, [reg_line(n="5"), reg_line(n="5", status="Pending")])
    assert "ambiguous" in run_cab(lb, capsys)


def cab_entry(
    lb,
    word_jira,
    rows,
    *,
    today=dt.date(2026, 10, 15),
    fresh=True,
    item=None,
    not_registered=False,
    fixing=(),
):
    register = build(lb, rows, today=today)
    cab = lb.cab_info(register, "DA-1234", list(fixing), today)
    info = {"jira_status": word_jira}
    return lb.board_entry(
        "DA-1234", info, item or [], None, today, True, "", cab, fresh, not_registered
    )


def flag_fixes(e) -> list[str]:
    return [fix for _, fix in e["flags"]]


def test_jira_cancel_leaves_the_board(lb: ModuleType) -> None:
    assert (
        lb.JIRA_STATUS["Cancel"] == "CANCELLED"
        and lb.STATUS_COLOR["CANCELLED"] == "neutral"
    )
    cache = {
        "DA-1": {"track": True, "jira_status": "Cancel", "refreshed": TODAY.isoformat()}
    }
    entries, _, _ = lb.derive_board(cache, [], {}, TODAY)
    assert entries == []


def test_register_ahead_of_jira_proposes_the_jira_move(lb: ModuleType) -> None:
    e = cab_entry(
        lb, "Deployment", [raw(real="15/10/26", pat_end="22/10/26", pat_status="")]
    )
    assert any("move Jira to PAT" in f for f in flag_fixes(e))


def test_jira_ahead_of_the_register_is_not_a_board_flag(lb: ModuleType) -> None:
    e = cab_entry(lb, "Deployment", [raw(status="Register CAB")])
    assert e["flags"] == []


def test_pat_done_is_proposed_with_the_register_values(lb: ModuleType) -> None:
    rows = [raw(real="12/10/26", pat_end="19/10/26", pat_status="Open")]
    e = cab_entry(lb, "PAT", rows, today=dt.date(2026, 10, 19))
    assert e["propose_done"] is True
    text = " ".join(t for t, _ in e["flags"])
    assert "Status PAT" in text and "Open" in text and "2026-10-19" in text


def test_pat_window_ended_with_an_error_signal_proposes_nothing(lb: ModuleType) -> None:
    rows = [raw(real="12/10/26", pat_end="19/10/26", pat_status="")]
    e = cab_entry(
        lb, "PAT", rows, today=dt.date(2026, 10, 20), fixing=[dt.date(2026, 10, 15)]
    )
    assert e["propose_done"] is False
    assert any("PAT window ended but" in t for t, _ in e["flags"])


def test_before_the_planned_end_the_board_says_nothing(lb: ModuleType) -> None:
    rows = [raw(real="12/10/26", pat_end="19/10/26", pat_status="")]
    e = cab_entry(lb, "PAT", rows, today=dt.date(2026, 10, 16))
    assert e["flags"] == [] and e["propose_done"] is False


def test_the_register_decides_pat_and_the_changelog_age_is_skipped(
    lb: ModuleType,
) -> None:
    rows = [raw(real="12/10/26", pat_end="19/10/26", pat_status="")]
    register = build(lb, rows)
    cab = lb.cab_info(register, "DA-1234", [], TODAY)
    info = {"jira_status": "PAT", "pat_since": "2026-01-01"}
    e = lb.board_entry("DA-1234", info, [], None, TODAY, True, "", cab, True, False)
    assert not any("in PAT since" in t for t, _ in e["flags"])


def test_stale_register_adds_no_cab_flags_and_keeps_the_old_pat_logic(
    lb: ModuleType,
) -> None:
    rows = [raw(real="12/10/26", pat_end="19/10/26", pat_status="Closed")]
    e = cab_entry(lb, "PAT", rows, fresh=False)
    assert e["propose_done"] is False
    assert not any("register" in t.lower() for t, _ in e["flags"])


def test_ambiguous_ticket_gets_no_cab_flag(lb: ModuleType) -> None:
    e = cab_entry(lb, "Deployment", [raw(n="5"), raw(n="5")])
    assert e["flags"] == []


def test_rollback_and_cancel_flags_only_when_jira_is_later(lb: ModuleType) -> None:
    rollback = cab_entry(lb, "PAT", [raw(status="Rollback")])
    assert any("Rollback" in t for t, _ in rollback["flags"])
    assert not any("move Jira" in f for f in flag_fixes(rollback))
    early = cab_entry(lb, "Data Development", [raw(status="Rollback")])
    assert early["flags"] == []
    cancel = cab_entry(lb, "Deployment", [raw(status="Cancel")])
    assert any("move Jira to Cancel" in f for f in flag_fixes(cancel))


def test_not_registered_flag_comes_only_from_derive_board(lb: ModuleType) -> None:
    today = dt.date(2026, 10, 15)
    wib = dt.timezone(dt.timedelta(hours=7))
    now = dt.datetime(2026, 10, 15, 9, 0, tzinfo=wib)
    register = build(lb, [raw(name="DA-9999 - other")], today=today)
    register["mtime"] = dt.datetime(2026, 10, 14, 16, 0, tzinfo=wib)
    cache = {
        "DA-1234": {
            "track": True,
            "jira_status": "Ready For Release",
            "refreshed": today.isoformat(),
        }
    }
    items = [
        [
            row("2026-10-08", "DA-1234", "Ready For Release"),
            row("2026-10-12", "DA-1234", "Ready For Release"),
        ]
    ]
    entries, _, _ = lb.derive_board(
        cache, items, {}, today, None, register, now, lb.cab_sessions({})
    )
    assert any("not registered for CAB" in t for t, _ in entries[0]["flags"])
    young = [[row("2026-10-14", "DA-1234", "Ready For Release")]]
    entries, _, _ = lb.derive_board(
        cache, young, {}, today, None, register, now, lb.cab_sessions({})
    )
    assert not any("not registered" in t for t, _ in entries[0]["flags"])
    nonjira = {
        "bug-1": {
            "track": True,
            "jira_status": "Ready For Release",
            "refreshed": today.isoformat(),
        }
    }
    old = [[row("2026-10-01", "bug-1", "Ready For Release")]]
    entries, _, _ = lb.derive_board(
        nonjira, old, {}, today, None, register, now, lb.cab_sessions({})
    )
    assert not any("not registered" in t for t, _ in entries[0]["flags"])
    register["mtime"] = dt.datetime(
        2026, 10, 14, 14, 0, tzinfo=wib
    )  # before the session end
    entries, _, _ = lb.derive_board(
        cache, items, {}, today, None, register, now, lb.cab_sessions({})
    )
    assert not any("not registered" in t for t, _ in entries[0]["flags"])


def test_board_line_shows_the_cab_dates(lb: ModuleType) -> None:
    e = cab_entry(
        lb,
        "Deployment",
        [raw(status="Onprogress Deployment", cab="14/10/26", plan="15/10/26")],
    )
    assert "CAB 2026-10-14" in e["cab_line"] and "deploy 2026-10-15" in e["cab_line"]


def test_render_board_batches_pat_done_and_shows_the_register_banner(
    lb: ModuleType,
) -> None:
    rows = [raw(real="12/10/26", pat_end="19/10/26", pat_status="Open")]
    e = cab_entry(lb, "PAT", rows, today=dt.date(2026, 10, 19))
    text = lb.render_board(
        [e],
        True,
        "2026-10-19",
        [],
        "CAB register not updated since the Wednesday 14 Oct session",
    )
    assert "PAT done: propose Done" in text and "DA-1234" in text
    assert "CAB register not updated" in text


def test_check_reports_register_flags_only_when_fresh(
    lb, tmp_path, monkeypatch, capsys
) -> None:
    path = cab_env(
        lb,
        tmp_path,
        [
            reg_line(
                n="1",
                real="15/10/26",
                cab="14/10/26",
                pat_end="22/10/26",
                pat_status="",
            )
        ],
    )
    cfg = json.loads((tmp_path / "config.json").read_text())
    cfg["repo_paths"] = {}
    (tmp_path / "config.json").write_text(json.dumps(cfg))
    today = dt.date.today().isoformat()
    (tmp_path / "jira-cache.json").write_text(
        json.dumps({"DA-1234": {"jira_status": "Deployment", "refreshed": today}})
    )
    write_csv(lb.LOGBOOK, [row("2026-10-12", "DA-1234", "Deployment")])
    monkeypatch.setattr(lb, "_run", fake_run_factory([]))
    wib = dt.timezone(dt.timedelta(hours=7))
    monkeypatch.setattr(
        lb, "now_wib", lambda: dt.datetime(2026, 10, 16, 9, 0, tzinfo=wib)
    )
    os.utime(path, (dt.datetime(2026, 10, 15, 9, 0, tzinfo=wib).timestamp(),) * 2)
    out = run_check(lb, capsys)
    assert "move Jira to PAT" in out
    os.utime(path, (dt.datetime(2026, 10, 13, 9, 0, tzinfo=wib).timestamp(),) * 2)
    out = run_check(lb, capsys)
    assert "move Jira to PAT" not in out and "not updated" in out


def week_lines(lb, rows, week="2026-W42", banner=""):
    return lb.cab_week_lines(week, build(lb, rows), banner)


def test_cab_week_block_groups_registered_sessions_deployed_and_pat_ends(
    lb: ModuleType,
) -> None:
    rows = [
        raw(
            n="1",
            name="DA-1111 - a",
            reg="10/12/2026",
            cab="12/10/26",
            real="13/10/26",
            pat_end="18/10/26",
        ),
        raw(
            n="2",
            name="DA-2222 - b",
            reg="10/12/2026",
            cab="14/10/26",
            real="15/10/26",
            pat_end="22/10/26",
        ),
        raw(n="3", name="DA-3333 - c", status="Register CAB", reg="10/12/2026"),
    ]
    text = "\n".join(week_lines(lb, rows))
    assert "### CAB this week" in text
    assert "Registered: DA-1111, DA-2222, DA-3333 (date unverified)" in text
    assert "2026-10-12 (DA-1111)" in text and "2026-10-14 (DA-2222)" in text
    assert "DA-1111 (2026-10-13)" in text and "DA-2222 (2026-10-15)" in text
    assert "PAT windows ending" in text and "DA-1111 (2026-10-18)" in text


def test_cab_week_lists_a_ticket_once_per_row_and_keeps_history(lb: ModuleType) -> None:
    rows = [
        raw(
            n="1", reg="10/12/2026", cab="12/10/26", real="13/10/26", pat_end="20/10/26"
        ),
        raw(
            n="2", reg="10/14/2026", cab="14/10/26", real="14/10/26", pat_end="21/10/26"
        ),
    ]
    text = "\n".join(week_lines(lb, rows))
    assert text.count("DA-1234") == 6  # registered, session and deploy, once per row


def test_cab_week_skips_rollback_and_cancel_in_pat_windows(lb: ModuleType) -> None:
    rows = [
        raw(
            status="Rollback",
            reg="10/12/2026",
            cab="12/10/26",
            real="13/10/26",
            pat_end="16/10/26",
        )
    ]
    assert "PAT windows ending" not in "\n".join(week_lines(lb, rows))


def test_cab_week_empty_week_prints_nothing_and_off_register_too(
    lb: ModuleType,
) -> None:
    assert week_lines(lb, [raw(reg="1/5/2026", cab="2/5/26")]) == []
    assert lb.cab_week_lines("2026-W42", None, "") == []


def test_cab_week_marks_unverified_dates_counts_unlinked_and_shows_the_banner(
    lb,
) -> None:
    rows = [
        raw(n="1", reg="10/12/2026"),
        raw(n="2", name="BAST Master Data", reg="10/12/2026", cab="12/10/26"),
    ]
    text = "\n".join(
        week_lines(
            lb,
            rows,
            banner="CAB register not updated since the Wednesday 14 Oct session",
        )
    )
    assert "unverified" in text and "Unlinked rows: 1" in text
    assert text.splitlines()[0].startswith("CAB register not updated")


def test_week_prints_the_cab_block_even_with_no_logbook_entries(
    lb, tmp_path, capsys
) -> None:
    cab_env(
        lb,
        tmp_path,
        [
            reg_line(
                n="1",
                reg="10/12/2026",
                cab="12/10/26",
                real="13/10/26",
                pat_end="18/10/26",
            )
        ],
    )
    lb.cmd_week(argparse.Namespace(week="2026-W42"))
    out = capsys.readouterr().out
    assert "CAB this week" in out and "No entries" not in out


def test_week_without_a_register_still_says_no_entries(lb, tmp_path, capsys) -> None:
    (tmp_path / "config.json").write_text(
        json.dumps({"cab_register": str(tmp_path / "nope.csv")})
    )
    lb.cmd_week(argparse.Namespace(week="2026-W42"))
    assert "No entries for 2026-W42." in capsys.readouterr().out


def test_config_example_documents_the_cab_keys() -> None:
    cfg = json.loads((ROOT / "CLAUDE/skills/logbook/config.example.json").read_text())
    assert {
        "cab_register",
        "cab_sessions",
        "cab_max_lag_days",
        "cab_grace_days",
    } <= set(cfg)
    assert cfg["cab_sessions"] == {"days": ["Mon", "Wed"], "end": "15:00"}


def test_skill_text_describes_the_cab_register() -> None:
    text = (ROOT / "CLAUDE/skills/logbook/SKILL.md").read_text(encoding="utf-8")
    for needle in (
        "## CAB register",
        "logbook.py cab",
        "cab_register",
        "Monday and Wednesday",
    ):
        assert needle in text
    assert "Last PAT Date" in text and "assumed done" in text
    assert "CAB register" in (ROOT / "CLAUDE/commands/pipeline.md").read_text(
        encoding="utf-8"
    )


def test_pat_done_block_shows_the_pat_flag_even_when_another_flag_comes_first(
    lb: ModuleType,
) -> None:
    rows = [raw(real="12/10/26", pat_end="19/10/26", pat_status="Open")]
    item = [row("2026-10-14", "DA-1234", "Deployment")]
    e = cab_entry(lb, "PAT", rows, today=dt.date(2026, 10, 19), item=item)
    assert e["flags"][0][0].startswith("Jira PAT vs logbook")
    text = lb.render_board([e], True, "2026-10-19", [])
    block = text.split("## PAT done: propose Done")[1].split("##")[0]
    assert "PAT done (assumed)" in block and "vs logbook" not in block


def test_the_changelog_age_still_applies_when_the_register_has_no_planned_end(
    lb: ModuleType,
) -> None:
    register = build(lb, [raw(real="12/10/26", pat_end="", pat_status="Open")])
    cab = lb.cab_info(register, "DA-1234", [], TODAY)
    info = {"jira_status": "PAT", "pat_since": "2026-10-02"}
    e = lb.board_entry("DA-1234", info, [], None, TODAY, True, "", cab, True, False)
    assert any("in PAT since 2026-10-02" in t for t, _ in e["flags"])
    no_since = lb.board_entry(
        "DA-1234", {"jira_status": "PAT"}, [], None, TODAY, True, "", cab, True, False
    )
    assert any("PAT date unknown" in t for t, _ in no_since["flags"])


def test_the_changelog_age_applies_when_the_register_is_behind_jira(
    lb: ModuleType,
) -> None:
    register = build(lb, [raw(status="Onprogress Deployment")])
    cab = lb.cab_info(register, "DA-1234", [], TODAY)
    info = {"jira_status": "PAT", "pat_since": "2026-10-02"}
    e = lb.board_entry("DA-1234", info, [], None, TODAY, True, "", cab, True, False)
    assert any("in PAT since" in t for t, _ in e["flags"])


def test_cab_report_lists_unknown_statuses(lb: ModuleType) -> None:
    quality = lb.register_quality(
        build(lb, [raw(n="4", status="Weird"), raw(n="5", status="")])
    )
    assert any("unknown status" in line and "Weird" in line for line in quality)
    assert any("unknown status" in line for line in quality if "5" in line)


def test_bad_cab_config_falls_back_to_the_defaults(lb: ModuleType) -> None:
    default = {"days": ["Mon", "Wed"], "end": "15:00"}
    assert lb.cab_sessions({"cab_sessions": {"days": [], "end": "15:00"}}) == default
    assert lb.cab_sessions({"cab_sessions": {"days": ["Mon"], "end": "3pm"}}) == default
    assert (
        lb.cab_sessions({"cab_sessions": {"days": ["Funday"], "end": "15:00"}})
        == default
    )
    assert lb.cab_sessions({"cab_sessions": {"days": ["Tue", "Thu"], "end": "09:30"}}) == {
        "days": ["Tue", "Thu"], "end": "09:30",
    }  # fmt: skip
    assert lb.cab_grace_days({"cab_grace_days": "x"}) == 3
    assert lb.cab_grace_days({"cab_grace_days": 5}) == 5
    assert lb.cab_grace_days({}) == 3


def test_not_registered_applies_only_to_da_keys(lb: ModuleType) -> None:
    today = dt.date(2026, 10, 15)
    wib = dt.timezone(dt.timedelta(hours=7))
    now = dt.datetime(2026, 10, 15, 9, 0, tzinfo=wib)
    register = build(lb, [raw(name="DA-9999 - other")], today=today)
    register["mtime"] = dt.datetime(2026, 10, 14, 16, 0, tzinfo=wib)
    cache = {
        "IN-123": {
            "track": True,
            "jira_status": "Ready For Release",
            "refreshed": today.isoformat(),
        }
    }
    items = [[row("2026-10-01", "IN-123", "Ready For Release")]]
    entries, _, _ = lb.derive_board(
        cache, items, {}, today, None, register, now, lb.cab_sessions({})
    )
    assert not any("not registered" in t for t, _ in entries[0]["flags"])


def test_cancelled_tickets_are_never_aged(lb: ModuleType) -> None:
    assert "CANCELLED" in lb.NO_AGING
