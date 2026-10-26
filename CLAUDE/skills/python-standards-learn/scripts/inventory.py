#!/usr/bin/env python3
"""Read-only inventory of Python repos: facts for the python-standards-learn skill.

Usage:
    python3 inventory.py [ROOT ...] [--max-depth N] [--out FILE]

Finds directories holding a pyproject.toml, Dockerfile or requirements.txt (that are
also git repos or sit inside one), and prints one JSON object per repo with facts about
layout, config/secret handling, tests, lint/typing, Docker and CI. Suggests a project type
with the signals that led to it.

Read-only by design: it never runs the repos' code, never reads .env or credential file
contents (only whether they exist or are tracked), and never writes inside a repo.
Runs on Python 3.9+ (stdlib only).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

SKIP_DIRS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    "legacy",
    "scratch",
    "temp",
    "logs",
    ".mypy_cache",
    ".ruff_cache",
    ".pytest_cache",
    "site-packages",
}
MARKERS = ("pyproject.toml", "Dockerfile", "requirements.txt")
SECRET_NAME_RE = re.compile(
    r"(\.env($|\.)|service[_-]?account.*\.json|credentials.*\.json|.*\.pem$|.*\.key$|id_rsa)",
    re.IGNORECASE,
)


def read(path: Path, limit: int = 200_000) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")[:limit]
    except OSError:
        return ""


def git(repo: Path, *args: str) -> str:
    try:
        out = subprocess.run(
            ["git", "-C", str(repo), *args],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        return out.stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        return ""


def find_repos(roots: list[Path], max_depth: int) -> list[Path]:
    found: list[Path] = []

    def walk(d: Path, depth: int) -> None:
        if depth > max_depth:
            return
        try:
            entries = list(d.iterdir())
        except OSError:
            return
        names = {e.name for e in entries}
        if any(m in names for m in MARKERS):
            found.append(d)
            return  # a project is a leaf: its subfolders belong to it, not separate repos
        for e in entries:
            if e.is_dir() and e.name not in SKIP_DIRS and not e.name.startswith("."):
                walk(e, depth + 1)

    for r in roots:
        walk(r, 0)
    return sorted(set(found))


def dep_names(text: str) -> list[str]:
    """Package names from pyproject [project] dependencies and requirements-style lines."""
    names: list[str] = []
    m = re.search(r"^dependencies\s*=\s*\[(.*?)\]", text, re.DOTALL | re.MULTILINE)
    block = m.group(1) if m else ""
    for item in re.findall(r"\"([^\"]+)\"|'([^']+)'", block):
        spec = item[0] or item[1]
        n = re.split(r"[\s\[<>=!~(;]", spec, maxsplit=1)[0].strip().lower()
        if n:
            names.append(n)
    return sorted(set(names))


def req_names(text: str) -> list[str]:
    out = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith(("#", "-")):
            continue
        n = re.split(r"[\s\[<>=!~(;@]", line, maxsplit=1)[0].strip().lower()
        if n:
            out.append(n)
    return sorted(set(out))


def dockerfile_facts(path: Path) -> dict:
    t = read(path)
    froms = re.findall(r"^FROM\s+(\S+)(?:\s+AS\s+(\S+))?", t, re.MULTILINE | re.IGNORECASE)
    last_user = re.findall(r"^USER\s+(\S+)", t, re.MULTILINE | re.IGNORECASE)
    cmd = re.findall(r"^(?:CMD|ENTRYPOINT)\s+(.+)$", t, re.MULTILINE | re.IGNORECASE)
    return {
        "file": path.name,
        "from": [f[0] for f in froms],
        "multi_stage": len(froms) > 1,
        "base_pinned_by_digest": all("@sha256:" in f[0] for f in froms)
        if froms
        else False,
        "base_floating_tag": any(
            ("@sha256:" not in f[0])
            and f[0].lower() != "scratch"
            and f[0] not in {x[1] for x in froms if x[1]}
            for f in froms
        ),
        "user": last_user[-1] if last_user else None,
        "runs_as_root": not last_user or last_user[-1] in {"root", "0"},
        "expose": re.findall(r"^EXPOSE\s+(.+)$", t, re.MULTILINE | re.IGNORECASE),
        "healthcheck": bool(re.search(r"^HEALTHCHECK\b", t, re.MULTILINE | re.IGNORECASE)),
        "cmd_entrypoint": [c[:120] for c in cmd][-2:],
        "installs_with": [
            tool
            for tool, pat in (
                ("uv", r"\buv\b"),
                ("poetry", r"\bpoetry\b"),
                ("pip", r"\bpip3?\s+install\b"),
                ("conda", r"\bconda\b"),
            )
            if re.search(pat, t)
        ],
        "uv_version_pinned": bool(re.search(r"uv==\d", t)),
        "copies_env_file": bool(re.search(r"^(COPY|ADD)\s+.*\.env\b", t, re.MULTILINE | re.IGNORECASE)),
        "apt_install": bool(re.search(r"apt(-get)?\s+install", t)),
    }


def workflow_facts(repo: Path) -> list[dict]:
    out = []
    wf_dir = repo / ".github" / "workflows"
    if not wf_dir.is_dir():
        return out
    for f in sorted(wf_dir.glob("*.y*ml")):
        t = read(f)
        out.append(
            {
                "file": f.name,
                "on_pull_request": bool(re.search(r"^\s*pull_request\b", t, re.MULTILINE)),
                "on_push": bool(re.search(r"^\s*push\b", t, re.MULTILINE)),
                "on_dispatch": "workflow_dispatch" in t,
                "builds_docker": "docker" in t.lower() and ("build" in t.lower()),
                "provenance_false": "provenance: false" in t,
                "uses_login_action": "docker/login-action" in t,
                "has_permissions": bool(re.search(r"^permissions:", t, re.MULTILINE)),
                "has_concurrency": bool(re.search(r"^concurrency:", t, re.MULTILINE)),
                "runs_lint_or_tests": bool(re.search(r"\b(ruff|mypy|pytest)\b", t)),
            }
        )
    return out


def config_facts(repo: Path, tracked: list[str], all_text: str) -> dict:
    top = {p.name for p in repo.iterdir()} if repo.is_dir() else set()
    tracked_secrets = [
        t
        for t in tracked
        if SECRET_NAME_RE.search(Path(t).name)
        and not re.search(r"(template|example|sample)", t, re.IGNORECASE)
    ]
    return {
        "env_template_file": sorted(
            n for n in top if re.match(r"\.env\.(template|example|sample)$", n)
        ),
        "env_file_present_untracked_ok": ".env" in top,
        "tracked_secret_like_files": tracked_secrets[:10],
        "gitignore_ignores_env": bool(
            re.search(r"^\.env(\.\*|\*)?\s*$", read(repo / ".gitignore"), re.MULTILINE)
        ),
        "uses_dotenv": "dotenv" in all_text,
        "uses_pydantic_settings": "pydantic_settings" in all_text
        or "pydantic-settings" in all_text,
        "uses_os_environ": bool(re.search(r"os\.(environ|getenv)", all_text)),
        "uses_airflow_variable_or_connection": bool(
            re.search(r"airflow.*(Variable|BaseHook)", all_text)
        ),
        "has_configs_dir": any(n in top for n in ("configs", "config", "conf")),
        "has_secrets_dir_or_mount_hint": bool(
            re.search(r"/run/secrets|SECRETS_DIR|secretKeyRef", all_text)
        ),
    }


def sample_source_text(repo: Path, cap: int = 400_000) -> str:
    """Concatenate .py sources (first N bytes) for cheap pattern checks."""
    buf: list[str] = []
    size = 0
    files: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(repo):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        files += [Path(dirpath) / f for f in sorted(filenames) if f.endswith(".py")]
    for p in files:
        s = read(p, 20_000)
        buf.append(s)
        size += len(s)
        if size >= cap:
            break
    return "\n".join(buf)


def suggest_type(
    deps: set[str], facts: dict, top: set[str], src: str, name: str
) -> dict:
    """Suggest a project type. Strong signals score 2, weak ones 1; weak alone never decides."""
    score: dict[str, int] = {}
    sig: dict[str, list[str]] = {}

    def add(t: str, why: str, weight: int = 2) -> None:
        score[t] = score.get(t, 0) + weight
        sig.setdefault(t, []).append(f"{'strong' if weight > 1 else 'weak'}: {why}")

    d = " ".join(sorted(deps))
    cmds = " ".join(
        c for df in facts["dockerfiles"] for c in df["cmd_entrypoint"]
    ).lower()
    exposes = [e for df in facts["dockerfiles"] for e in df["expose"]]
    lname = name.lower()
    if "apache-airflow" in d or "dags" in top:
        add("airflow-job", "airflow dependency or dags/ dir")
    if "airflow" in lname:
        add("airflow-job", "repo name contains 'airflow'")
    if cmds and not exposes and not re.search(r"uvicorn|gunicorn|streamlit", cmds):
        add("airflow-job", "one-shot CMD/ENTRYPOINT without EXPOSE", 1)
    if "fastapi" in deps or "uvicorn" in deps:
        add("fastapi-service", "fastapi/uvicorn dependency")
    if "uvicorn" in cmds or "gunicorn" in cmds:
        add("fastapi-service", "uvicorn/gunicorn in CMD")
    if "flask" in deps:
        add("flask-service", "flask dependency")
    if "streamlit" in deps or "streamlit" in cmds:
        add("streamlit", "streamlit dependency or CMD")
    if deps & {"kafka-python", "confluent-kafka", "aiokafka"}:
        add("consumer", "kafka client dependency")
    if "consumer" in lname:
        add("consumer", "repo name contains 'consumer'")
    if re.search(r"signal\.(signal|SIGTERM)", src):
        add("consumer", "signal handling in source", 1)
    if deps & {"dbt-core", "dbt-trino"}:
        add("dbt", "dbt dependency")
    if deps & {"google-adk", "mcp", "claude-agent-sdk", "fastmcp"}:
        add("agent-mcp", "ADK/MCP/agent SDK dependency")
    if "crawler" in lname or "scraper" in lname:
        add("crawler-batch", "repo name contains crawler/scraper")
    ranked = sorted(score.items(), key=lambda kv: -kv[1])
    decided = [t for t, v in ranked if v >= 2]
    best = decided[0] if decided else "unclassified"
    tie = len(ranked) > 1 and ranked[0][1] == ranked[1][1] and ranked[0][1] >= 2
    return {
        "suggested": best,
        "types": decided or ["unclassified"],
        "needs_confirmation": best == "unclassified"
        or tie
        or len(decided) > 1
        or len(facts["dockerfiles"]) > 1,
        "signals": sig,
    }


def inventory(repo: Path) -> dict:
    top = {p.name for p in repo.iterdir()}
    pyproject = read(repo / "pyproject.toml")
    requires = re.search(r"^requires-python\s*=\s*\"([^\"]+)\"", pyproject, re.MULTILINE)
    backend = re.search(r"^build-backend\s*=\s*\"([^\"]+)\"", pyproject, re.MULTILINE)
    deps = set(dep_names(pyproject))
    for rq in sorted(repo.glob("requirements*.txt")):
        deps |= set(req_names(read(rq)))
    if "[tool.poetry.dependencies]" in pyproject:
        sect = pyproject.split("[tool.poetry.dependencies]", 1)[1].split("\n[", 1)[0]
        deps |= {
            m.lower() for m in re.findall(r"^([A-Za-z0-9_.-]+)\s*=", sect, re.MULTILINE)
        } - {"python"}

    tracked = git(repo, "ls-files").splitlines()
    src = sample_source_text(repo)

    test_files = [t for t in tracked if re.match(r"(.*/)?(test_.*|.*_test)\.py$", t)]
    dev_tools = sorted(
        {
            t
            for t in (
                "pytest",
                "mypy",
                "ruff",
                "pyrefly",
                "black",
                "flake8",
                "pylint",
                "isort",
            )
            if re.search(rf"\b{t}\b", pyproject)
        }
    )

    facts: dict = {
        "path": str(repo),
        "name": repo.name,
        "git": {
            "is_repo": bool(git(repo, "rev-parse", "--is-inside-work-tree")),
            "toplevel_is_this_dir": git(repo, "rev-parse", "--show-toplevel") == str(repo),
            "branch": git(repo, "branch", "--show-current"),
            "last_commit": git(repo, "log", "-1", "--format=%cs"),
            "commits_last_12_months": len(
                git(repo, "log", "--since=12 months ago", "--format=%h").splitlines()
            ),
            "remote": re.sub(
                r"//[^@/]+@", "//", git(repo, "remote", "get-url", "origin")
            ),
        },
        "layout": {
            "top_level": sorted(
                n for n in top if not n.startswith(".") and n not in {"__pycache__"}
            ),
            "src_layout": "src" in top,
            "app_dir": "app" in top,
            "has_main_py": "main.py" in top,
            "has_dags_dir": "dags" in top,
            "has_release_dir": "release" in top,
            "has_scratch_dir": "scratch" in top,
            "has_legacy_dir": "legacy" in top,
            "has_claude_md": "CLAUDE.md" in top,
            "has_readme": "README.md" in top,
            "has_docs_dir": "docs" in top,
        },
        "packaging": {
            "requires_python": requires.group(1) if requires else None,
            "python_version_file": read(repo / ".python-version").strip() or None,
            "build_backend": backend.group(1) if backend else None,
            "uses_uv_lock": "uv.lock" in top,
            "uses_poetry": "poetry.lock" in top or "[tool.poetry" in pyproject,
            "uses_requirements_txt": any(repo.glob("requirements*.txt")),
            "uses_conda_env": "environment.yml" in top,
            "dev_tools_declared": dev_tools,
            "dependencies": sorted(deps),
        },
        "lint_typing": {
            "ruff_toml": "ruff.toml" in top or "[tool.ruff" in pyproject,
            "mypy_ini": "mypy.ini" in top or "[tool.mypy" in pyproject,
            "pyrefly_toml": "pyrefly.toml" in top,
            "ruff_line_length": (
                re.search(r"line-length\s*=\s*(\d+)", read(repo / "ruff.toml"))
                or [None, None]
            )[1],
            "ruff_target": (
                re.search(
                    r"target-version\s*=\s*\"([^\"]+)\"", read(repo / "ruff.toml")
                )
                or [None, None]
            )[1],
            "pre_commit": ".pre-commit-config.yaml" in top,
        },
        "tests": {
            "tests_dir": any(n in top for n in ("tests", "test")),
            "test_file_count": len(test_files),
            "conftest": any(t.endswith("conftest.py") for t in tracked),
            "pytest_config": "[tool.pytest" in pyproject or "pytest.ini" in top,
        },
        "docker": {
            "dockerfiles": [
                dockerfile_facts(p) for p in sorted(repo.glob("Dockerfile*"))
            ],
            "dockerignore": ".dockerignore" in top,
            "compose": any(
                n in top for n in ("docker-compose.yml", "docker-compose.yaml")
            ),
        },
        "ci": {"workflows": workflow_facts(repo)},
        "config_secrets": config_facts(repo, tracked, src),
    }
    facts["type"] = suggest_type(deps, facts["docker"], top, src, repo.name)
    return facts


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("roots", nargs="*", default=[str(Path.home() / "repo")])
    ap.add_argument("--max-depth", type=int, default=3)
    ap.add_argument("--out", help="write JSON here instead of stdout")
    args = ap.parse_args()

    roots = [Path(r).expanduser() for r in args.roots]
    repos = find_repos(roots, args.max_depth)
    results = []
    for r in repos:
        try:
            results.append(inventory(r))
        except Exception as exc:  # keep going: one broken repo must not stop the sweep
            results.append(
                {
                    "path": str(r),
                    "name": r.name,
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )
    payload = json.dumps({"repos": results}, indent=2)
    if args.out:
        Path(args.out).write_text(payload, encoding="utf-8")
        print(f"wrote {len(results)} repos to {args.out}", file=sys.stderr)
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
