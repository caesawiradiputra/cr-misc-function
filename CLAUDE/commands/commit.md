---
description: Generate Conventional Commit + gitmoji message from staged changes, review, refine, and commit
argument-hint: "[guidance text, or 'amend' to refine HEAD's message]"
allowed-tools: Bash(git status:*), Bash(git diff:*), Bash(git log:*), Bash(git branch:*), Bash(git commit:*), Bash(git reset:*), Bash(git add:*)
---

# Commit

Generate a well-structured, semantically correct commit message using **Conventional Commits** format with **gitmoji** annotations, review it with the user, refine on feedback, and create the commit. Analyzes staged changes, distinguishes primary vs secondary changes, and recommends splitting when beneficial.

## Argument Routing

`$ARGUMENTS` selects the entry point:

| Arguments | Behavior |
| --- | --- |
| *(empty)* | Full flow: analyze → generate → review → commit |
| `amend` | Refine the message of `HEAD`: read it with `git log -1 --format=%B`, jump to Phase 4, finish with `git commit --amend` |
| anything else | Treat as upfront guidance for generation (e.g. `/commit emphasize the bug fix over the refactor`) |

## Workflow

### Phase 1: Analysis

#### Step 1 — Validate repository state

```powershell
git status
```

- ✅ Staged changes exist → proceed
- ❌ Nothing staged → inform user: suggest `git add .` or `git add -p`
- ❌ Merge conflicts → ask user to resolve first

If the workspace root is not the git repo (nested repo folder), locate the folder containing `.git` and run all git commands from there.

#### Step 2 — Analyze staged diff

```powershell
git diff --staged
```

Parse file headers to determine change type:

- `new file mode` → **NEW FILE** (use "add" verb)
- `--- a/ +++ b/` → **MODIFIED** (use context verb)
- `deleted file mode` → **DELETED** (use "remove" verb)

#### Step 3 — Extract ticket ID from branch name

```powershell
git branch --show-current
```

Pattern: `feat/DA-1000-description` → extract `DA-1000`

### Phase 2: Categorize Changes

**PRIMARY changes** (application-impacting — drives commit title):

- New routes, endpoints, handlers, functions, or classes
- Logic changes: conditionals, algorithms, calculations
- Configuration changes affecting behavior
- Model/schema changes, database alterations
- Bug fixes, security fixes, performance improvements in critical paths

**SECONDARY changes** (refactoring/maintenance — list in body):

- Docstring additions or improvements
- Type hint modernization
- Import reorganization, code style/formatting fixes
- Code restructuring without logic change
- Dev dependencies, logging additions, comment improvements
- Dead code removal

**Decision rule — CRITICAL**:

- If PRIMARY changes exist → type is based on PRIMARY; secondary goes in body
- If ONLY secondary changes → type is based on secondary change type
- Even if 80% of diff is type hints, if 20% adds a new route → use `feat`

### Phase 3: Generate Message

#### Step 4 — Select type and gitmoji

```text
Primary changes present?
├─ New functionality/endpoints? → feat ✨
├─ Bug fixed in logic? → fix 🐛
├─ Performance improved? → perf 🚀
├─ Security issue resolved? → security 🔒
├─ Config/schema changed (new)? → feat ✨
├─ Config/schema changed (fix)? → fix 🐛
└─ Major architecture change? → arch 🏗️

Only secondary changes?
├─ Code restructuring? → refactor ♻️
├─ Type hints only? → chore 🔧
├─ Docstrings only? → docs 📝
├─ Logging only? → chore 🔧
├─ Code formatting? → style 🎨
├─ Tests added/fixed? → test 🧪
└─ Code removed? → chore 🗑️
```

#### Step 5 — Select scope

- Single word or hyphenated, lowercase, ≤15 chars
- Examples: `auth`, `db-pool`, `api`, `onboarding`, `parser`
- Skip scope if changes span multiple unrelated modules (or use `core`, `infra`)

#### Step 6 — Write subject line

Format: `<gitmoji> <type>(<scope>): <description>`

Rules:

- Imperative mood: "Add", "Fix", "Refactor" (not "Added", "Fixes")
- Lowercase (except proper nouns)
- No period at end
- Total length ≤72 characters

#### Step 7 — Write body (optional)

- Blank line after subject
- Explain WHAT and WHY (not HOW)
- 2-4 bullet points max
- List secondary changes as supporting details

#### Step 8 — Write footer (when applicable)

- `Refs DA-XXXX` — related ticket
- `Closes DA-1234` — resolves ticket (GitHub auto-closes on merge)
- `BREAKING CHANGE: description`

### Phase 4: Review & Refine (interactive loop)

Present the generated message in a fenced `text` block, then **always ask which action to take** — never commit without review, and never leave the user to run the commit manually (gitmoji cannot be reliably copy-pasted in the terminal):

```text
What would you like to do?
1. Commit — create the commit with this message
2. Refine — tell me what to change and I'll iterate
3. Split — divide staged changes into multiple commits
4. Cancel — do nothing; staged changes stay intact
```

**On Refine** — apply the matching action, re-present the message, and offer the same options again (stay in this loop):

| Feedback | Action |
| --- | --- |
| "Too long" | Trim subject; remove adjectives; use shorter synonyms; move details to body |
| "Too vague" | Add specific detail (e.g. "in login handler", "for bulk orders"); replace generic terms |
| "Wrong type" | Re-verify against the diff: behavior change → feat/fix; structure only → refactor; speed → perf |
| "Wrong scope" | Narrow or broaden scope; re-evaluate module |
| "Missing context" | Add 1-2 body lines explaining WHY the change was needed |
| "Emphasize X" | Reorder body bullets; put primary change first |
| "Add/remove ticket" | Insert or delete Refs/Closes footer lines |

Refinement example — shorten an overlong subject by demoting detail to the body:

```text
❌ BEFORE (98 chars):
✨ feat(api-gateway): add request rate limiting with sliding window algorithm and per-user quotas

✅ AFTER (59 chars):
✨ feat(api-gateway): add request rate limiting with quotas

- Implement sliding window algorithm
- Apply per-user quota enforcement
```

Every refinement must keep the format constraints from Phase 3 (subject ≤72 chars, imperative mood, no period, body explains WHY). Stop after 2-3 refinement rounds — if direction is still unclear, re-run Phases 1-3 from the actual diff.

**On Cancel** — do nothing and confirm the staged changes are still intact.

### Phase 5: Execute Commit

Gitmoji gets mangled by console encoding, so **never pass the message inline with `-m`**:

1. Write the full message to `.git\COMMIT_MSG_CLAUDE.txt` (inside the repo root) using the Write tool — it writes UTF-8 and preserves the emoji
2. Commit from the file and confirm:

```powershell
git commit -F .git\COMMIT_MSG_CLAUDE.txt
git log --oneline -1
Remove-Item ".git\COMMIT_MSG_CLAUDE.txt"
```

For `amend` mode, use `git commit --amend -F .git\COMMIT_MSG_CLAUDE.txt` instead.

Report the new commit hash and subject to the user.

## Splitting

Recommend splitting (or accept the user's Split choice) when staged changes include:

- Multiple unrelated PRIMARY changes
- PRIMARY change + very large secondary refactoring that could stand alone
- Different modules with different types (fix in auth + new feature in payments)

**Execution** — propose the grouping first, get confirmation, then do it:

1. Present the proposed commits: files per group + subject line for each
2. After confirmation: `git reset`
3. For each group: `git add <files of group>`, then run Phase 3 → Phase 5 for that commit

```text
I notice your staged changes include:
1. PRIMARY: New endpoint (app/api/users.py)
2. SECONDARY: Modernized type hints (50+ lines, app/utils/)

I recommend 2 commits:
  Commit 1: ✨ feat(api): add user management endpoints
  Commit 2: ♻️ refactor(core): modernize type hints

Proceed with this split?
```

## Type & Gitmoji Reference

| Gitmoji | Type | When to Use |
| --- | --- | --- |
| ✨ | `feat` | New feature, endpoint, capability |
| 🐛 | `fix` | Bug fix, logic error, crash |
| 🚀 | `perf` | Performance improvement |
| ♻️ | `refactor` | Code restructuring, no behavior change |
| 📝 | `docs` | Documentation, docstrings, README |
| 🧪 | `test` | Test additions, updates, fixes |
| 📦 | `build` | Dependencies, packaging |
| 🔧 | `ci` | CI/CD configuration or scripts |
| 🎨 | `style` | Code formatting, lint fixes |
| 🔒 | `security` | Security fix or hardening |
| 🗑️ | `chore` | Remove dead code, unused files |
| 🏗️ | `arch` | Major architecture change |
| ⏮️ | `revert` | Revert previous commit |

## Examples

```text
✨ feat(auth): add two-factor authentication support

Refs DA-1234
```

```text
🐛 fix(parser): resolve null reference exception in token validation

- Add null checks before accessing token properties
- Handle edge case when token is expired

Closes DA-5678
```

```text
✨ feat(onboarding): add updated_at timestamp column

- Add updated_at column with server default CURRENT_TIMESTAMP
- Modernize type hints to Python 3.10+ union syntax

Refs DA-9012
```

```text
🏗️ arch(db): redesign connection pool configuration

BREAKING CHANGE: `connection_config` dict replaced with `DBConfig` dataclass; migrate before upgrading

Refs DA-6789
```

## Critical Rules

1. **Never base type on line count** — 200 lines of docstrings + 10 lines of new logic = `feat`, not `docs`
2. **Never assume from chat history** — always verify with `git diff --staged`
3. **Always present for user review** before committing — never auto-commit
4. **Always use imperative mood** — "Add caching layer" not "Added caching layer"
5. **Subject ≤72 chars**, lowercase except proper nouns, no trailing period
6. **Secondary changes go in the body**, never in the title
7. **Ticket footer** (`Refs`/`Closes DA-XXXX`) whenever the branch name carries a ticket ID
8. **`BREAKING CHANGE:` footer** whenever behavior or interfaces break
9. **Never commit with inline `-m`** — always `git commit -F` from a UTF-8 file (Phase 5)
10. **Only run `git commit` when the user has explicitly said to** — either by invoking `/commit` themselves or by explicitly telling you to commit. Finishing an implementation, staging files, or reaching a natural stopping point is never itself permission to commit; if in doubt, stage the changes and stop, and wait for `/commit` or an explicit instruction.
