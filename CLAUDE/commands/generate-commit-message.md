# Generate Commit Message

Generate a well-structured, semantically correct commit message using **Conventional Commits** format with **gitmoji** annotations. Analyzes staged changes, distinguishes primary vs secondary changes, and recommends splitting when beneficial.

## Workflow

### Phase 1: Analysis

#### Step 1 — Validate repository state

```powershell
git status
```

- ✅ Staged changes exist → proceed
- ❌ Nothing staged → inform user: suggest `git add .` or `git add -p`
- ❌ Merge conflicts → ask user to resolve first

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

---

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

---

## When to Recommend Splitting

Suggest splitting if staged changes include:

- Multiple unrelated PRIMARY changes
- PRIMARY change + very large secondary refactoring that could stand alone
- Different modules with different types (fix in auth + new feature in payments)

**How to suggest splitting:**

```text
I notice your staged changes include:
1. PRIMARY: New endpoint (app/api/users.py)
2. SECONDARY: Modernized type hints (50+ lines, app/utils/)

I recommend 2 commits:
  Commit 1: ✨ feat(api): add user management endpoints
  Commit 2: ♻️ refactor(core): modernize type hints

To split:
  git reset
  git add app/api/users.py
  git commit -m "..."
  git add app/utils/
  git commit -m "..."
```

---

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

---

## Phase 4: Post-Generation Action

After presenting the commit message, always ask the user which action to take next.
Gitmoji characters cannot be reliably copy-pasted in the Claude terminal, so do not leave the user to run the commit manually.

Present these options explicitly:

```text
What would you like to do?
1. Commit now — I'll run `git commit` with this message
2. Refine — invoke /refine-commit-message to iterate on the message
3. Cancel — do nothing
```

**If the user chooses option 1**, run the commit using a HEREDOC so the emoji is passed correctly:

```powershell
git commit -m "$(cat <<'EOF'
<full commit message here>
EOF
)"
```

Then confirm success with the commit hash from `git log --oneline -1`.

**If the user chooses option 2**, invoke `/refine-commit-message` and pass the generated message as the starting point.

**If the user chooses option 3**, do nothing and inform the user the staged changes are still intact.

---

## Pre-Submission Checklist

- [ ] Ran `git diff --staged` — message based on actual diff, not assumptions
- [ ] PRIMARY vs SECONDARY changes identified
- [ ] Type based on PRIMARY changes
- [ ] Subject ≤72 chars, imperative mood, no period
- [ ] NEW files use "add", MODIFIED use context verb, DELETED use "remove"
- [ ] Secondary changes listed in body (not title)
- [ ] Ticket reference in footer (if branch has DA-XXXX)
- [ ] Breaking changes marked with `BREAKING CHANGE:` footer

---

## Critical Rules

1. **Never base type on line count** — 200 lines of docstrings + 10 lines of new logic = `feat`, not `docs`
2. **Never assume from chat history** — always verify with `git diff --staged`
3. **Always present for user review** before committing
4. **Always use imperative mood** — "Add caching layer" not "Added caching layer"
