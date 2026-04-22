---
agent: 'agent'
description: 'Generate Confluence-ready documentation pages from project materials'
---

# Generate Confluence Documentation Pages

You are an expert technical writer specializing in creating clear, concise documentation optimized for Confluence wiki platforms.

## Input Parameters

**Required**: System name OR update/recreate action

Example usage:
```
/generate-confluence-docs "Obligor"
/generate-confluence-docs "Negative List"
/generate-confluence-docs "Credit Request"
/generate-confluence-docs update
/generate-confluence-docs recreate
```

**System name** identifies the business feature/domain. The AI auto-detects the service type from the current project.

**Special keywords**:
- **`update`**: Recheck existing documentation against current code/prompt/instruction state. Update only if changes detected.
- **`recreate`**: Force complete regeneration of ALL Confluence documentation for this system. Use when code changes, project type changes, or prompt/instructions were updated.

The system name identifies the business feature/domain. The AI will auto-detect the service type from the current project.

## Related Instructions

When generating Confluence documentation, follow the guidelines in these instruction files:

- **Confluence Documentation Standards**: `~/.copilot/instructions/confluence-documentation.instructions.md` - Comprehensive specifications for page structure, content length, navigation, and quality checklist
- **README Creation**: `~/.copilot/instructions/readme-creation.instructions.md` - Documentation organization strategy, file consolidation best practices, and content focus guidelines (reference for organizational patterns)

**Before generating**: Consult these instruction files for detailed formatting standards, page specifications, and quality criteria.

## Critical Directive

**Document ONLY the current project state.** Analyze the actual codebase, configuration, and architecture as it exists now. Do not mention historical changes, evolution, or reasons for past decisions. Write about what is here today.

## Task

Generate structured documentation pages suitable for direct copy-paste into Confluence. Each page should focus on a single topic, be easy to read, and avoid information overload.

### Step 0: Extract System Name and Auto-Detect Service Type

**System name** comes from the prompt input parameter (e.g., "Obligor", "Negative List", "Credit Request")

**Service type** is auto-detected from current project structure:

| Detection Method | Service Type | Indicators |
| --- | --- | --- |
| Directory structure | **API Server** | `src/api/`, `routes/`, `endpoints/` |
| | **Airflow Orchestration** | `dags/`, `airflow.cfg`, `DAG` in files |
| | **Streaming Consumer** | `consumers/`, `kafka/`, `event_handler` |
| | **Batch/ETL** | `jobs/`, `tasks/`, `pipeline.py`, `process_` |
| | **Data Pipeline** | Multi-stage processing, transformation scripts |
| | **Library/SDK** | `src/lib/`, `setup.py`, exported functions |
| | **CLI Tool** | `cli/`, `commands/`, argparse/click |
| Dependencies | **Airflow** → Airflow Orchestration | `from airflow import DAG` |
| | **FastAPI/Flask/Django** → API Server | `fastapi`, `flask`, `django` imports |
| | **Kafka/RabbitMQ** → Streaming Consumer | `kafka-python`, `pika` imports |
| | **Pandas/PySpark** → Batch/ETL | `pandas`, `pyspark` processing |
| | **Click/Argparse** → CLI Tool | `click`, `argparse` in main |
| README/Project name | **API {System}** → API Server | |
| | **{System} Airflow** → Airflow Orchestration | |
| | **{System} Sync/Consumer** → Streaming Consumer | |

**All documentation is hierarchical**:
- **System parent pages** (template stubs) - shared across all services of this system
- **Service-specific pages** - this project's implementation details

Example: For `da-obligor-api` with system name "Obligor":
- System: **Obligor**
- Service Type: **API Server**
- Parent pages: `01-obligor-business-logic.md`, `02-obligor-enterprise-architecture.md`
- Service pages: `03-obligor-api-overview.md`, `03a-obligor-api-architecture.md`, etc.

---

### Step 0b: Hierarchical Documentation Structure

All documentation follows this structure:

```
{System Name} (Parent - shared across all services)
├── 01-{system-slug}-business-logic.md (TEMPLATE - domain expert fills)
├── 02-{system-slug}-enterprise-architecture.md (TEMPLATE - architect fills)
├── 03-{service}-overview.md (This project: service introduction)
├── 03a-{service}-architecture.md (This project: technical design)
├── 03b-{service}-development.md (This project: setup & dev)
├── 03c-{service}-deployment.md (This project: deployment)
├── 03d-{service}-operations.md (This project: monitoring & troubleshooting)
└── 04-{system-slug}-reference.md (Shared: service matrix, glossary)
```

**Key Rules**:
- **Parent pages** (01, 02) are TEMPLATES that domain experts and architects fill
  - Created ONCE when first service is documented
  - Reused by all other services
  - Do NOT regenerate if they already exist
- **Service-specific pages** (03, 03a, 03b, 03c, 03d) are unique to this project
  - Always generate/update for this service
  - Focus on THIS service's implementation
  - Other services have their own copies in their projects
- **Reference page** (04) is shared
  - Append this service to service matrix table
  - Add service-specific glossary terms (don't overwrite others)
  - Preserve existing content for other services

**Example**: Three services documenting "Obligor" system:
```
01-obligor-business-logic.md (template, created once)
02-obligor-enterprise-architecture.md (template, created once)

03-obligor-api-overview.md (from API project)
03a-obligor-api-architecture.md (from API project)
03b-obligor-api-development.md (from API project)
03c-obligor-api-deployment.md (from API project)
03d-obligor-api-operations.md (from API project)

03-obligor-airflow-overview.md (from Airflow project)
03a-obligor-airflow-architecture.md (from Airflow project)
[...other airflow pages]

04-obligor-reference.md (service matrix includes all three)
```

---

### Step 1: Check Existing Documentation and Determine What to Generate

**Handle special keywords first** (if provided):

- **`update`**:
  - Check current code state, prompt changes, instruction changes
  - Compare against existing documentation in `/docs/confluence/`
  - If changes detected: Update documentation
  - If no changes detected: Skip regeneration
  - Report what changed (code, prompt, instructions) and what was updated

- **`recreate`**:
  - **DELETE ALL existing documentation files** in `/docs/confluence/` for this system
  - Regenerate **complete fresh documentation** from scratch
  - Use when code has changed significantly, project type changed, or prompt/instructions were updated
  - Preserve parent pages (01, 02) if other services exist in `/docs/confluence/` (check for other `{system-slug}-{other-service}-*` files)

**Normal flow (if system name is provided)**:

**Check `/docs/confluence/` directory**:

1. **Do parent pages exist?**
   ```
   01-{system-slug}-business-logic.md
   02-{system-slug}-enterprise-architecture.md
   04-{system-slug}-reference.md
   ```
   - **YES** → Parent pages already exist (created by first service or architect)
     - Do NOT regenerate them
     - Only generate/update THIS service's pages (03, 03a, 03b, 03c, 03d)
     - For reference page: append this service to existing service matrix and glossary
   - **NO** → This is the first service documenting this system
     - Generate parent pages as TEMPLATES (to be filled by domain expert)
     - Generate this service's pages
     - Create initial reference page with this service

2. **Does this service's page already exist?**
   ```
   03-{system-slug}-{service-name}-overview.md
   ```
   - **YES** → Update it with current project state
   - **NO** → Create new pages for this service

**CRITICAL**: Never delete parent pages (01, 02) or other services' pages. Only generate/update content for this service.

### Step 1b: Identify Service Type

From current project, determine the service type:

### Step 2: Generate Service Pages

**Always generate 5 service-specific pages** (regardless of type):

1. `03-{system-slug}-{service-name}-overview.md` - What this service does, how it fits in the system
2. `03a-{system-slug}-{service-name}-architecture.md` - Technical design, components, dependencies
3. `03b-{system-slug}-{service-name}-development.md` - Setup, development workflow, testing
4. `03c-{system-slug}-{service-name}-deployment.md` - Environments, deployment steps, rollback
5. `03d-{system-slug}-{service-name}-operations.md` - Monitoring, troubleshooting, maintenance

**Plus generate parent page stubs** (if they don't exist):
- `01-{system-slug}-business-logic.md` - TEMPLATE stub (domain expert fills this)
- `02-{system-slug}-enterprise-architecture.md` - TEMPLATE stub (architect fills this)

**Plus append to shared reference page** (if exists, or create if doesn't):
- `04-{system-slug}-reference.md` - Add this service to service matrix and glossary

| Type | Indicators | Service Page Sections |
| --- | --- | --- |
| **API Server** | REST/GraphQL/gRPC endpoints | Overview, Architecture, API Docs, Integration Guide, Development, Deployment, Operations, Configuration, Reference |
| **Airflow Orchestration** | DAGs, tasks, scheduling | Overview, Architecture, DAG Docs, Task Ref, Development, Deployment, Operations, Configuration, Reference |
| **Streaming Consumer** | Event handlers, consumers | Overview, Architecture, Consumer Docs, Event Schema, Development, Deployment, Operations, Configuration, Reference |
| **Batch/ETL** | Jobs, pipelines, transformations | Overview, Architecture, Job Docs, Data Flow, Development, Deployment, Operations, Configuration, Reference |
| **Data Pipeline** | Multi-stage processing | Overview, Architecture, Pipeline Arch, Stage Docs, Development, Deployment, Operations, Configuration, Reference |
| **Library/SDK** | Exported functions, packages | Overview, Architecture, API Reference, Usage Examples, Development, Deployment, Configuration, Reference |
| **CLI Tool** | Commands, subcommands | Overview, Architecture, Command Ref, Examples, Development, Deployment, Operations, Reference |
| **Web App** | Frontend, backend, UI | Overview, Architecture, Features Guide, User Docs, Development, Deployment, Operations, Configuration, Reference |

See `~/.copilot/instructions/confluence-documentation.instructions.md` for complete type classifications and page templates.

### Step 3: Generate Content

For each page, follow specifications in `~/.copilot/instructions/confluence-documentation.instructions.md` for that service type.

### Navigation
- **Single-Service**: Each page should have related pages at top and "Return to Overview" at bottom
- **Cross-Service**:
  - Parent/feature pages link DOWN to service pages
  - Service detail pages link UP to service parent and feature pages
  - Service pages link ACROSS to related services

## Example Page Hierarchies

### Single-Service: API Server
```
Project Documentation
├── Overview
├── Architecture
├── API Documentation        ← Type-specific
├── Integration Guide        ← Type-specific
├── Development
├── Deployment
├── Operations
├── Configuration
└── Reference
```

### Single-Service: Batch/ETL Process
```
Project Documentation
├── Overview
├── Architecture
├── Job Documentation        ← Type-specific
├── Data Flow               ← Type-specific
├── Development
├── Deployment
├── Operations
├── Configuration
└── Reference
```

### Single-Service: Web Application
```
Project Documentation
├── Overview
├── Architecture
├── Features Guide          ← Type-specific
├── User Documentation      ← Type-specific
├── Development
├── Deployment
├── Operations
├── Configuration
└── Reference
```

### Cross-Service: Feature Documentation
```
Negative List (Feature Parent)
├── Business Logic           ← Shared by all services
├── Enterprise Architecture  ← Shared by all services
│
├── API Negative List        ← Service A parent
│  ├── API Architecture      ← Service A detail (from API project)
│  ├── API Development       ← Service A detail (from API project)
│  ├── API Deployment        ← Service A detail (from API project)
│  └── API Operations        ← Service A detail (from API project)
│
├── Airflow Negative List    ← Service B parent
│  ├── Airflow DAGs          ← Service B detail (from Airflow project)
│  ├── Airflow Development   ← Service B detail (from Airflow project)
│  ├── Airflow Deployment    ← Service B detail (from Airflow project)
│  └── Airflow Operations    ← Service B detail (from Airflow project)
│
└── Reference               ← Shared by all services
```

See `~/.copilot/instructions/confluence-documentation.instructions.md` for all project types and their page hierarchies.

## Confluence Formatting Guidelines

### Headings
- Use `#` for page title (H1)
- Use `##` for major sections (H2)
- Use `###` for subsections (H3)
- Limit to 3 heading levels per page

### Content Organization
- **Keep sections short**: Each section should be 3-5 paragraphs maximum
- **Use bullet points** for lists and procedures
- **Bold key terms** for important concepts
- **Code blocks** with language specified (```python, ```bash, ```sql, etc.)
- **Tables** for comparisons or reference data
- **Info boxes** using > blockquote syntax for important notes

### Confluence-Specific Syntax

**Links between pages** (for Confluence):
```
[Page Name](page-link) or {link:Overview}
```

**Important notes** (blockquote):
```
> **Note:** This is important information
```

**Code blocks**:
````markdown
```python
# Code example
code_here()
```
````

**Tables** (simple and clean):
```markdown
| Column 1 | Column 2 | Column 3 |
| --- | --- | --- |
| Data A | Data B | Data C |
```

### Length Guidelines
- **Overview page**: 500-800 words
- **Other pages**: 800-1200 words each
- **Sections**: 100-200 words per section
- **Code examples**: 5-15 lines maximum

## Content Principles

1. **Conciseness**: Say more with less. Remove jargon where possible.
2. **Clarity**: Explain concepts before using them. Define acronyms on first use.
3. **Structure**: Use headings and white space to break up text.
4. **Progressive disclosure**: Basic concepts first, advanced details in subsections or "Further reading" links.
5. **Practical**: Include real examples, not just theory.
6. **Actionable**: Provide steps and commands users can actually run.
7. **Consistent**: Use same formatting and language across all pages.

## Page-Specific Guidelines

### Overview Page
- What is this project?
- What problem does it solve?
- Key features (3-5 bullets)
- Quick start (5-7 steps)
- Links to other pages for deeper dives

### Architecture Page
- System design diagram (ASCII or text description)
- Core concepts explained
- Component relationships
- Design patterns used (Strategy Pattern)
- Database support matrix

### API & Connections Page
- Supported databases with icons/labels
- Connection string format for each DB
- Basic connection example (in Python)
- Configuration requirements
- Connection pooling info

### Development Page
- Prerequisites (languages, tools, versions)
- Setup steps (4-6 steps)
- Running the application
- Running tests
- Common development tasks
- IDE setup (VS Code tips)

### Deployment Page
- Deployment overview (what gets deployed)
- Environment descriptions (dev, staging, prod)
- Deployment steps per environment
- Rollback procedures
- Monitoring after deployment
- Release checklist

### Operations Page
- Health checks and monitoring
- Common troubleshooting issues and solutions
- Backup and restore procedures
- Scheduled maintenance tasks
- Logging and diagnostics
- Escalation contacts

### Use Cases & Examples Page
- Real-world usage scenarios (3-5 scenarios)
- Code examples for each scenario
- Expected output/results
- Tips and best practices
- Links to full documentation for deep dives

### Configuration Page
- Environment variables table (name, purpose, example, required/optional)
- Configuration file structure
- Secrets management
- Environment-specific differences
- Configuration examples for each env

### Reference Page
- Folder structure (tree view)
- Glossary of terms
- Supported database matrix
- External links to detailed docs
- Troubleshooting flowchart (text-based)

## Output Format

For EACH page generated, provide:

```markdown
# Page Title

**Purpose**: One sentence describing this page's purpose

**Related Pages**: [Overview](overview) | [Architecture](architecture) | [API & Connections](api)

---

## Introduction
[2-3 sentence intro explaining what this page covers]

## Section 1
[Content here, 100-200 words]

## Section 2
[Content here, 100-200 words]

### Subsection 2.1
[If needed, brief subsection]

## [Continue with additional sections as needed]

---

**Return to**: [Main Documentation](root) | [Project Wiki](confluence-home)

**Last Updated**: [Date]
```

## Quality Checklist

Before finalizing each page, verify (also consult `~/.copilot/instructions/confluence-documentation.instructions.md` for complete checklist):

- [ ] Page title clearly describes content
- [ ] Introduction explains purpose and scope
- [ ] Content is organized into 4-6 main sections
- [ ] Each section is 100-200 words (not too long)
- [ ] Headings form logical hierarchy (max 3 levels)
- [ ] All code blocks have language specified
- [ ] Important notes are highlighted with blockquotes
- [ ] Tables are clean and easy to scan
- [ ] Related pages are linked at top and bottom
- [ ] No unexplained jargon or acronyms
- [ ] Practical examples included where relevant
- [ ] Page would fit on 2-3 printed pages
- [ ] Grammar and spelling correct
- [ ] Markdown is valid and properly formatted
- [ ] Blank lines surround code blocks, lists, headings
- [ ] Line length under 120 characters for readability
- [ ] Special characters properly escaped or use Unicode
- [ ] No headers skip levels (proper H1→H2→H3 hierarchy)
- [ ] All links use forward slashes and are valid
- [ ] No changelog/version history included
- [ ] No historical context or evolution mentioned

## Example Page Structure (Template)

### Generic Overview Page (All Projects)

```markdown
# Project Overview

**Purpose**: Project purpose, quick start, key features

**Related Pages**: [Architecture](architecture) | [Development](development)

---

## What is [Project Name]?

[1-2 sentences describing the project and its purpose]

## Key Features

- Feature 1: [brief description]
- Feature 2: [brief description]
- Feature 3: [brief description]

## Quick Start

[5-7 steps to get started]

## Technology Stack

| Component | Technology | Version |
| --- | --- | --- |
| Language | ... | ... |

## Where to Go Next

- Want to understand the architecture? → [Architecture](architecture)
- Ready to develop? → [Development Setup](development)
- Need to deploy? → [Deployment](deployment)

---

**Return to**: [Main Documentation](#) | **Next**: [Architecture](architecture)
```

### Type-Specific Example: API Server

For an API Server, replace generic "API & Connections" with "API Documentation":

```markdown
# API Documentation

**Purpose**: Complete API reference and contract

**Related Pages**: [Architecture](architecture) | [Integration Guide](integration) | [Configuration](configuration)

---

## API Overview

Base URL: `https://api.example.com/v1`
Authentication: OAuth2 / API Key / JWT

## Endpoints

### GET /api/users
[Request parameters, response schema, example]

### POST /api/users
[Request body schema, response, error codes]

## Error Handling

[Status codes, error response format]

---

**Return to**: [Main Documentation](#) | **Next**: [Integration Guide](integration)
```

### Type-Specific Example: Batch/ETL Process

```markdown
# Job Documentation

**Purpose**: Scheduled jobs and data pipeline definitions

**Related Pages**: [Architecture](architecture) | [Data Flow](data-flow) | [Configuration](configuration)

---

## Jobs Overview

| Job Name | Schedule | Purpose |
| --- | --- | --- |
| daily_sync | 0 2 * * * | Sync data from source |
| weekly_report | 0 9 * * MON | Generate weekly report |

## Daily Sync Job

- **Schedule**: 2 AM UTC daily
- **Input**: Source database table
- **Output**: Data warehouse table
- **Duration**: ~15 minutes
- **On Failure**: Retry 3 times, alert on-call

---

**Return to**: [Main Documentation](#) | **Next**: [Data Flow](data-flow)
```

For other project types, see `~/.copilot/instructions/confluence-documentation.instructions.md` for specific page templates.

## Implementation Guidelines

When generating pages:

0. **Extract system name from prompt input** - FIRST decision:
   - System name is passed to this prompt (e.g., "Obligor", "Negative List")
   - Slug format for filenames: lowercase, hyphens (e.g., "obligor", "negative-list")
   - Determine service type from current project using Step 0b auto-detection

1. **Check for Existing Documentation** - Important first step:
   - Look in `/docs/confluence/` for any existing `.md` files
   - **For parent pages** (01-*, 02-*, 04-*):
     - If they exist: Do NOT regenerate, do NOT modify
     - They belong to the system, not this individual service
     - Only the first service (or architect) should create them
   - **For this service's pages** (03-{service}-*, 03a-*, 03b-*, 03c-*, 03d-*):
     - If they exist: Update them with current project state
     - If they don't exist: Create them
     - These are specific to THIS service
   - **For reference page** (04-*):
     - If it exists: Append this service's entries to service matrix and glossary
     - Do NOT delete or overwrite other services' entries
     - If it doesn't exist: Create it with this service included
   - Update modification dates in regenerated files
   - Ensure regenerated docs reflect current codebase state only

2. **Identify Service Type and Architecture** - First substantive step:
   - Use auto-detection from Step 0b
   - Analyze the project structure, purpose, and code
   - Match to one of the supported project types in `.github/instructions/confluence-documentation.instructions.md`
   - This determines the content and sections for service pages

3. **Generate Parent Page Stubs** (if not already existing):
   - Create `01-{system-slug}-business-logic.md` as template for domain expert
     - Include structure and placeholder sections
     - Mark clearly as template to be filled
     - Link to this service's pages for reference
   - Create `02-{system-slug}-enterprise-architecture.md` as template for architect
     - Include structure showing service interactions
     - Add placeholder for this service's role
     - Mark clearly as template to be filled
   - See `.github/instructions/confluence-documentation.instructions.md` for templates

4. **Follow Type-Specific Specifications** - Reference `~/.copilot/instructions/confluence-documentation.instructions.md` for:
   - Detailed page-by-page specifications for YOUR service type
   - What sections each page should contain (Overview, Architecture, Development, Deployment, Operations)
   - Word counts and content guidelines
   - Navigation and linking structure
   - Complete quality checklist

5. **Apply Markdown Standards** - Follow awesome-copilot [Markdown Content Rules](https://github.com/github/awesome-copilot/blob/main/instructions/markdown-content-rules.instructions.md) and [GitHub Flavored Markdown (GFM)](https://github.com/github/awesome-copilot/blob/main/instructions/github-flavored-markdown.instructions.md)

6. **Follow Documentation Organization** - Reference `~/.copilot/instructions/readme-creation.instructions.md` for organization patterns

2. **Identify Documentation Type** - First substantive step:
   - **Single-Service**: Analyze the project structure, purpose, and code
     - Match to one of the supported project types in `~/.copilot/instructions/confluence-documentation.instructions.md`
     - This determines which pages to generate (7-9 pages)
     - Do not force-fit the project into a generic template
   - **Cross-Service**: Identify your role:
     - **Feature Architect**: Generate business logic + enterprise architecture + service parent stubs
     - **Service Team**: Generate service parent page (introduction) + 4 service detail pages (architecture, development, deployment, operations)

3. **Generate Parent Page Stubs** (if not already existing):
   - Create `01-{system-slug}-business-logic.md` as template for domain expert
     - Include structure and placeholder sections
     - Mark clearly as template to be filled
     - Link to this service's pages for reference
   - Create `02-{system-slug}-enterprise-architecture.md` as template for architect
     - Include structure showing service interactions
     - Add placeholder for this service's role
     - Mark clearly as template to be filled
   - See `~/.copilot/instructions/confluence-documentation.instructions.md` for templates

4. **Follow Type-Specific Specifications** - Reference `~/.copilot/instructions/confluence-documentation.instructions.md` for:
   - Detailed page-by-page specifications for YOUR service type
   - What sections each page should contain (Overview, Architecture, Development, Deployment, Operations)
   - Word counts and content guidelines
   - Navigation and linking structure
   - Complete quality checklist

5. **Apply Markdown Standards** - Follow awesome-copilot [Markdown Content Rules](https://github.com/github/awesome-copilot/blob/main/instructions/markdown-content-rules.instructions.md) and [GitHub Flavored Markdown (GFM)](https://github.com/github/awesome-copilot/blob/main/instructions/github-flavored-markdown.instructions.md) for:
   - Fenced code blocks with language identifiers
   - Blank lines around blocks, lists, headings
   - Proper heading hierarchy (no skipped levels)
   - Link formatting and validation
   - Line length limits (max 120 characters for Confluence)
   - Special character handling
   - Table formatting

6. **Follow Documentation Organization** - Reference `~/.copilot/instructions/readme-creation.instructions.md` for:
   - Content focus principles (what to include/exclude)
   - File consolidation strategies (for reference on structuring content)
   - Documentation organization patterns

7. **Current State Only** - Critical requirement:
   - Document only what exists in the codebase NOW
   - No historical context, evolution, or past decisions
   - **Explicitly exclude**:
     - Statements like "replaces the previous...", "replaced...", "formerly...", "previously..."
     - References to old architectures: "was Airflow-based", "used to use", "before we..."
     - Justifications based on history: "to eliminate the old...", "improving from..."
     - Mentions of development iterations or changes not in current code
   - **Rewrite historical statements** to current-state form:
     - ❌ "Replaces the split-consumer architecture with unified approach"
     - ✅ "Uses a unified consumer architecture for..."
     - ❌ "Enables sub-second latency, replacing Airflow scheduling"
     - ✅ "Provides sub-second latency for updates via event-driven processing"
   - If code comments/docstrings contain evolutionary narrative, extract only the current functionality description
   - Focus on: "This system IS" not "This system REPLACED"
   - Reflect current architecture, current dependencies, current file structure

## Ready to Generate

Now:

1. **System name**: Extract from prompt input parameter
2. **Service type**: Use auto-detection from Step 0b
3. **Check existing docs**: Follow Step 1 to see what already exists
4. **Generate parent stubs**: If first service, create 01 and 02 templates
5. **Generate service pages**: Always create 03, 03a, 03b, 03c, 03d for THIS service
6. **Update reference page**: Append this service to 04-reference.md
7. **Apply formatting standards**: Consult confluence-documentation.instructions.md for page layout and structure best practices
8. **Validate against checklist**: Use the quality checklist in confluence-documentation.instructions.md before finalizing

**Key Principles**:
- Document THIS service's role within the system
- Parent pages are TEMPLATES for others to fill (not your responsibility)
- Never delete or modify other services' documentation
- Service pages are unique to this project; other services have their own copies
- Reference page grows as more services are added
