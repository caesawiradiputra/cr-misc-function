# GitHub Copilot Context Architecture

**Last Updated**: April 22, 2026

This document clarifies the three-tier Copilot context system and how to use it across multiple projects.

---

## Architecture Overview

```text
Tier 1: PROJECT WORKSPACE (highest priority)
├── [projectWorkspace]/.github/copilot-instructions.md
├── [projectWorkspace]/.github/instructions/
├── [projectWorkspace]/.github/prompts/
├── [projectWorkspace]/.github/skills/
├── [projectWorkspace]/.github/agents/
└── [projectWorkspace]/.github/references/

                    ↓ (if not found above)

Tier 2: GLOBAL SHARED CONTEXT
├── ~/.copilot/instructions/
├── ~/.copilot/prompts/
├── ~/.copilot/skills/
├── ~/.copilot/agents/
└── ~/.copilot/references/

                    ↓ (if not found above)

Tier 3: AWESOME-COPILOT AUTHORITATIVE
└── https://github.com/github/awesome-copilot/
```

**Precedence**: Project → Global → Awesome-Copilot (automatic fallback)

---

## Three Key Files

### 1. `master-control.instructions.md` (GLOBAL - One Copy)

**Purpose**: Defines the 3-level precedence chain for ALL projects

**Location**: `~/.copilot/instructions/master-control.instructions.md`

**Content**:

- How Copilot searches for instructions (precedence order)
- File organization across tiers
- Setup instructions (one-time, when first created)
- How the precedence chain works in practice

**When to update**:

- Sparingly (when precedence rules change)
- Almost never in practice

**Who manages it**: You, globally (affects all projects)

---

### 2. `copilot-instructions.md` (PER-PROJECT - Template)

**Purpose**: Project entry point; customized for each project's type and needs

**Template location**: `c:\Users\203715\Documents\Repo\cr-misc-function\.github\copilot-instructions.md`

**Copy to**: `[newProject]/.github/copilot-instructions.md` (for each project)

**Content**:

- ⚠️ ENTRY POINT INFORMATION (immutable; shared architecture reference)
- ✏️ PROJECT CONTEXT (customize for this project)
  - Project Identity (name, description, type)
  - Tech Stack (language, frameworks, dependencies)
  - Project-Specific Patterns & Conventions
  - Awesome-Copilot References (select relevant to project type)
  - Project-Specific Instructions & Files
  - Metadata (Last Updated)

**When to update**:

- Periodically, as your project evolves
- When language/framework changes
- When architectural patterns change
- Use the "update-copilot-instructions" skill to guide updates

**Who manages it**: You, per project (different for each project)

---

### 3. Project-Specific Files in `.github/`

**Purpose**: Store instructions/prompts/skills unique to this project

**Locations**:

- `.github/instructions/` - Project-specific instructions
- `.github/prompts/` - Project-specific prompts
- `.github/skills/` - Project-specific skills
- `.github/agents/` - Project-specific agents
- `.github/references/` - Project-specific references

**When to add**:

- When you need project-type-specific guidance
- When instructions apply only to this project

**When to copy to global** (`~/.copilot/`):

- When the file is REUSABLE across multiple projects
- Example: A generic "refactor-python-code" skill can be copied; project-specific CDE data cannot

---

## Workflow: Setting Up a New Project

### Step 1: Copy Template (Per Project)

```text
Source: c:\Users\203715\Documents\Repo\cr-misc-function\.github\copilot-instructions.md
Dest:   [newProject]/.github/copilot-instructions.md
Result: Fresh template in the new project
```

### Step 2: Customize Template (Per Project)

```text
Run skill: "update-copilot-instructions"
Input:     Analyze the new project's purpose, type, tech stack
Output:    Filled-in copilot-instructions.md with:
           - Correct project name and description
           - Selected project type (API, Pipeline, App, Library)
           - Actual tech stack
           - Relevant awesome-copilot references
           - Project-specific patterns
```

### Step 3: Share Reusable Files (Optional, Per Project)

```text
Identify reusable files in [newProject]/.github/
Copy to: ~/.copilot/
Result:  Available across all projects
```

### Step 4: Update Globally (One-Time Only)

```text
Copy once: master-control.instructions.md to ~/.copilot/instructions/
Result:    All projects use the same precedence chain
```

---

## File Lifecycle

### Global Files (ONE copy, shared)

```text
master-control.instructions.md
├── Created once
├── Updated sparingly (when precedence rules change)
├── Used by all projects automatically
└── Location: ~/.copilot/instructions/
```

### Project Template (COPIED, customized per project)

```text
copilot-instructions.md
├── Template in cr-misc-function/.github/
├── Copied to [newProject]/.github/copilot-instructions.md
├── Customized with project-specific context
├── Updated periodically as project evolves
└── Each project maintains its own copy
```

### Reusable Instructions (OPTIONALLY shared)

```text
[generic-instruction].md
├── Starts in [projectWorkspace]/.github/instructions/
├── When reusable across projects: copy to ~/.copilot/instructions/
├── Automatically discovered by all projects
└── Each project can contribute different reusable files
```

### Project-Specific Files (STAY local)

```text
[project-only-file].md
├── Lives in [projectWorkspace]/.github/
├── NOT copied to global
├── Used only by this project
└── Examples: CDE data files, project-specific configurations
```

---

## Key Rules

### ✅ DO

- Copy `copilot-instructions.md` template to new projects
- Customize the template with your project's context
- Copy `master-control.instructions.md` to `~/.copilot/` once
- Use "update-copilot-instructions" skill when updating project context
- Copy REUSABLE instructions from `.github/` to `~/.copilot/`

### ❌ DON'T

- Modify ENTRY POINT INFORMATION section in copilot-instructions.md
- Update `master-control.instructions.md` frequently
- Copy project-specific data to global context
- Add task-specific file mappings (Copilot discovers automatically)
- Manually specify which file for which task

---

## Example: Setting Up Project B from Project A Template

```text
1. Copy template:
   cp cr-misc-function/.github/copilot-instructions.md \
      project-b/.github/copilot-instructions.md

2. Customize for Project B:
   - Open project-b/.github/copilot-instructions.md
   - Run "update-copilot-instructions" skill
   - Fill in Project B's name, description, type, tech stack
   - Select appropriate awesome-copilot references
   - Add Project B-specific patterns

3. Share if needed:
   - Identify reusable files from Project A
   - Copy to ~/.copilot/
   - All future projects automatically discover them

4. Global setup (one-time):
   - Copy master-control.instructions.md to ~/.copilot/instructions/
   - Done! All projects now use the same precedence chain
```

---

## FAQ

**Q: Do I copy master-control.instructions.md to every project?**
A: No. Only ONCE to `~/.copilot/instructions/`. All projects reference the same global copy.

**Q: Do I copy copilot-instructions.md to every project?**
A: Yes. It's a template. Copy to each new project's `.github/` folder and customize.

**Q: When do I update copilot-instructions.md?**
A: Periodically, as the project evolves. Use the "update-copilot-instructions" skill to guide updates.

**Q: How often do I update master-control.instructions.md?**
A: Sparingly. Only when the precedence chain itself needs to change (rare).

**Q: What goes in ~/.copilot/ vs [projectWorkspace]/.github/?**
A: Reusable instructions → global. Project-specific data → local.

**Q: Will new projects automatically find global instructions?**
A: Yes. The precedence chain searches ~/.copilot/ automatically if not found in the project.

---

## See Also

- [Master Control](./instructions/master-control.instructions.md) - Global precedence chain
- [Copilot Instructions Template](./copilot-instructions.md) - Per-project template
- [Update Copilot Instructions Skill](./.github/skills/update-copilot-instructions/SKILL.md) - How to customize templates
