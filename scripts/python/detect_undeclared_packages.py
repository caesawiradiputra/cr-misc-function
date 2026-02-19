#!/usr/bin/env python3
"""
Detect manually installed packages not declared in pyproject.toml (PEP 621).

Correctly excludes:
- transitive dependencies
- tooling packages
- conda/system noise

✅ How To Validate Lockfile First:
    1️⃣ Validate pyproject syntax
       poetry check

    2️⃣ Validate lock consistency (Poetry 2+)
       poetry lock

    If lockfile is outdated → it regenerates it.
    If nothing changes → you're good.

🚀 Usage:
    Detect:
        python scripts/python/detect_undeclared_packages.py

    Suggest fix:
        python scripts/python/detect_undeclared_packages.py --auto-add

    CI fail if found:
        python scripts/python/detect_undeclared_packages.py --strict

✅ After Detecting and Updating:
    Strict install validation:
        poetry sync

    This ensures installed packages match lockfile exactly.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tomllib
from pathlib import Path

# ---------- Utilities ----------


def run(cmd: list[str]) -> str:
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def normalize(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def extract_name(req: str) -> str:
    name = re.split(r"[<>=!~\[\]; ]", req, maxsplit=1)[0]
    return normalize(name)


# ---------- Load Declared ----------


def load_declared(include_dev: bool) -> set[str]:
    pyproject = Path("pyproject.toml")

    if not pyproject.exists():
        raise FileNotFoundError(
            f"❌ pyproject.toml not found at: {pyproject.resolve()}"
        )

    with pyproject.open("rb") as f:
        data = tomllib.load(f)

    deps: set[str] = set()

    for dep in data["project"].get("dependencies", []):
        deps.add(extract_name(dep))

    if include_dev:
        optional = data["project"].get("optional-dependencies", {})
        for group in optional.values():
            for dep in group:
                deps.add(extract_name(dep))

    return deps


# ---------- Installed ----------


def get_installed() -> dict[str, str]:
    output = run([sys.executable, "-m", "pip", "freeze"])

    installed: dict[str, str] = {}

    for line in output.splitlines():
        if "==" in line:
            name, version = line.split("==", 1)
            installed[normalize(name)] = version

    return installed


# ---------- Dependency Graph ----------


def get_dependency_graph() -> dict[str, set[str]]:
    """
    Returns:
        {package: {dependencies}}
    """
    output = run([sys.executable, "-m", "pipdeptree", "--json"])
    tree = json.loads(output)

    graph: dict[str, set[str]] = {}

    for node in tree:
        name = normalize(node["package"]["key"])
        deps = {normalize(d["key"]) for d in node.get("dependencies", [])}
        graph[name] = deps

    return graph


def collect_recursive_deps(
    declared: set[str], graph: dict[str, set[str]]
) -> set[str]:
    """
    Get all recursive dependencies of declared packages.
    """
    visited: set[str] = set()
    stack = list(declared)

    while stack:
        pkg = stack.pop()
        for dep in graph.get(pkg, set()):
            if dep not in visited:
                visited.add(dep)
                stack.append(dep)

    return visited


# ---------- Filtering ----------


IGNORED_PACKAGES = {
    "pip",
    "setuptools",
    "wheel",
    "pipdeptree",
}


def main() -> None:
    """
    Detect manually installed packages not declared in pyproject.toml.

    🚀 Usage:
        Detect:
            python scripts/python/detect_undeclared_packages.py

        Suggest fix:
            python scripts/python/detect_undeclared_packages.py --auto-add

        CI fail if found:
            python scripts/python/detect_undeclared_packages.py --strict
    """
    parser = argparse.ArgumentParser(
        description="Detect manually installed but undeclared packages."
    )
    parser.add_argument("--include-dev", action="store_true")
    parser.add_argument("--auto-add", action="store_true")
    parser.add_argument("--strict", action="store_true")

    args = parser.parse_args()

    # ===== Diagnostic Info =====
    print("\n🔍 Environment Information:")
    print(f"   📁 Working Directory:    {os.getcwd()}")
    print(f"   🐍 Python Executable:    {sys.executable}")
    print(f"   📋 pyproject.toml Path:  {Path('pyproject.toml').resolve()}")
    print()

    declared = load_declared(args.include_dev)
    installed = get_installed()
    graph = get_dependency_graph()

    transitive = collect_recursive_deps(declared, graph)

    manually_installed = (
        set(installed)
        - declared
        - transitive
        - IGNORED_PACKAGES
    )

    if not manually_installed:
        print("✓ No undeclared manually installed packages found.")
        return

    print("⚠ Manually installed but undeclared packages:\n")

    for pkg in sorted(manually_installed):
        print(f"  - {pkg}=={installed[pkg]}")

    if args.auto_add:
        print("\nSuggested commands:\n")
        for pkg in sorted(manually_installed):
            print(f"poetry add {pkg}")

    if args.strict:
        sys.exit(1)


if __name__ == "__main__":
    main()
