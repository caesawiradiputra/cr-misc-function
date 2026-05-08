# Git Repository Workflow with Tag & Release Management

> **Authoritative Source**: This document supersedes all other workflow documents. Follow this as the single source of truth for git workflow, branching strategy, and CI/CD processes.

---

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

---

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

#### **Rules:**

- **Always start from `dev`**, not from `sit` or `master`
- Pull latest changes from `dev` before creating branch
- Keep branches focused on a single feature or fix

### 2.3 Testing in SIT / UAT

Once development is complete on your feature/fix branch:

#### **Step 1: Create a PR from feature/fix branch to `sit`**

```text
fea/*  or fix/* → sit
```

#### **Step 2: Deploy `sit` branch to SIT/UAT environment**

- Push changes to `sit` through the PR merge
- Notify QA/testing team for validation

#### **Step 3: If bugs are found during testing**

- Push fixes to the **same feature/fix branch** (do NOT commit directly to sit)
- The updated PR will automatically reflect the new changes
- Redeploy `sit` for re-testing

#### **Important Rules:**

- ✅ **All changes go through PRs** (no direct commits to long-lived branches)
- ❌ **Do NOT commit directly to `sit`**, even for SIT-specific fixes
- Every change must be traceable back to a PR for audit compliance
- `sit` is a **testing branch only**, not a long-term integration branch

### 2.4 Promotion to Dev (Staging)

Once SIT/UAT testing is **approved by QA/testing team**:

#### **Create a PR from feature/fix branch to `dev`:**

```text
fea/*  or fix/* → dev
```

#### **Merge Strategy: SQUASH MERGE**

- Squash all commits into a single commit
- One commit per feature or fix in dev history
- Provides clean, readable development history
- Makes git log easier to follow

#### **Before Merging: SQUASH MERGE**

- ✅ Ensure all SIT/UAT testing is approved
- ✅ Verify PR has been reviewed
- ✅ Confirm no merge conflicts with dev
- ✅ Delete the feature/fix branch after merge

### 2.5 Docker Image Creation & Validation

After merging into `dev`, create a Docker image for final validation:

#### **Step 1: Trigger Docker Image Build (Manual)**

1. Go to GitHub → **Actions** tab
2. Select **Docker Image CI** workflow
3. Click **Run workflow**
4. Enter Docker image tag (e.g., `v1.2.0` or `staging-2026-01-14`)
5. Start the workflow

#### **Step 2: Validate Docker Image**

- **Who validates:** Developer or Team Lead
- **What to check:**
  - Image builds successfully
  - All dependencies are included
  - Image starts without errors
  - Health checks pass
- **Where deployed:** Staging environment (`dev` deployment)

#### **Step 3: Approval Decision**

- ✅ **Approved:** Proceed to production merge
- ❌ **Issues found:** Push fixes back to feature branch and restart workflow

### 2.6 Promotion to Production (Master)

After Docker image validation in `dev`:

#### **Create a PR from `dev` to `master`:**

```text
dev → master
```

#### **Merge Strategy: NORMAL MERGE (No Squash)**

- Preserves all commits from dev history
- Maintains clear release boundaries
- Creates merge commit for traceability
- Shows complete history of what was released

#### **Before Merging: NORMAL MERGE**

- ✅ Docker image successfully validated
- ✅ All SIT/UAT testing completed and approved
- ✅ Team Lead approval (if required by org policy)
- ✅ Release notes/CHANGELOG prepared

#### **After Merge:**

- Create Git tag on `master` (see Section 4)
- Create GitHub Release with release notes
- Monitor production deployment

---

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

#### **Manual Trigger (Recommended):**

1. Go to GitHub → **Actions** tab
2. Select **Docker Image CI** workflow
3. Click **Run workflow** button
4. Enter Docker image tag:
   - For dev/staging: `staging-2026-01-14` or `dev-v1.2.0`
   - For production: `v1.2.0` (semantic versioning)
5. Click **Run workflow**

#### **Expected Outcome:**

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

#### **Benefits:**

- Docker image tag automatically matches Git tag (v1.2.0)
- Guaranteed consistency between code and artifacts
- Easy rollback to previous releases
- Clear audit trail of what was deployed

---

## 4. Git Tag Usage

### 4.1 What Is a Git Tag

A Git tag is an immutable pointer to a specific commit.

- **Immutable**: Tags never move or change after creation
- **Milestone Marker**: Tags mark important releases and versions
- **Uses**:
  - Production release identification
  - Versioning (code, Docker images, packages)
  - CI/CD triggers
  - Rollback and audit reference points

### 4.2 Where Tags Are Created

Tags are created **ONLY on `master` branch**.

#### **Rules: Tags**

- ❌ **Do NOT tag `dev`** (staging is not production-ready)
- ❌ **Do NOT tag `sit`** (testing environment is not production-ready)
- ✅ **Tag only after `dev` → `master` is merged** (after production release)

Every tag on `master` represents a **production release**.

### 4.3 Tag Naming Convention

The repository uses **semantic versioning**:

```text
vMAJOR.MINOR.PATCH
```

#### **Examples:**

- `v1.0.0` - Initial production release (major version bump)
- `v1.1.0` - New feature released (minor version bump)
- `v1.1.1` - Bug fix released (patch version bump)

#### **When to increment:**

- **MAJOR** (X.0.0): Breaking changes, significant refactoring, major feature
- **MINOR** (1.Y.0): New features added (backwards compatible)
- **PATCH** (1.1.Z): Bug fixes, security patches, minor improvements

### 4.4 When to Create a Tag

Tags are created **after successful production deployment**:

1. ✅ Feature/fix branch tested and approved in SIT/UAT
2. ✅ Feature/fix branch merged into `dev` (squash merge)
3. ✅ Docker image built and validated in staging (`dev`)
4. ✅ `dev` merged into `master` (normal merge)
5. ✅ **Create and push Git tag on `master`** (after production deployment)

#### **Tag Lifecycle:**

- Create tag after `dev` → `master` merge
- Push tag to remote repository
- Create corresponding GitHub Release
- Tag is permanent and should never be modified

### 4.5 How to Create and Push a Tag

```bash
# Step 1: Ensure you are on master and up to date
git checkout master
git pull origin master

# Step 2: Create annotated tag with release message
git tag -a v1.2.0 -m "Release v1.2.0: Add feature X and fix bug Y"

# Step 3: Push tag to remote repository
git push origin v1.2.0

# Step 4: Verify tag was pushed successfully
git tag -l  # List local tags
git ls-remote --tags origin  # Verify tag on remote
```

#### **Important:**

- Use **annotated tags** (`-a` flag), not lightweight tags
- Include clear message describing what's in the release
- Tags are **immutable** - never delete or modify after pushing
- If you need to retag, create a new version (e.g., v1.2.1) instead

---

## 5. GitHub Releases

### 5.1 Relationship Between Tags and Releases

#### **GitHub Releases** are built on top of Git tags. A release provides

- Human-readable release notes
- Summary of changes and improvements
- Links to related artifacts and documentation
- Visibility into what was released and when

#### **Requirement:**

- **Every production tag should have a corresponding GitHub Release**
- Release notes document what was deployed and why
- Provides team and stakeholders visibility into releases

### 5.2 Creating a GitHub Release

#### **Step 1: Navigate to GitHub Releases**

- Go to your GitHub repository
- Click on **Releases** (right sidebar)
- Click **Draft a new release**

#### **Step 2: Select or Create Tag**

- Select existing tag (e.g., `v1.2.0`)
- Or create new tag during release creation

#### **Step 3: Fill Release Information**

- **Title**: Release version and summary (e.g., "v1.2.0 - Add customer deduplication")
- **Description**: Complete release notes (see format below)
- **Attach files** (optional): Add artifacts like DDL scripts, migration guides

#### **Step 4: Publish**

- Click **Publish release**
- GitHub will send notifications to watchers

### 5.3 Release Notes Template

Use this format for consistency and completeness:

```markdown
# Release v1.2.0

#### **Release Date:** 2026-01-15

## Summary
Brief description of what this release includes. Example: "This release adds customer deduplication feature and improves payment validation reliability."

## Features & Improvements
- **DA-1421**: Add realtime exposure index for SRF rule validation
- **DA-1470**: Improve obligor rule evaluation with caching
- **DA-1455**: Refactor database connection pooling

## Bug Fixes
- **DA-1488**: Fix null reference exception in payment processor
- **DA-1492**: Resolve timeout issue in batch processing

## Breaking Changes
None (or list any breaking changes if applicable)

## Deployment Artifacts
- **Docker Image**: `registry-intl.ap-southeast-5.aliyuncs.com/bfi-registry/your-image:v1.2.0`
- **Release Package**: `/release/2026-01-15_DA-1421/`
- **Database Changes**: See `release/2026-01-15_DA-1421/ddl/` for schema migrations

## Deployment Instructions
1. Pull latest Docker image: `docker pull registry-intl.ap-southeast-5.aliyuncs.com/bfi-registry/your-image:v1.2.0`
2. Run database migrations: See `/release/2026-01-15_DA-1421/ddl/migrations.sql`
3. Update configuration: See `/release/2026-01-15_DA-1421/config/`
4. Deploy to production environment

## Rollback Plan
If issues occur:
1. Revert to previous release: `v1.1.1`
2. Run rollback scripts: See `/release/2026-01-15_DA-1421/ddl/rollback.sql`
3. Restart services with previous Docker image

## Related Documentation
- [Architecture Decision Record](docs/architecture/...)
- [Migration Guide](release/2026-01-15_DA-1421/docs/migration-guide.md)
- Related Tickets: DA-1421, DA-1470, DA-1455
```

---

## 6. Release Artifacts Management

### 6.1 Release Folder Structure

Release-specific files are stored in version control for traceability:

```text
release/
└── YYYY-MM-DD_JIRA-ID/
    ├── CHANGELOG.md          # Detailed release notes and documentation
    ├── ddl/
    │   ├── migrations.sql    # Database schema changes
    │   └── rollback.sql      # Rollback script if deployment fails
    ├── data/
    │   └── seed-data.sql     # Data migrations or seed scripts
    ├── config/
    │   └── application.yaml  # Configuration changes for deployment
    └── docs/
        ├── migration-guide.md     # Step-by-step deployment guide
        ├── architecture-changes.md # Technical design documentation
        └── rollback-plan.md       # Detailed rollback procedures
```

### 6.2 Benefits of Centralized Release Artifacts

- **Single Source of Truth**: All release info in one location
- **Git History**: Full version history and audit trail
- **Rollback Reference**: Easy access to rollback scripts
- **Team Documentation**: Clear deployment and rollback procedures
- **Traceability**: Link from GitHub Release to release folder

---

## 7. Branch Cleanup & Maintenance Rules

### 7.1 Cleanup After Merge

After feature/fix branch is merged to `dev` or `sit`:

```bash
# Delete local branch
git branch -d fea/<feature-name>

# Delete remote branch
git push origin --delete fea/<feature-name>
```

#### **When to delete:**

- ✅ After merge to `sit` (can recreate if needed for retesting)
- ✅ After merge to `dev` (feature is integrated)
- ✅ After merge to `master` (feature is in production)

### 7.2 Maintaining Long-Lived Branches

#### **Keeping `sit` updated:**

- Periodically rebase or merge `dev` into `sit` when idle
- Prevents `sit` from falling too far behind `dev`
- Example: `git checkout sit && git merge dev` (with fast-forward or merge commit)

#### **Keeping `master` clean:**

- Never commit directly to `master`
- Only accept PRs from `dev`
- Every commit represents a production release

### 7.3 Tag & Release Maintenance

#### **Tag Rules (Permanent):**

- ❌ **Never delete** tags after release
- ❌ **Never force-update** tag pointers
- ✅ **If a release is bad**: Create a new tag (e.g., `v1.2.1`) with a fix

#### **Release Cleanup:**

- ❌ **Never delete** GitHub Releases
- ✅ **Mark deprecated releases**: Use description to note if superseded
- ✅ **Archive old releases**: Move to separate release notes document if needed

#### **Example - Bad Release:**

```text
v1.2.0 - Released with critical bug
v1.2.1 - Hotfix release (bug fix only, use instead of v1.2.0)
```

### 7.4 Cleaning Stale Local Branches

Regularly clean up old local and remote branches:

```bash
# Remove local branches no longer on remote
git fetch -p

# List merged branches (safe to delete)
git branch --merged

# Delete multiple merged branches
git branch -d branch1 branch2 branch3
```

---

## 8. Quick Reference: Complete Feature Workflow

### From Start to Finish

```text
1. CREATE BRANCH from dev
   git checkout dev && git pull origin dev
   git checkout -b fea/my-feature

2. DEVELOP & COMMIT
   git add .
   git commit -m "✨ feat(scope): description"

3. PUSH TO REMOTE
   git push origin fea/my-feature

4. CREATE PR to sit
   Feature branch → sit (for testing)

5. TEST IN SIT/UAT
   Deploy, test, and approve (no direct commits to sit)

6. CREATE PR to dev
   Feature branch → dev (squash merge)
   Delete feature branch after merge

7. BUILD DOCKER IMAGE
   GitHub Actions → Docker Image CI workflow (manual trigger)

8. VALIDATE IMAGE
   Developer or Team Lead approves image

9. CREATE PR to master
   dev → master (normal merge, preserves history)

10. CREATE GIT TAG
    git tag -a v1.2.0 -m "Release v1.2.0"
    git push origin v1.2.0

11. CREATE GITHUB RELEASE
    Add release notes and link to release artifacts

12. DEPLOY TO PRODUCTION
    Use Docker image and run database migrations
```

### Timeline Example

```text
Day 1: Feature development starts
  - Create fea/auth-api from dev
  - Make commits, push changes

Day 2-3: Testing phase
  - PR to sit for SIT/UAT testing
  - Team tests feature
  - Any bugs fixed in same branch, re-tested

Day 4: Ready for staging
  - PR to dev (squash merge)
  - Feature merged into dev
  - Branch deleted

Day 4-5: Staging validation
  - Trigger Docker image build (manual)
  - Dev/Team Lead validates image
  - Run integration tests

Day 5-6: Production release
  - PR from dev to master
  - Merge to master (normal merge)
  - Create Git tag (v1.2.0)
  - Create GitHub Release with notes
  - Deploy image to production
```

---

## 9. Summary

### Core Principles

- **One PR per feature** from start to finish
- **Feature branches** always start from `dev`, not `sit`
- **All changes** go through PRs (no direct commits to long-lived branches)
- **Squash merge** for feature → dev (clean history)
- **Normal merge** for dev → master (preserve release boundaries)
- **Docker image** built and validated manually before production
- **Tags** created only on `master` after production deployment
- **GitHub Releases** document every production release

### What This Ensures

- ✅ **Clean History**: Easy to understand what was released and why
- ✅ **Strong Traceability**: Every change linked to a PR and ticket
- ✅ **Safe Rollback**: Previous releases available via tags and GitHub Releases
- ✅ **Clear Ownership**: Release responsibility and validation checkpoints clear
- ✅ **Audit Compliance**: Complete change history and approval trail
- ✅ **Quality Gates**: Testing in SIT/UAT before production
- ✅ **Fast Deployment**: Manual Docker workflow enables controlled releases
