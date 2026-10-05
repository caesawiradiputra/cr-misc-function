# uv Migration Guide for {ProjectName}

**Generated:** {Timestamp}
**Target Python:** {PythonVersion} (the lowest version the original `pyproject.toml` allowed)

This guide moves the project from Poetry (and a Conda env, if it had one) to uv
on **Linux / WSL 2**. uv installs and manages Python itself, so you don't need
Conda.

> The original files are backed up in `legacy/`. See `README_LEGACY.md` to roll back.

---

## Prerequisites

- **uv is installed.** Run `curl -LsSf https://astral.sh/uv/install.sh | sh`,
  then open a new shell and check that `uv --version` works. If `uv` works in
  your own shell but not inside Claude Code or `sudo`, see the "`uv`/`uvx` not
  found" section in `cr-misc-function/docs/claude-code-wsl-setup.md`.
- **Run every command from the project root** (the folder that contains
  `legacy/`).

---

## Migration Steps

### Step 1 - Install the Python Runtime

```bash
uv python install {PythonVersion}
uv python list --only-installed   # Confirm {PythonVersion} is listed
```

To move to a newer Python instead (3.11 is the team standard), replace
`{PythonVersion}` with that version in every command in this guide. In Step 4,
also replace `{RuffTarget}` with the matching tag (e.g. `py311`).

### Step 2 - Replace the Poetry pyproject.toml With a uv Project

`uv init` won't run in a folder that already has a `pyproject.toml`, and a
freshly pulled Poetry project always has one. Remove the Poetry files first.
Both are backed up in `legacy/`, and the `test` guard removes nothing if that
backup is missing:

```bash
test -f legacy/pyproject.poetry.toml && rm -f pyproject.toml poetry.lock

uv init --bare --python {PythonVersion}
uv python pin {PythonVersion}
uv venv
```

This creates:

- `pyproject.toml`: a minimal uv project with no build system, so it is not packaged
- `.python-version`: pins the interpreter for uv and for the IDE
- `.venv/`: the virtual environment (`.venv/bin/python`)

`uv.lock` is created by the first `uv add` in Step 3.

### Step 3 - Add Dependencies

{UvAddDependencies}

### Step 4 - Add Lint and Type-Check Config

Copy the shared configs into the project root, unless the project already has
its own. The shared templates target Python 3.11, so each copy is pointed at
Python {PythonVersion}. Otherwise ruff and mypy would check the code as if it
ran on 3.11 and miss syntax or stdlib usage that breaks on {PythonVersion}:

```bash
if [ ! -f ruff.toml ]; then
    cp '{TemplatesDir}/ruff.toml' ./ruff.toml &&
    sed -i 's/^target-version = .*/target-version = "{RuffTarget}"/' ruff.toml
fi
if [ ! -f mypy.ini ]; then
    cp '{TemplatesDir}/mypy.ini' ./mypy.ini &&
    sed -i 's/^python_version = .*/python_version = {PythonVersion}/' mypy.ini
fi
```

If the project already had its own `ruff.toml` / `mypy.ini`, check that
`target-version` / `python_version` match {PythonVersion} yourself.

<!-- IF:old-mypy -->
> **Note (Python {PythonVersion}):** current mypy (2.x) runs on, and type-checks
> code for, Python 3.10 or newer only. For this project, `uv add --dev mypy` in
> Step 3 therefore resolves an older mypy: 1.14.x on 3.8, 1.20.x on 3.9. That
> is the last release supporting {PythonVersion}, and it no longer gets fixes.
> To use current mypy, move the project to Python 3.10+ (3.11 is the team
> standard) in Step 1. Ruff is unaffected, since it supports py37 and newer.
> In Claude Code, the `upgrade-python-version` skill does the code side of
> that move: dependency bumps, syntax-only rewrites, and an upgrade guide.
<!-- ENDIF:old-mypy -->

### Step 5 - Configure VS Code

Add this to `.vscode/settings.json`:

```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/{ProjectName}/.venv/bin/python",
  "python-envs.workspaceSearchPaths": [
    "./**/.venv"
  ],
  "terminal.integrated.cwd": "${workspaceFolder}/{ProjectName}"
}
```

If the workspace root *is* the project folder, not an umbrella folder that
contains it, drop the `{ProjectName}/` segment from both paths.

You don't need a Conda terminal profile. The Python extension activates
`.venv` for you. In a plain shell, run `source .venv/bin/activate`, or put
`uv run` in front of each command.

### Step 6 - Verify Installation

```bash
uv --version
uv run python --version    # Should show Python {PythonVersion}.x
uv pip list                # All dependencies from Step 3
uv run ruff check .        # May report existing issues; that's fine for now
```

### Step 7 - Update Dockerfile

If the project has a Dockerfile, switch it to uv:

#### Old (Poetry)

```dockerfile
RUN pip install poetry
COPY pyproject.toml poetry.lock ./
RUN poetry install --no-dev
```

#### New (uv)

```dockerfile
# Install uv package manager
RUN pip install uv

# Copy dependency manifests first for better layer caching
COPY pyproject.toml uv.lock .python-version ./

# Install Python dependencies using uv (frozen lock for reproducibility)
RUN uv sync --frozen --no-dev

ENV PATH="/app/.venv/bin:$PATH"

# Copy application code
COPY . .
```

> The base image's Python must match `.python-version` ({PythonVersion}).
> Otherwise `uv sync` tries to download its own Python at build time, and that
> can fail on the corporate network.

### Step 8 - Commit

```bash
git add pyproject.toml uv.lock ruff.toml mypy.ini
git add -f .python-version   # -f: many Python .gitignore templates ignore it, but Docker/CI need it
git rm --cached --ignore-unmatch --quiet poetry.lock   # Stage the poetry.lock removal
git commit -m "chore: migrate from Poetry to uv"
```

Also commit `.vscode/settings.json` if it lives in this repo rather than in the
umbrella workspace folder.

---

## Useful uv Commands

```bash
uv sync              # Install all dependencies (creates/updates .venv)
uv add package-name  # Add a new package
uv add --dev pytest  # Add a dev dependency
uv remove package    # Remove a package
uv pip freeze        # Show all installed packages
uv lock              # Update uv.lock file
uv run script.py     # Run a Python script with the project venv
```

---

## Troubleshooting

**Issue: `uv: command not found`**

- Open a new shell after installing, or add `~/.local/bin` to `PATH`. See the
  PATH section in `cr-misc-function/docs/claude-code-wsl-setup.md`.

**Issue: `uv init` fails with "Project is already initialized"**

- The Poetry `pyproject.toml` is still there. Run the removal line from Step 2 first.

**Issue: `uv add` cannot resolve a version**

- A Poetry pin may not support Python {PythonVersion}. Loosen that package's pin
  in the Step 3 command, or choose a different Python in Step 1.
- Any git, path, or URL dependency listed as a manual item in Step 3 needs its
  own `uv add` (`uv add git+https://...` or `uv add ./path`).

**Issue: `uv add` / `uv sync` fails with "Failed to build `<package>`"**

- Some packages (e.g. old `pyodbc`, `psycopg2`, `mysqlclient`) have no wheel
  for this Python and are built from source. Conda used to provide the native
  libraries they need; on WSL, install them with apt. Example:
  `pyodbc` → `fatal error: sql.h: No such file or directory`:

  ```bash
  sudo apt install build-essential unixodbc-dev   # pyodbc
  sudo apt install libpq-dev                      # psycopg2 (non-binary)
  sudo apt install default-libmysqlclient-dev pkg-config   # mysqlclient
  ```

- Or raise the pin to a version that ships a prebuilt wheel for Python {PythonVersion}
  (e.g. `'pyodbc>=4.0.39,<5'`).
- A wheel removes the *build* dependency but not the *runtime* one. `pyodbc`
  still needs `libodbc.so.2` (`sudo apt install unixodbc`) and, for SQL Server,
  Microsoft's ODBC driver (`msodbcsql18`).

**Issue: `pip`, `pytest`, etc. not found in the terminal**

- Run `source .venv/bin/activate`, or put `uv run` in front of the command
  (`uv run pytest`).

**Issue: `.venv` is not picked up by the Python extension**

- Check that `python.defaultInterpreterPath` in `.vscode/settings.json` points
  to `.venv/bin/python`. Then reload the window and wait for the Python
  extension to index.

**Issue: Need to roll back to Poetry**

- See `README_LEGACY.md` for restoration instructions.

---

## See Also

- **README_LEGACY.md**: how to restore the Poetry setup
- [uv Documentation](https://docs.astral.sh/uv/)

---

**Generated by:** dev-migrate-conda-poetry-to-uv.sh
