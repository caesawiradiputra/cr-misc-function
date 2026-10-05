#!/usr/bin/env python3
"""Check whether a project's pinned dependencies install on a target Python.

Collects the dependency list from (first match wins):
  1. uv.lock + pyproject.toml  -> `uv export` (exact locked versions, all groups)
  2. requirements.txt
  3. pyproject.toml            -> PEP 621 lists or classic [tool.poetry.*] tables
                                  (caret/tilde converted to PEP 440)

Installs everything into a throwaway venv on the target Python (uv downloads it
if needed), in rounds: each failing package (direct or transitive) is looked up
on PyPI for the OLDEST release above the current pin that ships a wheel for the
target (the smallest possible bump), the bump is applied (direct pins are
edited, transitive ones forced with a uv override), and the install is retried
until it succeeds or no further bump helps. The result is a validated list of
minimal pin changes, never applied to the project itself.

With --from, it also resolves the SAME requirements for the old and the new
Python (`uv pip compile`, no builds) and reports "resolution drift": packages
whose resolved version jumps a major (or 0.x minor) version only because the
Python changed. Loose pins like `numpy<=2.0.0` install fine on both but give
numpy 1.x on 3.8 and 2.x on 3.11, which can break imports at runtime.

Usage:
    python check_deps.py --python 3.11 [--from 3.8] [--path .] [--max-rounds 8]

Needs uv on PATH and Python >= 3.11 to run (tomllib). Prints Markdown.
Exit code: 0 = installs as pinned (no drift), 1 = needs the reported bumps or
has breaking drift, 2 = unresolved.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import tomllib
import urllib.request

_NAME = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)(\[[^\]]*\])?\s*(.*)$")
_VERSION = re.compile(r"(\d+)(?:\.(\d+))?(?:\.(\d+))?")


# ---------------------------------------------------------------- collection
def _bump(version: str, level: int) -> str | None:
    m = _VERSION.fullmatch(version)
    if not m:
        return None
    parts = [int(p) for p in m.groups() if p is not None]
    upper = parts[: level + 1]
    upper[-1] += 1
    return f">={version},<{'.'.join(map(str, upper))}"


def poetry_constraint(spec: str) -> str:
    out = []
    for part in spec.split(","):
        part = part.strip()
        if part in ("", "*"):
            continue
        if part.startswith("^"):
            v = part[1:].strip()
            m = _VERSION.fullmatch(v)
            nums = [int(p) for p in m.groups() if p is not None] if m else []
            level = next((i for i, n in enumerate(nums) if n != 0), max(len(nums) - 1, 0))
            out.append(_bump(v, level) or part)
        elif part.startswith("~") and not part.startswith("~="):
            v = part[1:].strip()
            m = _VERSION.fullmatch(v)
            out.append(_bump(v, 0 if m and m.group(2) is None else 1) or part)
        elif part[0].isdigit():
            out.append("==" + part)
        else:
            out.append(part)
    return ",".join(out)


def from_poetry_table(table: dict) -> list[str]:
    reqs = []
    for name, value in table.items():
        if name == "python":
            continue
        if isinstance(value, str):
            reqs.append(name + poetry_constraint(value))
        elif isinstance(value, dict) and "version" in value:
            extras = value.get("extras") or []
            reqs.append(name + (f"[{','.join(extras)}]" if extras else "")
                        + poetry_constraint(str(value["version"])))
    return reqs


def _names(reqs: list[str]) -> set[str]:
    return {_norm(m.group(1)) for r in reqs if (m := _NAME.match(r))}


def collect(path: str) -> tuple[list[str], str, set[str]]:
    """(requirements, source label, normalized names of DIRECT dependencies)."""
    pyproject = os.path.join(path, "pyproject.toml")
    if os.path.isfile(os.path.join(path, "uv.lock")) and os.path.isfile(pyproject):
        out = subprocess.run(
            ["uv", "export", "--frozen", "--no-hashes", "--no-emit-project", "--all-groups",
             "--no-header", "--no-annotate"],
            cwd=path, capture_output=True, text=True)
        if out.returncode == 0:
            ## Keep environment markers: a universal lock pins some packages
            ## once per Python range, and only the markers tell them apart.
            reqs = [ln.strip() for ln in out.stdout.splitlines()
                    if ln.strip() and not ln.startswith(("#", "-e", "."))]
            with open(pyproject, "rb") as f:
                data = tomllib.load(f)
            direct = list(data.get("project", {}).get("dependencies", []))
            for grp in data.get("dependency-groups", {}).values():
                direct += [g for g in grp if isinstance(g, str)]
            return reqs, "uv.lock (uv export)", _names(direct)
    req_txt = os.path.join(path, "requirements.txt")
    if os.path.isfile(req_txt):
        with open(req_txt, encoding="utf-8") as f:
            reqs = [ln.split("#")[0].strip() for ln in f
                    if ln.strip() and not ln.lstrip().startswith(("#", "-"))]
        reqs = [r for r in reqs if r]
        return reqs, "requirements.txt", _names(reqs)
    if os.path.isfile(pyproject):
        with open(pyproject, "rb") as f:
            data = tomllib.load(f)
        project = data.get("project", {})
        reqs = list(project.get("dependencies", []))
        for group in ("dev",):
            reqs += project.get("optional-dependencies", {}).get(group, [])
            reqs += [g for g in data.get("dependency-groups", {}).get(group, [])
                     if isinstance(g, str)]
        poetry = data.get("tool", {}).get("poetry", {})
        reqs += from_poetry_table(poetry.get("dependencies", {}))
        reqs += from_poetry_table(poetry.get("dev-dependencies", {}))
        for grp in poetry.get("group", {}).values():
            reqs += from_poetry_table(grp.get("dependencies", {}))
        ## "pkg (>=1,<2)" -> "pkg>=1,<2"
        reqs = [re.sub(r"\s*\((.+)\)\s*$", r"\1", r) for r in reqs]
        return reqs, "pyproject.toml", _names(reqs)
    sys.exit("No uv.lock, requirements.txt or pyproject.toml found")


# ------------------------------------------------------------------ install
def venv_python(venv: str) -> str:
    return os.path.join(venv, "Scripts" if os.name == "nt" else "bin",
                        "python.exe" if os.name == "nt" else "python")


_NETWORK = re.compile(r"error sending request|client error \(Connect\)|timed out|Could not connect",
                      re.I)


def uv_install(py: str, reqs: list[str], overrides: dict[str, str], tmp: str) -> tuple[bool, str]:
    """Install; retry up to 3 times with backoff when the index is unreachable."""
    for attempt in range(4):
        ok, err = _uv_install_once(py, reqs, overrides, tmp)
        if ok or not _NETWORK.search(err) or attempt == 3:
            return ok, err
        time.sleep(15 * (attempt + 1))
    return ok, err


def _uv_install_once(py: str, reqs: list[str], overrides: dict[str, str],
                     tmp: str) -> tuple[bool, str]:
    cmd = ["uv", "pip", "install", "--python", py, *reqs]
    if overrides:
        path = os.path.join(tmp, "overrides.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(overrides.values()) + "\n")
        cmd += ["--override", path]
    p = subprocess.run(cmd, capture_output=True, text=True)
    return p.returncode == 0, p.stderr or ""


_FAILED = re.compile(r"(?:Failed to (?:build|download|prepare)|no wheels? (?:for|with))"
                     r"[^`]*`([A-Za-z0-9][A-Za-z0-9._-]*)==([^`]+)`", re.I)
_FAILED_ALT = re.compile(r"Because ([A-Za-z0-9][A-Za-z0-9._-]*)==(\S+) (?:has no wheels|depends on Python)",
                         re.I)


def failures(stderr: str) -> list[tuple[str, str]]:
    found = _FAILED.findall(stderr) + _FAILED_ALT.findall(stderr)
    return list(dict.fromkeys((n, v.rstrip(".,")) for n, v in found))


def summarize(stderr: str) -> str:
    lines = [ln.strip() for ln in stderr.splitlines()
             if re.search(r"error|×|fatal|No solution|unsatisf|depends on", ln, re.I)]
    return " / ".join(lines[:3]).replace("|", "/")[:240]


# ------------------------------------------------------------------ suggest
def _norm(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _ver_key(v: str) -> tuple:
    return tuple(int(x) if x.isdigit() else -1 for x in re.split(r"[.+-]", v))


def _wheel_ok(filename: str, xy: str) -> bool:
    ## name-ver(-build)?-py-abi-plat.whl
    py, abi, plat = filename[:-4].split("-")[-3:]
    if plat != "any":
        if os.name == "nt" and "win_amd64" not in plat:
            return False
        if os.name != "nt" and not ("linux" in plat and "x86_64" in plat):
            return False
    pys = py.split(".")
    if f"cp{xy}" in pys or "py3" in pys:
        return True
    if abi == "abi3":
        return any(p.startswith("cp3") and p[3:].isdigit() and int(p[3:]) <= int(xy)
                   for p in pys)
    return False


def pypi(name: str, version: str | None = None) -> dict | None:
    url = f"https://pypi.org/pypi/{name}/{version}/json" if version else \
        f"https://pypi.org/pypi/{name}/json"
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                return json.load(r)
        except Exception:  # noqa: BLE001 - network is best-effort, retried
            time.sleep(5 * (attempt + 1))
    return None


def minimal_wheel_version(name: str, above: str, xy: str) -> tuple[str | None, str]:
    """(oldest non-pre-release version > `above` with a wheel for Python xy, why-not)."""
    data = pypi(name)
    if not data:
        return None, "PyPI lookup failed (network)"
    floor = _ver_key(above)
    for v in sorted(data["releases"], key=_ver_key):
        if re.search(r"[a-zA-Z]", v) or _ver_key(v) <= floor:
            continue
        files = [f for f in data["releases"][v] if not f.get("yanked")]
        if any(f["filename"].endswith(".whl") and _wheel_ok(f["filename"], xy) for f in files):
            return v, ""
    return None, f"no release above {above} has a py{xy} wheel"


def parents(name: str, reqs: list[str]) -> list[str]:
    """Direct requirements whose pinned release declares a dependency on `name`."""
    out = []
    for req in reqs:
        m = _NAME.match(req)
        pin = re.search(r"==\s*([0-9][0-9A-Za-z.]*)", req)
        if not m or not pin:
            continue
        info = (pypi(m.group(1), pin.group(1)) or {}).get("info", {})
        for dep in info.get("requires_dist") or []:
            dm = _NAME.match(dep)
            if dm and _norm(dm.group(1)) == _norm(name) and "extra ==" not in dep:
                out.append(f"`{m.group(1)}=={pin.group(1)}` requires `{dep.split(';')[0].strip()}`")
    return out


# -------------------------------------------------------------------- drift
def resolve(reqs: list[str], version: str, overrides: dict[str, str], tmp: str) -> dict[str, str]:
    """name -> version as uv resolves `reqs` for `version` (no install/build)."""
    src = os.path.join(tmp, f"drift-{version}.txt")
    with open(src, "w", encoding="utf-8") as f:
        f.write("\n".join(reqs) + "\n")
    cmd = ["uv", "pip", "compile", "-q", "--python-version", version, "--no-header",
           "--no-annotate", src]
    if overrides:
        cmd += ["--override", os.path.join(tmp, "overrides.txt")]
    p = subprocess.run(cmd, capture_output=True, text=True)
    out = {}
    for ln in p.stdout.splitlines():
        m = re.match(r"^([A-Za-z0-9][A-Za-z0-9._-]*)==([^\s;]+)", ln.strip())
        if m:
            out[_norm(m.group(1))] = m.group(2)
    return out


def _breaking(old: str, new: str) -> bool:
    o, n = _ver_key(old), _ver_key(new)
    if not o or not n:
        return False
    if o[0] != n[0]:
        return True
    return o[0] == 0 and len(o) > 1 and len(n) > 1 and o[1] != n[1]


def drift(reqs: list[str], current: list[str], old_py: str, new_py: str,
          overrides: dict[str, str], direct: set[str], tmp: str) -> tuple[list[str], bool]:
    """(Markdown lines, whether any breaking drift was found)."""
    out = [f"\n### Resolution drift {old_py} -> {new_py}\n"]
    before = resolve(reqs, old_py, {}, tmp)
    after = resolve(current, new_py, overrides, tmp)
    if not before or not after:
        return out + ["Could not resolve for both versions; drift not checked."], False
    rows = [(n, before[n], after[n]) for n in sorted(set(before) & set(after))
            if before[n] != after[n] and _breaking(before[n], after[n])]
    if not rows:
        return out + ["No major-version jumps caused by the Python change."], False
    out.append("These resolve to a new MAJOR (or 0.x minor) version only because the Python"
          " changed. They install, but may break at import/runtime: pin the old line"
          " (e.g. `numpy<2`) unless the code is verified against the new one.\n")
    out += [f"| Package | On {old_py} | On {new_py} | Kind |", "| --- | --- | --- | --- |"]
    out += [f"| {n} | {o} | {v} | {'direct' if n in direct else 'transitive'} |"
            for n, o, v in rows]
    return out, True


# --------------------------------------------------------------------- main
def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--python", required=True, help="target version, e.g. 3.11")
    ap.add_argument("--path", default=".")
    ap.add_argument("--from", dest="src", help="current Python, e.g. 3.8 (enables drift check)")
    ap.add_argument("--max-rounds", type=int, default=8)
    args = ap.parse_args()
    xy = "".join(args.python.split(".")[:2])

    reqs, source, direct = collect(args.path)
    print(f"## Dependency check on Python {args.python}\n")
    print(f"Source: {source} ({len(reqs)} requirements)\n")
    drift_lines: list[str] = []
    drifted = False
    by_name: dict[str, list[int]] = {}
    for i, r in enumerate(reqs):
        if m := _NAME.match(r):
            by_name.setdefault(_norm(m.group(1)), []).append(i)
    current = list(reqs)
    overrides: dict[str, str] = {}
    changes: list[tuple[str, str, str, str, str]] = []  # name, old, new, kind, reason
    stuck: list[str] = []
    ok, err = False, ""
    with tempfile.TemporaryDirectory(prefix="pyupgrade-deps-") as tmp:
        venv = os.path.join(tmp, "venv")
        p = subprocess.run(["uv", "venv", venv, "--python", args.python, "--quiet"],
                           capture_output=True, text=True)
        if p.returncode != 0:
            sys.exit(f"could not create a Python {args.python} venv: {p.stderr.strip()}")
        py = venv_python(venv)
        for _ in range(args.max_rounds):
            ok, err = uv_install(py, current, overrides, tmp)
            if ok:
                break
            progressed = False
            for name, ver in failures(err):
                new, why = minimal_wheel_version(name, ver, xy)
                if not new:
                    stuck.append(f"`{name}=={ver}`: {why}")
                    continue
                key = _norm(name)
                if key in by_name:
                    ## Every line for the package (one per marker) gets the pin.
                    for i in by_name[key]:
                        m = _NAME.match(current[i])
                        marker = current[i].split(";", 1)[1] if ";" in current[i] else ""
                        current[i] = f"{m.group(1)}{m.group(2) or ''}=={new}" + (
                            f" ;{marker}" if marker else "")
                    kind = "direct" if key in direct else "transitive (locked) via " + (
                        "; ".join(parents(name, [reqs[i] for i in range(len(reqs))
                                                 if _NAME.match(reqs[i]) and _norm(
                                                     _NAME.match(reqs[i]).group(1)) in direct])
                                  ) or "unknown parent")
                    changes.append((name, f"{name}=={ver}", f"{name}=={new}", kind,
                                    summarize(err)))
                else:
                    overrides[key] = f"{name}>={new}"
                    via = "; ".join(parents(name, reqs)) or "unknown parent"
                    changes.append((name, f"{name}=={ver}", f"{name}>={new}",
                                    f"transitive via {via}", summarize(err)))
                progressed = True
            if not progressed:
                break
        if ok and args.src:
            drift_lines, drifted = drift(reqs, current, args.src, args.python, overrides,
                                         direct, tmp)

    if ok and not changes:
        print(f"All {len(reqs)} requirements install as pinned on Python {args.python}.")
        print("\n".join(drift_lines))
        sys.exit(1 if drifted else 0)
    if changes:
        print("| Package | Current | Minimal working | Kind | Original error |")
        print("| --- | --- | --- | --- | --- |")
        for name, old, new, kind, reason in changes:
            print(f"| {name} | `{old}` | `{new}` | {kind} | {reason} |")
        print()
    if ok:
        print(f"**Validated:** the full set installs on Python {args.python} with the bumps above."
              + (" Transitive bumps were forced with uv overrides: fix them by raising the"
                 " parent pin until it allows that version." if overrides else ""))
        print("\n".join(drift_lines))
        sys.exit(1)
    if _NETWORK.search(err):
        print(f"**Network error** reaching the package index - not a dependency problem."
              f" Re-run when the index is reachable: {summarize(err)}")
        sys.exit(2)
    print(f"**Unresolved:** install still fails on Python {args.python}: {summarize(err)}")
    for item in dict.fromkeys(stuck):
        print(f"- {item}")
    print("\nNeeds manual analysis (e.g. a yanked/removed package, a resolution conflict,"
          " or a package with no wheel for this Python at any version).")
    sys.exit(2)


if __name__ == "__main__":
    main()
