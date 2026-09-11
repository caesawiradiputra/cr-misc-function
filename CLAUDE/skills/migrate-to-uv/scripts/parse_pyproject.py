#!/usr/bin/env python3
"""Extract dependency info from a pyproject.toml for a Poetry/Conda -> uv migration.

Reads the file with stdlib tomllib (Python >=3.11) rather than regex, and
understands two dependency shapes because real-world Poetry projects use both:

  1. PEP 621 lists   - [project] dependencies = ["pkg (>=1.0,<2.0)", ...]
                        (what modern Poetry writes when poetry-core is the
                        backend but the project table follows PEP 621)
  2. Classic tables   - [tool.poetry.dependencies] pkg = "^1.0"
                        (what Poetry wrote by default for years; a plain
                        regex on `dependencies = [...]` misses this entirely)

Dev dependencies are looked up in priority order: PEP 735 [dependency-groups]
dev, then [project.optional-dependencies] dev, then the classic
[tool.poetry.group.dev.dependencies] / [tool.poetry.dev-dependencies] tables.

Usage:
    python parse_pyproject.py <path-to-pyproject.toml> [--no-default-devtools]

Prints a single JSON object to stdout.
"""

from __future__ import annotations

import json
import re
import sys

try:
    import tomllib
except ImportError:  # pragma: no cover - Python <3.11 fallback
    try:
        import tomli as tomllib  # type: ignore[no-redef]
    except ImportError:
        print(
            json.dumps(
                {
                    "error": (
                        "No TOML parser available. Python 3.11+ has tomllib "
                        "built in; on older Python, `pip install tomli` first."
                    )
                }
            )
        )
        sys.exit(1)

DEFAULT_DEV_TOOLS = ["mypy", "ruff"]

# "pandas (>=2.3.1,<3.0.0)" -> name="pandas", spec=">=2.3.1,<3.0.0"
_PAREN_SPEC = re.compile(r"^([A-Za-z0-9_.-]+)\s*\((.+)\)$")
# "pandas>=2.3.1,<3.0.0" -> name="pandas", spec=">=2.3.1,<3.0.0"
_BARE_SPEC = re.compile(r"^([A-Za-z0-9_.-]+)\s*([<>=!~].*)$")
# Poetry caret/tilde on a classic table value: "^2.3.1", "~2.3", "2.3.1"
_CARET = re.compile(r"^\^(\d+)(?:\.(\d+))?(?:\.(\d+))?")


def normalize_pep508(entry: str) -> str:
    """Turn a PEP-621-list-style entry into a bare `uv add`-able argument."""
    dep = entry.strip().strip("'\"")
    m = _PAREN_SPEC.match(dep)
    if m:
        name, spec = m.group(1), m.group(2).strip()
        return f"{name}{spec}"
    m = _BARE_SPEC.match(dep)
    if m:
        return dep
    return dep


def caret_to_range(spec: str) -> str:
    """Best-effort conversion of Poetry's caret/tilde shorthand to PEP 440.

    Not exhaustive (Poetry's version syntax has more corners than this), but
    covers the common `^X`, `^X.Y`, `^X.Y.Z` cases. Anything it can't
    confidently convert is passed through unchanged with the original
    caret/tilde intact so a human notices it during review.
    """
    spec = spec.strip()
    m = _CARET.match(spec)
    if not m:
        return spec
    major, minor, patch = m.group(1), m.group(2), m.group(3)
    lower = f"{major}.{minor or 0}.{patch or 0}"
    next_major = int(major) + 1
    return f">={lower},<{next_major}.0.0"


def entry_from_classic_table(name: str, value) -> str | None:
    """Convert one [tool.poetry.dependencies]-style key/value pair."""
    if name == "python":
        return None
    if isinstance(value, str):
        spec = value.strip()
        if spec in ("*", ""):
            return name
        if spec.startswith("^") or spec.startswith("~"):
            spec = caret_to_range(spec)
        elif spec[0].isdigit():
            spec = f"=={spec}"
        return f"{name}{spec}"
    if isinstance(value, dict):
        version = value.get("version")
        if version:
            return entry_from_classic_table(name, version)
        return name  # git/path/url dependency - uv add can't infer this; flag as bare name
    return name


def collect_dev_deps(data: dict) -> tuple[list[str], str]:
    groups = data.get("dependency-groups", {})
    if isinstance(groups.get("dev"), list) and groups["dev"]:
        return [normalize_pep508(d) for d in groups["dev"]], "dependency-groups.dev"

    optional = data.get("project", {}).get("optional-dependencies", {})
    if isinstance(optional.get("dev"), list) and optional["dev"]:
        return [normalize_pep508(d) for d in optional["dev"]], "project.optional-dependencies.dev"

    poetry = data.get("tool", {}).get("poetry", {})
    group_dev = poetry.get("group", {}).get("dev", {}).get("dependencies", {})
    if group_dev:
        out = [entry_from_classic_table(k, v) for k, v in group_dev.items()]
        return [d for d in out if d], "tool.poetry.group.dev.dependencies"

    legacy_dev = poetry.get("dev-dependencies", {})
    if legacy_dev:
        out = [entry_from_classic_table(k, v) for k, v in legacy_dev.items()]
        return [d for d in out if d], "tool.poetry.dev-dependencies"

    return [], "none-found"


def collect_main_deps(data: dict) -> tuple[list[str], str]:
    project_deps = data.get("project", {}).get("dependencies")
    if isinstance(project_deps, list) and project_deps:
        return [normalize_pep508(d) for d in project_deps], "project.dependencies"

    poetry_deps = data.get("tool", {}).get("poetry", {}).get("dependencies", {})
    if poetry_deps:
        out = [entry_from_classic_table(k, v) for k, v in poetry_deps.items()]
        return [d for d in out if d], "tool.poetry.dependencies"

    return [], "none-found"


def quote_if_needed(dep: str) -> str:
    # Quote whenever a shell would otherwise treat part of this as syntax —
    # not just comma/space, but also the PEP 508 comparison operators
    # (>, <, !) which double as redirect/negation in PowerShell and bash.
    return f"'{dep}'" if re.search(r"[,\s<>!]", dep) else dep


def main() -> None:
    args = sys.argv[1:]
    if not args:
        print(json.dumps({"error": "usage: parse_pyproject.py <path> [--no-default-devtools]"}))
        sys.exit(1)

    path = args[0]
    add_default_devtools = "--no-default-devtools" not in args

    with open(path, "rb") as f:
        data = tomllib.load(f)

    project = data.get("project", {})
    poetry = data.get("tool", {}).get("poetry", {})
    build_backend = data.get("build-system", {}).get("build-backend", "")
    build_requires = data.get("build-system", {}).get("requires", [])
    uses_poetry = "poetry" in build_backend or any("poetry" in r for r in build_requires)

    name = project.get("name") or poetry.get("name") or ""
    requires_python = project.get("requires-python")
    if not requires_python:
        py_spec = poetry.get("dependencies", {}).get("python")
        if isinstance(py_spec, str) and (py_spec.startswith("^") or py_spec.startswith("~")):
            requires_python = ">=" + caret_to_range(py_spec).split(",")[0].lstrip(">=")
        elif py_spec:
            requires_python = py_spec

    deps, dep_source = collect_main_deps(data)
    dev_deps, dev_source = collect_dev_deps(data)

    if add_default_devtools:
        existing_names = {re.split(r"[<>=!~\s]", d, 1)[0].strip("'\"").lower() for d in dev_deps}
        for tool in DEFAULT_DEV_TOOLS:
            if tool not in existing_names:
                dev_deps.append(tool)

    uv_add_dependencies = (
        "uv add " + " ".join(quote_if_needed(d) for d in deps) if deps else ""
    )
    uv_add_dev = (
        "uv add --dev " + " ".join(quote_if_needed(d) for d in dev_deps) if dev_deps else ""
    )

    result = {
        "name": name,
        "requires_python": requires_python,
        "build_backend": build_backend,
        "uses_poetry": uses_poetry,
        "dependencies": deps,
        "dependency_source": dep_source,
        "dev_dependencies": dev_deps,
        "dev_dependency_source": dev_source,
        "uv_add_dependencies": uv_add_dependencies,
        "uv_add_dev": uv_add_dev,
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
