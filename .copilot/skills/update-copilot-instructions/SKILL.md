---
name: 'update-copilot-instructions'
description: 'Update project copilot instructions with project context and awesome-copilot references'
---

# Update Project Copilot Instructions Skill

**Purpose**: Customize `[projectWorkspace]/.github/copilot-instructions.md` with accurate project context and relevant awesome-copilot references.

**Scope**: Scans the current project workspace, identifies project type, and fills in all template placeholders with project-specific information.

---

## Decision Tree: Which Workflow?

Start here to find the right workflow for your project type.

### 1. What is your project's primary purpose?

**API Service** (REST/GraphQL/gRPC endpoints)
- FastAPI, Flask, Django, Express, etc.
- Handles HTTP requests, returns responses
- Focus: API design, request/response validation
- → See [API Service Workflow](./workflows/api-service.md)

**Data Pipeline** (ETL, batch processing, Airflow)
- Apache Airflow, dbt, Pandas, PySpark, Kubernetes jobs
- Processes/transforms data in batches or workflows
- Focus: Data flow, job orchestration, error handling
- → See [Data Pipeline Workflow](./workflows/data-pipeline.md)

**Consumer App** (Web frontend, mobile, CLI client)
- React, Vue, Angular, Flutter, mobile apps, CLIs
- Consumes APIs or other services
- Focus: UI/UX, state management, user interaction
- → See [Consumer App Workflow](./workflows/consumer-app.md)

**Library** (Reusable code, utilities, SDK)
- Utility functions, helper modules, packages
- Consumed by other projects as dependencies
- Focus: Public API, testing, documentation
- → See [Library Workflow](./workflows/library.md)

**Other**
- Doesn't fit above categories
- Monorepo, specialized service, internal tool
- → Adapt closest workflow or use [Library Workflow](./workflows/library.md) as base

---

## Common Steps (All Workflows)

Every workflow follows these foundational steps:

1. **Analyze the Project**
   - Read `README.md`, `pyproject.toml`, package manifest
   - Scan folder structure to understand purpose
   - Identify key technologies and dependencies

2. **Review Current Template**
   - Open `[projectWorkspace]/.github/copilot-instructions.md`
   - Check which placeholders need filling:
     - `[PROJECT_NAME]`
     - `[DESCRIBE PROJECT HERE]`
     - `[API Service / Consumer App / Data Pipeline / Library / Other]`
     - Tech stack sections
     - Project-Specific Patterns

3. **Fill Project Identity Section**
   - Replace placeholders with actual values
   - No more `[EXAMPLE]` text after completion

4. **Update Tech Stack Section**
   - Primary language and version
   - Main frameworks/libraries
   - Key dependencies

5. **Validate Changes**
   - No task-specific file mappings added
   - Entry Point Information NOT modified
   - All awesome-copilot links are correct
   - Descriptions match actual project purpose

6. **Update Metadata**
   - Change Last Updated date to today
   - Update Author if different

---

## Workflow Selection Summary

| Project Type | Best For | Read This |
|---|---|---|
| REST API, GraphQL, gRPC services | Backend services handling requests | [API Service Workflow](./workflows/api-service.md) |
| ETL, batch processing, Airflow DAGs | Data movement and transformation | [Data Pipeline Workflow](./workflows/data-pipeline.md) |
| Web/mobile frontends, CLI tools | Apps consuming APIs/services | [Consumer App Workflow](./workflows/consumer-app.md) |
| Utilities, helpers, SDK packages | Code reused across projects | [Library Workflow](./workflows/library.md) |

---

## Common References

All project types use these awesome-copilot references. See [references.md](./references.md) for details:

- **Core Development Standards**
  - Code Generation Guidelines
  - Security Standards (OWASP)
  - AI Prompt Engineering & Safety

- **Documentation & Communication**
  - Markdown Content Rules
  - GitHub Flavored Markdown (GFM)

- **Version Control & CI/CD**
  - GitHub Actions CI/CD Best Practices

---

## Next Steps

1. **Identify** your project type (see Decision Tree above)
2. **Open** the corresponding workflow file
3. **Follow** the workflow steps specific to your project
4. **Validate** using the success criteria in the workflow
5. **Commit** changes with appropriate message

---

## File Organization

```
.github/skills/update-copilot-instructions/
├── SKILL.md                         ← YOU ARE HERE
├── workflows/
│   ├── api-service.md              ← For REST/GraphQL/gRPC APIs
│   ├── data-pipeline.md            ← For ETL/Airflow/batch processing
│   ├── consumer-app.md             ← For web/mobile/CLI clients
│   └── library.md                  ← For utilities/SDKs
└── references.md                   ← Common awesome-copilot refs
```

---

## Do NOT Change

When using any workflow, remember:

- ❌ **Entry Point Information** section in copilot-instructions.md (immutable)
- ❌ **Precedence Chain** section (static 3-level fallback)
- ❌ **How Copilot Uses This File** section
- ❌ **File Organization** diagram
- ❌ Never add task-specific file mappings
- ❌ Don't add custom sections; only fill placeholders

---

## Tips

- **Unsure about your project type?** Read the descriptions in the Decision Tree. Pick the closest match.
- **Multiple project purposes?** Pick the PRIMARY purpose (main service/focus).
- **Still confused?** Start with [Library Workflow](./workflows/library.md) as a safe baseline.
- **Need framework-specific references?** Check the workflow file for your project type; it lists relevant awesome-copilot links.

---

## Questions?

Each workflow file has:
- ✅ Detailed step-by-step instructions
- ✅ Example before/after updates
- ✅ Type-specific awesome-copilot references
- ✅ Success criteria for validation
