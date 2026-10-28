"""Tests for the ticket handover helper (CLAUDE/skills/handover/handover.py)."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "CLAUDE/skills/handover/handover.py"


@pytest.fixture
def ho() -> ModuleType:
    spec = importlib.util.spec_from_file_location("handover_under_test", SRC)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    path = tmp_path / "repo"
    path.mkdir()
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    return path


T = "PROJ-1234"


@pytest.mark.parametrize("ticket", ["PROJ-1234", "my_slug.1", "a-b", "X"])
def test_valid_tickets(ho: ModuleType, ticket: str) -> None:
    assert ho.validate_ticket(ticket) == ticket


@pytest.mark.parametrize(
    "ticket", ["", "../x", "a/b", "a..b", " x", "a b", ".hidden", "x\\y"]
)
def test_invalid_tickets_are_refused(ho: ModuleType, ticket: str) -> None:
    with pytest.raises(ho.HandoverError):
        ho.validate_ticket(ticket)


def test_find_repo_from_a_subdirectory_and_an_explicit_path(
    ho, repo, monkeypatch
) -> None:
    sub = repo / "a" / "b"
    sub.mkdir(parents=True)
    monkeypatch.chdir(sub)
    assert ho.find_repo(None).resolve() == repo.resolve()
    monkeypatch.chdir(repo.parent)  # the umbrella folder above the repository
    assert ho.find_repo(str(repo)).resolve() == repo.resolve()


def test_find_repo_refuses_outside_a_repository(ho, tmp_path, monkeypatch) -> None:
    outside = tmp_path / "plain"
    outside.mkdir()
    monkeypatch.chdir(outside)
    with pytest.raises(ho.HandoverError, match="not inside a git repository"):
        ho.find_repo(None)
    with pytest.raises(ho.HandoverError):
        ho.find_repo(str(tmp_path / "missing"))


def test_paths(ho: ModuleType, tmp_path: Path) -> None:
    assert (
        ho.inventory_path(tmp_path, T)
        == tmp_path / "release" / T / "docs" / "HANDOVER.md"
    )
    assert (
        ho.state_path(tmp_path, T) == tmp_path / "scratch" / T / "handover.state.json"
    )
    with pytest.raises(ho.HandoverError):
        ho.inventory_path(tmp_path, "../x")


@pytest.mark.parametrize(
    "value",
    ["password=hunter2", "PWD: abc", "token=abc", "Token: xyz", "secret=1", "api_key=zz",
     "api-key: zz", "access_key=1", "https://user:pass@host/db"],
)  # fmt: skip
def test_credentials_are_refused(ho: ModuleType, value: str) -> None:
    with pytest.raises(ho.HandoverError, match="credential"):
        ho.check_value(value, "locator")


@pytest.mark.parametrize(
    "value",
    ["token_log", "password_reset", "secret_santa", "node N", "host H / database D"],
)
def test_ordinary_names_are_accepted(ho: ModuleType, value: str) -> None:
    assert ho.check_value(value, "object") == value


def test_secret_override_and_newline_rule(ho: ModuleType) -> None:
    assert ho.check_value("token=abc", "note", allow_secret_like=True) == "token=abc"
    with pytest.raises(ho.HandoverError, match="single line"):
        ho.check_value("a\nb", "note", allow_secret_like=True)


def test_row_split_and_join_escape_pipes(ho: ModuleType) -> None:
    cells = ["DataWorks", "ws W / flow F", "node a|b", "dev", "touched", "-", "-"]
    line = ho.join_row(cells)
    assert "a\\|b" in line
    assert ho.split_row(line) == cells


def test_init_creates_the_file_and_refuses_twice(ho, repo) -> None:
    path = ho.cmd_init(repo, T, "fea/PROJ-1234-x")
    text = path.read_text()
    assert "# Handover: PROJ-1234" in text and "- Branch: `fea/PROJ-1234-x`" in text
    assert "| Platform | Locator | Object | Env | State | Plan | Source |" in text
    assert "## Notes" in text
    with pytest.raises(ho.HandoverError, match="already exists"):
        ho.cmd_init(repo, T, "fea/PROJ-1234-x")
    with pytest.raises(ho.HandoverError):
        ho.cmd_init(repo, "../x", "b")


def test_inventory_roundtrip_keeps_unknown_lines_malformed_rows_and_crlf(
    ho: ModuleType,
) -> None:
    text = (
        "# Handover: PROJ-1234\r\n\r\n- Branch: `b`\r\nan unknown line\r\n\r\n"
        "## Objects\r\n\r\n"
        "| Platform | Locator | Object | Env | State | Plan | Source |\r\n"
        "| --- | --- | --- | --- | --- | --- | --- |\r\n"
        "| DataWorks | w / f | node N | dev | touched | - | - |\r\n"
        "| broken | row |\r\n\r\n## Notes\r\n\r\n- a note\r\n"
    )
    inv = ho.Inventory(text)
    assert inv.eol == "\r\n"
    rows, problems = inv.rows()
    assert len(rows) == 1 and rows[0][1][2] == "node N"
    assert len(problems) == 1 and "malformed" in problems[0]
    assert inv.dump() == text


def add(ho, repo, **kw):
    base = {"platform": "DataWorks", "locator": "workspace-w / workflow-f", "obj": "node N",
            "env": "dev", "state": "touched"}  # fmt: skip
    base.update(kw)
    return ho.cmd_add(repo, T, **base)


def table_rows(ho, repo):
    rows, problems = ho.load_inventory(repo, T).rows()
    return [cells for _, cells in rows], problems


@pytest.fixture
def inited(ho: ModuleType, repo: Path) -> Path:
    ho.cmd_init(repo, T, "fea/PROJ-1234-x")
    return repo


def test_add_inserts_a_row_and_upserts_by_normalised_key(ho, inited) -> None:
    assert add(ho, inited) == "added"
    assert (
        add(
            ho,
            inited,
            platform="dataworks",
            locator="workspace-w  /  workflow-f",
            obj="NODE n",
        )
        == "updated"
    )
    rows, _ = table_rows(ho, inited)
    assert len(rows) == 1
    assert rows[0][:5] == [
        "DataWorks",
        "workspace-w / workflow-f",
        "node N",
        "dev",
        "touched",
    ]


def test_same_object_in_another_env_is_another_row(ho, inited) -> None:
    add(ho, inited)
    add(ho, inited, env="prod")
    rows, _ = table_rows(ho, inited)
    assert [r[3] for r in rows] == ["dev", "prod"]


def test_planned_never_downgrades_touched_and_touched_upgrades(ho, inited) -> None:
    add(ho, inited, state="planned")
    assert table_rows(ho, inited)[0][0][4] == "planned"
    add(ho, inited, state="touched")
    assert table_rows(ho, inited)[0][0][4] == "touched"
    add(ho, inited, state="planned")
    assert table_rows(ho, inited)[0][0][4] == "touched"


def test_sources_append_normalised_and_deduplicated(ho, inited) -> None:
    add(ho, inited, source="./scratch//PROJ-1234\\dataworks/N")
    add(ho, inited, source="release/PROJ-1234/ddl/001_x.sql")
    add(ho, inited, source="scratch/PROJ-1234/dataworks/N")
    cell = table_rows(ho, inited)[0][0][6]
    assert ho.split_list(cell) == [
        "scratch/PROJ-1234/dataworks/N",
        "release/PROJ-1234/ddl/001_x.sql",
    ]


@pytest.mark.parametrize("source", ["../outside", "a/../../b", "/etc/passwd"])
def test_sources_outside_the_repository_are_refused(ho, inited, source) -> None:
    with pytest.raises(ho.HandoverError):
        add(ho, inited, source=source)


def test_an_absolute_path_inside_the_repository_becomes_relative(ho, inited) -> None:
    add(ho, inited, source=str(inited / "scratch" / T / "x.sql"))
    assert ho.split_list(table_rows(ho, inited)[0][0][6]) == ["scratch/PROJ-1234/x.sql"]


@pytest.mark.parametrize(
    ("field", "value"),
    [("platform", "Nope"), ("env", "stage"), ("state", "applied"), ("locator", ""), ("obj", ""),
     ("locator", "a\nb"), ("obj", "password=x")],
)  # fmt: skip
def test_add_validates_every_field(ho, inited, field, value) -> None:
    with pytest.raises(ho.HandoverError):
        add(ho, inited, **{field: value})
    assert table_rows(ho, inited)[0] == []


def test_a_name_with_a_pipe_is_escaped_and_survives(ho, inited) -> None:
    add(ho, inited, obj="node a|b")
    assert table_rows(ho, inited)[0][0][2] == "node a|b"


def test_remove_deletes_only_the_matching_row(ho, inited) -> None:
    add(ho, inited)
    add(ho, inited, obj="node M")
    assert (
        ho.cmd_remove(
            inited, T, "DataWorks", "workspace-w / workflow-f", "NODE n", "dev"
        )
        is True
    )
    assert [r[2] for r in table_rows(ho, inited)[0]] == ["node M"]
    assert ho.cmd_remove(inited, T, "DataWorks", "x", "y", "dev") is False


def test_note_appends_in_the_notes_section_with_the_credential_check(
    ho, inited
) -> None:
    ho.cmd_note(inited, T, "ask the data owner first")
    ho.cmd_note(inited, T, "blocked on access")
    text = ho.cmd_show(inited, T)
    assert (
        text.index("## Notes")
        < text.index("- ask the data owner first")
        < text.index("- blocked on access")
    )
    with pytest.raises(ho.HandoverError):
        ho.cmd_note(inited, T, "password=abc")
    with pytest.raises(ho.HandoverError):
        ho.cmd_note(inited, T, "two\nlines")


def test_set_branch_replaces_the_branch_line(ho, inited) -> None:
    ho.cmd_set_branch(inited, T, "fix/PROJ-1234-y")
    assert "- Branch: `fix/PROJ-1234-y`" in ho.cmd_show(inited, T)
    assert ho.cmd_show(inited, T).count("- Branch:") == 1


def test_writes_preserve_unknown_lines_malformed_rows_notes_and_crlf(
    ho, inited
) -> None:
    path = ho.inventory_path(inited, T)
    original = (
        "# Handover: PROJ-1234\r\n\r\n- Branch: `b`\r\nan unknown line\r\n\r\n## Objects\r\n\r\n"
        + ho.HEADER_LINE + "\r\n" + ho.SEPARATOR_LINE + "\r\n"
        "| broken | row |\r\n\r\n## Notes\r\n\r\n- keep me\r\n"
    )  # fmt: skip
    path.write_bytes(original.encode())
    add(ho, inited)
    ho.cmd_note(inited, T, "another")
    ho.cmd_set_branch(inited, T, "c")
    text = path.read_bytes().decode()
    assert text.count("\r\n") == text.count("\n")  # still CRLF everywhere
    for kept in (
        "an unknown line",
        "| broken | row |",
        "- keep me",
        "- another",
        "- Branch: `c`",
    ):
        assert kept in text
    assert "node N" in text
    rows, problems = ho.load_inventory(inited, T).rows()
    assert len(rows) == 1 and len(problems) == 1


def test_missing_file_is_a_clear_error(ho, repo) -> None:
    with pytest.raises(ho.HandoverError, match="run init"):
        ho.load_inventory(repo, T)


def obj(
    name="node N", platform="DataWorks", locator="workspace-w / workflow-f", env="dev"
):
    return {"platform": platform, "locator": locator, "object": name, "env": env}


PLAN = "release/PROJ-1234/docs/plan.md"


def sync(ho, repo, objects, source=PLAN, **kw):
    return ho.cmd_plan_sync(repo, T, source, objects, **kw)


def states(ho, repo):
    return {r[2]: (r[4], ho.split_list(r[5])) for r in table_rows(ho, repo)[0]}


def test_a_draft_plan_adds_planned_rows_with_the_plan_source(ho, inited) -> None:
    result = sync(
        ho,
        inited,
        [obj("node N"), obj("table T", "Hologres", "host-h / db / schema-s")],
    )
    assert result == {"added": 2, "kept": 0, "removed": 0}
    assert states(ho, inited) == {
        "node N": ("planned", [PLAN]),
        "table T": ("planned", [PLAN]),
    }


def test_a_revised_plan_removes_planned_rows_it_no_longer_names(ho, inited) -> None:
    sync(ho, inited, [obj("node N"), obj("node M")])
    result = sync(ho, inited, [obj("node N")])
    assert result == {"added": 0, "kept": 1, "removed": 1}
    assert list(states(ho, inited)) == ["node N"]


def test_a_row_named_by_another_plan_source_stays(ho, inited) -> None:
    sync(ho, inited, [obj("node N")], source="release/PROJ-1234/docs/plan.md")
    sync(ho, inited, [obj("node N")], source="release/PROJ-1234/docs/spec.md")
    sync(ho, inited, [], source="release/PROJ-1234/docs/plan.md", allow_empty=True)
    assert states(ho, inited) == {
        "node N": ("planned", ["release/PROJ-1234/docs/spec.md"])
    }


def test_a_touched_row_is_never_removed_by_plan_sync(ho, inited) -> None:
    sync(ho, inited, [obj("node N")])
    add(ho, inited, state="touched")
    sync(ho, inited, [obj("node M")])
    result = states(ho, inited)
    assert result["node N"][0] == "touched" and result["node N"][1] == []
    assert result["node M"][0] == "planned"


def test_an_existing_touched_row_gets_the_plan_source(ho, inited) -> None:
    add(ho, inited, state="touched")
    sync(ho, inited, [obj("node N")])
    assert states(ho, inited)["node N"] == ("touched", [PLAN])


def test_an_empty_list_is_refused_without_allow_empty(ho, inited) -> None:
    sync(ho, inited, [obj("node N")])
    with pytest.raises(ho.HandoverError, match="empty"):
        sync(ho, inited, [])
    assert list(states(ho, inited)) == ["node N"]
    sync(ho, inited, [], allow_empty=True)
    assert states(ho, inited) == {}


@pytest.mark.parametrize(
    "bad",
    [
        [obj("node N"), obj("NODE n")],  # duplicate key
        [obj("node N", platform="Nope")],
        [obj("node N", env="stage")],
        [obj("node N", locator="password=x")],
        [{"platform": "DataWorks", "locator": "w"}],  # missing fields
        ["not a dict"],
    ],
)
def test_invalid_input_changes_nothing(ho, inited, bad) -> None:
    sync(ho, inited, [obj("node M")])
    before = ho.inventory_path(inited, T).read_bytes()
    with pytest.raises(ho.HandoverError):
        sync(ho, inited, bad)
    assert ho.inventory_path(inited, T).read_bytes() == before


def test_the_objects_file_loader(ho, tmp_path) -> None:
    good = tmp_path / "o.json"
    good.write_text(json.dumps([obj()]))
    assert ho.load_objects_file(good) == [obj()]
    bad = tmp_path / "b.json"
    bad.write_text("{not json")
    with pytest.raises(ho.HandoverError):
        ho.load_objects_file(bad)
    notlist = tmp_path / "n.json"
    notlist.write_text('{"a": 1}')
    with pytest.raises(ho.HandoverError):
        ho.load_objects_file(notlist)
    with pytest.raises(ho.HandoverError):
        ho.load_objects_file(tmp_path / "missing.json")


def test_plan_sync_keeps_malformed_rows_and_notes(ho, inited) -> None:
    path = ho.inventory_path(inited, T)
    text = path.read_text().replace("## Notes", "| broken | row |\n\n## Notes")
    path.write_text(text + "- a note\n")
    sync(ho, inited, [obj("node N")])
    after = path.read_text()
    assert "| broken | row |" in after and "- a note" in after and "node N" in after


def state(ho, repo):
    return ho.load_state(repo, T)


def render(ho, repo, status="Data Development", date="2026-10-16"):
    return ho.render(repo, T, status, date)


def footer(text: str) -> str:
    return [ln for ln in text.splitlines() if ln.startswith("Fingerprint:")][0].split(
        ": "
    )[1]


@pytest.fixture
def two(ho: ModuleType, inited: Path) -> Path:
    add(ho, inited)
    add(
        ho,
        inited,
        platform="Hologres",
        locator="host-h / db / schema-s",
        obj="table T",
        state="planned",
    )
    return inited


def test_render_has_marker_status_groups_links_notes_and_footer(ho, two) -> None:
    ho.cmd_note(two, T, "ask the data owner")
    ho.cmd_set_links(
        two, T, pr="https://example.test/pr/1", bast="https://example.test/bast"
    )
    text = render(ho, two)
    lines = text.splitlines()
    assert lines[0] == "Handover inventory for PROJ-1234 (edited in place)"
    assert "Updated: 2026-10-16" in lines
    assert "Status: Data Development | planned: 1 | touched: 1" in lines
    assert lines.index("DataWorks") < lines.index("Hologres")
    assert "- node N | workspace-w / workflow-f | dev | touched" in lines
    for want in (
        "Branch: fea/PROJ-1234-x",
        "PR: https://example.test/pr/1",
        "BAST: https://example.test/bast",
        "- ask the data owner",
        "Details: release/PROJ-1234/docs/HANDOVER.md",
    ):
        assert want in text
    assert len(footer(text)) == 12


def test_render_is_compact_above_25_objects(ho, inited) -> None:
    for n in range(26):
        add(ho, inited, obj=f"node {n:02d}")
    text = render(ho, inited)
    assert "Objects: 26 (compact)" in text and "- DataWorks: 26" in text
    assert "- node 00 |" not in text


def test_fingerprint_follows_the_published_fields_only(ho, two) -> None:
    base = footer(render(ho, two))
    assert (
        footer(render(ho, two, status="Testing", date="2030-01-01")) == base
    )  # status and date excluded
    add(ho, two, source="scratch/PROJ-1234/x.sql")  # Source is not published
    assert footer(render(ho, two)) == base
    sync(ho, two, [obj("node N")])  # Plan is not published
    assert footer(render(ho, two)) == base
    add(
        ho,
        two,
        platform="Hologres",
        locator="host-h / db / schema-s",
        obj="table T",
        state="touched",
    )
    assert footer(render(ho, two)) != base  # a state change is published


@pytest.mark.parametrize("change", ["note", "pr", "bast", "branch", "row"])
def test_each_published_field_changes_the_fingerprint(ho, two, change) -> None:
    base = footer(render(ho, two))
    if change == "note":
        ho.cmd_note(two, T, "n")
    elif change == "pr":
        ho.cmd_set_links(two, T, pr="https://example.test/p")
    elif change == "bast":
        ho.cmd_set_links(two, T, bast="https://example.test/b")
    elif change == "branch":
        ho.cmd_set_branch(two, T, "other")
    else:
        add(ho, two, obj="node Z")
    assert footer(render(ho, two)) != base


def test_row_order_does_not_change_the_fingerprint(ho, inited) -> None:
    add(ho, inited, obj="node A")
    add(ho, inited, obj="node B")
    first = footer(render(ho, inited))
    other = repo_copy = inited  # same repo; rebuild in reverse order
    path = ho.inventory_path(other, T)
    inv = ho.Inventory(path.read_text())
    rows, _ = inv.rows()
    a, b = rows[0][0], rows[1][0]
    inv.lines[a], inv.lines[b] = inv.lines[b], inv.lines[a]
    path.write_text(inv.dump())
    assert footer(render(ho, repo_copy)) == first


def test_changed_before_any_post(ho, two) -> None:
    assert ho.cmd_changed(two, T) == "no-state"
    ho.cmd_set_links(two, T)  # creates the state file
    assert ho.cmd_changed(two, T) == "changed"


def test_changed_for_an_empty_inventory_is_quiet(ho, inited) -> None:
    ho.cmd_set_links(inited, T)
    assert ho.cmd_changed(inited, T) == ""


def post(ho, repo, comment_id="10123", date="2026-10-16"):
    ho.cmd_begin_post(repo, T)
    ho.cmd_mark_posted(repo, T, comment_id, date)


def test_the_posting_cycle_and_change_detection(ho, two) -> None:
    ho.cmd_set_links(two, T)
    post(ho, two)
    s = state(ho, two)
    assert (
        s["comment_id"] == "10123"
        and s["posting"] == {"state": "idle"}
        and s["posted_date"] == "2026-10-16"
    )
    assert ho.cmd_changed(two, T) == ""
    add(ho, two, obj="node Z")
    assert ho.cmd_changed(two, T) == "changed"


def test_pending_wins_over_closed_and_changed(ho, two) -> None:
    ho.cmd_set_links(two, T)
    ho.cmd_begin_post(two, T)
    assert ho.cmd_changed(two, T) == "pending"
    s = state(ho, two)
    s["closed"] = True
    ho.save_state(two, T, s)
    assert ho.cmd_changed(two, T) == "pending"


def test_begin_post_refuses_while_pending_and_abort_clears_only_the_pending_state(
    ho, two
) -> None:
    ho.cmd_set_links(two, T, pr="https://example.test/p")
    ho.cmd_begin_post(two, T)
    with pytest.raises(ho.HandoverError, match="pending"):
        ho.cmd_begin_post(two, T)
    ho.cmd_abort_post(two, T)
    s = state(ho, two)
    assert s["posting"] == {"state": "idle"} and s["pr"] == "https://example.test/p"


def test_mark_posted_records_the_approved_fingerprint_not_a_recomputed_one(
    ho, two
) -> None:
    ho.cmd_set_links(two, T)
    ho.cmd_begin_post(two, T)
    approved = state(ho, two)["posting"]["approved"]
    add(ho, two, obj="node B")  # the inventory changes after the approval
    ho.cmd_mark_posted(two, T, "10123", "2026-10-16")
    assert state(ho, two)["posted_fingerprint"] == approved
    assert ho.cmd_changed(two, T) == "changed"  # version B is not recorded as posted


def test_mark_posted_refuses_when_nothing_is_pending(ho, two) -> None:
    ho.cmd_set_links(two, T)
    with pytest.raises(ho.HandoverError, match="no post is pending"):
        ho.cmd_mark_posted(two, T, "1")


def test_adopt_rebuilds_a_missing_state_from_a_comment_footer(ho, two) -> None:
    text = render(ho, two)
    ho.cmd_adopt(two, T, "777", footer(text))
    s = state(ho, two)
    assert s["comment_id"] == "777"
    assert ho.cmd_changed(two, T) == ""  # prefix comparison
    add(ho, two, obj="node Z")
    assert ho.cmd_changed(two, T) == "changed"


def test_close_preconditions(ho, two) -> None:
    ho.cmd_set_links(two, T)
    with pytest.raises(ho.HandoverError, match="unpublished"):
        ho.cmd_close(two, T)  # never posted, inventory not empty
    post(ho, two)
    ho.cmd_begin_post(two, T)
    with pytest.raises(ho.HandoverError, match="pending"):
        ho.cmd_close(two, T)
    ho.cmd_abort_post(two, T)
    ho.cmd_close(two, T)
    assert state(ho, two)["closed"] is True and ho.cmd_changed(two, T) == "closed"


def test_close_is_refused_while_changes_are_unpublished_and_ok_for_an_empty_inventory(
    ho, two, inited
) -> None:
    ho.cmd_set_links(two, T)
    post(ho, two)
    add(ho, two, obj="node Z")
    with pytest.raises(ho.HandoverError, match="unpublished"):
        ho.cmd_close(two, T)


def test_close_accepts_an_empty_inventory_that_was_never_posted(ho, repo) -> None:
    ho.cmd_init(repo, T, "b")
    ho.cmd_close(repo, T)
    assert state(ho, repo)["closed"] is True


def test_reopen_and_the_automatic_reopen_when_jira_leaves_done(ho, two) -> None:
    ho.cmd_set_links(two, T)
    post(ho, two)
    ho.cmd_close(two, T)
    assert ho.cmd_changed(two, T, "Done") == "closed"
    add(ho, two, obj="node Z")
    assert (
        ho.cmd_changed(two, T, "Data Development") == "changed"
    )  # reopened, then evaluated
    assert state(ho, two)["closed"] is False
    ho.cmd_reopen(two, T)
    assert state(ho, two)["closed"] is False


def test_the_state_file_is_local_only(ho, two) -> None:
    ho.cmd_set_links(two, T, pr="https://example.test/p")
    post(ho, two)
    ignored = subprocess.run(
        ["git", "-C", str(two), "status", "--porcelain"], capture_output=True, text=True
    ).stdout
    assert (
        "scratch" in ignored
    )  # untracked here: the kickoff skill is what ignores scratch/
    (two / ".gitignore").write_text("scratch/\n")
    clean = subprocess.run(
        ["git", "-C", str(two), "status", "--porcelain", "--", "scratch"],
        capture_output=True,
        text=True,
    ).stdout
    assert clean == ""


def touch(repo: Path, rel: str) -> None:
    p = repo / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("x")


def test_check_lists_files_with_no_source_and_names_the_scanned_directories(
    ho, inited
) -> None:
    touch(inited, "release/PROJ-1234/ddl/001_a.sql")
    touch(inited, "release/PROJ-1234/ddl/002_b.sql")
    touch(inited, "scratch/PROJ-1234/dataworks/N/node.json")
    touch(inited, "scratch/PROJ-1234/CONTEXT.md")
    touch(inited, "scratch/PROJ-1234/docs/sample.csv")
    touch(inited, "release/PROJ-1234/docs/plan.md")
    add(ho, inited, source="release/PROJ-1234/ddl/001_a.sql")
    add(
        ho, inited, obj="node M", source="scratch/PROJ-1234/dataworks/N"
    )  # a directory source
    scanned, unmatched = ho.cmd_check(inited, T)
    assert scanned == ["release/PROJ-1234/ddl", "scratch/PROJ-1234"]
    assert unmatched == ["release/PROJ-1234/ddl/002_b.sql"]


def test_check_with_no_folders_scans_nothing(ho, inited) -> None:
    assert ho.cmd_check(inited, T) == ([], [])


def run_cli(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SRC), *args], capture_output=True, text=True, cwd=cwd
    )


def test_the_cli_end_to_end_from_the_umbrella_folder(ho, repo, tmp_path) -> None:
    base = ["--repo", str(repo)]
    assert (
        run_cli("init", "--ticket", T, "--branch", "b", *base, cwd=tmp_path).returncode
        == 0
    )
    r = run_cli("add", "--ticket", T, "--platform", "dataworks", "--locator", "w / f", "--object",
                "node N", "--env", "dev", "--state", "touched", *base, cwd=tmp_path)  # fmt: skip
    assert r.returncode == 0 and "added" in r.stdout
    objs = tmp_path / "o.json"
    objs.write_text(json.dumps([obj("node P")]))
    r = run_cli(
        "plan-sync",
        "--ticket",
        T,
        "--source",
        PLAN,
        "--objects-file",
        str(objs),
        *base,
        cwd=tmp_path,
    )
    assert r.returncode == 0 and "added 1" in r.stdout
    assert (
        run_cli(
            "note", "--ticket", T, "--text", "ask the owner", *base, cwd=tmp_path
        ).returncode
        == 0
    )
    r = run_cli(
        "render",
        "--ticket",
        T,
        "--jira-status",
        "Testing",
        "--date",
        "2026-10-16",
        *base,
        cwd=tmp_path,
    )
    assert r.returncode == 0 and "Status: Testing | planned: 1 | touched: 1" in r.stdout
    assert (
        run_cli("changed", "--ticket", T, *base, cwd=tmp_path).stdout.strip()
        == "no-state"
    )
    assert (
        run_cli(
            "set", "--ticket", T, "--pr", "https://example.test/p", *base, cwd=tmp_path
        ).returncode
        == 0
    )
    assert run_cli("begin-post", "--ticket", T, *base, cwd=tmp_path).returncode == 0
    assert (
        run_cli("changed", "--ticket", T, *base, cwd=tmp_path).stdout.strip()
        == "pending"
    )
    assert (
        run_cli(
            "mark-posted", "--ticket", T, "--comment-id", "9", *base, cwd=tmp_path
        ).returncode
        == 0
    )
    assert run_cli("changed", "--ticket", T, *base, cwd=tmp_path).stdout.strip() == ""
    assert run_cli("close", "--ticket", T, *base, cwd=tmp_path).returncode == 0
    assert (
        run_cli("changed", "--ticket", T, *base, cwd=tmp_path).stdout.strip()
        == "closed"
    )
    assert run_cli("show", "--ticket", T, *base, cwd=tmp_path).stdout.startswith(
        "# Handover: PROJ-1234"
    )


def test_the_cli_reports_errors_without_a_traceback(ho, repo, tmp_path) -> None:
    r = run_cli("show", "--ticket", T, "--repo", str(repo), cwd=tmp_path)
    assert r.returncode != 0 and "run init" in r.stderr and "Traceback" not in r.stderr
    r = run_cli("show", "--ticket", "../x", "--repo", str(repo), cwd=tmp_path)
    assert r.returncode != 0 and "invalid ticket" in r.stderr
    r = run_cli(
        "show", "--ticket", T, cwd=tmp_path
    )  # the umbrella folder is not a repository
    assert r.returncode != 0 and "not inside a git repository" in r.stderr


def test_the_cli_check_and_remove_report_their_result(ho, repo, tmp_path) -> None:
    base = ["--repo", str(repo)]
    run_cli("init", "--ticket", T, "--branch", "b", *base, cwd=tmp_path)
    touch(repo, "release/PROJ-1234/ddl/001_a.sql")
    r = run_cli("check", "--ticket", T, *base, cwd=tmp_path)
    assert "release/PROJ-1234/ddl" in r.stdout and "001_a.sql" in r.stdout
    r = run_cli("remove", "--ticket", T, "--platform", "Hive", "--locator", "x", "--object", "y",
                "--env", "dev", *base, cwd=tmp_path)  # fmt: skip
    assert r.returncode == 1 and "no such row" in r.stdout


def text(name: str) -> str:
    return (ROOT / name).read_text(encoding="utf-8")


def test_skill_describes_recording_posting_and_recovery() -> None:
    body = text("CLAUDE/skills/handover/SKILL.md")
    for needle in ("handover.py init", "plan-sync", "begin-post", "mark-posted", "abort-post",
                   "Handover inventory for", "Fingerprint:", "listJiraIssueComments",
                   "addOrEditJiraIssueComment", "after the user's OK", "silent", "adopt", "reopen"):  # fmt: skip
        assert needle in body, needle


def test_handover_command_exists() -> None:
    body = text("CLAUDE/commands/handover.md")
    assert (
        body.startswith("---\ndescription:")
        and "handover.py" in body
        and "touched outside this session" in body
    )


def test_integrations_are_present() -> None:
    assert "handover.py init" in text("CLAUDE/skills/jira-ticket-kickoff/SKILL.md")
    assert "HANDOVER.md" in text("CLAUDE/skills/jira-ticket-kickoff/SKILL.md")
    commit = text("CLAUDE/commands/commit.md")
    assert (
        "handover" in commit
        and "Bash(python3:*)" in commit
        and "after the commit" in commit
    )
    pr = text("CLAUDE/commands/generate-pr-message.md")
    assert "handover" in pr and "both PRs" in pr
    assert "handover set --bast" in text(
        "CLAUDE/skills/bast-generator/SKILL.md"
    ) or "handover.py set --bast" in text("CLAUDE/skills/bast-generator/SKILL.md")
    assert "## Ticket Handover" in text("CLAUDE/CLAUDE.md")
    assert "/handover" in text("CLAUDE/CLAUDE.md") and "/handover" in text(
        "CLAUDE/README.md"
    )


def test_no_old_status_words_in_the_new_text() -> None:
    old = [
        "`In progress`",
        "`PR to dev`",
        "`Merged to dev`",
        "`Released`",
        "Ready to Release",
    ]
    for name in ("CLAUDE/skills/handover/SKILL.md", "CLAUDE/commands/handover.md"):
        assert [w for w in old if w in text(name)] == []
