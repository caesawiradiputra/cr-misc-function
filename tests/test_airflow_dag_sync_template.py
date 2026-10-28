"""Tests of the Airflow DAG sync template (workflow plus scripts) against throwaway git repos."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

TEMPLATE = (
    Path(__file__).resolve().parents[1] / "templates/github-workflows/airflow-dag-sync"
)
WORKFLOW = TEMPLATE / "sync-dags.yml"
SYNC = TEMPLATE / "scripts/sync_dags.sh"
PUBLISH = TEMPLATE / "scripts/publish_dags.sh"

EXECUTOR = "demo_dag_executor.py"
UTILS = "demo_dag_utils"
SLUG = "demo-dag"
DAG_ENV = {"DAG_SLUG": SLUG, "DAG_EXECUTOR": EXECUTOR, "DAG_UTILS": UTILS}

pytestmark = pytest.mark.skipif(
    shutil.which("bash") is None or shutil.which("git") is None,
    reason="needs bash and git",
)


def run(
    cmd: list[str],
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=cwd,
        env={**os.environ, **(env or {})},
        capture_output=True,
        text=True,
        check=check,
    )


def git(cwd: Path, *args: str) -> str:
    return run(["git", *args], cwd=cwd).stdout.strip()


@pytest.fixture
def source(tmp_path: Path) -> Path:
    src = tmp_path / "source"
    (src / "dags" / UTILS / "__pycache__").mkdir(parents=True)
    (src / "dags" / EXECUTOR).write_text("# executor v1\n")
    (src / "dags" / UTILS / "config.py").write_text("# config v1\n")
    (src / "dags" / UTILS / "__pycache__" / "config.cpython-311.pyc").write_bytes(b"x")
    (src / "dags" / "unrelated_other_dag.py").write_text("# not ours\n")
    return src


@pytest.fixture
def deployment(tmp_path: Path) -> Path:
    dep = tmp_path / "deploy"
    (dep / "airflow" / "dags" / UTILS).mkdir(parents=True)
    (dep / "airflow" / "dags" / UTILS / "stale.py").write_text("# stale\n")
    (dep / "airflow" / "dags" / "other_team_dag.py").write_text("# other team\n")
    (dep / "airflow" / "dags" / "utils").mkdir()
    (dep / "airflow" / "dags" / "utils" / "shared.py").write_text("# shared\n")
    return dep


def sync(source: Path, dest: Path, **env: str) -> subprocess.CompletedProcess[str]:
    return run(
        ["bash", str(SYNC), str(source), str(dest)],
        env={**DAG_ENV, **env},
        check=False,
    )


def test_sync_copies_only_the_named_files_and_replaces_the_utils_folder(
    source: Path, deployment: Path
) -> None:
    result = sync(source, deployment)
    assert result.returncode == 0, result.stderr
    dags = deployment / "airflow" / "dags"
    assert (dags / EXECUTOR).read_text() == "# executor v1\n"
    assert (dags / UTILS / "config.py").read_text() == "# config v1\n"
    assert not (dags / UTILS / "stale.py").exists()
    assert not (dags / UTILS / "__pycache__").exists()
    assert (dags / "other_team_dag.py").exists()
    assert (dags / "utils" / "shared.py").exists()
    assert not (dags / "unrelated_other_dag.py").exists()


def test_sync_honours_a_custom_destination_folder(source: Path, tmp_path: Path) -> None:
    dep = tmp_path / "dep2"
    (dep / "orchestration" / "dags").mkdir(parents=True)
    result = sync(source, dep, DAG_DEST_DIR="orchestration/dags")
    assert result.returncode == 0, result.stderr
    assert (dep / "orchestration" / "dags" / EXECUTOR).exists()


def test_sync_refuses_a_destination_that_is_not_a_deployment_checkout(
    source: Path, tmp_path: Path
) -> None:
    assert sync(source, tmp_path / "empty").returncode == 3


def test_sync_fails_when_the_source_files_are_missing(
    tmp_path: Path, deployment: Path
) -> None:
    assert sync(tmp_path / "nothing", deployment).returncode == 2


def test_sync_requires_the_dag_names(source: Path, deployment: Path) -> None:
    result = run(["bash", str(SYNC), str(source), str(deployment)], check=False)
    assert result.returncode != 0 and "DAG_EXECUTOR" in result.stderr


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("DAG_UTILS", ".."),
        ("DAG_UTILS", "a/b"),
        ("DAG_UTILS", ""),
        ("DAG_UTILS", "x y"),
        ("DAG_EXECUTOR", "../evil.py"),
        ("DAG_EXECUTOR", "no_extension"),
        ("DAG_DEST_DIR", "../outside"),
        ("DAG_DEST_DIR", "/abs/path"),
    ],
)
def test_sync_rejects_unsafe_names_before_removing_anything(
    source: Path, deployment: Path, name: str, value: str
) -> None:
    result = sync(source, deployment, **{name: value})
    assert result.returncode != 0
    assert value == "" or f"bad {name}" in result.stderr
    assert (deployment / "airflow" / "dags" / UTILS / "stale.py").exists()


@pytest.fixture
def remote(tmp_path: Path, deployment: Path) -> tuple[Path, Path]:
    """A bare 'GitHub' with master and airflow-dev, and a working clone of it."""
    bare = tmp_path / "remote.git"
    run(["git", "init", "--bare", "-b", "master", str(bare)])
    seed = tmp_path / "seed"
    run(["git", "clone", str(bare), str(seed)])
    git(seed, "config", "user.email", "t@example.com")
    git(seed, "config", "user.name", "t")
    (seed / "airflow" / "dags").mkdir(parents=True)
    (seed / "airflow" / "dags" / "other_team_dag.py").write_text("# other team\n")
    git(seed, "add", "-A")
    git(seed, "commit", "-m", "seed")
    git(seed, "push", "origin", "master")
    git(seed, "push", "origin", "master:airflow-dev")
    clone = tmp_path / "clone"
    run(["git", "clone", str(bare), str(clone)])
    return bare, clone


def publish(
    source: Path,
    clone: Path,
    mode: str,
    base: str,
    sha: str = "abcdef1234567",
    gh: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    env = {
        **DAG_ENV,
        "GIT_USER_NAME": "bot",
        "GIT_USER_EMAIL": "bot@example.com",
        "SOURCE_REPO": "source-repo",
    }
    if gh:
        env["GH_BIN"] = str(gh)
    return run(
        ["bash", str(PUBLISH), str(source), str(clone), mode, base, sha], env=env
    )


def commit_count(bare: Path, branch: str) -> int:
    return int(run(["git", "rev-list", "--count", branch], cwd=bare).stdout)


def test_direct_publish_pushes_to_the_base_branch_and_a_rerun_pushes_nothing(
    source: Path, remote: tuple[Path, Path]
) -> None:
    bare, clone = remote
    before = commit_count(bare, "airflow-dev")
    publish(source, clone, "direct", "airflow-dev")
    assert commit_count(bare, "airflow-dev") == before + 1
    shown = run(
        ["git", "show", f"airflow-dev:airflow/dags/{EXECUTOR}"], cwd=bare
    ).stdout
    assert shown == "# executor v1\n"
    message = run(["git", "log", "-1", "--format=%s", "airflow-dev"], cwd=bare).stdout
    assert "abcdef1" in message and SLUG in message and "source-repo" in message
    assert commit_count(bare, "master") == 1
    publish(source, clone, "direct", "airflow-dev")
    assert commit_count(bare, "airflow-dev") == before + 1


def test_direct_publish_rebases_over_a_concurrent_push(
    source: Path, remote: tuple[Path, Path], tmp_path: Path
) -> None:
    bare, clone = remote
    other = tmp_path / "other"
    run(["git", "clone", "-b", "airflow-dev", str(bare), str(other)])
    git(other, "config", "user.email", "o@example.com")
    git(other, "config", "user.name", "o")
    (other / "airflow" / "dags" / "another.py").write_text("# another team\n")
    git(other, "add", "-A")
    git(other, "commit", "-m", "other team push")
    git(other, "push", "origin", "airflow-dev")
    publish(source, clone, "direct", "airflow-dev")
    listing = run(
        ["git", "ls-tree", "-r", "--name-only", "airflow-dev"], cwd=bare
    ).stdout
    assert "airflow/dags/another.py" in listing
    assert f"airflow/dags/{EXECUTOR}" in listing


def make_gh_stub(tmp_path: Path, existing_pr: str = "") -> tuple[Path, Path]:
    log = tmp_path / "gh.log"
    stub = tmp_path / "gh"
    stub.write_text(
        "#!/usr/bin/env bash\n"
        f'echo "$@" >> "{log}"\n'
        f'if [ "$1 $2" = "pr list" ]; then echo "{existing_pr}"; fi\n'
    )
    stub.chmod(0o755)
    return stub, log


def test_pr_mode_pushes_a_sync_branch_and_opens_one_pr(
    source: Path, remote: tuple[Path, Path], tmp_path: Path
) -> None:
    bare, clone = remote
    stub, log = make_gh_stub(tmp_path)
    publish(source, clone, "pr", "master", gh=stub)
    assert f"sync/{SLUG}" in run(["git", "branch", "--list"], cwd=bare).stdout
    assert commit_count(bare, "master") == 1
    calls = log.read_text()
    assert "pr create" in calls and "--base master" in calls


def test_pr_mode_reuses_an_open_pr_and_updates_the_same_branch(
    source: Path, remote: tuple[Path, Path], tmp_path: Path
) -> None:
    bare, clone = remote
    stub, log = make_gh_stub(tmp_path, existing_pr="42")
    publish(source, clone, "pr", "master", gh=stub)
    (source / "dags" / EXECUTOR).write_text("# executor v2\n")
    publish(source, clone, "pr", "master", sha="1234567abcdef", gh=stub)
    branches = run(["git", "branch", "--list", "sync/*"], cwd=bare).stdout.split()
    assert branches == [f"sync/{SLUG}"]
    shown = run(
        ["git", "show", f"sync/{SLUG}:airflow/dags/{EXECUTOR}"], cwd=bare
    ).stdout
    assert shown == "# executor v2\n"
    assert "pr create" not in log.read_text()


def test_pr_mode_does_nothing_when_the_open_pr_branch_already_has_these_files(
    source: Path, remote: tuple[Path, Path], tmp_path: Path
) -> None:
    bare, clone = remote
    stub, log = make_gh_stub(tmp_path, existing_pr="42")
    publish(source, clone, "pr", "master", gh=stub)
    tip = run(["git", "rev-parse", f"sync/{SLUG}"], cwd=bare).stdout
    out = publish(source, clone, "pr", "master", sha="1234567abcdef", gh=stub).stdout
    assert "No changes to publish" in out and "#42" in out
    assert run(["git", "rev-parse", f"sync/{SLUG}"], cwd=bare).stdout == tip
    assert "pr create" not in log.read_text()


def test_pr_mode_still_opens_a_pr_when_none_is_open_for_the_same_files(
    source: Path, remote: tuple[Path, Path], tmp_path: Path
) -> None:
    bare, clone = remote
    stub, log = make_gh_stub(tmp_path)  # no open PR
    publish(source, clone, "pr", "master", gh=stub)
    publish(source, clone, "pr", "master", sha="1234567abcdef", gh=stub)
    assert log.read_text().count("pr create") == 2


def test_publish_rejects_an_unknown_mode_and_a_bad_slug(
    source: Path, remote: tuple[Path, Path]
) -> None:
    _, clone = remote
    args = [str(source), str(clone), "force", "master", "abc"]
    assert run(["bash", str(PUBLISH), *args], env=DAG_ENV, check=False).returncode == 2
    args[2] = "direct"
    bad = {**DAG_ENV, "DAG_SLUG": "Bad Slug"}
    assert run(["bash", str(PUBLISH), *args], env=bad, check=False).returncode == 2


def test_publish_lists_the_copied_files(
    source: Path, remote: tuple[Path, Path]
) -> None:
    _, clone = remote
    out = publish(source, clone, "direct", "airflow-dev").stdout
    assert EXECUTOR in out and "config.py" in out


# The workflow is checked as text so the tests need no YAML library.
TEXT = WORKFLOW.read_text()


def test_workflow_triggers_and_read_only_token() -> None:
    assert "branches: [master, dev, sit]" in TEXT
    assert "workflow_dispatch:" in TEXT
    assert '- "dags/**"' in TEXT
    assert re.search(r"^permissions:\n  contents: read$", TEXT, re.M)


def test_write_job_uses_the_scoped_environment_and_the_branch_allowlist() -> None:
    assert re.search(r"^    environment: airflow-sync$", TEXT, re.M)
    assert (
        "if: github.ref_name == 'master' || github.ref_name == 'dev' "
        "|| github.ref_name == 'sit'"
    ) in TEXT


def test_dry_run_job_has_no_environment_and_no_secret() -> None:
    dry = TEXT[TEXT.index("  dry-run:") :]
    assert "environment:" not in dry and "secrets." not in dry


def test_no_expression_is_interpolated_into_run_scripts() -> None:
    for block in re.findall(r"run: \|\n((?:          .*\n?)+)", TEXT):
        assert "${{" not in block


def test_every_run_step_uses_bash_and_checkout_drops_credentials() -> None:
    assert TEXT.count("        shell: bash") == TEXT.count("        run: ")
    assert TEXT.count("persist-credentials: false") == TEXT.count(
        "uses: actions/checkout@"
    )


def test_template_has_todos_and_no_company_values() -> None:
    assert TEXT.count("# TODO") == 6
    for path in (WORKFLOW, SYNC, PUBLISH):
        assert not re.search(r"bfi|aliyun", path.read_text(), re.I), path.name


APP_TEXT = (TEMPLATE / "sync-dags.github-app.yml").read_text()


def test_pat_variant_reads_the_organization_or_environment_secret_by_one_name() -> None:
    assert TEXT.count("secrets.DA_AIRFLOW_SYNC_TOKEN") == 2
    assert "DEPLOY_REPO_TOKEN" not in TEXT


def test_app_variant_mints_a_scoped_token_and_stores_no_pat() -> None:
    assert "secrets.DA_AIRFLOW_SYNC_TOKEN" not in APP_TEXT
    assert "uses: actions/create-github-app-token@" in APP_TEXT
    assert "repositories: ${{ steps.target.outputs.repo }}" in APP_TEXT
    assert "permission-contents: write" in APP_TEXT
    assert "permission-pull-requests: write" in APP_TEXT
    assert APP_TEXT.count("${{ steps.app-token.outputs.token }}") == 2
    assert re.search(r"^    environment: airflow-sync$", APP_TEXT, re.M)


def test_app_variant_reads_client_id_and_key_as_secrets() -> None:
    assert "secrets.DA_AIRFLOW_SYNC_APP_CLIENT_ID" in APP_TEXT
    assert "secrets.DA_AIRFLOW_SYNC_APP_PRIVATE_KEY" in APP_TEXT
    assert "vars." not in APP_TEXT


def test_app_variant_creates_the_token_after_resolving_the_target_and_before_cloning() -> (
    None
):
    order = [
        APP_TEXT.index("- name: Resolve the target branch and mode"),
        APP_TEXT.index("- name: Create the deployment repository token"),
        APP_TEXT.index("- name: Clone the deployment repository"),
    ]
    assert order == sorted(order)


def test_app_variant_keeps_the_same_dry_run_job_and_env_block() -> None:
    tail = "  dry-run:"
    assert TEXT[TEXT.index(tail) :] == APP_TEXT[APP_TEXT.index(tail) :]
    env_block = re.compile(r"^env:\n(?:  .*\n)+", re.M)
    first, second = env_block.search(TEXT), env_block.search(APP_TEXT)
    assert first and second and first.group() == second.group()


def test_app_variant_has_no_interpolation_in_run_scripts_or_company_values() -> None:
    for block in re.findall(r"run: \|\n((?:          .*\n?)+)", APP_TEXT):
        assert "${{" not in block
    assert not re.search(r"bfi|aliyun", APP_TEXT, re.I)
