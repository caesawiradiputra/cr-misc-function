---
description: 'CDE Lineage Flow: Business-context-specific documentation of how CDEs move through technical systems'
applyTo: '**/*_lineage_flow.tsv,**/lineage/**/*.tsv'
---

# CDE Lineage Flow Instructions

## Overview

**LINEAGE_FLOW** documents HOW Common Data Elements (CDEs) move through technical systems within a specific business context. It tracks pipelines, transformations, and system-to-system data movement.

**Key Principle**: One row per CDE per lineage step per pipeline, all referencing master CDE definitions.

---

## Purpose and Foreign Key Relationship

**Purpose**: Document HOW CDEs move through technical systems in a specific business context

**File**: `{business_context}_lineage_flow.tsv` — One file per business context
- Examples: `onboarding_lineage_flow.tsv`, `payments_lineage_flow.tsv`, `anti_fraud_lineage_flow.tsv`

**One row per**: Unique combination of `(pipeline_name + cde_id + lineage_step)` within this business_context

**Foreign Key Relationship**:
- ✅ Every `cde_id` in LINEAGE_FLOW MUST exist in `master_cde_registry.tsv`
- ✅ LINEAGE_FLOW documents HOW a CDE flows in this business_context's pipelines
- ✅ CDE **definition** stays in master registry (not duplicated here)

**Cross-References**:
- **Master Registry**: See [CDE Master Registry Instructions](./cde-master-registry.instructions.md)
- **Usage Patterns**: See [CDE Usage Patterns Instructions](./cde-usage-patterns.instructions.md)

---

## Column Specifications (17 Columns)

| Column | Type | Required | Description |
|--------|------|----------|-------------|
| **pipeline_name** | String | Yes | Business-facing pipeline name (anti_fraud_realtime, collection_batch, risk_scoring) |
| **cde_id** | String | Yes | Foreign key to master CDE_REGISTRY. Links flow to CDE definition |
| **lineage_step** | Integer | Yes | Sequential step (1, 2, 3...) within this pipeline for this CDE |
| **process_name** | String | Yes | Technical process/stage name (db_change_event, cdc_publish_kafka, flink_join) |
| **transformation_type** | String | Yes | Category: passthrough, cast, normalize, join, enrich, aggregate, derive, constant, upsert |
| **is_derived** | String | Yes | Yes if new business attribute created; No if data flows through |
| **upstream_system** | String | Yes | Source system name (LORA_DB, BRAVO_DB, Kafka, Flink, S3) |
| **upstream_type** | String | Yes | Type: database, topic, event-stream, logic, constant |
| **upstream_object** | String | Yes | Source object name (table name, topic name, stream name) |
| **upstream_column** | String | Yes | Column name at source |
| **downstream_system** | String | Yes | Target system (Kafka, Postgres, Flink, S3, Redis) |
| **downstream_type** | String | Yes | Type: database, topic, table, event-stream |
| **downstream_object** | String | Yes | Target object name |
| **downstream_column** | String | Yes | Column name at destination |
| **relational_role** | String | Yes | Database role: primary_key, foreign_key, unique_key, none |
| **load_type** | String | Yes | Load pattern: cdc, insert, upsert, batch, insert_on_conflict |
| **sla** | String | Yes | Service level: realtime, near_realtime, hourly, daily, best_effort |

---

## Data Validation Rules

### pipeline_name Format
- **Pattern**: Lowercase with underscores (snake_case)
- **Examples**: `anti_fraud_realtime`, `collection_batch`, `risk_scoring_daily`
- **Must match**: Actual pipeline/job names in orchestration tool (Airflow, Dagster, etc.)

### lineage_step
- **Sequential**: Positive integer (1, 2, 3...)
- **Starts at 1**: For each unique `pipeline_name + cde_id` combination
- **Represents**: Order of processing within that pipeline for that CDE

### process_name Format
- **Pattern**: Lowercase with underscores
- **Examples**: `db_change_event`, `cdc_publish_kafka`, `flink_join_onboarding`, `consumer_upsert_postgres`
- **Must match**: Actual process/stage names in your systems

### transformation_type Values (APPROVED LIST ONLY)
- `passthrough` - Data passes without modification
- `cast` - Data type conversion (e.g., string → numeric)
- `normalize` - Data normalization (e.g., uppercase, format standardization, phone to E.164)
- `join` - Combine with other CDE in JOIN operation
- `enrich` - Add context or reference data from external source
- `aggregate` - Sum, average, count, or group operation
- `derive` - Create new calculated field from existing data
- `constant` - Add fixed value (e.g., version number, timestamp)
- `upsert` - Update if exists, insert if not

**Governance**: Only use approved transformation types. Extension requires Data Governance approval.

### is_derived Values
- `Yes` - New CDE or business attribute created in this step
- `No` - Data flows through without creating new business attribute

### upstream_type / downstream_type Values
- `database` - Relational database (MSSQL, Postgres, MySQL)
- `topic` - Kafka or message queue topic
- `event-stream` - Event stream system (Kinesis, Pulsar)
- `logic` - Output from processing logic (Flink, Spark, Lambda function)
- `constant` - Fixed value or configuration

### relational_role Values
- `primary_key` - Primary key field in database
- `foreign_key` - Foreign key reference to another table
- `unique_key` - Unique constraint (not primary key)
- `none` - No relational role

### load_type Values
- `cdc` - Change Data Capture (delta changes only)
- `insert` - Insert only (append-only, no updates)
- `upsert` - Update if exists, insert if not
- `batch` - Batch load (truncate and reload, or full refresh)
- `insert_on_conflict` - Insert with conflict resolution strategy

### sla Values
- `realtime` - Sub-second latency (< 1s)
- `near_realtime` - Near real-time (< 1 minute)
- `hourly` - Hourly refresh
- `daily` - Daily refresh
- `best_effort` - No strict SLA

---

## Example LINEAGE_FLOW

### Onboarding Business Context

**File**: `onboarding_lineage_flow.tsv`

```tsv
pipeline_name	business_context	cde_id	lineage_step	process_name	transformation_type	is_derived	upstream_system	upstream_type	upstream_object	upstream_column	downstream_system	downstream_type	downstream_object	downstream_column	relational_role	load_type	sla
anti_fraud_realtime	onboarding	CDE-APPL-001	1	db_change_event	passthrough	No	LORA_DB	database	applicants	ktp_number	Kafka	topic	applicant_events	ktp_number	primary_key	cdc	realtime
anti_fraud_realtime	onboarding	CDE-APPL-001	2	cdc_publish_kafka	passthrough	No	Kafka	topic	applicant_events	ktp_number	Kafka	topic	fraud_detection_stream	ktp_number	none	insert	realtime
anti_fraud_realtime	onboarding	CDE-APPL-001	3	flink_enrich_risk	enrich	No	Kafka	topic	fraud_detection_stream	ktp_number	Kafka	topic	fraud_enriched	ktp_enriched	none	upsert	near_realtime
onboarding_realtime_join	onboarding	CDE-APPL-002	1	cdc_publish_kafka	passthrough	No	LORA_DB	database	applications	id	Kafka	topic	app_submission_events	app_id	none	cdc	realtime
onboarding_realtime_join	onboarding	CDE-CUST-001	1	cdc_publish_kafka	passthrough	No	LORA_DB	database	applicants	dob	Kafka	topic	applicant_events	birth_date	none	cdc	realtime
onboarding_realtime_join	onboarding	CDE-CUST-001	2	flink_join_enrich	join	No	Kafka	topic	applicant_events	birth_date	Postgres	database	applicant_profile	dob_input	none	upsert	near_realtime
```

**Key Addition**: `business_context` column is set to `"onboarding"` (constant across all rows in onboarding_lineage_flow.tsv). This preserves business context metadata during exports to central catalogs, ensuring semantic context is never lost during federation or integration.

**Note**: All `cde_id` values (CDE-APPL-001, CDE-APPL-002, CDE-CUST-001) reference entries in `master_cde_registry.tsv`. This file contains **only Onboarding business_context pipelines**.

---

## Common Lineage Patterns

### Pattern 1: CDC to Kafka to Database (Realtime)
```
Pipeline: anti_fraud_realtime
CDE-APPL-001 Step 1: LORA_DB.applicants → Kafka.applicant_events (CDC)
CDE-APPL-001 Step 2: Kafka.applicant_events → Kafka.fraud_detection_stream (Flink enrichment)
CDE-APPL-001 Step 3: Kafka.fraud_detection_stream → Postgres.fraud_scores (upsert)
```

### Pattern 2: API to Lake to Warehouse (Batch)
```
Pipeline: risk_scoring_daily
CDE-CUST-001 Step 1: Salesforce_API → S3.data_lake/customer_events/ (extract)
CDE-CUST-001 Step 2: S3 → Spark transformation → S3.processed_zone/ (normalize)
CDE-CUST-001 Step 3: S3 → Redshift.dim_customer (batch load, full refresh)
```

### Pattern 3: Multi-Source Join with Enrichment
```
Pipeline: onboarding_realtime_join
CDE-APPL-001 Step 1: LORA_DB.applications → Kafka.app_events (CDC)
CDE-CUST-001 Step 1: BRAVO_DB.customers → Kafka.customer_events (CDC)
CDE-APPL-001 Step 2: Kafka.app_events + Kafka.customer_events → Flink join → Kafka.joined_entity
CDE-APPL-001 Step 3: Kafka.joined_entity → Postgres.enriched_applications (insert_on_conflict)
```

### Pattern 4: Phone Normalization Across Business Contexts
**Demonstrates Cross-Business-Context Transformation Semantics Policy**

```
# Onboarding normalizes phone to E.164
Pipeline: onboarding_realtime | business_context: onboarding
CDE-CUST-001 (Customer.Phone) Step 1: LORA_DB → Kafka (passthrough)
CDE-CUST-001 Step 2: Kafka → Flink normalize → Kafka (normalize to E.164 format)

# Collections hashes phone for privacy
Pipeline: collection_outreach | business_context: collections
CDE-CUST-001 (Customer.Phone) Step 1: BRAVO_DB → Kafka (passthrough)
CDE-CUST-001 Step 2: Kafka → Lambda hash → S3 (normalize via hashing)
```

**Both transformations reference same CDE-CUST-001 from master registry, but apply different technical operations per business_context needs. Each file (onboarding_lineage_flow.tsv vs collections_lineage_flow.tsv) has business_context column set appropriately.**

---

## Best Practices

### LINEAGE_FLOW Maintenance
- ✅ **One row per step** — Each `pipeline_name + cde_id + lineage_step` combination unique
- ✅ **Sequential lineage_step** — Start at 1 for each new CDE in each pipeline
- ✅ **Match actual systems** — `process_name` and `pipeline_name` must match real system names
- ✅ **Document transformations** — `transformation_type` clearly describes what happens
- ✅ **Denormalize for analysis** — Store both upstream AND downstream in each row
- ✅ **Track format changes** — If column name changes (e.g., `id` → `application_id`), show in columns
- ✅ **Reference master** — All `cde_id` must exist in `master_cde_registry.tsv`
- ✅ **Business_context scope** — Include ONLY this business_context's pipelines

### Names Must Match Reality
- **pipeline_name**: Actual pipeline/job name in orchestration tool
  - ✅ `anti_fraud_realtime` (actual Airflow DAG name)
  - ❌ `fraud_check` (too generic, doesn't match actual system)
- **process_name**: Actual process/stage in pipeline
  - ✅ `flink_join_onboarding` (actual Flink job name)
  - ❌ `join_data` (ambiguous, doesn't identify specific process)
- **System names**: Exact as referenced in architecture
  - ✅ `LORA_DB`, `Kafka`, `Flink`, `Postgres`
  - ❌ `Database`, `Message Queue` (too generic)

### Completeness
- ✅ **Document all steps** — Not just first and last, but intermediate transformations
- ✅ **Show dead-ends** — If data consumed but not passed downstream, document with clear `downstream_object`
- ✅ **Track column renames** — Show how column names change through pipeline

---

## Quality Checklist

### LINEAGE_FLOW Validation
- [ ] All 19 columns populated in every row
- [ ] All `business_context` values match filename (e.g., `onboarding_lineage_flow.tsv` has `business_context="onboarding"`)
- [ ] All `cde_id` values exist in `master_cde_registry.tsv` ✅ **CRITICAL: Referential integrity**
- [ ] All `lineage_step` values sequential (1, 2, 3...) per `pipeline_name + cde_id`
- [ ] All `pipeline_name` and `process_name` match actual system names
- [ ] All `transformation_type` from approved list only
- [ ] All `is_derived` justified (Yes only if new attribute created)
- [ ] All upstream → downstream flows logically consistent
- [ ] All upstream/downstream columns exist in their respective objects
- [ ] All `relational_role` relevant to system type
- [ ] All `sla` achievable with specified systems
- [ ] No conflicting transformations for same CDE in same pipeline
- [ ] No empty cells in required columns
- [ ] File contains **only pipelines for this business_context**

### Cross-File Integrity
- [ ] Every `cde_id` exists in master registry
- [ ] All `cde_id` consistent format across files (e.g., CDE-APPL-001)
- [ ] No duplicate rows (same `pipeline_name + cde_id + lineage_step`)
- [ ] Transformations respect master registry business definitions
- [ ] Can trace complete flow from source to destination

---

## File Organization

### Directory Structure
```
docs/data-lineage/
├── master_cde_registry.tsv                 (Master CDE definitions)
├── onboarding/
│   ├── onboarding_lineage_flow.tsv         (THIS FILE TYPE - Onboarding flows)
│   └── onboarding_cde_usage.tsv
├── payments/
│   ├── payments_lineage_flow.tsv           (THIS FILE TYPE - Payments flows)
│   └── payments_cde_usage.tsv
└── (other business_contexts...)
```

### Governance Model

| Aspect | Details |
|--------|---------|
| **Owner** | Business_Context Technical Lead |
| **Update Frequency** | As pipelines are added/modified within business_context |
| **Scope** | Only pipelines for this specific business_context |
| **Naming** | `{business_context}_lineage_flow.tsv` (lowercase, underscores) |

---

## Cross-References

- **Master Registry**: See [CDE Master Registry Instructions](./cde-master-registry.instructions.md) for CDE definitions
- **Usage Patterns**: See [CDE Usage Patterns Instructions](./cde-usage-patterns.instructions.md) for consumption documentation
- **Generation Prompts**: See [CDE Prompts README](../prompts/README.md) for Mode A vs. Mode B selection
