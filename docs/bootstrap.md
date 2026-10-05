# Workspace Bootstrap & AI Environment Synchronization

Your objective is to initialize this workspace according to the best practices of the currently running IDE and AI Agent while keeping all reusable configurations centralized in the shared project `cr-misc-function`.

## Objectives

1. Detect the current execution environment.
2. Discover existing workspace templates.
3. Reuse existing templates whenever possible.
4. Generate missing configurations following the latest official best practices.
5. Separate global (user) configuration from workspace configuration.
6. Save reusable templates back into `cr-misc-function` for future projects.

---

# Phase 1 - Detect Environment

Determine as accurately as possible:

## IDE

Examples include (but are not limited to):

- VS Code
- Cursor
- Windsurf
- Qoder
- JetBrains IDE
- Zed
- Neovim

## AI Agent

Examples include:

- Claude Code
- GitHub Copilot Chat
- GitHub Copilot Agent
- OpenAI Codex
- Gemini CLI
- Gemini Code Assist
- OpenRouter AI
- Qoder AI
- Cline
- Roo Code
- Continue
- Aider

Determine:

- IDE name
- IDE version (if available)
- AI Agent name
- AI Agent version
- Supported configuration files
- Supported instruction files
- Supported prompt/template files
- Supported MCP configuration
- Supported terminal approval configuration
- Supported workspace configuration
- Supported user/global configuration

Do not guess unsupported features.

---

# Phase 2 - Scan Shared Template Repository

Assume this workspace contains a shared repository named:

cr-misc-function

Search recursively for reusable assets, including but not limited to:

- IDE settings
- AI agent configuration
- Prompt templates
- Skills
- Commands
- MCP configuration
- Workspace rules
- User rules
- Coding standards
- Documentation templates
- Git templates
- Terminal auto approval configuration
- Security configuration
- Task templates
- Slash commands
- Context files
- Memory files

Recognize configuration regardless of naming convention.

Examples:

.github/
.vscode/
.cursor/
.claude/
.codex/
.gemini/
.qoder/
.mcp/
.ai/
.templates/
.skills/
.prompts/
.instructions/

Also inspect Markdown documentation that describes setup procedures.

Produce an inventory of discovered templates.

---

# Phase 3 - Match Existing Templates

Determine whether templates already exist for:

Current IDE

Current AI Agent

Current IDE + Current AI Agent combination

If found:

- validate them
- check for outdated configuration
- compare against current best practices
- identify deprecated options
- identify missing capabilities

Recommend improvements if needed.

---

# Phase 4 - Bootstrap Missing Configuration

If configuration does not exist:

Use existing templates from other IDEs or AI agents as references.

Reuse their intent while translating them into the current platform's native configuration.

Do NOT simply rename files.

Follow the official configuration schema of the detected IDE and AI agent.

Generate:

## Global/User Configuration

Contains reusable settings such as:

- terminal auto approval
- model preferences
- coding standards
- reusable instructions
- security rules
- MCP defaults
- default permissions
- reusable prompt templates
- formatting preferences
- AI behavior
- documentation preferences

These settings should be applicable across all projects.

---

## Workspace Configuration

Contains only project-specific configuration.

Examples:

- project commands
- build commands
- test commands
- lint commands
- formatter commands
- project MCP servers
- project prompts
- project context
- project memory
- repository instructions
- workspace-specific terminal approvals

Do not duplicate global configuration.

Workspace configuration should be minimal.

---

# Phase 5 - Validate

Validate generated configuration against:

- current IDE capabilities
- current AI Agent capabilities
- official configuration schema
- deprecated options
- unsupported fields

Never invent configuration options.

---

# Phase 6 - Synchronize Template Repository

After successful generation:

Create reusable templates inside:

cr-misc-function

using a clear structure.

Example:

templates/

    ide/
        vscode/
        cursor/
        qoder/
        jetbrains/

    ai/
        claude-code/
        github-copilot/
        codex/
        gemini/
        openrouter/
        qoder/

    shared/
        prompts/
        instructions/
        skills/
        commands/
        mcp/
        terminal/
        security/
        documentation/

Store only reusable templates.

Never store project-specific configuration here.

---

# Phase 7 - Best Practice Review

Review the generated configuration for:

- latest official recommendations
- least privilege principle
- minimal duplication
- maintainability
- portability
- future compatibility

If a newer recommended configuration exists, prefer it.

If multiple valid approaches exist, explain why the selected approach is preferred.

---

# Phase 8 - Summary

Produce a report containing:

## Environment

Detected IDE

Detected AI Agent

Versions

Configuration files used

---

## Existing Templates

List reused templates.

---

## Generated Templates

List newly created templates.

---

## Updated Templates

List improved templates.

---

## Workspace Configuration

List files created or modified.

---

## Global Configuration

List files created or modified.

---

## Recommendations

Suggest improvements that could benefit all future workspaces.

Always prioritize reuse over duplication.

The shared repository (`cr-misc-function`) is the single source of truth for reusable templates.

Project workspaces should remain lightweight and contain only project-specific configuration.