# Data Pipeline Workflow

**Project Type**: ETL, batch processing, Airflow DAGs, data transformation jobs

**Applies to**: Services that move, transform, or process data in batches or workflows

**Key Focus**: Data flow orchestration, job scheduling, error handling, data validation

---

## Workflow Steps

### 1. Analyze the Data Pipeline

Read these files to understand the pipeline:

- `README.md` - What data does this pipeline process?
- `pyproject.toml` or equivalent - What orchestration tool? (Airflow, dbt, Kubernetes, etc.)
- Folder structure - How are jobs/DAGs organized?
- DAG/job definitions - What are the main processes?
- Configuration - How is scheduling/environment configured?

**Questions to answer**:

- What is the data source and destination?
- What transformations occur?
- What orchestration tool is used (Airflow, dbt, custom scheduler)?
- How often does it run (hourly, daily, on-demand)?
- What dependencies exist between jobs?
- How are failures handled and retried?

---

### 2. Fill Project Identity Section

Update the `PROJECT CONTEXT` section in `[projectWorkspace]/.github/copilot-instructions.md`:

```markdown
**Project Name**: [Actual pipeline name, e.g., "user-analytics-pipeline", "data-warehouse-etl"]

**Description**: [1-2 sentences describing what data is processed and where it goes]
Example: "ETL pipeline that extracts user behavior data from logs, transforms it for analytics, and loads into the data warehouse."

**Project Type**: Data Pipeline

**Language**: Python 3.9+ (or Scala, SQL, etc.)
**Framework**: Apache Airflow (or dbt, Kubernetes, custom scheduler, etc.)
**Key Dependencies**: [List main deps, e.g., "Apache Airflow, Pandas, SQLAlchemy, pytest"]
```

---

### 3. Add Project-Specific Patterns

Document unique conventions for THIS data pipeline:

```markdown
**Project-Specific Patterns & Conventions**:
- DAG Organization: Organized by domain (users, orders, analytics) in separate files
- Task Patterns: Standardized task naming: `[domain]_[operation]_[target]` (e.g., `users_extract_api`)
- Error Handling: Retry on failure with exponential backoff; email alerts on critical failures
- Data Validation: Schema validation on source data; row count checks before loading
- Scheduling: Daily runs at 2 AM UTC; SLA of 3 hours; backfill support for historical data
- Logging: Structured logging with correlation IDs; logs stored in CloudWatch/ELK
- Testing: Unit tests for transformations; data quality tests; mock external APIs
- Configuration: Environment-based config (dev/staging/prod); secrets from AWS Secrets Manager
- Monitoring: Custom metrics for pipeline health; alerting on job failures or slow runs
- Documentation: YAML config files document each step; README explains data lineage
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

**Add these for Python pipelines**:

- [Python Development](https://github.com/github/awesome-copilot/blob/main/instructions/python.instructions.md)

**Add these if applicable**:

- [ETL & Data Pipeline Best Practices](https://github.com/github/awesome-copilot/blob/main/instructions/etl-data-pipeline.instructions.md) ← For pipeline design
- [Data Validation & Quality](https://github.com/github/awesome-copilot/blob/main/instructions/data-validation.instructions.md) ← For data quality checks
- [Database Access Patterns](https://github.com/github/awesome-copilot/blob/main/instructions/database-access.instructions.md) ← For data sources/destinations
- [Job Orchestration](https://github.com/github/awesome-copilot/blob/main/instructions/job-orchestration.instructions.md) ← For Airflow/scheduler patterns
- [Error Handling Best Practices](https://github.com/github/awesome-copilot/blob/main/instructions/error-handling.instructions.md) ← For retry/failure handling
- [Testing Best Practices](https://github.com/github/awesome-copilot/blob/main/instructions/testing.instructions.md) ← For pipeline testing

**Example reference section**:

```markdown
### Language/Framework-Specific References

**For Python projects**:
- [Python Development](https://github.com/github/awesome-copilot/blob/main/instructions/python.instructions.md)

**For ETL & data pipelines**:
- [ETL & Data Pipeline Best Practices](https://github.com/github/awesome-copilot/blob/main/instructions/etl-data-pipeline.instructions.md)
- [Data Validation & Quality Checks](https://github.com/github/awesome-copilot/blob/main/instructions/data-validation.instructions.md)

**For Airflow DAGs**:
- [Apache Airflow Best Practices](https://github.com/github/awesome-copilot/blob/main/instructions/airflow.instructions.md)

**For database operations**:
- [Database Access Patterns](https://github.com/github/awesome-copilot/blob/main/instructions/database-access.instructions.md)

**For error handling & retries**:
- [Error Handling & Resilience](https://github.com/github/awesome-copilot/blob/main/instructions/error-handling.instructions.md)

**For testing**:
- [Data Pipeline Testing](https://github.com/github/awesome-copilot/blob/main/instructions/testing-data-pipelines.instructions.md)
```

---

### 5. Document Project-Specific Instructions

If your pipeline has special instructions in `.github/instructions/`, document them:

```markdown
## Project-Specific Instructions & Files

This data pipeline has the following project-specific instructions:

**dag-development.md**
- Description: Guidelines for writing Airflow DAGs, task definitions, and operators
- When to use: When creating or modifying DAGs or tasks
- Location: `.github/instructions/dag-development.md`

**data-validation-patterns.md**
- Description: Standards for data quality checks, schema validation, and row count assertions
- When to use: When adding data quality tests or validation steps
- Location: `.github/instructions/data-validation-patterns.md`

**pipeline-monitoring.md**
- Description: Metrics, alerting, and debugging patterns for pipeline monitoring
- When to use: When troubleshooting failures or setting up monitoring
- Location: `.github/instructions/pipeline-monitoring.md`
```

If no special instructions:

```markdown
## Project-Specific Instructions & Files

This data pipeline follows standard Airflow/ETL conventions. See the awesome-copilot references above for detailed guidance on pipeline design, testing, and error handling.
```

---

### 6. Validate Changes

**Checklist**:

- [ ] Pipeline name is accurate (e.g., "user-analytics-pipeline", not "[PROJECT_NAME]")
- [ ] Description explains what data is processed and destination (1-2 sentences)
- [ ] Project Type is "Data Pipeline"
- [ ] Language and Framework (Airflow, dbt, etc.) are correctly specified
- [ ] Tech Stack includes key dependencies (Airflow, Pandas, etc.)
- [ ] Project-Specific Patterns describe actual DAG/task patterns, scheduling, validation
- [ ] All awesome-copilot links are correct and applicable to data pipelines
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

## Example: User Analytics ETL Pipeline

**Before**:

```markdown
**Project Name**: [PROJECT_NAME]

**Description**: [DESCRIBE PROJECT HERE]

**Project Type**: [API Service / Consumer App / Data Pipeline / Library / Other]

**Language**: [e.g., Python 3.9+]
```

**After**:

```markdown
**Project Name**: user-analytics-etl

**Description**: ETL pipeline that extracts user behavior events from application logs, transforms them into analytics dimensions/facts, and loads into the data warehouse for reporting.

**Project Type**: Data Pipeline

**Language**: Python 3.9+
**Framework**: Apache Airflow 2.5+ with PythonOperator and SQLOperator
**Key Dependencies**: Apache Airflow, Pandas, SQLAlchemy, boto3 (AWS), pytest, great_expectations
```

**Project-Specific Patterns Example**:

```markdown
**Project-Specific Patterns & Conventions**:
- DAG Organization: Organized by data domain (users, orders, payments, analytics); each domain in separate file
- Task Naming: `[domain]_[operation]_[target]` format (e.g., `users_extract_api`, `orders_transform_facts`, `analytics_load_warehouse`)
- Scheduling: Daily DAG runs at 2 AM UTC; SLA of 3 hours max runtime; backfill support via CLI
- Error Handling: Retry failed tasks up to 3 times with exponential backoff; email alerts on SLA breach
- Data Quality: Great Expectations for schema validation; row count checks before loading; custom data quality operators
- Testing: Unit tests for transformations (Pandas operations); integration tests for full DAG runs; mock S3/database
- Logging: Structured logs with correlation IDs; CloudWatch logs; custom metrics to Datadog
- Configuration: Environment-based (dev/staging/prod); secrets from AWS Secrets Manager; Airflow Variables for thresholds
- Monitoring: Custom dashboards in Datadog; alerts for pipeline failures; data freshness checks
```

**References Example**:

```markdown
### Language/Framework-Specific References

**For Python projects**:
- [Python Development](https://github.com/github/awesome-copilot/blob/main/instructions/python.instructions.md)

**For ETL & data pipelines**:
- [ETL & Data Pipeline Best Practices](https://github.com/github/awesome-copilot/blob/main/instructions/etl-data-pipeline.instructions.md)
- [Data Quality & Validation](https://github.com/github/awesome-copilot/blob/main/instructions/data-validation.instructions.md)

**For Apache Airflow**:
- [Apache Airflow Best Practices](https://github.com/github/awesome-copilot/blob/main/instructions/airflow.instructions.md)

**For database operations**:
- [SQL & Database Patterns](https://github.com/github/awesome-copilot/blob/main/instructions/database-access.instructions.md)

**For testing**:
- [Data Pipeline Testing](https://github.com/github/awesome-copilot/blob/main/instructions/testing-data-pipelines.instructions.md)
```

---

## Success Criteria

✅ Pipeline name, description, and type accurately reflect this data pipeline
✅ Language and Framework (Airflow, dbt, etc.) are correctly specified
✅ Tech Stack lists actual dependencies and tools
✅ Project-Specific Patterns describe real task patterns, DAG organization, scheduling, validation
✅ All placeholder text `[EXAMPLE]` is replaced with actual values
✅ Awesome-copilot references are relevant to ETL/data pipeline development
✅ Entry Point Information section was NOT modified
✅ Last Updated date is current
✅ No task-specific file mappings were added
✅ Documentation is specific to this pipeline's architecture

---

## Tips for Data Pipelines

- **DAG Organization**: Describe how DAGs/jobs are organized (by domain, by frequency, etc.)
- **Scheduling**: Mention frequency (hourly, daily, weekly) and SLA requirements
- **Data Quality**: Document validation patterns and checks performed
- **Error Handling**: Describe retry logic and failure notifications
- **Monitoring**: Reference dashboards or alerting tools used
- **Data Lineage**: Mention if data lineage tracking is used
