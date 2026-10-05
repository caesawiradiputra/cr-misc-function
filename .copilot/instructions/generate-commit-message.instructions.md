---
description: 'Instructions for GitHub Copilot to generate Conventional Commits with gitmoji from staged Git changes'
applyTo: '**'
---

# Generate Commit Message Instructions

## Trigger
User prompts **"generate commit message"** or **"commit message"**

## Workflow
When triggered, the agent will:
1. Run `git status` to check repository state
2. Analyze staged changes using `git diff --staged`
3. Distinguish between NEW, MODIFIED, and DELETED files
4. **Identify PRIMARY changes (logic/features) vs SECONDARY changes (refactoring/style)**
   - Primary: Schema changes, new functionality, behavior changes, database alterations
   - Secondary: Type hint updates, import reorganization, code formatting, stylistic improvements
5. Generate a **Conventional Commit message** with gitmoji for the staged changes, prioritizing primary changes

**File Type Analysis:**
- **NEW FILES** (marked `new file mode 100644` in diff): Use "add" verb in commit
  - Example: "add configuration files" not "fix" or "update"
- **MODIFIED FILES** (marked with `---/+++` and hunks): Use appropriate verb
  - Use "fix" for bug fixes, "refactor" for restructuring, "update" for changes
  - Example: "fix Python version compatibility" not "add Python version"
- **DELETED FILES** (marked `deleted file mode`): Use "remove" verb
  - Example: "remove deprecated configuration"

**Priority of Changes:**
When analyzing staged changes, identify the most impactful changes:
1. **Logic/Feature Changes** - Schema, functionality, behavior: These should drive the commit title
   - Schema changes: Adding/modifying database columns
   - New functionality: Features, capabilities, business logic
   - Behavior changes: Logic modifications that affect output/behavior
   - Database alterations: Any changes to data structure
2. **Refactoring/Style Changes** - Type hints, imports, formatting: Include as supporting details
   - Type hint modernization: Converting to newer Python syntax
   - Import reorganization: Reordering imports for clarity
   - Code style: Formatting, linting, style-only changes
   - Code refactoring: Code restructuring without behavior change

**Title Strategy:**
The commit title summarizes what changed. If logic changes exist, focus on them. Otherwise focus on the refactoring type.

**Example:**
If commit adds `updated_at` column AND updates type hints:
- Title: `feat(onboarding): add updated_at timestamp column` (focuses on logic change)
- Bullet details:
  - Add updated_at column with server default CURRENT_TIMESTAMP
  - Modernize type hints to Python 3.10+ union syntax
  - Reorganize imports for better readability

**Behavior:**
- If staged changes exist: generate commit message from the diff
- If nothing is staged: inform user and suggest `git add` or `git add -p` workflow
- Prefer a single, well-scoped commit; suggest splitting if changes are diverse
- Always verify the proposed message matches the actual change type (NEW vs MODIFIED)
- Do NOT use past tense or assume what changed without reading the diff

## Conventional Commits Format

### Structure
```
<gitmoji> <type>(<scope>): <description>

[optional body: explanation of what and why]

[optional footer: Refs DA-XXXX, BREAKING CHANGE: ...]
```

### Subject Line Requirements

#### Conventional Commits
Follow the Conventional Commits format for clear, structured commit history.

#### Character Limits
Limit the subject line to **72 characters or less** (including gitmoji and space). This ensures:
- Readability in Git logs and terminal displays
- Proper display in GitHub/GitLab UIs
- Email compatibility

#### Formatting and Styling
Use **gitmoji** for each commit to add visual context and semantic meaning.

Format: `<gitmoji> <type>(<scope>): <description>`

**Common gitmoji and mappings:**
- ✨ (`:sparkles:`) - New feature or capability
- 🐛 (`:bug:`) - Bug fix or issue resolution
- 📝 (`:memo:`) - Documentation, comments, or docstrings
- ♻️ (`:recycle:`) - Code refactoring (no behavior change)
- 🚀 (`:rocket:`) - Performance improvement
- 🧪 (`:test_tube:`) - Test additions or updates
- 📦 (`:package:`) - Build system, dependencies, or packaging
- 🔧 (`:wrench:`) - Configuration, build scripts, or tooling
- 🎨 (`:art:`) - Code formatting or style (no logic change)
- 🔒 (`:lock:`) - Security fix or hardening
- 🗑️ (`:wastebasket:`) - Remove code, files, or dead code
- 🏗️ (`:building_construction:`) - Architecture or major refactor
- ⏮️ (`:back:`) - Revert a previous commit

#### Imperative Mood
Use imperative mood (command form, present tense) for the subject line:
- ✅ `Add feature X` not `Added feature X`
- ✅ `Fix bug in parser` not `Fixes bug in parser`
- ✅ `Update documentation` not `Updates documentation`
- ✅ `Refactor authentication module` not `Refactored authentication module`

### Body (Optional)
Include a body if changes need explanation:
- Explain the **what** and **why**, not the **how**
- Keep to 2-4 short lines
- Omit if changes are self-explanatory or obvious from the diff
- Start with a blank line after the subject

### Footer (Optional)
Add footer information when applicable:
- **References**: `Refs DA-XXXX` (link to related ticket/issue)
- **Closes**: `Closes DA-1234` (if this commit resolves a ticket)
- **Breaking Changes**: `BREAKING CHANGE: <description>` (if this introduces breaking changes)

## Commit Types

| Type | Usage | Gitmoji |
| ------ | ------- | --------- |
| `feat` | New feature or capability | ✨ |
| `fix` | Bug fix or issue resolution | 🐛 |
| `perf` | Performance improvement | 🚀 |
| `refactor` | Code restructuring (no behavior change) | ♻️ |
| `docs` | Documentation, comments, or docstrings | 📝 |
| `test` | Test additions, updates, or fixes | 🧪 |
| `build` | Build system, dependencies, or packaging | 📦 |
| `ci` | CI/CD configuration or scripts | 🔧 |
| `chore` | Developer experience, config, tooling | 🔧 |
| `style` | Code formatting or style (no logic change) | 🎨 |
| `security` | Security fix or hardening | 🔒 |
| `remove` | Remove code, files, or dead code | 🗑️ |
| `arch` | Architecture or major refactor | 🏗️ |
| `revert` | Revert a previous commit | ⏮️ |

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

## Guidelines

### Character Count Verification
- Subject must be ≤72 characters total
- Count the gitmoji (1 char) + space (1 char) + type + scope + description
- Example: `✨ feat(module): add new feature` = 32 chars ✅

### Scope Selection
- Use single word or hyphenated scope when possible
- Scope should indicate the affected module/area
- Examples: `auth`, `db-pool`, `api-gateway`, `user-service`

### Body Guidelines
- Provide context only when changes require explanation
- Omit body for obvious or self-explanatory changes
- Avoid repeating information from the subject line
- Use bullet points for multiple related changes

### Footer Guidelines
- Always include reference if ticket number exists
- Use `Closes` for tickets that should be auto-closed
- Use `Refs` for related tickets that shouldn't auto-close
- Mark breaking changes prominently

## Quality Checklist

Before finalizing, ensure:
- [ ] Subject line uses gitmoji and imperative mood
- [ ] Subject line is ≤72 characters
- [ ] Type and scope are lowercase
- [ ] Body (if included) explains WHY, not WHAT
- [ ] Footer includes ticket reference if applicable
- [ ] Breaking change is clearly marked if applicable
- [ ] Message is specific to the staged changes
- [ ] No generic or template language used

## Important: NEW vs MODIFIED Files

**Always check the git diff output format:**

```
# NEW FILE - Use "add" verb
new file mode 100644
index 0000000..530941f
--- /dev/null
+++ b/file.toml
@@ -0,0 +1,80 @@

# MODIFIED FILE - Use appropriate verb (fix/refactor/update)
--- a/existing_file.toml
+++ b/existing_file.toml
@@ -1,5 +1,10 @@

# DELETED FILE - Use "remove" verb
deleted file mode 100644
index 530941f..0000000
```

## Notes

- **ALWAYS** run `git diff --staged` to verify file types (NEW vs MODIFIED)
- **ALWAYS** check for `new file mode` in the diff output
- Do NOT assume change type from chat history or previous commits
- **ALWAYS** identify logic/feature changes vs refactoring/style changes
- If logic changes exist, make them the focus of the title; otherwise focus on the refactoring type
- Include all related changes as bullet points in the body, not labeled as primary/secondary
- If staged changes span multiple unrelated areas, suggest splitting into multiple commits
- Do not generate commit messages for unstaged changes
- Validate the message matches the actual change type (NEW/MODIFIED/DELETED) before presenting
- Use "add" only for NEW files, not for modifications to existing files
