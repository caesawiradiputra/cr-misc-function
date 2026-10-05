---
description: Generate Conventional Commit messages with gitmoji from staged Git changes (supports standard and release modes)
---

# Generate Commit Message from Staged Changes

**CRITICAL:** Always run `git status` and `git diff --staged` to analyze CURRENT staged changes. Do not assume previous context is still valid.

You are an expert at writing clear, descriptive commit messages following **Conventional Commits** standard with **gitmoji** annotations.

## Workflow

**For every commit message request:**
1. **Run** `git status` to verify repository state
2. **Run** `git diff --staged` to analyze current staged changes only
3. **Identify** file types (NEW, MODIFIED, DELETED)
4. **Prioritize** changes (logic/feature vs refactoring/style)
5. **Generate** commit message using Conventional Commits format

## Quick Reference: File Types & Verbs

```
NEW FILES (new file mode):        Use "add" verb (✨ feat)
MODIFIED FILES (--- a/ +++ b/):   Use appropriate verb (fix/refactor/perf/etc)
DELETED FILES (deleted mode):     Use "remove" verb (🗑️ chore)
```

## Commit Message Format

```
<gitmoji> <type>(<scope>): <description>

[optional body: explain what and why]

[optional footer: Refs DA-XXXX, BREAKING CHANGE: ...]
```

## Type Reference

| Type | Usage | Gitmoji | Type | Usage | Gitmoji |
|------|-------|---------|------|-------|---------|
| `feat` | New feature | ✨ | `fix` | Bug fix | 🐛 |
| `perf` | Performance | 🚀 | `refactor` | Restructuring | ♻️ |
| `docs` | Documentation | 📝 | `test` | Test changes | 🧪 |
| `build` | Dependencies | 📦 | `ci` | CI/CD config | 🔧 |
| `style` | Formatting | 🎨 | `security` | Security fix | 🔒 |
| `arch` | Major refactor | 🏗️ | `revert` | Revert commit | ⏮️ |

## Subject Line (Required)

- **Format**: `<gitmoji> <type>(<scope>): <description>`
- **Length**: ≤72 characters (including gitmoji)
- **Mood**: Imperative ("Add feature" not "Added feature")
- **Case**: Lowercase except proper nouns
- **Punctuation**: No period at end
- **Scope**: Single word or hyphenated (e.g., `auth`, `db-pool`)

## Body (Optional)

Include ONLY if changes need context:
- Explain **WHAT** and **WHY**, not HOW
- Keep to 2-4 lines maximum
- Use bullet points for multiple changes
- Blank line between subject and body
- Omit for obvious/self-explanatory changes

## Footer (Optional)

Add when applicable:
- **References**: `Refs DA-XXXX` (related ticket, no auto-close)
- **Closes**: `Closes DA-1234` (resolves ticket, auto-closes it)
- **Breaking**: `BREAKING CHANGE: description` (if applicable)

## Change Prioritization

When analyzing diff, identify:

**Primary Changes** (drive the commit title):
- Schema changes, new columns
- New functionality or features
- Behavior/logic changes
- Database alterations

**Secondary Changes** (included as bullet points):
- Type hint updates, import reorganization
- Code formatting, linting
- Code restructuring without behavior change

**Example**: Adding `updated_at` column + updating type hints:
```
✨ feat(onboarding): add updated_at timestamp column

- Add updated_at column with CURRENT_TIMESTAMP default
- Modernize type hints to Python 3.10+ union syntax
- Reorganize imports for better readability

Closes DA-1505
```

## Examples

### Simple Feature
```
✨ feat(api): add webhook retry mechanism

Refs DA-1234
```

### Bug Fix with Context
```
🐛 fix(auth): resolve null reference in token validation

- Add null checks before token access
- Handle expired token edge case
- Add unit tests for both scenarios

Closes DA-5678
```

### Performance Improvement
```
🚀 perf(database): optimize user lookup queries

- Add composite index on user_id and created_at
- Reduce query execution from 2s to 200ms

Refs DA-2345
```

### Refactoring
```
♻️ refactor(api): consolidate duplicate request handlers

Extract common logic into base handler to reduce duplication.
```

### Breaking Change
```
🏗️ arch(db): redesign connection pool configuration

BREAKING CHANGE: connection_config dict replaced with DBConfig dataclass; migrate before upgrading

Refs DA-6789
```

## Release Mode (Optional)

For release commits, create organized folder:

```
release/YYYY-MM-DD_JIRA-ID/
├── README.md (summary, breaking changes, migration steps)
├── ddl/
│   ├── database_schema_changes.sql
│   └── data_migrations.sql
├── config/
│   ├── environment_variables.md
│   └── configuration_changes.md
└── docs/
    ├── IMPLEMENTATION_NOTES.md
    ├── API_CHANGES.md (if applicable)
    └── BREAKING_CHANGES.md (if applicable)
```

## Git Repository Structure

This workspace uses nested git folders:
- Workspace root: `c:\Users\203715\Documents\Repo\cr-misc-function\`
- Git repo: `c:\Users\203715\Documents\Repo\cr-misc-function\cr-misc-function\`

Run git commands from the child folder (same name as parent).

## Quality Checklist

Before submitting:
- [ ] Subject uses gitmoji and imperative mood
- [ ] Subject is ≤72 characters
- [ ] Type and scope are lowercase
- [ ] Body (if used) explains WHY, not WHAT
- [ ] Footer includes ticket reference if applicable
- [ ] NEW FILES use "add" verb
- [ ] MODIFIED FILES use appropriate verb
- [ ] DELETED FILES use "remove" verb
- [ ] No generic language or assumptions from chat history

---

**Refer to `~/.copilot/instructions/generate-commit-message.instructions.md` for comprehensive reference and additional examples.**
