# Qoder AI Configuration Templates

Reusable templates for configuring Qoder AI in any project workspace. Qoder is a VS Code-based IDE with built-in AI capabilities including agent orchestration, skills, memory, and MCP server support.

## Configuration Model

Qoder AI reads configuration from multiple sources, merged in priority order:

| Priority | Source | Scope | Committed to Git |
| --- | --- | --- | --- |
| 1 (highest) | User settings (`~/.vscode/settings.json`) | Global | No |
| 2 | Workspace `.vscode/settings.json` | Project | Yes |
| 3 | `AGENTS.md` (workspace root) | Project | Yes |
| 4 | `.vscode/mcp.json` | Project | Yes |
| 5 (lowest) | Default values | N/A | N/A |

### What Goes Where

| Config Type | Workspace (committed) | User (global) |
| --- | --- | --- |
| Project-specific tool auto-approve | `.vscode/settings.json` | — |
| Universal safe commands (cd, ls, pwd) | — | `~/.vscode/settings.json` |
| Universal blocklist (rm, curl, wget) | — | `~/.vscode/settings.json` |
| MCP server definitions | `.vscode/mcp.json` | — |
| Project context & conventions | `AGENTS.md` | — |
| User preferences & memory | — | Qoder memory system |
| Skills definitions | — | Qoder skills system |

## Templates in This Directory

### `AGENTS.template.md`

The primary configuration file for AI agent guidance. Place at the workspace root as `AGENTS.md`.

**What it provides:**
- Project overview and architecture quick reference
- Quick commands (setup, lint, test, run)
- Code conventions and style rules
- Common development tasks with step-by-step guides
- Pitfalls and debugging tips
- Qoder-specific configuration file locations

**How to use:**
1. Copy `AGENTS.template.md` to your project root
2. Rename to `AGENTS.md`
3. Replace all `[PLACEHOLDER]` values with your project's details
4. Remove sections that don't apply
5. Add project-specific sections as needed

### `mcp.template.json`

MCP (Model Context Protocol) server configuration. Place at `.vscode/mcp.json`.

**What it provides:**
- Input definitions for API keys (prompted securely, stored in OS keychain)
- HTTP server examples (remote endpoints)
- stdio server examples (local Python/Node processes)
- Authentication patterns (Bearer tokens, API keys)

**How to use:**
1. Copy `mcp.template.json` to `.vscode/mcp.json`
2. Uncomment the server types you need
3. Replace `[PLACEHOLDER]` values with actual server details
4. Add `inputs` entries for any API keys
5. Remove unused examples

### `workspace-settings.template.jsonc`

Qoder-specific VS Code workspace settings. Place at `.vscode/settings.json`.

**What it provides:**
- Chat/MCP integration settings
- Terminal auto-approve patterns (project-specific only)
- References to base VS Code settings from `templates/vscode/settings.json`
- Python, formatting, and linting config placeholders

**How to use:**
1. Copy `workspace-settings.template.jsonc` to `.vscode/settings.json`
2. Also copy the base settings from `templates/vscode/settings.json`
3. Merge both files — base settings for editor/Python, this template for Qoder AI settings
4. Uncomment and configure project-specific auto-approve patterns
5. Remove sections that don't apply to your project

**Important:** Do NOT duplicate global auto-approve rules here. Only project-specific tool patterns belong in workspace settings. Universal safe commands and blocklist entries go in user-level settings.

## Qoder AI Features

### AGENTS.md
- Workspace-level instruction file that Qoder reads automatically
- Contains project context, conventions, and guidance
- Replaces the need for `.github/copilot-instructions.md` and `CLAUDE/CLAUDE.md` when using Qoder
- Supports all AI agents that read AGENTS.md (not just Qoder)

### Memory System
- Persistent context across sessions
- Categories: user preferences, project info, development standards, lessons learned
- Automatically grows as you work with Qoder
- Can be manually created/updated via the memory tools

### Skills
- Reusable workflows invoked with `/skill-name` syntax
- Can be project-specific or globally available
- Combine multiple tool calls into a single workflow
- Similar to Claude Code's slash commands or Copilot's skills

### Subagent Orchestration
- Qoder can delegate tasks to specialized subagents
- Leader/expert pattern for complex multi-step tasks
- Task management with dependency tracking

### MCP (Model Context Protocol)
- Extend Qoder with external tools and data sources
- HTTP and stdio transport types supported
- Configured via `.vscode/mcp.json`
- Secrets managed through VS Code's input mechanism (stored in OS keychain)

### Terminal Auto-Approval
- Pre-approve safe terminal commands so Qoder can run them without confirmation
- Configured in `chat.tools.terminal.autoApprove` in settings.json
- Supports exact match and regex patterns
- See `templates/ai/shared/terminal-auto-approval.md` for comprehensive patterns

## Setup Checklist for New Projects

1. [ ] Copy `AGENTS.template.md` to project root as `AGENTS.md` and customize
2. [ ] Copy `workspace-settings.template.jsonc` to `.vscode/settings.json` and merge with base settings
3. [ ] Copy `mcp.template.json` to `.vscode/mcp.json` and add any MCP servers
4. [ ] Configure terminal auto-approve for project-specific tools in settings.json
5. [ ] Set up global user-level auto-approve rules for universal safe commands
6. [ ] Verify Qoder reads AGENTS.md by checking the chat context
7. [ ] Test MCP server connections in the Qoder chat panel
8. [ ] Add project-specific memory entries as you work (Qoder builds these automatically)

## Relationship to Other AI Templates

This directory is part of the `templates/ai/` collection:

```
templates/ai/
├── qoder/                           ← Qoder AI (this directory)
│   ├── AGENTS.template.md
│   ├── mcp.template.json
│   ├── workspace-settings.template.jsonc
│   └── README.md
├── claude-code/                     ← Claude Code
│   └── README.md
├── github-copilot/                  ← GitHub Copilot
│   └── README.md
└── shared/                          ← Cross-AI shared resources
    └── terminal-auto-approval.md
```

Each AI tool has its own configuration model. The `shared/` directory contains patterns applicable to all of them.
