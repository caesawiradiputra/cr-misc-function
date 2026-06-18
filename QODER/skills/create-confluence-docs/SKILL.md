---
name: create-confluence-docs
version: "1.0.0"
updated: "2026-06-18"
related_skills:
  - create-readme
description: Generate Confluence-ready documentation with hierarchical structure (business logic, enterprise architecture, service pages, reference). Use when the user triggers /create-confluence-docs, asks to create Confluence docs, or needs project documentation for a business system.
---

# Create Confluence Documentation

Generate Confluence-ready documentation with standard hierarchical structure. All projects are part of a business system.

## Target

If arguments specify a system name, service type, or business context, use that. Otherwise, analyze the project and ask for clarification.

## Core Principle

**Every project is part of a larger business system.** Documentation structure reflects this:
- **Parent pages (01, 02)**: Business logic + enterprise architecture (shared by all services)
- **Service pages (03, 03a-d)**: This project's specific implementation
- **Reference page (04)**: Shared glossary and service matrix

**Generate documentation ONLY from current project state** — no historical changes or decision rationale.

## File Naming Convention

Format: `{page#}-{system-slug}-{service-name}-{section}.md`

Save all files to: `docs/confluence/`

## Service Type Detection

| Type | Indicators | Key Sections |
| --- | --- | --- |
| **API Server** | FastAPI, Flask, routes | Endpoints, auth, request/response |
| **Airflow** | DAGs, operators, schedules | DAG structure, task dependencies, SLAs |
| **Batch/ETL** | Scheduled jobs, transformations | Job docs, data flow, transformation logic |
| **Streaming Consumer** | Kafka consumer, event listeners | Event schemas, processing logic, consumer lag |
| **Library** | No main app, reusable modules | API reference, usage examples |
| **CLI Tool** | argparse, click, typer | Command reference, subcommands |

## Page Specifications

### 01 — Business Logic (approx. 500-1000 words)
**Audience**: Product managers, business analysts, architects

Sections: What is {System}?, Business Rules, Services Involved (table), Common Use Cases.

### 02 — Enterprise Architecture (approx. 800-1200 words)
**Audience**: Architects, tech leads, senior developers

Sections: System architecture diagram (ASCII), service interaction flows, data consistency model, key architectural decisions, failure scenarios.

### 03 — Service Overview (approx. 600-800 words)
**Audience**: Other teams, external users, non-technical stakeholders

Focus on **how to use** this service. For APIs: access through gateways, environments/endpoints, authentication, rate limits. For non-APIs: business outcome, who uses it, SLAs.

### 03a — Service Architecture (approx. 800-1200 words)
Technical design, components and dependencies, service-type-specific details, data flow.

### 03b — Development (approx. 800-1200 words)
Prerequisites, local setup steps (numbered, with commands), running the app, running tests, common workflows.

### 03c — Deployment (approx. 800-1200 words)
Environments overview, deployment procedures per environment, rollback procedures, monitoring after deployment.

### 03d — Operations (approx. 800-1200 words)
Health checks and monitoring, common issues and solutions (3-5 scenarios), logging and diagnostics, escalation contacts.

### 04 — Reference (approx. 600-1000 words)
Glossary, service comparison table, common cross-service workflows, troubleshooting flowchart, links to all services.

## Confluence Formatting Standards

> See [_shared/markdown-standards.md](../_shared/markdown-standards.md) for common markdown formatting rules. Below are Confluence-specific additions.

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

### Formatting Rules
- Code blocks: always specify language
- Notes/Warnings: use `> **Note**:`, `> **Warning**:`, `> **Tip**:`
- Blank line after headings, before/after code blocks, tables, blockquotes
- Maximum 5 bullet items per list, maximum 4 rows per table

> Word counts are approximate suggestions. Adjust based on project complexity. Smaller projects may need shorter pages; larger systems may need longer ones.

## Output Structure

```text
docs/confluence/
+-- 01-{system-slug}-business-logic.md
+-- 02-{system-slug}-enterprise-architecture.md
+-- 03-{system-slug}-{service}-overview.md
+-- 03a-{system-slug}-{service}-architecture.md
+-- 03b-{system-slug}-{service}-development.md
+-- 03c-{system-slug}-{service}-deployment.md
+-- 03d-{system-slug}-{service}-operations.md
+-- 04-{system-slug}-reference.md
```

For multi-service systems, each service adds its own `03/03a-d` pages. Pages `01`, `02`, `04` are shared.

## Publishing

The generated files are standard markdown. To publish them on Confluence:

- **REST API**: Use the Confluence REST API to create/update pages programmatically.
- **Confluence CLI**: Use the `confluence` CLI tool to push markdown files.
- **Manual copy-paste**: Copy the rendered markdown into the Confluence editor.

This skill generates content only — it does not implement publishing. Choose the method that fits your workflow.

## Quality Checklist

- [ ] Title describes page content precisely
- [ ] Related pages listed at top and bottom
- [ ] Proper heading hierarchy (H1 -> H2 -> H3, no skipping)
- [ ] Code blocks have language specified
- [ ] Blank lines around blocks, tables, quotes
- [ ] Lists concise (max 5 items), tables scannable
- [ ] Examples are copy-paste executable
- [ ] No unexplained acronyms
- [ ] Internal cross-references valid
- [ ] Navigation complete (top and bottom links)
- [ ] Markdown valid (no formatting errors)
