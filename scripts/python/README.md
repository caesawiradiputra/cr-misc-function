# Python Utility Scripts

This folder contains helper Python scripts for environment management, dependency analysis, and project maintenance.

## Scripts

### generate_env.py

Generates a clean, portable `environment.yml` file from the active conda environment with intelligent dependency detection.

**Purpose:** Create a shareable, reproducible conda environment file that includes only top-level dependencies (not transitive dependencies). Automatically detects Poetry projects and adjusts output accordingly.

**Features:**

- 🎯 **Smart Dependency Detection:** Uses `pipdeptree` to identify only top-level pip packages (those you explicitly installed)
- 📦 **Poetry Support:** Automatically detects `pyproject.toml` + `poetry.lock` and skips pip dependencies
- 🔄 **Fallback Support:** Falls back to `pip freeze` if pipdeptree is unavailable
- 🧹 **Clean Output:** Removes duplicate dependencies already managed by conda
- 📝 **Environment Preservation:** Captures Python version and conda channels

**Usage:**

```powershell
cd cr-misc-function

# Generate environment.yml from active conda environment
python scripts/python/generate_env.py

# Preview the YAML without writing file (dry-run)
python scripts/python/generate_env.py --dry-run

# Specify custom output file
python scripts/python/generate_env.py --output custom-env.yml

# Generate from base environment (normally prevented)
python scripts/python/generate_env.py --allow-base
```

**Parameters:**

- `--output <file>` (default: `environment.yml`) - Output file path
- `--dry-run` - Print YAML to console without writing file
- `--allow-base` - Allow generating from base conda environment (normally prevented)

**Behavior:**

1. Detects the active conda environment name and Python version
2. Exports explicitly installed conda packages using `conda env export --from-history`
3. Detects pip packages using:
   - **Primary:** `pipdeptree` to get only top-level packages (dependencies excluded)
   - **Fallback:** `pip freeze` if pipdeptree not available
4. Removes conda packages already installed (avoids duplication)
5. Checks for `pyproject.toml` + `poetry.lock` files
6. If Poetry detected:
   - Skips pip dependencies in YAML (Poetry manages them)
   - Adds comment: `Install Python packages using: poetry install`
7. Generates YAML with proper structure and writes to file
8. Returns appropriate instructions based on project type

**Example Output (Standard Project):**

```yaml
name: cr-misc-function-env
channels:
  - conda-forge
  - defaults
dependencies:
  - python=3.11
  - openjdk
  - pyyaml
  - pip
  - pip:
    - requests==2.28.0
    - sqlalchemy==2.0.0
```

**Example Output (Poetry Project):**

```yaml
name: cr-misc-function-env
channels:
  - conda-forge
  - defaults
dependencies:
  - python=3.11
  - openjdk
  - pyyaml
_comment: Install Python packages using: poetry install
```

**Exit Codes:**

- `0`: Success — environment.yml generated
- `1`: Error — conda environment not found, Python error, or file write error

**When to Use:**

- Setting up a new project environment file
- Updating environment.yml after installing new conda packages
- Sharing project setup with team members
- Creating reproducible builds across machines
- Before version control commit to track dependencies

**Best Practices:**

1. **Run after conda changes:** Update environment.yml whenever you `conda install` packages
2. **Use with Poetry projects:** Don't manually add pip packages when using Poetry
3. **Version control:** Commit generated `environment.yml` to git for reproducibility
4. **Share for collaboration:** Team members use: `conda env create -f environment.yml`

**Common Workflow:**

```powershell
# 1. Activate your project environment
conda activate cr-misc-function-env

# 2. Install packages as needed
conda install numpy pandas

# 3. Generate clean environment.yml
python scripts/python/generate_env.py

# 4. Verify dry-run before updating
python scripts/python/generate_env.py --dry-run

# 5. Commit to version control
git add environment.yml
git commit -m "chore: update environment dependencies"
```

---

### detect_undeclared_packages.py

Detects Python packages imported in your code but not explicitly declared in your project dependencies.

**Purpose:** Identify missing, undeclared, or forgotten dependencies that would cause import errors in a fresh environment. Helps maintain accurate `pyproject.toml` or `environment.yml` specifications.

**Features:**

- 🔍 **Deep Code Analysis:** Scans Python files for import statements
- 📋 **Dependency Comparison:** Compares imports against declared dependencies
- 🎯 **Accurate Detection:** Handles various import styles and edge cases
- 📊 **Clear Reporting:** Shows which modules are imported but not declared
- ⚡ **Fast Scanning:** Efficiently processes large codebases

**Usage:**

```powershell
cd cr-misc-function

# Scan current project directory for undeclared packages
python scripts/python/detect_undeclared_packages.py

# Scan specific directory
python scripts/python/detect_undeclared_packages.py --path ./app

# Ignore specific packages
python scripts/python/detect_undeclared_packages.py --ignore tests,docs

# Show detailed import locations
python scripts/python/detect_undeclared_packages.py --verbose

# Generate report file
python scripts/python/detect_undeclared_packages.py --output report.txt
```

**Parameters:**

- `--path <dir>` (default: `.`) - Root directory to scan
- `--ignore <list>` - Comma-separated list of packages to ignore
- `--verbose` - Show detailed information about each import
- `--output <file>` - Write report to file instead of stdout

**Behavior:**

1. Scans all `.py` files in the project directory
2. Parses import statements (regular and conditional imports)
3. Extracts package names from various import styles:
   - `import package`
   - `from package import module`
   - `import package as alias`
   - `from package.subpackage import name`
4. Reads declared dependencies from:
   - `pyproject.toml` (poetry: `[tool.poetry.dependencies]`)
   - `requirements.txt` (pip format)
   - `environment.yml` (conda format)
5. Compares imports against declared dependencies
6. Reports missing declarations
7. Filters system/stdlib packages automatically

**Example Output:**

```text
Undeclared Package Dependencies
================================

Scanning: /path/to/project
Found .py files: 42
Imports found: 156

UNDECLARED PACKAGES (5):
  1. requests         - imported in: app/api/client.py:5, app/services/http.py:12
  2. numpy            - imported in: app/analysis/stats.py:3
  3. pandas           - imported in: app/data/processing.py:8
  4. sqlalchemy       - imported in: app/models/database.py:1
  5. python-dateutil  - imported in: app/utils/dates.py:15

Declared packages (15):
  pyyaml, openjdk, pytest, black, ruff, mypy, ...

RECOMMENDATIONS:
  - Run: pip install requests numpy pandas sqlalchemy python-dateutil
  - Or: poetry add requests numpy pandas sqlalchemy python-dateutil
  - Then: python scripts/python/generate_env.py
```

**Exit Codes:**

- `0`: Success — scan complete (may have undeclared packages)
- `1`: Error — directory not found or parsing error

**When to Use:**

- After adding new imports to your code
- Before committing code to ensure dependencies are documented
- During code review to catch missing dependency declarations
- When setting up a new development environment
- As part of CI/CD pipeline to enforce dependency documentation

**Common Scenarios:**

#### **Scenario 1: Found missing imports**

```powershell
# Run detection
python scripts/python/detect_undeclared_packages.py

# Install missing packages
pip install requests numpy
# OR
poetry add requests numpy

# Update environment files
python scripts/python/generate_env.py
```

#### **Scenario 2: Check before environment export**

```powershell
# Verify all imports are declared
python scripts/python/detect_undeclared_packages.py

# If clean (no undeclared), generate environment
python scripts/python/generate_env.py

# Commit
git add environment.yml pyproject.toml
git commit -m "chore: update dependencies"
```

#### **Scenario 3: Onboarding new developer**

```powershell
# New dev clones project
git clone <repo>

# Check for undeclared packages (will fail if any exist)
python scripts/python/detect_undeclared_packages.py

# If clean, set up environment
conda env create -f environment.yml
conda activate my-project
poetry install  # (if using Poetry)
```

---

## Prerequisites

- Python 3.11+
- conda (for environment.yml generation and detection)
- pipdeptree (optional, for `generate_env.py` — installs fallback to pip freeze if missing)

## Installation

### Install Optional Dependencies

For optimal experience, install `pipdeptree` in your **base conda environment** for accurate top-level dependency detection. This is a utility tool, not a project dependency:

```powershell
# Install in base conda environment (NOT in project environment)
conda activate base
conda install pipdeptree

# Or using pip
pip install pipdeptree

# Then activate your project environment
conda activate cr-misc-function-env
```

Without pipdeptree, scripts fall back to `pip freeze` (which includes all transitive dependencies).

## Workflow Integration

### Complete Dependency Management Workflow

```powershell
# 1. Activate project environment
conda activate cr-misc-function-env

# 2. Install new conda packages as needed
conda install numpy

# 3. Check for undeclared imports
python scripts/python/detect_undeclared_packages.py

# 4. Install any Python packages not in conda
pip install requests
# OR
poetry add requests

# 5. Update environment files
python scripts/python/generate_env.py

# 6. Verify output (dry-run)
python scripts/python/generate_env.py --dry-run

# 7. Commit changes
git add environment.yml pyproject.toml poetry.lock
git commit -m "chore: update project dependencies"
```

### With CI/CD Pipeline

```powershell
# In your CI/CD workflow:
# 1. Check that all imports are declared (fail if not)
python scripts/python/detect_undeclared_packages.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Undeclared package imports found!"
    exit 1
}

# 2. Validate environment files are up-to-date
# (Add your own validation logic here)

# 3. Proceed with tests/deployment
```

---

## Best Practices

- **Regular Updates:** Run `generate_env.py` after each `conda install` session
- **Dependency Review:** Use `detect_undeclared_packages.py` before commits
- **Version Control:** Always commit updated `environment.yml` and `pyproject.toml`
- **Team Sharing:** Ensure everyone runs `conda env create -f environment.yml` to match dependencies
- **Poetry Priority:** If using Poetry, let it manage Python dependencies; conda manages system packages (java, etc.)
- **Documentation:** Document any manual environment setup steps in ENVIRONMENT_SETUP.md

---

## Troubleshooting

> **Q: Script reports "conda not found"**

- Ensure conda is installed and available in PATH
- Activate your conda environment first: `conda activate myenv`

> **Q: `pipdeptree` not found**

- Install it: `pip install pipdeptree` or `conda install pipdeptree`
- Scripts will fall back to `pip freeze` if unavailable

> **Q: Environment file not generated**

- Check file permissions (can you write to that directory?)
- Ensure you're not generating from base environment without `--allow-base`

- Check console output for specific error messages

> **Q: Undeclared packages found but they're from standard library**

- These are typically filtered automatically
- If not, you can ignore them: `--ignore sys,os,json`
