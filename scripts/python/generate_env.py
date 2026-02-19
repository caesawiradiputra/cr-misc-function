#!/usr/bin/env python3
"""
Generate a clean, portable environment.yml from the active conda environment.

Usage:
    python scripts/generate_env.py
    python scripts/generate_env.py --dry-run
    python scripts/generate_env.py --output custom.yml
    python scripts/generate_env.py --allow-base
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import yaml


def run_command(command: list[str]) -> str:
    """Run shell command and return stdout."""
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def get_active_conda_env() -> tuple[str, str]:
    """Return active conda environment name and path."""
    output = run_command(["conda", "info", "--json"])
    data = json.loads(output)

    env_name = data.get("active_prefix_name")
    env_path = data.get("active_prefix")

    if not env_name or not env_path:
        raise RuntimeError("Could not detect active conda environment.")

    return env_name, env_path


def get_python_version() -> str:
    """Return python major.minor version."""
    output = run_command(["python", "--version"])
    version = output.split()[1]
    major_minor = ".".join(version.split(".")[:2])
    return major_minor


def export_conda_from_history() -> list[str]:
    """Return explicitly installed conda packages."""
    output = run_command(["conda", "env", "export", "--from-history"])
    data = yaml.safe_load(output)

    dependencies = data.get("dependencies", [])

    conda_packages: list[str] = []
    for dep in dependencies:
        if isinstance(dep, str):
            conda_packages.append(dep.split("=")[0])

    return sorted(set(conda_packages))


def get_pip_packages() -> dict[str, str]:
    """Return pip packages as {name: version}.

    Uses pipdeptree to get only top-level packages (directly installed),
    not their dependencies. Falls back to pip freeze if pipdeptree unavailable.
    """
    # First, try to use pipdeptree to get only top-level packages
    try:
        output = run_command(["pipdeptree", "--warn", "silence"])
        packages: dict[str, str] = {}

        for line in output.splitlines():
            # Top-level packages don't have indentation
            if line and not line[0].isspace():
                # Line format: "package-name==version"
                if "==" in line:
                    name, version = line.split("==", 1)
                    packages[name.lower().strip()] = version.strip()

        if packages:
            return packages
    except (subprocess.CalledProcessError, FileNotFoundError):
        # pipdeptree not available, fall through to pip freeze
        pass

    # Fallback: use pip freeze (includes all dependencies)
    try:
        output = run_command(["pip", "freeze"])
    except subprocess.CalledProcessError:
        return {}

    packages: dict[str, str] = {}
    for line in output.splitlines():
        if "==" in line:
            name, version = line.split("==", 1)
            packages[name.lower()] = version

    return packages


def remove_duplicates(
    conda_packages: list[str],
    pip_packages: dict[str, str],
) -> dict[str, str]:
    """Remove pip packages that are already managed by conda."""
    conda_set = {pkg.lower() for pkg in conda_packages}
    return {
        name: version
        for name, version in pip_packages.items()
        if name not in conda_set
    }


def has_poetry_files() -> bool:
    """Check if pyproject.toml and poetry.lock exist in current directory."""
    current_dir = Path.cwd()
    return (current_dir / "pyproject.toml").exists() and (current_dir / "poetry.lock").exists()


def build_environment_yaml(
    name: str,
    python_version: str,
    conda_packages: list[str],
    pip_packages: dict[str, str],
    use_poetry: bool = False,
) -> dict:
    """Build final YAML structure.

    Args:
        name: Environment name
        python_version: Python version (e.g., "3.11")
        conda_packages: List of conda package names
        pip_packages: Dictionary of {package_name: version}
        use_poetry: If True, skip pip dependencies and add poetry install comment
    """
    dependencies: list = []

    dependencies.append(f"python={python_version}")

    for pkg in sorted(conda_packages):
        if pkg != "python":
            dependencies.append(pkg)

    # Only add pip packages if not using poetry
    if pip_packages and not use_poetry:
        dependencies.append("pip")
        dependencies.append(
            {
                "pip": [
                    f"{name}=={version}"
                    for name, version in sorted(pip_packages.items())
                ]
            }
        )

    data = {
        "name": name,
        "channels": ["conda-forge", "defaults"],
        "dependencies": dependencies,
    }

    # Add comment for poetry-based environments
    if use_poetry:
        data["_comment"] = "Install Python packages using: poetry install"

    return data


def validate_yaml_file(path: Path) -> None:
    """Validate YAML syntax."""
    with path.open("r", encoding="utf-8") as f:
        yaml.safe_load(f)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate clean environment.yml from active conda environment."
    )
    parser.add_argument(
        "--output",
        default="environment.yml",
        help="Output file name",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print YAML instead of writing file",
    )
    parser.add_argument(
        "--allow-base",
        action="store_true",
        help="Allow generating from base environment",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    env_name, _ = get_active_conda_env()

    if env_name == "base" and not args.allow_base:
        print("Base environment detected. Use --allow-base to override.")
        sys.exit(1)

    python_version = get_python_version()
    conda_packages = export_conda_from_history()
    pip_packages = get_pip_packages()
    pip_packages = remove_duplicates(conda_packages, pip_packages)

    # Check if project uses poetry for dependency management
    use_poetry = has_poetry_files()

    env_yaml = build_environment_yaml(
        name=env_name,
        python_version=python_version,
        conda_packages=conda_packages,
        pip_packages=pip_packages,
        use_poetry=use_poetry,
    )

    if args.dry_run:
        print(yaml.dump(env_yaml, sort_keys=False))
        return

    output_path = Path(args.output)
    with output_path.open("w", encoding="utf-8") as f:
        yaml.dump(env_yaml, f, sort_keys=False)

    validate_yaml_file(output_path)

    print(f"✓ Generated {output_path}")
    if use_poetry:
        print("Note: Python packages are managed by Poetry")
        print("Run: poetry install")
    else:
        print("Run: conda env create -f", output_path)


if __name__ == "__main__":
    main()
