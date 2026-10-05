# Git Repository Workflow with Tag & Release Management

## 1. Branch Overview

This repository uses three long-living branches with clear responsibilities:

### Core Branches

#### `master` → Production Environment

- **Source of truth** for production code
- Only accepts PRs from `dev` (never direct commits)
- Every commit on `master` represents a production-ready release
- Tagged with semantic versions (e.g., `v1.0.0`)

#### `dev` → Staging / Pre-Production Environment

- **Integration branch** for validated features
- Used for:
  - Docker image creation (via GitHub Actions)
  - Final validation before production merge
  - Package builds and testing
- All feature/fix branches merge here after SIT/UAT approval
- **Feature and fix branches are always created from `dev`**

#### `sit` → SIT / UAT Testing Environment

- **Testing branch** for user acceptance testing
- Receives feature/fix branches for validation
- May be rebased from `dev` when clean or idle
- Testing issues are fixed in the same feature/fix branch and re-tested

## 2. Feature & Fix Development Workflow

### 2.1 Branch Naming Conventions

Feature and fix branches follow consistent naming:

```bash
fea/<feature-name>          # New feature (e.g., fea/add-auth-api)
fix/<bug-description>       # Bug fix (e.g., fix/null-reference-exception)
refactor/<component>        # Refactoring (e.g., refactor/db-connection-pool)
```

### 2.2 Creating Feature / Fix Branches

All new development starts from `dev`:

```bash
git checkout dev
git pull origin dev
git checkout -b fea/<feature-name>
# or
git checkout -b fix/<bug-description>
```

**Rules:**

- **Always start from `dev`**, not from `sit` or `master`
- Pull latest changes from `dev` before creating branch
- Keep branches focused on a single feature or fix

### 2.2 Testing in SIT / UAT

To test changes in SIT/UAT:

**Create a PR from:**

- `fea/*` or `fix/*` → `sit`

**Deploy** `sit` branch to the SIT/UAT environment

**If bugs are found:**

- Fix them in the same feature/fix branch
- Re-PR to sit

**Note:** `sit`
Re-PR to sit

sit is a testing branch, not a long-term integration branch.

2.3 Promotion to Dev

Once SIT/UAT testing is approved:

### 2.3 Promotion to Dev

Once SIT/UAT testing is approved:

**Create a PR from:**

- `fea/*` or `fix/*` → `dev`

**Merge strategy:**

- Squash merge is recommended
- One commit per feature or fix
- After final verification in dev (image/package tested):

Create a PR from:

dev → master

### 2.4 Promotion to Production

After final verification in dev (image/package tested):

**Create a PR from:**

- `dev` → `master`

**Merge strategy:**

- Normal merge (no squash)
- Preserves release boundaries
-

Tags mark important milestones, especially releases

## 3. CI/CD: Docker Image Build & Deployment

### 3.1 GitHub Actions Workflow Setup

Create `.github/workflows/docker-image-ci.yml` for automated Docker builds:

```yaml
name: Docker Image CI

on:
  workflow_dispatch:
    inputs:
      image_tag:
        description: 'Docker Image Tag (e.g., v1.2.0 or staging-YYYY-MM-DD)'
        required: true
        default: 'latest'

jobs:
  build-and-push:
    runs-on: ubuntu-latest

    env:
      IMAGE_NAME: "your-image-name"  # Set your Docker image name

    steps:
    - name: Checkout repository
      uses: actions/checkout@v4

    - name: Set IMAGE_TAG from input
      run: echo "IMAGE_TAG=${{ github.event.inputs.image_tag }}" >> $GITHUB_ENV

    - name: Log in to Alibaba Cloud Container Registry
      run: echo "${{ secrets.ALIYUN_REGISTRY_PASSWORD }}" | docker login --username=${{ secrets.ALIYUN_REGISTRY_USERNAME }} --password-stdin registry-intl.ap-southeast-5.aliyuncs.com

    - name: Build the Docker image
      run: |
        docker build -t registry-intl.ap-southeast-5.aliyuncs.com/bfi-registry/${{ env.IMAGE_NAME }}:${{ env.IMAGE_TAG }} .

    - name: Push Docker Image to Alibaba Cloud
      run: |
        docker push registry-intl.ap-southeast-5.aliyuncs.com/bfi-registry/${{ env.IMAGE_NAME }}:${{ env.IMAGE_TAG }}

    - name: Print Image URL
      run: echo "Image pushed: registry-intl.ap-southeast-5.aliyuncs.com/bfi-registry/${{ env.IMAGE_NAME }}:${{ env.IMAGE_TAG }}"
```

### 3.2 GitHub Secrets Configuration

Store sensitive credentials in GitHub:

1. Go to Repository → **Settings** → **Secrets and variables** → **Actions**
2. Add these secrets:
   - `ALIYUN_REGISTRY_USERNAME`: Your Alibaba Cloud registry username
   - `ALIYUN_REGISTRY_PASSWORD`: Your Alibaba Cloud registry password

### 3.3 Running the Docker Build Workflow

**Manual Trigger (Recommended):**

1. Go to GitHub → **Actions** tab
2. Select **Docker Image CI** workflow
3. Click **Run workflow** button
4. Enter Docker image tag:
   - For dev/staging: `staging-2026-01-14` or `dev-v1.2.0`
   - For production: `v1.2.0` (semantic versioning)
5. Click **Run workflow**

**Expected Outcome:**

- Docker image builds successfully
- Image is pushed to Alibaba Cloud registry
- Image URL appears in workflow logs
- Team can retrieve image for validation

### 3.4 Production Deployment via Tags (Optional)

To automatically build Docker images when tags are pushed to `master`:

```yaml
on:
  push:
    tags:
      - 'v*'  # Matches tags like v1.0.0, v1.2.3
```

**Benefits:**

- Docker image tag automatically matches Git tag (v1.2.0)
- Guaranteed consistency between code and artifacts
- Easy rollback to previous releases
- Clear audit trail of what was deployed

---

## 4. Git Tag Usage

### 4.1 What Is a Git Tag

A Git tag is an immutable pointer to a specific commit.

- Tags do not move
- Tags mark important milestones, especially releases
- Tags are used as:
  - Version identifiers
  - Release references
  - ❌ Do not tag dev

❌ Do not tag sit

✅ Tag only after dev → master is merged

### 3.2 Where Tags Are Created

Tags are created **ONLY on master**.

**Rules:**

- ❌ Do not tag dev
- ❌ Do not tag sit
- v1.1.0

### 3.3 Tag Naming Convention

The repository uses semantic versioning:

```

vMAJOR.MINOR.PATCH

```

**Examples:**

### 3.4 When to Create a Tag

Tags are created after production readiness:

1. `fea/*` or `fix/*` → `sit` (testing)
2. `fea/*` or `fix/*` → `dev` (staging)
3. `dev` → `master` (production code)

4. # Create annotated tag

git tag -a v1.2.0 -m "Release v1.2.0"

# Push tag to remote

git push origin v1.2.0

### 3.5 How to Create and Push a Tag

```bash
# Make sure you are on master
git checkout master
git pull origin master

# Create annotated tag
git tag -a v1.2.0 -m "Release v1.2.0"

# Push tag to remote
## 5. GitHub Releases

### 4.1 Relationship Between Tags and Releases

GitHub Releases are built on tags.

**A release:**
- References a tag
- Adds release notes
- Can attach artifacts

### 4.2 Creating a GitHub Release

1. Go to GitHub → Releases
2. Click Draft a new release
3. Select the tag (e.g., `v1.2.0`)
4. Fill release notes:
   - Jira IDs
   - Summary of changes
   - Links to release artifacts
5. ### Changes
- DA-1421: Add realtime exposure index
- DA-1470: Improve obligor rule evaluation

### Artifacts
- Docker image: da-af-rules-engine:v1.2.0
- Release scripts: /release/2024-11-18_DA-1421

### Deployment
### 4.3 Recommended Release Notes Format

```markdown
## Version v1.2.0

### Changes
- DA-1421: Add realtime exposure index
- DA-1470: Improve obligor rule evaluation

### Artifacts
- Docker image: da-af-rules-engine:v1.2.0
## 5. CI/CD and Tags (Optional but Recommended)

Tags can be used to trigger CI/CD pipelines:

```yaml
on:
  push:
    tags:
      - 'v*'
```

**Benefits:**

- Docker image tag matches Git tag
- Guaranteed consistency between code and artifact
- release/
└── YYYY-MM-DD_JIRA-ID/
    ├── ddl/
    ├── rollback/

## 6. Release Artifacts Management

Release-specific files (DDL, templates, migrations) are stored in Git:

```
release/
└── YYYY-MM-DD_JIRA-ID/
    ├── ddl/
    ├── rollback/
    └── CHANGELOG.md
```

- One folder per business change
- Git history handles versioning
- git fetch -p

## 7. Cleanup & Maintenance Rules

- Feature/fix branches are deleted after merge
- Local stale branches cleaned with:

```bash
git fetch -p
```

- Tags are never deleted once released
- If a release is bad:
  - Create a new tag (e.g., `v1.2.1`)
  -

master + tag = production truth

This workflow ensures:

## 8. Summary

- **Branches** move forward
- **Tags** mark releases
- **GitHub Releases** document production deployments
- **master + tag** = production truth

### This workflow ensures

- Clean history
- Strong traceability
- Safe rollback
-
