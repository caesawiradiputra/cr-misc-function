---
description: "GitHub Copilot instructions for [PROJECT_NAME] - integrates awesome-copilot with project-specific conventions"
templateFor: "All projects - copy and customize this file"
---

# GitHub Copilot Instructions for [PROJECT_NAME]

**This is a template file.** Copy it to `[newProject]/.github/copilot-instructions.md` and customize the PROJECT CONTEXT section for your specific project.

**When to update this file:**
- Periodically, as your project evolves (language upgrades, new frameworks, architectural changes)
- Use the "update-copilot-instructions" skill to guide updates by project type
- Keep ENTRY POINT INFORMATION section immutable (it's shared architecture)

---

## ⚠️ ENTRY POINT INFORMATION (Immutable)

**Do not modify this section.** This defines how Copilot discovers instructions.

### Purpose

Entry point for GitHub Copilot in this workspace. Defines how Copilot finds and uses instructions across the precedence chain.

> **Reference**: See `~/.copilot/instructions/master-control.instructions.md` for the authoritative fallback chain (one copy, globally shared across all projects)

### Precedence Chain (Where Copilot Looks)

When Copilot needs an instruction, it searches in this order:

1. **This Workspace** (highest priority) - `[projectWorkspace]/.github/`
   - Project-specific instructions
   - Project-specific configurations
   - Project-specific customizations

2. **Global Context** (fallback) - `~/.copilot/`
   - Reusable instructions shared across projects
   - Common workflows and prompts
   - Shared references and definitions

3. **Awesome-Copilot** (authoritative) - https://github.com/github/awesome-copilot/
   - Best practices and standards
   - Language-specific guidance
   - Official references

### How Copilot Uses This File

1. **On Initialization**: Copilot loads this file when you start working in this workspace
2. **For Discovery**: Uses the precedence chain to find instructions automatically
3. **For Context**: References awesome-copilot when project-specific guidance is insufficient
4. **For Auto-Apply**: Instructions with `applyTo` patterns trigger automatically on matching files

---

## ✏️ PROJECT CONTEXT (Customize for this workspace)

Edit this section to define your project's characteristics, type, and standards.

### Project Identity

**Project Name**: [PROJECT_NAME]

**Description**: [DESCRIBE PROJECT HERE]

**Project Type**: [API Service / Consumer App / Data Pipeline / Library / Other]

### Tech Stack

**Language**: [e.g., Python 3.9+]

**Framework**: [if applicable]

**Key Dependencies**: [if applicable]

### Project-Specific Patterns & Conventions

[Add any unique conventions for this project]

Example:
- Code style preferences beyond Ruff/Linting
- Testing patterns specific to this project
- Database/data model conventions
- Deployment procedures
- Secrets/configuration management approach

---

## Awesome-Copilot References for This Project

Select references relevant to your project type. These are the authoritative sources for coding standards.

### Core Development Standards (All Projects)

**References**:
- [Code Generation Guidelines](https://github.com/github/awesome-copilot/blob/main/instructions/code-generation-guidelines.instructions.md)
- [Security Standards (OWASP Top 10 2025)](https://github.com/github/awesome-copilot/blob/main/instructions/security-standards.instructions.md)
- [AI Prompt Engineering & Safety Best Practices](https://github.com/github/awesome-copilot/blob/main/instructions/ai-prompt-engineering-safety-best-practices.instructions.md)

### Documentation & Communication (All Projects)

**References**:
- [Markdown Content Rules](https://github.com/github/awesome-copilot/blob/main/instructions/markdown-content-rules.instructions.md)
- [GitHub Flavored Markdown (GFM)](https://github.com/github/awesome-copilot/blob/main/instructions/github-flavored-markdown.instructions.md)

### Version Control & CI/CD (All Projects)

**References**:
- [GitHub Actions CI/CD Best Practices](https://github.com/github/awesome-copilot/blob/main/instructions/github-actions-ci-cd-best-practices.instructions.md)

### Language/Framework-Specific References

**For Python projects**:
- [Python Development](https://github.com/github/awesome-copilot/blob/main/instructions/python.instructions.md)
- [Python MCP Server Development](https://github.com/github/awesome-copilot/blob/main/instructions/python-mcp-server-development.instructions.md)

**For other languages/frameworks**: Add relevant awesome-copilot links here

### Development Environment

**For this machine (Windows PowerShell):**
- [windows-powershell-environment.instructions.md](C:/Users/203715/.copilot/instructions/windows-powershell-environment.instructions.md) — Terminal commands, path handling, and PowerShell syntax for Windows development

---

## Project-Specific Instructions & Files

This workspace contains project-specific instructions in `.github/instructions/`:

**[Add descriptions of any project-specific instruction files]**

Example structure:
```
.github/instructions/
├── [project-specific-instruction-1].md
├── [project-specific-instruction-2].md
└── [more as needed]
```

**Note**: Reusable instructions should be copied to `~/.copilot/` to benefit other projects.

---

## How to Update This File

**Use the "update-copilot-instructions" skill to guide your customization:**

The skill provides step-by-step workflows for each project type (API Service, Data Pipeline, Consumer App, Library). It will guide you through:

1. **Analyzing your project** - Understanding its purpose, type, and technologies
2. **Filling placeholders** - Project name, description, tech stack, patterns
3. **Selecting references** - Choosing relevant awesome-copilot resources for your project type
4. **Validating changes** - Ensuring completeness and correctness

**Manual alternative** (if not using skill):

1. **Update Project Context**: Modify the "Project Identity", "Tech Stack", and "Project-Specific Patterns" sections
   - Replace all `[PLACEHOLDER]` text with actual values
   - Add project-specific patterns and conventions

2. **Customize Awesome-Copilot References**: Update "Language/Framework-Specific References"
   - Select references matching your project's technology stack
   - Remove references that don't apply to your project type
   - Use the skill's workflow files for guidance on which references to include

3. **Document Project-Specific Instructions**: Describe files in `.github/instructions/` if any
   - Only document files that exist in your project
   - Describe when and how to use each instruction

4. **Update metadata**: Change the Last Updated date to today

**Important**: Do NOT modify the "Entry Point Information" section—it's shared across all projects and defines the architecture.

---

## Workflow: When to Copy to Global Context

Copy files from `.github/` to `~/.copilot/` when they're reusable across projects:

✅ **Copy to `~/.copilot/`**:
- Generic instruction files
- Reusable prompt templates
- Common workflows
- Shared utilities

❌ **Keep in `.github/`**:
- Project-specific instructions
- CDE data files (*.tsv)
- Project configurations
- Type-specific patterns (only for this project type)

---

## File Organization (This Workspace)

```
[projectWorkspace]/
├── .github/
│   ├── copilot-instructions.md        ← YOU ARE HERE (project entry point)
│   ├── instructions/                  ← Project-specific instruction files
│   ├── prompts/                       ← Project-specific prompt templates
│   ├── skills/                        ← Project-specific skill definitions
│   ├── agents/                        ← Project-specific agent workflows
│   └── references/                    ← Project-specific references
├── .vscode/
├── [project-code]/
│   ├── .git/
│   ├── .venv/
│   └── [source files]
└── [other workspace files]
```

---

## Last Updated

- **Date**: April 22, 2026
- **Status**: Template ready for project customization
- **Author**: GitHub Copilot

