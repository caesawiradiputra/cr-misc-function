"""End-to-end test of the WSL migration backup and restore scripts on throwaway repos."""

from __future__ import annotations

import os
import shutil
import subprocess
import tarfile
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts/bash"
BACKUP = SCRIPTS / "wsl-migration-backup.sh"
RESTORE = SCRIPTS / "wsl-migration-restore.sh"

pytestmark = pytest.mark.skipif(
    shutil.which("bash") is None or shutil.which("git") is None,
    reason="needs bash and git",
)


def sh(
    *args: str | Path, cwd: Path | None = None, env: dict[str, str] | None = None
) -> str:
    merged = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
              "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t", **(env or {})}  # fmt: skip
    done = subprocess.run(
        [str(a) for a in args],
        cwd=cwd,
        env=merged,
        capture_output=True,
        text=True,
        check=False,
    )
    assert done.returncode == 0, f"{args}\n{done.stdout}\n{done.stderr}"
    return done.stdout


def git(repo: Path, *args: str) -> str:
    return sh("git", "-C", str(repo), *args)


@pytest.fixture
def world(tmp_path: Path) -> dict[str, Path]:
    home = tmp_path / "home"
    (home / ".claude/skills/demo").mkdir(parents=True)
    (home / ".claude/CLAUDE.md").write_text("rules\n")
    (home / ".claude/.credentials.json").write_text('{"token": "x"}')
    (home / ".claude/skills/demo/SKILL.md").write_text("skill\n")
    (home / ".claude/projects/-p/memory").mkdir(parents=True)
    (home / ".claude/projects/-p/memory/note.md").write_text("memory\n")
    root = home / "repo"

    bare = tmp_path / "remote.git"
    sh("git", "init", "-q", "--bare", "-b", "main", bare)
    work = root / "grp/app"
    work.parent.mkdir(parents=True)
    sh("git", "clone", "-q", bare, work)
    (work / "a.txt").write_text("one\n")
    (work / ".gitignore").write_text("scratch/\n.env\n")
    git(work, "add", "-A")
    git(work, "commit", "-qm", "base")
    git(work, "push", "-q", "origin", "main")
    git(work, "checkout", "-q", "-b", "wip-local")  # a branch the remote does not have
    (work / "b.txt").write_text("local branch\n")
    git(work, "add", "-A")
    git(work, "commit", "-qm", "local only commit")
    git(work, "checkout", "-q", "main")
    for n in (1, 2):  # two stashes: a bundle would keep only the newest
        (work / "a.txt").write_text(f"stash {n}\n")
        git(work, "stash", "push", "-qm", f"parked {n}")
    (work / "a.txt").write_text("uncommitted\n")
    (work / "new.txt").write_text("untracked\n")
    (work / "scratch").mkdir()
    (work / "scratch/notes.txt").write_text("ignored but valuable\n")
    (work / ".env").write_text("SECRET=hunter2\n")

    solo = root / "grp/solo"
    solo.mkdir()
    sh("git", "init", "-q", "-b", "main", solo)
    (solo / "s.txt").write_text("no remote\n")
    (solo / ".env").write_text("SECRET=hunter2\n")
    git(solo, "add", "s.txt")
    git(solo, "commit", "-qm", "solo")
    return {
        "home": home,
        "root": root,
        "out": tmp_path / "out",
        "new": tmp_path / "new",
    }


def backup(w: dict[str, Path], *extra: str) -> str:
    env = {"HOME": str(w["home"]), "WSL_MIGRATION_FAST": "1"}
    return sh("bash", BACKUP, "all", "--out", w["out"], "--repos-root", w["root"],
              "--claude-dir", w["home"] / ".claude", *extra, env=env)  # fmt: skip


def test_backup_classifies_repos_and_keeps_secrets_out(world: dict[str, Path]) -> None:
    backup(world)
    rows = {
        r.split("\t")[0]: r.split("\t")
        for r in (world["out"] / "MANIFEST.tsv").read_text().splitlines()[1:]
    }
    assert rows["grp/app"][4] == "at-risk" and rows["grp/solo"][4] == "local-only"
    assert (world["out"] / "repos/grp__app.bundle").exists()
    assert (world["out"] / "repos/grp__app.stash-0.patch").stat().st_size > 0
    assert (world["out"] / "repos/grp__app.stash-1.patch").stat().st_size > 0
    assert (world["out"] / "repos/grp__app.tracked.patch").stat().st_size > 0
    for archive in [
        *world["out"].glob("repos/*.tar.gz"),
        world["out"] / "claude/claude-config.tar.gz",
    ]:
        with tarfile.open(archive) as tar:
            names = tar.getnames()
        assert not any(
            n.endswith(".env") or n.endswith(".credentials.json") for n in names
        ), archive
    with tarfile.open(world["out"] / "repos/grp__app.extra.tar.gz") as tar:
        extra = tar.getnames()
    assert "scratch/notes.txt" in extra and "new.txt" in extra
    sh("bash", BACKUP, "verify", "--out", world["out"])


def test_restore_rebuilds_repos_branches_stashes_and_changes(
    world: dict[str, Path],
) -> None:
    backup(world)
    sh("bash", RESTORE, "plan", "--from", world["out"])
    sh(
        "bash",
        RESTORE,
        "claude",
        "--from",
        world["out"],
        "--claude-dir",
        world["new"] / ".claude",
    )
    assert (
        world["new"] / ".claude/projects/-p/memory/note.md"
    ).read_text() == "memory\n"
    assert not (world["new"] / ".claude/.credentials.json").exists()

    # the remote moves on to the cloned path, as it would on a new machine
    manifest = world["out"] / "MANIFEST.tsv"
    bare = world["home"].parent / "remote.git"
    lines = manifest.read_text().splitlines()
    lines = [
        ln.replace(
            git(world["root"] / "grp/app", "remote", "get-url", "origin").strip(),
            str(bare),
        )
        for ln in lines
    ]
    manifest.write_text("\n".join(lines) + "\n")

    new_root = world["new"] / "repo"
    out = sh("bash", RESTORE, "repos", "--from", world["out"], "--repos-root", new_root)
    app, solo = new_root / "grp/app", new_root / "grp/solo"
    assert (solo / "s.txt").read_text() == "no remote\n" and not (
        solo / ".env"
    ).exists()
    assert "wip-local" in git(app, "branch", "--list", "wip-local")
    assert (app / "a.txt").read_text() == "uncommitted\n"
    assert (app / "new.txt").read_text() == "untracked\n"
    assert (app / "scratch/notes.txt").read_text() == "ignored but valuable\n"
    assert not (app / ".env").exists()
    branches = git(app, "branch", "--list", "restored/stash-*")
    assert "restored/stash-0" in branches and "restored/stash-1" in branches
    assert git(app, "show", "restored/stash-1:a.txt").strip() == "stash 1"
    assert "restored as branch restored/stash-0" in out
    again = sh(
        "bash", RESTORE, "repos", "--from", world["out"], "--repos-root", new_root
    )
    assert again.count("already restored") == 2


def test_dry_run_changes_nothing(world: dict[str, Path]) -> None:
    sh(
        "bash",
        BACKUP,
        "repos",
        "--out",
        world["out"],
        "--repos-root",
        world["root"],
        "--dry-run",
    )
    assert not world["out"].exists()


def test_backup_requires_out(world: dict[str, Path]) -> None:
    done = subprocess.run(
        ["bash", str(BACKUP), "all"], capture_output=True, text=True, check=False
    )
    assert done.returncode == 1 and "--out" in done.stderr
