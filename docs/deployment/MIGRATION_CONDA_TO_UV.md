# Migration Guide: Conda → uv

## Project

cr-misc-function

## Objective

Migrate from per-project Conda environment to:

- Conda (Python runtime only)
- uv (project dependency manager)

Maintain rollback capability.

---

## Phase 0: Safety Snapshot (Legacy Archive)

Before modifying anything, archive the existing Conda environment and project configuration.

### 1. Activate your conda environment

Ensure you're in the named conda environment (not base):

```bash
conda activate cr-misc-function-env
```

### 2. Run automated backup script

From project root, run:

```powershell
.\scripts\powershell\dev-backup_legacy.ps1
```

This script automatically:

- Detects the current Conda environment
- Exports environment spec: `conda env export --from-history`
- Creates `legacy/` folder if not present
- Backs up `poetry.lock` (if exists)
- Backs up `pyproject.toml` (as `pyproject.poetry.toml`)
- Backs up Conda exports (`conda-env.yml`, `conda-explicit-lock.txt`)
- Stores exported conda environment as `conda-env-<envname>.yml`
- Generates `legacy/README.md` documentation

Use `-Force` flag to overwrite existing backups:

```powershell
.\scripts\powershell\dev-backup_legacy.ps1 -Force
```

### 3. Manual export (Optional)

If you prefer to manually export with different options:

```bash
conda env export > legacy/conda-env-explicit.yml
conda list --explicit > legacy/conda-explicit-lock.txt
```

### 4. Commit legacy folder

Once backed up, commit to Git:

```bash
git add legacy/
git commit -m "docs: archive legacy Conda environment for rollback"
```

**At this point rollback is guaranteed.**

---

## Phase 1: Prepare Clean Python Runtime

Create minimal Conda runtime using the template:

```bash
conda env create -f .\templates\conda\py311\environment.yml
```

This environment must NOT contain project dependencies.

---

## Phase 2: Initialize uv in Project

Activate runtime:

```bash
conda activate py311
```

### For New Project

Inside project root:

```bash
uv init
```

Edit `pyproject.toml`:

- Add `requires-python = ">=3.11"`
- Add only direct project dependencies

### For Existing Project (with pyproject.toml)

If `pyproject.toml` already exists (e.g., from Poetry or pip-tools):

#### 1. Update build system

Replace Poetry's build backend with uv-compatible hatchling:

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

#### 2. Verify project metadata

**Important**: If migrating from Poetry, you can keep the existing `pyproject.toml` as-is. uv will read and respect the dependency specifications.

If the file has Poetry-specific sections, remove:

- `[tool.poetry]` sections
- `[tool.poetry.dependencies]` → convert to `[project.dependencies]`
- `[tool.poetry.dev-dependencies]` → convert to `[project.optional-dependencies] dev`

Update `requires-python = ">=3.11"` in the `[project]` section if not already set.

#### 3. Create virtual environment

```bash
uv venv
```

This creates a `.venv/` virtual environment in the project.

- Do NOT copy full conda list

---

## Phase 3: Create uv Virtual Environment

```bash
uv venv
uv sync
```

This creates:

- `.venv/`
- `uv.lock`

Commit:

- `pyproject.toml`
- `uv.lock`

Do NOT commit `.venv`

---

## Phase 4: Validation

Run application:

```bash
uv run python -m your_entrypoint
```

Run tests:

```bash
uv run pytest
```

Compare behavior with old Conda environment.

If missing dependencies, add them directly using `uv add`:

```bash
uv add package_name
```

For development dependencies:

```bash
uv add --dev pytest
```

This automatically updates `pyproject.toml`, `uv.lock`, and installs into `.venv` in one step.

Repeat until all dependencies are resolved.

---

## Phase 4.5: Configure VS Code Workspace Settings

Update `.vscode/settings.json` to point to the uv-managed virtual environment:

```json
{
    "python.defaultInterpreterPath": "cr-misc-function/.venv/Scripts/python.exe"
}
```

This ensures:

- IntelliSense uses the correct Python version
- Linters and formatters use the correct environment
- Debugger runs against the uv-managed dependencies

Reload VS Code or click "Python: Select Interpreter" to confirm the change.

---

## Phase 4.6: Alternative - Quick Debug with Conda Environment

If you need to debug using the original Conda environment (e.g., to test with specific conda-installed libraries or to bypass the uv virtual environment):

### Activate Conda Environment (PowerShell)

```powershell
(C:\Users\203715\AppData\Local\miniconda3\shell\condabin\conda-hook.ps1) ; (conda activate py311)
```

Or for Python 3.9:

```powershell
(C:\Users\203715\AppData\Local\miniconda3\shell\condabin\conda-hook.ps1) ; (conda activate py39)
```

### Use Cases

- **Debugging**: Run the application with conda libraries to isolate issues
- **Library Testing**: Verify behavior with conda-installed packages before switching back to uv
- **Fallback**: Quick access to the original environment without decommissioning it

### Return to uv Environment

```powershell
conda deactivate
# Then activate your uv .venv
.\.venv\Scripts\Activate.ps1
```

---

## Phase 5: Decommission Old Conda Env

Once validated:

```bash
conda remove -n cr-misc-function-env --all
```

The project now depends on:

- Conda runtime (py311 or py39)
- uv-managed .venv

---

## Rollback Procedure (If Needed)

To restore exact previous environment:

```bash
conda create --name rollback-env --file legacy/conda-explicit-lock.txt
```

Or recreate high-level env:

```bash
conda env create -f legacy/conda-env-cr-misc-function.yml
```

---

## Final Architecture

| Component | Purpose |
| --------- | ------- |
| Conda (py39) | Python runtime only |
| uv | Project dependency manager |
| `.venv` | Isolated per-project virtual environment |
| `uv.lock` | Deterministic dependency lock |

---

## Important Rules

- Do NOT install project dependencies into Conda
- Do NOT use `pip install` manually
- Always use `uv sync`
- Commit `uv.lock`
- Keep `legacy/` folder untouched
