"""Tests of the umbrella-review skill: classification and the sensitive-file guarantee.

All repos are throwaway ones built in a temp folder; no real data is used.
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "CLAUDE/skills/umbrella-review/scripts"
CANARIES = [
    "CANARY_ENV_SECRET",
    "CANARY_TOKEN_JSON",
    "CANARY_NODE_MODULE",
    "CANARY_VENV",
    "CANARY_DIFF_BODY",
    "CANARY_STASH_BODY",
]


def load(name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def run(repo: Path, *args: str) -> str:
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "me@example.com",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "me@example.com",
    }
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    ).stdout


@pytest.fixture
def umbrella(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setattr(Path, "home", lambda: tmp_path / "home")
    root = tmp_path / "umbrella"
    repo = root / "demo"
    repo.mkdir(parents=True)
    run(repo, "init", "-b", "master")
    run(repo, "config", "user.email", "me@example.com")
    (repo / "README.md").write_text("# Demo\n\nVersion: 1.0.0\n")
    (repo / "CLAUDE.md").write_text("# Demo\n")
    (repo / "pyproject.toml").write_text(
        '[project]\nname = "demo"\nversion = "1.0.0"\n'
    )
    (repo / ".env").write_text("TOKEN=CANARY_ENV_SECRET\n")
    (repo / "token.json").write_text('{"k": "CANARY_TOKEN_JSON"}')
    (repo / "node_modules/x").mkdir(parents=True)
    (repo / "node_modules/x/index.js").write_text("// CANARY_NODE_MODULE\n")
    (repo / ".venv/lib").mkdir(parents=True)
    (repo / ".venv/lib/a.py").write_text("# CANARY_VENV\n")
    run(repo, "add", "-f", ".")
    run(repo, "commit", "-m", "initial")
    run(repo, "branch", "dev")
    run(repo, "checkout", "-b", "feat/DA-1-old-work")
    (repo / "app.py").write_text("x = 'CANARY_DIFF_BODY'  # TODO fix\n")
    run(repo, "add", "app.py")
    run(repo, "commit", "-m", "feat: add app")
    (repo / "app.py").write_text("x = 'CANARY_STASH_BODY'\n")
    run(repo, "stash", "push", "-m", "wip")
    (repo / ".env.local").write_text("TOKEN=CANARY_ENV_SECRET\n")
    return root


def collect(umbrella: Path, tmp_path: Path) -> dict[str, Any]:
    mod = load("collect")
    out = tmp_path / "c.json"
    sys.argv = ["collect", str(umbrella), "--out", str(out)]
    assert mod.main() == 0
    data: dict[str, Any] = json.loads(out.read_text())
    return data


def test_no_canary_in_json_or_report(umbrella: Path, tmp_path: Path) -> None:
    doc = collect(umbrella, tmp_path)
    render = load("render")
    report, _ = render.render(doc, {"decisions": {}, "seen": {}})
    blob = json.dumps(doc) + report
    for canary in CANARIES:
        assert canary not in blob, canary
    assert ".env.local" not in blob
    assert doc["repos"][0]["dirty"]["hidden_secret_like"] >= 1


def test_files_opened_are_allow_listed(umbrella: Path, tmp_path: Path) -> None:
    doc = collect(umbrella, tmp_path)
    mod = load("collect")
    assert doc["files_opened"]
    for path in doc["files_opened"]:
        assert Path(path).name in mod.ALLOWED_READ
        assert not any(p in mod.SKIP_DIRS for p in Path(path).parts)


def test_git_guard_refuses_content_commands(umbrella: Path) -> None:
    mod = load("collect")
    repo = umbrella / "demo"
    for args in (
        ("show", "HEAD"),
        ("log", "-p"),
        ("diff", "HEAD~1"),
        ("stash", "show", "-p"),
        ("push",),
    ):
        with pytest.raises(ValueError):
            mod.git(repo, *args)


def test_every_git_call_is_allow_listed(
    umbrella: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    mod = load("collect")
    calls: list[list[str]] = []
    real = subprocess.run

    def spy(
        cmd: list[str], *a: object, **k: object
    ) -> subprocess.CompletedProcess[str]:
        if cmd and cmd[0] == "git":
            calls.append(cmd)
        return real(cmd, *a, **k)  # type: ignore[call-overload,no-any-return]

    monkeypatch.setattr(mod.subprocess, "run", spy)
    out = tmp_path / "c.json"
    monkeypatch.setattr(sys, "argv", ["collect", str(umbrella), "--out", str(out)])
    mod.main()
    assert calls
    for cmd in calls:
        sub = cmd[cmd.index("-c") + 2] if "-c" in cmd else cmd[3]
        assert sub in mod.ALLOWED_GIT, cmd


def test_unmerged_branch_is_flagged_and_stash_listed(
    umbrella: Path, tmp_path: Path
) -> None:
    doc = collect(umbrella, tmp_path)
    repo = doc["repos"][0]
    branch = next(b for b in repo["branches"] if b["name"] == "feat/DA-1-old-work")
    assert branch["class"] in ("local_only", "pushed_no_pr")
    assert branch["ticket"] == "DA-1"
    assert repo["stashes"]
    assert repo["roles"]["integration"] == "dev"
    assert repo["fetch_age_days"] is None or repo["fetch_age_days"] >= 0


def test_report_goes_outside_git_work_tree(umbrella: Path, tmp_path: Path) -> None:
    doc = collect(umbrella, tmp_path)
    render = load("render")
    inside = umbrella / "demo" / "knowledge"
    chosen = render.pick_out_dir(umbrella / "demo", str(inside))
    assert not str(chosen).startswith(str(umbrella / "demo"))
    assert doc["repos"]


def test_decision_is_persisted(tmp_path: Path) -> None:
    render = load("render")
    state_dir = tmp_path / "state"
    sys.argv = [
        "render",
        "decide",
        str(state_dir),
        "demo",
        "feat/x",
        "waiting",
        "user testing",
    ]
    assert render.main() == 0
    assert (
        render.load_state(state_dir)["decisions"]["demo::feat/x"]["status"] == "waiting"
    )


@pytest.mark.parametrize(
    "line,version",
    [
        ("Version: 1.7.0 · Updated: 2026-11-13", "1.7.0"),
        ("**Version:** 1.7.0", "1.7.0"),
        ("> Version: v2.0.1-sit | x", "2.0.1-sit"),
    ],
)
def test_version_line_formats(line: str, version: str) -> None:
    match = load("collect").VERSION_RE.search(line)
    assert match and match.group(1) == version
