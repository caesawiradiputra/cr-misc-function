---
name: commit
description: Generate Conventional Commit + gitmoji message from staged changes, review, refine, and commit
---

# Commit

Generate a well-structured commit message using **Conventional Commits** format with **gitmoji** annotations, review with the user, and commit.

## When to Use

- Staged changes are ready to be committed
- You need a structured commit message following project conventions
- You want to amend the HEAD commit message

## Argument Routing

| Arguments | Behavior |
| --- | --- |
| *(empty)* | Full flow: analyze → generate → review → commit |
| `amend` | Refine the message of `HEAD`, jump to Phase 4, finish with `git commit --amend` |
| anything else | Treat as upfront guidance for generation |

## Workflow

### Phase 1: Analysis

1. **Validate repository state** — `git status`
   - Staged changes exist → proceed
   - Nothing staged → suggest `git add .` or `git add -p`
   - Merge conflicts → ask user to resolve first

2. **Analyze staged diff** — `git diff --staged`
   - `new file mode` → NEW FILE
   - `--- a/ +++ b/` → MODIFIED
   - `deleted file mode` → DELETED

3. **Extract ticket ID** — `git branch --show-current`
   - Pattern: `feat/DA-1000-description` → extract `DA-1000`

### Phase 2: Categorize Changes

**PRIMARY** (drives commit title): New routes, logic changes, config changes, model/schema changes, bug fixes, security fixes, performance improvements.

**SECONDARY** (goes in body): Docstrings, type hints, import reorganization, code style, restructuring, logging, dead code removal.

**Decision rule**: If PRIMARY changes exist → type is based on PRIMARY. Even if 80% of diff is type hints, if 20% adds a new route → use `feat`.

### Phase 3: Generate Message

1. **Select type and gitmoji**:
   - `feat ✨` — new functionality
   - `fix 🐛` — bug fix
   - `perf 🚀` — performance
   - `refactor ♻️` — restructuring
   - `docs 📝` — documentation
   - `test 🧪` — tests
   - `chore 🔧` — maintenance
   - `style 🎨` — formatting

2. **Select scope** — single word, lowercase, ≤15 chars (e.g., `auth`, `api`, `db-pool`)

3. **Write subject line**: `<gitmoji> <type>(<scope>): <description>`
   - Imperative mood, lowercase (except proper nouns), no period, ≤72 chars

4. **Write body** (optional): WHAT and WHY, 2-4 bullet points max

5. **Write footer**: `Refs {TICKET-PREFIX}-XXXX`, `Closes {TICKET-PREFIX}-XXXX`, `BREAKING CHANGE: description`

### Phase 4: Review & Refine

Present the message and ask:

```text
1. Commit — create the commit with this message
2. Refine — tell me what to change and I'll iterate
3. Split — divide staged changes into multiple commits
4. Cancel — do nothing
```

### Phase 5: Execute Commit

**Never pass the message inline with `-m`** (gitmoji gets mangled by console encoding):

1. Write full message to `.git\COMMIT_MSG_QODER.txt` using UTF-8
2. `git commit -F .git\COMMIT_MSG_QODER.txt`
3. `git log --oneline -1`
4. `Remove-Item ".git\COMMIT_MSG_QODER.txt"`

## Type & Gitmoji Reference

| Gitmoji | Type | When to Use |
| --- | --- | --- |
| ✨ | `feat` | New feature, endpoint, capability |
| 🐛 | `fix` | Bug fix, logic error, crash |
| 🚀 | `perf` | Performance improvement |
| ♻️ | `refactor` | Code restructuring, no behavior change |
| 📝 | `docs` | Documentation, docstrings |
| 🧪 | `test` | Test additions, updates |
| 📦 | `build` | Dependencies, packaging |
| 🔧 | `ci` | CI/CD configuration |
| 🎨 | `style` | Code formatting |
| 🔒 | `security` | Security fix |
| 🗑️ | `chore` | Remove dead code |
| 🏗️ | `arch` | Major architecture change |

## Examples

```text
✨ feat(auth): add two-factor authentication support

Refs {{TICKET_PREFIX}}-1234
```

```text
🐛 fix(parser): resolve null reference in token validation

- Add null checks before accessing token properties
- Handle edge case when token is expired

Closes {{TICKET_PREFIX}}-5678
```

## Validation

- Never base type on line count
- Always verify with `git diff --staged`
- Always present for user review before committing
- Subject ≤72 chars, imperative mood, no period
- Secondary changes go in body
- Ticket footer when branch carries a ticket ID
- Never commit with inline `-m`
