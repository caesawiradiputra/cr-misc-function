# Common Awesome-Copilot References

All project types (API Service, Data Pipeline, Consumer App, Library) use these common awesome-copilot references as a foundation. Add project-type-specific references on top of these.

---

## Core Development Standards

These apply to all projects, regardless of type:

- **[Code Generation Guidelines](https://github.com/github/awesome-copilot/blob/main/instructions/code-generation-guidelines.instructions.md)**
  - Best practices for AI-assisted code generation
  - When to use generated code vs. hand-written code
  - How to review and validate generated code

- **[Security Standards (OWASP Top 10 2025)](https://github.com/github/awesome-copilot/blob/main/instructions/security-standards.instructions.md)**
  - Common security vulnerabilities and mitigations
  - Secure coding practices
  - Authentication, authorization, data protection

- **[AI Prompt Engineering & Safety Best Practices](https://github.com/github/awesome-copilot/blob/main/instructions/ai-prompt-engineering-safety-best-practices.instructions.md)**
  - How to write effective prompts for AI assistants
  - Safety considerations when using AI for code generation
  - Quality checks and validation

---

## Documentation & Communication

These apply to all projects:

- **[Markdown Content Rules](https://github.com/github/awesome-copilot/blob/main/instructions/markdown-content-rules.instructions.md)**
  - Standards for writing README files
  - Documentation structure and formatting
  - Best practices for technical writing

- **[GitHub Flavored Markdown (GFM)](https://github.com/github/awesome-copilot/blob/main/instructions/github-flavored-markdown.instructions.md)**
  - GFM syntax and features
  - Code block formatting
  - Tables, lists, and other markdown elements

---

## Version Control & CI/CD

These apply to all projects:

- **[GitHub Actions CI/CD Best Practices](https://github.com/github/awesome-copilot/blob/main/instructions/github-actions-ci-cd-best-practices.instructions.md)**
  - Workflow configuration best practices
  - Common CI/CD patterns
  - Testing, linting, and deployment automation

---

## How to Use These References

1. **Start with the core references above** - they apply to every project
2. **Add language-specific references** - pick references matching your language (Python, JavaScript, etc.)
3. **Add framework-specific references** - add references for your framework (FastAPI, React, Django, etc.)
4. **Add domain-specific references** - add references for your project type (API, pipeline, app, library)

**Example**: For a Python FastAPI service:

```text
✅ Core Standards (Code Generation, Security, AI Prompt Engineering)
✅ Documentation (Markdown, GFM)
✅ CI/CD (GitHub Actions)
✅ Language: Python Development
✅ Framework: FastAPI Best Practices
✅ Domain: API Design, Error Handling, Testing
```

---

## For Each Project Type

See the workflow files for type-specific references:

- **API Service**: [api-service.md](./workflows/api-service.md)
  - API design, error handling, request validation
  - Authentication, performance, testing

- **Data Pipeline**: [data-pipeline.md](./workflows/data-pipeline.md)
  - ETL patterns, data validation, job orchestration
  - Airflow, data quality, monitoring

- **Consumer App**: [consumer-app.md](./workflows/consumer-app.md)
  - Component design, state management, API integration
  - Testing, performance, accessibility

- **Library**: [library.md](./workflows/library.md)
  - Public API, testing, documentation
  - Package distribution, backward compatibility

---

## Finding New References

To discover additional awesome-copilot references relevant to your project:

1. Visit [awesome-copilot GitHub](https://github.com/github/awesome-copilot/blob/main/instructions/)
2. Browse available `.instructions.md` files
3. Read the descriptions to find relevant references for your project type
4. Add them to the appropriate section in your `copilot-instructions.md`

---

## Notes

- **No task-specific mappings**: References are listed only for discovery; Copilot uses the precedence chain automatically
- **Awesome-copilot is authoritative**: When in doubt, defer to awesome-copilot references
- **Project-type matters**: Different project types emphasize different references
- **Keep it focused**: List only references relevant to YOUR project; avoid adding unrelated references
