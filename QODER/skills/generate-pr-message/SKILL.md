---
name: generate-pr-message
version: "1.1.0"
updated: "2026-06-18"
related_skills:
  - commit
description: Generate staging + production PR messages and per-ticket release changelog for the dev/master deployment flow. Use when the user triggers /generate-pr-message, asks to create a PR message, or needs release documentation. Accepts optional version and requirement text.
---

# Generate PR Message

Generate pull request messages and release documentation for promoting a feature/fix branch through the deployment flow:

```text
feature/fix branch --PR--> dev (Staging) --PR--> master (Production)
```

Produces **both** PR messages at once:
1. **Feature/Fix -> Dev** — full message for the staging PR (used now)
2. **Dev -> Master** — short message for the production PR (reused later)

Also creates/updates a per-ticket changelog at `release/<TICKET-ID>/CHANGELOG.md`.

## Usage

```text
/generate-pr-message [version] ["optional requirement text"]
```

- `[version]` — semantic version without `v` prefix (e.g. `1.2.0`). Omit -> `[Unreleased]`.
- `["requirement text"]` — Issue tracker context for understanding intent only. **Never copied** into output.

## Critical Rules

1. **Git diff is the only source of truth.** If not in `git diff origin/dev...HEAD`, it does not exist.
2. **Never copy requirement text** into CHANGELOG or PR — reference the ticket instead (`Refs <TICKET-ID>`).
3. **No Business Requirements section** — all requirements live in the issue tracker.
4. **Description only if the user provided one.**
5. **Testing section only if** test files appear in the diff OR user explicitly asks.
6. **Version never carries a `v` prefix** — use `1.2.0`, not `v1.2.0`.
7. **Agent creates files only.** Do NOT run `git add`/`commit`/`push`/`tag`.
8. **Release folder files are the FIX.** Files in `release/<TICKET-ID>/` are the new/corrected versions being deployed, not passive reference material. Analyze them for logic changes and document what they fix.
9. **Current ticket = new, older ticket = old.** When comparing release folders across tickets, the current ticket's folder is always the NEW/FIX version. Older tickets' folders represent the OLD/BUGGY versions that are being corrected.
10. **PR messages in fenced code blocks.** All PR messages, commit messages, and git tag commands must be output inside fenced markdown code blocks (` ```markdown `, ` ```powershell `) for direct copy-paste. Never render as plain markdown.

## Workflow

### Phase 1: Detect Context

```powershell
git fetch origin
git branch --show-current
```

- **Extract ticket ID** from branch: auto-detect the first segment matching `[A-Z]+-\d+` from the branch name (e.g. `fea/DA-1079-feature-name` -> `DA-1079`, `fea/PROJ-456-thing` -> `PROJ-456`)
- **Identify type** from prefix: `fea/` -> Feature, `fix/` -> Fix, `refactor/` -> Refactor
- **Resolve version:** provided `X.Y.Z` as-is (strip leading `v`), else `Unreleased`

### Phase 2: Analyze Changes (BEFORE writing anything)

```powershell
git diff origin/dev...HEAD --name-status
git log  origin/dev..HEAD --oneline
git diff origin/dev...HEAD
```

Categorize changes based **only on actual diff content**. Two sources feed every output: (1) the git diff, and (2) files in the ticket folder.

#### Phase 2b: Analyze Release Folder Artifacts

Read ALL files in `release/<TICKET-ID>/` (all subfolders). For SQL/config/script files:
- Identify what logic they contain and what they fix compared to previous releases
- If older release folders exist (e.g. `release/DA-1505/`), compare them to understand what changed
- Document the fix direction: OLD (previous ticket) → NEW (current ticket)
- Release folder files are active deployment artifacts — they must be listed in Changes Made, not just Release Artifacts

### Phase 3: Create/Update the Per-Ticket Changelog

Path: `release/<TICKET-ID>/CHANGELOG.md`

```text
release/<TICKET-ID>/
+-- CHANGELOG.md
+-- ddl/       # database schema changes
+-- data/      # data migration scripts
+-- config/    # configuration changes
+-- flink/     # Flink SQL streaming jobs
+-- docs/      # implementation details
+-- (any other subfolder — scan all)
```

#### Step 3a — Inventory & read the ticket folder FIRST

Scan `release/<TICKET-ID>/` for ALL files recursively. Read artifacts and fold into changelog:
- `ddl/` — schema/migration impact
- `data/` — backfills or one-off scripts
- `config/` — new/changed settings
- `flink/` — Flink SQL streaming jobs (analyze logic changes vs previous releases)
- `docs/` — context only (requirement PDFs for understanding, not copying)
- Any other subfolder — scan and categorize

**Important:** Release folder files are the corrected versions being deployed. Analyze their logic to understand what they fix — do not just list filenames.

List every file in **Release Artifacts** section.

**If CHANGELOG exists**: append/update (newest version on top, preserve header + older entries). **If not**: create folder structure and new CHANGELOG.

### Phase 4: Generate Both PR Messages

Always display both, regardless of which PR is being opened now.

### Phase 5: Generate Release Folder Commit Message

After generating both PR messages, also generate a commit message for the release folder:

```text
📦 release(<TICKET-ID>): {brief description of artifacts}

- {list key files and what they fix/add}

Refs <TICKET-ID>
```

## Output Templates

### CHANGELOG.md (per ticket, appendable)

```markdown
# Changelog — {Ticket-ID}: {Brief Title}

**Ticket:** {Ticket-ID}
**Branch:** {branch-name}
**Issue Tracker:** {ISSUE_TRACKER_URL}/{Ticket-ID}

---

## [{version}] — YYYY-MM-DD

**Type:** {Feature/Fix/Refactor/Perf}

### Summary
[2-3 paragraphs describing technical code changes — NOT business requirements.]

### Objectives
[Derived from actual code changes only.]

### Changes Made
**Files Modified**
- `path/to/file.py` — Description of change (from diff)

**Key Implementations**
1. **Name** (`path`): what was added/modified

### Release Artifacts
[Files in ticket folder. Omit empty groups.]

### Testing Performed
[Only if test files in diff or explicitly requested.]

### Breaking Changes
[List, or "None". Include schema/migration impact.]

### Dependencies
[Added/updated with reason, or "No new dependencies".]

### Code Review Notes
- Note for reviewers

---

**Author:** {Name}
**Reviewed By:** [To be filled after review]
```

### PR Message 1 — Feature/Fix -> Dev (under 25 lines)

Title: `[{Type}] {Ticket-ID}: {Brief description}`

Sections: Overview (1-2 sentences), Changes (from diff), Testing (if applicable), Deployment Steps (only if ticket folder has artifacts), Notes, Documentation link, Refs footer.

### PR Message 2 — Dev -> Master (under 20 lines)

Title: `Release {version}: {Brief summary}` (or `Promote {Ticket-ID} to production`)

Sections: Production Release header, Included (ticket + type), Staging Validation checklist, Production Deployment Steps (only if artifacts exist), Documentation link, Refs footer.

### Git Tag Commands (after Dev -> Master PR merged)

> **Agent: do NOT execute these commands.** Display them as reference for the user to run manually.
> Rule 7 applies: the agent creates files only — no `git add`, `commit`, `push`, or `tag`.

```powershell
# Run manually after the Dev -> Master PR is merged:
git checkout master
git pull origin master
git tag -a X.Y.Z -m "Release X.Y.Z: {Brief description}"
git push origin X.Y.Z
```

## Pre-Submission Checklist

- [ ] No hallucinations — every file/method/test verified against diff
- [ ] Branch name parsed -> correct ticket ID
- [ ] Version without `v` prefix (or `[Unreleased]`)
- [ ] Changelog at `release/<TICKET-ID>/CHANGELOG.md` — no date in filename
- [ ] Ticket folder inventoried before editing; artifacts reflected in Release Artifacts
- [ ] Existing changelog appended/updated — never overwritten
- [ ] Both PR messages generated
- [ ] Requirement text not copied anywhere
- [ ] Testing section only if test files in diff
- [ ] PR messages within line limits (25/20)
- [ ] All PR messages, commit messages, and tag commands in fenced code blocks
- [ ] Release folder files analyzed for logic changes (not just listed)
- [ ] Old vs new release version correctly identified (current ticket = fix, older ticket = buggy)
- [ ] Release folder commit message generated
- [ ] No git commands run by agent
