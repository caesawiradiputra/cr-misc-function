---
name: upgrade-python-version
description: Upgrades a Python project to a newer Python version (e.g. 3.8 → 3.11) without changing its structure or behavior. Checks which dependency pins won't install on the target and finds the smallest working bumps, scans for stdlib removals and behavior changes, applies syntax-only modernization (Optional/Union → X | Y, typing.List/Dict → list/dict, collections.abc imports, IOError → OSError, etc.) through bundled scripts, updates version strings in config (pyproject, .python-version, ruff/mypy, Dockerfile, CI), verifies nothing structural changed, and writes an upgrade guideline document. Use this whenever the user wants to upgrade, bump, or move a project to a newer Python, modernize type hints or syntax for a newer Python, asks "what breaks if we go to 3.11/3.12", or wants a Python upgrade guide or checklist — even if they only say "move this repo off 3.8" or "use the new union syntax".
---

# Upgrade Python Version

Moving a project from an old Python (say 3.8) to a new one (say 3.11) has three
separate risk areas, and they need different treatment:

1. **Dependencies:** old pins often have no wheel for the new Python and fail to build.
2. **Stdlib/runtime changes:** removed APIs and silently changed behavior.
3. **Syntax:** the new Python allows cleaner spellings of the same thing.

Only (3) is safe to apply mechanically. (1) and (2) change what the program
does, so they go into the guideline for a human decision.

## The contract: what may change, and what may not

The user wants a newer Python **without changing code structure or
functionality**. Hold to this strictly, because a Python upgrade that changes
behavior breaks production pipelines in ways tests often don't cover.

**Allowed without asking:**
- Syntax rewrites that produce the *identical runtime object or behavior*:
  - `Optional[X]` / `Union[X, Y]` → `X | None` / `X | Y`
  - `List`/`Dict`/`Tuple`/`Set`/`Type` → `list`/`dict`/`tuple`/`set`/`type`
  - `typing` → `collections.abc` imports for ABCs
  - `class A(object)` → `class A`
  - `IOError` → `OSError` (the same class since Python 3.3)
  - `super(Cls, self)` → `super()`
  - `open(f, "r")` → `open(f)`
  - `collections.Mapping` → `collections.abc.Mapping` (the same class object)
- Removing the `typing` imports those rewrites left unused.
- Version strings in config: `requires-python`, `.python-version`, ruff
  `target-version`, mypy `python_version`, the Dockerfile base image tag, and
  the CI `python-version`.

**Report in the guide and apply only after the user confirms:**
- Dependency pin bumps. Even a patch bump is new code running in production.
- Fixes for stdlib behavior changes, e.g. adding `.value` where a `(str, Enum)`
  member is formatted.

**Never:**
- Refactors, renames, reformatting, or new abstractions.
- Changing logic, or "while I'm here" cleanups.
- f-string conversion, unless the user explicitly asks
  (`--include-string-format`). It is behavior-preserving but rewrites many
  lines and makes the diff hard to review.
- Deleting `sys.version_info` branches.
- `StrEnum` conversion, which changes what `str()` returns.

When in doubt whether a change is syntax-only, leave it out and list it in the
guide.

## Bundled scripts

All four live in `scripts/`. They are stdlib-only Python, need `uv` on PATH, and
work the same on Linux/WSL and Windows. Run them with a Python ≥ 3.11
(`uv run --no-project --python 3.11 python scripts/<name>.py ...` works anywhere).
Each prints Markdown that can be pasted straight into the guide.

| Script | What it does | Changes files? |
| --- | --- | --- |
| `check_deps.py --python 3.11 --from 3.8` | Installs the pinned dependencies into a throwaway venv on the target Python. It works in rounds: find the failing package, look up the oldest release on PyPI with a compatible wheel, retry. Its output is a **validated** table of minimal bumps, direct or transitive (with the parent that pins it). With `--from`, it also reports **resolution drift**: packages that land on a new major version only because the Python changed. Reads `uv.lock`, `requirements.txt`, or `pyproject.toml` (PEP 621 or classic Poetry). | No |
| `scan_upgrade_risks.py --from 3.8 --to 3.11` | Static scan for stdlib removals and behavior changes in the (from, to] range, with file:line locations. | No |
| `upgrade_syntax.py --target 3.11` | Runs ruff's pyupgrade (`UP`) rules in isolated mode, **safe fixes only**. Rules that aren't pure syntax are excluded. Prunes the `typing` names the rewrite left unused. Use `--dry-run` to preview. | Yes |
| `check_structure.py [--rev HEAD]` | Compares every changed file with git `HEAD`: definition inventory, signatures, and bodies with annotations stripped. Exit 0: only annotations and imports changed. Exit 1: code changes to justify. Exit 2: structure changed. | No |

`check_deps.py` can take several minutes when old pins build from source; run
it in the background while you do the scan.

## Workflow

### 0. Preflight

- Find the project root and the **current** version from every place it is
  declared: `requires-python` or `[tool.poetry.dependencies] python`,
  `.python-version`, the Dockerfile `FROM` tag, `.github/workflows/*`
  `python-version`, `mypy.ini` / `ruff.toml`. If they disagree (e.g. Poetry
  says `^3.8`, `.python-version` says 3.9, Docker uses 3.8), treat the
  *deployed* one (Docker/CI) as the true current version and note the
  mismatch in the guide.
- The **target** comes from the user. If they don't give one, use 3.11, the
  team standard.
- Check `git status`. The syntax step rewrites files in place, and
  `check_structure.py` compares against git, so uncommitted edits to `.py`
  files would get mixed into the diff. If `.py` files are dirty, ask the user
  to commit or stash first, or create a worktree. Work on a branch such as
  `chore/python-3.11-upgrade`; don't commit unless asked.

### 1. Baseline

Record the current state so you can later show you *didn't* introduce anything:

```bash
uvx ruff check --isolated --select F --output-format concise . | tail -1   # undefined names / unused imports
```

Also note whether the project has tests or a mypy config. You'll re-run
those on the target later.

### 2. Dependencies (report, then confirm)

Run `check_deps.py --python <target> --from <current>`. How to read the result:
- **"installs as pinned":** nothing to do.
- **Direct bump within the same major version** (e.g. `pyodbc 4.0.30 → 4.0.35`):
  low risk, but still list it.
- **A bump across a major version, or a 0.x minor bump** (0.x releases break
  freely; e.g. `uvicorn 0.11 → 0.2x`), and **transitive** bumps (the parent
  must be raised until it allows the needed version): these are decisions.
  Look up the changelog of each such package for breaking changes, and
  summarize what the project actually uses from it.
- **Resolution drift** is the trap an install check can't see. A loose pin
  such as `numpy<=2.0.0` gives numpy 1.x on 3.8 and 2.x on 3.11. The install
  succeeds, and then a library still using `np.float_` fails on import. For
  each drifted package, propose pinning the old major line (`numpy<2`)
  unless you've verified the code against the new one. That's the
  behavior-preserving choice.
- Packages that build from source need system libraries that may be missing
  on the machine or in Docker, e.g. `unixodbc-dev` for `pyodbc`. Name them.

Present the bump table to the user and apply only the bumps they approve,
using the project's own tool (`uv add 'pkg==x.y'` for uv projects, editing
`pyproject.toml` for Poetry). If they approve none, finish the syntax work
anyway and mark the deps as a blocker in the guide.

### 3. Stdlib and behavior risks (report)

Run `scan_upgrade_risks.py`. For each finding, decide which kind it is:
- **Identical-object replacement** (e.g. `collections.Mapping` →
  `collections.abc.Mapping`): allowed, apply it.
- **Needs a code change to keep the old behavior** (e.g. formatting a
  `(str, Enum)` member now gives `Cls.MEMBER`; `random.sample(set)` raises):
  put the exact file:line and the minimal fix in the guide, and ask before
  applying.
- **Deprecation only:** list it and don't change it.

The scanner is a pattern list, not proof of absence. Also search the code for
anything version-dependent it can't see: `sys.version_info` checks,
`# type: ignore` notes that mention a version, and C extensions.

### 4. Syntax modernization (apply)

```bash
python scripts/upgrade_syntax.py --target 3.11 --dry-run   # preview counts
python scripts/upgrade_syntax.py --target 3.11             # apply
```

Some frameworks read annotations **at runtime**: pydantic models, FastAPI
`response_model=` and parameters, dataclasses read via `get_type_hints`,
typer, SQLAlchemy 2 `Mapped[...]`. `list[X]` and `X | Y` are only safe there
if the framework version *on the target Python* supports them. Don't guess
from a version table. Verify it in step 6 by importing the modules and, for
FastAPI, generating the OpenAPI schema. If that fails, revert those files and
re-run with `--runtime-annotation-files 'app/schemas/*.py' ...` to exclude
them, and note it in the guide.

### 5. Version strings in config (apply)

Update the declarations found in step 0 to the target:
- `requires-python` (or the Poetry `python` constraint)
- `.python-version`
- ruff `target-version = "py311"`
- mypy `python_version = 3.11`
- the Dockerfile base image tag. Keep the same image family, e.g.
  `tiangolo/uvicorn-gunicorn:python3.8` → `:python3.11`, and check the tag
  exists.
- the CI workflow `python-version`

Nothing else in those files.

### 6. Verify

All of these, on the **target** Python:

1. `python scripts/check_structure.py` must exit 0 or 1, never 2. For exit 1,
   justify each listed definition in the guide against the rewrite that
   touched it:
   - **body:** equivalent aliases, e.g. `IOError` → `OSError`, dropped `"r"` mode.
   - **bases:** `(object)` removed.
   - **decorators:** usually `response_model=List[X]` → `list[X]`, which is
     runtime-evaluated; that's what item 4 of this list proves.
   Anything you can't tie to a specific safe rule gets reverted.
2. `python -m compileall -q <package>` succeeds.
3. `uvx ruff check --isolated --select F --target-version py3XX .` shows no
   more findings than the baseline, and none new in the changed files.
4. **Import smoke test** in a venv with the (approved) target dependencies:
   import every changed module. Build that venv from the project's **lock
   file** (`uv.lock`, `poetry.lock`) where one exists, not a fresh resolve of
   `pyproject.toml`. Unpinned transitive dependencies can resolve to
   combinations that were already broken on the old Python, and that failure
   isn't the upgrade's fault. If an import fails, re-run the same import on
   the old Python with the original code before blaming the upgrade.
   For FastAPI apps, go further and compare the schema. Dump
   `json.dumps(app.openapi(), sort_keys=True)` for the original code on the
   old Python and for the rewritten code on the target. **Byte-identical
   output proves** the runtime-evaluated annotations (`response_model=`,
   pydantic fields) mean exactly what they did before. Don't copy `.env`
   files to make the app import, and respect any permission rules that
   block them; set only the variables the import actually needs.
5. The test suite and mypy, if the project has them. Compare with the
   baseline, don't just require green. Pre-existing failures are fine;
   new ones are not.

If a check can't run (e.g. dependencies not approved yet, so step 4 can't
install), say so explicitly in the guide and the report. Don't claim it passed.

### 7. Write the guideline

Fill `assets/guide-template.md` and save it as
`docs/python-upgrade-<from>-to-<to>.md`, or put it in the project's
`release/<TICKET>/` folder if that is where it keeps change documents. Paste
the scripts' Markdown output into the matching sections rather than
re-summarizing it; the tables carry the file:line evidence reviewers need.

### 8. Report

Tell the user:
- what was applied: file and fix counts, config files touched
- what is waiting for their decision: dependency bumps and behavior fixes,
  each with its risk
- which verification steps passed, failed, or couldn't run
- where the guide is

Leave everything uncommitted.
