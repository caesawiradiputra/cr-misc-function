# API Service Workflow

**Project Type**: REST/GraphQL/gRPC API services, backend services handling requests

**Applies to**: Services that expose endpoints for other applications to consume

**Key Focus**: API design, request/response validation, error handling, authentication

---

## Workflow Steps

### 1. Analyze the API Service

Read these files to understand the service:

- `README.md` - What does this API do?
- `pyproject.toml` or equivalent - What framework? (FastAPI, Flask, Django, Express, etc.)
- Folder structure - How are endpoints organized?
- API documentation - What endpoints exist?
- Configuration - How is it configured (env vars, config files)?

**Questions to answer**:

- What is the main purpose of this API?
- What framework/language is used?
- What are the main endpoints or domains it handles?
- Does it use authentication? Database? External services?
- What are the code organization patterns?

---

### 2. Fill Project Identity Section

Update the `PROJECT CONTEXT` section in `[projectWorkspace]/.github/copilot-instructions.md`:

```markdown
**Project Name**: [Actual service name, e.g., "order-service", "user-api"]

**Description**: [1-2 sentences describing what the API does and handles]
Example: "REST API service for managing user orders, handling order creation, updates, retrieval, and status tracking."

**Project Type**: API Service

**Language**: Python 3.9+ (or Node.js, Go, etc.)
**Framework**: FastAPI (or Flask, Django, Express, etc.)
**Key Dependencies**: [List main deps, e.g., "FastAPI, SQLAlchemy, Pydantic, pytest"]
```

---

### 3. Add Project-Specific Patterns

Document unique conventions for THIS API service:

```markdown
**Project-Specific Patterns & Conventions**:
- API Design: RESTful endpoints with versioning (e.g., `/api/v1/orders`)
- Request/Response: Pydantic models for validation, JSON responses with standard error format
- Authentication: JWT tokens with bearer scheme, validated on protected endpoints
- Error Handling: Consistent error responses with status codes and error codes
- Logging: Structured logging with request tracing, correlation IDs for debugging
- Testing: Unit tests for handlers, integration tests for endpoints, min 80% coverage
- Database: SQLAlchemy ORM with async support, migrations managed by Alembic
- Code Style: Black formatting, mypy type checking, ruff linting
- Documentation: OpenAPI/Swagger docs auto-generated from models
- Async Patterns: Uses async/await for I/O operations
```

---

### 4. Select Awesome-Copilot References

**Always include these** (all projects):

- Code Generation Guidelines
- Security Standards (OWASP)
- AI Prompt Engineering & Safety
- Markdown Content Rules
- GitHub Flavored Markdown
- GitHub Actions CI/CD Best Practices

**Add these for Python API services**:

- [Python Development](https://github.com/github/awesome-copilot/blob/main/instructions/python.instructions.md)

**Add these if applicable**:

- [API Design Best Practices](https://github.com/github/awesome-copilot/blob/main/instructions/api-design.instructions.md) ← For API architecture
- [Database Access Patterns](https://github.com/github/awesome-copilot/blob/main/instructions/database-access.instructions.md) ← If uses database
- [Authentication & Authorization](https://github.com/github/awesome-copilot/blob/main/instructions/authentication.instructions.md) ← If has auth
- [Error Handling Best Practices](https://github.com/github/awesome-copilot/blob/main/instructions/error-handling.instructions.md) ← For structured errors

- [Testing Best Practices](https://github.com/github/awesome-copilot/blob/main/instructions/testing.instructions.md) ← For unit/integration tests
- [Performance & Optimization](https://github.com/github/awesome-copilot/blob/main/instructions/performance-optimization.instructions.md) ← If performance-critical

**Example reference section**:

```markdown
### Language/Framework-Specific References

**For Python projects**:
- [Python Development](https://github.com/github/awesome-copilot/blob/main/instructions/python.instructions.md)

**For REST API services**:
- [API Design Best Practices](https://github.com/github/awesome-copilot/blob/main/instructions/api-design.instructions.md)
- [Error Handling & Status Codes](https://github.com/github/awesome-copilot/blob/main/instructions/error-handling.instructions.md)

**For authentication**:
- [Authentication & Authorization Patterns](https://github.com/github/awesome-copilot/blob/main/instructions/authentication.instructions.md)

**For database operations**:
- [Database Access Patterns](https://github.com/github/awesome-copilot/blob/main/instructions/database-access.instructions.md)

**For testing**:
- [Testing Best Practices](https://github.com/github/awesome-copilot/blob/main/instructions/testing.instructions.md)
```

---

### 5. Document Project-Specific Instructions

If your API has special instructions in `.github/instructions/`, document them:

```markdown
## Project-Specific Instructions & Files

This API service has the following project-specific instructions:

**api-handler-patterns.md**
- Description: Guidelines for writing request handlers and endpoint definitions
- When to use: When adding new endpoints or modifying request handling logic
- Location: `.github/instructions/api-handler-patterns.md`

**database-operations.md**
- Description: Standards for database queries, migrations, and data access patterns

- When to use: When working with the database layer or ORM
- Location: `.github/instructions/database-operations.md`
```

If no special instructions:

```markdown
## Project-Specific Instructions & Files

This API service follows standard Python/FastAPI conventions. See the awesome-copilot references above for detailed guidance on API design, testing, and error handling.
```

---

### 6. Validate Changes

**Checklist**:

- [ ] Service name is accurate (e.g., "order-service", not "[PROJECT_NAME]")
- [ ] Description explains what the API does (1-2 sentences)
- [ ] Project Type is "API Service"
- [ ] Language and Framework are correctly specified
- [ ] Tech Stack includes key dependencies (FastAPI, SQLAlchemy, Pydantic, etc.)
- [ ] Project-Specific Patterns describe actual conventions (endpoints, auth, error handling)
- [ ] All awesome-copilot links are correct and applicable to API services
- [ ] Entry Point Information section was NOT modified
- [ ] No task-specific file mappings added
- [ ] All sections are filled (no empty placeholders remain)

---

### 7. Update Metadata

Change the Last Updated section at the bottom:

```markdown
## Last Updated

- **Date**: April 22, 2026
- **Status**: Project context complete
- **Author**: GitHub Copilot

```

---

## Example: Order Management API

**Before**:

```markdown
**Project Name**: [PROJECT_NAME]


**Description**: [DESCRIBE PROJECT HERE]

**Project Type**: [API Service / Consumer App / Data Pipeline / Library / Other]

**Language**: [e.g., Python 3.9+]
```

**After**:

```markdown
**Project Name**: order-service

**Description**: REST API service for managing user orders, including creation, updates, cancellations, and status tracking.


**Project Type**: API Service

**Language**: Python 3.9+
**Framework**: FastAPI with async support
**Key Dependencies**: FastAPI, SQLAlchemy, Pydantic, pytest, pytest-asyncio
```

**Project-Specific Patterns Example**:

```markdown
**Project-Specific Patterns & Conventions**:
- Endpoints: RESTful with `/api/v1/` prefix; separate routers for each domain (orders, users, payments)

- Request/Response: Pydantic models for validation; consistent JSON response format with data/error fields
- Authentication: JWT bearer tokens, validated with FastAPI dependencies; roles-based access control
- Error Handling: StandardError response with code, message, details; HTTP status codes aligned with semantics
- Logging: Structured logging with correlation IDs; request tracing for debugging; async-safe logging
- Database: SQLAlchemy with async engine; Alembic migrations; connection pooling configured per environment
- Testing: Unit tests for services, integration tests for endpoints; min 85% coverage; fixtures for database/auth
- Code Quality: Black formatter, mypy strict mode, ruff linter; pre-commit hooks enforced
```

**References Example**:

```markdown
### Language/Framework-Specific References

**For Python projects**:
- [Python Development](https://github.com/github/awesome-copilot/blob/main/instructions/python.instructions.md)

**For REST API services**:
- [API Design Best Practices](https://github.com/github/awesome-copilot/blob/main/instructions/api-design.instructions.md)
- [Error Handling & HTTP Status Codes](https://github.com/github/awesome-copilot/blob/main/instructions/error-handling.instructions.md)

**For authentication & security**:
- [Authentication & Authorization](https://github.com/github/awesome-copilot/blob/main/instructions/authentication.instructions.md)

**For database**:
- [SQLAlchemy ORM Best Practices](https://github.com/github/awesome-copilot/blob/main/instructions/sqlalchemy.instructions.md)

**For testing**:
- [Pytest Best Practices](https://github.com/github/awesome-copilot/blob/main/instructions/pytest.instructions.md)
```

---

## Success Criteria

✅ Service name, description, and type accurately reflect this API
✅ Language and Framework are correctly specified
✅ Tech Stack lists actual dependencies and technologies
✅ Project-Specific Patterns describe real API conventions (endpoints, auth, error handling, async patterns)
✅ All placeholder text `[EXAMPLE]` is replaced with actual values
✅ Awesome-copilot references are relevant to API service development
✅ Entry Point Information section was NOT modified
✅ Last Updated date is current
✅ No task-specific file mappings were added
✅ Documentation is specific to this service's architecture

---

## Tips for API Services

- **Versioning**: Mention API versioning strategy (URL prefix, header-based, etc.)
- **Authentication**: Clearly document the auth mechanism (JWT, OAuth, API keys, etc.)
- **Error Format**: Describe the standardized error response format
- **Async**: Note if service uses async/await or synchronous patterns
- **Rate Limiting**: Mention if there are rate limiting requirements
- **Documentation**: Reference OpenAPI/Swagger if auto-generated
