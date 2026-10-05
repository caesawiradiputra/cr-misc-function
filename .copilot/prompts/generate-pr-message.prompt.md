---
description: Generate pull request messages for feature/fix branch deployments to SIT/UAT or Production with release documentation
---

# Generate Pull Request Messages for Feature Branch Deployments

**CRITICAL:** Always compare the current feature/fix branch to the target environment branch to analyze changes. Every PR is a deployment/release.

**Important:** Release documentation is always created for deployment traceability. Save to `release/` folder structure.

You are an expert at writing clear, comprehensive pull request descriptions and release documentation for feature deployments.

## 🎯 ONE PR PER FEATURE: Always a Deployment

Each feature branch gets **ONE PR** for deployment to the target environment.

**Workflow:**
```
Feature Branch → One PR → Deploy to Target (SIT/UAT or Production)
```

No "standard vs release" - every PR includes release documentation.

## 📋 Usage

```
/generate-pr-message [version] [target-branch] ["optional requirement text"]
```

**Parameters:**
- `[version]` - Version number (optional, semantic versioning: vX.Y.Z)
  - If omitted: uses timestamp-based deployment ID (YYYY-MM-DD_HHMM)
  - Use when: deploying app code changes that increment version
  - Omit when: DB schema changes, config updates, infrastructure changes only
- `[target-branch]` - Target environment branch (default: `master` for production)
  - `dev` or `sit` → Deploy to SIT/UAT (staging)
  - `master` or nothing → Deploy to Production
- `["optional requirement text"]` - JIRA ticket context/business requirements (optional, quoted string)
  - Supports any language: Indonesian, English, or other languages
  - Used only for understanding context - will NOT be copied into changelog or PR message
  - Can include or omit ticket ID - it's derived from current git branch name automatically
  - Example: `"Penambahan variable baru untuk tracking..."` (ticket ID extracted from branch)
  - Example: `"DA-1515: Add new variable..."` (works with or without ticket ID in text)

**Examples:**
- `/generate-pr-message v1.0.0 dev` → Deploy to SIT/UAT (with version, no requirements)
- `/generate-pr-message v1.0.0 dev "Add new antifraud variable based on license plate and phone"` → Deploy with requirements
- `/generate-pr-message dev "Penambahan variable baru untuk identifikasi aplikasi dengan riwayat reject sebelumnya"` → Deploy to SIT/UAT (no version, with Indonesian requirements)
- `/generate-pr-message v1.0.0 master` → Deploy to Production (with version, no requirements)
- `/generate-pr-message dev` → Deploy to SIT/UAT (no version, no requirements)
- `/generate-pr-message` → Deploy to Production (no version, no requirements)

---

## 🔀 Outputs Based on Target

### Deploying to SIT/UAT (Staging - `dev` or `sit` branch)

**Generates:**
1. **Release Folder**: `release/YYYY-MM-DD_JIRA-ID/`
2. **PR Message for Feature → Dev/SIT** (for staging deployment)
3. **PR Template for Dev → Master** (ready for production later after testing)

Compare: `origin/dev...HEAD` or `origin/sit...HEAD`

### Deploying to Production (Master)

**Generates:**
1. **Release Folder**: `release/YYYY-MM-DD_JIRA-ID/`
2. **PR Message for Feature → Master** (for production deployment)

Compare: `origin/master...HEAD`

---

## ⚠️ WORKFLOW REMINDER
**Parse parameters and detect target environment:**
1. **ALWAYS** run `git fetch origin` to sync remote refs
2. **ALWAYS** run `git branch --show-current` to identify feature branch
   - Extract ticket ID from branch name (e.g., `fea/DA-1079-feature-name` → `DA-1079`)
   - Ticket ID in branch is authoritative; use it regardless of whether requirement text includes it
3. **CHECK if release folder already exists**: `release/YYYY-MM-DD_JIRA-ID/`
   - If YES: Recheck the folder, update CHANGELOG.md with latest changes
   - If NO: Create new release folder structure
4. **Parse parameters to identify version, target, and requirements:**
   - Parameter like `v1.0.0` = version (starts with 'v' followed by numbers)
   - Parameter like `dev`, `sit`, `master` = target branch
   - Parameter in quotes (e.g., `"requirement text here"`) = requirement text (last parameter)
   - If only one parameter provided: determine if it's version or target
     - Example: `/generate-pr-message v1.0.0` → version=v1.0.0, target=master (default)
     - Example: `/generate-pr-message dev` → version=none, target=dev
   - If three parameters: `/generate-pr-message v1.0.0 dev "requirements here"` → all three parsed
5. **Determine target environment:**
   - `dev` or `sit` → **SIT/UAT Deployment** (staging environment)
   - `master` or no parameter → **Production Deployment** (production environment)
6. **Generate version identifier:**
   - If provided: use as-is throughout (e.g., `v1.0.0`)
   - If omitted: generate timestamp ID (e.g., `2026-01-13_1430`)
7. **Extract and analyze requirement text** (if provided):
   - Use for context only to understand feature purpose
   - **Do NOT copy or include requirement text** in CHANGELOG or PR
   - Ticket ID is already extracted from branch name, not from requirement text
   - Requirement text is optional - you have ticket ID from branch regardless
   - Use to map code changes to business needs, then describe only the code
8. **ALWAYS** run `git diff <target-branch>...HEAD --name-status` to see changed files
9. **ALWAYS** run `git log <target-branch>..HEAD --oneline` to see commit history
10. **Create or update release folder** in all cases (always a deployment)
11. **DO NOT** assume previous analysis is still valid

**Important:** Compare current feature/fix branch to target branch. Work directly with current branch.

---

## 🚫 CRITICAL: DO NOT COPY REQUIREMENT TEXT INTO OUTPUTS

**When requirement text is provided (optional):**
- ⚠️ **NEVER copy requirement text verbatim** into CHANGELOG or PR messages
- ⚠️ **Requirement text is for context ONLY** - understand what was needed, not what to write
- ⚠️ **Focus on code changes** - describe what was implemented, not what was required
- ⚠️ **Ticket ID comes from git branch**, not from requirement text
- ⚠️ **All requirements are in JIRA** - don't duplicate them in commit messages

**Ticket ID Derivation:**
- Primary: Extract from git branch name (e.g., `fea/DA-1515-feature-name` → `DA-1515`)
- Use in: Release folder `release/YYYY-MM-DD_DA-1515/` and CHANGELOG footer `Refs: DA-1515`
- Requirement text with or without ticket ID doesn't matter - branch is authoritative

**Correct Approach:**
1. Extract ticket ID from git branch
2. Read requirement text (if provided) to understand context
3. Run git diff to see actual code changes
4. Describe only the code changes in CHANGELOG and PR
5. Reference the ticket ID extracted from branch

**Wrong Approach:**
❌ Copy requirement text into CHANGELOG
❌ Translate requirement text and include it
❌ Extract ticket ID from requirement text instead of branch name
❌ Include "Business Requirements" section with requirement text
❌ Summarize requirements instead of code changes
❌ Create duplicate documentation of what's already in JIRA

---

## 🏷️ Git Tagging for Releases

**Tag Creation:** After your PR is merged and deployed to master:
1. Checkout master: `git checkout master`
2. Pull latest: `git pull origin master`
3. Create annotated tag: `git tag -a vX.Y.Z -m "Release vX.Y.Z: {description}"`
4. Push tag: `git push origin vX.Y.Z`

**When to Tag:**
- **SIT/UAT Deployment**: No tag (staging only)
- **Production Deployment**: Create tag after PR is merged to master
- **Tag Format**: vX.Y.Z (semantic versioning)
- **Tag Message**: Should include version and brief summary of changes

**Example Tag Commands:**
```bash
# After deploying v1.2.0 to production
git tag -a v1.2.0 -m "Release v1.2.0: Add SRF negative list rule and fix customer deduplication bug"
git push origin v1.2.0

# After deploying v1.2.3 with multiple fixes
git tag -a v1.2.3 -m "Release v1.2.3: Hotfix - payment validation and connection pooling optimization"
git push origin v1.2.3
```

---

## 📌 Version Number Handling

**If user provides version (e.g., `v1.0.0`):**
- Use it throughout all PR messages and changelog
- Semantic Versioning Format: vX.Y.Z
  - **X (Major)**: Major changes, breaking changes, significant new features
  - **Y (Minor)**: Minor changes, new features, enhancements (backwards compatible)
  - **Z (Patch)**: Bug fixes, small improvements, security patches

**If user omits version:**
- Generate deployment ID from current timestamp: `YYYY-MM-DD_HHMM` (e.g., `2026-01-13_1430`)
- Use deployment ID in release folder and PR messages: `release/2026-01-13_1430_JIRA-ID/`
- Useful for: DB schema changes, config updates, infrastructure changes, or when version TBD

**Examples:**
- With version: `/generate-pr-message v1.0.0 dev` → Folder: `release/YYYY-MM-DD_vX.Y.Z-TICKET-ID/`
- Without version: `/generate-pr-message dev` → Folder: `release/2026-01-13_1430_TICKET-ID/`

## Task
Analyze the changes between current **feature/fix branch** and **target branch**:

**For SIT/UAT Deployment** (`dev` or `sit` target):
1. **Release Folder** - `release/YYYY-MM-DD_JIRA-ID/`
2. **PR Message for Feature → Dev/SIT** - Brief deployment message for staging
3. **Dev/SIT → Master PR Template** - To use later for production after testing

**For Production Deployment** (`master` target):
1. **Release Folder** - `release/YYYY-MM-DD_JIRA-ID/`
2. **PR Message for Feature → Master** - Brief deployment message for production

## 📁 Output Organization
**ALL generated documentation must be placed in appropriate folders to keep root directory clean.**

**Release Deployment Structure:**
- **Release Folder**: `release/YYYY-MM-DD_JIRA-ID/` or `release/YYYY-MM-DD_vX.Y.Z_JIRA-ID/` (with version if provided)
  - `release/YYYY-MM-DD_JIRA-ID/CHANGELOG.md` - Comprehensive changelog with all deployment details
  - `release/YYYY-MM-DD_JIRA-ID/ddl/` - Database changes
  - `release/YYYY-MM-DD_JIRA-ID/data/` - Data migration scripts
  - `release/YYYY-MM-DD_JIRA-ID/config/` - Configuration changes
  - `release/YYYY-MM-DD_JIRA-ID/docs/` - Implementation details

## Git Repository Location
**Important:** This workspace uses a nested git folder structure:
- Workspace root: `<root-workspace>/`
- Git repository folder: `<root-workspace>/<project-name>/` (child folder with same name)

**Example:**
- Workspace: `c:\Users\203715\Documents\Repo\cr-misc-function\`
- Git repo: `c:\Users\203715\Documents\Repo\cr-misc-function\cr-misc-function\`

When analyzing branch differences:
1. Navigate to the git repository folder (child folder)
2. Run all git commands from that location
3. Compare current feature/fix branch to target branch (dev or master based on workflow)
4. Extract ticket ID from branch name (e.g., `fea/DA-1079-...` → `DA-1079`)

## Pull Request Message Standards

### 1️⃣ PR Message: Feature/Fix Branch → Dev (Squash-Merge)
**Only for Full Workflow (skip for master-only)**

This is for merging your feature/fix branch to the dev (staging) branch.

#### Title Format
```
[{Type}] {Ticket-ID}: {Brief description}
```

**Examples:**
- `[Feature] DA-1079: Add SRF negative list rule for customer`
- `[Fix] DA-2145: Resolve null reference in payment validation`
- `[Refactor] DA-3021: Optimize database connection pooling`

**Type Options:** `[Feature]`, `[Fix]`, `[Refactor]`, `[Perf]`, `[Docs]`, `[Chore]`

#### Description Structure
```markdown
## 🎯 Overview
[1-2 sentences explaining what this PR does]

## 📋 Changes
- Change 1
- Change 2
- Change 3

## 🧪 Testing
- [ ] Unit tests added/updated
- [ ] Manual testing completed
- [ ] Edge cases covered

## 📝 Notes
- Any important notes for reviewers
- Dependencies or related tickets

## 📚 Documentation
See release folder for comprehensive details: `release/YYYY-MM-DD_JIRA-ID/CHANGELOG.md`

---
**Refs:** {Ticket-ID}
**Type:** {Feature/Fix/Refactor}
```

**Keep under 25 lines.**

---

### 2️⃣ Release Folder & CHANGELOG (Commit to Feature Branch)

This comprehensive release folder and changelog documents all deployment details for traceability.

#### Folder Structure
```
release/YYYY-MM-DD_JIRA-ID/
├── CHANGELOG.md          # Comprehensive changelog
├── ddl/                  # Database schema changes
├── data/                 # Data migration scripts
├── config/               # Configuration changes
└── docs/                 # Implementation details
```

**Example:** `release/2026-01-09-DA-1079/CHANGELOG.md`

#### CHANGELOG.md Structure
```markdown
# [{Type}] {Ticket-ID}: {Brief Description} - v{X.Y.Z}

**Date:** YYYY-MM-DD
**Version:** vX.Y.Z (or YYYY-MM-DD_HHMM if no version)
**Ticket:** {Ticket-ID}
**Type:** {Feature/Fix/Refactor}
**Branch:** {branch-name}

## 💼 Business Requirements

[If requirement text provided: Include the requirement text here with translation/clarification if needed]

## 📝 Summary

[2-3 paragraphs explaining what was changed and why. If requirements provided, explain how implementation addresses them]

## 🎯 Objectives

[Extract from requirement text if provided, or derive from code analysis]
- Objective 1
- Objective 2

## 📋 Changes Made

### Files Modified
- `path/to/file1.py` - Description of changes
- `path/to/file2.py` - Description of changes

### Key Implementations
1. **Implementation 1**: Detailed explanation
2. **Implementation 2**: Detailed explanation

## 🧪 Testing Performed
**[Only include if: test results are in git diff OR user specifically asks for it]**

### Test Cases
- Test case 1: Expected result
- Test case 2: Expected result

### Edge Cases Covered
- Edge case 1
- Edge case 2

## 💥 Breaking Changes

[List any breaking changes, or state "None"]

## 📦 Dependencies

### Added/Updated
- dependency@version - reason

## 🔍 Code Review Notes

- Note 1 for reviewers
- Note 2 for reviewers

## 📚 References

- Related documentation
- Related tickets
- External resources
- Ticket: https://bfifinance.atlassian.net/browse/DA-1079

---

**Author:** {Name}
**Reviewed By:** [To be filled after review]
```

---

### 3️⃣ PR Message: Dev → Master (Production Release)

This is for deploying tested changes from dev to production (master).

#### Title Format
```
Release vX.Y.Z: Deploy to Production
```

#### Description Structure
```markdown
## 🚀 Production Release vX.Y.Z

This release deploys the following tested changes from staging (dev) to production (master).

## 📋 Features & Fixes Included
- **{Ticket-ID}**: {Brief description} - [{Type}]
- **{Ticket-ID}**: {Brief description} - [{Type}]

## ✅ Staging Validation
- [x] All features tested in staging environment
- [x] Integration tests passed
- [x] Performance verified
- [x] Security review completed

## 🚀 Deployment Plan
- **Target Date:** YYYY-MM-DD
- **Rollback Plan:** Standard rollback to previous release
- **Monitoring:** {Metrics to monitor post-deployment}

## 📚 Documentation
- Release folder: `release/YYYY-MM-DD_JIRA-ID/CHANGELOG.md`

---
**Refs:** {Ticket-IDs}
**Release Type:** {Major/Minor/Patch}
```

**Keep under 30 lines.**

## Generation Guidelines

### ⚠️ CRITICAL: No Assumptions or Hallucinations - Only Git Diff Facts

**BEFORE GENERATING ANY CONTENT:**
- ❌ **DO NOT assume** what changed based on branch name, requirement text, or git history
- ❌ **DO NOT hallucinate** implementation details, test cases, or objectives
- ❌ **DO NOT invent** files, methods, or code changes that don't exist
- ✅ **ALWAYS verify** everything against actual `git diff <target-branch>...HEAD` output
- ✅ **ONLY describe** what is present in the actual git diff
- ✅ **ONLY include description** if the user provided it in the prompt

**Golden Rule:**
```
If it's not in the git diff output, it doesn't exist in this PR.
```

**Description Rule:**
- If user provided description/summary in prompt → Use it
- If user did NOT provide description → Do NOT generate or assume one; leave blank or omit section

**Example:**
- ✅ Correct: "Three files modified: connection.py, strategy_factory.py, and tests" (from git diff)
- ❌ Wrong: "Added comprehensive error handling" (not verified in diff)
- ❌ Wrong: Generating a description when user only said `/generate-pr-message dev`

### 1. Extract Branch Information
- Get current branch name: Extract ticket ID (e.g., `fea/DA-1079-...` → `DA-1079`)
- Identify type from branch prefix: `fea/` = Feature, `fix/` = Fix, `refactor/` = Refactor

### 2. Analyze Changes Thoroughly
- **RUN FIRST**: `git diff <target-branch>...HEAD` to examine actual code changes (do this BEFORE writing anything)
- **RUN SECOND**: `git diff <target-branch>...HEAD --name-status` to see actual changed files
- ⚠️ **GIT DIFF IS THE ONLY SOURCE OF TRUTH** - All descriptions must match actual diff output
- ⚠️ **ONLY INCLUDE facts from the diff** - do NOT infer, assume, or add details not present in the diff
- ⚠️ **If something is not in git diff, it is not part of this PR** - do not mention it
- Compare current feature/fix branch to target branch (dev or master)
- Categorize changes by file and functionality **based on actual diff content only**
- Identify breaking changes or dependencies **only if visible in actual code changes**
- Note test coverage additions **only if test files are in the diff**
- **Extract ticket ID from git branch name** (e.g., `fea/DA-1079-feature-name` → `DA-1079`)
  - This is the authoritative ticket ID for the release folder and CHANGELOG footer
  - Use it regardless of whether requirement text includes it
- **If requirement text provided**:
  - Use ONLY for context (understand business purpose)
  - **DO NOT copy or include** requirement text anywhere in output
  - **ONLY describe actual code changes** that are present in git diff output
  - **DO NOT generate descriptions if not present in diff** (e.g., "Added error handling" if not in diff)
  - Focus only on: what files changed (from diff), what methods were added/modified (from diff), what tests were added (from diff)
- **If release folder already exists**: Check for existing CHANGELOG.md
  - Read current content to preserve context
  - Update version if user provided different version
  - Merge new changes into CHANGELOG.md (keep structure but update with latest analysis)
  - Preserve ddl/, data/, config/, docs/ subfolders (user may have added files)
  - Do NOT delete or reset existing folder structure
- **If release folder is new**: Create full structure with all subfolders

**Testing Section Handling:**
- **Include ONLY if:**
  - Test files (*.py test cases) are present in the git diff, OR
  - User specifically asks for testing information, OR
  - Test results are explicitly mentioned in the prompt
- **Omit if:**
  - No test files in the diff
  - No test results mentioned
  - User did NOT ask for testing information
- **When included**: Describe only tests that are actually in the diff (don't assume test cases)

### 4. Maintain Consistency
- Use same version number (or timestamp ID if no version) across all outputs
- Keep ticket IDs consistent
- Link release folder in both PR messages
- All outputs related to same deployment package

### 5. Keep PR Messages Brief
- Feature → Dev/SIT (if applicable): Under 25 lines
- Feature → Master (production): Under 30 lines
- Dev → Master (full workflow): Under 30 lines
- Detailed info goes in release folder CHANGELOG.md only
- Focus on code changes, not business requirements
- Reference ticket for requirements: "See DA-1515 in JIRA for business requirements"

### 6. Incorporate Requirement Text (If Provided)
- **Critical**: Never copy or paste requirement text verbatim
- **Use for context only**: Understand what business need this addresses, but don't include it
- **Reference ticket instead**: Link to JIRA ticket (e.g., "Refs: DA-1515") instead of copying requirement
- **ONLY generate description if user provided it** - If no description in prompt, do not invent or assume one
- **In PR Overview**: Use ONLY description provided by user (or omit if not provided) + ticket reference
- **In CHANGELOG Summary**: Describe ONLY the technical changes made to the code (from git diff)
- **In CHANGELOG Objectives**: Extract ONLY from actual code changes (not from requirement text or assumptions)
- **In CHANGELOG Key Implementations**:
  - Describe what code was added/modified (not what was required)
  - Show only files, classes, methods that are actually in the diff
  - Explain only technical implementation details visible in the code changes
- **In CHANGELOG Footer**: Add ticket reference (e.g., "Refs: DA-1515")
- **No Requirement Section**: Do NOT create a "Business Requirements" or similar section - all requirements are in JIRA
- **No Generated Descriptions**: If user did NOT provide description/summary text, do NOT generate one from assumptions
## Output Format

**IMPORTANT:**
- **Release folder with CHANGELOG.md**: CREATE files (but do NOT run git commands)
- **PR messages**: Display in chat response only (user copies to GitHub PR interface)
- **DO NOT run**: `git add`, `git commit`, `git push` - user does this after review

**Agent Action:**
1. Check if release folder already exists
   - If YES: Recheck folder, read current CHANGELOG.md
   - If NO: Create new folder structure
2. Create or update CHANGELOG.md file (reflecting latest changes and any version updates)
3. Preserve existing ddl/, data/, config/, docs/ subfolders (user may have added files)
4. Display PR message content in chat for review

**User Action:**
1. Review all generated files
2. Make any edits if needed
3. Run: `git add release/YYYY-MM-DD_JIRA-ID/`
4. Run: `git commit -m "release: add deployment package..."`
5. Create PR in GitHub with provided message
6. Run: `git push` after review and approval

**For SIT/UAT Deployment (Feature → Dev/SIT):**
```markdown
## 📁 Output 1: Release Folder Created
**Folder created:** release/YYYY-MM-DD_JIRA-ID/
**File created:** release/YYYY-MM-DD_JIRA-ID/CHANGELOG.md
[comprehensive changelog content]

**You manually run:**
```bash
git add release/YYYY-MM-DD_JIRA-ID/
git commit -m "📦 release({ticket}): add {brief-description} deployment package"
git push
```

## 📝 Output 2: PR Message (Feature/Fix → Dev/SIT)
**Copy this to GitHub PR description:**
```
[PR message content here]
```

## 📝 Output 3: PR Template (Dev → Master)
**Save this for later (use after testing in staging):**
```
[PR message template for production deployment]
```
```

**For Production Deployment (Feature → Master):**
```markdown
## 📁 Output 1: Release Folder Created
**Folder created:** release/YYYY-MM-DD_JIRA-ID/
**File created:** release/YYYY-MM-DD_JIRA-ID/CHANGELOG.md
[comprehensive changelog content]

**You manually run:**
```bash
git add release/YYYY-MM-DD_JIRA-ID/
git commit -m "📦 release({ticket}): add {brief-description} deployment package"
git push
```

## 📝 Output 2: PR Message (Feature/Fix → Master)
**Copy this to GitHub PR description:**
```
[PR message content here]
```

## 🏷️ Output 3: Git Tag Command (After PR Merge)
**Run this AFTER your PR is merged and deployed to master:**
```bash
git checkout master
git pull origin master
git tag -a vX.Y.Z -m "Release vX.Y.Z: {Brief description of features and fixes}"
git push origin vX.Y.Z
```

**Example:**
```bash
git tag -a v1.2.3 -m "Release v1.2.3: Add SRF negative list rule and fix payment validation"
git push origin v1.2.3
```
```

### 1️⃣ PR Message: Feature/Fix Branch → Dev

**Copy this to GitHub PR description:**
```
[Generated PR message for feature/fix to dev - ready to paste]
```

### 2️⃣ Detailed Changelog File
**Filename:** `docs/changelog/YYYY-MM-DD-vX.Y.Z-{ticket}-{summary}.md`

```markdown
[Comprehensive changelog content - save this file and commit to feature branch]
```

### 3️⃣ PR Message: Dev → Master

**Copy this to GitHub PR description (use after testing in staging):**
```
[Generated PR message for dev to master - save for later use]
```

---

**Workflow:**
1. Agent creates release folder and CHANGELOG.md file
2. Agent displays PR message content in chat
3. User reviews all generated files
4. User manually runs: `git add release/YYYY-MM-DD_JIRA-ID/`
5. User manually runs: `git commit -m "..."`
6. User creates PR in GitHub with provided message text
7. User runs: `git push` after review and approval

**⚠️ IMPORTANT:** Agent creates files but does NOT run git add/commit/push. User handles all git operations.

## Example Outputs

### 1️⃣ Example: PR Message (Feature → Dev)

```
[Feature] DA-1079: Add SRF Negative List Rule for Customer

## 🎯 Overview
Implements SRF (Single Request Filter) negative list rule to prevent duplicate customer entries in the processing pipeline.

## 📋 Changes
- Added `SRFNegativeListRule` class in `rules/srf_negative_list.py`
- Implemented customer deduplication logic based on customer_id and transaction_date
- Added validation for negative list criteria
- Updated rule configuration in `config/rules.yaml`

## 🧪 Testing
- [x] Unit tests added for SRFNegativeListRule class
- [x] Manual testing with sample customer data
- [x] Edge cases: duplicate IDs, null values, boundary conditions

## 📝 Notes
- Rule is disabled by default; enable via configuration
- Performance impact: minimal (< 5ms per 1000 records)

## 📚 Documentation
See release folder: `release/2026-01-09-DA-1079/CHANGELOG.md`

---
**Refs:** DA-1079
**Type:** Feature
```

### 2️⃣ Example: Release Folder with CHANGELOG

**Folder Structure:** `release/2026-01-09-DA-1079/`

**File:** `release/2026-01-09-DA-1079/CHANGELOG.md`

```markdown
# [Feature] DA-1079: Add SRF Negative List Rule for Customer - v1.2.3

**Date:** 2026-01-09
**Version:** v1.2.3
**Ticket:** DA-1079
**Type:** Feature
**Branch:** fea/DA-1079-SRF-Negative-List-Rule-Customer

## 📝 Summary

This feature implements a Single Request Filter (SRF) negative list rule to prevent duplicate customer entries from being processed in the transaction pipeline. The rule validates incoming customer records against a negative list and filters out duplicates based on customer ID and transaction date combination.

This addresses the issue where duplicate customer requests were causing data inconsistencies and processing delays. The negative list is maintained in the database and updated automatically based on business rules.

## 🎯 Objectives

- Prevent duplicate customer entries in transaction processing
- Implement configurable negative list criteria
- Maintain audit trail of filtered requests
- Ensure minimal performance impact (< 5ms per 1000 records)

## 📋 Changes Made

### Files Modified
- `app/rules/srf_negative_list.py` - New rule implementation
- `app/rules/__init__.py` - Added SRFNegativeListRule export
- `app/config/rules.yaml` - Added rule configuration
- `app/repositories/negative_list_repository.py` - Database access layer
- `tests/test_srf_negative_list.py` - Unit tests

### Key Implementations

1. **SRFNegativeListRule Class**: Core rule logic for filtering duplicate customers
   - Validates customer_id and transaction_date combination
   - Queries negative list from database via repository
   - Returns filtered list with audit information

2. **NegativeListRepository**: Database access layer
   - `check_customer_exists(customer_id, date)` - Check if customer is in negative list
   - `add_to_negative_list(customer_id, reason)` - Add customer to negative list
   - Implements connection pooling for performance

3. **Configuration**: Rule settings in YAML
   - `enabled`: Toggle rule on/off (default: false)
   - `cache_ttl`: Cache duration for negative list (default: 300s)
   - `batch_size`: Records to process in batch (default: 1000)

## 🧪 Testing Performed

### Test Cases
- Test 1: Single customer not in negative list → passes through
- Test 2: Single customer in negative list → filtered out
- Test 3: Batch of 1000 customers, 10% in negative list → 900 passed, 100 filtered
- Test 4: Null customer_id → raises validation error
- Test 5: Invalid date format → raises validation error

### Edge Cases Covered
- Duplicate customer_id with different dates (allowed)
- Duplicate customer_id with same date (filtered)
- Empty negative list (all pass through)
- Large batch processing (10,000+ records)

### Performance Results
- 1,000 records: 4.2ms average
- 10,000 records: 38ms average
- Cache hit rate: 85% after warm-up

## 💥 Breaking Changes

None - this is a new feature with no impact on existing functionality.

## 📦 Dependencies

### No Changes
Existing database connection and repository infrastructure used.

## 🔍 Code Review Notes

- Rule is disabled by default to allow gradual rollout
- Negative list cache improves performance significantly
- Database repository pattern maintains separation of concerns
- Comprehensive unit tests cover main scenarios and edge cases

## 📚 References

- Ticket: https://bfifinance.atlassian.net/browse/DA-1079
- Design Doc: `docs/architecture/srf-negative-list-design.md`
- Related: DA-1050 (Customer deduplication initiative)

---

**Author:** Development Team
**Reviewed By:** [To be filled after review]
```

### 3️⃣ Example: PR Message (Dev → Master)

```
## 🚀 Production Release v1.2.3

This release deploys the SRF negative list feature from staging to production.

## 📋 Features & Fixes Included
- **DA-1079**: Add SRF negative list rule for customer - [Feature]

## ✅ Staging Validation
- [x] Feature tested in staging environment (3 days)
- [x] Integration tests passed with production data sample
- [x] Performance verified (< 5ms per 1000 records)
- [x] Security review completed (no sensitive data exposure)

## 🚀 Deployment Plan
- **Target Date:** 2026-01-15
- **Rollback Plan:** Disable rule via configuration; standard rollback available
- **Monitoring:** Track filter rate, processing time, cache hit rate

## 📚 Documentation
- Release folder: `release/2026-01-09-DA-1079/CHANGELOG.md`

---
**Refs:** DA-1079
**Release Type:** Minor
```

### 4️⃣ Example: Git Tag Command (After PR Merge)

**Run this AFTER your PR is merged to master:**

```bash
git checkout master
git pull origin master
git tag -a v1.2.3 -m "Release v1.2.3: Add SRF negative list rule and fix customer deduplication bug"
git push origin v1.2.3
```

**What this does:**
- Creates an annotated tag `v1.2.3` on the merge commit
- Pushes the tag to GitHub for release tracking
- Tag message provides release summary for documentation
- Use semantic versioning (vX.Y.Z format)

---

## 📌 Examples with Technical Focus (No Requirement Text Copy)

### 5️⃣ Example: Antifraud Feature (Requirement Provided but NOT Copied)

**Command:**
```
/generate-pr-message v1.3.0 dev "Penambahan variable baru pada data antifraud yang merepresentasikan indikasi keterkaitan dengan riwayat reject sebelumnya, berdasarkan referensi license plate kendaraan dan/atau nomor telepon customer"
```

**Generated CHANGELOG.md (Technical Focus ONLY):**
```markdown
# [Feature] DA-1515: Rejection History Correlation in Antifraud Data - v1.3.0

**Date:** 2026-02-16
**Version:** v1.3.0
**Ticket:** DA-1515
**Type:** Feature
**Branch:** fea/DA-1515-antifraud-rejection-history

## 📝 Summary

Implements rejection history correlation tracking in the antifraud data model. Adds new fields and database query methods to identify applications linked to previous rejections by license plate or phone number.

## 📋 Changes Made

### Files Modified
- `app/models/antifraud_data.py` - Added data model fields
- `app/repositories/antifraud_repository.py` - Added query methods
- `app/rules/antifraud_rule.py` - Updated rule evaluation logic
- `tests/test_antifraud_rejection_history.py` - New tests

### Key Implementations

1. **Antifraud Data Model** (`app/models/antifraud_data.py`)
   - Added `rejection_history_link_indicator: Optional[str]` field to track correlation ID
   - Added `RejectionReferenceType` enum: LICENSE_PLATE, PHONE_NUMBER
   - Both fields optional, backward compatible with existing data

2. **Repository Query Methods** (`app/repositories/antifraud_repository.py`)
   - `get_rejection_history_by_plate(license_plate: str) -> List[RejectionRecord]`
   - `get_rejection_history_by_phone(phone: str) -> List[RejectionRecord]`
   - Uses connection pooling, includes caching (TTL: 1 hour)

3. **Antifraud Rule Update** (`app/rules/antifraud_rule.py`)
   - Added `check_rejection_correlation()` method
   - Executed before main rule evaluation
   - Returns rejection records if any matches found

## 🧪 Testing Performed

### Test Cases
- Single application with no rejection history → passes through
- Single application linked by license plate → rejected with correlation details
- Batch of 100 applications, 8 linked by phone → 92 passed, 8 rejected
- Query performance with 50k rejection records → <100ms response time
- Cache invalidation after rejection record added → cache refreshes correctly

### Edge Cases Covered
- Missing license plate or phone number → skips reference type, uses available data
- Null rejection_link_indicator → treated as no correlation
- Concurrent requests with same reference → cache prevents duplicate queries

## 💥 Breaking Changes

None - new fields are optional, existing API unchanged.

## 📦 Dependencies

No new dependencies added. Uses existing database connection and repository infrastructure.

## 🔍 Code Review Notes

- Feature disabled by default; enable via feature flag for gradual rollout
- Query methods use existing connection pool
- Caching prevents N+1 query problems
- All new code includes type hints and docstrings

## 📚 References

- Ticket: https://bfifinance.atlassian.net/browse/DA-1515
- Related: DA-1400 (Antifraud system architecture)

---

**Author:** Development Team
**Reviewed By:** [To be filled after review]
```

**Generated PR Message (Feature → Dev) - Technical Focus:**
```markdown
## 🎯 Overview
Adds rejection history correlation tracking to antifraud data model. Implements query methods for license plate and phone number lookups, and updates antifraud rule evaluation to check for linked applications during processing.

## 📋 Changes
- New model fields for rejection correlation tracking
- Repository methods for rejection history queries by plate/phone
- Antifraud rule updated to check correlations before accepting applications
- Query caching (1 hour TTL) to minimize database load
- New integration tests for correlation detection

## 🧪 Testing
- [x] Unit tests added for model and repository layers
- [x] Integration tests for rule evaluation
- [x] Performance tests confirm <100ms query time
- [x] Edge cases: missing data, null values, concurrent access

## 📝 Notes
- Feature disabled by default; uses feature flag for rollout
- No API changes; fully backward compatible
- Database migration not required (new fields optional)

## 📚 Documentation
Detailed implementation in: `release/2026-02-16-DA-1515/CHANGELOG.md`

---
**Refs:** DA-1515
**Type:** Feature
```

### 6️⃣ Example: Connection Pooling (No Requirement Text Included)

**Command:**
```
/generate-pr-message v1.8.0 dev "Add support for connection pooling optimization to reduce database connection overhead and improve query performance by 15-20%. Performance baseline: 2500ms for 10k connections. Target: 2000ms."
```

**Generated CHANGELOG.md (Technical ONLY):**
```markdown
# [Perf] DA-1234: Connection Pool Optimization - v1.8.0

**Date:** 2026-02-16
**Version:** v1.8.0
**Ticket:** DA-1234
**Type:** Perf
**Branch:** fea/DA-1234-connection-pool-optimization

## 📝 Summary

Optimizes database connection pooling configuration to improve query performance and reduce connection creation overhead.

## 📋 Changes Made

### Files Modified
- `app/connections/strategies/factory.py` - Connection pool parameters
- `app/connections/strategies/base.py` - Connection lifecycle management
- `app/main.py` - Application startup
- `tests/test_connection_pooling_perf.py` - Performance benchmarks

### Key Implementations

1. **Pool Configuration Update** (`factory.py`)
   - `pool_size`: 5 → 10 (maintains more ready connections)
   - `max_overflow`: 10 → 20 (allows more surge capacity)
   - `pool_recycle`: 3600 seconds (prevents stale connections)

2. **Connection Recycling** (`base.py`)
   - Added `pool_recycle` parameter to invalidate connections after 1 hour
   - Prevents database-side connection timeouts
   - Automatic reconnection on next use

3. **Pool Warmup on Startup** (`main.py`)
   - Pre-creates initial 10 connections during app startup
   - Eliminates first-request creation delay
   - Improves initial request latency

## 🧪 Testing Performed

### Performance Results
- 10k concurrent connections: baseline 2500ms → optimized 2050ms (18% improvement)
- Query latency P95: 150ms → 125ms
- Connection acquisition time: 50ms → 5ms
- No increase in memory usage (connection pooling is more efficient)

### Test Cases
- Normal load (100 concurrent) → all queries complete within SLA
- Peak load (500 concurrent) → no connection exhaustion, graceful queueing
- Connection timeout → automatic reconnect on next request
- Long-running queries → connection held until query completes

## 💥 Breaking Changes

None - configuration change only, no API changes.

## 📦 Dependencies

No new dependencies.

## 🔍 Code Review Notes

- Pool parameters tuned for typical workload; monitor metrics post-deployment
- Connection recycling prevents stale connection issues
- Warmup adds ~100ms to startup time (acceptable)

## 📚 References

- Ticket: https://bfifinance.atlassian.net/browse/DA-1234
- Performance metrics: `release/2026-02-16-DA-1234/perf_benchmark.txt`

---

**Author:** Development Team
**Reviewed By:** [To be filled after review]
```

## Quality Checklist

Before finalizing output, ensure:
- [ ] **NO HALLUCINATIONS** - Everything verified against actual `git diff <target>...HEAD` output
  - [ ] No assumed facts about what changed (verified from diff only)
  - [ ] No inferred implementation details (from diff only)
  - [ ] No invented test cases or edge cases (from diff only)
  - [ ] No generated descriptions if user did NOT provide one in prompt
- [ ] Branch name parsed correctly to extract ticket ID
- [ ] Version number used consistently across all outputs
- [ ] Target branch (dev/sit/master) identified correctly
- [ ] **Git diff analyzed first** - examined actual code changes before writing anything
- [ ] **All facts match git diff output** - Every statement verified against actual diff
  - [ ] File lists match actual changed files in diff
  - [ ] Method/function names match actual code in diff
  - [ ] Test cases reflect tests actually added in diff
  - [ ] Nothing mentioned that isn't in the diff
- [ ] **Requirement text NOT copied** into CHANGELOG or PR (if provided)
  - [ ] No verbatim requirement text in any output
  - [ ] Ticket ID referenced instead (e.g., "Refs: DA-1515")
  - [ ] Requirement used only for context, not for content
- [ ] **Description only if user provided it** - No generated or assumed descriptions
  - [ ] If user did NOT provide description/summary → section is omitted or blank
  - [ ] If user provided description → use it as-is, do not embellish or change it
- [ ] **CHANGELOG is technical-focused**
  - [ ] Summary describes code changes, not business requirements
  - [ ] Files modified list shows actual changed files from diff
  - [ ] Implementations describe what was coded (from diff), not what was needed
  - [ ] **Testing section included ONLY if test files in diff or explicitly requested**
  - [ ] If testing included: test cases reflect actual tests in diff, not assumed tests
- [ ] **NO Business Requirements section** - All requirements are in JIRA ticket
- [ ] PR messages are under line limits (25 and 30 lines)
- [ ] Changelog file includes comprehensive technical details
- [ ] All sections in changelog are filled appropriately
- [ ] Type ([Feature]/[Fix]/[Perf]/etc.) is consistent
- [ ] No generic or template language remains
- [ ] File paths and code examples are specific to ACTUAL changes in the diff
- [ ] Release folder structure is complete (CHANGELOG.md, ddl/, data/, config/, docs/)
- [ ] **Ticket reference in CHANGELOG footer** (e.g., "Refs: DA-1515")

---

**You are now ready to generate PR messages and changelog.**
**Remember:** Only describe what's in the git diff. No assumptions. No hallucinations. No generated content if not provided by user.
