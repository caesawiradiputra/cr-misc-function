"""
Clean conda environment.yml by removing build artifacts and internal packages.

This module provides functionality to clean conda environment files by:
- Removing conda/OS/compiler internals (vc*, ucrt, tk, openssl, mkl, etc.)
- Removing poetry and related packages
- Removing the 'prefix' line
- Preserving comments and formatting using ruamel.yaml
"""

import sys
from pathlib import Path
from typing import Optional

from ruamel.yaml import YAML

# Packages to remove by prefix matching
REMOVE_PREFIXES = {
    "lib",
    "vc",
    "ucrt",
    "tk",
    "openssl",
    "llvm",
    "mkl",
    "zstd",
    "bzip2",
    "ca-certificates",
    "python_abi",
}

# Poetry and build tooling packages to remove
POETRY_PACKAGES = {
    "poetry",
    "poetry-core",
    "cleo",
    "dulwich",
    "cachecontrol",
    "cachecontrol-with-filecache",
    "virtualenv",
    "keyring",
    "pbs-installer",
    "python-installer",
    "python-build",
    "pyproject_hooks",
    "pkginfo",
    "trove-classifiers",
    "rapidfuzz",
    "shellingham",
    "requests-toolbelt",
}


def should_remove_package(dep: str, remove_poetry: bool = True) -> bool:
    """
    Determine if a package should be removed based on removal rules.

    Args:
        dep: Package dependency string (e.g., "numpy=1.24.0")
        remove_poetry: Whether to also remove poetry packages

    Returns:
        True if package should be removed, False otherwise
    """
    # Extract package name (before the = sign)
    pkg_name = dep.split("=")[0].lower().strip()

    # Check against prefix patterns
    for prefix in REMOVE_PREFIXES:
        if pkg_name.startswith(prefix):
            return True

    # Check against poetry packages
    if remove_poetry and pkg_name in POETRY_PACKAGES:
        return True

    return False


def clean_environment_file(
    input_file: Path,
    output_file: Optional[Path] = None,
    remove_poetry: bool = True,
    dry_run: bool = False,
) -> dict:
    """
    Clean a conda environment.yml file by removing build artifacts.

    Args:
        input_file: Path to input environment.yml
        output_file: Path to output file (defaults to input_file)
        remove_poetry: Whether to remove poetry packages
        dry_run: If True, return stats without writing file

    Returns:
        Dictionary with statistics: {
            'total': int,
            'removed': int,
            'kept': int,
            'removed_packages': List[str]
        }
    """
    if output_file is None:
        output_file = input_file

    # Load YAML with ruamel.yaml to preserve formatting
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.default_flow_style = False
    yaml.indent(mapping=2, sequence=2, offset=2)

    with open(input_file, "r", encoding="utf-8") as f:
        data = yaml.load(f)

    # Remove prefix if it exists
    if "prefix" in data:
        del data["prefix"]

    # Process dependencies
    original_deps = data.get("dependencies", [])
    clean_deps = []
    removed_packages = []
    pip_section = None

    for dep in original_deps:
        if isinstance(dep, str):
            # Regular conda package
            if should_remove_package(dep, remove_poetry):
                removed_packages.append(dep)
            else:
                clean_deps.append(dep)
        elif isinstance(dep, dict) and "pip" in dep:
            # Preserve pip section as-is
            pip_section = dep

    # Add pip section back if it exists
    if pip_section:
        clean_deps.append(pip_section)

    # Update dependencies
    data["dependencies"] = clean_deps

    # Statistics
    stats = {
        "total": len(original_deps) - (1 if pip_section else 0),
        "removed": len(removed_packages),
        "kept": len(clean_deps) - (1 if pip_section else 0),
        "removed_packages": removed_packages,
    }

    # Write cleaned file (unless dry run)
    if not dry_run:
        # Get environment name for the comment
        env_name = data.get("name", "cr-misc-function-env")

        # Prepare header comment with conda commands
        header = f"""# To recreate this environment, run:
#   conda env remove -n {env_name}
#   conda env create -f environment.yml
#   conda activate {env_name}

"""

        # Write header comment first, then YAML content
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(header)
            yaml.dump(data, f)

    return stats


def main():
    """CLI entry point for cleaning environment files."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Clean conda environment.yml by removing build artifacts"
    )
    parser.add_argument("input_file", type=Path, help="Path to environment.yml file")
    parser.add_argument(
        "-o", "--output", type=Path, help="Output file (defaults to input file)"
    )
    parser.add_argument(
        "--keep-poetry", action="store_true", help="Keep poetry and related packages"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be removed without making changes",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Show detailed output"
    )

    args = parser.parse_args()

    # Validate input file
    if not args.input_file.exists():
        print(f"ERROR: File not found: {args.input_file}", file=sys.stderr)
        sys.exit(1)

    # Clean the file
    try:
        stats = clean_environment_file(
            input_file=args.input_file,
            output_file=args.output,
            remove_poetry=not args.keep_poetry,
            dry_run=args.dry_run,
        )

        # Print statistics
        print(f"Total packages: {stats['total']}")
        print(f"Removed: {stats['removed']}")
        print(f"Kept: {stats['kept']}")

        if args.verbose and stats["removed_packages"]:
            print("\nRemoved packages:")
            for pkg in stats["removed_packages"][:20]:
                print(f"  - {pkg}")
            if len(stats["removed_packages"]) > 20:
                print(f"  ... and {len(stats['removed_packages']) - 20} more")

        if args.dry_run:
            print("\nDRY RUN: No changes made")
        else:
            output = args.output or args.input_file
            print(f"\nCleaned file written to: {output}")

    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
