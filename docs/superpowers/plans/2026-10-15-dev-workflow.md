# Dev Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the logbook use the Jira stage words, migrate the existing rows safely, update the instruction text that still uses git-step words, and add a `pipeline` board that shows every open ticket by stage with the next action.

**Architecture:** All code lives in the existing stdlib-only helper `CLAUDE/skills/logbook/logbook.py` (the `~/.claude` copy is identical and is replaced from it at deployment). Unit A changes the status vocabulary, `check`, the cache fields and adds a one-off `migrate-statuses` command. Unit B adds a `pipeline` subcommand built on `git_evidence` and the Jira cache. Instruction files (`CLAUDE.md`, commands, skills) get the same textual edit in the `CLAUDE/` template and, at deployment, in the live `~/.claude` files, because they differ from the template by placeholders and cannot be copied over.

**Tech Stack:** Python 3.9-compatible stdlib (helper) tested with pytest on the project's Python 3.11 and on 3.9/3.12 with `uv run --no-project --python X`; ruff; Markdown.

**Spec:** `docs/superpowers/specs/2026-10-15-dev-workflow-design.md`

## Global Constraints

- Helper runs on system `python3` 3.9 and on 3.10+: keep `from __future__ import annotations`, no `match`, no `zip(strict=...)`, no runtime `X | None`.
- Nothing is committed, pushed or opened as a PR unless the user asks. A "Checkpoint" step below means: show `git status` and the diff summary, then commit only when the user says so.
- Commits: Conventional Commits + gitmoji, ending with `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`. PR bodies end with `🤖 Generated with [Claude Code](https://claude.com/claude-code)`.
- The repo is public: no internal hosts, ids, account names or logbook data in repo files; use placeholders.
- Markdown: code fences always carry a language (`text` for plain), table separators are `| --- |`, object names and paths in backticks.
- The helper cannot call Jira or Confluence; Jira data reaches it only through `cache set`.
- Status words (exact): `Analysis`, `Development`, `Testing`, `Ready For Release`, `Deployment`, `PAT`, `Done`, `Fixing`, `Hold`. Page words: `ANALYST`, `DEVELOPMENT`, `TESTING`, `READY FOR RELEASE`, `DEPLOYMENT`, `PAT`, `DONE`, `FIXING`, `HOLD`.
- Jira order: `Data Analysis` → `Data Development` → `Testing` → `Ready For Release` → `Deployment` → `PAT` → `Done`; forward-only; `Hold` anywhere.
- Jira wins over the logbook for status. A `master` merge never means deployed.
- Lozenge colours allowed: `neutral`, `purple`, `blue`, `red`, `yellow`, `green`. `DEPLOYMENT` is `blue`, `PAT` is `purple`.
- 7-day rules use calendar days in the local date (Asia/Jakarta).

## Review Focus

Failure modes the spec implies that no single task's happy path exercises:

1. A legacy CSV (old words) must stay readable by `migrate-statuses` while `read_rows` rejects it (Task 4 tests both).
2. A `Released` ticket whose Jira cache entry is missing, stale or unmapped must never be written as `Done` (Task 4).
3. Two `Released` rows for one ticket on different days: only the last takes the Jira-derived status (Task 4).
4. A held ticket with a merged PR must produce a note, not a workflow flag (Task 9).
5. A Jira outage (cache not refreshed today) must suppress Jira-dependent flags and show the stale banner (Task 9).

---

## File Structure

| File | Responsibility |
| --- | --- |
| `CLAUDE/skills/logbook/logbook.py` | Helper: vocabulary, `check`, cache, migration (A), board (B) |
| `tests/test_logbook.py` | New tests for everything above, loading the helper by path |
| `CLAUDE/skills/logbook/SKILL.md` | Logbook skill text: status table, Jira wins, new commands |
| `CLAUDE/skills/logbook/config.example.json` | `other_court` list with the four waiting stages |
| `CLAUDE/CLAUDE.md`, `CLAUDE/commands/generate-pr-message.md`, `CLAUDE/skills/jira-ticket-kickoff/SKILL.md`, `CLAUDE/skills/bast-generator/SKILL.md` | Old-word and Jira-status-rule edits |
| `CLAUDE/commands/pipeline.md` | New `/pipeline` slash command (Unit B) |
| `docs/guidelines/DEV-WORKFLOW.md` | Reusable trimmed workflow doc |
| `README.md`, `CLAUDE/README.md` | Links and command table rows |

---

# Unit A: status vocabulary, migration and instruction text

### Task 1: Test harness and the new status vocabulary

**Files:**
- Create: `tests/test_logbook.py`
- Modify: `CLAUDE/skills/logbook/logbook.py:47-81` (constants block: `STATUSES`, `PAGE_STATUS`, `FINISHED`, `JIRA_STATUS`, `OTHER_COURT`, `STATUS_COLOR`)

**Interfaces:**
- Produces: `STATUSES: list[str]`, `PAGE_STATUS: dict[str, str]`, `PAGE_TO_LOGBOOK: dict[str, str]` (inverse of `PAGE_STATUS`), `FINISHED: set[str]`, `JIRA_STATUS: dict[str, str]` (now with `Deployment`, `PAT`), `OTHER_COURT: list[str]`, `STATUS_COLOR: dict[str, str]`. Test fixture `lb` (loads the helper with `LOGBOOK_PATH` in `tmp_path`) used by all later tasks.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_logbook.py`:

```python
"""Tests for the logbook helper (CLAUDE/skills/logbook/logbook.py)."""

from __future__ import annotations

import csv
import importlib.util
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
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_logbook.py -v`
Expected: FAIL (assertions on `STATUSES`, missing `PAGE_TO_LOGBOOK`).

- [ ] **Step 3: Replace the constants block**

In `CLAUDE/skills/logbook/logbook.py`, replace `STATUSES` through `STATUS_COLOR` (lines 47-81) with:

```python
STATUSES = [
    "Analysis", "Development", "Testing", "Ready For Release", "Deployment",
    "PAT", "Done", "Fixing", "Hold",
]  # fmt: skip
## Logbook status -> the status words used on the Confluence weekly page.
PAGE_STATUS = {
    "Analysis": "ANALYST", "Development": "DEVELOPMENT", "Testing": "TESTING",
    "Ready For Release": "READY FOR RELEASE", "Deployment": "DEPLOYMENT",
    "PAT": "PAT", "Done": "DONE", "Fixing": "FIXING", "Hold": "HOLD",
}  # fmt: skip
PAGE_TO_LOGBOOK = {word: status for status, word in PAGE_STATUS.items()}
FINISHED = {"Done"}
## Jira workflow status -> page status, for tickets the user has not logged work on and
## for the Jira-wins comparison.
JIRA_STATUS = {
    "Hold": "HOLD", "Testing": "TESTING", "Ready For Release": "READY FOR RELEASE",
    "Deployment": "DEPLOYMENT", "PAT": "PAT",
    "In Progress": "DEVELOPMENT", "Data Development": "DEVELOPMENT",
    "Data Analysis": "ANALYST", "Revisi SRF Data": "ANALYST", "Bug Fixing": "FIXING",
    "[BU] Todo": "TODO", "TODO": "TODO", "To Do": "TODO", "Backlog": "TODO",
    "Done": "DONE",
}  # fmt: skip
## Start-date cell fill once unfinished work gets old: tiers light to strong.
AGING_COLORS = ["#FFFAE6", "#FFF0B3", "#FF8F73"]
AGING_DAYS = [30, 60, 90]  # override with "aging_days" in config.json
NO_AGING = {"DONE", "HOLD"}  # finished, or deliberately paused: never highlighted
## Statuses where the ball is in someone else's court. Their age is shown on the LastUpdate
## cell (time since anything moved, i.e. when to follow up) instead of on Start Date.
OTHER_COURT = [
    "TESTING",
    "READY FOR RELEASE",
    "DEPLOYMENT",
    "PAT",
]  # override with "other_court" in config.json
FOLLOWUP_DAYS = [7, 14, 30]  # override with "followup_days" in config.json
## Lozenge colour per page status (Confluence only accepts neutral, purple, blue, red,
## yellow, green).
STATUS_COLOR = {
    "ANALYST": "purple", "DEVELOPMENT": "blue", "FIXING": "red", "TESTING": "yellow",
    "READY FOR RELEASE": "green", "DEPLOYMENT": "blue", "PAT": "purple",
    "DONE": "green", "HOLD": "neutral", "TODO": "neutral",
}  # fmt: skip
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_logbook.py -v`
Expected: PASS (6 tests).

- [ ] **Step 5: Checkpoint**

Run: `uv run ruff check tests/test_logbook.py CLAUDE/skills/logbook/logbook.py && uv run ruff format --check tests/test_logbook.py CLAUDE/skills/logbook/logbook.py`
Expected: clean. Show `git status`; commit only if the user asks (`✨ feat(claude): use the Jira stage words as logbook statuses`).

---

### Task 2: Git evidence maps to the new stages; `check` makes Jira win

**Files:**
- Modify: `CLAUDE/skills/logbook/logbook.py` (`STAGE`, `pr_stage`, `git_evidence`, `cmd_check`)
- Test: `tests/test_logbook.py`

**Interfaces:**
- Consumes: `PAGE_STATUS`, `PAGE_TO_LOGBOOK`, `JIRA_STATUS` from Task 1.
- Produces: `STAGE: dict[str, int]` (ranks), `OUTSIDE_ORDER = {"Fixing", "Hold"}`, `pr_stage(pr) -> str`, `git_evidence(...)` where each evidence dict is `{"stage": str, "last": str, "repos": set[str], "master": bool}`. `check` prints `Jira wins; propose: add --ticket T --status "<Status>"` for a Jira/logbook difference.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_logbook.py`:

```python
import json


@pytest.mark.parametrize(
    ("pr", "expected"),
    [
        (
            {
                "baseRefName": "master",
                "mergedAt": "2026-10-01T00:00:00Z",
                "state": "MERGED",
            },
            "",
        ),
        ({"baseRefName": "master", "state": "OPEN"}, ""),
        ({"baseRefName": "main", "state": "OPEN"}, ""),
        (
            {
                "baseRefName": "sit",
                "mergedAt": "2026-10-01T00:00:00Z",
                "state": "MERGED",
            },
            "Development",
        ),
        ({"baseRefName": "sit", "state": "OPEN"}, "Development"),
        ({"baseRefName": "dev", "state": "OPEN"}, "Testing"),
        (
            {
                "baseRefName": "dev",
                "mergedAt": "2026-10-01T00:00:00Z",
                "state": "MERGED",
            },
            "Ready For Release",
        ),
        ({"baseRefName": "dev", "state": "CLOSED"}, ""),
    ],
)
def test_pr_stage_maps_git_events_to_logbook_statuses(lb, pr, expected) -> None:
    assert lb.pr_stage(pr) == expected


def test_stage_ranks_follow_the_jira_order(lb: ModuleType) -> None:
    order = [
        "Analysis",
        "Development",
        "Testing",
        "Ready For Release",
        "Deployment",
        "PAT",
        "Done",
    ]
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
    lb: ModuleType, monkeypatch
) -> None:
    prs = [{"title": "DA-1 release", "headRefName": "dev", "baseRefName": "master",
            "state": "OPEN", "mergedAt": None, "updatedAt": "2026-10-14T00:00:00Z"}]  # fmt: skip
    monkeypatch.setattr(lb, "_run", fake_run_factory(prs))
    evidence, _ = lb.git_evidence({"r": "/x"}, "2026-10-01")
    assert evidence["DA-1"]["master"] is True
    assert evidence["DA-1"]["stage"] == ""


def make_check_env(
    lb: ModuleType, tmp_path: Path, monkeypatch, status: str, jira: str, prs: list[dict]
) -> None:
    write_csv(lb.LOGBOOK, [row("2026-10-10", "DA-1", status)])
    (tmp_path / "config.json").write_text(
        json.dumps({"repo_paths": {"r": str(tmp_path)}})
    )
    (tmp_path / "jira-cache.json").write_text(
        json.dumps({"DA-1": {"jira_status": jira, "updated": "2026-10-12"}})
    )
    monkeypatch.setattr(lb, "_run", fake_run_factory(prs))


def run_check(lb: ModuleType, capsys) -> str:
    import argparse

    lb.cmd_check(argparse.Namespace(since="2026-10-01"))
    return capsys.readouterr().out


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
    prs = [{"title": "DA-1 x", "headRefName": "fea/DA-1", "baseRefName": "dev", "state": "MERGED",
            "mergedAt": "2026-10-13T00:00:00Z", "updatedAt": "2026-10-13T00:00:00Z"}]  # fmt: skip
    make_check_env(lb, tmp_path, monkeypatch, "Testing", "Testing", prs)
    assert "but a PR is at 'Ready For Release'" in run_check(lb, capsys)


def test_check_ignores_pr_lag_for_hold_and_fixing(
    lb, tmp_path, monkeypatch, capsys
) -> None:
    prs = [{"title": "DA-1 x", "headRefName": "fea/DA-1", "baseRefName": "dev", "state": "MERGED",
            "mergedAt": "2026-10-13T00:00:00Z", "updatedAt": "2026-10-13T00:00:00Z"}]  # fmt: skip
    make_check_env(lb, tmp_path, monkeypatch, "Hold", "Hold", prs)
    assert "a PR is at" not in run_check(lb, capsys)
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/test_logbook.py -v -k "pr_stage or stage_ranks or git_evidence or check"`
Expected: FAIL (old `pr_stage` words, no `OUTSIDE_ORDER`, no `master` key, old verdict text).

- [ ] **Step 3: Implement**

Replace the `STAGE` block and `pr_stage`:

```python
## How far along a logbook status is; used to spot a row that lags behind its PR.
## Fixing and Hold sit outside the order and are skipped by the lag check.
STAGE = {
    "": 0, "Analysis": 1, "Development": 2, "Testing": 3, "Ready For Release": 4,
    "Deployment": 5, "PAT": 6, "Done": 7,
}  # fmt: skip
OUTSIDE_ORDER = {"Fixing", "Hold"}
```

```python
def pr_stage(pr: dict[str, Any]) -> str:
    """Logbook status a pull request implies. A PR to master implies none."""
    merged, is_open = bool(pr.get("mergedAt")), pr.get("state") == "OPEN"
    base = pr.get("baseRefName")
    if base in ("master", "main"):
        return ""
    if base == "sit":
        return "Development" if (merged or is_open) else ""
    return "Ready For Release" if merged else ("Testing" if is_open else "")
```

In `git_evidence`, change the evidence dict default to `{"stage": "", "last": "", "repos": set(), "master": False}` and, in the PR loop, before the `for key in ...` line add the master flag:

```python
            is_master_pr = pr.get("baseRefName") in ("master", "main") and (
                pr.get("state") == "OPEN" or pr.get("mergedAt")
            )
```

and inside the key loop replace the `note(...)` call with:

```python
            for key in set(TICKET_RE.findall(f"{pr['headRefName']} {pr['title']}")):
                note(key, repo, when, pr_stage(pr))
                if is_master_pr:
                    evidence[key]["master"] = True
```

In `cmd_check`, change the lag condition to:

```python
        if (
            last["status"] not in OUTSIDE_ORDER
            and STAGE.get(last["status"], 0) < STAGE.get(ev["stage"], 0)
        ):
```

and replace the Jira-vs-logbook loop body with:

```python
    for ticket, item in sorted(items.items()):
        info = cache.get(ticket, {})
        jira = JIRA_STATUS.get(info.get("jira_status", ""))
        mine = PAGE_STATUS.get(item[-1]["status"], "")
        target = PAGE_TO_LOGBOOK.get(jira or "")
        if jira and mine and jira != mine and target:
            findings.append(
                f"{ticket}: Jira '{info['jira_status']}' ({jira}) vs logbook "
                f"'{item[-1]['status']}' ({mine}, {item[-1]['date']}) -> Jira wins; "
                f'propose: add --ticket {ticket} --status "{target}"'
            )
```

- [ ] **Step 4: Run to verify they pass**

Run: `uv run pytest tests/test_logbook.py -v`
Expected: PASS (all).

- [ ] **Step 5: Sweep for the old verdict and old words**

Run: `grep -nE "Jira is newer|logbook is newer|same day, decide|Merged to|PR to (dev|master)|Released|In progress" CLAUDE/skills/logbook/logbook.py`
Expected: no match except inside `LEGACY_MAP` (added in Task 4) and docstrings you decide to reword; fix any other hit.

- [ ] **Step 6: Checkpoint**

`uv run ruff check . && uv run ruff format --check .`; show diff; commit only on request (`✨ feat(claude): map git events to the new stages and let Jira win in check`).

---

### Task 3: Cache fields `refreshed` and `pat_since`; Jira-first page status

**Files:**
- Modify: `CLAUDE/skills/logbook/logbook.py` (`cmd_cache`, `item_status`, argparse for `cache`)
- Test: `tests/test_logbook.py`

**Interfaces:**
- Produces: `cache set --jira-status X` stores `refreshed` = today (ISO); `cache set --pat-since YYYY-MM-DD` stores `pat_since`; `jira_fresh(info: dict, today: dt.date | None = None) -> bool` (true when `refreshed` is within `JIRA_FRESH_DAYS = 7` days); `item_status(last, info)` returns the Jira page word when the entry is fresh and mapped, else the logbook word.

- [ ] **Step 1: Write the failing tests**

```python
import argparse
import datetime as dt


def cache_args(**kw: str) -> argparse.Namespace:
    base = {"action": "set", "ticket": "DA-1", "created": "", "source": "", "description": "",
            "summary": "", "jira_status": "", "updated": "", "project": "", "before_hold": "",
            "hold_since": "", "pat_since": "", "track": ""}  # fmt: skip
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


def test_item_status_falls_back_to_the_logbook_when_jira_is_stale_or_unmapped(
    lb: ModuleType,
) -> None:
    last = {"status": "Testing"}
    assert (
        lb.item_status(last, {"jira_status": "PAT", "refreshed": "2020-01-01"})
        == "TESTING"
    )
    today = dt.date.today().isoformat()
    assert (
        lb.item_status(last, {"jira_status": "Weird", "refreshed": today}) == "TESTING"
    )
    assert lb.item_status({"status": ""}, {"jira_status": "Weird"}) == "WEIRD"
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/test_logbook.py -v -k "cache_set or jira_fresh or item_status"`
Expected: FAIL (no `pat_since`, no `jira_fresh`).

- [ ] **Step 3: Implement**

In `cmd_cache`, add `"pat_since"` to the field-name tuple, add `args.pat_since` to the date-validation tuple (`for date in (args.updated, args.hold_since, args.pat_since):`), and after the `track` handling add:

```python
    if args.jira_status:
        entry["refreshed"] = dt.date.today().isoformat()
```

Add to the `cache` argparse block:

```python
    cache.add_argument(
        "--pat-since", default="", help="date it entered PAT (Jira changelog), YYYY-MM-DD"
    )
```

Replace `item_status` and add `jira_fresh` above it:

```python
JIRA_FRESH_DAYS = (
    7  # a cached Jira status older than this no longer outranks the logbook
)


def jira_fresh(info: dict, today: dt.date | None = None) -> bool:
    """True when the cache entry was refreshed from Jira within JIRA_FRESH_DAYS."""
    stamp = info.get("refreshed", "")
    if not stamp:
        return False
    try:
        age = ((today or dt.date.today()) - dt.date.fromisoformat(stamp)).days
    except ValueError:
        return False
    return age <= JIRA_FRESH_DAYS


def item_status(last: dict[str, str], info: dict) -> str:
    """Page status word for a ticket: a fresh, mapped Jira status wins, else the logbook."""
    jira = JIRA_STATUS.get(info.get("jira_status", ""))
    if jira and jira_fresh(info):
        return jira
    return (
        PAGE_STATUS.get(last["status"])
        or jira
        or (last["status"] or info.get("jira_status", "")).upper()
        or "-"
    )
```

- [ ] **Step 4: Run to verify they pass**

Run: `uv run pytest tests/test_logbook.py -v`
Expected: PASS.

- [ ] **Step 5: Checkpoint**

Ruff check and format; show diff; commit only on request (`✨ feat(claude): record Jira refresh and PAT dates, make Jira win on the page`).

---

### Task 4: `migrate-statuses` command

**Files:**
- Modify: `CLAUDE/skills/logbook/logbook.py` (new `LEGACY_MAP`, `read_legacy`, `migrate_rows`, `cmd_migrate`, argparse)
- Test: `tests/test_logbook.py`

**Interfaces:**
- Consumes: `STATUSES`, `PAGE_TO_LOGBOOK`, `JIRA_STATUS`, `row_problem`, `write_rows`, `COLUMNS`, `LOGBOOK`, `ARCHIVE`, `load_cache` from earlier tasks.
- Produces: `LEGACY_MAP: dict[str, str]`, `RECENT_DAYS = 7`, `read_legacy(path: Path) -> list[dict[str, str]]`, `migrate_rows(rows, cache, today, resolve) -> tuple[list[dict], list[str], list[tuple[str, str]]]` (new rows, report lines, review list of `(date, ticket)`), `cmd_migrate(args)` with `--dry-run` and repeatable `--resolve TICKET=Status`.

- [ ] **Step 1: Write the failing tests**

```python
TODAY = dt.date(2026, 10, 15)


def migrate(lb: ModuleType, rows, cache=None, resolve=None):
    return lb.migrate_rows(rows, cache or {}, TODAY, resolve or {})


def test_legacy_words_map_and_new_words_pass_through(lb: ModuleType) -> None:
    rows = [
        row("2026-09-01", "A", "In progress"),
        row("2026-09-01", "B", "PR to dev"),
        row("2026-09-01", "C", "Merged to sit"),
        row("2026-09-01", "D", "Merged to dev"),
        row("2026-09-01", "E", "PR to master"),
        row("2026-09-01", "F", "Analysis"),
        row("2026-09-01", "G", "Fixing"),
        row("2026-09-01", "H", "Hold"),
        row("2026-09-01", "I", "Done"),
        row("2026-09-01", "J", ""),
    ]
    new, _, review = migrate(lb, rows)
    assert [r["status"] for r in new] == [
        "Development", "Testing", "Development", "Ready For Release",
        "Ready For Release", "Analysis", "Fixing", "Hold", "Done", "",
    ]  # fmt: skip
    assert review == []


@pytest.mark.parametrize(
    ("jira", "expected"),
    [("Hold", "Hold"), ("Testing", "Testing"), ("Ready For Release", "Ready For Release"),
     ("Deployment", "Deployment"), ("PAT", "PAT"), ("Done", "Done")],
)  # fmt: skip
def test_released_takes_the_known_jira_status(lb, jira, expected) -> None:
    new, _, review = migrate(
        lb, [row("2026-08-01", "A", "Released")], {"A": {"jira_status": jira}}
    )
    assert new[0]["status"] == expected and review == []


@pytest.mark.parametrize(
    "cache",
    [{}, {"A": {}}, {"A": {"jira_status": "Weird"}}, {"A": {"jira_status": "To Do"}}],
)
def test_released_with_unknown_or_unmapped_jira_status_goes_to_review(
    lb, cache
) -> None:
    new, _, review = migrate(lb, [row("2026-08-01", "A", "Released")], cache)
    assert review == [("2026-08-01", "A")]
    assert new[0]["status"] == "Released"  # nothing guessed, nothing written as Done


def test_recent_boundary_is_flagged_but_keeps_the_jira_status(lb: ModuleType) -> None:
    cache = {"A": {"jira_status": "Hold"}, "B": {"jira_status": "Hold"}}
    rows = [
        row("2026-10-08", "A", "Released"),
        row("2026-10-07", "B", "Released"),
    ]  # 7 and 8 days old
    new, report, review = migrate(lb, rows, cache)
    assert [r["status"] for r in new] == ["Hold", "Hold"] and review == []
    flagged = [line for line in report if "check" in line]
    assert len(flagged) == 1 and "A" in flagged[0]


def test_only_the_last_released_row_of_a_ticket_takes_the_jira_status(
    lb: ModuleType,
) -> None:
    rows = [row("2026-08-01", "A", "Released"), row("2026-09-01", "A", "Released")]
    new, _, _ = migrate(lb, rows, {"A": {"jira_status": "PAT"}})
    assert [r["status"] for r in new] == ["Done", "PAT"]


def test_resolve_decides_a_reviewed_row(lb: ModuleType) -> None:
    new, _, review = migrate(
        lb, [row("2026-08-01", "A", "Released")], resolve={"A": "PAT"}
    )
    assert new[0]["status"] == "PAT" and review == []


def test_unknown_legacy_word_aborts(lb: ModuleType) -> None:
    with pytest.raises(SystemExit):
        migrate(lb, [row("2026-08-01", "A", "Mystery")])


def test_every_released_row_has_exactly_one_outcome(lb: ModuleType) -> None:
    rows = [row("2026-08-01", t, "Released") for t in "ABC"]
    cache = {"A": {"jira_status": "Done"}, "B": {"jira_status": "Weird"}}
    new, _, review = migrate(lb, rows, cache)
    resolved = [r for r in new if r["status"] in lb.STATUSES]
    assert len(resolved) + len(review) == len(rows)


def run_migrate(lb, tmp_path, *, dry_run: bool, resolve=None):
    return lb.cmd_migrate(argparse.Namespace(dry_run=dry_run, resolve=resolve or []))


def test_old_csv_is_unreadable_by_read_rows_but_migrates(
    lb: ModuleType, tmp_path: Path
) -> None:
    write_csv(
        lb.LOGBOOK,
        [row("2026-09-01", "A", "PR to dev"), row("2026-09-02", "A", "Released")],
    )
    (tmp_path / "jira-cache.json").write_text('{"A": {"jira_status": "Done"}}')
    with pytest.raises(SystemExit):
        lb.read_rows()
    run_migrate(lb, tmp_path, dry_run=False)
    assert [r["status"] for r in lb.read_rows()] == ["Testing", "Done"]
    assert list(tmp_path.glob("logbook.csv.pre-migration-*"))


def test_dry_run_writes_nothing(lb: ModuleType, tmp_path: Path) -> None:
    write_csv(lb.LOGBOOK, [row("2026-09-01", "A", "PR to dev")])
    before = lb.LOGBOOK.read_text()
    run_migrate(lb, tmp_path, dry_run=True)
    assert lb.LOGBOOK.read_text() == before
    assert not list(tmp_path.glob("*.pre-migration-*"))


def test_unresolved_review_blocks_the_write(lb: ModuleType, tmp_path: Path) -> None:
    write_csv(lb.LOGBOOK, [row("2026-09-01", "A", "Released")])
    before = lb.LOGBOOK.read_text()
    with pytest.raises(SystemExit):
        run_migrate(lb, tmp_path, dry_run=False)
    assert lb.LOGBOOK.read_text() == before


def test_archive_file_is_migrated_too(lb: ModuleType, tmp_path: Path) -> None:
    write_csv(lb.LOGBOOK, [row("2026-09-01", "A", "In progress")])
    write_csv(lb.ARCHIVE, [row("2026-06-01", "Z", "Released")])
    (tmp_path / "jira-cache.json").write_text('{"Z": {"jira_status": "Done"}}')
    run_migrate(lb, tmp_path, dry_run=False)
    assert lb.read_rows(lb.ARCHIVE)[0]["status"] == "Done"
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/test_logbook.py -v -k "legacy or released or recent or resolve or migrate or archive_file or dry_run or unresolved"`
Expected: FAIL (`migrate_rows` missing).

- [ ] **Step 3: Implement**

Add after `cmd_check` (before `group_items`):

```python
## One-off migration from the git-step words to the Jira stage words (spec section 7).
LEGACY_MAP = {
    "In progress": "Development", "PR to dev": "Testing", "Merged to sit": "Development",
    "Merged to dev": "Ready For Release", "PR to master": "Ready For Release",
}  # fmt: skip
RECENT_DAYS = 7  # a Released row this young is flagged "check" in the migration report


def read_legacy(path: Path) -> list[dict[str, str]]:
    """Read a CSV without validating statuses: the old words must stay readable here."""
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != COLUMNS:
            sys.exit(f"{path}: header {reader.fieldnames} != expected {COLUMNS}.")
        return list(reader)


def _released_outcome(
    row: dict[str, str], cache: dict, today: dt.date, resolve: dict[str, str]
) -> tuple[str | None, str]:
    """Status for the last Released row of a ticket, or None when the user must decide."""
    ticket = row["ticket"]
    if ticket in resolve:
        return resolve[ticket], "resolved by the user"
    jira = cache.get(ticket, {}).get("jira_status", "")
    status = PAGE_TO_LOGBOOK.get(JIRA_STATUS.get(jira, ""))
    if not status:
        return None, f"Jira status {jira or 'unknown'!r} has no logbook status"
    try:
        age = (today - dt.date.fromisoformat(row["date"])).days
    except ValueError:
        return status, f"Jira {jira!r} (check: no usable date)"
    note = f"Jira {jira!r}"
    return status, note + (" (check: recent row)" if age <= RECENT_DAYS else "")


def migrate_rows(
    rows: list[dict[str, str]], cache: dict, today: dt.date, resolve: dict[str, str]
) -> tuple[list[dict[str, str]], list[str], list[tuple[str, str]]]:
    """Return (new rows, report lines, review list of (date, ticket)). Pure; writes nothing."""
    last: dict[str, int] = {}
    for i, r in enumerate(rows):  # last row per ticket by date, ties keep file order
        j = last.get(r["ticket"])
        if j is None or r["date"] >= rows[j]["date"]:
            last[r["ticket"]] = i
    out: list[dict[str, str]] = []
    report: list[str] = []
    review: list[tuple[str, str]] = []
    for i, r in enumerate(rows):
        new, old, note = dict(r), r["status"], ""
        if old in LEGACY_MAP:
            new["status"] = LEGACY_MAP[old]
        elif old == "Released":
            if last[r["ticket"]] != i:
                new["status"], note = "Done", "earlier Released row: history"
            else:
                status, note = _released_outcome(r, cache, today, resolve)
                if status is None:
                    review.append((r["date"], r["ticket"]))
                    report.append(
                        f"{r['date']} {r['ticket']}: Released -> REVIEW ({note})"
                    )
                    out.append(new)
                    continue
                new["status"] = status
        elif old and old not in STATUSES:
            sys.exit(f"Unknown legacy status {old!r} on {r['date']} {r['ticket']}.")
        if new["status"] != old:
            tail = f" [{note}]" if note else ""
            report.append(
                f"{r['date']} {r['ticket']}: {old or '-'} -> {new['status']}{tail}"
            )
        out.append(new)
    return out, report, review


def cmd_migrate(args: argparse.Namespace) -> None:
    """Rewrite old status words in the logbook and archive. --dry-run writes nothing."""
    resolve: dict[str, str] = {}
    for item in args.resolve:
        ticket, _, status = item.partition("=")
        if status not in STATUSES:
            sys.exit(f"--resolve {item!r}: status must be one of {STATUSES}.")
        resolve[ticket] = status
    cache, today = load_cache(), dt.date.today()
    results = []
    blocked = False
    for path in (LOGBOOK, ARCHIVE):
        rows = read_legacy(path)
        new, report, review = migrate_rows(rows, cache, today, resolve)
        before = sorted({r["status"] or "-" for r in rows})
        print(
            f"## {path.name}: {len(rows)} row(s), statuses before: {', '.join(before) or '-'}"
        )
        print("\n".join(f"- {line}" for line in report) or "- nothing to change")
        for date, ticket in review:
            print(f"! REVIEW {date} {ticket}: rerun with --resolve {ticket}=<status>")
        blocked = blocked or bool(review)
        results.append((path, rows, new))
    if blocked:
        sys.exit("Rows need a decision; nothing was written.")
    if args.dry_run:
        print("\nDry run: nothing was written.")
        return
    for path, rows, new in results:
        problems = [row_problem(r) for r in new if row_problem(r)]
        if len(new) != len(rows) or problems:
            sys.exit(
                f"{path}: validation failed ({problems[:1]}); nothing was written."
            )
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    for path, rows, new in results:
        if path.exists():
            shutil.copy2(path, path.with_name(f"{path.name}.pre-migration-{stamp}"))
        write_rows(new, path)
    print("\nMigrated. Backups: *.pre-migration-" + stamp)
```

Add the subcommand in `main()` after `rename`:

```python
    mig = sub.add_parser(
        "migrate-statuses", help="One-off: rewrite old status words to the Jira stage words"
    )
    mig.add_argument("--dry-run", action="store_true")
    mig.add_argument(
        "--resolve", action="append", default=[], metavar="TICKET=STATUS",
        help="decide a Released row that needs review (repeatable)",
    )  # fmt: skip
    mig.set_defaults(func=cmd_migrate)
```

- [ ] **Step 4: Run to verify they pass**

Run: `uv run pytest tests/test_logbook.py -v`
Expected: PASS.

- [ ] **Step 5: Python 3.9 and 3.12 check**

Run: `for v in 3.9 3.12; do uv run --no-project --python $v python -c "import importlib.util,sys;s=importlib.util.spec_from_file_location('l','CLAUDE/skills/logbook/logbook.py');m=importlib.util.module_from_spec(s);sys.modules['l']=m;s.loader.exec_module(m);print('$v ok')"; done`
Expected: `3.9 ok` and `3.12 ok`.

- [ ] **Step 6: Checkpoint**

Ruff check and format; show diff; commit only on request (`✨ feat(claude): add the one-off migrate-statuses command`).

---

### Task 5: Instruction text, config example and workflow doc (template side)

**Files:**
- Modify: `CLAUDE/skills/logbook/SKILL.md`, `CLAUDE/skills/logbook/config.example.json`, `CLAUDE/CLAUDE.md`, `CLAUDE/commands/generate-pr-message.md`, `CLAUDE/skills/jira-ticket-kickoff/SKILL.md`, `CLAUDE/skills/bast-generator/SKILL.md`, `README.md`, `CLAUDE/README.md`
- Create: `docs/guidelines/DEV-WORKFLOW.md`
- Test: `tests/test_logbook.py` (a text-sweep test)

**Interfaces:**
- Produces: instruction files that contain none of the removed words; the same edits are re-applied to the live files in Task 7.

- [ ] **Step 1: Write the failing sweep test**

```python
OLD_WORDS = ["`In progress`", "`PR to dev`", "`Merged to dev`", "`Merged to sit`",
             "`PR to master`", "`Released`", "Ready to Release"]  # fmt: skip
SWEPT = [
    "CLAUDE/CLAUDE.md", "CLAUDE/commands/generate-pr-message.md",
    "CLAUDE/skills/jira-ticket-kickoff/SKILL.md", "CLAUDE/skills/bast-generator/SKILL.md",
    "CLAUDE/skills/logbook/SKILL.md", "docs/guidelines/DEV-WORKFLOW.md",
]  # fmt: skip


@pytest.mark.parametrize("name", SWEPT)
def test_instruction_files_use_only_the_new_status_words(name: str) -> None:
    text = (ROOT / name).read_text(encoding="utf-8")
    assert [w for w in OLD_WORDS if w in text] == []


def test_config_example_lists_the_four_waiting_stages() -> None:
    cfg = json.loads((ROOT / "CLAUDE/skills/logbook/config.example.json").read_text())
    assert cfg["other_court"] == ["TESTING", "READY FOR RELEASE", "DEPLOYMENT", "PAT"]
```

(The `logbook/SKILL.md` migration section may name the old words inside the `migrate-statuses` description; write them without backticks there, e.g. "the old git-step words", so the sweep stays strict.)

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/test_logbook.py -v -k "instruction_files or config_example"`
Expected: FAIL for `CLAUDE.md`, `generate-pr-message.md`, `jira-ticket-kickoff`, `logbook/SKILL.md`, config; the missing `DEV-WORKFLOW.md` and unchanged `bast-generator` file error or pass respectively.

- [ ] **Step 3: Apply the edits**

`CLAUDE/skills/logbook/config.example.json`: set `"other_court": ["TESTING", "READY FOR RELEASE", "DEPLOYMENT", "PAT"],`.

`CLAUDE/CLAUDE.md`, section "Jira Status on PRs": replace the sentence `PR to `dev` → `Testing`; PR to `master` → `Ready to Release`. Notify and ask before` with:

```text
PR to `dev` → `Testing`; the PR merged into `dev` (user approval) → `Ready For Release`;
a PR to `master` changes nothing (CAB approval moves the ticket to `Deployment` and the
deployment to `PAT`; the user moves those, and the pipeline board reminds). Notify and ask before
```

`CLAUDE/commands/generate-pr-message.md`:
- Table rows become `| Feature → `dev` | `Testing` |` and `| `dev` → `master` | no change (`Ready For Release` was set when the PR merged into `dev`) |`.
- Step 6 text `(`/logbook add`, `status` = `PR to dev` / `PR to master`)` becomes `(`/logbook add`, `status` = `Testing`; when the user later reports the PR merged into `dev`, offer `Ready For Release` the same way)`.
- Checklist line becomes `- [ ] Jira status checked (`Testing` for → dev, `Ready For Release` once merged into dev, no change for → master); transition only after the user confirmed`.

`CLAUDE/skills/jira-ticket-kickoff/SKILL.md`: `status` = `In progress` becomes `status` = `Development` (`Analysis` when the ticket starts in design).

`CLAUDE/skills/bast-generator/SKILL.md` step 8: append `, `status` = `Testing`` after `` `type` = `docs` ``.

`CLAUDE/skills/logbook/SKILL.md`:
- Replace the rule-4 status table with:

```markdown
   | State | `status` | Jira status |
   | --- | --- | --- |
   | Brainstorming, design, plan | `Analysis` | `Data Analysis` |
   | Implementation and SIT | `Development` | `Data Development` |
   | PR open to `dev`, UAT, BAST generated | `Testing` | `Testing` |
   | PR merged into `dev` (user approval), CAB registration | `Ready For Release` | `Ready For Release` |
   | CAB approved, deploying | `Deployment` | `Deployment` |
   | Deployed, production assurance test | `PAT` | `PAT` |
   | Finished, no error one week after PAT; non-code work finished | `Done` | `Done` |
   | Fixing a defect found after release or testing | `Fixing` | none |
   | Blocked or on hold | `Hold` | `Hold` |

   **Jira wins** on status when it differs from the logbook (the user moves the ticket in Jira).
   A PR to `master` and a merge into `sit` do not move the status.
```

- Replace the `Status` mapping sentence (page words) with: `` `Status` = the latest status mapped to the page words (`Analysis` → `ANALYST`, `Development` → `DEVELOPMENT`, `Testing` → `TESTING`, `Ready For Release` → `READY FOR RELEASE`, `Deployment` → `DEPLOYMENT`, `PAT` → `PAT`, `Done` → `DONE`, plus `FIXING` and `HOLD`) ``, and say a fresh (refreshed within 7 days), mapped Jira status outranks the logbook status.
- Remove the lines saying a ticket with logbook rows keeps the logbook status (publish step 0a) and the "whichever changed more recently" rule; replace both by `Jira wins; mention any ticket whose logbook status differs and propose the `add`.`
- In the backfill section replace ``mark tickets with no PR `In progress` `` by ``mark tickets with no PR `Development` `` and in the command example use `--status "Testing"`.
- Add to "Commands": `logbook.py migrate-statuses --dry-run` (one-off, old git-step words to the Jira stage words; `--resolve TICKET=Status` for rows it cannot decide), `cache set ... --pat-since YYYY-MM-DD`.
- Add to publish step 0a: `Also record the date a PAT ticket entered PAT with `--pat-since`, read from the changelog (`expand: changelog`).`

`docs/guidelines/DEV-WORKFLOW.md`: copy section 3 (stage table), section 4 (status table without its "Replaces" column, so the old words stay out of it), the trigger table of 5.2 and the precedence rules of 5.1 from the spec, with a one-paragraph intro, no ticket keys of real tickets and no internal hosts.

`README.md` and `CLAUDE/README.md`: add `DEV-WORKFLOW.md` to the guidelines list, next to the WSL migration and Windows guides.

- [ ] **Step 4: Run to verify it passes**

Run: `uv run pytest tests/test_logbook.py -v`
Expected: PASS.

- [ ] **Step 5: Sweep the changeset**

Run: `grep -rnE "In progress|PR to (dev|master)|Merged to (dev|sit)|Ready to Release|Released" CLAUDE docs/guidelines README.md | grep -v "create-readme.md" | grep -v "logbook.py"`
Expected: no output. (`create-readme.md` has an unrelated "In progress" table cell.)

- [ ] **Step 6: Checkpoint**

`uv run ruff check . && uv run ruff format --check . && uv run pytest`; show `git status`; commit only on request (`📝 docs(claude): move the logbook and Jira rules to the Jira stage words`).

---

### Task 6: Unit A verification and PR

**Files:** none new.

- [ ] **Step 1: Full verification**

Run: `uv run ruff check . && uv run ruff format --check . && uv run mypy . && uv run pytest`
Expected: all pass (mypy: if the helper is not in its scope, the run is unchanged from before).

- [ ] **Step 2: Python 3.9 and 3.12 test run of the helper tests**

Run: `for v in 3.9 3.12; do uv run --no-project --python $v --with pytest python -m pytest tests/test_logbook.py -q; done`
Expected: all tests pass on both. If `3.9` fails on typing in the tests themselves, keep the helper compatible and run the test file under 3.11 only; the helper import check from Task 4 step 5 is the gate.

- [ ] **Step 3: Open the PR only when the user asks**

Branch from `dev` (e.g. `feat/dev-workflow-vocabulary`), push, PR to `dev` with the release changelog if the repo's flow requires one. PR body ends with `🤖 Generated with [Claude Code](https://claude.com/claude-code)`. Propose a logbook row (`ticket` = `dev-workflow`, `type` = `chore`, `status` = `Testing`).

---

### Task 7: Deploy to the live `~/.claude` and migrate the logbook (with the user present)

**Files:** live `~/.claude/skills/logbook/logbook.py`, `SKILL.md`, `config.json`, `~/.claude/CLAUDE.md`, `~/.claude/commands/generate-pr-message.md`, `~/.claude/skills/jira-ticket-kickoff/SKILL.md`, `~/.claude/skills/bast-generator/SKILL.md`, `~/.claude/logbook/*`.

Do this only after Unit A is merged into `dev`, and in one sitting. `~/.claude` is not a git repository, so the backup in step 1 is the only rollback.

- [ ] **Step 1: Back up**

```bash
stamp=$(date +%Y%m%d-%H%M%S); b=~/.claude/logbook/pre-migration-$stamp; mkdir -p "$b"
cp ~/.claude/logbook/{logbook.csv,logbook-archive.csv,jira-cache.json,config.json} "$b"/ 2>/dev/null
cp ~/.claude/skills/logbook/{logbook.py,SKILL.md} "$b"/
cp ~/.claude/CLAUDE.md ~/.claude/commands/generate-pr-message.md "$b"/
cp ~/.claude/skills/jira-ticket-kickoff/SKILL.md "$b"/kickoff-SKILL.md
cp ~/.claude/skills/bast-generator/SKILL.md "$b"/bast-SKILL.md
ls "$b"
```

Expected: all files listed.

- [ ] **Step 2: Read-only Jira transition check**

For one existing DA ticket in each of `Testing`, `Ready For Release`, `Deployment`, `PAT`, list the transitions the Atlassian MCP offers (`discover` then `executeRead`; no transition call). Record that the next stage is offered from each. If one is missing, report it and stop here.

- [ ] **Step 3: Refresh the Jira cache for every ticket with a Released row**

```bash
python3 - <<'EOF'
import csv, pathlib
rows = []
for name in ("logbook.csv", "logbook-archive.csv"):
    p = pathlib.Path.home() / ".claude/logbook" / name
    if p.exists():
        rows += list(csv.DictReader(p.open(newline="", encoding="utf-8")))
print(", ".join(sorted({r["ticket"] for r in rows if r["status"] == "Released" and r["ticket"][:3] == "DA-"})))
EOF
```

Fetch those keys with `searchJiraIssuesUsingJql` (`key in (...)`, fields `status`, `updated`) and store each with `cache set --ticket K --jira-status "<status>" --updated <date>` (live helper still the old one: this works because `cache set` is unchanged apart from the new flags). For tickets in `PAT`, read the changelog and add `--pat-since`.

- [ ] **Step 4: Install the new helper and the live instruction edits**

```bash
cp CLAUDE/skills/logbook/logbook.py ~/.claude/skills/logbook/logbook.py
python3 ~/.claude/skills/logbook/logbook.py --help | grep migrate-statuses
```

Then apply the Task 5 edits to the live `SKILL.md`, `CLAUDE.md`, `generate-pr-message.md`, kickoff and bast files with the Edit tool (Read each first; they differ from the template by placeholders, so do not copy the template over them). In `~/.claude/logbook/config.json` set `"other_court": ["TESTING", "READY FOR RELEASE", "DEPLOYMENT", "PAT"]`.

- [ ] **Step 5: Dry run, then migrate**

```bash
python3 ~/.claude/skills/logbook/logbook.py migrate-statuses --dry-run
```

Show the report to the user. For each `REVIEW` row, ask the user for the status and rerun with `--resolve TICKET=Status`. After the user's OK:

```bash
python3 ~/.claude/skills/logbook/logbook.py migrate-statuses [--resolve ...]
python3 ~/.claude/skills/logbook/logbook.py week
python3 ~/.claude/skills/logbook/logbook.py check
python3 ~/.claude/skills/logbook/logbook.py sync
```

Expected: `week` and `check` run without a status error; `sync` copies the new CSV.

- [ ] **Step 6: Recovery (only if step 5 fails or the result is wrong)**

```bash
cp "$b"/logbook.csv "$b"/logbook-archive.csv "$b"/jira-cache.json "$b"/config.json ~/.claude/logbook/
cp "$b"/logbook.py "$b"/SKILL.md ~/.claude/skills/logbook/
cp "$b"/CLAUDE.md ~/.claude/CLAUDE.md
cp "$b"/generate-pr-message.md ~/.claude/commands/generate-pr-message.md
cp "$b"/kickoff-SKILL.md ~/.claude/skills/jira-ticket-kickoff/SKILL.md
cp "$b"/bast-SKILL.md ~/.claude/skills/bast-generator/SKILL.md
```

Then `python3 ~/.claude/skills/logbook/logbook.py week` must run again. Keep the backup until Unit B's first `pipeline` and `check` runs pass.

---

# Unit B: the `pipeline` board

### Task 8: Board derivation (pure)

**Files:**
- Modify: `CLAUDE/skills/logbook/logbook.py` (new `BOARD_ORDER`, `NEXT_ACTION`, `PAT_DONE_DAYS`, `board_refreshed`, `board_entry`, `derive_board`)
- Test: `tests/test_logbook.py`

**Interfaces:**
- Consumes: `JIRA_STATUS`, `PAGE_STATUS`, `PAGE_TO_LOGBOOK`, `STAGE`, `OUTSIDE_ORDER`, evidence dicts from Task 2, `group_items`.
- Produces: `board_refreshed(cache: dict) -> str` (latest `refreshed` among tracked entries), `board_entry(ticket, info, item, ev, today, live) -> dict` with keys `ticket, word, jira_status, logbook_status, repos, git, next, flags` (`flags` is a list of `(text, fix)` tuples), `derive_board(cache, items, evidence, today) -> tuple[list[dict], bool, str]` (entries sorted by stage then ticket, `live`, `refreshed`).

- [ ] **Step 1: Write the failing tests**

```python
def ev(
    stage: str = "", last: str = "2026-10-14", master: bool = False, repos=("r",)
) -> dict:
    return {"stage": stage, "last": last, "repos": set(repos), "master": master}


def entry(
    lb, status="", jira="", info_extra=None, evidence=None, live=True, today=TODAY
):
    info = {"jira_status": jira, **(info_extra or {})}
    item = [row("2026-10-10", "DA-1", status)] if status else []
    return lb.board_entry("DA-1", info, item, evidence, today, live)


def flag_texts(e) -> list[str]:
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
    assert any("Data Analysis" in t or "analysis" in t.lower() for t in flag_texts(e))


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
        lb,
        "Testing",
        "Hold",
        {"hold_since": "2026-10-01"},
        evidence=ev("Ready For Release", master=True),
    )
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
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/test_logbook.py -v -k "board or word_comes or merged_dev or master_pr or commits_while or pat_age or hold_wins or degraded or jira_and_logbook"`
Expected: FAIL (`board_entry` missing).

- [ ] **Step 3: Implement**

Add after `cmd_check`'s neighbours (before `group_items` is fine):

```python
## The board (spec 5.1): where every open ticket stands, and what to do next.
BOARD_ORDER = [
    "TODO", "ANALYST", "DEVELOPMENT", "TESTING", "READY FOR RELEASE", "DEPLOYMENT",
    "PAT", "FIXING", "HOLD",
]  # fmt: skip
NEXT_ACTION = {
    "TODO": "start it (jira-ticket-kickoff)",
    "ANALYST": "finish the spec and plan, then move Jira to Data Development",
    "DEVELOPMENT": "finish and test (SIT), then open the PR to dev (/generate-pr-message)",
    "TESTING": "generate the BAST, get UAT approval, merge the PR into dev",
    "READY FOR RELEASE": "update the BAST with the approval, open dev to master, wait for CAB",
    "DEPLOYMENT": "deploy, then move Jira to PAT",
    "PAT": "watch production; Done after 7 days without error",
    "FIXING": "finish the fix, then follow its stage",
}  # fmt: skip
PAT_DONE_DAYS = 7


def board_refreshed(cache: dict) -> str:
    """Latest Jira refresh stamp among the tracked cache entries ('' when none)."""
    stamps = [i.get("refreshed", "") for i in cache.values() if i.get("track")]
    return max(stamps) if stamps else ""


def board_entry(
    ticket: str,
    info: dict,
    item: list[dict[str, str]],
    ev: dict | None,
    today: dt.date,
    live: bool,
) -> dict[str, Any]:
    """One board line. Jira supplies the status; git evidence only raises flags."""
    last = item[-1] if item else None
    jira_word = JIRA_STATUS.get(info.get("jira_status", ""))
    log_word = PAGE_STATUS.get(last["status"]) if last else None
    word = jira_word or log_word or "TODO"
    entry: dict[str, Any] = {
        "ticket": ticket, "word": word, "jira_status": info.get("jira_status", ""),
        "logbook_status": last["status"] if last else "",
        "repos": sorted(ev["repos"]) if ev else [],
        "git": (ev["stage"] or "commits") if ev else "",
        "next": NEXT_ACTION.get(word, ""), "flags": [],
    }  # fmt: skip
    flags: list[tuple[str, str]] = entry["flags"]
    if word == "HOLD":
        entry["next"] = f"on hold since {info.get('hold_since') or 'an unknown date'}"
        if ev and (ev["stage"] or ev["master"]):
            flags.append(("note: git activity while on hold", "resolve the hold first"))
        return entry
    if not live:
        return entry
    if ev:
        rank = STAGE.get(ev["stage"], 0)
        if ev["stage"] == "Ready For Release" and word == "TESTING":
            flags.append(
                (
                    "PR merged into dev but Jira is still Testing",
                    "move Jira to Ready For Release",
                )
            )
        if ev["master"] and word == "TESTING":
            flags.append(
                (
                    "a dev to master PR exists but Jira is still Testing",
                    "move Jira to Ready For Release first",
                )
            )
        if word == "ANALYST" and rank <= STAGE["Development"]:
            flags.append(
                (
                    "commits exist but Jira is still Data Analysis",
                    "move Jira to Data Development",
                )
            )
    if word == "PAT":
        since = info.get("pat_since")
        if not since:
            flags.append(
                (
                    "PAT date unknown",
                    "read the Jira changelog and run cache set --pat-since",
                )
            )
        elif (today - dt.date.fromisoformat(since)).days >= PAT_DONE_DAYS:
            flags.append(
                (
                    f"in PAT since {since} (7 or more days)",
                    "propose Done in Jira and the logbook, then /clean-gone",
                )
            )
    target = PAGE_TO_LOGBOOK.get(jira_word or "")
    if target and log_word and jira_word != log_word:
        flags.append((
            f"Jira {jira_word} vs logbook {log_word}",
            f'Jira wins: add --ticket {ticket} --status "{target}"',
        ))  # fmt: skip
    return entry


def derive_board(
    cache: dict,
    items: list[list[dict[str, str]]],
    evidence: dict[str, dict],
    today: dt.date,
) -> tuple[list[dict[str, Any]], bool, str]:
    """Entries for every open ticket, ordered by stage; live only if Jira was refreshed today."""
    refreshed = board_refreshed(cache)
    live = refreshed == today.isoformat()
    by_ticket = {i[0]["ticket"]: i for i in items}
    tickets = {t for t, info in cache.items() if info.get("track")}
    tickets |= {t for t, i in by_ticket.items() if i[-1]["status"] not in FINISHED}
    entries = []
    for ticket in sorted(tickets):
        item = by_ticket.get(ticket, [])
        e = board_entry(
            ticket, cache.get(ticket, {}), item, evidence.get(ticket), today, live
        )
        if e["word"] == "DONE":
            continue
        entries.append(e)
    entries.sort(
        key=lambda e: (
            BOARD_ORDER.index(e["word"]) if e["word"] in BOARD_ORDER else 99,
            e["ticket"],
        )
    )
    return entries, live, refreshed
```

- [ ] **Step 4: Run to verify they pass**

Run: `uv run pytest tests/test_logbook.py -v`
Expected: PASS.

- [ ] **Step 5: Checkpoint**

Ruff check and format; show diff; commit only on request (`✨ feat(claude): derive the pipeline board from Jira, git and the logbook`).

---

### Task 9: `pipeline` subcommand, rendering and degraded banner

**Files:**
- Modify: `CLAUDE/skills/logbook/logbook.py` (`render_board`, `cmd_pipeline`, argparse)
- Test: `tests/test_logbook.py`

**Interfaces:**
- Consumes: `derive_board`, `git_evidence`, `group_items`, `read_rows`, `load_config`, `load_cache`.
- Produces: `render_board(entries, live, refreshed, notes) -> str`; `logbook.py pipeline [--since YYYY-MM-DD]` (default 30 days ago) printing the board and writing nothing.

- [ ] **Step 1: Write the failing tests**

```python
def test_render_board_groups_by_stage_and_shows_flags(lb: ModuleType) -> None:
    e = entry(lb, "Testing", "Testing", evidence=ev("Ready For Release"))
    text = lb.render_board([e], True, TODAY.isoformat(), [])
    assert "## TESTING (1)" in text
    assert "DA-1" in text and "next:" in text
    assert "PR merged into dev but Jira is still Testing" in text
    assert "STALE" not in text


def test_render_board_shows_the_stale_banner_in_degraded_mode(lb: ModuleType) -> None:
    text = lb.render_board(
        [entry(lb, "Testing", "Testing")],
        False,
        "2026-10-01",
        ["r: gh pr list unavailable (commits only)"],
    )
    assert "STALE" in text and "2026-10-01" in text
    assert "gh pr list unavailable" in text


def test_pipeline_command_prints_and_writes_nothing(
    lb, tmp_path, monkeypatch, capsys
) -> None:
    write_csv(lb.LOGBOOK, [row("2026-10-10", "DA-1", "Testing")])
    (tmp_path / "config.json").write_text(
        json.dumps({"repo_paths": {"r": str(tmp_path)}})
    )
    (tmp_path / "jira-cache.json").write_text(
        json.dumps(
            {
                "DA-1": {
                    "track": True,
                    "jira_status": "Testing",
                    "refreshed": dt.date.today().isoformat(),
                }
            }
        )
    )
    monkeypatch.setattr(lb, "_run", fake_run_factory([]))
    before = lb.LOGBOOK.read_text()
    lb.cmd_pipeline(argparse.Namespace(since=""))
    assert "## TESTING (1)" in capsys.readouterr().out
    assert lb.LOGBOOK.read_text() == before


def test_pipeline_works_without_gh(lb, tmp_path, monkeypatch, capsys) -> None:
    (tmp_path / "config.json").write_text(
        json.dumps({"repo_paths": {"r": str(tmp_path)}})
    )
    (tmp_path / "jira-cache.json").write_text(
        json.dumps(
            {
                "DA-1": {
                    "track": True,
                    "jira_status": "Data Development",
                    "refreshed": dt.date.today().isoformat(),
                }
            }
        )
    )

    def no_gh(cmd, cwd):
        if cmd[:2] == ["git", "config"]:
            return "me\n"
        if cmd[:2] == ["git", "log"]:
            return ""
        return None

    monkeypatch.setattr(lb, "_run", no_gh)
    lb.cmd_pipeline(argparse.Namespace(since=""))
    out = capsys.readouterr().out
    assert "gh pr list unavailable" in out and "DA-1" in out
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/test_logbook.py -v -k "render_board or pipeline"`
Expected: FAIL (`render_board`, `cmd_pipeline` missing).

- [ ] **Step 3: Implement**

```python
def render_board(
    entries: list[dict[str, Any]], live: bool, refreshed: str, notes: list[str]
) -> str:
    """Text board grouped by stage; a stale banner when Jira was not refreshed today."""
    lines = [f"# Pipeline board {dt.date.today().isoformat()}"]
    if not live:
        lines += [
            "",
            f"STALE: the Jira cache was last refreshed {refreshed or 'never'}. Statuses are "
            "from the cache and not verified; Jira-dependent flags are hidden. "
            "Refresh with cache set (logbook skill, step 0a) for flags.",
        ]
    lines += [f"- {n}" for n in notes]
    for word in BOARD_ORDER:
        group = [e for e in entries if e["word"] == word]
        if not group:
            continue
        lines += ["", f"## {word} ({len(group)})"]
        for e in group:
            where = f" [{', '.join(e['repos'])}]" if e["repos"] else ""
            git = f" | git: {e['git']}" if e["git"] else ""
            lines.append(
                f"- {e['ticket']}{where} | Jira: {e['jira_status'] or '-'}{git}"
            )
            lines.append(f"  next: {e['next']}")
            lines += [f"  ! {text} -> {fix}" for text, fix in e["flags"]]
    if not entries:
        lines += ["", "No open tickets."]
    return "\n".join(lines)


def cmd_pipeline(args: argparse.Namespace) -> None:
    """Print where every open ticket stands. Read-only: writes no file."""
    cfg, cache = load_cache_and_config()
    since = args.since or (dt.date.today() - dt.timedelta(days=30)).isoformat()
    iso_week(since)
    evidence, notes = git_evidence(cfg.get("repo_paths", {}), since)
    entries, live, refreshed = derive_board(
        cache, group_items(read_rows()), evidence, dt.date.today()
    )
    print(render_board(entries, live, refreshed, notes))
```

Use the two loaders the file already has instead of a helper: replace `cfg, cache = load_cache_and_config()` with `cfg, cache = load_config(), load_cache()`.

Add the subcommand in `main()` after `check`:

```python
pipe = sub.add_parser("pipeline", help="Board of open tickets by stage (read-only)")
pipe.add_argument(
    "--since", default="", help="YYYY-MM-DD for git/PR scan (default: 30 days ago)"
)
pipe.set_defaults(func=cmd_pipeline)
```

- [ ] **Step 4: Run to verify they pass**

Run: `uv run pytest tests/test_logbook.py -v && for v in 3.9 3.12; do uv run --no-project --python $v python -c "import importlib.util,sys;s=importlib.util.spec_from_file_location('l','CLAUDE/skills/logbook/logbook.py');m=importlib.util.module_from_spec(s);sys.modules['l']=m;s.loader.exec_module(m);print('$v ok')"; done`
Expected: all tests pass; `3.9 ok`, `3.12 ok`.

- [ ] **Step 5: Checkpoint**

Ruff check and format; show diff; commit only on request (`✨ feat(claude): add the read-only pipeline board command`).

---

### Task 10: `/pipeline` command, trigger prompts, docs and Unit B PR

**Files:**
- Create: `CLAUDE/commands/pipeline.md`
- Modify: `CLAUDE/skills/logbook/SKILL.md` (document `pipeline` and the trigger prompts), `CLAUDE/CLAUDE.md` (command table row, "Work Logbook" prompt list), `CLAUDE/README.md` and `README.md` (command lists), `docs/guidelines/DEV-WORKFLOW.md` (board section)
- Test: `tests/test_logbook.py`

- [ ] **Step 1: Write the failing test**

```python
def test_pipeline_command_file_exists_and_calls_the_helper() -> None:
    text = (ROOT / "CLAUDE/commands/pipeline.md").read_text(encoding="utf-8")
    assert text.startswith("---\ndescription:")
    assert "logbook.py pipeline" in text and "cache set" in text
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/test_logbook.py -v -k pipeline_command_file`
Expected: FAIL (file missing).

- [ ] **Step 3: Create the command**

`CLAUDE/commands/pipeline.md`:

````markdown
---
description: Show where every open ticket stands (stage, git state, next step) and flag gaps between Jira, git and the logbook
allowed-tools: Bash(python3:*), Bash(git:*), Bash(gh:*)
---

# Pipeline board

Show every open ticket by stage with the next action. Read-only: nothing is written to Jira, git or the logbook without the user's OK.

## Steps

1. Refresh Jira first so the flags are live: run the logbook skill's step 0a (assigned DA tickets with `cache set --track yes --jira-status ... --updated ...`). For each ticket in `PAT` read the issue changelog and store `--pat-since <date it entered PAT>`.
2. Run the board:

   ```bash
   python3 ~/.claude/skills/logbook/logbook.py pipeline
   ```

3. Show the output as is. For each `!` flag, propose the fix it names (Jira transition by target status, logbook `add`, `Done`, `/clean-gone`) and apply it only after the user confirms, one at a time.
4. If the board prints `STALE`, Jira could not be refreshed: say so, do not act on Jira-dependent advice, and offer to retry.
````

Add to `SKILL.md` a "Pipeline board and trigger prompts" section with the trigger table of spec 5.2 (event → prompt), and state that `/pipeline` is the entry point. Add the `/pipeline` row to the slash-command tables in `CLAUDE/CLAUDE.md`, `CLAUDE/README.md`, `README.md`.

- [ ] **Step 4: Run to verify it passes, then full verification**

Run: `uv run pytest && uv run ruff check . && uv run ruff format --check .`
Expected: all pass.

- [ ] **Step 5: Deploy the command and run the live dry run (with the user)**

```bash
cp CLAUDE/commands/pipeline.md ~/.claude/commands/pipeline.md
cp CLAUDE/skills/logbook/logbook.py ~/.claude/skills/logbook/logbook.py
python3 ~/.claude/skills/logbook/logbook.py pipeline
```

Apply the same `CLAUDE.md` and `SKILL.md` additions to the live files with the Edit tool. Compare the board by hand against the Jira board. Fix mismatches in the helper (with a new test each) before relying on it.

- [ ] **Step 6: Checkpoint and PR**

Show `git status`; commit only on request (`✨ feat(claude): add /pipeline and the stage trigger prompts`). Open the Unit B PR to `dev` only when the user asks; propose the logbook row (`ticket` = `dev-workflow`, `status` = `Testing`).

---

## Self-Review

**Spec coverage**
- Section 3 stage model and the `Ready For Release` correction: Task 5 (text), Task 2 (`pr_stage`).
- Section 4 status table, `JIRA_STATUS`/`STATUS_COLOR`/court/finished: Task 1; Jira-wins in `check` and page: Tasks 2 and 3; non-Jira `Done`: Task 5 table.
- 5.1 board, flags, precedence, modes, PAT age: Tasks 8 and 9; 5.1.1 table: Task 2; `refreshed`/`--pat-since`: Task 3.
- 5.2 trigger prompts: Task 10 (SKILL text) and Task 5 (generate-pr-message, kickoff, bast).
- 5.3 edits, read-only transition check: Tasks 5 and 7.
- Section 7 migration, rollback: Tasks 4 and 7.
- Section 9 tests: Tasks 1-4, 8, 9. Section 10 units: Units A and B, repo files in PRs, live files at deployment.

**Placeholder scan:** no TBD or deferred code; every code step has the code. Task 5 describes text edits with exact replacement text; the long `DEV-WORKFLOW.md` is specified as a copy of named spec sections.

**Type consistency:** `pr_stage` returns logbook status words used by `STAGE`; evidence keys `stage, last, repos, master` match in Tasks 2, 8 and tests; `board_entry` signature in Task 8 matches the tests and `derive_board`; `migrate_rows`/`cmd_migrate` names match across Task 4.
