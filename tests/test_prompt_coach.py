"""Tests for the prompt-coach helper shipped with the prompt-coach skill."""

from __future__ import annotations

import importlib.util
import io
import json
import os
import re
import stat
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType

import pytest

UTC = timezone.utc  # noqa: UP017 - datetime.UTC needs Python 3.11; the helper runs on 3.9

COACH = Path(__file__).resolve().parents[1] / "CLAUDE/skills/prompt-coach/coach.py"

JWT = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.abcDEF123_-xyzXYZ"
PEM = (
    "-----BEGIN PRIVATE KEY-----\n"
    "MIIEvQIBADANBgkqhkiG9w0BAQEFAASC\n"
    "-----END PRIVATE KEY-----"
)


@pytest.fixture()
def coach() -> ModuleType:
    spec = importlib.util.spec_from_file_location("prompt_coach", COACH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["prompt_coach"] = module
    spec.loader.exec_module(module)
    return module


# (input, text the output must contain, text the output must not contain)
HIDES = [
    ("password=hunter2", "password=[REDACTED:secret]", "hunter2"),
    ('{"api_key": "abc123xyz"}', "[REDACTED:secret]", "abc123xyz"),
    ("Authorization: Bearer abcDEF123xyz", "[REDACTED:bearer]", "abcDEF123xyz"),
    ("postgres://u:p4ss@db.internal/x", "[REDACTED:url-credentials]", "p4ss"),
    (f"token {JWT}", "[REDACTED:jwt]", "abcDEF123_-xyzXYZ"),
    (PEM, "[REDACTED:private-key]", "MIIEvQIBADANBgkqhkiG9w0BAQEFAASC"),
    ("hash " + "a1b2c3d4" * 4, "[REDACTED:opaque]", "a1b2c3d4a1b2c3d4"),
    ("key LTAI" + "Ab12" * 4, "[REDACTED:access-key]", "LTAIAb12"),
    ("key AKIA" + "ABCD1234" * 2, "[REDACTED:access-key]", "AKIAABCD1234"),
    ("key ghp_" + "aB3" * 12, "[REDACTED:access-key]", "ghp_aB3"),
    ("key sk-" + "x9" * 20, "[REDACTED:access-key]", "sk-x9x9"),
    ("mail me@example.com now", "[REDACTED:email]", "me@example.com"),
    ("host 10.12.3.4 down", "[REDACTED:ip]", "10.12.3.4"),
]


@pytest.mark.parametrize(("text", "has", "lacks"), HIDES)
def test_mask_hides(coach: ModuleType, text: str, has: str, lacks: str) -> None:
    out = coach.mask(text)
    assert has in out
    assert lacks not in out


@pytest.mark.parametrize(
    "text",
    [
        "DA-1234",
        "another-repo",
        "release/DA-1234/CHANGELOG.md",
        "version 1.7.0 and 1.2.3",
        "short sha 3b36804 only",
        "docs/superpowers/plans/2026-11-02-prompt-coach.md",
    ],
)
def test_mask_keeps(coach: ModuleType, text: str) -> None:
    assert coach.mask(text) == text


@pytest.mark.parametrize("text", [h[0] for h in HIDES])
def test_mask_is_idempotent(coach: ModuleType, text: str) -> None:
    once = coach.mask(text)
    assert coach.mask(once) == once


def test_mask_prose_secret_passes_through(coach: ModuleType) -> None:
    # Documented limit: a secret written in ordinary prose is not recognized.
    assert coach.mask("my password is hunter2") == "my password is hunter2"


def test_mask_failure_never_leaks(
    coach: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def boom(text: str) -> str:
        raise re.error("boom")

    monkeypatch.setattr(coach, "_RULES", [("secret", boom)])
    assert coach.mask("secret=abc") == "[REDACTED:error]"
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == ""


def test_mask_large_input_has_no_catastrophic_backtracking(coach: ModuleType) -> None:
    inputs = [
        "word " * 200_000 + " password=hunter2",
        "a" * 200_000,
        "=" * 200_000,
        ":" * 200_000,
        "eyJ." * 50_000,
        "eyJ" * 60_000,
        "-----BEGIN PRIVATE KEY-----" * 5_000,
        "http://" * 30_000,
    ]
    start = time.monotonic()
    outputs = [coach.mask(text) for text in inputs]
    assert time.monotonic() - start < 20
    assert "hunter2" not in outputs[0]


# ---------------------------------------------------------------- Task 2: capture


@pytest.fixture()
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "prompt-coach"
    monkeypatch.setenv("PROMPT_COACH_HOME", str(path))
    return path


def turn_on(home: Path) -> None:
    home.mkdir(parents=True, exist_ok=True)
    (home / "enabled").write_text("on\n")


def payload(
    prompt: object, cwd: str = "/home/someone/repo/my-repo"
) -> dict[str, object]:
    return {"prompt": prompt, "session_id": "sess-1", "cwd": cwd}


def log_lines(home: Path) -> list[dict[str, object]]:
    path = home / "prompts.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines()]


def test_off_writes_nothing(coach: ModuleType, home: Path) -> None:
    assert coach.capture(payload("please update the logbook for today")) is None
    assert not home.exists()


def test_short_prompt_logged_without_coaching(coach: ModuleType, home: Path) -> None:
    turn_on(home)
    result = coach.capture(payload("go ahead"))
    assert result is not None and result[1] is False
    lines = log_lines(home)
    assert len(lines) == 1 and lines[0]["coach"] is False
    assert lines[0]["text"] == "go ahead"


@pytest.mark.parametrize(
    "prompt",
    [
        "This session is being continued from a previous conversation that ran out of context.",
        "/logbook",
    ],
)
def test_continuation_and_slash_command_not_coached(
    coach: ModuleType, home: Path, prompt: str
) -> None:
    turn_on(home)
    result = coach.capture(payload(prompt))
    assert result is not None and result[1] is False


def test_normal_prompt_is_coached(coach: ModuleType, home: Path) -> None:
    turn_on(home)
    result = coach.capture(payload("please update the logbook for DA-1234 today"))
    assert result is not None and result[1] is True
    assert re.fullmatch(r"[0-9a-f]{8}", result[0])
    assert log_lines(home)[0]["id"] == result[0]


def test_pure_pasted_block_stub(coach: ModuleType, home: Path) -> None:
    turn_on(home)
    body = "top secret text that must never be stored " * 5
    block = f'<pasted_content id="x">{body}</pasted_content id="x">'
    result = coach.capture(payload(block))
    assert result is not None and result[1] is False
    assert log_lines(home)[0]["text"] == f"[pasted content, {len(body)} chars]"
    assert "top secret" not in (home / "prompts.jsonl").read_text()


def test_mixed_prompt_stubs_only_the_paste(coach: ModuleType, home: Path) -> None:
    turn_on(home)
    prompt = (
        'please check <pasted_content id="a">secret body here</pasted_content id="a">'
        " and tell me what it means"
    )
    result = coach.capture(payload(prompt))
    assert result is not None and result[1] is True
    text = log_lines(home)[0]["text"]
    assert text == "please check [pasted content, 16 chars] and tell me what it means"


def test_logged_text_is_masked_and_project_only(coach: ModuleType, home: Path) -> None:
    turn_on(home)
    coach.capture(payload("please use password=hunter2 for the new database"))
    raw = (home / "prompts.jsonl").read_text()
    line = log_lines(home)[0]
    assert "hunter2" not in raw and "password=[REDACTED:secret]" in raw
    assert line["project"] == "my-repo"
    assert "/home/" not in raw


def test_large_prompt_is_truncated(coach: ModuleType, home: Path) -> None:
    turn_on(home)
    coach.capture(payload("word " * 200_000))
    text = str(log_lines(home)[0]["text"])
    assert len(text) < 4100 and "…[truncated" in text


def test_refuses_git_worktree(
    coach: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    inside = repo / "coach"
    monkeypatch.setenv("PROMPT_COACH_HOME", str(inside))
    inside.mkdir()
    (inside / "enabled").write_text("on\n")
    with pytest.raises(coach.CoachError):
        coach.capture(payload("please update the logbook for today"))
    assert not (inside / "prompts.jsonl").exists()


def test_modes(coach: ModuleType, home: Path) -> None:
    coach.capture(payload("not enabled so nothing happens here at all"))
    turn_on(home)
    coach.capture(payload("please update the logbook for today"))
    assert stat.S_IMODE(home.stat().st_mode) == 0o700
    assert stat.S_IMODE((home / "prompts.jsonl").stat().st_mode) == 0o600


def test_concurrent_capture_keeps_every_line(coach: ModuleType, home: Path) -> None:
    turn_on(home)

    def worker() -> None:
        for _ in range(10):
            coach.capture(payload("please update the logbook for today"))

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    lines = log_lines(home)
    assert len(lines) == 80
    assert len({line["id"] for line in lines}) == 80


# ---------------------------------------------------------------- Task 3: add


NOV2 = datetime(2026, 11, 2, 14, 5, tzinfo=UTC)


def captured(coach: ModuleType, home: Path, when: datetime = NOV2) -> str:
    turn_on(home)
    result = coach.capture(
        payload("please update the logbook for DA-1234 today"), now=when
    )
    assert result is not None
    return str(result[0])


def entry(prompt_id: str, **fields: object) -> str:
    data: dict[str, object] = {
        "id": prompt_id,
        "verdict": "minor",
        "context": "Logbook session",
        "understanding": "Update the logbook row for DA-1234",
        "alternatives": [],
        "rewrite": "Please update today's logbook row for DA-1234.",
        "changes": "Added the object and the time frame.",
        "tags": ["missing-goal", "ambiguous-reference"],
    }
    data.update(fields)
    return json.dumps(data)


def test_add_writes_entry_with_header_and_fields(coach: ModuleType, home: Path) -> None:
    prompt_id = captured(coach, home)
    assert coach.add_entry(entry(prompt_id), now=NOV2) == prompt_id
    text = (home / "2026-11.md").read_text()
    assert f"## 2026-11-02 14:05 - {prompt_id} - my-repo" in text
    assert "**Verdict:** minor" in text
    assert "**You wrote:** please update the logbook for DA-1234 today" in text
    assert "**Context:** Logbook session" in text
    assert "**Understood as:** Update the logbook row for DA-1234" in text
    assert "**Other readings:** none" in text
    assert "**Suggested:** Please update today's logbook row for DA-1234." in text
    assert "**Tags:** missing-goal, ambiguous-reference" in text


def test_add_text_survives_literally(coach: ModuleType, home: Path) -> None:
    prompt_id = captured(coach, home)
    nasty = "He said \"yes\" and 'no'\nsecond line 🙂 tolong cek $(rm -rf x) `ls` COACH_JSON_END"
    coach.add_entry(entry(prompt_id, understanding=nasty), now=NOV2)
    text = (home / "2026-11.md").read_text()
    for piece in (
        "He said \"yes\" and 'no'",
        "second line 🙂 tolong cek",
        "$(rm -rf x)",
        "`ls`",
        "COACH_JSON_END",
    ):
        assert piece in text


def test_add_continuation_lines_cannot_forge_a_header(
    coach: ModuleType, home: Path
) -> None:
    prompt_id = captured(coach, home)
    coach.add_entry(
        entry(prompt_id, understanding="a\n## 2026-01-01 00:00 - deadbeef - x"),
        now=NOV2,
    )
    text = (home / "2026-11.md").read_text()
    assert text.count("\n## ") + text.startswith("## ") == 1


def test_add_masks_generated_fields(coach: ModuleType, home: Path) -> None:
    prompt_id = captured(coach, home)
    coach.add_entry(
        entry(prompt_id, understanding="uses token=abc123 for the call"), now=NOV2
    )
    text = (home / "2026-11.md").read_text()
    assert "abc123" not in text and "token=[REDACTED:secret]" in text


@pytest.mark.parametrize(
    "mutate",
    [
        lambda i: entry(i, surprise="x"),
        lambda i: entry("XYZ"),
        lambda i: entry("deadbeef"),
        lambda i: entry(i, verdict="great"),
        lambda i: entry(i, tags=["not-a-tag"]),
        lambda i: entry(i, understanding=5),
        lambda i: entry(i, alternatives="one"),
        lambda i: "{not json",
        lambda i: "[]",
    ],
    ids=[
        "unknown-field",
        "bad-id-format",
        "id-not-in-log",
        "bad-verdict",
        "bad-tag",
        "non-string-field",
        "alternatives-not-list",
        "malformed-json",
        "json-array",
    ],
)
def test_add_rejects_and_writes_nothing(
    coach: ModuleType, home: Path, mutate: object
) -> None:
    prompt_id = captured(coach, home)
    with pytest.raises(coach.EntryError):
        coach.add_entry(mutate(prompt_id), now=NOV2)  # type: ignore[operator]
    assert not list(home.glob("*.md"))


def test_parse_entry_truncates_oversized_fields(coach: ModuleType) -> None:
    parsed = coach.parse_entry(entry("a1b2c3d4", understanding="x" * 5000))
    assert len(parsed["understanding"]) == 600 and parsed["understanding"].endswith(
        "..."
    )
    parsed = coach.parse_entry(entry("a1b2c3d4", alternatives=["a", "b", "c", "d"]))
    assert parsed["alternatives"] == ["a", "b", "c"]


def test_parse_entry_fits_total_limit_by_trimming_longest_first(
    coach: ModuleType,
) -> None:
    long = "y" * 600
    parsed = coach.parse_entry(
        entry(
            "a1b2c3d4",
            context=long,
            understanding=long,
            rewrite=long,
            changes=long,
            alternatives=[long, long, long],
        )
    )
    total = sum(
        len(parsed[k]) for k in ("context", "understanding", "rewrite", "changes")
    ) + sum(len(a) for a in parsed["alternatives"])
    assert total <= 3000
    assert parsed["context"].endswith("...") or parsed["alternatives"][0].endswith(
        "..."
    )


def test_add_for_prompt_captured_last_month(coach: ModuleType, home: Path) -> None:
    oct31 = datetime(2026, 10, 31, 23, 50, tzinfo=UTC)
    prompt_id = captured(coach, home, when=oct31)
    nov1 = datetime(2026, 11, 1, 9, 0, tzinfo=UTC)
    coach.add_entry(entry(prompt_id), now=nov1)
    assert (home / "2026-11.md").exists() and not (home / "2026-10.md").exists()


def test_month_file_is_oldest_first(coach: ModuleType, home: Path) -> None:
    first = captured(coach, home)
    second_result = coach.capture(
        payload("please also check the pipeline board today"), now=NOV2
    )
    assert second_result is not None
    coach.add_entry(entry(first), now=NOV2)
    coach.add_entry(
        entry(second_result[0]), now=datetime(2026, 11, 3, 8, 0, tzinfo=UTC)
    )
    text = (home / "2026-11.md").read_text()
    assert text.index(first) < text.index(second_result[0])


# ------------------------------------------------- Task 4: commands, hook, CLI

WARNING_START = "Local capture may still keep sensitive information"


def feed(monkeypatch: pytest.MonkeyPatch, text: str) -> None:
    monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(io.BytesIO(text.encode())))


def test_on_off_toggle_flag(coach: ModuleType, home: Path) -> None:
    assert (
        coach.set_enabled(True) == "prompt-coach: on (takes effect on the next prompt)"
    )
    assert [p.name for p in home.iterdir()] == ["enabled"]
    assert coach.set_enabled(False) == "prompt-coach: off"
    assert not (home / "enabled").exists()
    assert coach.set_enabled(False) == "prompt-coach: off"
    assert coach.set_enabled(True).startswith("prompt-coach: on")
    assert coach.set_enabled(True).startswith("prompt-coach: on")


def test_status_reports_path_counts_and_warning(coach: ModuleType, home: Path) -> None:
    prompt_id = captured(coach, home)
    coach.add_entry(entry(prompt_id))
    out = coach.status()
    assert str(home) in out and "on" in out.splitlines()[0]
    assert "Entries this month: 1" in out
    assert "minor 1" in out and "clear 0" in out
    assert WARNING_START in out


def test_status_explains_a_refused_directory(
    coach: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / ".git").mkdir()
    monkeypatch.setenv("PROMPT_COACH_HOME", str(tmp_path / "coach"))
    out = coach.status()
    assert "git worktree" in out and WARNING_START in out
    assert (
        coach.hook_output(json.dumps(payload("please update the logbook today"))) == ""
    )


def test_show_is_newest_first_and_read_only(coach: ModuleType, home: Path) -> None:
    first = captured(coach, home)
    second = coach.capture(
        payload("please also check the pipeline board today"), now=NOV2
    )
    assert second is not None
    coach.add_entry(entry(first), now=NOV2)
    coach.add_entry(entry(second[0]), now=datetime(2026, 11, 3, 8, 0, tzinfo=UTC))
    path = home / "2026-11.md"
    before = path.read_bytes()
    out = coach.show(2)
    assert out.index(second[0]) < out.index(first)
    assert second[0] in coach.show(1) and first not in coach.show(1)
    assert path.read_bytes() == before


def test_show_with_no_entries(coach: ModuleType, home: Path) -> None:
    assert "no entries" in coach.show()
    assert not home.exists()


def test_hook_output_for_coached_prompt(coach: ModuleType, home: Path) -> None:
    turn_on(home)
    out = coach.hook_output(
        json.dumps(payload("please update the logbook for DA-1234 today"))
    )
    data = json.loads(out)
    assert data["hookSpecificOutput"]["hookEventName"] == "UserPromptSubmit"
    context = data["hookSpecificOutput"]["additionalContext"]
    prompt_id = str(log_lines(home)[0]["id"])
    script = os.path.expanduser("~/.claude/skills/prompt-coach/coach.py")
    assert f"python3 {script} add <<'COACH_JSON_END_{prompt_id}'" in context
    assert f"\nCOACH_JSON_END_{prompt_id}\n" in context
    for phrase in (
        "exactly as you would without",
        "LAST tool call",
        "Prompt coach:",
        "clear, no change",
        "Better:",
        "Alternative reading",
    ):
        assert phrase in context
    assert len(context.split()) < 200


def test_hook_output_empty_when_off_or_uncoached(coach: ModuleType, home: Path) -> None:
    assert (
        coach.hook_output(json.dumps(payload("please update the logbook today"))) == ""
    )
    turn_on(home)
    assert coach.hook_output(json.dumps(payload("go ahead"))) == ""
    assert len(log_lines(home)) == 1


@pytest.mark.parametrize(
    "raw", ["", "not json", "{}", '{"prompt": 5}', '{"prompt": null}', "[]"]
)
def test_hook_survives_bad_input(
    coach: ModuleType, home: Path, monkeypatch: pytest.MonkeyPatch, raw: str
) -> None:
    turn_on(home)
    assert coach.hook_output(raw) == ""
    feed(monkeypatch, raw)
    assert coach.main(["hook"]) == 0
    assert log_lines(home) == []


def test_main_add_failure_exits_zero_and_prints_one_line(
    coach: ModuleType,
    home: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    turn_on(home)
    feed(monkeypatch, "{secret=hunter2 not json")
    assert coach.main(["add"]) == 0
    out = capsys.readouterr().out
    assert len(out.strip().splitlines()) == 1
    assert "EntryError" in out and "hunter2" not in out


def test_main_hook_error_goes_to_stderr_not_stdout(
    coach: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    (tmp_path / ".git").mkdir()
    monkeypatch.setenv("PROMPT_COACH_HOME", str(tmp_path / "coach"))
    feed(monkeypatch, json.dumps(payload("please update the logbook today")))
    assert coach.main(["hook"]) == 0
    assert capsys.readouterr().out == ""


def test_main_unknown_command_is_an_error(coach: ModuleType) -> None:
    assert coach.main(["frobnicate"]) == 2


# ---------------------------------------------------- Task 5: bash hook wrapper

HOOK = (
    Path(__file__).resolve().parents[1]
    / "CLAUDE/linux-wsl/hooks/prompt-coach-capture.sh"
)


def run_hook(
    stdin: str, script: Path | str = COACH, timeout: float = 20
) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "PROMPT_COACH_SCRIPT": str(script)}
    return subprocess.run(
        ["bash", str(HOOK)],
        input=stdin,
        capture_output=True,
        text=True,
        env=env,
        timeout=timeout,
    )


def test_hook_script_coach_on_prints_context(home: Path) -> None:
    turn_on(home)
    result = run_hook(
        json.dumps(payload("please update the logbook for DA-1234 today"))
    )
    assert result.returncode == 0
    context = json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"]
    assert str(log_lines(home)[0]["id"]) in context


def test_hook_script_coach_off_is_silent(home: Path) -> None:
    result = run_hook(
        json.dumps(payload("please update the logbook for DA-1234 today"))
    )
    assert result.returncode == 0 and result.stdout == ""
    assert not home.exists()


def test_hook_script_missing_helper_is_silent(home: Path, tmp_path: Path) -> None:
    turn_on(home)
    result = run_hook("{}", script=tmp_path / "missing.py")
    assert result.returncode == 0 and result.stdout == "" and result.stderr == ""


def test_hook_script_failing_helper_is_silent(home: Path, tmp_path: Path) -> None:
    stub = tmp_path / "stub.py"
    stub.write_text("import sys\nsys.exit(1)\n")
    result = run_hook("{}", script=stub)
    assert result.returncode == 0 and result.stdout == ""


def test_hook_script_slow_helper_is_cut_off(home: Path, tmp_path: Path) -> None:
    stub = tmp_path / "slow.py"
    stub.write_text("import time\ntime.sleep(10)\n")
    start = time.monotonic()
    result = run_hook("{}", script=stub)
    assert result.returncode == 0 and result.stdout == ""
    assert time.monotonic() - start < 8


# ---------------------------------------------- Final review: fix pass (RED first)

MORE_SECRET_FORMS = [
    ("clientSecret=abc123XYZ", "abc123XYZ"),
    ('accessToken: "tok_live_abcdef"', "tok_live_abcdef"),
    ("dbpassword=hunter2", "hunter2"),
    ("userPassword=hunter2", "hunter2"),
    ("DB_PASS=abc12", "abc12"),
    ("pass=hunter2", "hunter2"),
    ("private_key=abc12", "abc12"),
    ("SECRET_KEY=django-insecure-a!b@c#d$", "django-insecure"),
    ("AWS_SECRET_ACCESS_KEY=abcd/efgh+ijkl", "abcd/efgh"),
    ('password = "my pass phrase"', "pass phrase"),
    ("Authorization: Basic dXNlcjpwYXNzd29yZA==", "dXNlcjpwYXNzd29yZA"),
    ("postgres://u:p@ss@host/db", "ss@host"),
]


@pytest.mark.parametrize(("text", "lacks"), MORE_SECRET_FORMS)
def test_mask_hides_more_secret_forms(coach: ModuleType, text: str, lacks: str) -> None:
    out = coach.mask(text)
    assert lacks not in out
    assert coach.mask(out) == out


@pytest.mark.parametrize("sep", [" ", " ", "\u0085"])
def test_prompt_with_unicode_line_separator_can_be_reviewed(
    coach: ModuleType, home: Path, sep: str
) -> None:
    turn_on(home)
    result = coach.capture(payload(f"please update the logbook{sep}for today now"))
    assert result is not None
    assert coach.add_entry(entry(result[0])) == result[0]
    assert "Prompts logged: 1" in coach.status()


def test_add_after_off_writes_nothing(coach: ModuleType, home: Path) -> None:
    prompt_id = captured(coach, home)
    coach.set_enabled(False)
    with pytest.raises(coach.EntryError):
        coach.add_entry(entry(prompt_id), now=NOV2)
    assert not list(home.glob("*.md"))


def test_add_when_never_enabled_creates_nothing(coach: ModuleType, home: Path) -> None:
    with pytest.raises(coach.EntryError):
        coach.add_entry(entry("a1b2c3d4"))
    assert not home.exists()


def test_template_files_hold_no_company_names() -> None:
    root = Path(__file__).resolve().parents[1]
    pattern = re.compile(r"DA-(?!1234)\d+|da-(?:privis|pricelist)")
    files = [
        root / "CLAUDE/skills/prompt-coach/SKILL.md",
        root / "CLAUDE/skills/prompt-coach/coach.py",
        root / "CLAUDE/linux-wsl/hooks/prompt-coach-capture.sh",
        root / "docs/superpowers/specs/2026-11-02-prompt-coach-design.md",
        root / "docs/superpowers/plans/2026-11-02-prompt-coach.md",
        Path(__file__),
    ]
    found = {f.name: pattern.findall(f.read_text()) for f in files}
    assert {name: hits for name, hits in found.items() if hits} == {}
