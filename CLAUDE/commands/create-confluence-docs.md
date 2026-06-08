# Create Confluence Documentation

Generate Confluence-ready documentation with the standard hierarchical structure. All projects are part of a business system — documentation reflects this hierarchy.

## Target: $ARGUMENTS

If `$ARGUMENTS` specifies a system name, service type, or business context, use that. Otherwise, analyze the project and ask for clarification.

---

## Core Principle

**Every project is part of a larger business system.** A project like `da-obligor-api` is part of the "Obligor" system. Documentation structure always reflects this:

- **Parent pages (01, 02)**: Business logic + enterprise architecture (shared by all services in the system)
- **Service pages (03, 03a-d)**: This project's specific implementation
- **Reference page (04)**: Shared glossary and service matrix

**Generate documentation ONLY from current project state** — no historical changes, previous versions, or decision rationale.

---

## File Naming Convention

Format: `{page#}-{system-slug}-{service-name}-{section}.md`

Examples:

- `01-obligor-business-logic.md`
- `02-obligor-enterprise-architecture.md`
- `03-obligor-api-overview.md`
- `03a-obligor-api-architecture.md`
- `03b-obligor-api-development.md`
- `03c-obligor-api-deployment.md`
- `03d-obligor-api-operations.md`
- `04-obligor-reference.md`

Save all files to: `docs/confluence/`

---

## Service Type Detection

Identify project type from codebase (determines page content):

| Type | Indicators | Key Sections |
| --- | --- | --- |
| **API Server** | FastAPI, Flask, routes | Endpoints, auth, request/response |
| **Airflow** | DAGs, operators, schedules | DAG structure, task dependencies, SLAs |
| **Batch/ETL** | Scheduled jobs, transformations | Job docs, data flow, transformation logic |
| **Streaming Consumer** | Kafka consumer, event listeners | Event schemas, processing logic, consumer lag |
| **Library** | No main app, reusable modules | API reference, usage examples |
| **CLI Tool** | argparse, click, typer | Command reference, subcommands |

---

## Page Specifications

### 01 — Business Logic (500-1000 words)

**Audience**: Product managers, business analysts, architects

```markdown
# {System} - Business Logic

## What is {System}?
[Business description — non-technical]

## Business Rules
- Rule 1: [Non-technical description]
- Rule 2: ...

## Services Involved
| Service | Purpose | Team | Status |
| --- | --- | --- | --- |
| API Service | [Purpose] | [Team] | Active |

## Common Use Cases
1. [Use case with business context]
2. ...

---
**Next**: [Enterprise Architecture](02-{system}-enterprise-architecture)
```

### 02 — Enterprise Architecture (800-1200 words)

**Audience**: Architects, tech leads, senior developers

Sections: System architecture diagram (ASCII), service interaction flows, data consistency model, key architectural decisions, failure scenarios.

### 03 — Service Overview (600-800 words)

**Audience**: Other teams, external users, non-technical stakeholders

Focus on **how to use** this service — not how it's built.

**For API Services:**

- What does this API do? (business value)
- Access through gateways (Apigee → Internal Gateway → Backend)
- Environments and endpoints (SIT/UAT, Production)
- Authentication methods
- Common use cases and rate limits
- Getting started steps

**For Non-API Services:**

- What does this service do? (business outcome)
- Who uses it?
- How to request features / report issues
- Availability / SLAs

### 03a — Service Architecture (800-1200 words)

- Technical design specific to this service
- Components and dependencies
- Service-type-specific details (see table above)
- Data flow within this service

### 03b — Development (800-1200 words)

- Prerequisites
- Local setup steps (numbered, with commands)
- Running the application
- Running tests
- Common development workflows
- IDE setup tips

### 03c — Deployment (800-1200 words)

- Environments overview (dev, staging, prod)
- Deployment procedures per environment
- Rollback procedures
- Monitoring after deployment

### 03d — Operations (800-1200 words)

- Health checks and monitoring
- Common issues and solutions (3-5 scenarios)
- Logging and diagnostics
- Scheduled maintenance
- Escalation contacts

### 04 — Reference (600-1000 words)

- Glossary (shared terminology)
- Service comparison table
- Common cross-service workflows
- Troubleshooting flowchart
- Links to all services

---

## Confluence Formatting Standards

### Navigation Links (Required on Every Page)

**Top:**

```markdown
**Related Pages**: [Business Logic](01-{system}-business-logic) | [Architecture](03a-{system}-{service}-architecture)
```

**Bottom:**

```markdown
---
**Return to**: [{System} Overview](03-{system}-{service}-overview) | **Previous**: [Page X](link) | **Next**: [Page Y](link)
```

### Code Blocks

Always specify language:

```markdown
```python
def example(): ...
```

```bash
git clone https://repo.git
```

```text

### Notes/Warnings

```markdown
> **Note**: Important information that stands out

> **Warning**: Critical information users must know

> **Tip**: Helpful hint or best practice
```

### Tables

```markdown
| Header 1 | Header 2 | Header 3 |
| --- | --- | --- |
| Data A | Data B | Data C |
```

### Spacing Rules

- Blank line after headings
- Blank line before/after code blocks, tables, blockquotes
- Maximum 5 bullet items per list (split if more)
- Maximum 4 rows per table (use multiple tables if needed)

---

## Content Length Guidelines

| Page | Word Count | Sections | Code Examples |
| --- | --- | --- | --- |
| Overview | 500-800 | 4-5 | 1-2 |
| Technical | 800-1200 | 5-7 | 2-3 |
| Reference | 600-1000 | 5-6 | 1-2 |
| Procedural | 800-1200 | 6-8 | 2-4 |

**Principle**: Each page = 3-5 minute read.

---

## Output Structure

```text
docs/confluence/
├── 01-{system-slug}-business-logic.md
├── 02-{system-slug}-enterprise-architecture.md
├── 03-{system-slug}-{service}-overview.md
├── 03a-{system-slug}-{service}-architecture.md
├── 03b-{system-slug}-{service}-development.md
├── 03c-{system-slug}-{service}-deployment.md
├── 03d-{system-slug}-{service}-operations.md
└── 04-{system-slug}-reference.md
```

For multi-service systems, each service adds its own `03/03a-d` pages. Pages `01`, `02`, `04` are shared — create once, reuse for all services.

---

## Quality Checklist

- [ ] Title is clear and describes page content precisely
- [ ] Related pages listed at top and bottom
- [ ] Proper heading hierarchy (H1 → H2 → H3, no skipping)
- [ ] Code blocks have language specified
- [ ] Blank lines around blocks, tables, quotes
- [ ] Tables are scannable (not too wide)
- [ ] Lists are concise (max 5 items)
- [ ] Examples are copy-paste executable
- [ ] No unexplained acronyms (explained on first use)
- [ ] Internal links work (cross-references valid)
- [ ] Navigation complete (top and bottom links)
- [ ] Professional and consistent tone throughout
- [ ] Markdown valid (no formatting errors)
