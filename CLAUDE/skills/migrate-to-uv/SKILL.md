---
name: migrate-to-uv
description: Migrates a Python project off Poetry and/or Conda-managed dependencies onto uv — backs up the old configuration to legacy/, parses dependencies (handles both PEP 621 dependency lists and classic [tool.poetry.dependencies] tables), runs uv init/uv venv/uv add, installs ruff+mypy config, merges the new interpreter path into .vscode/settings.json, and verifies the result. Use this whenever the user asks to migrate, convert, or switch a project from Poetry or Conda to uv, says things like "get this repo off poetry", "ditch conda for uv", "modernize our dependency management", or is clearly dealing with a project that still has a Poetry-style pyproject.toml, poetry.lock, or Conda environment.yml lying around — even if they never say the word "migrate" or "uv" explicitly.
---

# Migrate to uv

A Python project that still depends on Poetry and/or Conda for dependency management needs its `pyproject.toml` rewritten, its dependencies re-added through uv, and its editor config repointed at the new `.venv` — all without losing the ability to roll back if something about the target project doesn't translate cleanly. This skill walks through that end-to-end, actually running the migration rather than just handing the user a checklist.

## Before you start

**Back up before you touch anything.** The whole point of this workflow is that it's safe to run even if the target project has uncommitted work: everything Poetry/Conda-related gets copied into `legacy/` before it is deleted or overwritten, and nothing is deleted until its backup is confirmed on disk. Don't skip or reorder the backup step to save time — an untracked `poetry.lock` or an in-progress `pyproject.toml` edit has no other safety net.

**Check git status first.** If the target is a git repo, run `git status`. Uncommitted changes aren't a blocker, but they're worth surfacing to the user before you start rewriting `pyproject.toml` — a quick "you've got uncommitted changes in X, want to commit/stash those first, or should I proceed?" costs one message and avoids tangling migration changes with unrelated work-in-progress.

**Confirm you're in the right place.** Resolve the project root (ask if ambiguous), and confirm it actually has a `pyproject.toml` or Conda environment to migrate from. If `uv.lock` already exists and there's no Poetry/Conda marker left, the project is probably already migrated — say so and ask whether the user wants you to proceed anyway rather than assuming.

## Step 1 — Detect what's there

- Read `pyproject.toml`. Check `[build-system].build-backend` and `.requires` for anything containing `poetry` — that's your signal this is a Poetry project, not just a project that happens to use uv-incompatible syntax.
- Detect an active Conda environment properly: check `$env:CONDA_DEFAULT_ENV` (or `$CONDA_DEFAULT_ENV` on POSIX) together with whether the `conda` command is actually on PATH. (The script this skill replaces had a bug here — it gated the Conda-export step on a variable, `$CondaCommand`, that was never assigned anywhere, so that block silently never ran, even with Conda active. Don't reintroduce that: check a variable you've actually set.)
- If a Conda env is active, you'll export it in Step 2; if not, that's fine — plenty of Poetry projects don't use Conda at all, only note it as skipped rather than treating it as an error.

## Step 2 — Back up to `legacy/`

Create `legacy/` if it doesn't exist. Copy into it, for anything that exists in the project:

- `pyproject.toml` → `legacy/pyproject.poetry.toml`
- Any `*.lock` file except `uv.lock` (covers `poetry.lock` and friends)
- `requirements.txt`, if present
- `Dockerfile`, if present (reference only — you won't be editing the live one automatically; see Step 6)
- If a Conda env is active: `conda env export --from-history` → `legacy/conda-env.yml`, and `conda list --explicit` → `legacy/conda-explicit-lock.txt`

If `legacy/` already has files from a previous run, ask the user whether to overwrite or reuse them rather than silently clobbering — someone may have hand-edited a backup for a reason.

Do not proceed to Step 4 (which deletes the live `pyproject.toml`) until you've confirmed the backup files actually landed on disk.

## Step 3 — Parse dependencies

Run the bundled parser against the **backed-up** copy, not the live file — that way later steps can't affect what gets parsed:

```bash
python scripts/parse_pyproject.py legacy/pyproject.poetry.toml
```

(Use whatever `python` is on PATH — Conda's, if a Conda env is active. Any Python 3.11+ works since it only needs stdlib `tomllib`.)

This prints JSON with `requires_python`, `dependencies`, `dev_dependencies`, and ready-to-run `uv_add_dependencies` / `uv_add_dev` command strings. It's a proper TOML parser rather than a regex, so it correctly handles both dependency shapes you'll encounter in the wild:

- Modern Poetry writing PEP 621 lists under `[project].dependencies` (with Poetry's `"pkg (>=1.0,<2.0)"` paren style)
- Classic Poetry writing a `[tool.poetry.dependencies]` table (`pkg = "^1.0"`) — a plain regex on `dependencies = [...]` misses this shape entirely, so don't fall back to eyeballing the file if the parser reports an empty dependency list; check which table the project actually uses.

It also always folds in `mypy` and `ruff` as dev dependencies if they're not already listed (this org's projects standardize on both — see the root `CLAUDE.md` Commands section). Pass `--no-default-devtools` if the target project shouldn't get them.

## Step 4 — Run the migration

Only after the backup is confirmed:

1. Delete the live `pyproject.toml` and any non-`uv.lock` lock files — `uv init` refuses to run in a directory that already has a `pyproject.toml`, and you already have a safe copy in `legacy/`.
2. `uv init` (check `uv init --help` first if you're unsure of current flags — uv's CLI changes between versions, don't assume flags from memory). Set the project name and Python version to match what the parser reported, if uv's init doesn't infer them correctly on its own. `uv init` also scaffolds a starter `main.py` (and sometimes `README.md`/`.python-version`/`.gitignore`) as if this were a brand-new project — remove whichever of those didn't exist in the project before you ran it, so the migration doesn't leave placeholder files behind in someone's real codebase.
3. `uv venv`
4. Run the `uv_add_dependencies` command from Step 3's output, then the `uv_add_dev` command.
5. Copy `assets/mypy.ini` and `assets/ruff.toml` into the project root — but only if the project doesn't already have its own (check first; don't clobber a customized config someone already wrote).

## Step 5 — Editor config and docs

- Read the project's `.vscode/settings.json` if it exists (treat missing as `{}`). Merge in `python.defaultInterpreterPath` (pointing at the new `.venv`), `python-envs.workspaceSearchPaths`, and `terminal.integrated.cwd` — merge, don't overwrite, so you don't blow away unrelated settings someone already has in there.
- Render `assets/README_LEGACY.template.md` → `legacy/README_LEGACY.md`, filling in `{ProjectName}` and `{Timestamp}`. This is the rollback doc.
- Render `assets/README_MIGRATION.template.md` → `legacy/README_MIGRATION.md`, filling in `{ProjectName}`, `{Timestamp}`, and `{UvAddDependencies}` (a fenced code block with the actual `uv add` / `uv add --dev` commands you ran, plus the "Copy `mypy.ini`/`ruff.toml`" note if you had to add them). Unlike the script this skill replaces — which generated this file as an instruction sheet for the user to follow by hand — you've already executed the steps, so this document is a record of what happened, useful for anyone reviewing the diff later.

## Step 6 — Verify, then flag what's left for a human

Run and show the user:

```bash
python --version
uv --version
uv pip list
```

Two things are deliberately **not** automatic, and you shouldn't do them without asking first:

- **Dockerfile changes.** If the project has a `Dockerfile`, propose the Poetry→uv diff (template in `README_MIGRATION.md`) and get confirmation before editing it — build files affect CI/CD, and a wrong assumption about the base image or entrypoint is expensive to unwind.
- **Committing.** Never commit automatically. Tell the user the migration is done and ready to review, and give them the `git add`/`git commit` command to run themselves once they're satisfied.

## Reference

- `scripts/parse_pyproject.py` — the dependency parser from Step 3. Self-contained, stdlib-only.
- `assets/README_LEGACY.template.md`, `assets/README_MIGRATION.template.md` — doc templates rendered in Step 5.
- `assets/mypy.ini`, `assets/ruff.toml` — config templates copied in Step 4. If you're working inside the `cr-misc-function` repo itself (or it's checked out locally), these mirror `templates/mypy.ini` and `templates/ruff.toml` there — check that repo for a newer version if these look stale, since it's the canonical source.
