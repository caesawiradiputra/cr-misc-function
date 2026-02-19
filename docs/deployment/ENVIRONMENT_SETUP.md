# Conda + Poetry Hybrid Architecture Guide

**Status**: ✅ Production Ready
**Platform**: Windows (No Admin Required)
**Last Updated**: February 2026

---

## Table of Contents

1. [Goal](#goal)
2. [Architecture Overview](#architecture-overview)
3. [Installation & Setup](#installation--setup)
4. [Configuration](#configuration)
5. [Dependency Management](#dependency-management)
6. [Pre-Rebuild Safety Check](#pre-rebuild-safety-check-detect-undeclared-packages)
7. [Docker Integration](#docker-integration)
8. [Troubleshooting](#troubleshooting)
9. [Mental Model & Best Practices](#mental-model--best-practices)

---

## Goal

Establish a **clean, non-corrupt, maintainable development environment** using a hybrid approach:

| Tool          | Responsibility                                                            |
| ------------- | ------------------------------------------------------------------------- |
| **Miniconda** | Python version + Java + system/non-Python dependencies                    |
| **Poetry**    | Python dependency management, locking, reproducible builds                |
| **Docker**    | Containerized deployments with `micropipenv` (no Conda inside containers) |

**Key Principle**: Clear separation of concerns. No corruption. No PATH confusion.

---

## Architecture Overview

### Directory & Environment Layout

```text
Miniconda Installation
 └── base environment
      └── poetry (tool only, installed via pip)

Project Conda Environment (cr-misc-function-env)
 ├── python=3.11
 ├── openjdk
 └── system libraries

Project Folder
 ├── pyproject.toml
 ├── poetry.lock
 ├── environment.yml (optional Conda lock file)
 └── .venv/  ← Created by poetry install (inside project)
```

### Golden Rule

> **Poetry is a TOOL, not a library.**
> It does NOT belong inside project conda environments.
> It lives in Miniconda base only.

---

## Installation & Setup

### Step 1: Install Poetry (One Time Only)

Activate the Miniconda base environment and install Poetry as a global tool:

```powershell
# Activate base environment
conda activate base

# Install Poetry (latest stable version)
pip install --upgrade poetry

# Verify installation
poetry --version
```

**Expected Output**:

```text
Poetry (version 1.8.x)
```

---

### Step 2: Make Poetry Available in All Conda Environments

Poetry is installed in the base environment's `Scripts` folder. To use it from any conda environment, add it to your user PATH.

#### Find Your Miniconda Scripts Path

```powershell
# Activate base
conda activate base

# Find Poetry executable
Get-Command poetry

# or
where.exe poetry

# Look at the "Source" line in the output
```

**Example Output**:

```text
CommandType     : Application
Name            : poetry
Source          : C:\Users\203715\miniconda3\Scripts\poetry.exe
Version         : 1.8.x
```

**Note your path**: `C:\Users\203715\miniconda3\Scripts` (replace `203715` with your username)

#### Add to User PATH (No Admin Required)

```powershell
# Add Poetry scripts to PATH permanently
# Replace the path with YOUR actual path
setx PATH "$($env:PATH);C:\Users\203715\miniconda3\Scripts"
```

**Then**:

1. Close the current terminal
2. Open a new terminal
3. Test in project environment:

```powershell
conda activate cr-misc-function-env
poetry --version
```

**If version prints → Setup complete ✅.**

---

### Step 3: Create a Project Conda Environment

Create a conda environment with only **system-level dependencies**. Do NOT install Python libraries here.

```powershell
# Create new environment with Python 3.11 and Java
conda create -n cr-misc-function-env python=3.11 openjdk

# Activate it
conda activate cr-misc-function-env
```

**Important**:

- ❌ Do NOT install Python libraries via `conda install`
- ❌ Do NOT install Poetry in this environment
- ✅ Only system dependencies: Python version, Java, system libs

---

### Step 4: Configure Poetry (Run Once Per Project)

Inside your project directory, configure Poetry to keep `.venv` inside the project folder and use the active conda Python:

```powershell
cd c:\Users\203715\Documents\Repo\cr-misc-function

poetry config virtualenvs.in-project true
poetry config virtualenvs.prefer-active-python true
```

**What this does**:

- `virtualenvs.in-project true` → Creates `.venv` folder INSIDE project (not in AppData)
- `virtualenvs.prefer-active-python true` → Uses currently activated Python (from conda env)

---

### Step 5: Install Python Dependencies

Ready to install? Simple:

```powershell
# Make sure you're in project directory
cd c:\Users\203715\Documents\Repo\cr-misc-function

# Activate project conda environment
conda activate cr-misc-function-env

# Install dependencies from pyproject.toml + poetry.lock
poetry install
```

**What gets created**:

```text
./.venv/
  ├── Lib/site-packages/  (all Python packages)
  ├── Scripts/            (executables, ipython, etc.)
  └── pyvenv.cfg
```

**Result**: All Python dependencies isolated in `.venv`, no conda pollution ✅

---

## Configuration

### Poetry Configuration Files

After running the setup commands above, Poetry creates a config file at:

```text
C:\Users\<username>\AppData\Roaming\pypoetry\config.toml
```

You can view current settings:

```powershell
poetry config --list
```

**Key settings for this project**:

| Setting                            | Value  | Reason                                |
| ---------------------------------- | ------ | ------------------------------------- |
| `virtualenvs.in-project`           | `true` | Keep `.venv` inside project folder    |
| `virtualenvs.prefer-active-python` | `true` | Use conda Python, not system Python   |
| `installer.modern-installation`    | `true` | Use modern pip behavior (recommended) |

---

## Dependency Management

### Adding a New Dependency

Only use Poetry to add dependencies:

```powershell
poetry add requests              # Add latest version
poetry add "requests>=2.28.0"    # Add with version constraint
poetry add pytest --group dev    # Add to dev group
```

**Never do this**:

```powershell
❌ conda install requests
❌ pip install requests
❌ poetry install (in polluted environment)
```

### Updating Dependencies

Update to latest versions respecting constraints:

```powershell
poetry update                    # Update all
poetry update requests pytest    # Update specific packages
```

Creates fresh `poetry.lock` with resolved versions.

### Installing from poem.lock (Deterministic)

To reinstall exact versions from lock file:

```powershell
poetry install --no-root
```

---

## Pre-Rebuild Safety Check: Detect Undeclared Packages

### Why This Step Is Important

Before performing a clean rebuild of your Conda environment, you **MUST** verify that no Python packages were installed manually via:

```powershell
❌ pip install <package>
❌ conda install <python-package>
```

These installs bypass `pyproject.toml` and corrupt reproducibility.

**If someone installed a package like**:

```powershell
pip install requests
conda install pandas
```

But did NOT run:

```powershell
poetry add requests
poetry add pandas
```

**Then**:

- `pyproject.toml` is incomplete
- `poetry.lock` is incomplete
- Docker builds may fail
- Rebuild will silently lose dependencies

### Using the Detection Script

We provide an automated detection script to prevent this:

**Location**: [scripts/python/detect_undeclared_packages.py](../../scripts/python/detect_undeclared_packages.py)

#### When To Run This

Run this **BEFORE**:

- Deleting a conda environment
- Running a clean rebuild
- Regenerating `poetry.lock`
- Creating a production Docker image

#### How To Run

Activate your project conda environment:

```powershell
conda activate cr-misc-function-env
```

Then run:

```powershell
python scripts/python/detect_undeclared_packages.py
```

#### Possible Outputs

**Case 1 — Everything Clean** ✅

```text
✓ No undeclared manually installed packages found.
```

Safe to rebuild.

**Case 2 — Undeclared Packages Found** ⚠️

```text
⚠ Manually installed but undeclared packages:

  - requests==2.32.4
  - rich==13.7.0
```

This means someone used `pip install` or `conda install`.

### How To Fix Undeclared Packages

#### Step 1: Auto-Suggest Mode

Use auto-suggest to generate Poetry commands:

```powershell
python scripts/python/detect_undeclared_packages.py --auto-add
```

Example output:

```text
Suggested commands:

poetry add requests
poetry add rich
```

#### Step 2: Execute Suggested Commands

```powershell
poetry add requests
poetry add rich
```

This updates:

- `pyproject.toml` (adds to dependencies)
- `poetry.lock` (resolves versions exactly)

#### Step 3: Validate Lock Consistency

Always validate after adding:

```powershell
poetry check
poetry lock
poetry sync
```

### CI Enforcement Mode

To fail CI if undeclared packages exist, use strict mode:

```powershell
python scripts/python/detect_undeclared_packages.py --strict
```

If undeclared packages are found, the script exits with non-zero status (⚠️ pipeline fails).

**Recommended for pipeline validation** to prevent broken builds.

### Complete Workflow Before Clean Rebuild

Following this safe workflow prevents environment corruption:

```powershell
# Activate project environment
conda activate cr-misc-function-env

# 1️⃣ Detect undeclared packages
python scripts/python/detect_undeclared_packages.py

# 2️⃣ If needed, auto-suggest fixes
python scripts/python/detect_undeclared_packages.py --auto-add

# 3️⃣ Execute suggested commands (if any)
poetry add requests    # example from script output
poetry add rich        # example from script output

# 4️⃣ Validate lock file consistency
poetry check
poetry lock

# 5️⃣ Strict sync (install only what's in lock)
poetry sync

# 6️⃣ NOW safe to rebuild conda environment (if needed)
# conda remove -n cr-misc-function-env --all
# conda create -n cr-misc-function-env python=3.11 openjdk
# poetry install
```

**Golden Rule**: 🔍 Detect → Fix → Lock → Sync → Rebuild

Never rebuild blindly.

---

## Docker Integration

### Multi-Stage Dockerfile (No Conda)

For production Docker builds, use `micropipenv` instead of Poetry (smaller image, no Conda):

```dockerfile
# Stage 1: Builder
FROM python:3.11-slim AS builder

RUN pip install --upgrade pip micropipenv

WORKDIR /app

COPY pyproject.toml poetry.lock ./

RUN micropipenv install --deploy --no-dev


# Stage 2: Runtime
FROM python:3.11-slim

WORKDIR /app

COPY --from=builder /app/.venv .venv

COPY . .

ENV PATH="/app/.venv/bin:$PATH"

CMD ["python", "app/main.py"]
```

**Key Points**:

- ✅ No Conda inside Docker
- ✅ Uses `poetry.lock` for reproducible builds
- ✅ `micropipenv` handles lock file parsing & installation
- ✅ Multi-stage build keeps image size minimal

### Building the Docker Image

```powershell
docker build -t cr-misc-function:latest .
docker run cr-misc-function:latest
```

---

## Troubleshooting

### Problem: `poetry` command not found

**Cause**: PATH not updated or terminal not restarted

**Solution**:

1. Close all terminals
2. Open new terminal
3. Verify path: `Get-Command poetry` or `where.exe poetry`
4. If still missing, manually add to PATH and restart

### Problem: Poetry using wrong Python version

**Cause**: `virtualenvs.prefer-active-python` not set

**Solution**:

```powershell
poetry config virtualenvs.prefer-active-python true
poetry env remove  # Remove old venv
poetry install     # Recreate with correct Python
```

### Problem: `.venv` created outside project

**Cause**: `virtualenvs.in-project` not configured

**Solution**:

```powershell
poetry config virtualenvs.in-project true
poetry env remove
poetry install
```

### Problem: Mixed Conda + pip + Poetry dependencies causing conflicts

**Cause**: Installing packages in multiple ways in same environment

**Solution** (Nuclear option - clean rebuild):

```powershell
# Remove polluted environment
conda deactivate
conda remove -n cr-misc-function-env --all

# Recreate clean
conda create -n cr-misc-function-env python=3.11 openjdk
conda activate cr-misc-function-env

# Reconfigure Poetry
poetry config virtualenvs.in-project true
poetry config virtualenvs.prefer-active-python true

# Reinstall
poetry install
```

### Problem: `poetry.lock` is corrupted after conda/pip installs

**Cause**: System packages installed with `conda install` conflicted with Poetry's resolution

**Solution**:

```powershell
# Backup current lock
copy poetry.lock poetry.lock.backup

# Remove lock and regenerate
rm poetry.lock
poetry lock --no-update  # Resolve only, don't update versions
```

---

## Mental Model & Best Practices

### Tool Responsibilities (Final Truth Table)

| Task                   | Tool                 | Command                                 |
| ---------------------- | -------------------- | --------------------------------------- |
| Install Python version | Conda                | `conda create -n env python=3.11`       |
| Install Java           | Conda                | `conda install openjdk`                 |
| Install system libs    | Conda                | `conda install libpq-dev` (if needed)   |
| Install Python package | Poetry               | `poetry add requests`                   |
| Lock dependencies      | Poetry               | `poetry lock` (automatic on add/update) |
| Install from lock      | Poetry               | `poetry install`                        |
| Docker deployment      | Docker + micropipenv | See Docker section                      |

### Golden Rules Checklist

- ✅ Poetry installed in Miniconda base ONLY
- ✅ Project conda env has Python + system deps ONLY
- ✅ Python packages added via `poetry add` ONLY
- ✅ Poetry config: `virtualenvs.in-project=true`
- ✅ Poetry config: `virtualenvs.prefer-active-python=true`
- ✅ `.venv` is INSIDE project folder
- ✅ Docker uses `micropipenv`, not Conda

### Workflow (Day-to-Day)

#### Starting Work

```powershell
# Navigate to project
cd c:\Users\203715\Documents\Repo\cr-misc-function

# Activate environment
conda activate cr-misc-function-env

# Install/update dependencies
poetry install

# Verify environment
poetry env info

# Start developing
poetry run python app/main.py
```

#### Adding a Dependency

```powershell
poetry add pandas              # Latest production release
poetry add pytest --group dev  # Development dependency
```

#### Running Tests

```powershell
poetry run pytest tests/
```

#### Updating Dependencies

```powershell
poetry update                  # Update all
poetry update --dry-run        # Preview changes first
```

---

## Common Mistakes & How to Avoid Them

### ❌ Mistake #1: Installing Poetry in project environment

```powershell
# WRONG - Creates pollution
conda activate myenv
pip install poetry
poetry install
```

**Why it fails**: Poetry updates itself and pollutes the environment's dependency resolution.

**Correct way**:

```powershell
# Poetry lives in base ONLY
conda activate base
pip install poetry

# Then use from project env
conda activate myenv
poetry install
```

---

### ❌ Mistake #2: Mixing dependency managers

```powershell
# WRONG - Destroys reproducibility
poetry add requests
conda install pandas
pip install numpy
```

**Why it fails**: Each tool has different resolution logic. Lock file becomes meaningless.

**Correct way**:

```powershell
poetry add requests
poetry add pandas
poetry add numpy
# All go through poetry.lock
```

---

### ❌ Mistake #3: Not using `poetry run`

```powershell
# WRONG - Uses system Python or random PATH Python
python app/main.py

# CORRECT - Uses .venv Python
poetry run python app/main.py
```

---

## Quick Reference

### Essential Commands

```powershell
# Setup (one time)
poetry config virtualenvs.in-project true
poetry config virtualenvs.prefer-active-python true

# Daily work
conda activate cr-misc-function-env
poetry install
poetry add <package>
poetry run python app.py

# Maintenance
poetry lock --no-update
poetry update
poetry env remove
```

### Environment Inspection

```powershell
# Show active environment
poetry env info

# Show installed packages
poetry show

# Audit for vulnerabilities
poetry audit
```

---

## Result: Why This Architecture Works

| Problem                       | Solution                        | Benefit                   |
| ----------------------------- | ------------------------------- | ------------------------- |
| Python version conflicts      | Conda manages Python            | Single source of truth    |
| System dependencies scattered | Conda manages system libs       | Reproducible OS layer     |
| Lock file corruption          | Poetry + separate concern       | Deterministic deployments |
| Docker bloat                  | micropipenv (no Docker Conda)   | Minimal container size    |
| Admin requirements            | User PATH only                  | Works without privileges  |
| Dependency chaos              | One tool (Poetry) adds packages | Reproducible lock file    |

**Final Status**: ✅ Clean hybrid architecture ready for team collaboration and production deployment

---

## See Also

- [Poetry Documentation](https://python-poetry.org/docs/)
- [Miniconda Documentation](https://docs.conda.io/projects/miniconda/en/latest/)
- [micropipenv Documentation](https://github.com/thoth-station/micropipenv)
- [Docker Best Practices](./DOCKER_SETUP.md) (if available)
