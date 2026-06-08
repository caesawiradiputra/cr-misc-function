---
description: "GitHub Copilot domain-level instructions for [DOMAIN_NAME] - shared context across related projects"
templateFor: "Domain outer folder - copy to [domain]/.github/copilot-instructions.md and customize"
---

# GitHub Copilot Instructions for [DOMAIN_NAME] Domain

**This is a domain-level instructions file.** It provides shared context for all projects within this domain.
Place it at `[domain]/.github/copilot-instructions.md` (the outer folder, alongside the git repos).

**Scope**: Applies to all workspace roots in `[domain].code-workspace`.
**Precedence**: Domain-level. Each project's own `.github/copilot-instructions.md` takes priority over this file.

---

## ⚠️ ENTRY POINT INFORMATION (Immutable)

**Do not modify this section.**

### Purpose

Domain entry point for GitHub Copilot. Provides shared context across related projects in this domain.

> **Reference**: See `~/.copilot/instructions/master-control.instructions.md` for the authoritative fallback chain.

### Precedence Chain (Where Copilot Looks)

1. **Project-level** (highest priority) — `[project]/.github/copilot-instructions.md` inside each git repo
2. **Domain-level** (this file) — `[domain]/.github/copilot-instructions.md` — shared across all projects in domain
3. **Global context** — `~/.copilot/` — shared across all domains and projects
4. **Awesome-Copilot** (authoritative) — <https://github.com/github/awesome-copilot/>

### How This File Is Used

- Loaded when any file from this domain workspace is active
- Provides shared domain knowledge Copilot can reference for cross-project tasks
- Supplements (does not replace) each project's own instructions

---

## ✏️ DOMAIN CONTEXT (Customize this section)

### Domain Identity

**Domain Name**: [DOMAIN_NAME]

**Description**: [Describe the business domain — what problem this domain solves, its bounded context]

**Domain Type**: [e.g., Microservices / Event-driven / API + Consumer pair / Data Pipeline cluster]

### Projects in This Domain

| Project | Type | Repo Folder | Description |
| --- | --- | --- | --- |
| [project-1-name] | [API Service / Consumer / etc.] | `[folder-name]/` | [brief description] |
| [project-2-name] | [API Service / Consumer / etc.] | `[folder-name]/` | [brief description] |

### Shared Tech Stack

**Language**: [e.g., Python 3.11+]

**Shared Frameworks & Libraries**:

- [e.g., FastAPI (API layer)]
- [e.g., Kafka / Confluent (messaging)]
- [e.g., SQLAlchemy (ORM)]
- [e.g., Pydantic (validation & schemas)]

**Shared Infrastructure**:

- [e.g., PostgreSQL — primary database]
- [e.g., Redis — caching]
- [e.g., Kafka topic: `domain.entity.event`]

**Dependency Manager**: [e.g., uv — each project has its own `.venv`]

**Code Quality**: [e.g., Ruff (lint + format), mypy (type checking)]

### Shared Patterns & Conventions

#### Cross-Project Contracts

[Describe interfaces, schemas, or events shared between projects in this domain]

Example:

- **Shared Pydantic models** in `[project]/app/schemas/` — used by both API and consumer
- **Kafka event schema**: `{ "event_type": str, "entity_id": str, "payload": dict, "timestamp": str }`
- **API contract**: REST endpoints documented in `[project]/docs/api/`

#### Domain-Wide Code Conventions

- [e.g., Python 3.11+ union syntax `X | Y` not `Optional[T]`]
- [e.g., Double quotes, 4-space indent, line length 88]
- [e.g., Repository pattern for DB access]
- [e.g., Strategy pattern for pluggable implementations]

#### Configuration Management

[Describe how secrets/config are managed across this domain]

Example:

- Priority order: Vault secrets > `.env` file > environment variables > defaults
- Each project has its own `.env` (never shared between projects)
- Shared config schema in `[project]/app/configs/config_schemas.py`

#### Inter-Project Communication

[How do the projects in this domain communicate with each other?]

Example:

- `[project-1]` publishes events to Kafka topic `[topic-name]`
- `[project-2]` consumes from that topic and processes downstream
- Shared event contract defined in `[project-1]/app/events/schemas.py`

---

## Awesome-Copilot References

### Core Standards (All Projects)

- [Code Generation Guidelines](https://github.com/github/awesome-copilot/blob/main/instructions/code-generation-guidelines.instructions.md)
- [Security Standards (OWASP Top 10 2025)](https://github.com/github/awesome-copilot/blob/main/instructions/security-standards.instructions.md)

### Language-Specific

**For Python domains**:

- [Python Development](https://github.com/github/awesome-copilot/blob/main/instructions/python.instructions.md)

**Add relevant references for your domain's tech stack here.**

### Development Environment

**Windows PowerShell**:

- [windows-powershell-environment.instructions.md](C:/Users/203715/.copilot/instructions/windows-powershell-environment.instructions.md)

---

## Project-Specific Instructions

Each project has its own `.github/copilot-instructions.md` with project-specific details.
Those take priority over this domain file.

| Project | Instructions File | What It Covers |
| --- | --- | --- |
| [project-1-name] | `[folder-name]/.github/copilot-instructions.md` | [e.g., API endpoints, auth, middleware] |
| [project-2-name] | `[folder-name]/.github/copilot-instructions.md` | [e.g., Kafka consumer, retry logic, DLQ] |

---

## Workspace Structure

```text
[domain]/                                    ← domain outer folder
├── .github/
│   └── copilot-instructions.md             ← YOU ARE HERE (domain-level)
├── .vscode/
│   ├── settings.json                        ← shared workspace settings
│   └── mcp.json                             ← MCP server config
├── [domain].code-workspace
├── [project-1]/                             ← git repo #1
│   ├── .git/
│   ├── .github/
│   │   └── copilot-instructions.md         ← project-level (overrides this)
│   ├── .vscode/
│   │   ├── settings.json                    ← project-specific settings
│   │   └── launch.json
│   ├── .venv/
│   └── app/
└── [project-2]/                             ← git repo #2
    ├── .git/
    ├── .github/
    │   └── copilot-instructions.md         ← project-level (overrides this)
    ├── .vscode/
    │   ├── settings.json
    │   └── launch.json
    ├── .venv/
    └── app/
```

---

## Last Updated

- **Date**: [DATE]
- **Status**: [Active / Draft]
- **Domain**: [DOMAIN_NAME]
