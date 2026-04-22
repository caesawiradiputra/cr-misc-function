---
name: generate-commit-message
description: Generate well-structured, semantically correct commit messages using **Conventional Commits** format with **gitmoji** annotations. This skill analyzes only staged Git changes and produces technical commit messages.
---

# Generate Commit Message Skill

Master the art of crafting meaningful, standardized commit messages that document your changes clearly and enable better project history tracking.

## When to Use This Skill

Trigger this skill when you want to:
- Generate a commit message from staged Git changes
- Create a well-structured message following **Conventional Commits** standard
- Add semantic meaning through **gitmoji** annotations
- Distinguish between primary changes (logic/features) and secondary changes (refactoring/style)
- Ensure proper formatting and character limits (≤72 chars)

**Common prompts:**
- "generate commit message"
- "commit message"
- "create a commit message"
- "what should my commit message be?"

## Prerequisites

- Git repository initialized
- Changes staged with `git add` or `git add -p`
- Git configured with user name and email

## Workflow: Analyzing Staged Changes

### Step 1: Validate Repository State

- Run `git status` to check for staged changes
- If nothing is staged: inform user and suggest `git add` workflow
- If staged changes exist: proceed to analysis

```bash
git status
```

### Step 2: Analyze Staged Changes

Run `git diff --staged` to retrieve full diff and parse file headers:

```bash
git diff --staged
```

**Parse file diff headers** to categorize each change:
- `new file mode 100644` → **NEW FILE** (use "add" verb)
- `--- a/file +++ b/file` → **MODIFIED** (use context-appropriate verb)
- `deleted file mode 100644` → **DELETED** (use "remove" verb)

Group changes by type: **Logic/Feature changes** vs **Refactoring/Style changes**

### Step 3: Identify Primary vs Secondary Changes

**PRIMARY CHANGES** (drives commit title):
- Schema changes (new/modified database columns)
- New functionality (features, capabilities, business logic)
- Behavior changes (logic modifications affecting output/behavior)
- Database alterations (any data structure changes)

**SECONDARY CHANGES** (supporting details in body):
- Type hint modernization (e.g., Python 3.10+ union syntax)
- Import reorganization
- Code formatting/style
- Code refactoring (without behavior change)

**Decision Logic:**
- If PRIMARY changes exist → select type based on primary change
- If ONLY secondary changes → select type based on refactoring type

### Step 4: Select Type and Gitmoji

Use the reference table below to select appropriate type. Consider what changed:
- New feature? → `feat` ✨
- Bug fix? → `fix` 🐛
- Refactor only? → `refactor` ♻️
- Performance? → `perf` 🚀
- Tests? → `test` 🧪
- Docs/comments? → `docs` 📝

### Step 5: Determine Scope

- Use **single word or hyphenated scope** (lowercase, 15 chars max)
- Scope = affected module/area (e.g., `auth`, `db-pool`, `api-gateway`)
- If multiple scopes: pick primary scope or use generic term (`core`, `infra`)
- Scope is **optional** but **recommended**

### Step 6: Write and Validate Subject Line

Format: `<gitmoji> <type>(<scope>): <description>`

**Constraints:**
- **≤72 characters TOTAL** (including gitmoji and space)
- **Imperative mood** (command form, present tense)
- **Lowercase** except proper nouns/acronyms
- **No period** at end
- **Specific and descriptive** (what changed, not just "update file")

**Character Count Example:**
```
✨ feat(auth): add multi-factor authentication support
^ ^ ^^^^      ^^^  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
| |  type     |   description (44 chars)
| scope      |
gitmoji (2)  space
Total: 2 + 1 + 4 + 1 + 1 + 44 = 53 chars ✓
```

### Step 7: Write Body (Optional)

Include only if changes need explanation:
- Explain the **WHAT** and **WHY**, not the **HOW**
- Keep to **2-4 short lines** maximum
- Omit if self-explanatory
- Start with **blank line** after subject
- Use **bullet points** for multiple related changes

### Step 8: Write Footer (Optional)

Add footer information when applicable:

```
Refs DA-XXXX              # Reference related ticket
Closes DA-1234            # Auto-closes ticket on merge
BREAKING CHANGE: <desc>   # Mark breaking changes prominently
```

## Conventional Commits Format

### Structure

```
<gitmoji> <type>(<scope>): <description>

[optional body: explanation of what and why]

[optional footer: Refs DA-XXXX, BREAKING CHANGE: ...]
```

### Subject Line Requirements

**Character Limits:**
- Target: ≤72 characters (including gitmoji and space)
- Maximum: 120 characters
- **Count everything:** gitmoji (1 char) + space (1 char) + type + scope + description

**Formatting:**
```
✨ feat(onboarding): add updated_at timestamp column
```
This is 50 characters ✅

### Commit Types & Gitmoji Reference

| Gitmoji | Type | Usage | When to Use |
|---------|------|-------|-------------|
| ✨ | `feat` | New feature or capability | New endpoint, new calculation, new functionality |
| 🐛 | `fix` | Bug fix or issue resolution | Fix null reference, fix logic error, fix crash |
| 🚀 | `perf` | Performance improvement | Optimize query, cache result, speed up algorithm |
| ♻️ | `refactor` | Code restructuring (no behavior change) | Extract method, rename variables, restructure module |
| 📝 | `docs` | Documentation, comments, docstrings | Update README, add docstrings, clarify comments |
| 🧪 | `test` | Test additions, updates, fixes | Add unit tests, fix flaky test, improve coverage |
| 📦 | `build` | Build system, dependencies, packaging | Add dependency, update version, configure build |
| 🔧 | `ci` | CI/CD configuration or scripts | Add GitHub Actions, update pipeline config |
| 🎨 | `style` | Code formatting or style (no logic change) | Prettier, black formatting, lint fixes |
| 🔒 | `security` | Security fix or hardening | Fix vulnerability, sanitize input, add validation |
| 🗑️ | `chore` | Remove code/files/dead code | Delete unused files, remove legacy code |
| 🏗️ | `arch` | Architecture or major refactor | Redesign module, restructure system, rearchitect |
| ⏮️ | `revert` | Revert a previous commit | Undo broken release, revert failed change |

### Description Requirements

**Use imperative mood (command form, present tense):**
- ✅ `Add feature X` (not "Added feature X")
- ✅ `Fix bug in parser` (not "Fixes bug in parser")
- ✅ `Update documentation` (not "Updates documentation")

**Keep specific and actionable:**
- ✅ `fix: handle null reference in token validation`
- ❌ `fix: stuff`

### Scope Selection

Scope indicates the affected module/area:
- Use single word or **hyphenated scope** when possible
- Examples: `auth`, `db-pool`, `api-gateway`, `user-service`
- Optional but recommended

---

## Decision Tree: Type Selection

```
Does diff include PRIMARY changes?
├─ YES (schema, logic, behavior, DB changes)
│  └─ Select type based on PRIMARY change
│     ├─ New functionality? → feat
│     ├─ Bug fixed? → fix
│     ├─ Performance improved? → perf
│     └─ Architecture changed? → arch
│
└─ NO (only refactoring/style)
   └─ Select type based on secondary change type
      ├─ Type hints, imports → refactor
      ├─ Code formatting → style
      ├─ Optimize without new logic → perf
      ├─ Add tests → test
      └─ Remove code → chore
```

---

## Common Pitfalls to Avoid

❌ **"Add" verb for MODIFIED files**
- ✅ Correct: `fix(module): handle null reference`
- ❌ Incorrect: `add null check` (diff shows MODIFIED, not new file)

❌ **Generic or vague descriptions**
- ✅ Correct: `fix(parser): resolve stack overflow in recursive descent`
- ❌ Incorrect: `fix parser bug`

❌ **Past tense or non-imperative**
- ✅ Correct: `Refactor authentication handler`
- ❌ Incorrect: `Refactored authentication handler`

❌ **Subject line too long**
- ✅ Correct (58 chars): `feat(auth): add multi-factor authentication support`
- ❌ Incorrect (98 chars): `add comprehensive multi-factor authentication support with SMS and email notifications`

---

### Body (Optional)

Include only if changes need explanation:
- Explain the **WHAT** and **WHY**, not the **HOW**
- Keep to 2-4 short lines
- Omit if self-explanatory
- Start with blank line after subject

**Example:**
```
✨ feat(onboarding): add updated_at timestamp column

- Add updated_at column with server default CURRENT_TIMESTAMP
- Modernize type hints to Python 3.10+ union syntax
- Reorganize imports for better readability
```

### Footer (Optional)

Add footer information when applicable:

```
Refs DA-XXXX              # Reference related ticket
Closes DA-1234            # Auto-closes ticket on merge
BREAKING CHANGE: <desc>   # Mark breaking changes prominently
```

## Examples

### Simple Feature
```
✨ feat(auth): add two-factor authentication support

Refs DA-1234
```

### Bug Fix with Explanation
```
🐛 fix(parser): resolve null reference exception in token validation

- Add null checks before accessing token properties
- Handle edge case when token is expired
- Add unit tests for both scenarios

Closes DA-5678
```

### Performance Improvement
```
🚀 perf(database): optimize query execution time for user lookups

- Add composite index on user_id and created_at
- Reduce query execution from 2s to 200ms
- Benchmark results in performance tracking system

Refs DA-2345
```

### Refactoring
```
♻️ refactor(api): consolidate duplicate request handlers into base class

Refs DA-3456
```

### Documentation
```
📝 docs(readme): update installation and configuration instructions

Closes DA-4567
```

### Breaking Change
```
🏗️ arch(db): redesign connection pool configuration

BREAKING CHANGE: `connection_config` dict replaced with `DBConfig` dataclass; migrate configuration before upgrading

Refs DA-6789
```

### Security Fix
```
🔒 security(auth): sanitize user input to prevent XSS attacks

- Add HTML escaping to all user-facing output
- Add CSP headers to responses
- Add security audit notes

Closes DA-7890
```

## Step-by-Step Workflow

### 1. Run Git Diff Staged
```bash
git diff --staged
```

### 2. Identify File Types
Look for these patterns in the diff:
- `new file mode 100644` → **NEW FILE** (use "add")
- `--- a/file` and `+++ b/file` → **MODIFIED** (use "fix"/"refactor"/"update")
- `deleted file mode 100644` → **DELETED** (use "remove")

### 3. Prioritize Changes
- Logic/features/schema changes = PRIMARY (title focus)
- Type hints/imports/formatting = SECONDARY (body details)
- If only secondary changes, focus title on refactoring type

### 4. Generate Message
Choose appropriate type and gitmoji, count characters, apply format.

### 5. Create Commit
```bash
git commit -m "✨ feat(scope): description"

# Or for multi-line (opens editor):
git commit
```

## Troubleshooting

### "Nothing to commit"
```bash
# Stage changes first
git add .              # or git add -p for selective staging
git diff --staged      # verify staging
```

### "Message seems too short"
Add more detail:
- What changed? (be specific)
- Why did it change?
- Any related tickets?

### "Validation fails"
Check:
- [ ] Subject ≤72 characters?
- [ ] Using imperative mood?
- [ ] Includes gitmoji?
- [ ] Type is lowercase?
- [ ] No trailing punctuation?

## Quality Checklist

Before presenting the commit message, verify:

- [ ] Analyzed only `git diff --staged` (not chat history)
- [ ] Correctly identified file types (NEW vs MODIFIED vs DELETED)
- [ ] Subject line uses gitmoji + type + lowercase scope + imperative mood
- [ ] Subject line is ≤72 characters
- [ ] Type and scope are accurate and lowercase
- [ ] No period at end of subject line
- [ ] Body (if included) explains WHY, not WHAT
- [ ] Body uses 2-4 lines maximum
- [ ] Footer includes ticket reference if applicable
- [ ] Breaking change is clearly marked if applicable
- [ ] Message matches actual change type (NEW/MODIFIED/DELETED)
- [ ] Message is technical and diff-specific (no business context assumptions)

---

## Skill Execution Notes

### Ticket Parsing
- Extract ticket ID from branch name if pattern `[DA-XXXX]` exists
  - Example: branch `feat/DA-1000-add-auth` → suggest `Refs DA-1000` or `Closes DA-1000`

### Multiple Commits Suggestion
- If staged changes span **unrelated areas**, suggest splitting into multiple commits:
  - Commit 1: (module A change)
  - Commit 2: (module B change)
  - This keeps commit history clean and enables granular rollbacks

### Never Assume
- The diff is the **source of truth**
- Do not assume change type from conversation context
- Do not reference business context or chat history
- Stand-alone message must make sense without conversation context

### Validate Before Output
- Re-read the entire commit message
- Verify it accurately reflects the diff
- Check character count one more time
- Confirm no trailing punctuation

---

## Quick Commands

```bash
# Check staged changes
git status
git diff --staged

# View commit history
git log --oneline -10

# Amend last commit message
git commit --amend

# Revert to staging area (undo commit, keep changes)
git reset --soft HEAD~1
```

## References

- [Conventional Commits Specification](https://www.conventionalcommits.org/)
- [gitmoji Reference](https://gitmoji.dev/)
- [Google Commit Message Guidelines](https://google.github.io/styleguide/shellstyle.html#comments)
- [Udacity Git Style Guide](https://udacity.github.io/git-styleguide/)
