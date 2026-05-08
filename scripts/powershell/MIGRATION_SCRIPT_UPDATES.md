# dev-migrate-conda-poetry-to-uv.ps1 - Latest Updates

## Summary of Changes

The migration utility script has been enhanced to support two separate README files (legacy/restoration vs migration steps) and a lightweight "guide-only" generation mode.

---

## New Features

### 1. **-GenerateMigrationGuideOnly Switch Parameter**

**Purpose:** Regenerate the migration guide without running full validation, backup, or removal logic.

**Use Case:** Update migration guides after dependencies change, without needing to validate the entire environment.

**How it works:**
- Skips all validation checks (no need for pyproject.toml, Conda, etc.)
- Attempts to parse dependencies if pyproject.toml exists (but doesn't fail if it doesn't)
- Creates `legacy/` directory if it doesn't exist
- Generates fresh `README_MIGRATION.md` with current settings
- Fast and lightweight - perfect for quick updates
- Early exits after guide generation (skip backup/removal phases)

**Usage:**
```powershell
.\dev-migrate-conda-poetry-to-uv.ps1 -GenerateMigrationGuideOnly

# Or if in different directory:
.\dev-migrate-conda-poetry-to-uv.ps1 -GenerateMigrationGuideOnly -ProjectRoot "C:\path\to\project"
```

### 2. **Separated README Files**

The single `README.md` has been split into two specialized files:

#### **README_LEGACY.md** (Restoration & Rollback)
- **Location:** `legacy/README_LEGACY.md`
- **Contents:**
  - Information about archive files (poetry.lock, pyproject.toml, conda exports)
  - **Restoration instructions** with 3 different recovery options
  - Conda environment restoration commands
  - Poetry dependency reinstallation steps
  - When-to-restore guidance

- **Purpose:** Quick reference for rolling back if migration fails

#### **README_MIGRATION.md** (Step-by-Step Guide)
- **Location:** `legacy/README_MIGRATION.md`
- **Contents:**
  - 7-step migration walkthrough
  - Conda activation instructions
  - uv initialization and venv creation
  - Dependency extraction and uv add commands
  - VS Code settings.json template
  - Dockerfile before/after comparison
  - Troubleshooting section
  - Useful uv commands reference

- **Purpose:** Complete migration workflow guide

---

## When to Use Each Mode

### Normal Mode (Full Validation)
```powershell
.\dev-migrate-conda-poetry-to-uv.ps1
```

**Runs:**
1. ✓ Validate pyproject.toml
2. ✓ Check Conda environment
3. ✓ Create backups (poetry.lock, pyproject.toml, conda exports)
4. ✓ Extract dependencies
5. ✓ Generate both README files
6. ✓ Optionally remove Poetry artifacts

**Best for:** First-time setup, fresh migration validation


### Guide-Only Mode
```powershell
.\dev-migrate-conda-poetry-to-uv.ps1 -GenerateMigrationGuideOnly
```

**Runs:**
1. ✓ Auto-detect project folder
2. ✓ Attempt to parse dependencies (if pyproject.toml exists)
3. ✓ Generate README_MIGRATION.md
4. ✗ Skip all validation
5. ✗ Skip all backups
6. ✗ Skip all file removal

**Best for:**
- Updating guide after dependencies change
- Regenerating guide without environment checks
- Quick reference guide creation

### With Force Override
```powershell
.\dev-migrate-conda-poetry-to-uv.ps1 -Force
```

Overwrites existing backup files and regenerates guides (useful after re-running checks)


### With Artifact Removal
```powershell
.\dev-migrate-conda-poetry-to-uv.ps1 -RemovePoetryArtifacts
```

After verifying backups are safe, removes:
- `poetry.lock` (backed up first)
- `pyproject.toml` (backed up as `pyproject.poetry.toml`)

---

## Output Structure

After running the script, the `legacy/` folder contains:

```
legacy/
├── README_LEGACY.md              # ← NEW: Restoration & rollback guide
├── README_MIGRATION.md           # ← NEW: Step-by-step migration guide
├── poetry.lock                   # Backup of original lock file
├── pyproject.poetry.toml         # Backup of original pyproject.toml
├── conda-env.yml                 # Conda environment export
└── conda-explicit-lock.txt       # Full Conda package list
```

---

## Implementation Details

### Early Exit for Guide-Only Mode
When `-GenerateMigrationGuideOnly` is set:
```powershell
if ($GenerateMigrationGuideOnly) {
    # Extract dependencies if available
    # Create legacy/ if needed
    # Generate README_MIGRATION.md
    # Exit immediately
    exit 0
}

# ... Rest of validation/backup/removal logic follows
```

### Dynamic Content Generation
Both README files are generated with project-specific values:
- **`$ProjectFolderName`** - Auto-detected from working directory
- **`$UvAddCommands`** - Extracted from pyproject.toml dependencies
- **`$(Get-Date)`** - Current timestamp

### Conditional File Creation
Both README files are created if:
- File doesn't exist, OR
- `-Force` switch is used

This prevents overwriting user edits unless explicitly requested.

---

## Example Workflows

### Workflow 1: Fresh Migration Setup
```powershell
# Step 1: Validate environment and create backups
.\dev-migrate-conda-poetry-to-uv.ps1

# Step 2: Follow migration guide
# Open legacy/README_MIGRATION.md and execute steps

# Step 3: Clean up artifacts after verifying it works
.\dev-migrate-conda-poetry-to-uv.ps1 -RemovePoetryArtifacts -Force
```

### Workflow 2: Quick Guide Regeneration
```powershell
# After updating dependencies in pyproject.toml:
.\dev-migrate-conda-poetry-to-uv.ps1 -GenerateMigrationGuideOnly

# Then review updated README_MIGRATION.md:
code legacy/README_MIGRATION.md
```

### Workflow 3: Rollback From Failed Migration
```powershell
# Need to restore Poetry?
code legacy/README_LEGACY.md

# Follow restoration instructions in the file
# (e.g., cp legacy/pyproject.poetry.toml ./pyproject.toml)
```

---

## Help Documentation

All parameters are documented with examples:
```powershell
get-help .\dev-migrate-conda-poetry-to-uv.ps1
get-help .\dev-migrate-conda-poetry-to-uv.ps1 -Detailed
get-help .\dev-migrate-conda-poetry-to-uv.ps1 -Full
```

---

## Benefits

✅ **Better separation of concerns** - Legacy info separate from migration steps
✅ **Lightweight updates** - Guide-only mode for quick regeneration
✅ **Clear rollback path** - Dedicate README for restoration instructions
✅ **Non-destructive** - Guide-only mode has zero side effects
✅ **Self-explanatory** - Two focused READMEs instead of one monolithic file

---

## Related Files

- **conda-py311-init-env.ps1** - Conda environment initialization (updated with help docs)
- **conda-py39-init-env.ps1** - Alternative Python version
- **git-reset-branches.ps1** - Git branch safety utility

---

**Generated:** $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
