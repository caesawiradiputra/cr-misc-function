#!/usr/bin/env python3
"""
Display the command to remove base-only utility packages from conda environment.

Analyzes the current conda environment and displays the command to remove
packages that are typically only needed in the base conda environment but
not required for project-specific work. You decide when to run the command.

Base-only packages identified:
- poetry, poetry-core: Dependency and package management
- pipdeptree: Dependency tree visualization
- pip-audit: Pip package security auditing
- jupyter, jupyterlab: Notebook environments (optional)
- ipython: Interactive Python shell (optional)

Usage:
    python scripts/python/dev_remove_base_only_packages.py
    python scripts/python/dev_remove_base_only_packages.py --include-jupyter
    python scripts/python/dev_remove_base_only_packages.py --include-jupyter --include-ipython
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys


def run_command(cmd: list[str]) -> tuple[str, int]:
    """Run command and return (stdout, returncode)."""
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip(), result.returncode


def get_active_conda_env() -> str:
    """Get active conda environment name."""
    output, code = run_command(["conda", "info", "--json"])

    if code != 0:
        raise RuntimeError("❌ Conda not found or not accessible")

    data = json.loads(output)
    active_env = data.get("active_prefix_name")

    if not active_env:
        raise RuntimeError("❌ Could not detect active conda environment")

    return active_env


def get_installed_packages() -> set[str]:
    """Get list of installed packages in current conda environment."""
    output, code = run_command(["conda", "list", "--json"])

    if code != 0:
        raise RuntimeError("❌ Failed to retrieve installed packages")

    packages = json.loads(output)
    return {pkg["name"] for pkg in packages}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Display command to remove base-only packages from conda environment"
    )
    parser.add_argument(
        "--include-jupyter",
        action="store_true",
        help="Also identify jupyter and jupyterlab for removal",
    )
    parser.add_argument(
        "--include-ipython",
        action="store_true",
        help="Also identify ipython for removal",
    )

    args = parser.parse_args()

    print()
    print("=" * 49)
    print("     Remove Base-Only Packages")
    print("=" * 49)
    print()

    try:
        # Step 1: Check conda and get active environment
        print("\033[36m[*] Checking conda environment\033[0m")

        active_env = get_active_conda_env()
        print(f"\033[32m[OK] Active environment: {active_env}\033[0m")

        # Step 2: Define packages to remove
        print("\033[36m[*] Identifying packages to remove\033[0m")

        base_only_packages = [
            "poetry",
            "poetry-core",
            "pipdeptree",
            "pip-audit",
        ]

        if args.include_jupyter:
            base_only_packages.extend(["jupyter", "jupyterlab"])

        if args.include_ipython:
            base_only_packages.append("ipython")

        print(f"\033[90m[INFO] Target packages: {', '.join(base_only_packages)}\033[0m")

        # Step 3: Check which packages are installed
        print("\033[36m[*] Checking installed packages\033[0m")

        installed = get_installed_packages()
        packages_to_remove = [pkg for pkg in base_only_packages if pkg in installed]

        if not packages_to_remove:
            print("\033[33m[WARN] No base-only packages are currently installed\033[0m")
            print("\033[90m[INFO] Nothing to do!\033[0m")
            return

        print(
            f"\033[32m[OK] Found {len(packages_to_remove)} package(s) to remove:\033[0m"
        )
        for pkg in packages_to_remove:
            print(f"  - {pkg}")

        # Step 4: Display the command to run
        print("\033[36m[*] Command to execute\033[0m")
        print()

        remove_command = f"conda remove --yes --quiet {' '.join(packages_to_remove)}"
        print(f"\033[36m{remove_command}\033[0m")
        print()

        # Step 5: Summary
        print("=" * 49)
        print("     Ready to Run")
        print("=" * 49)
        print()
        print("\033[32m[OK] Copy and run the command above when ready\033[0m")
        print(
            f"\033[90m[INFO] This will remove {len(packages_to_remove)} package(s) from your environment\033[0m"
        )
        print()

    except Exception as e:
        print()
        print(f"\033[31m[ERROR] {e}\033[0m")
        sys.exit(1)


if __name__ == "__main__":
    main()
