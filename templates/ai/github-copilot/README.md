# GitHub Copilot Configuration — Quick Reference

GitHub Copilot is GitHub's AI pair programmer, integrated into VS Code and other editors. This reference documents how Copilot is configured in this project.

## Configuration File Locations

GitHub Copilot reads configuration from a 3-tier precedence chain:

```
1. Workspace (highest priority)
   [projectWorkspace]/
   ├── .github/
   │   ├── copilot-instructions.md    ← Entry point (project-specific)
   │   ├── instructions/              ← Auto-apply instruction files
   │   ├── prompts/                   ← Project prompt templates
   │   ├── skills/                    ← Project skill definitions
   │   ├── agents/                    ← Project agent workflows
   │   └── references/                ← Project reference documents

2. Global Context (fallback)
   ~/.copilot/
   ├── instructions/                  ← Reusable instructions
   ├── prompts/                       ← Shared prompt templates
   ├── skills/                        ← Shared skill definitions
   ├── agents/                        ← Shared agent workflows
   └── references/                    ← Shared references

3. Awesome-Copilot (authoritative)
   https://github.com/github/awesome-copilot/
   ├── instructions/                  ← Best practices & standards
   └── ...                            ← Language-specific guidance
```

## 3-Tier Precedence System

When Copilot needs an instruction, it searches in this order:

1. **This Workspace** (highest priority) — `.github/`
   - Project-specific instructions and configurations
   - Always takes precedence over global/authoritative sources

2. **Global Context** (fallback) — `~/.copilot/`
   - Reusable instructions shared across projects
   - Common workflows, prompts, and references

3. **Awesome-Copilot** (authoritative) — GitHub repository
   - Best practices and language-specific guidance
   - Used when project-specific guidance is insufficient

## copilot-instructions.md Structure

The entry point file (`.github/copilot-instructions.md`) contains two main sections:

### Immutable Section (do not modify)

- Purpose and discovery mechanism
- Precedence chain definition
- How Copilot uses the file

### Customizable Section (project-specific)

- **Project Identity**: Name, description, type
- **Tech Stack**: Language, framework, dependencies
- **Project-Specific Patterns**: Unique conventions
- **Awesome-Copilot References**: Selected language/framework references
- **Project-Specific Instructions**: Description of files in `.github/instructions/`

## Instruction Files with `applyTo`

Files in `.github/instructions/` can include frontmatter with an `applyTo` pattern:

```yaml
---
applyTo: "**/*.py"
---
# Python-specific instructions
...
```

These instructions trigger automatically when Copilot works on matching files.

## Available Skills (This Project)

Skills are defined in `.copilot/skills/` and `.github/skills/`:

- **update-copilot-instructions**: Guides customization of `copilot-instructions.md` for new projects
- Additional project-specific skills may be defined in `.github/skills/`

## Syncing to Global Context

Use the sync script to copy reusable files to `~/.copilot/`:

```powershell
# Preview what will be synced
.\scripts\powershell\chat-Sync-CopilotContext.ps1 -DryRun

# Actually sync
.\scripts\powershell\chat-Sync-CopilotContext.ps1
```

**Copy to `~/.copilot/`**: Generic instructions, reusable prompts, common workflows
**Keep in `.github/`**: Project-specific instructions, CDE data, project configurations

## Relationship to Other AI Configs

GitHub Copilot's configuration is separate from but parallel to:

- **Claude Code**: `.claude/settings.json`, `CLAUDE/CLAUDE.md`, `CLAUDE/commands/`
- **Qoder AI**: `AGENTS.md`, `.vscode/settings.json`, `.vscode/mcp.json`

The `AGENTS.md` file at the workspace root serves as a shared entry point that all AI agents can read. Copilot also reads `.github/copilot-instructions.md` for Copilot-specific instructions and the precedence chain.
