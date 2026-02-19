#!/usr/bin/env python3
"""
Enterprise Environment Pollution Detector
for Conda + Poetry hybrid setup.

Features:
    - Detect Conda-layer pollution
    - Auto-exclude Conda-core Python dependencies
    - Detect active interpreter pollution
    - Scan project imports
    - Suggest poetry add only for truly required packages
    - CI-ready exit code
"""

from __future__ import annotations

import ast
import importlib.metadata as metadata
import json
import re
import subprocess
import sys
import tomllib
from pathlib import Path

# --------------------------------------------------
# Utilities
# --------------------------------------------------


def normalize(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def run_command(cmd: list[str]) -> str:
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


# --------------------------------------------------
# Project Metadata
# --------------------------------------------------


def get_project_name() -> str:
    pyproject = Path("pyproject.toml")
    if not pyproject.exists():
        return ""

    with pyproject.open("rb") as f:
        data = tomllib.load(f)

    return normalize(data.get("project", {}).get("name", ""))


def get_locked_packages() -> set[str]:
    lock_file = Path("poetry.lock")
    if not lock_file.exists():
        raise FileNotFoundError("❌ poetry.lock not found.")

    locked = set()
    with lock_file.open("r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("name ="):
                name = line.split("=", 1)[1].strip().strip('"')
                locked.add(normalize(name))

    return locked


# --------------------------------------------------
# Conda Layer
# --------------------------------------------------


def get_conda_python_packages() -> dict[str, str]:
    python_dists = {}

    for dist in metadata.distributions():
        name = dist.metadata.get("Name")
        if not name:
            continue
        python_dists[normalize(name)] = dist.version

    try:
        conda_json = run_command(["conda", "list", "--json"])
    except Exception:
        return {}

    conda_data = json.loads(conda_json)
    conda_names = {normalize(pkg["name"]) for pkg in conda_data}

    return {
        name: python_dists[name]
        for name in conda_names
        if name in python_dists
    }


# --------------------------------------------------
# Detect Conda-Core Python Dependencies
# --------------------------------------------------


def get_conda_core_dependencies() -> set[str]:
    """
    Identify Python packages required by Conda itself.
    """

    try:
        result = subprocess.run(
            ["pipdeptree", "--json"],
            capture_output=True,
            text=True,
            check=True,
        )
    except Exception:
        return set()

    tree = json.loads(result.stdout)

    graph = {}
    for node in tree:
        name = normalize(node["package"]["key"])
        deps = {normalize(dep["key"]) for dep in node.get("dependencies", [])}
        graph[name] = deps

    conda_core_roots = {"conda", "conda-libmamba-solver", "libmambapy"}

    core_deps = set()
    stack = list(conda_core_roots)

    while stack:
        pkg = stack.pop()
        for dep in graph.get(pkg, set()):
            if dep not in core_deps:
                core_deps.add(dep)
                stack.append(dep)

    return core_deps


# --------------------------------------------------
# Active Interpreter Layer
# --------------------------------------------------


def get_active_python_packages() -> dict[str, str]:
    pkgs = {}

    for dist in metadata.distributions():
        name = dist.metadata.get("Name")
        if not name:
            continue
        pkgs[normalize(name)] = dist.version

    return pkgs


# --------------------------------------------------
# Project Import Scanner
# --------------------------------------------------


def get_project_imports() -> set[str]:
    imports = set()

    for py_file in Path(".").rglob("*.py"):
        if ".venv" in str(py_file):
            continue

        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8"))
        except Exception:
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(normalize(alias.name.split(".")[0]))

            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.add(normalize(node.module.split(".")[0]))

    return imports


# --------------------------------------------------
# Ignore Minimal Toolchain
# --------------------------------------------------


IGNORED = {
    "pip",
    "setuptools",
    "wheel",
    "packaging",
}


# --------------------------------------------------
# Reporting
# --------------------------------------------------


def report_layer(title: str,
                 pollution: set[str],
                 version_map: dict[str, str],
                 project_imports: set[str]) -> bool:

    print(f"\n🔍 {title}")

    if not pollution:
        print("   ✓ Clean")
        return False

    print("   ⚠ Undeclared packages detected:\n")

    for pkg in sorted(pollution):
        marker = " (USED IN PROJECT)" if pkg in project_imports else ""
        print(f"     - {pkg}=={version_map[pkg]}{marker}")

    needed = pollution & project_imports

    if needed:
        print("\n   Suggested poetry add commands:\n")
        for pkg in sorted(needed):
            print(f"     poetry add {pkg}")

    return True


# --------------------------------------------------
# Main
# --------------------------------------------------


def main() -> None:
    print("Enterprise Environment Pollution Detector\n")

    locked = get_locked_packages()
    project_name = get_project_name()
    project_imports = get_project_imports()

    polluted = False

    # ---- Conda Layer ----
    conda_pkgs = get_conda_python_packages()
    conda_core_deps = get_conda_core_dependencies()

    conda_pollution = (
        set(conda_pkgs)
        - locked
        - {project_name}
        - IGNORED
        - conda_core_deps
    )

    polluted |= report_layer(
        "Conda Layer",
        conda_pollution,
        conda_pkgs,
        project_imports
    )

    # ---- Active Interpreter Layer ----
    active_pkgs = get_active_python_packages()

    active_pollution = (
        set(active_pkgs)
        - locked
        - {project_name}
        - IGNORED
    )

    polluted |= report_layer(
        f"Active Interpreter Layer ({sys.executable})",
        active_pollution,
        active_pkgs,
        project_imports
    )

    if polluted:
        print("\n❌ Environment pollution detected.")
        sys.exit(1)

    print("\n✅ Environment is clean.")


if __name__ == "__main__":
    main()
