---
description: 'Guidelines for creating Confluence-ready documentation with hierarchical structure. All projects are part of a business system/feature with auto-detected service types.'
applyTo: '**/docs/confluence/**/*.md'
---

# Confluence Documentation Guidelines

## Core Principle: All Projects Are Part of a System

**Assume every project is part of a business system or feature.** A project like "da-obligor-api" is always part of the "Obligor" system. This creates a hierarchical documentation structure:

- **Parent pages** (01, 02): Business logic + enterprise architecture (shared by all services in this system)
- **Service pages** (03, 03a-d, 04): This project's implementation details
- **Reference page** (04): Shared glossary and service matrix (grows as services are added)

**This structure works whether you have:**
- 1 service (just this project)
- Multiple services in the same system (Obligor API + Obligor Airflow + Obligor Consumer)
- Services added later (new services reuse the same parent pages)

## Critical Instruction

**Generate documentation ONLY from the current project state.** Analyze the existing codebase, files, and architecture as they are now. Do not reference, mention, or document any historical changes, previous versions, or reasons for implementation decisions. Document what exists today.

---

## Hierarchical File Structure (Always Used)

### Example: "Negative List" System with Multiple Services

**All services reuse the same parent pages (01, 02) and reference page (04). Each service has its own detail pages (03a-d).**

```
01-negative-list-business-logic.md
   (What is Negative List, Why, Business rules - shared)

02-negative-list-enterprise-architecture.md
   (How services interact, Data flows - shared)

03-negative-list-api-overview.md (from API project)
├── 03a-negative-list-api-architecture.md
├── 03b-negative-list-api-development.md
├── 03c-negative-list-api-deployment.md
└── 03d-negative-list-api-operations.md

03-negative-list-airflow-overview.md (from Airflow project)
├── 03a-negative-list-airflow-architecture.md
├── 03b-negative-list-airflow-development.md
├── 03c-negative-list-airflow-deployment.md
└── 03d-negative-list-airflow-operations.md

03-negative-list-consumer-overview.md (from Consumer project)
├── 03a-negative-list-consumer-architecture.md
├── 03b-negative-list-consumer-development.md
├── 03c-negative-list-consumer-deployment.md
└── 03d-negative-list-consumer-operations.md

04-negative-list-reference.md
   (Service matrix, glossary - shared by all)
```

**Key Benefit**: Each service uses the same page numbers (03, 03a-d). No renumbering needed when adding new services. Services have distinct filenames via {system-slug}-{service-name} pattern.

### File Naming Convention

**Format**: `{page#}-{system-slug}-{service-name}-{section}.md`

**System slug**: Lowercase with hyphens ("Obligor" → "obligor", "Negative List" → "negative-list")

**Examples**:
- Parent pages: `01-obligor-business-logic.md`, `02-obligor-enterprise-architecture.md`
- Service pages (API): `03-obligor-api-overview.md`, `03a-obligor-api-architecture.md`
- Service pages (Airflow): `03-obligor-airflow-overview.md`, `03a-obligor-airflow-architecture.md`
- Service pages (Consumer): `03-obligor-consumer-overview.md`, `03a-obligor-consumer-architecture.md`
- Reference: `04-obligor-reference.md`

### Confluence Page Hierarchy in UI

In Confluence, structure appears as:

```
Obligor (System - root page)
├─ Business Logic (01 - shared)
├─ Enterprise Architecture (02 - shared)
├─ API Service (03 - overview)
│  ├─ API Architecture (03a - detail)
│  ├─ API Development (03b - detail)
│  ├─ API Deployment (03c - detail)
│  └─ API Operations (03d - detail)
├─ Airflow Service (03 - overview)
│  ├─ Airflow Architecture (03a - detail)
│  ├─ Airflow Development (03b - detail)
│  ├─ Airflow Deployment (03c - detail)
│  └─ Airflow Operations (03d - detail)
└─ Reference (04 - shared)
```

**Breadcrumbs**:
- Business Logic page: `Obligor > Business Logic`
- API Architecture page: `Obligor > API Service > API Architecture`
- Airflow Operations page: `Obligor > Airflow Service > Airflow Operations`

---

## Service Type Classification

Identify the current project's service type. This determines which sections to include in pages 03, 03a, 03b, 03c, 03d:

### Supported Project Types

| Project Type | Purpose | Key Documentation |
| --- | --- | --- |
| **API Server** | REST/GraphQL/gRPC API | API Documentation, Integration Guide, Webhooks |
| **Web Application** | Frontend/Backend web app | Features Guide, User Documentation, Frontend Architecture |
| **Batch/ETL Process** | Data pipeline, scheduled jobs | Job Documentation, Data Flow, Transformation Logic |
| **Airflow Orchestration** | Orchestrated workflows | DAG Documentation, Task Dependencies, Schedule/SLAs |
| **Streaming Consumer** | Event/message consumer | Consumer Documentation, Event Schemas, Processing Logic |
| **Streaming Producer** | Event/message producer | Producer Documentation, Event Schema, Emission Patterns |
| **Library/SDK** | Reusable code library | API Reference, Usage Examples, Integration Patterns |
| **Data Pipeline** | Complex multi-stage ETL | Pipeline Architecture, Stage Documentation, Data Flow |
| **CLI Tool** | Command-line utility | Command Reference, Subcommands, Usage Examples |
| **Service (Generic)** | General backend service | Service Architecture, Endpoints/Jobs, Integration Points |

---

## Service Pages Structure (Always 5 Pages)

**Every service generates 5 pages** (03, 03a, 03b, 03c, 03d) with consistent purposes:

### 03 - Service Overview

**Audience**: Other teams, external users, non-technical stakeholders

**Purpose**: How to use this service (not how it's built). Focus on access methods, environments, and usage patterns.

**Content**:
- What does this service do? (user-facing description, not technical details)
- How to access it (endpoints, proxies, authentication)
- Available environments (SIT/UAT, Production) with endpoints
- For APIs: Access flow through Apigee Gateway → Internal Gateway → Backend
- Quick start / common use cases
- Links to authentication, API reference, and detailed docs

**Note**: Omit internal technical details (ports, tech stack, architecture) unless relevant to usage. This page is for teams that *use* the service, not teams that *build* it.

### 03a - Service Architecture
- Technical design specific to this service
- Components and dependencies
- Service-type-specific details:
  - **API Server**: Endpoints, request/response schemas
  - **Airflow**: DAG structure, task dependencies
  - **Consumer**: Event schemas, processing logic
  - **Batch/ETL**: Job definitions, data transformations
  - **Library**: API reference, exported functions
  - **Web App**: Feature overview, user workflows

### 03b - Development
- Local setup and prerequisites
- Development workflow
- Testing strategies
- Common development tasks

### 03c - Deployment
- Environment descriptions (dev, staging, prod)
- Deployment procedures
- Rollback procedures
- Environment-specific configuration

### 03d - Operations
- Monitoring and health checks
- Common troubleshooting scenarios
- Scheduled maintenance
- Logging and diagnostics
- Escalation contacts

### Plus: Parent Pages (01, 02) and Reference (04)

These are shared by all services in the system (generated once by first service or architect):
- **01-{system-slug}-business-logic.md** - What the feature/system does at business level
- **02-{system-slug}-enterprise-architecture.md** - How services interact, data flows
- **04-{system-slug}-reference.md** - Glossary, service matrix, cross-service runbooks

---

## Shared System Pages: Business Logic and Enterprise Architecture

All services in a system share these two parent pages (generated once by first service or architect, then reused):

### 01 - Business Logic Page (500-1000 words)

**Purpose**: Executive summary - what the system does at business level

**Sections**:
- What is this feature/system?
- Why do we have it? (business value, problem solved)
- Key business rules (validation rules, constraints)
- Which services are involved? (table: Service Name | Purpose | Status)
- Common use cases
- RACI or ownership matrix

**Audience**: Product managers, business analysts, architects

**Example structure**:
```markdown
# {System} - Business Logic

## What is {System}?

[Business description]

## Business Rules

- Rule 1: [Non-technical description]
- Rule 2: [Non-technical description]

## Services Involved

| Service | Purpose | Team | Status |
| --- | --- | --- | --- |
| API Service | [Purpose] | [Team] | Active |
| Airflow Service | [Purpose] | [Team] | Active |

## Common Use Cases

1. [Use case with business context]
2. [Use case with business context]

---

**Next**: [Enterprise Architecture](02-enterprise-architecture) or jump to specific service docs
```

### 02 - Enterprise Architecture Page (800-1200 words)

**Purpose**: Enterprise-level architecture - how services interact and stay in sync

**Sections**:
- System architecture diagram (ASCII or text description)
- Service interaction flows
- Data consistency model (how services stay in sync)
- Key architectural decisions
- Service communication patterns
- Failure scenarios and resilience

**Audience**: Architects, tech leads, senior developers

**Example structure**:
```markdown
# {System} - Enterprise Architecture

## System Architecture

[ASCII diagram showing all services and interactions]

## Service Interaction Flow

1. [Service A does X]
2. [Publishes to event stream]
3. [Service B consumes event]
4. [Updates shared database]

## Data Consistency Model

[Explanation of sync strategy: real-time, batch, eventual consistency]

---

**To understand specific services**, see:
- [API Service Architecture](03a-{system}-api-architecture)
- [Airflow Architecture](03a-{system}-airflow-architecture)
```

---

## Documentation Organization Strategy

### Hierarchical Structure (Always Used)

This structure accommodates 1 service (just this project) or multiple services (with shared parent pages):

For **"Obligor" system with multiple services**:

```
01-obligor-business-logic.md (shared)
02-obligor-enterprise-architecture.md (shared)

03-obligor-api-overview.md (from API project)
├── 03a-obligor-api-architecture.md
├── 03b-obligor-api-development.md
├── 03c-obligor-api-deployment.md
└── 03d-obligor-api-operations.md

03-obligor-airflow-overview.md (from Airflow project)
├── 03a-obligor-airflow-architecture.md
├── 03b-obligor-airflow-development.md
├── 03c-obligor-airflow-deployment.md
└── 03d-obligor-airflow-operations.md

04-obligor-reference.md (shared)
```

For **"Obligor" system with just API service** (one project):

```
01-obligor-business-logic.md (template - to be filled)
02-obligor-enterprise-architecture.md (template - to be filled)

03-obligor-api-overview.md
├── 03a-obligor-api-architecture.md
├── 03b-obligor-api-development.md
├── 03c-obligor-api-deployment.md
└── 03d-obligor-api-operations.md

04-obligor-reference.md (just this service)
```

**Key Principle**: Structure stays the same. New services just add their own 03/03a-d pages. Parent pages stay constant.

**Purpose**: Executive summary for non-technical stakeholders and architects

**Sections**:
- What is this feature? (business description, not technical)
- Why do we have it? (business value, problem solved)
- Key business rules (validation rules, business constraints)
- Which services are involved? (table: Service Name | Purpose | Status)
- Data flow overview (simple, business-focused diagram)
- Common use cases
- Who should own this feature? (RACI chart if applicable)

**Audience**: Product managers, business analysts, architects, tech leads

**Example**:
```markdown
# Negative List - Business Logic

**Related**: [Architecture](negative-list-architecture) | [API Service](api-negative-list) | [Airflow Process](airflow-negative-list) | [Sync Consumer](sync-negative-list)

## What is Negative List?

[Business description: The negative list is a system that...]

## Business Rules

- Rule 1: [Non-technical description]
- Rule 2: [Non-technical description]
- Rule 3: [Non-technical description]

## Services Involved

| Service | Purpose | Team | Status |
| --- | --- | --- | --- |
| API Negative List | REST API for query/update | Platform Team | Active |
| Airflow Negative List | Daily batch sync | Data Ops | Active |
| Consumer Negative List | Event-based sync | Integration Team | Active |

## Common Use Cases

1. [Use case with business context]
2. [Use case with business context]
3. [Use case with business context]

---

**Next**: [Enterprise Architecture](negative-list-architecture) or jump to specific service:
- [API Negative List](api-negative-list)
- [Airflow Negative List](airflow-negative-list)
- [Sync Consumer](sync-negative-list)
```

### Parent Level: Architecture Page (800-1200 words)

**Purpose**: Enterprise-level architecture showing how services interact

**Sections**:
- System architecture diagram (ASCII or text description)
- Service interaction flows
- Data consistency model (how services stay in sync)
- Key architectural decisions
- Service communication patterns
- Failure scenarios and resilience

**Audience**: Architects, tech leads, senior developers

**Example**:
```markdown
# Negative List - Architecture

**Related**: [Business Logic](negative-list-logic) | [Service Details](#specific-services-below)

## Enterprise Architecture

```
┌──────────────────────────┐
│   External Systems       │
│  (Banks, Partners, etc)  │
└──────────────┬───────────┘
               │ REST API
        ┌──────▼──────────┐
        │ API Service     │
        │ (Query/Update)  │
        └────────┬────────┘
                 │
         ┌───────┴────────────┬──────────────┐
         │                    │              │
      Events                Events        Cache
         │                    │              │
    ┌────▼─────┐      ┌──────▼──────┐      │
    │  Event   │      │  Airflow    │      │
    │  Stream  │      │  Scheduler  │      │
    └────┬─────┘      └──────┬──────┘      │
         │                   │              │
    ┌────▼────────────────────▼──────┐      │
    │  Unified Database               │◄────┘
    │  (MSSQL / PostgreSQL)           │
    └─────────────────────────────────┘

Sync: Event-driven (real-time) + Batch (daily)
Consistency: Eventual with hourly reconciliation
```

## Service Interaction Flow

1. Client calls API Negative List → returns cached/live data
2. API writes change → publishes event to event stream
3. Airflow picks up scheduled sync → publishes batch update events
4. Sync Consumer listens to events → updates unified database
5. All services query unified database for current state

## Data Consistency Model

[Explanation of how services stay in sync, conflict resolution, etc.]

---

**To understand specific services**, see:
- [API Negative List Architecture](api-negative-list-architecture)
- [Airflow Process DAGs](airflow-negative-list-dags)
- [Sync Consumer Implementation](sync-consumer-architecture)
```

### Service Section: Service Overview Page (600-800 words)

**Purpose**: How to use this service. Written for teams outside your service (not developers building it).

**Audience**: Product teams, other services, external partners

**Sections** (adapt based on service type):

#### For API Services:
- What does this API do? (business value, not technical details)
- Access through gateways (external: Apigee → Internal: Gateway → Backend)
- Environments and base URLs (SIT/UAT, Production)
- Authentication methods (API key, OAuth 2.0, etc.)
- Common use cases
- Rate limits / quotas (if applicable)
- Getting started / contact for access

#### For Non-API Services:
- What does this service do? (business outcome)
- Who uses it? (internal teams, external partners)
- How to request features / report issues
- Availability / SLAs
- Contact / support

**Example (API Service - Apigee + Internal Gateway Pattern)**:
```markdown
# Negative List API

**Parent Feature**: [Negative List](negative-list) > [Feature Architecture](negative-list-architecture)

## What is Negative List API?

The Negative List API allows partner banks and systems to query and report accounts, merchants, or individuals that should be blocked from transactions. Use this API to check if an entity is on the negative list before processing any transaction.

## How to Access

All API requests are routed through **Apigee Gateway** → **Internal Gateway** → Backend service. See [API Gateway Architecture](insert-bfi-gateway-reference) for detailed access flow.

You interact with the **Apigee Gateway URL only** (external endpoint). The internal gateway handles internal routing—you don't need to access it directly.

## Environments and Endpoints

| Environment | Endpoint | Use Case |
| --- | --- | --- |
| **Production** | `https://gateway.bfi.co.id/negative-list` | Live transactions |
| **UAT/Staging** | `https://gateway-gc.bfi.co.id/negative-list` | Testing integrations |
| **SIT/Development** | `https://gateway-sit.bfi.co.id/negative-list` | Initial development |

## Authentication

### Option 1: OAuth 2.0 (Recommended for Production)

1. Request client credentials from the Negative List team
2. Exchange credentials for access token:
   ```
   POST /oauth/client_credentials/token?grant_type=client_credentials
   Authorization: Basic {base64(client_id:client_secret)}
   ```
3. Include token in all requests:
   ```
   Authorization: Bearer {access_token}
   ```

See [OAuth Authentication Details](#) for full instructions.

### Option 2: API Key (For Testing)

Include your API key in every request:

```
apikey: {your_api_key}
```

## Common Use Cases

### Check if Account is on Negative List

```
GET /negative-list/check?entity_type=account&entity_id=12345678
```

Returns: `blocked: true/false` with reason if blocked.

### Report a Fraudulent Account

```
POST /negative-list/report
{
  "entity_type": "account",
  "entity_id": "12345678",
  "reason": "fraud_detected"
}
```

## Rate Limits

- **Production**: 10,000 requests/hour
- **UAT/Staging**: 1,000 requests/hour
- **SIT/Development**: Unlimited

If you exceed rate limits, you'll receive a `429 Too Many Requests` response. Contact the Negative List team for higher limits.

## Getting Started

1. **Request Access**: Contact @negative-list-support with your team name and use case
2. **Get Credentials**: Receive client_id/client_secret or API key for your environment
3. **Test in SIT**: Use SIT environment first to verify integration
4. **Move to UAT**: Test against UAT data before production
5. **Go to Production**: Deploy with OAuth 2.0 credentials

## Need Help?

- **Documentation**: [Full API Reference](#)
- **Error Troubleshooting**: [Common Issues](#)
- **Support**: Slack @negative-list-support or email negative-list@bfi.co.id

---

**Detailed Guides**:
- [OAuth 2.0 Authentication](03a-negative-list-api-architecture) - In-depth auth instructions
- [API Endpoints Reference](03a-negative-list-api-architecture) - Complete endpoint documentation
- [Error Handling](03d-negative-list-api-operations) - Troubleshooting common errors

**Return to**: [Negative List](negative-list)
```

#### Example (Non-API Service):
```markdown
# Negative List - Batch Sync Service

**Parent Feature**: [Negative List](negative-list) > [Feature Architecture](negative-list-architecture)

## What Does This Service Do?

This service synchronizes negative list changes from the main API to all connected partner systems every 4 hours. If you're a partner bank, your system automatically receives the latest negative list without additional API calls.

## Who Uses This Service?

- Partner banks (automatic sync receivers)
- Internal systems (Real-time event consumers)

## How It Works

1. Changes are made to the negative list in the API
2. Every 4 hours, the batch sync service runs
3. Updates are sent to all registered partner systems
4. You receive a notification when your data is updated

## Getting Started

1. Register your system as a sync recipient
2. Provide a webhook URL or SFTP endpoint for receiving updates
3. You'll automatically receive negative list updates in your configured format

## Availability & Support

- **Service Status**: [BFI Status Page](#)
- **Scheduled Maintenance**: Sundays 2-4 AM GMT+7
- **Support Contact**: @platform-support

---

**More Information**:
- [Integration Guide](03a-negative-list-batch-sync-architecture) - How to integrate with batch sync
- [Event Schemas](03a-negative-list-batch-sync-architecture) - Format of sync messages
- [Troubleshooting](03d-negative-list-batch-sync-operations) - Common sync issues

**Return to**: [Negative List](negative-list)
```

### Service Detail Pages (Follow single-service patterns)

For each service, create detail pages following the single-service model:
- **[Service] Architecture** - Technical design specific to this service
- **[Service] Development** - Setup, testing, common tasks (this project's workspace)
- **[Service] Deployment** - Environment procedures (this project's workspace)
- **[Service] Operations** - Monitoring, troubleshooting (this project's workspace)

These pages are nested under the service overview page and follow the single-service page specifications (see below).

### Reference Page (600-1000 words)

**Purpose**: Cross-service lookup and runbooks

**Sections**:
- Glossary (shared terminology across all services)
- Service comparison table (features by service)
- Common cross-service workflows
- Troubleshooting flowchart (how to identify which service has the issue)
- Contact/escalation information
- Links to all services and documentation

**Example**:
```markdown
# Negative List - Reference

## Glossary

- **Negative List**: The master list of entities (accounts, persons, merchants) that should be blocked from transactions
- **Entity**: Any identifiable subject (account ID, person ID, merchant ID) that can be on the list
- **Sync Event**: A message indicating a negative list change
- **Cache**: Redis cache for frequently accessed results
- etc.

## Service Comparison

| Feature | API Service | Airflow | Consumer | Notes |
| --- | --- | --- | --- | --- |
| Query support | Yes | No | No | Airflow runs batch processes, not queries |
| Update support | Yes (manual) | Yes (scheduled) | No (passive) | Consumer only receives updates |
| Real-time | Yes | No (daily) | ~seconds delay | Depends on event processing |
| Database | PostgreSQL | PostgreSQL | PostgreSQL | All use unified DB |

## Troubleshooting Guide

> **Negative list shows stale data?**
> 1. Check if Redis cache is full → See [API Operations](api-negative-list-operations)
> 2. Check last Airflow run → See [Airflow Operations](airflow-negative-list-operations)
> 3. Check consumer lag → See [Consumer Operations](sync-consumer-operations)

> **New entry not appearing in negative list?**
> 1. Was update sent to API? → Check [API logs](api-negative-list-operations#logging)
> 2. Was event published? → Check [Event Stream](negative-list-architecture#data-flow)
> 3. Did Consumer process event? → Check [Consumer lag](sync-consumer-operations#monitoring)

---

**Services**: [API](api-negative-list) | [Airflow](airflow-negative-list) | [Consumer](sync-consumer-negative-list)
**Return to**: [Negative List Overview](negative-list)
```

**Purpose**: First impression - project summary for new developers

**Sections**:
- What is this project? (elevator pitch)
- Key features (3-5 bullet points)
- Quick start (5-7 steps)
- Technology stack (table)
- Next steps / where to go from here

**Tone**: Welcoming, non-technical language

**Example structure**:
```markdown
# Project Overview

**Related Pages**: [Architecture](architecture) | [Quick Start Guide](development)

## What is cr-misc-function?

[1 paragraph introducing the project]

## Key Features

- Feature 1: [brief description]
- Feature 2: [brief description]
- Feature 3: [brief description]

## Quick Start

[5-7 numbered steps to get running]

## Technology Stack

| Component | Technology | Version |
| --- | --- | --- |
| Language | Python | 3.11+ |
| ...

## Where to Go Next

- Want to understand the architecture? → [Architecture](architecture)
- Ready to develop? → [Development Setup](development)
- Need to deploy? → [Deployment](deployment)
```

### 2. Architecture Page (800-1200 words)

**Purpose**: System design and structural understanding

**Sections**:
- Architecture overview (diagram or ASCII art)
- Design patterns used (Strategy Pattern explanation)
- Core components
- Database abstraction layer
- Component interaction flow
- Design decisions and rationale

**Tone**: Technical but accessible

**Code Examples**: ASCII diagram showing relationships

**Example**:
```markdown
# System Architecture

**Related Pages**: [Overview](overview) | [API & Connections](api) | [Development](development)

## Architecture Overview

```
┌─────────────────────────────────┐
│   Application Layer             │
│  (Your Code)                    │
└──────────────┬──────────────────┘
               │
┌──────────────▼──────────────────┐
│  Connection Facade              │
│  (DBConnectorStrategy)          │
└──────────────┬──────────────────┘
               │
       ┌───────┴──────────┬──────────────┬─────────┐
       │                  │              │         │
┌──────▼──────┐ ┌─────────▼──────┐ ┌───▼──────┐  │
│  MSSQL      │ │ PostgreSQL     │ │ MySQL    │  │
│  Strategy   │ │ Strategy       │ │ Strategy │  │
└─────────────┘ └────────────────┘ └──────────┘  │
                                                   │
                                    ┌──────────────▼──────┐
                                    │  Hive, Trino, ODPS  │
                                    │  Strategies         │
                                    └─────────────────────┘
```

## Core Components

- **Strategies**: Database-specific implementations
- **Factory**: Routes database type to correct strategy
- **Configuration**: Environment variable loading
- **Facade**: Public API for application use

## Strategy Pattern Implementation

[Explain Strategy Pattern in context of this project]

## Database Support

[Matrix table of supported databases and features]

---

**Return to**: [Overview](overview) | **Next**: [API & Connections](api)
```

### 3. API & Connections Page (800-1200 words)

**Purpose**: How to connect to databases, what's supported, usage examples

**Sections**:
- Supported databases table
- Connection string formats
- Basic usage example
- Configuration requirements
- Connection pooling
- Error handling basics

**Tone**: Practical, reference-style

**Code Examples**: Real, runnable examples

**Example**:
```markdown
# API & Connections

**Related Pages**: [Architecture](architecture) | [Configuration](configuration) | [Development](development)

## Supported Databases

| Database | Version | Typical Use | Connection Method |
| --- | --- | --- | --- |
| MSSQL | 2019+ | Enterprise | pyodbc |
| PostgreSQL | 12+ | Linux/Cloud | psycopg2 |
| MySQL | 8.0+ | Web apps | mysql-connector |
| Hive | 2.3+ | Big Data | pyhive |
| Trino | 300+ | Distributed | trino-python |
| ODPS | Latest | Alibaba Cloud | pyodps |

## Connection Strings

### PostgreSQL
```
postgresql://user:password@localhost:5432/database
```

## Basic Usage

```python
from app.connections.strategies import create_strategy

# Create and use strategy
with create_strategy("postgres") as strategy:
    df = strategy.execute_query("SELECT * FROM users LIMIT 10")
    print(df)
```

## Configuration

Environment variables required:
- DATABASE_POSTGRES_HOST
- DATABASE_POSTGRES_USER
- DATABASE_POSTGRES_PASSWORD
- DATABASE_POSTGRES_DATABASE

See [Configuration](configuration) page for complete list.

---

**Return to**: [Architecture](architecture) | **Next**: [Development](development)
```

### 4. Development Page (800-1200 words)

**Purpose**: Getting a dev environment set up and running

**Sections**:
- Prerequisites
- Development setup (5-7 steps)
- Running the application
- Running tests
- Common development workflows
- Debugging tips
- IDE setup (VS Code)

**Tone**: Instructional, step-by-step

**Code Examples**: Setup and run commands

**Example structure**:
```markdown
# Development Setup

**Related Pages**: [Overview](overview) | [Configuration](configuration) | [Deployment](deployment)

## Prerequisites

- Python 3.11 or higher
- Git
- Database client tools (psql, mysql, etc.) - optional
- VS Code or preferred IDE
- Virtual environment tool (conda recommended)

## Setup Steps

1. Clone repository
   ```bash
   git clone [repo-url]
   cd cr-misc-function
   ```

2. Create virtual environment
   ```bash
   conda create -n cr-misc-function-env python=3.11
   conda activate cr-misc-function-env
   ```

3. Install dependencies
   ```bash
   pip install -r requirements.txt
   ```

4. Configure environment
   ```bash
   cp .env.template .env
   # Edit .env with your database credentials
   ```

5. Run application
   ```bash
   python app/main.py
   ```

6. Run tests
   ```bash
   pytest tests/
   ```

## Common Tasks

### Adding a New Database Strategy
[Steps and example]

### Running a Specific Test
```bash
pytest tests/test_mssql_strategy.py -v
```

### Debugging with VS Code
[Tips for debugging]

---

**Return to**: [API & Connections](api) | **Next**: [Deployment](deployment)
```

### 5. Deployment Page (800-1200 words)

**Purpose**: How to deploy to different environments

**Sections**:
- Environments overview (dev, staging, prod)
- Deployment checklist
- Deployment procedures by environment
- Rollback procedures
- Monitoring after deployment
- Release notes format

**Tone**: Procedural, safety-conscious

**Code Examples**: Deployment scripts and commands

### 6. Operations Page (800-1200 words)

**Purpose**: Running, monitoring, troubleshooting

**Sections**:
- Health checks
- Common issues and solutions (3-5 troubleshooting scenarios)
- Monitoring and alerting
- Backup and restore
- Scheduled maintenance
- Getting help (escalation contacts)

**Tone**: Problem-solving focused

**Code Examples**: Diagnostic commands

### 7. Use Cases & Examples (800-1200 words)

**Purpose**: Real-world usage scenarios

**Sections**:
- Use case 1 (with code example)
- Use case 2 (with code example)
- Use case 3 (with code example)
- Best practices
- Performance tips
- Anti-patterns to avoid

**Tone**: Practical, educational

**Code Examples**: 5-10 lines each, runnable

### 8. Configuration (800-1200 words)

**Purpose**: Environment setup and secrets management

**Sections**:
- Environment variables table (all variables, purpose, required/optional)
- Configuration file structure
- Secrets management (where to store sensitive data)
- Environment-specific configurations (dev vs staging vs prod)
- Configuration examples
- Troubleshooting configuration issues

**Tone**: Reference, technical

**Format**: Heavy use of tables

### 9. Reference (800-1200 words)

**Purpose**: Glossary, folder structure, quick lookups

**Sections**:
- Folder structure (tree or ASCII diagram)
- File organization explanation
- Glossary of terms and acronyms
- Supported database matrix
- Quick links to detailed documentation
- Troubleshooting flowchart (text-based decision tree)
- External resources and links

**Tone**: Reference, concise

---

## Confluence Formatting Standards

### Markdown Syntax for Confluence Compatibility

**Headings** (proper hierarchy):
```markdown
# Page Title (H1)
## Major Section (H2)
### Subsection (H3)
```

**Lists** (with proper spacing):
```markdown

- Item 1
- Item 2
  - Nested item
  - Nested item

1. Step 1
2. Step 2
3. Step 3

```

**Code Blocks** (always specify language):
```markdown

```python
def example():
    return True
```

```bash
git clone https://repository.git
```

```sql
SELECT * FROM users WHERE active = true;
```

```

**Important Notes** (using blockquote):
```markdown

> **Note**: This is important information that stands out

> **Warning**: Critical information users must know

> **Tip**: Helpful hint or best practice

```

**Tables** (simple, scannable):
```markdown

| Header 1 | Header 2 | Header 3 |
| --- | --- | --- |
| Data A | Data B | Data C |
| Data D | Data E | Data F |

```

**Internal Links** (between pages):
```markdown
[Page Name](page-name) - For Confluence, use link text
```

**External Links**:
```markdown
[External Site](https://example.com)
```

### Spacing and Readability

- **Blank line after headings**
- **Blank line before and after code blocks**
- **Blank line before and after tables**
- **Blank line before and after blockquotes**
- **Maximum 5 bullet items per list** (split into multiple lists if needed)
- **Maximum 4 rows per table** (use multiple tables if needed)

---

## Content Length Guidelines

| Page Type | Word Count | Sections | Code Examples |
| --- | --- | --- | --- |
| Overview | 500-800 | 4-5 | 1-2 |
| Technical | 800-1200 | 5-7 | 2-3 |
| Reference | 600-1000 | 5-6 | 1-2 |
| Procedural | 800-1200 | 6-8 | 2-4 |

**Principle**: Each page should take 3-5 minutes to read comfortably.

---

## Navigation and Linking

### Page Link Structure

Every page should include:

**Top Navigation**:
```markdown
**Related Pages**: [Page 1](page-1) | [Page 2](page-2) | [Page 3](page-3)
```

**Bottom Navigation**:
```markdown
**Return to**: [Main Page](home) | **Previous**: [Page X](page-x) | **Next**: [Page Y](page-y)
```

### Linking Best Practices

- Link to related pages, not unrelated ones
- Use descriptive link text (not "click here")
- Place navigation at top and bottom
- Include "Return to main" on all sub-pages

---

## Quality Checklist

Before deploying to Confluence, verify:

- [ ] **Title is clear** - Describes page content precisely
- [ ] **Related pages listed** - Links appear at top
- [ ] **Proper heading hierarchy** - H1, H2, H3 progression, no skipping
- [ ] **Sections are focused** - Each section covers one topic
- [ ] **Word counts reasonable** - Not too dense, not too sparse
- [ ] **Code blocks have language specified** - ```python, ```bash, etc.
- [ ] **Blank lines around blocks** - Code, tables, quotes properly spaced
- [ ] **Tables are scannable** - Not too wide, max 4 rows or multiple tables
- [ ] **Lists are concise** - Max 5 items per list
- [ ] **Important info highlighted** - Uses blockquote for notes/warnings
- [ ] **Examples are runnable** - Copy-paste executable
- [ ] **No unexplained acronyms** - Explained on first use
- [ ] **Internal links work** - All cross-references valid
- [ ] **Professional tone** - Consistent voice throughout
- [ ] **Markdown is valid** - No formatting errors
- [ ] **Printer-friendly** - Would print to 2-3 pages
- [ ] **Navigation complete** - Top and bottom links present

---

## Confluence Copy-Paste Workflow

### Exporting from Markdown

1. Generate `.md` file following these guidelines
2. Copy complete markdown content
3. In Confluence:
   - Create new page
   - Click "Insert" → "Markup" (or similar)
   - Paste markdown
   - Confluence automatically converts formatting
4. Review page layout
5. Adjust manually if needed (Confluence rendering sometimes differs)

### Best Practices

- Test links work after pasting
- Verify code blocks render correctly
- Check table alignment
- Ensure images/diagrams render (if included)
- Preview before publishing

---

## File Organization

Save generated documentation in `/docs/confluence/` with this structure:

**For system with single service**:
```
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

**For system with multiple services** (each service from different project):
```
docs/confluence/
├── 01-{system-slug}-business-logic.md (shared - all services reuse)
├── 02-{system-slug}-enterprise-architecture.md (shared - all services reuse)
│
├── 03-{system-slug}-api-overview.md (API project)
├── 03a-{system-slug}-api-architecture.md (API project)
├── 03b-{system-slug}-api-development.md (API project)
├── 03c-{system-slug}-api-deployment.md (API project)
├── 03d-{system-slug}-api-operations.md (API project)
│
├── 03-{system-slug}-airflow-overview.md (Airflow project)
├── 03a-{system-slug}-airflow-architecture.md (Airflow project)
├── 03b-{system-slug}-airflow-development.md (Airflow project)
├── 03c-{system-slug}-airflow-deployment.md (Airflow project)
├── 03d-{system-slug}-airflow-operations.md (Airflow project)
│
├── 03-{system-slug}-consumer-overview.md (Consumer project)
├── 03a-{system-slug}-consumer-architecture.md (Consumer project)
├── 03b-{system-slug}-consumer-development.md (Consumer project)
├── 03c-{system-slug}-consumer-deployment.md (Consumer project)
├── 03d-{system-slug}-consumer-operations.md (Consumer project)
│
└── 04-{system-slug}-reference.md (shared - all services append)
```

**Key Pattern**: 
- Pages 01, 02, 04 are shared (create once, reuse for all services)
- Pages 03, 03a-d are unique per service (each service creates its own)
- Filename includes both system slug AND service name for uniqueness

---

## Example: Complete Mini-Page

```markdown
# Quick Start

**Related Pages**: [Overview](overview) | [Development](development) | [Deployment](deployment)

---

## Get Running in 5 Minutes

### Prerequisites

- Python 3.11+
- Git

### Steps

1. Clone and setup
   ```bash
   git clone [repo]
   cd cr-misc-function
   python -m venv venv
   source venv/bin/activate  # or venv\Scripts\activate on Windows
   ```

2. Install and configure
   ```bash
   pip install -r requirements.txt
   cp .env.template .env
   # Edit .env with your database
   ```

3. Run application
   ```bash
   python app/main.py
   ```

4. Visit http://localhost:8000

> **Tip**: Use `python -m pytest` to run tests

## What's Next?

- [Full development guide](development)
- [Understanding the architecture](architecture)
- [Deploy to production](deployment)

---

**Return to**: [Overview](overview)
```

---

## Summary

✅ **9 focused pages** - Each independent but linked
✅ **Optimal length** - 3-5 minute read per page
✅ **Confluence-ready** - Copy-paste directly
✅ **Proper formatting** - Markdown standards followed
✅ **Scannable structure** - Headings, lists, tables
✅ **Navigation clear** - Easy to jump between topics
✅ **Examples practical** - Runnable code snippets
✅ **Professional quality** - Consistent, polished presentation

