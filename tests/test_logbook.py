"""Tests for the logbook helper (CLAUDE/skills/logbook/logbook.py)."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

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
