#!/usr/bin/env python3
"""
Generate a clean, portable environment.yml from a target conda environment.

Usage:
    python dev_generate_env.py --env my-env
    python dev_generate_env.py --env my-env --dry-run
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import yaml

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


# --------------------------------------------------
# Conda Environment Resolution
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
# Environment Inspection
# --------------------------------------------------

def get_python_version(python_path: Path) -> str:
    output = run([str(python_path), "--version"])
    version = output.split()[1]
    return ".".join(version.split(".")[:2])


def export_conda_from_history(env_name: str) -> list[str]:
    output = run(["conda", "env", "export", "-n", env_name, "--from-history"])
    data = yaml.safe_load(output)

    deps = data.get("dependencies", [])
    packages = []

    for dep in deps:
        if isinstance(dep, str):
            packages.append(dep.split("=")[0])

    return sorted(set(packages))


def get_pip_packages(python_path: Path) -> dict[str, str]:
    try:
        output = run([str(python_path), "-m", "pip", "freeze"])
    except subprocess.CalledProcessError:
        return {}

    packages = {}
    for line in output.splitlines():
        if "==" in line:
            name, version = line.split("==", 1)
            packages[name.lower()] = version

    return packages


def remove_duplicates(
    conda_packages: list[str],
    pip_packages: dict[str, str],
) -> dict[str, str]:
    conda_set = {pkg.lower() for pkg in conda_packages}
    return {
        name: version
        for name, version in pip_packages.items()
        if name not in conda_set
    }


def has_poetry_files(project_path: Path) -> bool:
    return (project_path / "pyproject.toml").exists() and (
        project_path / "poetry.lock"
    ).exists()


# --------------------------------------------------
# YAML Builder
# --------------------------------------------------

def build_environment_yaml(
    name: str,
    python_version: str,
    conda_packages: list[str],
    pip_packages: dict[str, str],
    use_poetry: bool,
) -> dict:

    dependencies: list = []

    dependencies.append(f"python={python_version}")

    for pkg in sorted(conda_packages):
        if pkg != "python":
            dependencies.append(pkg)

    if pip_packages and not use_poetry:
        dependencies.append("pip")
        dependencies.append(
            {"pip": [f"{k}=={v}" for k, v in sorted(pip_packages.items())]}
        )

    data = {
        "name": name,
        "channels": ["conda-forge", "defaults"],
        "dependencies": dependencies,
    }

    if use_poetry:
        data["_comment"] = "Install Python packages using: poetry install"

    return data


# --------------------------------------------------
# CLI
# --------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate environment.yml from specified conda environment."
    )
    parser.add_argument("--env", required=True, help="Target conda environment name")
    parser.add_argument("--output", default="environment.yml")
    parser.add_argument("--dry-run", action="store_true")

    args = parser.parse_args()

    project_path = Path.cwd()

    python_path = get_conda_env_python(args.env)
    python_version = get_python_version(python_path)

    conda_packages = export_conda_from_history(args.env)
    pip_packages = get_pip_packages(python_path)
    pip_packages = remove_duplicates(conda_packages, pip_packages)

    use_poetry = has_poetry_files(project_path)

    env_yaml = build_environment_yaml(
        name=args.env,
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

    print(f"✓ Generated {output_path}")
    print("\nRebuild:")
    print(f"  conda remove -n {args.env} --all")
    print(f"  conda env create -f {output_path}")
    print(f"  conda activate {args.env}")

    if use_poetry:
        print("  poetry install")


if __name__ == "__main__":
    main()
