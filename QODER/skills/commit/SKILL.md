---
name: commit
version: "1.0.0"
updated: "2026-06-18"
related_skills:
  - generate-pr-message
description: Generate Conventional Commit + gitmoji message from staged changes, review, refine, and commit. Use when the user triggers /commit, asks to commit changes, or wants help writing a commit message. Supports 'amend' mode and custom guidance text.
---

# Commit

Generate a well-structured, semantically correct commit message using **Conventional Commits** format with **gitmoji** annotations, review it with the user, refine on feedback, and create the commit.

## Argument Routing

| Arguments | Behavior |
| --- | --- |
| *(empty)* | Full flow: analyze -> generate -> review -> commit |
| `amend` | Refine HEAD message: read with `git log -1 --format=%B`, jump to Phase 4, finish with `git commit --amend` |
| anything else | Treat as upfront guidance (e.g. `/commit emphasize the bug fix`) |

## Workflow

### Phase 1: Analysis

#### Step 1 — Validate repository state

```powershell
git status
```

- Staged changes exist -> proceed
- Nothing staged -> inform user: suggest `git add .` or `git add -p`
- Merge conflicts -> ask user to resolve first

If workspace root is not the git repo, locate the folder containing `.git`.

#### Step 2 — Analyze staged diff

```powershell
git diff --staged
```

Parse file headers: `new file mode` -> NEW FILE ("add"), `--- a/ +++ b/` -> MODIFIED, `deleted file mode` -> DELETED ("remove").

#### Step 3 — Extract ticket ID from branch name

```powershell
git branch --show-current
```

Pattern: `fea/<TICKET>-1234-description` -> extract the first segment matching `[A-Z]+-\d+` from the branch name (e.g. `fea/DA-1000-feature` -> `DA-1000`, `fea/PROJ-456-thing` -> `PROJ-456`).

### Phase 2: Categorize Changes

**PRIMARY changes** (application-impacting — drives commit title):
- New routes, endpoints, handlers, functions, or classes
- Logic changes: conditionals, algorithms, calculations
- Configuration changes affecting behavior
- Model/schema changes, database alterations
- Bug fixes, security fixes, performance improvements

**SECONDARY changes** (refactoring/maintenance — list in body):
- Docstring additions, type hint modernization
- Import reorganization, code style/formatting
- Code restructuring without logic change
- Dev dependencies, logging, comments, dead code removal

**Decision rule**: PRIMARY changes exist -> type based on PRIMARY; only secondary -> type based on secondary. Even if 80% is type hints, if 20% adds a new route -> use `feat`.

### Phase 3: Generate Message

#### Step 4 — Select type and gitmoji

```text
Primary changes present?
+-- New functionality/endpoints? -> feat [sparkles]
+-- Bug fixed in logic? -> fix [bug]
+-- Performance improved? -> perf [rocket]
+-- Security issue resolved? -> security [lock]
+-- Config/schema changed (new)? -> feat [sparkles]
+-- Config/schema changed (fix)? -> fix [bug]
+-- Major architecture change? -> arch [building_construction]

Only secondary changes?
+-- Code restructuring? -> refactor [recycle]
+-- Type hints only? -> chore [wrench]
+-- Docstrings only? -> docs [memo]
+-- Logging only? -> chore [wrench]
+-- Code formatting? -> style [art]
+-- Tests added/fixed? -> test [test_tube]
+-- Code removed? -> chore [wastebasket]
```

#### Step 5 — Select scope

Single word or hyphenated, lowercase, <=15 chars. Skip if changes span multiple unrelated modules.

#### Step 6 — Write subject line

Format: `<gitmoji> <type>(<scope>): <description>`

Rules: Imperative mood, lowercase (except proper nouns), no period at end, total <=72 characters.

#### Step 7 — Write body (optional)

Blank line after subject. Explain WHAT and WHY (not HOW). 2-4 bullet points max. List secondary changes as supporting details.

#### Step 8 — Write footer (when applicable)

- `Refs <TICKET-ID>` — related ticket (use auto-detected ticket ID from branch)
- `Closes <TICKET-ID>` — resolves ticket
- `BREAKING CHANGE: description`

### Phase 4: Review & Refine (interactive loop)

Present the generated message in a fenced `text` block, then **always ask which action to take**:

```text
What would you like to do?
1. Commit — create the commit with this message
2. Refine — tell me what to change and I'll iterate
3. Split — divide staged changes into multiple commits
4. Cancel — do nothing; staged changes stay intact
```

**Refinement mapping:**

| Feedback | Action |
| --- | --- |
| "Too long" | Trim subject; move details to body |
| "Too vague" | Add specific detail |
| "Wrong type" | Re-verify against the diff |
| "Wrong scope" | Narrow or broaden scope |
| "Missing context" | Add 1-2 body lines explaining WHY |
| "Emphasize X" | Reorder body bullets |
| "Add/remove ticket" | Insert or delete Refs/Closes footer |

Stop after 2-3 refinement rounds. Every refinement must keep format constraints (subject <=72 chars, imperative mood, no period).

### Phase 5: Execute Commit

Write the full message to `.git/COMMIT_MSG.txt` using the Write tool (preserves UTF-8 emoji), then commit:

```powershell
git commit -F .git/COMMIT_MSG.txt
git log --oneline -1
Remove-Item ".git/COMMIT_MSG.txt"
```

For `amend` mode: `git commit --amend -F .git/COMMIT_MSG.txt`.

Report the new commit hash and subject.

## Splitting

Recommend splitting when staged changes include:
- Multiple unrelated PRIMARY changes
- PRIMARY + very large secondary refactoring
- Different modules with different types

Propose grouping first, get confirmation, then: `git reset`, then for each group: `git add <files>`, run Phase 3-5.

## Type & Gitmoji Reference

> For the complete type/gitmoji reference, see [_shared/commit-types.md](../_shared/commit-types.md)

## Critical Rules

1. **Never base type on line count** — 200 lines of docstrings + 10 lines of new logic = `feat`
2. **Never assume from chat history** — always verify with `git diff --staged`
3. **Always present for user review** before committing — never auto-commit
4. **Always use imperative mood** — "Add caching layer" not "Added"
5. **Subject <=72 chars**, lowercase except proper nouns, no trailing period
6. **Secondary changes go in the body**, never in the title
7. **Ticket footer** (`Refs`/`Closes <TICKET-ID>`) whenever branch name carries a ticket ID
8. **`BREAKING CHANGE:` footer** whenever behavior or interfaces break
9. **Never commit with inline `-m`** — always `git commit -F` from a UTF-8 file
