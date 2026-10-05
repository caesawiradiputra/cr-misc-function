---
name: create-readme
version: "1.0.0"
updated: "2026-06-18"
related_skills:
  - create-confluence-docs
description: Create or update a project's README.md following documentation standards. Use when the user triggers /create-readme, asks to create a README, or wants to update project documentation.
---

# Create README

Create or update the project's `README.md` following project documentation standards.

## Before Starting

1. **Check if README.md exists** in the project root:
   - If exists -> review and update (preserve relevant sections, add new ones)
   - If not -> create from scratch

2. **Analyze project structure**: read `pyproject.toml`, scan Python files, understand the project.

## Organization Rules

### Single Source of Truth
- The **only** README.md lives in the **project root**
- Never create README.md files in subdirectories
- Move all other `.md` files to `docs/` folder structure

### docs/ Folder Structure
```text
docs/
+-- guides/       - Usage guides and tutorials
+-- architecture/ - Architecture and design docs
+-- changelog/    - Release notes and version history
+-- examples/     - Code examples and demonstrations
+-- api/          - API reference (if applicable)
```

## README Content Structure

Include these sections in order:

1. **Title and Description** — Clear project name + one-sentence description
2. **Features** — Key capabilities as bullet list (3-7 items)
3. **Quick Start** — Installation and basic usage with code examples
4. **Requirements** — System requirements and dependencies
5. **Installation** — Detailed steps (if needed beyond quick start)
6. **Usage** — Usage examples and common scenarios
7. **Configuration** — Options and environment variables (if applicable)
8. **Architecture** — High-level overview (link to `docs/architecture/`)
9. **Contributing** — Link to `CONTRIBUTING.md` if it exists
10. **Further Reading** — Links to `docs/` folder
11. **License** — License info with link to `LICENSE` file

## Markdown Standards

> See [_shared/markdown-standards.md](../_shared/markdown-standards.md) for common markdown formatting rules. Below are README-specific additions.

- **Single H1 title** per file (the project name)
- **Forward slashes** for relative paths in links
- **Line length**: under 120 characters

## Quality Checklist

- [ ] Only one README.md exists (in root directory)
- [ ] All code blocks have language identifiers
- [ ] Blank lines surround code blocks, lists, and headings
- [ ] Headings follow hierarchy (no skipped levels)
- [ ] All links are valid and use forward slashes
- [ ] Lines are under 120 characters
- [ ] Tables properly aligned with header separators
- [ ] Documentation links point to `docs/` subfolder
- [ ] Content is current and accurate for project state
- [ ] Passes markdown linting (no formatting errors)
