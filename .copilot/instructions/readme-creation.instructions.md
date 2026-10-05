---
description: 'Guidelines for creating and maintaining README.md files'
applyTo: '**/README.md'
---

# README.md Creation Instructions

## Overview

This document provides guidelines for creating and maintaining README.md files in the project. The README is the primary entry point for users and contributors, so it must be clear, accurate, and well-organized.

---

## README.md Organization Rules

**Important:** Apply these organizational rules when creating or updating README files:

### 1. Single Source of Truth

- The main and **only** README.md file must be in the **root path** of the project
- This is the primary entry point for all users and contributors
- Never create additional README.md files in subdirectories

### 2. Check Before Creating

- Before creating a new README.md, check if one already exists in the root directory
- If it exists, review the current project structure and content
- Update the existing README.md only if the project has changed significantly
- Preserve existing sections that remain relevant; add new sections for new features
- Do not delete or remove information unnecessarily

### 3. Documentation Organization

- Move and organize all other `.md` files to the `docs/` folder structure:
  - `docs/guides/` - Usage guides and tutorials
  - `docs/architecture/` - Architecture and design documentation
  - `docs/changelog/` - Release notes and version history
  - `docs/examples/` - Code examples and demonstrations
  - `docs/api/` - API reference documentation (if applicable)
- Keep the root directory clean with only essential files:
  - README.md (main documentation entry point)
  - LICENSE (license file)
  - pyproject.toml, package.json, etc. (project configuration)
  - Other essential configuration files

### 4. Cross-References

- In the root README.md, add a "Further Reading" or "Documentation" section
- Link to detailed docs in the `docs/` folder
- Example structure:

```markdown
## Further Reading

- [Architecture Guide](docs/architecture/README.md) - Detailed system design and patterns
- [Usage Guide](docs/guides/README.md) - Comprehensive usage instructions
- [Examples](docs/examples/README.md) - Code examples and demonstrations
- [Changelog](docs/changelog/CHANGELOG.md) - Version history and release notes
```

---

## Markdown Lint Best Practices

Follow these markdown formatting standards for consistent, lintable output:

### 1. Fenced Code Blocks

- Always specify the language for syntax highlighting
- Examples: ` ```python`, ` ```javascript`, ` ```bash`, ` ```sql`, ` ```json`, ` ```yaml`
- Use backticks (` ``` `) for fenced code blocks, not indentation
- Never use bare ` ``` ` without a language identifier unless content is truly language-agnostic

### 2. Blank Lines Around Blocks

- Add blank lines before and after code blocks, lists, blockquotes, and headings
- Example structure:

```markdown
Some text here.

```python
code_block()
```

Continue with more text.
```

### 3. List Formatting

- Use consistent list markers (`-` for unordered, `1.` for ordered)
- Add blank line before first list item and after last list item when lists follow text
- Indent nested lists with 2 or 4 spaces consistently
- Avoid mixing ordered and unordered lists without clear nesting

### 4. Heading Hierarchy

- Use `#` for H1 (main title), `##` for H2, `###` for H3, etc.
- Do not skip heading levels (no H1 directly to H3)
- Add blank line before and after headings
- Use sentence case for heading text unless it's a proper noun

### 5. Links and References

- Use inline links `[text](url)` for better readability
- Ensure all relative links use forward slashes `/`, even on Windows
- Validate that all local file references actually exist in the repository
- Use descriptive link text that indicates the content destination

### 6. Line Length

- Keep lines under 120 characters for better readability
- Break long paragraphs or lists into multiple lines when reasonable
- This improves both GitHub rendering and terminal display

### 7. Special Characters

- Escape special characters where necessary: `\*`, `\_`, `\[`, etc.
- Use proper Unicode characters instead of HTML entities where possible
- Example: Use `→` instead of `&rarr;`, use `•` instead of `&#8226;`

### 8. Tables

- Use consistent pipe `|` alignment
- Ensure header row has separator row with dashes: `| --- |`
- Add blank lines before and after tables
- Example:

```markdown
| Feature | Status | Description |
| --- | --- | --- |
| Feature A | ✅ | Fully implemented |
| Feature B | 🔄 | In progress | 
```

---

## README Content Structure

When creating a README, follow this general structure:

1. **Title and Description** - Clear project name and one-sentence description
2. **Features** - Key features and capabilities (bullet list)
3. **Quick Start** - Installation and basic usage (code examples)
4. **Requirements** - System requirements and dependencies
5. **Installation** - Detailed installation instructions (if needed)
6. **Usage** - Usage examples and common scenarios
7. **Configuration** - Configuration options (if applicable)
8. **Architecture** - High-level overview (link to docs/architecture for details)
9. **Contributing** - Link to CONTRIBUTING.md if exists
10. **Further Reading** - Links to documentation in docs/ folder
11. **License** - License information with link to LICENSE file

---

## File Organization Workflow

When updating documentation:

1. **Audit existing MD files** in the root directory
2. **Create docs/ folder structure** if it doesn't exist:
   ```
   docs/
   ├── guides/
   ├── architecture/
   ├── changelog/
   ├── examples/
   └── api/
   ```
3. **Move supplementary MD files** to appropriate docs/ subfolder
4. **Update root README.md** with links to docs/ files
5. **Remove root-level MD files** (keep only README.md in root)

---

## Quality Checklist

Before finalizing a README.md, verify:

- [ ] Only one README.md exists in the root directory
- [ ] All code blocks have language identifiers
- [ ] Blank lines surround code blocks, lists, and headings
- [ ] Headings follow hierarchy (no skipped levels)
- [ ] All links are valid and use forward slashes
- [ ] Lines are under 120 characters (readability)
- [ ] Special characters are properly escaped or use Unicode
- [ ] Tables are properly aligned with header separators
- [ ] Documentation links point to docs/ subfolder files
- [ ] Markdown passes linting checks
- [ ] Content is current and accurate for the project state
