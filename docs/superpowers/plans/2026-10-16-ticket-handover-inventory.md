# Ticket Handover Inventory Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `handover` skill with a stdlib helper that keeps a per-ticket inventory of the platforms and objects a ticket touches, plus a `/handover` command and small hooks in the kickoff, `/commit`, `/generate-pr-message` and `bast-generator` flows, so a replacement PIC can see where the work lives.

**Architecture:** One Python 3.9-compatible helper `CLAUDE/skills/handover/handover.py` owns two files: the committed inventory `release/<TICKET>/docs/HANDOVER.md` (objects and notes) and a git-ignored local state file `scratch/<TICKET>/handover.state.json` (posting bookkeeping). The helper is pure and local: it never talks to Jira. The model reads Jira and posts one marker comment through the Atlassian tools after the user's OK, using a two-phase begin-post / mark-posted flow that can be recovered by comparing the comment's fingerprint footer.

**Tech Stack:** Python 3.9+ stdlib, pytest (3.11 project, 3.9 and 3.12 via `uv run --no-project --python X`), ruff, mypy, Markdown.

**Spec:** `docs/superpowers/specs/2026-10-16-ticket-handover-inventory-design.md`

## Global Constraints

- Helper runs on system `python3` 3.9 and on 3.10+: `from __future__ import annotations`, no `match`, no `zip(strict=...)`, no `X | None` outside annotations, no `dict | dict`.
- Nothing is committed, pushed or opened as a PR unless the user asks. A "Checkpoint" step means: show `git status` and the diff summary, and commit only when the user says so.
- Commits: Conventional Commits + gitmoji ending with `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`. PR bodies end with `🤖 Generated with [Claude Code](https://claude.com/claude-code)`.
- The repo is public: no company names, hosts, ticket titles or real Jira keys in repo files or tests. Use synthetic data (`PROJ-1234`, `host-h`, `workspace-w`).
- Markdown: code fences carry a language, table separators are `| --- |`, object names in backticks. `ruff format --check .` also formats Python blocks in Markdown, so run `uv run ruff format docs` after writing any doc with Python blocks.
- The helper writes only the two ticket files and never touches any platform. Every write is atomic (temporary file, then `os.replace`) and preserves unknown lines, malformed table rows, the `Notes` section and line endings.
- `<TICKET>` is a Jira key or a slug (letters, digits, dot, underscore, hyphen; no `..`, no slash, not empty), validated before any path is built.
- Posting to Jira is proposed first and written only after the user's OK; recording to the local files is silent.
- Inventory columns, in order: `Platform | Locator | Object | Env | State | Plan | Source`. Platforms: `DataWorks`, `Hologres`, `Hive`, `MaxCompute`, `Postgres`, `MySQL`, `Trino`, `Flink`, `OSS`, `Airflow`, `Kafka`, `Other`. Envs: `dev`, `sit`, `uat`, `prod`. States: `planned`, `touched`.
- Row key: `(platform, locator, object, env)`, compared case-insensitively with whitespace collapsed. `Plan` and `Source` are `; `-separated lists of repository-relative paths (stored in backticks, `-` when empty). A `|` in a cell is written `\|`; a newline is rejected.
- Secret check: refuse assignments such as `password=x`, `token: abc`, `api_key=x`, `secret=x`, `access_key=x`, and URLs with `user:pass@`; a bare word such as `token_log` is accepted; `--allow-secret-like` overrides.
- The Jira comment starts with the marker line `Handover inventory for <TICKET> (edited in place)` and ends with `Fingerprint: <first 12 hex>`. The fingerprint is SHA-256 of the rendered body without the `Updated:` line, the `Status:` line and the footer.

## Review Focus

Failure modes the spec implies that no single task's happy path exercises:

1. A crash after the Jira write but before `mark-posted` must never produce a second comment or publish text the user did not approve (Task 4 tests and the recovery text in Task 6).
2. A file with malformed rows, unknown lines and CRLF must survive every write command unchanged apart from the intended edit (Tasks 1 to 4).
3. `plan-sync` must never delete a `touched` row, and an empty or invalid objects file must change nothing (Task 3).
4. A closed ticket that returns to development must reopen, and `close` must refuse while a post is pending or changes are unpublished (Task 4).
5. The helper must work when the session starts in an umbrella folder above the repository (`--repo`) and must refuse outside a repository (Task 1).

---

## File Structure

| File | Responsibility |
| --- | --- |
| `CLAUDE/skills/handover/handover.py` | The helper: validation, inventory file, state file, `plan-sync`, `render`, fingerprint, posting state machine, `check`, CLI |
| `CLAUDE/skills/handover/SKILL.md` | When to record, when to propose a post, the posting and recovery procedure for the model |
| `CLAUDE/commands/handover.md` | The `/handover` slash command |
| `tests/test_handover.py` | All helper tests (loads the helper by path, like `tests/test_logbook.py`) |
| `CLAUDE/skills/jira-ticket-kickoff/SKILL.md` | Run `init` at kickoff; resume path reads the inventory first |
| `CLAUDE/commands/commit.md`, `CLAUDE/commands/generate-pr-message.md` | The check-and-prompt step |
| `CLAUDE/skills/bast-generator/SKILL.md` | Scope cross-check and `set --bast` |
| `CLAUDE/CLAUDE.md` | A "Ticket Handover" rule section (template; the live file gets the same text at deployment) |
| `docs/guidelines/DEV-WORKFLOW.md`, `README.md`, `CLAUDE/README.md` | Status note, command rows |

---

### Task 1: Foundations: validation, repository, inventory file, secret check, `init`

**Files:**
- Create: `CLAUDE/skills/handover/handover.py`
- Create: `tests/test_handover.py`

**Interfaces:**
- Produces:
  - `class HandoverError(Exception)`
  - `PLATFORMS`, `ENVS`, `STATES`, `COLUMNS`
  - `validate_ticket(ticket: str) -> str`
  - `find_repo(repo: str | None = None) -> Path`
  - `inventory_path(repo: Path, ticket: str) -> Path`, `state_path(repo: Path, ticket: str) -> Path`
  - `check_value(value: str, field: str, allow_secret_like: bool = False) -> str`
  - `write_atomic(path: Path, text: str) -> None`
  - `split_row(line: str) -> list[str]`, `join_row(cells: list[str]) -> str`
  - `class Inventory(text: str)` with `.eol`, `.lines`, `.dump()`, `.table_span()`, `.rows() -> tuple[list[tuple[int, list[str]]], list[str]]`
  - `cmd_init(repo: Path, ticket: str, branch: str) -> Path`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_handover.py`:

```python
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
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/test_handover.py -q`
Expected: FAIL (the helper file does not exist: collection error on `SRC`).

- [ ] **Step 3: Implement**

Create `CLAUDE/skills/handover/handover.py`:

```python
#!/usr/bin/env python3
"""Ticket handover inventory: where a ticket's work lives, for whoever takes over.

Two files per ticket, both under the repository:
  release/<TICKET>/docs/HANDOVER.md        committed: branch, object table, notes
  scratch/<TICKET>/handover.state.json     ignored: posting bookkeeping and links

The helper is local and never talks to Jira or to any platform. The model posts the Jira
comment with the Atlassian tools after the user's OK (see the skill text).
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

PLATFORMS = [
    "DataWorks", "Hologres", "Hive", "MaxCompute", "Postgres", "MySQL", "Trino",
    "Flink", "OSS", "Airflow", "Kafka", "Other",
]  # fmt: skip
ENVS = ["dev", "sit", "uat", "prod"]
STATES = ["planned", "touched"]
COLUMNS = ["Platform", "Locator", "Object", "Env", "State", "Plan", "Source"]
TICKET_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")
SECRET_RE = re.compile(
    r"(?i)\b(?:password|passwd|pwd|token|secret|api[_-]?key|access[_-]?key)\b\s*[=:]\s*\S+"
    r"|://[^/\s:@]+:[^@\s]+@"
)
HEADER_LINE = "| " + " | ".join(COLUMNS) + " |"
SEPARATOR_LINE = "| " + " | ".join("---" for _ in COLUMNS) + " |"
TEMPLATE = (
    "# Handover: {ticket}\n\n- Branch: `{branch}`\n\n## Objects\n\n"
    + HEADER_LINE
    + "\n"
    + SEPARATOR_LINE
    + "\n\n## Notes\n\n"
)


class HandoverError(Exception):
    """A user-facing error: bad input, a refused transition, a missing file."""


def validate_ticket(ticket: str) -> str:
    if not TICKET_RE.fullmatch(ticket) or ".." in ticket:
        raise HandoverError(
            f"invalid ticket id {ticket!r}: use letters, digits, dot, underscore and hyphen"
        )
    return ticket


def find_repo(repo: str | None = None) -> Path:
    """The repository top level for --repo, or for the current directory."""
    start = Path(repo).expanduser() if repo else Path.cwd()
    try:
        done = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=start, capture_output=True, text=True, timeout=30,
        )  # fmt: skip
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise HandoverError(f"cannot run git in {start}: {exc}") from exc
    if done.returncode != 0:
        raise HandoverError(f"{start} is not inside a git repository")
    return Path(done.stdout.strip())


def inventory_path(repo: Path, ticket: str) -> Path:
    return repo / "release" / validate_ticket(ticket) / "docs" / "HANDOVER.md"


def state_path(repo: Path, ticket: str) -> Path:
    return repo / "scratch" / validate_ticket(ticket) / "handover.state.json"


def check_value(value: str, field: str, allow_secret_like: bool = False) -> str:
    """A single-line value that does not look like a credential."""
    if "\n" in value or "\r" in value:
        raise HandoverError(f"{field} must be a single line")
    if not allow_secret_like and SECRET_RE.search(value):
        raise HandoverError(
            f"{field} looks like a credential; remove it or pass --allow-secret-like"
        )
    return value.strip()


def write_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(text.encode("utf-8"))
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def split_row(line: str) -> list[str]:
    text = line.strip()
    if text.startswith("|"):
        text = text[1:]
    if text.endswith("|") and not text.endswith("\\|"):
        text = text[:-1]
    return [cell.replace("\\|", "|").strip() for cell in re.split(r"(?<!\\)\|", text)]


def join_row(cells: list[str]) -> str:
    return "| " + " | ".join(cell.replace("|", "\\|") for cell in cells) + " |"


class Inventory:
    """The text of HANDOVER.md as a list of lines; edits touch only the lines they own."""

    def __init__(self, text: str) -> None:
        self.eol = "\r\n" if "\r\n" in text else "\n"
        self.lines = text.replace("\r\n", "\n").split("\n")

    def dump(self) -> str:
        return self.eol.join(self.lines)

    def heading(self, name: str) -> int | None:
        for i, line in enumerate(self.lines):
            if line.strip().lower() == f"## {name}".lower():
                return i
        return None

    def table_span(self) -> tuple[int, int] | None:
        """(index of the first data row, index after the last table line)."""
        start = self.heading("Objects")
        if start is None:
            return None
        i = start + 1
        while i < len(self.lines) and not self.lines[i].lstrip().startswith("|"):
            if self.lines[i].startswith("## "):
                return None
            i += 1
        if i + 1 >= len(self.lines) or not self.lines[i + 1].lstrip().startswith(
            "| ---"
        ):
            return None
        first = i + 2
        end = first
        while end < len(self.lines) and self.lines[end].lstrip().startswith("|"):
            end += 1
        return first, end

    def rows(self) -> tuple[list[tuple[int, list[str]]], list[str]]:
        """Valid rows as (line index, cells) and a problem per malformed row."""
        span = self.table_span()
        if span is None:
            raise HandoverError(
                "no Objects table in the handover file; run init or fix the file"
            )
        rows: list[tuple[int, list[str]]] = []
        problems: list[str] = []
        for idx in range(span[0], span[1]):
            cells = split_row(self.lines[idx])
            if len(cells) == len(COLUMNS):
                rows.append((idx, cells))
            else:
                problems.append(
                    f"line {idx + 1}: malformed table row ({len(cells)} cells)"
                )
        return rows, problems


def cmd_init(repo: Path, ticket: str, branch: str) -> Path:
    path = inventory_path(repo, ticket)
    if path.exists():
        raise HandoverError(f"{path} already exists")
    branch = check_value(branch, "branch", allow_secret_like=True)
    write_atomic(path, TEMPLATE.format(ticket=ticket, branch=branch))
    return path
```

- [ ] **Step 4: Run to verify they pass**

Run: `uv run pytest tests/test_handover.py -q`
Expected: PASS.

- [ ] **Step 5: Checkpoint**

`uv run ruff format -q . && uv run ruff check . && uv run mypy . && uv run pytest -q`. Show `git status`; commit only on request (`✨ feat(claude): add the handover helper foundations`).

---

### Task 2: Rows: `add`, `remove`, `note`, `set --branch`, `show`

**Files:**
- Modify: `CLAUDE/skills/handover/handover.py`
- Test: `tests/test_handover.py`

**Interfaces:**
- Consumes: Task 1.
- Produces: `load_inventory(repo, ticket) -> Inventory`, `save_inventory(repo, ticket, inv) -> None`, `norm(text) -> str`, `row_key(cells) -> tuple[str, str, str, str]`, `split_list(cell) -> list[str]`, `join_list(items) -> str`, `normalise_path(repo, value) -> str`, `canon_platform(value) -> str`, `canon_env(value) -> str`, `cmd_add(repo, ticket, platform, locator, obj, env, state, source=None, allow_secret_like=False) -> str` (returns `added`, `updated`), `cmd_remove(repo, ticket, platform, locator, obj, env) -> bool`, `cmd_note(repo, ticket, text, allow_secret_like=False) -> None`, `cmd_set_branch(repo, ticket, branch) -> None`, `cmd_show(repo, ticket) -> str`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_handover.py`:

```python
def add(ho, repo, **kw):
    base = {"platform": "DataWorks", "locator": "workspace-w / workflow-f", "obj": "node N",
            "env": "dev", "state": "touched"}  # fmt: skip
    base.update(kw)
    return ho.cmd_add(repo, T, **base)


def table_rows(ho, repo):
    rows, problems = ho.load_inventory(repo, T).rows()
    return [cells for _, cells in rows], problems


@pytest.fixture
def inited(ho, repo) -> Path:
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
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/test_handover.py -q -k "add or remove or note or branch or sources or preserve or pipe or missing_file or upgrades or env"`
Expected: FAIL (functions missing).

- [ ] **Step 3: Implement**

Append to `handover.py`:

```python
def norm(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def row_key(cells: list[str]) -> tuple[str, str, str, str]:
    return (
        cells[0].lower(),
        norm(cells[1]).lower(),
        norm(cells[2]).lower(),
        cells[3].lower(),
    )


def split_list(cell: str) -> list[str]:
    parts = [p.strip().strip("`").strip() for p in cell.split(";")]
    return [p for p in parts if p and p != "-"]


def join_list(items: list[str]) -> str:
    return "; ".join(f"`{i}`" for i in items) if items else "-"


def normalise_path(repo: Path, value: str) -> str:
    """A repository-relative path with forward slashes; refuses anything outside the repo."""
    text = value.strip().replace("\\", "/")
    if not text:
        raise HandoverError("empty path")
    if Path(text).is_absolute():
        try:
            text = Path(text).resolve().relative_to(repo.resolve()).as_posix()
        except ValueError:
            raise HandoverError(f"path {value!r} is outside the repository") from None
    parts: list[str] = []
    for part in text.split("/"):
        if part in ("", "."):
            continue
        if part == "..":
            if not parts:
                raise HandoverError(f"path {value!r} escapes the repository")
            parts.pop()
            continue
        parts.append(part)
    if not parts:
        raise HandoverError(f"path {value!r} is empty after normalising")
    return "/".join(parts)


def canon_platform(value: str) -> str:
    for name in PLATFORMS:
        if name.lower() == value.strip().lower():
            return name
    raise HandoverError(
        f"unknown platform {value!r}; use one of {', '.join(PLATFORMS)}"
    )


def canon_env(value: str) -> str:
    env = value.strip().lower()
    if env not in ENVS:
        raise HandoverError(
            f"unknown environment {value!r}; use one of {', '.join(ENVS)}"
        )
    return env


def load_inventory(repo: Path, ticket: str) -> Inventory:
    path = inventory_path(repo, ticket)
    if not path.exists():
        raise HandoverError(f"no handover file at {path}; run init")
    return Inventory(path.read_bytes().decode("utf-8"))


def save_inventory(repo: Path, ticket: str, inv: Inventory) -> None:
    write_atomic(inventory_path(repo, ticket), inv.dump())


def _clean_cells(
    platform: str, locator: str, obj: str, env: str, allow_secret_like: bool
) -> tuple[str, str, str, str]:
    plat = canon_platform(platform)
    e = canon_env(env)
    loc = norm(check_value(locator, "locator", allow_secret_like))
    name = norm(check_value(obj, "object", allow_secret_like))
    if not loc or not name:
        raise HandoverError("locator and object must not be empty")
    return plat, loc, name, e


def cmd_add(
    repo: Path,
    ticket: str,
    platform: str,
    locator: str,
    obj: str,
    env: str,
    state: str,
    source: str | None = None,
    allow_secret_like: bool = False,
) -> str:
    if state not in STATES:
        raise HandoverError(f"unknown state {state!r}; use planned or touched")
    plat, loc, name, e = _clean_cells(platform, locator, obj, env, allow_secret_like)
    src = normalise_path(repo, check_value(source, "source", True)) if source else None
    inv = load_inventory(repo, ticket)
    rows, _ = inv.rows()
    key = (plat.lower(), loc.lower(), name.lower(), e)
    for idx, cells in rows:
        if row_key(cells) == key:
            if state == "touched":
                cells[4] = "touched"
            if src and src not in split_list(cells[6]):
                cells[6] = join_list([*split_list(cells[6]), src])
            inv.lines[idx] = join_row(cells)
            save_inventory(repo, ticket, inv)
            return "updated"
    span = inv.table_span()
    assert span is not None
    inv.lines.insert(
        span[1],
        join_row([plat, loc, name, e, state, "-", join_list([src] if src else [])]),
    )
    save_inventory(repo, ticket, inv)
    return "added"


def cmd_remove(
    repo: Path, ticket: str, platform: str, locator: str, obj: str, env: str
) -> bool:
    plat, loc, name, e = _clean_cells(platform, locator, obj, env, True)
    inv = load_inventory(repo, ticket)
    rows, _ = inv.rows()
    key = (plat.lower(), loc.lower(), name.lower(), e)
    for idx, cells in rows:
        if row_key(cells) == key:
            del inv.lines[idx]
            save_inventory(repo, ticket, inv)
            return True
    return False


def cmd_note(
    repo: Path, ticket: str, text: str, allow_secret_like: bool = False
) -> None:
    line = check_value(text, "note", allow_secret_like)
    if not line:
        raise HandoverError("empty note")
    inv = load_inventory(repo, ticket)
    start = inv.heading("Notes")
    if start is None:
        inv.lines += ["", "## Notes", ""]
        start = len(inv.lines) - 2
    end = len(inv.lines)
    for i in range(start + 1, len(inv.lines)):
        if inv.lines[i].startswith("## "):
            end = i
            break
    pos = end
    while pos - 1 > start and inv.lines[pos - 1].strip() == "":
        pos -= 1
    if pos == start + 1:
        inv.lines[pos:pos] = ["", f"- {line}"]
    else:
        inv.lines.insert(pos, f"- {line}")
    save_inventory(repo, ticket, inv)


def cmd_set_branch(repo: Path, ticket: str, branch: str) -> None:
    branch = check_value(branch, "branch", True)
    inv = load_inventory(repo, ticket)
    for i, line in enumerate(inv.lines):
        if line.startswith("- Branch:"):
            inv.lines[i] = f"- Branch: `{branch}`"
            break
    else:
        inv.lines[2:2] = [f"- Branch: `{branch}`", ""]
    save_inventory(repo, ticket, inv)


def cmd_show(repo: Path, ticket: str) -> str:
    return load_inventory(repo, ticket).dump()
```

- [ ] **Step 4: Run to verify they pass**

Run: `uv run pytest tests/test_handover.py -q`
Expected: PASS.

- [ ] **Step 5: Checkpoint**

Ruff, mypy, pytest; commit only on request (`✨ feat(claude): add, remove and note rows in the handover inventory`).

---

### Task 3: `plan-sync`

**Files:**
- Modify: `CLAUDE/skills/handover/handover.py`
- Test: `tests/test_handover.py`

**Interfaces:**
- Consumes: Tasks 1 and 2.
- Produces: `load_objects_file(path: Path) -> list[dict[str, str]]`, `cmd_plan_sync(repo, ticket, source, objects, allow_empty=False) -> dict[str, int]` (keys `added`, `kept`, `removed`).

- [ ] **Step 1: Write the failing tests**

```python
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
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/test_handover.py -q -k "plan or objects_file or invalid_input"`
Expected: FAIL.

- [ ] **Step 3: Implement**

```python
def load_objects_file(path: Path) -> list[dict[str, str]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HandoverError(f"cannot read the objects file {path}: {exc}") from exc
    if not isinstance(data, list):
        raise HandoverError("the objects file must be a JSON list of objects")
    return data


def cmd_plan_sync(
    repo: Path,
    ticket: str,
    source: str,
    objects: list[Any],
    allow_empty: bool = False,
) -> dict[str, int]:
    """Reconcile one plan source: add what it names, drop planned rows it no longer names."""
    src = normalise_path(repo, source)
    if not objects and not allow_empty:
        raise HandoverError(
            "the objects list is empty; pass --allow-empty to remove its rows"
        )
    listed: dict[tuple[str, str, str, str], tuple[str, str, str, str]] = {}
    for entry in objects:
        if not isinstance(entry, dict) or not all(
            isinstance(entry.get(k), str)
            for k in ("platform", "locator", "object", "env")
        ):
            raise HandoverError(f"invalid object entry {entry!r}")
        plat, loc, name, env = _clean_cells(
            entry["platform"], entry["locator"], entry["object"], entry["env"], False
        )
        key = (plat.lower(), loc.lower(), name.lower(), env)
        if key in listed:
            raise HandoverError(f"duplicate object in the list: {name} ({loc}, {env})")
        listed[key] = (plat, loc, name, env)
    inv = load_inventory(repo, ticket)
    rows, _ = inv.rows()
    counts = {"added": 0, "kept": 0, "removed": 0}
    deletions: list[int] = []
    seen: set[tuple[str, str, str, str]] = set()
    for idx, cells in rows:
        key = row_key(cells)
        plans = split_list(cells[5])
        if key in listed:
            seen.add(key)
            if src not in plans:
                cells[5] = join_list([*plans, src])
                inv.lines[idx] = join_row(cells)
            counts["kept"] += 1
        elif src in plans:
            plans.remove(src)
            if cells[4] == "planned" and not plans:
                deletions.append(idx)
                counts["removed"] += 1
            else:
                cells[5] = join_list(plans)
                inv.lines[idx] = join_row(cells)
    for idx in sorted(deletions, reverse=True):
        del inv.lines[idx]
    span = inv.table_span()
    assert span is not None
    new_rows = [
        join_row([p, loc, name, env, "planned", join_list([src]), "-"])
        for key, (p, loc, name, env) in listed.items()
        if key not in seen
    ]
    inv.lines[span[1] : span[1]] = new_rows
    counts["added"] = len(new_rows)
    save_inventory(repo, ticket, inv)
    return counts
```

- [ ] **Step 4: Run to verify they pass**

Run: `uv run pytest tests/test_handover.py -q`
Expected: PASS.

- [ ] **Step 5: Checkpoint**

Ruff, mypy, pytest; commit only on request (`✨ feat(claude): synchronise planned objects from plan sources`).

---

### Task 4: State file, `render`, fingerprint, and the posting state machine

**Files:**
- Modify: `CLAUDE/skills/handover/handover.py`
- Test: `tests/test_handover.py`

**Interfaces:**
- Consumes: Tasks 1 to 3.
- Produces: `DEFAULT_STATE`, `load_state(repo, ticket) -> dict | None`, `save_state(repo, ticket, state) -> None`, `Inventory.branch()`, `Inventory.notes()`, `stable_lines(inv, state, ticket) -> list[str]`, `fingerprint(inv, state, ticket) -> str` (full SHA-256), `render(repo, ticket, jira_status, date) -> str`, `fp_equal(a, b) -> bool`, `cmd_changed(repo, ticket, jira_status=None) -> str`, `cmd_begin_post`, `cmd_abort_post`, `cmd_mark_posted(repo, ticket, comment_id, date=None)`, `cmd_adopt(repo, ticket, comment_id, fingerprint)`, `cmd_close`, `cmd_reopen`, `cmd_set_links(repo, ticket, pr=None, bast=None)`.

- [ ] **Step 1: Write the failing tests**

```python
def state(ho, repo):
    return ho.load_state(repo, T)


def render(ho, repo, status="Data Development", date="2026-10-16"):
    return ho.render(repo, T, status, date)


def footer(text: str) -> str:
    return [ln for ln in text.splitlines() if ln.startswith("Fingerprint:")][0].split(
        ": "
    )[1]


@pytest.fixture
def two(ho, inited) -> Path:
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
    ho.cmd_close  # still callable
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
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/test_handover.py -q -k "render or fingerprint or posting or changed or pending or mark_posted or adopt or close or reopen or begin_post or state_file"`
Expected: FAIL.

- [ ] **Step 3: Implement**

```python
COMPACT_LIMIT = 25
DEFAULT_STATE: dict[str, Any] = {
    "comment_id": "", "posted_fingerprint": "", "posted_date": "",
    "posting": {"state": "idle"}, "closed": False, "pr": "", "bast": "",
}  # fmt: skip


def load_state(repo: Path, ticket: str) -> dict[str, Any] | None:
    path = state_path(repo, ticket)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HandoverError(f"cannot read {path}: {exc}") from exc
    merged = {**DEFAULT_STATE, **data}
    merged["posting"] = data.get("posting") or {"state": "idle"}
    return merged


def save_state(repo: Path, ticket: str, state: dict[str, Any]) -> None:
    write_atomic(
        state_path(repo, ticket), json.dumps(state, indent=2, sort_keys=True) + "\n"
    )


def _state_or_default(repo: Path, ticket: str) -> dict[str, Any]:
    return load_state(repo, ticket) or {**DEFAULT_STATE, "posting": {"state": "idle"}}


def _branch(self: Inventory) -> str:
    for line in self.lines:
        if line.startswith("- Branch:"):
            return line.split(":", 1)[1].strip().strip("`")
    return "-"


def _notes(self: Inventory) -> list[str]:
    start = self.heading("Notes")
    if start is None:
        return []
    out: list[str] = []
    for line in self.lines[start + 1 :]:
        if line.startswith("## "):
            break
        if line.strip().startswith("- "):
            out.append(line.strip())
    return out


Inventory.branch = _branch  # type: ignore[attr-defined]
Inventory.notes = _notes  # type: ignore[attr-defined]


def stable_lines(inv: Inventory, state: dict[str, Any], ticket: str) -> list[str]:
    """The published body without the volatile date, status and footer lines."""
    rows = sorted(
        (cells for _, cells in inv.rows()[0]),
        key=lambda c: (c[0].lower(), norm(c[1]).lower(), norm(c[2]).lower(), c[3]),
    )
    lines = [f"Handover inventory for {ticket} (edited in place)"]
    if len(rows) > COMPACT_LIMIT:
        counts: dict[str, int] = {}
        for cells in rows:
            counts[cells[0]] = counts.get(cells[0], 0) + 1
        lines += ["", f"Objects: {len(rows)} (compact)"]
        lines += [f"- {name}: {counts[name]}" for name in sorted(counts)]
    else:
        current = None
        for cells in rows:
            if cells[0] != current:
                current = cells[0]
                lines += ["", current]
            lines.append(f"- {cells[2]} | {cells[1]} | {cells[3]} | {cells[4]}")
    lines += [
        "", f"Branch: {inv.branch()}",  # type: ignore[attr-defined]
        f"PR: {state['pr'] or '-'}", f"BAST: {state['bast'] or '-'}",
    ]  # fmt: skip
    notes = inv.notes()  # type: ignore[attr-defined]
    if notes:
        lines += ["", "Notes:", *notes]
    lines += ["", f"Details: release/{ticket}/docs/HANDOVER.md"]
    return lines


def fingerprint(inv: Inventory, state: dict[str, Any], ticket: str) -> str:
    return hashlib.sha256(
        "\n".join(stable_lines(inv, state, ticket)).encode("utf-8")
    ).hexdigest()


def render(repo: Path, ticket: str, jira_status: str, date: str) -> str:
    inv = load_inventory(repo, ticket)
    state = _state_or_default(repo, ticket)
    stable = stable_lines(inv, state, ticket)
    rows = inv.rows()[0]
    planned = sum(1 for _, c in rows if c[4] == "planned")
    touched = sum(1 for _, c in rows if c[4] == "touched")
    fp = hashlib.sha256("\n".join(stable).encode("utf-8")).hexdigest()
    body = [
        stable[0], f"Updated: {date}",
        f"Status: {jira_status} | planned: {planned} | touched: {touched}",
        *stable[1:], "", f"Fingerprint: {fp[:12]}",
    ]  # fmt: skip
    return "\n".join(body) + "\n"


def fp_equal(a: str, b: str) -> bool:
    return bool(a) and bool(b) and a[:12] == b[:12]


def _has_content(inv: Inventory) -> bool:
    return bool(inv.rows()[0]) or bool(inv.notes())  # type: ignore[attr-defined]


def cmd_set_links(
    repo: Path, ticket: str, pr: str | None = None, bast: str | None = None
) -> None:
    state = _state_or_default(repo, ticket)
    if pr is not None:
        state["pr"] = check_value(pr, "pr", True)
    if bast is not None:
        state["bast"] = check_value(bast, "bast", True)
    save_state(repo, ticket, state)


def cmd_changed(repo: Path, ticket: str, jira_status: str | None = None) -> str:
    state = load_state(repo, ticket)
    if state is None:
        return "no-state"
    if state["posting"].get("state") == "pending":
        return "pending"
    if state["closed"]:
        if jira_status is not None and jira_status != "Done":
            state["closed"] = False
            save_state(repo, ticket, state)
        else:
            return "closed"
    inv = load_inventory(repo, ticket)
    if not state["posted_fingerprint"]:
        return "changed" if _has_content(inv) else ""
    current = fingerprint(inv, state, ticket)
    return "" if fp_equal(current, state["posted_fingerprint"]) else "changed"


def cmd_begin_post(repo: Path, ticket: str) -> None:
    state = _state_or_default(repo, ticket)
    if state["posting"].get("state") == "pending":
        raise HandoverError("a post is already pending; recover it or run abort-post")
    inv = load_inventory(repo, ticket)
    state["posting"] = {
        "state": "pending",
        "approved": fingerprint(inv, state, ticket),
        "since": dt.date.today().isoformat(),
    }
    save_state(repo, ticket, state)


def cmd_abort_post(repo: Path, ticket: str) -> None:
    state = _state_or_default(repo, ticket)
    state["posting"] = {"state": "idle"}
    save_state(repo, ticket, state)


def cmd_mark_posted(
    repo: Path, ticket: str, comment_id: str, date: str | None = None
) -> None:
    state = _state_or_default(repo, ticket)
    if state["posting"].get("state") != "pending":
        raise HandoverError("no post is pending; run begin-post first")
    state["comment_id"] = check_value(str(comment_id), "comment id", True)
    state["posted_fingerprint"] = state["posting"]["approved"]
    state["posted_date"] = date or dt.date.today().isoformat()
    state["posting"] = {"state": "idle"}
    save_state(repo, ticket, state)


def cmd_adopt(repo: Path, ticket: str, comment_id: str, fp: str) -> None:
    state = _state_or_default(repo, ticket)
    state["comment_id"] = check_value(str(comment_id), "comment id", True)
    state["posted_fingerprint"] = check_value(fp, "fingerprint", True)
    state["posting"] = {"state": "idle"}
    save_state(repo, ticket, state)


def cmd_close(repo: Path, ticket: str) -> None:
    state = _state_or_default(repo, ticket)
    if state["posting"].get("state") == "pending":
        raise HandoverError("a post is pending; recover it before closing")
    inv = load_inventory(repo, ticket)
    published = fp_equal(fingerprint(inv, state, ticket), state["posted_fingerprint"])
    if not published and _has_content(inv):
        raise HandoverError("unpublished changes remain; post them before closing")
    state["closed"] = True
    save_state(repo, ticket, state)


def cmd_reopen(repo: Path, ticket: str) -> None:
    state = _state_or_default(repo, ticket)
    state["closed"] = False
    save_state(repo, ticket, state)
```

(`Inventory.branch` and `Inventory.notes` are shown as module-level functions attached to the class to keep the plan's code blocks short; in the file define them as normal methods inside `class Inventory` and drop the `type: ignore` comments.)

- [ ] **Step 4: Run to verify they pass**

Run: `uv run pytest tests/test_handover.py -q`
Expected: PASS. If a test's literal output differs from the implementation by wording only, change the implementation to match the spec text, not the assertion.

- [ ] **Step 5: Checkpoint**

Ruff, mypy, pytest, Python 3.9 and 3.12 import check:
`for v in 3.9 3.12; do uv run --no-project --python $v python -c "import importlib.util,sys;s=importlib.util.spec_from_file_location('h','CLAUDE/skills/handover/handover.py');m=importlib.util.module_from_spec(s);sys.modules['h']=m;s.loader.exec_module(m);print('$v ok')"; done`
Commit only on request (`✨ feat(claude): add the handover posting state machine and render`).

---

### Task 5: `check` and the command line

**Files:**
- Modify: `CLAUDE/skills/handover/handover.py` (`cmd_check`, `build_parser`, `main`)
- Test: `tests/test_handover.py`

**Interfaces:**
- Consumes: Tasks 1 to 4.
- Produces: `cmd_check(repo, ticket) -> tuple[list[str], list[str]]` (directories scanned, unmatched files), `build_parser() -> argparse.ArgumentParser`, `main(argv: list[str] | None = None) -> int`.

- [ ] **Step 1: Write the failing tests**

```python
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
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/test_handover.py -q -k "check or cli"`
Expected: FAIL.

- [ ] **Step 3: Implement**

```python
CHECK_SKIP_NAMES = {"CONTEXT.md", "handover.state.json"}


def cmd_check(repo: Path, ticket: str) -> tuple[list[str], list[str]]:
    """Files outside git (or the ticket's change folders) with no Source in the inventory."""
    validate_ticket(ticket)
    sources: set[str] = set()
    for _, cells in load_inventory(repo, ticket).rows()[0]:
        sources.update(split_list(cells[6]))
    dirs = [f"release/{ticket}/{d}" for d in ("ddl", "flink", "config", "data")]
    dirs.append(f"scratch/{ticket}")
    scanned: list[str] = []
    unmatched: list[str] = []
    for d in dirs:
        base = repo / d
        if not base.is_dir():
            continue
        scanned.append(d)
        for path in sorted(base.rglob("*")):
            if not path.is_file() or path.name in CHECK_SKIP_NAMES:
                continue
            rel = path.relative_to(repo).as_posix()
            if rel.startswith(f"scratch/{ticket}/docs/"):
                continue
            if any(rel == s or rel.startswith(s + "/") for s in sources):
                continue
            unmatched.append(rel)
    return scanned, unmatched


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    def command(name: str, *, ticket: bool = True) -> argparse.ArgumentParser:
        p = sub.add_parser(name)
        p.add_argument(
            "--repo", default=None, help="repository (default: the current one)"
        )
        if ticket:
            p.add_argument("--ticket", required=True)
        return p

    p = command("init")
    p.add_argument("--branch", required=True)
    p = command("add")
    for opt in ("platform", "locator", "object", "env"):
        p.add_argument(f"--{opt}", required=True)
    p.add_argument("--state", required=True, choices=STATES)
    p.add_argument("--source", default=None)
    p.add_argument("--allow-secret-like", action="store_true")
    p = command("remove")
    for opt in ("platform", "locator", "object", "env"):
        p.add_argument(f"--{opt}", required=True)
    p = command("plan-sync")
    p.add_argument("--source", required=True)
    p.add_argument("--objects-file", required=True)
    p.add_argument("--allow-empty", action="store_true")
    p = command("note")
    p.add_argument("--text", required=True)
    p.add_argument("--allow-secret-like", action="store_true")
    p = command("set")
    p.add_argument("--branch", default=None)
    p.add_argument("--pr", default=None)
    p.add_argument("--bast", default=None)
    command("show")
    command("check")
    p = command("render")
    p.add_argument("--jira-status", required=True)
    p.add_argument("--date", required=True)
    p = command("changed")
    p.add_argument("--jira-status", default=None)
    command("begin-post")
    command("abort-post")
    p = command("mark-posted")
    p.add_argument("--comment-id", required=True)
    p.add_argument("--date", default=None)
    p = command("adopt")
    p.add_argument("--comment-id", required=True)
    p.add_argument("--fingerprint", required=True)
    command("close")
    command("reopen")
    return parser


def run(args: argparse.Namespace) -> int:
    repo = find_repo(args.repo)
    t = args.ticket
    name = args.command
    if name == "init":
        print(f"created {cmd_init(repo, t, args.branch)}")
    elif name == "add":
        print(
            cmd_add(
                repo,
                t,
                args.platform,
                args.locator,
                args.object,
                args.env,
                args.state,
                args.source,
                args.allow_secret_like,
            )  # fmt: skip
        )
    elif name == "remove":
        if cmd_remove(repo, t, args.platform, args.locator, args.object, args.env):
            print("removed")
        else:
            print("no such row")
            return 1
    elif name == "plan-sync":
        counts = cmd_plan_sync(
            repo,
            t,
            args.source,
            load_objects_file(Path(args.objects_file)),
            args.allow_empty,
        )
        print(
            f"added {counts['added']}, kept {counts['kept']}, removed {counts['removed']}"
        )
    elif name == "note":
        cmd_note(repo, t, args.text, args.allow_secret_like)
        print("noted")
    elif name == "set":
        if args.branch is not None:
            cmd_set_branch(repo, t, args.branch)
        if args.pr is not None or args.bast is not None:
            cmd_set_links(repo, t, args.pr, args.bast)
        print("set")
    elif name == "show":
        print(cmd_show(repo, t), end="")
    elif name == "check":
        scanned, unmatched = cmd_check(repo, t)
        print("scanned: " + (", ".join(scanned) if scanned else "(no folders)"))
        print(
            "\n".join(f"no inventory line: {p}" for p in unmatched)
            if unmatched
            else "all files have an inventory line"
        )
    elif name == "render":
        print(render(repo, t, args.jira_status, args.date), end="")
    elif name == "changed":
        word = cmd_changed(repo, t, args.jira_status)
        if word:
            print(word)
    elif name == "begin-post":
        cmd_begin_post(repo, t)
        print("pending")
    elif name == "abort-post":
        cmd_abort_post(repo, t)
        print("idle")
    elif name == "mark-posted":
        cmd_mark_posted(repo, t, args.comment_id, args.date)
        print("posted")
    elif name == "adopt":
        cmd_adopt(repo, t, args.comment_id, args.fingerprint)
        print("adopted")
    elif name == "close":
        cmd_close(repo, t)
        print("closed")
    elif name == "reopen":
        cmd_reopen(repo, t)
        print("reopened")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return run(args)
    except HandoverError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
```

Recorded deviation from the spec: `check` also skips `scratch/<TICKET>/docs/`, `CONTEXT.md` and the state file, because those hold samples and indexes, not change artifacts; the SKILL text says so.

- [ ] **Step 4: Run to verify they pass**

Run: `uv run pytest tests/test_handover.py -q && for v in 3.9 3.12; do uv run --no-project --python $v --with pytest python -m pytest tests/test_handover.py -q -p no:cacheprovider 2>&1 | tail -1; done`
Expected: PASS on 3.11, 3.9 and 3.12.

- [ ] **Step 5: Checkpoint**

Ruff, mypy, full pytest; commit only on request (`✨ feat(claude): add the handover check and command line`).

---

### Task 6: Skill, command, integrations, rule text

**Files:**
- Create: `CLAUDE/skills/handover/SKILL.md`, `CLAUDE/commands/handover.md`
- Modify: `CLAUDE/skills/jira-ticket-kickoff/SKILL.md`, `CLAUDE/commands/commit.md`, `CLAUDE/commands/generate-pr-message.md`, `CLAUDE/skills/bast-generator/SKILL.md`, `CLAUDE/CLAUDE.md`, `docs/guidelines/DEV-WORKFLOW.md`, `README.md`, `CLAUDE/README.md`
- Test: `tests/test_handover.py`

- [ ] **Step 1: Write the failing text tests**

```python
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
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/test_handover.py -q -k "skill_describes or command_exists or integrations or old_status"`
Expected: FAIL.

- [ ] **Step 3: Write the texts**

`CLAUDE/skills/handover/SKILL.md` (frontmatter `name: handover`, a `description` that triggers on "/handover", "update the handover", "handover for PROJ-1234", "who takes over", and on the moments below). Body sections, each short:

1. **What it is**: the inventory (`release/<TICKET>/docs/HANDOVER.md`) and the local state (`scratch/<TICKET>/handover.state.json`); the helper path `~/.claude/skills/handover/handover.py`; it records where to look, not what changed.
2. **Recording (silent)**: the four events and the exact commands:
   - plan or spec written, revised or approved: read it, print the objects extracted on one line, write them to a small JSON file in the scratchpad, run `handover.py plan-sync --ticket T --source <plan> --objects-file <file>`;
   - Claude writes or edits a change artifact: `handover.py add ... --state touched --source <path>`;
   - the user reports applying or saving a change: `add --state touched` plus `note`;
   - ask once at each commit and PR: "any objects touched outside this session?".
   What does not count (comments, TODOs, reading). Locator formats per platform. No secrets.
3. **Posting (proposed, then OK)**: at `/commit` (after the commit succeeded), `/generate-pr-message` (both PR targets) and `/handover`. Steps: `changed`; if `changed`, show `render --jira-status <read from Jira> --date <today>`; on OK run `begin-post`, then find the target comment (stored id in the state, else `listJiraIssueComments` and take the newest whose first line is the marker), `addOrEditJiraIssueComment` (edit by id, create only if no marker comment exists; if the edit is refused or the id is gone, create a new marker comment with the same approved text), then `mark-posted --comment-id <id returned>`.
4. **Recovery** when `changed` prints `pending`: the four-step procedure of spec 6.2 verbatim in short form (`adopt`/`mark-posted` when the footer matches, `abort-post` and a fresh proposal otherwise); never write unapproved text.
5. **Done and reopening**: at `Done` the final-post policy and `close`; `changed --jira-status <status>` reopens a closed ticket that left `Done`.
6. **Taking over**: the five steps of spec 11.3.
7. **Rules**: personal slug work gets no automatic init; the description is never edited; `check` skips `scratch/<TICKET>/docs/`, `CONTEXT.md` and the state file.

`CLAUDE/commands/handover.md`: frontmatter `description: Update the ticket handover inventory and propose the Jira handover comment`, `allowed-tools: Bash(python3:*), Bash(git:*)` plus the Atlassian tools used (`mcp__plugin_atlassian_atlassian__getJiraIssue`, `...listJiraIssueComments` through `executeRead`, `...addOrEditJiraIssueComment`). Steps: resolve the ticket from the branch name; `check`; ask "any objects touched outside this session?" and record the answer; run the posting procedure of the skill; offer the final post when Jira reads `Done`.

Integrations (add after reading each file; keep every edit to a short paragraph):
- `jira-ticket-kickoff/SKILL.md`: in Step 6a (after the scaffold and the scratch step) for Jira-key paths A and B: `python3 ~/.claude/skills/handover/handover.py init --ticket <TICKET-ID> --branch <branch>` (skip when the file exists); in Path B's progress recap (Step 6b): read `release/<TICKET-ID>/docs/HANDOVER.md` first and show the objects, notes and the result of `handover.py check`; Path C (slug) does not run `init`.
- `commit.md`: add `Bash(python3:*)` and the Atlassian read/write tool names to `allowed-tools`; in Phase 1 run `handover.py check` and `handover.py changed` for the ticket in the branch name and add the one-line prompt to the Phase 4 review; in Phase 5, after the commit succeeded, run the posting procedure if the user accepted; `HANDOVER.md` is committed like any other changed file.
- `generate-pr-message.md`: in the Jira Status Check phase, after the status is read, run `handover.py changed --jira-status <status>` for both PRs (feature to `dev`, `dev` to `master`); run `handover.py set --pr <url>` when the URL is known; offer the posting or the final post.
- `bast-generator/SKILL.md`: Step 2 compares the BAST scope rows with `handover.py show`, lists objects present in one but not the other; Step 8 runs `handover.py set --bast <page url>`.
- `CLAUDE/CLAUDE.md`: a `## Ticket Handover` section stating the triggers, "recording is silent, posting is proposed", the two files, and the command `/handover`; add `/handover` to the slash command table.
- `DEV-WORKFLOW.md`: replace the "designed, not built yet" status line with the location of the skill and helper.
- `README.md` and `CLAUDE/README.md`: a `/handover` row in each command table and a `handover` row in the skills table.

- [ ] **Step 4: Run to verify, sweep, full verification**

Run: `uv run pytest tests/test_handover.py -q && uv run ruff format -q . && uv run ruff check . && uv run mypy . && uv run pytest -q`
`grep -rnE "\`In progress\`|\`PR to|\`Merged to|\`Released\`|Ready to Release" CLAUDE docs/guidelines | grep -v create-readme | grep -v logbook.py`
Expected: all green; the grep prints nothing.

- [ ] **Step 5: Checkpoint**

Show `git status`; commit only on request (`📝 docs(claude): add the handover skill and wire it into the dev cycle`).

---

### Task 7: Final verification and PR

- [ ] **Step 1: Full verification**

`uv run ruff format --check . && uv run ruff check . && uv run mypy . && uv run pytest -q`, then the 3.9 and 3.12 test runs of `tests/test_handover.py` and the logbook tests.
Expected: all green.

- [ ] **Step 2: Real-ticket dry run (read-only on Jira)**

In a scratch clone or a throwaway directory with `git init`, run the end-to-end CLI sequence of the Task 5 test by hand, then read the rendered comment and check it for hosts, names and secrets. Do not post to a real ticket during this step.

- [ ] **Step 3: Open the PR only when the user asks**

Branch from `dev` (for example `feat/ticket-handover`), push, PR to `dev`. The body ends with the Claude Code line. Propose a logbook row (personal tooling: `Done` once PR-ed to `master`).

---

### Task 8: Deploy to the live `~/.claude` (with the user)

Only after the PR is merged into `dev`. `~/.claude` is not a git repository, so a backup is the rollback.

- [ ] **Step 1: Back up**

```bash
stamp=$(date +%Y%m%d-%H%M%S); b=~/.claude/logbook/pre-handover-$stamp; mkdir -p "$b"
cp ~/.claude/CLAUDE.md "$b"/
cp ~/.claude/commands/{commit,generate-pr-message}.md "$b"/
cp ~/.claude/skills/jira-ticket-kickoff/SKILL.md "$b"/kickoff-SKILL.md
cp ~/.claude/skills/bast-generator/SKILL.md "$b"/bast-SKILL.md
ls "$b"
```

Expected: the five files are listed.

- [ ] **Step 2: Install**

Copy the new files (`skills/handover/`, `commands/handover.md`). Apply the Task 6 edits to the live `CLAUDE.md`, `commit.md`, `generate-pr-message.md`, `jira-ticket-kickoff/SKILL.md` and `bast-generator/SKILL.md` with the Edit tool (the live files differ from the template by company values, so do not copy the template over them). Check each live file against the template with the placeholders normalised.

- [ ] **Step 3: First run on a real ticket, by hand**

On the next ticket: `init` at kickoff, one `plan-sync`, one `add`, then a `/commit` that proposes a post; approve it once and check the Jira comment (marker line, objects, footer) and the local state file. Then simulate the crash path on a throwaway ticket: run `begin-post`, skip `mark-posted`, and run `changed` (expected `pending`).

- [ ] **Step 4: Recovery (only if something is wrong)**

Restore the backed-up files and delete the `skills/handover` folder; the helper's two ticket files are plain Markdown and JSON and can stay.

---

## Self-Review

**Spec coverage**
- Sections 1 and 2 (purpose, two files, columns, cell rules, normalisation, state file): Tasks 1 and 2 (`Inventory`, `add`, escaping, lists, paths) and Task 4 (state).
- Section 3 (states): Tasks 2 and 3. Section 4 (triggers): Task 6 texts.
- Section 5 (helper, every command): `init`, `add`, `remove`, `note`, `set` in Tasks 1, 2 and 4; `plan-sync` Task 3; `check`, CLI, `--repo` Task 5; `render`, `changed`, `begin-post`, `abort-post`, `mark-posted`, `adopt`, `close`, `reopen` Task 4.
- Section 6 (Jira comment, two-phase flow, recovery, final post, order of operations): the helper side in Task 4; the model-side procedure in the SKILL text of Task 6.
- Sections 7 to 11 (rules, errors, tests, rollout, integration): Tasks 6, 7 and 8; the `/pipeline` flag stays a separate follow-up.

**Placeholder scan:** no deferred code in the helper tasks. Task 6 gives the content required of each text and the exact commands; the wording is written when the files are read, because the anchors depend on each file's current text.

**Type consistency:** `cmd_*` functions take `(repo: Path, ticket: str, ...)` throughout; the state keys are `comment_id`, `posted_fingerprint`, `posted_date`, `posting`, `closed`, `pr`, `bast` in the tests and the code; `Inventory.rows()` returns `(rows, problems)` everywhere it is used.

**Recorded deviations from the spec:** `check` also skips `scratch/<TICKET>/docs/`, `CONTEXT.md` and the state file (samples and indexes, not change artifacts).
