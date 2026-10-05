# .qoder/ Directory

Qoder AI configuration for the cr-misc-function project.

## Structure

```text
.qoder/
├── QODER.md          # Always-on project instructions (environment, standards, skills)
├── README.md         # This file — structure documentation
└── skills/           # Skill files invoked as slash commands
    ├── commit.md
    ├── clean-gone.md
    ├── create-confluence-docs.md
    ├── create-readme.md
    ├── generate-cde-spreadsheet.md
    ├── generate-cde.md
    ├── generate-pr-message.md
    ├── refactor-python.md
    ├── refactor-repositories.md
    ├── setup-workspace.md
    ├── update-cde.md
    └── validate-lint-config.md
```

## How to Use Skills

Skills are invoked via `/skill-name` in Qoder. Each skill is a self-contained markdown file with:

- **Frontmatter** — `name` and `description` for discovery
- **When to Use** — scenarios where the skill applies
- **Workflow** — step-by-step instructions
- **Validation** — checklist to verify correct execution

Example: Type `/commit` to generate a Conventional Commit + gitmoji message from staged changes.

## Relationship to Other Config Files

| File | Purpose | Scope |
| --- | --- | --- |
| `AGENTS.md` (workspace root) | Always-on instructions for all AI agents | Workspace |
| `.qoder/QODER.md` | Always-on instructions specific to Qoder AI | Workspace |
| `.qoder/skills/*.md` | Structured workflows invoked as slash commands | Workspace |
| `.vscode/settings.json` | VS Code workspace settings | Workspace |
| `.vscode/mcp.json` | MCP server definitions | Workspace |

## Equivalents Across AI Tools

| Qoder | Claude Code | GitHub Copilot |
| --- | --- | --- |
| `.qoder/QODER.md` | `CLAUDE/CLAUDE.md` | `.copilot/instructions/` |
| `.qoder/skills/*.md` | `CLAUDE/commands/*.md` | `.copilot/skills/` |
| `AGENTS.md` | `CLAUDE/CLAUDE.md` | `.github/copilot-instructions.md` |
| Memory system | Memory system | N/A |
| Subagent orchestration | Subagent orchestration | N/A |

## Template Files

Reusable templates for other projects are stored at:

```text
templates/ai/qoder/
├── QODER.template.md           # QODER.md template with placeholders
├── global-config.md            # Global user configuration guide
└── skills/
    ├── commit.template.md      # Commit skill template
    ├── refactor-python.template.md  # Python refactoring template
    └── setup-workspace.template.md  # Workspace setup template
```

Copy these to a new project's `.qoder/` directory and fill in the placeholders.
