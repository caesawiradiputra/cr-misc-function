---
description: Generate staging + production PR messages and the per-ticket release changelog for the dev/master deployment flow
argument-hint: "[version] [\"optional requirement text\"]"
allowed-tools: Bash(git fetch:*), Bash(git branch:*), Bash(git diff:*), Bash(git log:*)
---

# Generate PR Message

Generate the pull request messages and release documentation for promoting a **feature/fix branch** through the deployment flow:

```text
feature/fix branch  ──PR──▶  dev (Staging / pre-prod)  ──PR──▶  master (Production)
```

**Branch roles:**

- `sit` — the SIT/UAT environment. **Intentionally out of scope:** merges to `sit` are frequent and often trivial (rename a function, tweak a test), so they don't warrant an AI-generated PR message or changelog. Write those by hand.
- `dev` — **staging / pre-production**, the gate before production. This command targets `dev`.
- `master` — production.

Run this command **when the branch is ready to merge into `dev`**. It always produces **both** PR messages at once:

1. **Feature/Fix → Dev** — full message for the staging PR (used now).
2. **Dev → Master** — short message for the production PR (reused later when `dev` is promoted to `master`).

It also creates or updates a single per-ticket changelog at `release/<TICKET-ID>/CHANGELOG.md`. **Every PR is a deployment** — the changelog is always created/updated for traceability.

## Usage

```text
/generate-pr-message [version] ["optional requirement text"]
```

**Parameters (both optional, order-independent):**

- `[version]` — semantic version **without a `v` prefix**, e.g. `1.2.0` (digits + dots).
  - Omit → the changelog entry is recorded under `[Unreleased]` until a version is assigned.
  - Provide when deploying app code that increments a version; omit for DB/config/infra-only changes.
- `["requirement text"]` — JIRA context in any language (quoted). Used **only** to understand intent. **Never copied** into any output. The ticket ID always comes from the branch name, not this text.

**Examples:**

- `/generate-pr-message 1.2.0` → versioned changelog entry + both PR messages
- `/generate-pr-message 1.2.0 "Penambahan variable baru untuk tracking reject"` → versioned, with Indonesian context
- `/generate-pr-message` → `[Unreleased]` changelog entry + both PR messages

---

## ⚠️ Critical Rules

1. **Git diff is the only source of truth.** If it is not in `git diff origin/dev...HEAD`, it does not exist in this PR. Never assume, infer, or invent files, methods, tests, or objectives.
2. **Never copy requirement text** into the CHANGELOG or PR — whether it comes from the `["requirement text"]` parameter or a requirement doc/PDF in the ticket folder. Use it for context only; reference the ticket instead (`Refs DA-XXXX`).
3. **No Business Requirements section** — all requirements live in JIRA.
4. **Description only if the user provided one.** If they did not, do not generate or assume one.
5. **Testing section only if** test files appear in the diff OR the user explicitly asks. Describe only tests actually present.
6. **Version never carries a `v` prefix** — use `1.2.0`, not `v1.2.0`, everywhere (changelog, PR messages, tags).
7. **Agent creates files only.** Do **not** run `git add`/`commit`/`push`/`tag` — the user does that after review.

---

## Workflow

> If the workspace root is not the git repo (nested repo folder), locate the folder containing `.git` and run all git commands from there. Project CLAUDE.md files document this where it applies.

### Phase 1: Detect Context

```powershell
git fetch origin
git branch --show-current
```

- **Extract ticket ID** from branch name — `fea/DA-1079-feature-name` → `DA-1079`. The branch is authoritative.
- **Identify type** from branch prefix: `fea/` → Feature, `fix/` → Fix, `refactor/` → Refactor, `perf/` → Perf.
- **Resolve version:** provided `X.Y.Z` as-is (strip any leading `v`), else use `Unreleased`.

### Phase 2: Analyze Changes (BEFORE writing anything)

The staging PR diff is the basis for both messages — the feature's changes are what will flow `dev → master`.

```powershell
git diff origin/dev...HEAD --name-status   # files changed
git log  origin/dev..HEAD --oneline         # commit history
git diff origin/dev...HEAD                  # actual code changes
```

Categorize changes by file and functionality **based only on actual diff content**. Note breaking changes and dependencies only if visible in the diff.

**Two sources feed every output:** (1) the git diff above, and (2) the files you placed in the ticket folder (DDL, scripts, config, requirement PDFs — inventoried in Step 3a). Code descriptions come from the diff; deployment artifacts and intent come from the folder. Reflect both in the changelog and reference them in the PR messages.

### Phase 3: Create / Update the Per-Ticket Changelog

The changelog lives at a stable, **date-free, per-ticket** path so every run for the same ticket lands in the same file:

```text
release/<TICKET-ID>/
├── CHANGELOG.md   # one file per ticket, multiple version entries appended over time
├── ddl/           # database schema changes
├── data/          # data migration scripts
├── config/        # configuration changes
└── docs/          # implementation details
```

Example: `release/DA-1079/CHANGELOG.md`

#### Step 3a — Inventory & read the ticket folder FIRST

Before writing anything to the changelog, **scan `release/<TICKET-ID>/` for files the user added** and read them — they are first-class context alongside the git diff:

```powershell
Get-ChildItem -Path "release\<TICKET-ID>" -Recurse -File | Select-Object FullName, Length
```

Then read the relevant artifacts and fold them into the changelog:

- **`ddl/`** — read each `.sql` file; reference DDL changes in the **Changes Made** and call out schema/migration impact under **Breaking Changes**.
- **`data/`** — read migration/seed scripts; note data backfills or one-off scripts reviewers must run.
- **`config/`** — read config changes; note new/changed settings.
- **`docs/`** — read implementation notes, design docs, and **requirement PDFs** (use the Read tool's `pages` parameter for PDFs — up to 20 pages per call). Use these the same way as the `["requirement text"]` parameter: **for context only**, to understand intent. **Do not copy** requirement text into the changelog; describe the actual code/DDL/script changes instead.

List every file found under these subfolders in the changelog's **Release Artifacts** section so the deployment package is self-documenting. If a folder is empty, omit it.

**Check whether `release/<TICKET-ID>/CHANGELOG.md` already exists:**

- **Does not exist** → create the folder structure and a new CHANGELOG with one version entry (see template).

  ```powershell
  New-Item -ItemType Directory -Path "release\<TICKET-ID>\ddl"    -Force
  New-Item -ItemType Directory -Path "release\<TICKET-ID>\data"   -Force
  New-Item -ItemType Directory -Path "release\<TICKET-ID>\config" -Force
  New-Item -ItemType Directory -Path "release\<TICKET-ID>\docs"   -Force
  ```

- **Already exists** → read it, then **append or update**, never overwrite the whole file:
  - If a section for the **same version** (or `[Unreleased]`) exists → update that section in place with the latest diff analysis.
  - If this is a **new version** → insert a new version section at the **top** of the entries (newest first), keeping all prior entries intact.
  - Preserve the file header and the `ddl/`, `data/`, `config/`, `docs/` subfolders (user may have added files).

### Phase 4: Generate Both PR Messages

Always display both, regardless of which PR is being opened right now:

- **Feature/Fix → Dev** (full) — for the staging PR you are opening now.
- **Dev → Master** (short) — save and reuse when promoting `dev` to production.

---

## Output Templates

### CHANGELOG.md (per ticket, appendable — newest entry first)

The file has a **stable header** (ticket-level, written once) followed by one **version section per release**. Re-running the command adds or updates a version section without disturbing the header or older entries.

```markdown
# Changelog — {Ticket-ID}: {Brief Title}

**Ticket:** {Ticket-ID}
**Branch:** {branch-name}
**JIRA:** https://bfifinance.atlassian.net/browse/{Ticket-ID}

All notable changes for this ticket are documented here. Newest entry on top.

---

## [{version}] — YYYY-MM-DD

**Type:** {Feature/Fix/Refactor/Perf}

### 📝 Summary
[2-3 paragraphs describing the technical code changes — NOT business requirements.]

### 🎯 Objectives
[Derived from actual code changes only.]
- Objective 1

### 📋 Changes Made
**Files Modified**
- `path/to/file.py` — Description of change (from diff)

**Key Implementations**
1. **Name** (`path`): what was added/modified in the code

### 📂 Release Artifacts
[Files added under the ticket folder. Omit any empty group.]
- **DDL:** `ddl/001_add_column.sql` — short description
- **Data:** `data/backfill.sql` — short description
- **Config:** `config/feature_flag.yaml` — short description
- **Docs:** `docs/requirement.pdf`, `docs/design.md`

### 🧪 Testing Performed
[Include ONLY if test files are in the diff or explicitly requested.]

### 💥 Breaking Changes
[List, or "None". Include schema/migration impact from `ddl/` here.]

### 📦 Dependencies
[Added/updated with reason, or "No new dependencies".]

### 🔍 Code Review Notes
- Note for reviewers

---

## [{previous-version}] — YYYY-MM-DD
[earlier entry preserved as-is …]

---

**Author:** {Name}
**Reviewed By:** [To be filled after review]
```

- Use `[Unreleased]` as the version heading when no version was provided. When a version is later supplied, rename that heading to `[X.Y.Z] — YYYY-MM-DD`.
- The trailing **Author / Reviewed By** block stays at the bottom of the file (ticket-level), not per entry.

### PR Message 1 — Feature/Fix → Dev (keep under 25 lines)

Title: `[{Type}] {Ticket-ID}: {Brief description}`

```markdown
## 🎯 Overview
[1-2 sentences — only if user provided a description, else describe code changes from diff.]

## 📋 Changes
- Change 1 (from diff)
- Change 2 (from diff)

## 🧪 Testing
- [ ] Items only if test files in diff

## 🚀 Deployment Steps
[Only if ticket folder has ddl/data/config artifacts; else omit this section.]
- [ ] Run `ddl/001_add_column.sql` on target DB
- [ ] Run `data/backfill.sql` after schema migration
- [ ] Apply `config/feature_flag.yaml`

## 📝 Notes
- Important reviewer notes

## 📚 Documentation
See `release/<TICKET-ID>/CHANGELOG.md`

---
**Refs:** {Ticket-ID}
**Type:** {Type}
```

### PR Message 2 — Dev → Master (short; keep under 20 lines)

Title: `Release {version}: {Brief summary}` (or `Promote {Ticket-ID} to production` if no version)

```markdown
## 🚀 Production Release {version}

Promotes the following staging-tested change to production.

## 📋 Included
- **{Ticket-ID}**: {Brief description} — [{Type}]

## ✅ Staging Validation
- [x] Validated in dev (staging / pre-prod)
- [x] Integration tests passed

## 🚀 Production Deployment Steps
[Only if ticket folder has ddl/data/config artifacts; else omit this section.]
- [ ] Run `ddl/...` on production DB
- [ ] Run `data/...` script
- [ ] Apply `config/...`

## 📚 Documentation
- `release/<TICKET-ID>/CHANGELOG.md`

---
**Refs:** {Ticket-ID}
**Release Type:** {Major/Minor/Patch}
```

### Git Tag Commands (after the Dev → Master PR is merged)

Tag once the change reaches production. Version has **no `v` prefix**:

```powershell
git checkout master
git pull origin master
git tag -a X.Y.Z -m "Release X.Y.Z: {Brief description of features and fixes}"
git push origin X.Y.Z
```

Semantic versioning: **X** major/breaking, **Y** minor/feature, **Z** patch/fix. (Omit tagging if no version was assigned.)

---

## User Action (after review)

The agent creates files and displays both PR messages; the user runs git:

```powershell
git add release\<TICKET-ID>\
git commit -m "📦 release(<ticket>): add <brief-description> deployment package"
git push
```

Tip: after staging the release folder, `/commit` generates and creates this commit following the full Conventional Commits + gitmoji convention.

Then open the **Feature → Dev** PR with PR Message 1. Later, when promoting `dev` to `master`, open that PR with PR Message 2.

---

## Pre-Submission Checklist

- [ ] **No hallucinations** — every file, method, and test verified against `git diff origin/dev...HEAD`
- [ ] Branch name parsed → correct ticket ID
- [ ] Version resolved correctly and written **without a `v` prefix** (or `[Unreleased]`)
- [ ] Changelog path is `release/<TICKET-ID>/CHANGELOG.md` — **no date/timestamp in the name**
- [ ] Ticket folder inventoried **before** editing the changelog; `ddl/` `data/` `config/` `docs/` files (incl. requirement PDFs) read and reflected in **Release Artifacts**
- [ ] Existing changelog **appended/updated** (new version on top, header + older entries preserved) — never overwritten
- [ ] Both PR messages generated (Feature → Dev full, Dev → Master short)
- [ ] Requirement text **not copied** anywhere; ticket referenced instead (`Refs DA-XXXX`)
- [ ] Description present **only** if user provided one
- [ ] CHANGELOG is technical-focused; **no Business Requirements section**
- [ ] Testing section only if test files in diff or explicitly requested
- [ ] PR messages within line limits (25 / 20)
- [ ] No git commands run by the agent — user handles add/commit/push/tag
