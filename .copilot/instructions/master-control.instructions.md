---
description: "Master control for GitHub Copilot context - fallback chain and precedence rules for awesome-copilot + project context"
applyTo: "**"
---

# Master Control: Awesome-Copilot + Project Context

**Version**: 1.0 (April 22, 2026)

This file serves as the **entry point** for all GitHub Copilot context decisions. It defines how Copilot should load instructions when switching between workspaces or when local context is insufficient.

---

## Precedence Chain (Load Order)

When Copilot needs an instruction, use this chain in order:

### 1. **Project Workspace Context** (highest priority)
- **Location**: `[projectWorkspace]/.github/copilot-instructions.md`
- **Why**: Contains this project's specific instructions and customizations
- **When**: Always check here first when working in this workspace
- **Includes**: `.github/instructions/`, `.github/prompts/`, `.github/skills/`, `.github/agents/`

### 2. **Global Awesome-Copilot** (fallback when workspace unavailable)
- **Location**: `~/.copilot/`
- **What to do**: Scan and use the global context folder
- **Why**: Reusable across all projects and workspaces
- **When**: If workspace context unavailable
- **How it gets there**: You manually copy reusable files from `[projectWorkspace]/.github/` to `~/.copilot/`

### 3. **GitHub Awesome-Copilot Repo** (authoritative when all else fails)
- **Location**: https://github.com/github/awesome-copilot/
- **Why**: Canonical reference for best practices
- **When**: Neither workspace nor global context have sufficient detail
- **Key references**:
  - [Python Development](https://github.com/github/awesome-copilot/blob/main/instructions/python.instructions.md)
  - [Markdown Content Rules](https://github.com/github/awesome-copilot/blob/main/instructions/markdown-content-rules.instructions.md)
  - [GitHub Flavored Markdown (GFM)](https://github.com/github/awesome-copilot/blob/main/instructions/github-flavored-markdown.instructions.md)
  - [Security Standards (OWASP Top 10 2025)](https://github.com/github/awesome-copilot/blob/main/instructions/security-standards.instructions.md)
  - [Code Generation Guidelines](https://github.com/github/awesome-copilot/blob/main/instructions/code-generation-guidelines.instructions.md)
  - [GitHub Actions CI/CD Best Practices](https://github.com/github/awesome-copilot/blob/main/instructions/github-actions-ci-cd-best-practices.instructions.md)

---

## How Copilot Uses This Chain

### Scenario A: Working in Your Project (Most Common)
```
User opens [projectWorkspace]/.github/
  ↓
Copilot loads [projectWorkspace]/.github/copilot-instructions.md
  ↓
Copilot searches in order:
  1. [projectWorkspace]/.github/ (found? use it)
  2. ~/.copilot/ (global context folder - found? use it)
  3. awesome-copilot GitHub (fallback if not found locally)
  ↓
Result: Use this project's instructions + reusable shared instructions + authoritative standards
  ✅ All instructions scoped to this project with automatic fallback
```

### Scenario B: Working in a Different Project (Another Workspace)
```
User opens [otherProjectWorkspace]/
  ↓
Copilot can't find context (different workspace)
  ↓
Copilot searches in order:
  1. [otherProjectWorkspace]/.github/ (found? use it)
  2. ~/.copilot/ (global context folder - use it)
  3. awesome-copilot GitHub (if needed)
  ↓
Result: Use shared instructions from ~/.copilot/ + awesome-copilot standards
  ✅ Reusable context available across all projects
```

### Scenario C: Fallback to Shared or Authoritative Sources
```
User in [projectWorkspace]/ asks for an instruction
  ↓
Copilot searches in order:
  1. [projectWorkspace]/.github/instructions/ (found? use it)
  2. ~/.copilot/instructions/ (found? use it)
  3. awesome-copilot GitHub URL (authoritative source)
  ↓
Result: Instruction found at some level of the chain
  ✅ Complete coverage: project-specific → shared reusable → authoritative
```

---

## File Organization

### Global Context (`.copilot/` - shared across all projects)
```
~/.copilot/
├── instructions/
│   ├── master-control.instructions.md     ← Precedence chain (ONE copy)
│   ├── [reusable instructions]
│   └── [more as needed]
├── prompts/                               ← Reusable prompt templates
├── skills/                                ← Reusable skill definitions
├── agents/                                ← Reusable agent workflows
└── references/                            ← Shared references
```

### Per-Project Workspace (`.github/` - specific to this project)
```
[projectWorkspace]/
├── .github/
│   ├── copilot-instructions.md            ← Entry point (manually copied)
│   ├── instructions/                      ← Project-specific files
│   │   ├── [your instructions]
│   │   └── [more as needed]
│   ├── prompts/                           ← Project-specific prompts
│   ├── skills/                            ← Project-specific skills
│   ├── agents/                            ← Project-specific agents
│   └── references/                        ← Project-specific references
├── .vscode/
├── [projectfolder]/
│   ├── .git/
│   ├── .venv/
│   ├── app/
│   └── [project files]
└── [other workspace files]
```

**Key principle**:
- `~/.copilot/` contains `master-control.instructions.md` (GLOBAL - one copy)
- Each project's `.github/` has `copilot-instructions.md` (manually maintained per project)
- Both files exist; they work together via precedence chain

---

## No Task-Specific Mapping

**Don't specify which file for which task.** Let Copilot discover instructions automatically via the precedence chain.

When Copilot needs an instruction:
1. Search `[projectWorkspace]/.github/` first
2. Search `~/.copilot/` next
3. Search awesome-copilot GitHub repo as fallback

**Result**: New instructions automatically available without updating any files.

---

## How to Implement: Step by Step

### Initial Setup (One-Time)

#### 1. Setup Global Context (Once, affects all projects)

**Copy this file to global context:**
- **File**: `master-control.instructions.md` (this file)
- **From**: `c:\Users\203715\Documents\Repo\cr-misc-function\.github\instructions\master-control.instructions.md`
- **To**: `~/.copilot/instructions/master-control.instructions.md`
- **Why**: Defines the precedence chain once, used by all projects
- **How often**: One-time only; update sparingly when precedence rules change

#### 2. Setup Per-Project Context (Per project)

**Each project gets its own copilot instructions:**
- **Template file**: `c:\Users\203715\Documents\Repo\cr-misc-function\cr-misc-function\.github\copilot-instructions.md`
- **Copy to**: `[newProject]/.github/copilot-instructions.md`
- **Then customize**: Fill in `[PROJECT_NAME]`, `[DESCRIBE PROJECT HERE]`, project type, tech stack, etc.
- **How often**: Manually maintained; update when project context changes
- **Use skill**: Run the "update-copilot-instructions" skill to guide the customization

**Template layout**:
- ⚠️ ENTRY POINT INFORMATION section (immutable—do NOT change)
- ✏️ PROJECT CONTEXT section (customize for your project)
  - Project Identity (name, description, type)
  - Tech Stack (language, frameworks, dependencies)
  - Project-Specific Patterns & Conventions
- Awesome-Copilot References (select relevant to your project type)
- Project-Specific Instructions & Files
- Metadata (Last Updated, Status)

#### 3. Setup Project-Specific Instructions (As needed)

**Create project-specific instructions in `.github/instructions/`:**
- Only store files unique to this project
- Example: `refactor-python-code.instructions.md`, `cde-definitions.instructions.md`, etc.
- Reusable files should be copied to `~/.copilot/instructions/` later

### When Ready to Share Instructions Across Projects

**Copy reusable files from `[projectWorkspace]/.github/` to `~/.copilot/`:**
- Reusable `instructions/*.md` → `~/.copilot/instructions/`
- Reusable `prompts/*.md` → `~/.copilot/prompts/`
- Reusable `skills/*/*.md` → `~/.copilot/skills/`
- Reusable `agents/*.md` → `~/.copilot/agents/`
- Reusable `references/*.md` → `~/.copilot/references/`
- **NOT `master-control.instructions.md`** (already there globally)

**Keep project-specific files in `[projectWorkspace]/.github/`:**
- Don't copy project-only instructions to global
- CDE data files (*.tsv, actual data) stay local
- Project configurations stay local

**Each project contributes to `~/.copilot/` independently:**
- Different projects may share different reusable instructions
- No conflict—Copilot searches both locations
- One global precedence chain handles the merging

---

## Copy Strategy (When Sharing Across Projects)

**Copy everything** from `[projectWorkspace]/.github/` to `~/.copilot/` **except project-specific data**:

```
✅ COPY TO GLOBAL (~/.copilot/)
- All instructions/*.md (reusable across projects)
- All prompts/*.md
- All skills/*/*.md
- All agents/*.md
- All references/*.md

❌ STAY IN WORKSPACE (.github/)
- Project-specific CDE data files (*.tsv, actual data)
- Project-specific configurations
```

**Reason**: Instructions are generic; data is project-specific.

---

## Automatic Discovery (Copilot Search Order)

**For ANY instruction in this project, Copilot searches in order:**

1. `[projectWorkspace]/.github/instructions/` (this project)
2. `~/.copilot/instructions/` (shared across all projects)
3. `https://github.com/github/awesome-copilot/` (authoritative source)

**Same for prompts, skills, agents, references:**

1. `[projectWorkspace]/.github/{prompts,skills,agents,references}/`
2. `~/.copilot/{prompts,skills,agents,references}/`

**No manual mapping needed.** Add new files anywhere and they're automatically discovered.

**Cross-project**: When you add instructions to `~/.copilot/`, all projects automatically find them.

---

## How It Works: Example

**You ask for ANY instruction (commit message, Python refactoring, CDE definitions, etc.)**

```
Copilot searches automatically:
  1. Check [projectWorkspace]/.github/ (found? use it)
  2. If not found, check ~/.copilot/ (found? use it)
  3. If still not found, check awesome-copilot GitHub (use it)

Result: Right instruction found automatically
```

**To add new instructions across projects**: Just copy to `~/.copilot/`, and all projects automatically find it.

---

## Fallback Chain in Action

Copilot automatically checks in order:

1. **This project's context** - If you have project-specific instructions in `.github/`, use them
2. **Shared global context** - If not in project, check `~/.copilot/` (available to all projects)
3. **Authoritative source** - If not found locally, use awesome-copilot GitHub

**Result**: Right instruction found for this project + benefits from shared context across all projects

---

## Next Steps

1. ✅ Create `master-control.instructions.md` in `~/.copilot/instructions/` (GLOBAL, one-time)
2. ✅ Each project gets `copilot-instructions.md` in `[projectWorkspace]/.github/` (manually copy/maintain)
3. ⏳ Copy this project's reusable instructions to `~/.copilot/` as needed
4. ⏳ Repeat copy process for other projects (each contributes its own reusable files)

---

**Last Updated**: April 22, 2026
**Status**: Active - Precedence-only design; no task-specific mappings
**Future-proof**: New instructions automatically discoverable across all workspaces

**See also**: [COPILOT-CONTEXT-ARCHITECTURE.md](../COPILOT-CONTEXT-ARCHITECTURE.md) for workflow guidance and FAQ
