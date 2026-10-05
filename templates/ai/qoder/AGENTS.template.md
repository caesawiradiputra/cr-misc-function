# AI Agent Guidance for [PROJECT_NAME]

Quick reference for AI agents (Qoder, GitHub Copilot, Claude Code, and others) contributing to or consuming from this project.

## Project Overview

**[PROJECT_DESCRIPTION]**

**Project Type**: [API Service / Consumer App / Data Pipeline / Library / Other]

**Design Philosophy**: [Copy-paste ready / Import-first / Framework-based / Other]

## Architecture Quick Reference

### Core Patterns

[Add your project's core architectural patterns here. Examples below:]

#### 1. **[Pattern Name]** ([Domain])

**What**: [One-sentence description]

**How it works**:

- [Key mechanism 1]
- [Key mechanism 2]
- [Key mechanism 3]

**Why**: [Rationale for this pattern]

#### 2. **[Pattern Name]** ([Domain])

**What**: [One-sentence description]

**How it works**:

- [Key mechanism 1]
- [Key mechanism 2]

**Why**: [Rationale for this pattern]

---

## Quick Commands

### Setup & Environment

```powershell
# [First-time setup command]
[SETUP_COMMAND]

# [Activate environment]
[ACTIVATE_COMMAND]
```

### Code Quality (Before Committing)

```powershell
# [Lint command]
[LINT_COMMAND]

# [Format command]
[FORMAT_COMMAND]

# [Type check command]
[TYPECHECK_COMMAND]

# Run all checks together (PowerShell: use semicolons)
[ALL_CHECKS_COMMAND]
```

### Testing

```powershell
# [Run all tests]
[TEST_COMMAND]

# [Run specific test]
[TEST_SPECIFIC_COMMAND]

# [Run with coverage]
[TEST_COVERAGE_COMMAND]
```

### Running Application

```powershell
# [Run main application]
[RUN_COMMAND]
```

## File Cross-Reference Guide

Quick lookup for key architecture files:

| File | Purpose | When to Reference |
| ------ | --------- | ------------------ |
| **[path/to/key/file]** | [Purpose] | [When to reference] |
| **[path/to/another/file]** | [Purpose] | [When to reference] |

## Code Conventions

### Type Hints

- [Type hint convention 1]
- [Type hint convention 2]

### Linting & Formatting

- **[Linter]**: [Rules/Config]
- **Line length**: [N] characters
- **Quotes**: [Single/Double] quotes
- **Imports**: [Sorting convention]

### Code Organization

- [Organization rule 1]
- [Organization rule 2]
- [Organization rule 3]

## Common Development Tasks

### [Task 1: e.g., Add a New Module]

1. [Step 1]
2. [Step 2]
3. [Step 3]
4. [Step 4]

### [Task 2: e.g., Create a New Feature]

1. [Step 1]
2. [Step 2]
3. [Step 3]

## Key Pitfalls to Avoid

| Issue | Mitigation |
| ------- | ----------- |
| **[Pitfall 1]** | [Mitigation strategy] |
| **[Pitfall 2]** | [Mitigation strategy] |
| **[Pitfall 3]** | [Mitigation strategy] |

## Configuration Management

[Describe your project's configuration approach, e.g.:]

**[N]-tier configuration system**:

1. **[Source 1]** ([Environment])
2. **[Source 2]** ([Environment])
3. **[Source 3]** ([Environment])
4. **Defaults** (built-in fallbacks)

## Debugging Tips

**[Error category 1]**:

- [Tip 1]
- [Tip 2]

**[Error category 2]**:

- [Tip 1]
- [Tip 2]

## Qoder AI Configuration

This workspace uses the following Qoder AI features:

- **AGENTS.md**: This file (workspace-level AI guidance)
- **Memory**: Persistent context across sessions (user preferences, project knowledge, lessons learned)
- **Skills**: Reusable workflows invoked via `/skill-name` syntax
- **MCP**: Model Context Protocol servers configured in `.vscode/mcp.json`
- **Terminal auto-approval**: Safe commands pre-approved in `.vscode/settings.json` under `chat.tools.terminal.autoApprove`

### Configuration File Locations

```
[projectWorkspace]/
├── AGENTS.md                          ← YOU ARE HERE (workspace entry point)
├── .vscode/
│   ├── settings.json                  ← Qoder/VS Code settings + terminal auto-approval
│   └── mcp.json                       ← MCP server definitions
├── [source files]
└── [other config files]
```

---

**Last Updated**: [DATE] | **Status**: [Active / Template / Draft]
**For detailed project context**: See [REFERENCE_LINK]
