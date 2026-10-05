#!/usr/bin/env python3
"""
Enterprise Environment Pollution Detector (Advanced)

Features:
    - External Conda env inspection
    - Distinguish pip-installed vs conda-installed
    - --explain mode
    - Optional .venv inspection
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

# --------------------------------------------------
# Utilities
# --------------------------------------------------

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


# --------------------------------------------------
# Conda Environment Lookup
# --------------------------------------------------

def get_conda_env_python(env_name: str) -> Path:
    info = json.loads(run(["conda", "info", "--json"]))
    envs = info.get("envs", [])

    for env_path in envs:
        if env_path.endswith(env_name):
            python_path = Path(env_path) / (
                "python.exe" if sys.platform == "win32" else "bin/python"
            )
            if python_path.exists():
                return python_path

    raise RuntimeError(f"Conda environment '{env_name}' not found.")


# --------------------------------------------------
# Installed Packages
# --------------------------------------------------

def get_pip_installed(python_path: Path) -> dict[str, str]:
    output = run([str(python_path), "-m", "pip", "list", "--format=json"])
    data = json.loads(output)

    return {
        normalize(pkg["name"]): pkg["version"]
        for pkg in data
    }


def get_conda_metadata(env_name: str) -> dict[str, dict]:
    output = run(["conda", "list", "-n", env_name, "--json"])
    data = json.loads(output)

    return {
        normalize(pkg["name"]): pkg
        for pkg in data
    }


# --------------------------------------------------
# Poetry Lock Parsing
# --------------------------------------------------

def parse_poetry_lock(lock_path: Path) -> set[str]:
    if not lock_path.exists():
        raise FileNotFoundError("poetry.lock not found in current directory.")

    locked = set()

    with lock_path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("name ="):
                name = line.split("=", 1)[1].strip().strip('"')
                locked.add(normalize(name))

    return locked


# --------------------------------------------------
# Reporting
# --------------------------------------------------

def explain(pkg: str,
            version: str,
            conda_meta: dict[str, dict]) -> None:

    print(f"  - {pkg}=={version}")

    if pkg in conda_meta:
        channel = conda_meta[pkg].get("channel", "unknown")
        print(f"      • Installed via conda (channel: {channel})")

        if channel == "pypi":
            print("      • Installed via pip inside conda (REAL pollution)")
        else:
            print("      • Conda-managed dependency (likely safe)")
    else:
        print("      • Not tracked by conda → pip-installed")


# --------------------------------------------------
# Severity & Color System
# --------------------------------------------------

class Severity:
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


def color(text: str, level: str) -> str:
    if not sys.stdout.isatty():
        return text

    colors = {
        Severity.INFO: "\033[36m",       # Cyan
        Severity.WARNING: "\033[33m",    # Yellow
        Severity.CRITICAL: "\033[31m",   # Red
    }
    reset = "\033[0m"

    return f"{colors.get(level, '')}{text}{reset}"


# --------------------------------------------------
# Detection Logic (Upgraded)
# --------------------------------------------------

def classify_package(pkg: str,
                     version: str,
                     conda_meta: dict[str, dict],
                     locked: set[str]) -> tuple[str, str] | tuple[None, None]:
    """
    Returns (severity, reason)
    """

    if pkg in locked:
        return None, None

    if pkg not in conda_meta:
        return Severity.CRITICAL, "pip-installed inside Conda (real pollution)"

    channel = conda_meta[pkg].get("channel", "")

    if channel == "pypi":
        return Severity.CRITICAL, "installed via pip (pypi channel)"

    return Severity.INFO, f"conda-managed dependency (channel: {channel})"


def detect_pollution(env_name: str,
                     explain_mode: bool,
                     strict_mode: bool,
                     check_venv: bool) -> None:

    print("\nEnterprise Environment Pollution Detector\n")

    python_path = get_conda_env_python(env_name)
    lock_path = Path("poetry.lock")

    print(f"🔍 Target Conda Env: {env_name}")
    print(f"🐍 Python Path: {python_path}")
    print(f"📋 poetry.lock: {lock_path.resolve()}\n")

    pip_pkgs = get_pip_installed(python_path)
    conda_meta = get_conda_metadata(env_name)
    locked = parse_poetry_lock(lock_path)

    issues = []

    for pkg, version in sorted(pip_pkgs.items()):
        if pkg in {"pip", "setuptools", "wheel"}:
            continue

        severity, reason = classify_package(pkg, version, conda_meta, locked)

        if severity:
            issues.append((severity, pkg, version, reason))

    if not issues:
        print(color("✓ Conda layer clean.\n", Severity.INFO))
    else:
        print("Detected packages:\n")

        for severity, pkg, version, reason in issues:
            label = color(f"[{severity}]", severity)
            print(f"{label} {pkg}=={version}")

            if explain_mode:
                print(f"    → {reason}")

        critical_found = any(s == Severity.CRITICAL for s, *_ in issues)

        if critical_found:
            print(color("\n❌ Critical pollution detected.\n", Severity.CRITICAL))
            if strict_mode:
                sys.exit(1)
        else:
            print(color("\n⚠ Only informational issues found.\n", Severity.WARNING))

    # --------------------------------------------------
    # Optional .venv Check
    # --------------------------------------------------

    if check_venv and Path(".venv").exists():
        print("\n🔍 Checking Poetry .venv layer\n")

        venv_python = (
            Path(".venv") / "Scripts/python.exe"
            if sys.platform == "win32"
            else Path(".venv") / "bin/python"
        )

        if venv_python.exists():
            venv_pkgs = get_pip_installed(venv_python)
            venv_undeclared = sorted(set(venv_pkgs) - locked)

            if not venv_undeclared:
                print(color("✓ .venv matches poetry.lock\n", Severity.INFO))
            else:
                print(color("⚠ .venv mismatch detected:\n", Severity.WARNING))
                for pkg in venv_undeclared:
                    print(f"  - {pkg}=={venv_pkgs[pkg]}")

                if strict_mode:
                    sys.exit(1)


# --------------------------------------------------
# CLI
# --------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Advanced Conda/Poetry environment pollution detector."
    )
    parser.add_argument("--env", required=True)
    parser.add_argument("--explain", action="store_true")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--check-venv", action="store_true")

    args = parser.parse_args()

    detect_pollution(
        env_name=args.env,
        explain_mode=args.explain,
        strict_mode=args.strict,
        check_venv=args.check_venv,
    )


if __name__ == "__main__":
    main()
