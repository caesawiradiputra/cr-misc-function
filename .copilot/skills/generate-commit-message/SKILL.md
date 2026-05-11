---
name: generate-commit-message
description: Generate well-structured, semantically correct commit messages using **Conventional Commits** format with **gitmoji** annotations. This skill analyzes only staged Git changes and produces technical commit messages.
---

# Generate Commit Message Skill

Master the art of crafting meaningful, standardized commit messages that document your changes clearly and enable better project history tracking.

## Quick Navigation

**New to commit messages?** → Start with [Prerequisites & Context](#prerequisites--context)

**Ready to generate?** → Jump to [Workflow: Analysis & Generation](#workflow-analysis--generation)

**Need a reference?** → See [Commit Message Format & Requirements](#commit-message-format--requirements)

**Stuck or getting errors?** → Check [Troubleshooting & Edge Cases](#troubleshooting--edge-cases)

**Want examples?** → Browse [Real-World Examples](#real-world-examples)

## When to Use This Skill

**✅ USE THIS SKILL FOR:**
- Generating a commit message from staged Git changes
- Creating well-structured messages following **Conventional Commits** standard
- Adding semantic meaning through **gitmoji** annotations
- Distinguishing between primary changes (logic/features) and secondary changes (refactoring/style)
- Ensuring proper formatting and character limits (≤72 chars)

**❌ DO NOT USE IF:**
- No changes are staged (`git diff --staged` returns empty)
- Changes are still being developed (stage first, then commit)
- You need to rewrite commit history (use `git rebase --interactive` instead)

**Common prompts:**
- "generate commit message"
- "commit message"
- "create a commit message"
- "what should my commit message be?"

## Prerequisites & Context

**Required:**
- Git repository initialized in workspace
- Changes staged with `git add` or `git add -p`
- Git configured with user name and email (`git config --list`)

**Execution context:**
- Run all commands from the Git repository root
- Commit message must reference only **staged** changes, never unstaged or chat history
- Message must be self-contained (makes sense without conversation context)

## Workflow: Analysis & Generation

### Phase 1: Analysis (3 steps)

#### Step 1: Validate Repository State

```bash
git status
```

**Expected outcomes:**
- ✅ Staged changes exist → proceed to Step 2
- ❌ Nothing is staged → inform user and suggest `git add` workflow
- ❌ Merge conflicts → ask user to resolve first

#### Step 2: Analyze Staged Diff

```bash
git diff --staged
```

**Parse file diff headers** to categorize changes:
- `new file mode 100644` → **NEW FILE** (use "add" verb)
- `--- a/file +++ b/file` with hunks → **MODIFIED** (use context-appropriate verb)
- `deleted file mode 100644` → **DELETED** (use "remove" verb)

**Key insight:** Git diff output is the **source of truth** — never assume change type from conversation.

#### Step 3: Categorize Changes

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

**Decision rule:**
- If PRIMARY changes exist → select type based on primary change
- If ONLY secondary changes exist → select type based on secondary change type

### Phase 2: Generation (5 steps)

#### Step 4: Select Type and Gitmoji (Decision Tree)

```
Does diff include PRIMARY changes?
├─ YES (schema, logic, behavior, DB changes)
│  └─ Select type based on PRIMARY change
│     ├─ New functionality? → feat ✨
│     ├─ Bug fixed? → fix 🐛
│     ├─ Performance improved? → perf 🚀
│     ├─ Security issue resolved? → security 🔒
│     └─ Major architecture changed? → arch 🏗️
│
└─ NO (only refactoring/style/tests)
   └─ Select type based on secondary change type
      ├─ Code restructuring? → refactor ♻️
      ├─ Code formatting? → style 🎨
      ├─ Tests added/fixed? → test 🧪
      ├─ Docs updated? → docs 📝
      └─ Code removed? → chore 🗑️
```

**Best practice:** If multiple types apply, choose the most impactful change type.

#### Step 5: Determine Scope

```
Does this commit affect multiple unrelated modules?
├─ NO  → Use specific scope (auth, db-pool, api, etc.)
└─ YES → Either:
   ├─ Pick primary scope only, OR
   └─ Use generic term (core, infra, deps)
```

- **Length**: 15 characters max
- **Format**: single word or hyphenated, lowercase
- **Optional** but recommended for readability

#### Step 6: Write Subject Line

Format: `<gitmoji> <type>(<scope>): <description>`

**Validation checklist:**
- [ ] Uses imperative mood (command form)
- [ ] Starts with gitmoji
- [ ] Type is lowercase and correct
- [ ] Scope (if used) is lowercase, single word or hyphenated
- [ ] Description is specific and actionable
- [ ] Total length ≤72 characters
- [ ] No period or punctuation at end

**Character count example:**
```
✨ feat(auth): add multi-factor authentication support
2  1   4      1 1  50 chars (description)
= 59 characters ✅
```

#### Step 7: Write Body (Optional)

Include ONLY if explanation is needed:
- Explain **WHAT** changed and **WHY** (not HOW)
- Maximum 2-4 short lines
- Use bullet points for multiple changes
- Blank line after subject line

#### Step 8: Write Footer (Optional)

Add footer only when applicable:
- Ticket references: `Refs DA-XXXX` or `Closes DA-1234`
- Breaking changes: `BREAKING CHANGE: description`
- Multiple lines: separate each with line break

### Phase 3: Ticket Parsing (Best Practice)

**Extract ticket ID from branch name when available:**
- Branch format: `feat/DA-1000-add-auth`
- Extract: `DA-1000`
- Add to footer: `Refs DA-1000` (or `Closes DA-1000` if it resolves the ticket)

**When to use `Closes` vs `Refs`:**
- Use `Closes` if this commit **resolves/fixes** the ticket
- Use `Refs` if this is related but doesn't complete the ticket
- GitHub auto-closes issues on merge with `Closes` keyword

## Commit Message Format & Requirements

### Structure

```
<gitmoji> <type>(<scope>): <description>

[optional body: explanation of what and why]

[optional footer: Refs DA-XXXX, BREAKING CHANGE: ...]
```

### Subject Line Requirements

**Character Limits:**
- **Target**: ≤72 characters (including gitmoji and space)
- **Maximum**: 120 characters (for emergency cases)
- **Measure everything**: gitmoji (1 char) + space (1 char) + type + scope + description

**Example with character count:**
```
✨ feat(auth): add multi-factor authentication support
```
This is 50 characters ✅

**Formatting rules:**
- **Imperative mood** (command form, present tense):
  - ✅ `Add feature X` (not "Added feature X")
  - ✅ `Fix bug in parser` (not "Fixes bug in parser")
  - ✅ `Update documentation` (not "Updates documentation")
- **Lowercase** (except proper nouns and acronyms)
- **No period** at end of line
- **Specific and descriptive** (what changed, not just "update file")

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

**Best practice:** Choose the MOST IMPACTFUL type when multiple apply. For example, if commit adds a feature AND fixes a bug in the same file, prioritize `feat`.

### Scope Selection Rules

Scope indicates the affected module/area:
- **Use single word or hyphenated scope** when possible
- **Length**: 15 characters max
- **Examples**: `auth`, `db-pool`, `api-gateway`, `user-service`, `onboarding`
- **Optional but recommended** — improves readability
- **Skip scope only if:**
  - Changes affect multiple unrelated modules (use generic: `core`, `infra`)
  - Commit is generic documentation or build configuration

**Bad scope examples (too broad):**
- ❌ `feat(app):` — too generic
- ❌ `feat(code):` — meaningless
- ❌ `feat(multiple-services-and-utilities):` — too long

### Body Content Rules

Include ONLY if changes need explanation:
- Explain the **WHAT** and **WHY**, not the **HOW** (diff shows HOW)
- Keep to **2-4 short lines** maximum
- **Blank line required** between subject and body
- Omit entirely if changes are self-explanatory
- Use **bullet points** for multiple related changes

**Example:**
```
✨ feat(onboarding): add updated_at timestamp column

- Add updated_at column with server default CURRENT_TIMESTAMP
- Modernize type hints to Python 3.10+ union syntax
- Reorganize imports for better readability
```

### Footer Content Rules

Add footer information ONLY when applicable:
- **`Refs DA-XXXX`** — Link to related ticket (no auto-close)
- **`Closes DA-1234`** — Resolves ticket (GitHub auto-closes on merge)
- **`BREAKING CHANGE: description`** — Mark breaking changes prominently
- Separate multiple footer lines with line breaks

## Common Pitfalls & How to Avoid Them

| ❌ Pitfall | ✅ Solution | Example |
|-----------|-----------|---------|
| **Using "add" for MODIFIED files** | Only use "add" for NEW files; use "fix"/"refactor" for modifications | Diff shows `--- a/ +++ b/`, so use `fix(module):` not `add(module):` |
| **Generic or vague descriptions** | Be specific about what changed | `fix(parser): resolve stack overflow in recursive descent` not `fix parser bug` |
| **Past tense or non-imperative** | Always use imperative mood (command form) | `Refactor authentication handler` not `Refactored authentication handler` |
| **Subject line too long** | Count characters; trim to ≤72 | Trim verbose descriptions; move details to body |
| **Scope too broad** | Use single module; skip if affects multiple | Use `auth` not `app`; skip scope for config files |
| **Mixing unrelated changes** | Suggest splitting into separate commits | If changing module A and B unrelated things, ask to `git reset --soft HEAD~1` and stage separately |
| **Missing context in body** | Explain WHY the change, not HOW | Instead of "added validation", explain "validation prevents null pointer exception when X occurs" |
| **No ticket reference** | Extract from branch name or ask user | Branch `feat/DA-1000-auth` → add `Closes DA-1000` |
| **Forgetting to stage changes** | Always run `git status` and `git diff --staged` first | If nothing staged: suggest `git add .` or `git add -p` |
| **Breaking changes not marked** | Always mark with `BREAKING CHANGE:` footer | If changing API, database schema, or removing functions, mark prominently |

---

## Real-World Examples

These examples demonstrate various commit patterns. Use as reference when generating messages.
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

## Step-by-Step Execution Checklist

**Before generating any message, verify:**

1. ✅ Run `git status` — confirm staged changes exist
2. ✅ Run `git diff --staged` — examine full diff
3. ✅ Identify file types (NEW vs MODIFIED vs DELETED)
4. ✅ Identify primary vs secondary changes
5. ✅ Extract ticket ID (if available in branch name)
6. ✅ Select appropriate type and gitmoji
7. ✅ Write subject line (imperative mood, ≤72 chars)
8. ✅ Add body (if needed; explain WHY)
9. ✅ Add footer (ticket reference, breaking changes)
10. ✅ Validate: Read entire message; confirm it matches the diff

**Result:** Self-contained commit message that documents the change clearly.

## Troubleshooting & Edge Cases

### Problem: "Nothing to commit"

**Cause:** No changes are staged

**Solution:**
```bash
git add .              # Stage all changes
# OR
git add -p             # Stage selectively (recommended)
git diff --staged      # Verify staging
```

### Problem: "Merge conflicts in staging area"

**Cause:** Repository has unresolved conflicts

**Solution:**
```bash
# View conflicts
git status

# Resolve conflicts in your editor, then:
git add <resolved-files>
git diff --staged      # Verify
```

### Problem: "Message seems incomplete or too generic"

**Cause:** Insufficient detail or vague language

**Solution:**
- Answer: "What specifically changed?" (be concrete)
- Answer: "Why was this change needed?" (add to body)
- Answer: "What is the business impact?" (add context if relevant)

### Problem: "Subject line exceeds 72 characters"

**Cause:** Too much detail in subject

**Solution:**
- Move details to body using bullet points
- Simplify description (use present perfect: "add" not "add support for")
- Split into multiple commits if changes are unrelated

### Problem: "Staged changes are very large/unrelated"

**Cause:** Multiple different changes staged together

**Solution:**
```bash
# Unstage everything
git reset

# Stage selectively
git add -p

# This enables separate commits for each logical change
```

### Problem: "Need to edit commit after creation"

**Use git amend to modify last commit:**
```bash
# Make changes to files
git add <files>

# Amend (replaces last commit, don't push yet!)
git commit --amend

# To undo last commit (keep changes in working dir):
git reset --soft HEAD~1
```

### Best Practice: Multiple Commits

When staged changes span **unrelated areas**, suggest splitting:
- Commit 1: Changes to module A (specific type)
- Commit 2: Changes to module B (different type)
- Commit 3: Documentation updates

**Why:** Cleaner history, easier debugging, better granular rollbacks.

## Pre-Submission Quality Checklist

**Subject Line Validation:**
- [ ] Uses gitmoji (✨, 🐛, 🚀, etc.)
- [ ] Type is lowercase and correct (feat, fix, refactor, etc.)
- [ ] Scope (if used) is lowercase, single word or hyphenated
- [ ] Uses imperative mood (Add, Fix, Refactor — not Added, Fixes, Refactoring)
- [ ] Description is specific and actionable
- [ ] No period or punctuation at end
- [ ] Total length ≤72 characters (re-count to verify)

**File Type Validation:**
- [ ] NEW FILES use "add" verb (`feat:` or `chore: add`)
- [ ] MODIFIED FILES use appropriate verb (`fix:`, `refactor:`, `perf:`, etc.)
- [ ] DELETED FILES use "remove" verb (typically `chore:` with 🗑️)

**Body Validation (if included):**
- [ ] Blank line after subject
- [ ] Explains WHAT and WHY (not HOW)
- [ ] 2-4 lines maximum
- [ ] Uses bullet points for multiple changes
- [ ] Each bullet is concise and specific

**Footer Validation (if included):**
- [ ] Ticket reference format: `Refs DA-XXXX` or `Closes DA-XXXX`
- [ ] Breaking changes marked prominently: `BREAKING CHANGE: description`
- [ ] Multiple footer items separated by line breaks

**Source Truth Validation:**
- [ ] Message reflects ONLY staged changes (from `git diff --staged`)
- [ ] Message does NOT assume from chat history or branch name
- [ ] Message is self-contained (makes sense without context)
- [ ] Message matches actual file types (NEW/MODIFIED/DELETED)

---

## Critical Principles: Never Assume

**🔴 DO NOT:**

1. **Assume change type from chat history**
   - Always run `git diff --staged` to verify
   - What user said they're doing ≠ what the diff shows
   - Example: User says "refactoring" but diff shows NEW files → use `feat`, not `refactor`

2. **Reference business context or domain knowledge**
   - Commit message must make sense from diff alone
   - Don't assume: "Obviously this is for the Q4 feature"
   - Keep messages technical, not business-focused

3. **Add context from branch name alone**
   - Extract ticket ID (DA-XXXX) from branch, yes
   - But verify with diff what actually changed
   - Example: Branch `fix/DA-1000-auth-bug` with diff showing new feature → use `feat`, add `Refs DA-1000`

4. **Commit before user verifies**
   - Always present the message for review
   - User catches mistakes better than AI
   - Ask: "Does this accurately describe your changes?"

5. **Use past tense or non-imperative mood**
   - ✅ "Add caching layer" (present tense, command form)
   - ❌ "Added caching layer" (past tense)
   - ❌ "Adding caching layer" (progressive)

**✅ DO INSTEAD:**

- Analyze `git diff --staged` as source of truth
- Let the diff guide type selection
- Ask user for ticket ID if not in branch name
- Present message; wait for confirmation
- Validate message against actual changes

---

## Quick Reference: Git Commands

**Stage changes:**
```bash
git add .              # Stage all changes
git add -p             # Stage selectively (recommended for focused commits)
git add <file>         # Stage specific file
```

**Verify staging:**
```bash
git status             # Show staged and unstaged changes
git diff --staged      # Show detailed diff of staged changes only
```

**Create commit:**
```bash
git commit -m "✨ feat(scope): description"

# Multi-line commit (opens editor):
git commit
```

**View history:**
```bash
git log --oneline -10              # View last 10 commits
git log --graph --oneline --all    # View branch structure
```

**Fix mistakes:**
```bash
# Amend last commit (before pushing):
git commit --amend

# Unstage changes (keep them in working directory):
git reset --soft HEAD~1

# Discard changes completely:
git reset --hard <commit>
```

## References & Standards

**Conventional Commits:**
- [conventionalcommits.org](https://www.conventionalcommits.org/) — official specification
- Format: `type(scope): description` with optional body and footer

**Gitmoji:**
- [gitmoji.dev](https://gitmoji.dev/) — comprehensive emoji reference
- Visual Git history with semantic meaning

**Project Standards:**
- See `~/.copilot/instructions/generate-commit-message.instructions.md` for authoritative guidelines
- See [commit-message-reference.prompt.md](../../prompts/commit-message-reference.prompt.md) for quick AI reference material
