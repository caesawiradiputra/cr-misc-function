---
description: 'Common Data Element (CDE) spreadsheet generation and management guidelines'
applyTo: '**/*.cde.tsv,**/*.lineage.tsv,**/cde/**'
---

# CDE Spreadsheet Generation Instructions

## Overview

These instructions guide the generation and maintenance of Common Data Element (CDE) spreadsheets that document data lineage, ownership, quality, and compliance across enterprise systems.

## Clarification and Information Gathering

**When these instructions are executed (manually or by AI agent), the following approach should be taken if context is incomplete:**

1. **Read Project Files First** — Before asking questions, explore:
   - `app/connections/`, `repositories/`, structure to understand business_contexts
   - Database configuration files to identify what data sources are supported
   - `docs/` files for SLA, deployment, and compliance requirements
   - README and comments to understand project purpose and scope
   - Existing configuration to understand data classification schemes

2. **Ask for Missing Information** — If unclear or missing, ask specifically:
   - "Which business_contexts should these CDEs support? (e.g., onboarding, payments, anti_fraud, collection?)"
   - "What are the SLA/performance requirements? (e.g., real-time vs. batch, latency, freshness?)"
   - "Are there existing CDEs I should reuse? Should I check `docs/data-lineage/master_cde_registry.tsv`?"
   - "For [entity], what criticality level: HIGH (regulatory/widely-used), MEDIUM (important), or LOW (supplemental)?"
   - "What data classification applies? (GDPR, CCPA, HIPAA, local laws?)"
   - "Is [cde_id] new or should I reuse an existing CDE?"

3. **Never Assume** — Do not guess business context, SLA, criticality levels, or regulatory classification

## Terminology Clarification

**See `.github/references/cde-terminology.md` for detailed explanation of:**
- **data_domain** — Semantic classification (e.g., APPL, CUST, PAY, RISK)
- **business_context** — Organizational boundary (e.g., Onboarding, Payments, Anti-Fraud)

Quick example: CDE-APPL-001 (Applicant.KTP Number) has **data_domain=APPL** and may appear in multiple **business_context** files (onboarding, collection, anti_fraud).

## 3-Sheet CDE Model

The CDE model uses a **consolidated master registry** with domain-specific flows to scale across many pipelines while keeping data consistent and avoiding duplication:

1. **CDE_REGISTRY** (Master) - Single source of truth for what the data is (ONE file for entire enterprise)
2. **LINEAGE_FLOW** - Domain-specific documentation of how data moves through systems
3. **CDE_USAGE** - Domain-specific consumption patterns showing who uses the CDE and how

### File Format
- **Format**: Tab-Separated Values (TSV)
- **Encoding**: UTF-8
- **Delimiter**: Tab character (`\t`)
- **File naming convention** (uses **business_context**, not data_domain):
  - `master_cde_registry.tsv` (ONE file, shared across enterprise)
  - `{business_context}_lineage_flow.tsv` (one per business context: onboarding, payments, anti_fraud, collection, etc.)
  - `{business_context}_cde_usage.tsv` (one per business context)
- **Example files**:
  - `master_cde_registry.tsv` (single source of truth)
  - `onboarding_lineage_flow.tsv`, `onboarding_cde_usage.tsv` (Onboarding business context)
  - `payments_lineage_flow.tsv`, `payments_cde_usage.tsv` (Payments business context)
  - `anti_fraud_lineage_flow.tsv`, `anti_fraud_cde_usage.tsv` (Anti-Fraud business context)

---

## Master CDE_REGISTRY — Data Definition (Enterprise-Wide)

**Purpose**: Single source of truth for ALL CDEs across the entire enterprise. No pipeline or technical transport details.

**File**: `master_cde_registry.tsv` (ONE file shared across all business contexts)

**One row per**: Unique CDE (identified by `cde_id`), regardless of data_domain or business_context

**Governance**:
- Maintained by: Data Governance team
- Updated when: New CDE is identified across any business context
- Never duplicate `cde_id`: Each CDE defined once, referenced by all business_context-specific flows

### Column Specifications for CDE_REGISTRY

| Column | Type | Required | Description |
|--------|------|----------|-------------|
| **cde_id** | String | Yes | Stable CDE identifier (format: `CDE-{data_domain}-{NUMBER}`, e.g., `CDE-APPL-001`). data_domain = semantic type (APPL, CUST, PAY, RISK, etc.) |
| **lineage_key** | String | Yes | Stable logical name combining entity and attribute (format: `Entity.Attribute`, e.g., `Applicant.KTP Number`) |
| **data_domain** | String | Yes | Semantic classification of the CDE (Applicant, Customer, Payment, Risk, Order, Account, etc.) — NOT the business context that uses it |

| **logical_entity** | String | Yes | Business entity name (Applicant, Application, Spouse, Vehicle, Customer, Order) |
| **logical_attribute** | String | Yes | Human-readable attribute name (KTP Number, Birth Date, Monthly Income, Email Address) |
| **business_definition** | String | Yes | Authoritative business meaning in clear, non-technical language |
| **semantic_owner** | String | Yes | Team or person who defines the meaning (e.g., LORA Team, BRAVO Team, Risk Team) |
| **data_classification_level** | String | Yes | Classification: PUBLIC, PII, SENSITIVE_PII, CONFIDENTIAL, METADATA |
| **regulatory_flag** | String | Yes | Whether subject to compliance/regulation (Yes/No) |
| **criticality_level** | String | Yes | Business impact level: HIGH, MEDIUM, LOW |
| **created_at** | String | Yes | ISO 8601 timestamp of CDE creation |
| **updated_at** | String | Yes | ISO 8601 timestamp of last update |

### Data Validation Rules for CDE_REGISTRY

**cde_id Format:**
- Pattern: `CDE-{data_domain}-{NUMBER}`
- Examples: `CDE-APPL-001`, `CDE-CUST-042`, `CDE-RISK-105`
- data_domain: Semantic domain abbreviation (3-4 uppercase letters) representing the data type (APPL=Applicant, CUST=Customer, PAY=Payment, RISK=Risk data)
- NUMBER: Sequential number unique within data_domain (zero-padded, 3 digits)
- Must be stable and never change

**lineage_key Format:**
- Pattern: `{Entity}.{Attribute}`
- Example: `Applicant.KTP Number`, `Application.Application ID`
- Character set: alphanumeric, spaces, hyphens allowed
- Must be unique across entire CDE_REGISTRY
- Represents stable logical name (independent of technical column names)

**data_classification_level Values:**
- `PUBLIC` - No access restrictions
- `METADATA` - System or metadata fields
- `PII` - Personally Identifiable Information
- `SENSITIVE_PII` - Highly sensitive PII (SSN, KTP, passport number)
- `CONFIDENTIAL` - Business confidential data

**criticality_level Values:**
- `HIGH` - Critical to business, widely used, regulatory importance
- `MEDIUM` - Important but not critical, used in specific processes
- `LOW` - Supplemental data, limited usage

**regulatory_flag Values:**
- `Yes` - Subject to compliance (GDPR, CCPA, HIPAA, local regulations)
- `No` - No regulatory constraints

**Timestamp Format:**
- ISO 8601 format: `YYYY-MM-DDTHH:MM:SSZ` (e.g., `2025-06-15T10:30:00Z`)

### Example Master CDE_REGISTRY Structure

```tsv
cde_id	lineage_key	data_domain	logical_entity	logical_attribute	business_definition	semantic_owner	data_classification_level	regulatory_flag	criticality_level	created_at	updated_at
CDE-APPL-001	Applicant.KTP Number	Applicant	Applicant	KTP Number	National identity card number issued by Indonesian government. Primary identifier for applicant verification.	LORA Team	SENSITIVE_PII	Yes	HIGH	2025-01-15T09:00:00Z	2025-06-10T14:30:00Z
CDE-APPL-002	Application.Application ID	Application	Application	Application ID	Unique system-generated identifier for each application submission. Used for end-to-end tracking.	LORA Team	PII	No	HIGH	2025-01-15T09:05:00Z	2025-06-10T14:30:00Z
CDE-CUST-001	Customer.Email Address	Customer	Customer	Email Address	Primary email address for customer contact and account recovery. Validated at registration.	BRAVO Team	PII	Yes	HIGH	2025-02-01T10:00:00Z	2025-06-10T14:30:00Z
```

---

## Sheet 2️⃣: LINEAGE_FLOW — Business-Context-Specific Technical Movement

**Purpose**: Document how CDEs move through technical systems within a specific business context.

**File**: `{business_context}_lineage_flow.tsv` — One file per business context (e.g., `onboarding_lineage_flow.tsv`, `payments_lineage_flow.tsv`)

**One row per**: Unique combination of `(pipeline_name + cde_id + lineage_step)` within this business_context

**Foreign Key Relationship**:
- Every `cde_id` in LINEAGE_FLOW MUST exist in `master_cde_registry.tsv`
- LINEAGE_FLOW documents HOW a CDE flows in this business_context's pipelines
- CDE definition stays in master registry (not duplicated)

### Column Specifications for LINEAGE_FLOW

| Column | Type | Required | Description |
|--------|------|----------|-------------|
| **pipeline_name** | String | Yes | Business-facing pipeline name (anti_fraud_realtime, collection_batch, risk_scoring) |
| **cde_id** | String | Yes | Foreign key to CDE_REGISTRY. Links flow to CDE definition |
| **lineage_step** | Integer | Yes | Sequential step (1, 2, 3...) within this pipeline |
| **process_name** | String | Yes | Technical process/stage name (db_change_event, cdc_publish_kafka, flink_join) |
| **transformation_type** | String | Yes | Category of transformation (passthrough, cast, normalize, join, enrich, aggregate, derive, constant, upsert) |
| **is_derived** | String | Yes | Yes if new business attribute created; No if data flows through |
| **upstream_system** | String | Yes | Source system name (LORA_DB, BRAVO_DB, Kafka, Flink, S3) |
| **upstream_type** | String | Yes | Type of upstream (database, topic, event-stream, logic, constant) |
| **upstream_object** | String | Yes | Source object name (table name, topic name, stream name) |
| **upstream_column** | String | Yes | Column name at source |
| **downstream_system** | String | Yes | Target system (Kafka, Postgres, Flink, S3, Redis) |
| **downstream_type** | String | Yes | Type of downstream (database, topic, table, event-stream) |
| **downstream_object** | String | Yes | Target object name |
| **downstream_column** | String | Yes | Column name at destination |
| **relational_role** | String | Yes | Database role if applicable (primary_key, foreign_key, unique_key, none) |
| **load_type** | String | Yes | Load pattern (cdc, insert, upsert, batch, insert_on_conflict) |
| **sla** | String | Yes | Service level (realtime, near_realtime, hourly, daily) |

### Data Validation Rules for LINEAGE_FLOW

**pipeline_name Format:**
- Pattern: Lowercase with underscores (snake_case)
- Examples: `anti_fraud_realtime`, `collection_batch`, `risk_scoring`
- Must match actual pipeline names in your systems

**lineage_step:**
- Sequential positive integer (1, 2, 3...)
- Starts at 1 for each unique `pipeline_name + cde_id` combination
- Represents order of processing within that pipeline for that CDE

**process_name Format:**
- Pattern: Lowercase with underscores
- Examples: `db_change_event`, `cdc_publish_kafka`, `flink_join_onboarding`, `consumer_upsert_postgres`

**transformation_type Values:**
- `passthrough` - Data passes without modification
- `cast` - Data type conversion (e.g., string → numeric)
- `normalize` - Data normalization (e.g., uppercase, format standardization)
- `join` - Combine with other CDE in JOIN operation
- `enrich` - Add context or reference data
- `aggregate` - Sum, average, or group operation
- `derive` - Create new calculated field from existing data
- `constant` - Add fixed value (e.g., version, timestamp)
- `upsert` - Update or insert based on key

**is_derived Values:**
- `Yes` - New CDE or business attribute created in this step
- `No` - Data flows through or is consumed

**upstream_type / downstream_type Values:**
- `database` - Relational database (MSSQL, Postgres, MySQL)
- `topic` - Kafka or message queue topic
- `event-stream` - Event stream system
- `logic` - Output from processing logic (Flink, Spark)
- `constant` - Fixed value

**relational_role Values:**
- `primary_key` - Primary key field
- `foreign_key` - Foreign key reference
- `unique_key` - Unique constraint
- `none` - No relational role

**load_type Values:**
- `cdc` - Change Data Capture
- `insert` - Insert only (append-only)
- `upsert` - Update if exists, insert if not
- `batch` - Batch load
- `insert_on_conflict` - Insert with conflict resolution

**sla Values:**
- `realtime` - Sub-second (< 1s)
- `near_realtime` - Near real-time (< 1 minute)
- `hourly` - Hourly refresh
- `daily` - Daily refresh

### Example LINEAGE_FLOW Structure

```tsv
pipeline_name	cde_id	lineage_step	process_name	transformation_type	is_derived	upstream_system	upstream_type	upstream_object	upstream_column	downstream_system	downstream_type	downstream_object	downstream_column	relational_role	load_type	sla
anti_fraud_realtime	CDE-APPL-001	1	db_change_event	passthrough	No	LORA_DB	database	applicants	ktp_number	Kafka	topic	applicant_events	ktp_number	none	cdc	realtime
anti_fraud_realtime	CDE-APPL-001	2	cdc_publish_kafka	passthrough	No	Kafka	topic	applicant_events	ktp_number	Kafka	topic	fraud_detection_stream	ktp_number	none	insert	realtime
anti_fraud_realtime	CDE-APPL-001	3	flink_enrich_risk	enrich	No	Kafka	topic	fraud_detection_stream	ktp_number	Kafka	topic	fraud_enriched	ktp_enriched	none	upsert	near_realtime
```

---

## Sheet 3️⃣: CDE_USAGE — Business-Context-Specific Consumption Patterns

**Purpose**: Document who uses each CDE in a specific business context, how they use it, and what they need.

**File**: `{business_context}_cde_usage.tsv` — One file per business context (e.g., `onboarding_cde_usage.tsv`, `payments_cde_usage.tsv`)

**One row per**: Unique combination of `(cde_id + consumer_system + consumption_purpose)` within this business_context

**Foreign Key Relationship**:
- Every `cde_id` in CDE_USAGE MUST exist in `master_cde_registry.tsv`
- CDE_USAGE documents CONSUMPTION of a CDE in this business_context
- CDE definition stays in master registry (not duplicated)

### Column Specifications for CDE_USAGE

| Column | Type | Required | Description |
|--------|------|----------|-------------|
| **cde_id** | String | Yes | Foreign key to CDE_REGISTRY. Links usage to CDE |
| **consumer_system** | String | Yes | System consuming the CDE (Postgres, Redis, Analytics Platform, ML System) |
| **consumption_purpose** | String | Yes | Why this system needs the CDE (realtime_ops, analytics_reporting, model_training, fraud_detection, caching) |
| **consumer_team** | String | Yes | Team responsible for consumption (Risk Team, Analytics, Engineering) |
| **data_quality_requirement** | String | Yes | Quality SLA needed (NOT NULL, unique, valid_format, freshness) |
| **retention_days** | Integer | Yes | How many days to retain in consumer system |
| **is_active** | String | Yes | Is this currently active consumption (Yes/No) |
| **notes** | String | No | Additional context or special requirements |

### Data Validation Rules for CDE_USAGE

**cde_id:**
- Must match existing `cde_id` in CDE_REGISTRY

**consumer_system Format:**
- Pattern: Human-readable system name
- Examples: `Postgres`, `Redis`, `Analytics Platform`, `ML Training Pipeline`

**consumption_purpose Format:**
- Pattern: Lowercase with underscores
- Examples: `realtime_ops`, `analytics_reporting`, `model_training`, `fraud_detection`, `caching`

**data_quality_requirement Values:**
- Comma-separated list of requirements
- Examples: `NOT NULL, unique`, `valid_email_format`, `completeness > 99%`, `freshness < 1min`

**retention_days:**
- Positive integer representing retention period
- Examples: 1 (realtime cache), 90 (3 months), 2555 (7 years for compliance)

**is_active Values:**
- `Yes` - Currently in use
- `No` - Legacy or planned consumption

### Example CDE_USAGE Structure

```tsv
cde_id	consumer_system	consumption_purpose	consumer_team	data_quality_requirement	retention_days	is_active	notes
CDE-APPL-001	Postgres	realtime_ops	LORA Team	NOT NULL, unique, valid_format	365	Yes	Primary operational store
CDE-APPL-001	Redis	caching	Engineering Team	NOT NULL	1	Yes	Cache for lookup performance
CDE-APPL-001	Analytics Platform	analytics_reporting	Analytics Team	completeness > 99%	1825	Yes	For compliance reporting
CDE-CUST-001	ML Training Pipeline	model_training	Risk Team	NOT NULL, freshness < 1h	90	Yes	Model training data lake
```



## Best Practices

### CDE ID Sequence Management
- ✅ **Check existing master registry first** — Before creating new CDEs, load existing `master_cde_registry.tsv` from `docs/data-lineage/` directory
- ✅ **Reuse existing cde_ids** — If CDE already exists in registry (e.g., `CDE-APPL-001`), use that ID in business_context files, never create a duplicate
- ✅ **Increment sequence by data_domain** — For new CDEs, find the highest sequence number within that data_domain:
  - If `CDE-APPL-001` and `CDE-APPL-002` exist, next NEW Applicant CDE is `CDE-APPL-003`
  - If `CDE-CUST-001` exists, next NEW Customer CDE is `CDE-CUST-002`
  - **Format**: Always zero-pad to 3 digits: `CDE-APPL-001` (not `CDE-APPL-1`)
- ✅ **Preserve existing metadata** — Never overwrite existing CDE definitions; if CDE already exists, reference it by ID only
- ✅ **Single source of truth** — Master registry is the authoritative source for cde_id assignments; once assigned, maintain consistency

### Master CDE_REGISTRY (Definition Sheet — Enterprise-Wide)
- ✅ **One row per unique CDE** — Single point of definition across entire enterprise
- ✅ **Never duplicate cde_id** — CDE-APPL-001 defined once, referenced by all domains
- ✅ **Stable identifiers** — cde_id should never change over time
- ✅ **Business-focused** — Use business terminology, not technical column names
  - ✅ `Applicant.KTP Number` (clear, business-focused)
  - ❌ `app.ktp_num` (too technical)
- ✅ **Clear definitions** — Non-technical, 15-100 words, understandable to business users
- ✅ **Consistent logical names** — Same CDE has same `lineage_key` everywhere
- ✅ **Include all domains** — CDE_REGISTRY includes CDEs used by Onboarding, Payments, Risk, etc.
- ❌ **Never leave empty cells** — Use "N/A" only if truly not applicable

### LINEAGE_FLOW (Business-Context-Specific Movement Sheet)
- ✅ **One row per step per pipeline** — Each `pipeline_name + cde_id + lineage_step` combination is unique within this business_context
- ✅ **Sequential lineage_step** — Start at 1 for each new CDE in each pipeline
- ✅ **Match actual systems** — process_name and pipeline_name must match real systems
- ✅ **Document transformations** — transformation_type clearly describes what happens
- ✅ **Denormalize for analysis** — Store both upstream AND downstream in each row for visibility
- ✅ **Track format changes** — If column name changes (e.g., `id` → `application_id`), show in upstream_column vs downstream_column
- ✅ **Reference master registry** — All cde_id values must exist in `master_cde_registry.tsv`
- ✅ **Include only this business_context's flows** — Onboarding LINEAGE_FLOW includes only onboarding pipelines (anti_fraud_realtime, onboarding_join, etc.)

### CDE_USAGE (Business-Context-Specific Consumption Sheet)
- ✅ **One row per consumer per purpose** — Multiple teams can consume same CDE for different purposes within this business_context
- ✅ **Specific quality requirements** — Not generic "good data" but measurable rules
- ✅ **Right retention** — Balance between business need and storage/compliance costs
- ✅ **Track active state** — Distinguish active from legacy or planned consumption
- ✅ **Reference master registry** — All cde_id values must exist in `master_cde_registry.tsv`
- ✅ **Include only this business_context's consumers** — Onboarding CDE_USAGE includes only onboarding team consumers (Postgres, Redis, Analytics for onboarding purposes)

### Scale Across Enterprise (Master Registry + Business_Context-Specific Flows)
- ✅ **Consolidated CDE_REGISTRY** — One master file for ALL CDEs (no duplication)
- ✅ **Business_context-specific flows** — One LINEAGE_FLOW and CDE_USAGE file per business_context (onboarding, payments, anti_fraud, collection, etc.)
- ✅ **Foreign keys link sheets** — All business_context flows reference master `cde_id`
- ✅ **Avoid duplication** — LINEAGE_FLOW and CDE_USAGE reference master CDE_REGISTRY, not duplicate definitions
- ✅ **Pipeline filtering** — Filter LINEAGE_FLOW by business_context, then by pipeline_name within that context
- ✅ **Impact analysis** — To find all uses of CDE-APPL-001: look in master registry, then search all business_context LINEAGE_FLOW and CDE_USAGE files

### Names must match reality
- **pipeline_name**: Must match actual pipeline/job names in your orchestration tool
  - ✅ `anti_fraud_realtime` (actual Airflow DAG name)
  - ❌ `fraud_check` (too generic)
- **process_name**: Must match actual process/stage in pipeline
  - ✅ `flink_join_onboarding` (actual Flink job name)
  - ❌ `join_data` (ambiguous)
- **system names**: Exact as referenced in your architecture
  - ✅ `LORA_DB`, `Kafka`, `Flink`
  - ❌ `Database`, `Message Queue` (too generic)

## Common Lineage Patterns (LINEAGE_FLOW)

### CDC to Kafka to Database (Realtime)
```
pipeline_name: `anti_fraud_realtime`
CDE-APPL-001	lineage_step=1: LORA_DB.applicants → Kafka.applicant_events
CDE-APPL-001	lineage_step=2: Kafka.applicant_events → Kafka.fraud_detection_stream (Flink enrichment)
CDE-APPL-001	lineage_step=3: Kafka.fraud_detection_stream → Postgres.fraud_scores (upsert)
```

### API to Lake to Warehouse (Batch)
```
pipeline_name: `risk_scoring_daily`
CDE-CUST-001	lineage_step=1: Salesforce_API → S3.data_lake/customer_events/
CDE-CUST-001	lineage_step=2: S3 → Spark transformation → S3.processed_zone/
CDE-CUST-001	lineage_step=3: S3 → Redshift.dim_customer (full_refresh nightly)
```

### Multi-Source Join with Enrichment
```
pipeline_name: `onboarding_realtime_join`
CDE-APPL-001	lineage_step=1: LORA_DB.applications → Kafka.app_events (CDC)
CDE-CUST-001	lineage_step=1: BRAVO_DB.customers → Kafka.customer_events (CDC)
CDE-APPL-001	lineage_step=2: Kafka.app_events + Kafka.customer_events → Flink join → Kafka.joined_entity (join transformation)
CDE-APPL-001	lineage_step=3: Kafka.joined_entity → Postgres.enriched_applications (insert_on_conflict)
```

### Multiple Consumers Pattern
One CDE flows through LINEAGE_FLOW to multiple endpoints, then tracked separately in CDE_USAGE:
```
CDE-CUST-001 (Email Address)
├── LINEAGE_FLOW: Postgres → Kafka → Redis (realtime cache)
├── CDE_USAGE Consumer 1: Redis (caching) - retention 1 day
├── CDE_USAGE Consumer 2: Analytics Platform (reporting) - retention 1825 days
└── CDE_USAGE Consumer 3: ML Pipeline (model_training) - retention 90 days
```

## Governance Rules and Policies

### Transformation Vocabulary Governance
- **Authoritative Maintainer**: Data Governance team defines and maintains `transformation_type` vocabulary
- **Approved Transformation Types**: passthrough, cast, normalize, join, enrich, aggregate, derive, constant, upsert (see LINEAGE_FLOW column specs)
- **Policy**: Each business_context must use only approved transformation types to prevent semantic fragmentation
- **Extension Process**: New transformation types require Data Governance approval before use in any business_context
- **Constraint**: Transformation type describes TECHNICAL operation, not business semantics — never invent new types for specific pipelines

### Cross-Business-Context Transformation Semantics Policy
- **Permitted**: Different business_contexts may apply different technical transformations to the same CDE
  - Example: Onboarding normalizes phone number to E.164 format; Collections hashes phone number for matching
  - Both reference same `CDE-CUST-001` (Customer.Phone) from master registry
- **Not Permitted**: Transformations must NOT alter the business definition from master registry
  - Example: If master defines "Phone = International format per E.164", all business_contexts must respect that semantic meaning
  - Technical transformations (normalization, hashing, masking) are **independent of business definition**
- **Governance Check**: During lineage review, confirm that transformation type does not contradict master registry business definition
- **Impact**: Ensures single source of truth for data meaning, while allowing technical flexibility per business_context

### CDE Identification
- **CDE (Common Data Element)** = data element used across multiple systems/processes
- **Criteria for CDE**:
  - Used in 2+ downstream systems
  - Appears in 2+ logical processes
  - Has enterprise-wide business definition
  - Subject to compliance/regulatory oversight
- **CDE Assignment**:
  - Assign `cde_id` format: `CDE-{DOMAIN}-{SEQUENTIAL}`
  - Domain abbreviation (3-4 chars): APP, CUST, PAY, FRAUD, RISK, etc.
  - Sequential number: Starting at 001, increment per new CDE in domain

### Data Sensitivity Classification
- **Risk-based assignment**: Higher sensitivity = more restrictive
- **Regulatory requirements**: PII and PHI require enhanced governance
- **Escalation protocol**: Any `PII` or `PHI` must have documented:
  - Compliance framework (GDPR, CCPA, HIPAA, etc.)
  - Data retention policy
  - Access control specifications

### Lineage Completeness
- **Every data element** must have complete upstream and downstream documentation
- **Dead-end data** (consumed but not passed downstream) should still be documented with clear `downstream_object`
- **Intermediate transformations** should show all steps, not just first and last

## Quality Checklist

### Master CDE_REGISTRY Validation
- [ ] All rows have 12 columns populated
- [ ] cde_id values are globally unique across entire registry
- [ ] cde_id format matches `CDE-{DOMAIN}-{NUMBER}` (e.g., CDE-APPL-001, CDE-CUST-042)
- [ ] lineage_key values are unique and follow `Entity.Attribute` format
- [ ] Each lineage_key represents a distinct business concept (no duplicate definitions under different cde_id)
- [ ] data_classification_level values are from approved list
- [ ] Business definitions are clear, non-technical, 15-100 words
- [ ] semantic_owner teams are current and identifiable
- [ ] criticality_level is justified (HIGH for regulatory/widely-used, etc.)
- [ ] Timestamps are valid ISO 8601 format
- [ ] No empty cells in any required column
- [ ] This file is the single source of truth for all CDE definitions

### Domain LINEAGE_FLOW Validation
- [ ] All rows have 17 columns populated
- [ ] cde_id values **only** reference CDEs that exist in `master_cde_registry.tsv`
- [ ] lineage_step values are sequential (1, 2, 3...) per unique `pipeline_name + cde_id` combination
- [ ] pipeline_name, process_name values match actual system pipeline names
- [ ] transformation_type values are from approved list
- [ ] is_derived is justified (Yes only if new attribute created)
- [ ] upstream_system → downstream_system flow is logical
- [ ] Upstream and downstream columns exist in their respective objects
- [ ] relational_role is relevant to the system type
- [ ] SLA is achievable with specified systems
- [ ] No empty cells in any required column
- [ ] This file contains **only** pipelines for this domain (no cross-domain flows)

### Domain CDE_USAGE Validation
- [ ] All rows have 8 columns populated (7 required + optional notes)
- [ ] cde_id values **only** reference CDEs that exist in `master_cde_registry.tsv`
- [ ] consumer_system and consumer_team are current, identifiable, and belong to this domain
- [ ] consumption_purpose clearly describes how CDE is used
- [ ] data_quality_requirement is specific and measurable
- [ ] retention_days is appropriate for consumption purpose
- [ ] is_active accurately reflects current consumption status
- [ ] No conflicting retention policies for same CDE across consumers (within this domain)
- [ ] No empty cells in required columns
- [ ] This file contains **only** consumers from this domain

### Cross-File Integrity Validation (Master + Domain Files)
- [ ] Every cde_id in `{domain}_lineage_flow.tsv` exists in `master_cde_registry.tsv` ✅ **Critical: Referential integrity**
- [ ] Every cde_id in `{domain}_cde_usage.tsv` exists in `master_cde_registry.tsv` ✅ **Critical: Referential integrity**
- [ ] All cde_id values are consistent in representation across all sheets (e.g., CDE-APPL-001, not CDE-APP-001)
- [ ] No duplicate rows within each sheet
- [ ] Business definitions in master registry are consistent with how CDE is referenced in domain files
- [ ] When searching for all uses of CDE-APPL-001: found in master registry + referenced in at least one domain flow/usage
- [ ] Impact analysis test: Can identify all domains using CDE-APPL-001 by searching all `{domain}_lineage_flow.tsv` + `{domain}_cde_usage.tsv` files

## File Organization

### Directory Structure (Master + Business_Context-Specific Model)

**Master Registry at Enterprise Level:**
```
docs/data-lineage/
├── master_cde_registry.tsv                 (ONE file — Enterprise source of truth, 12 columns)
```

**Business_Context-Specific Flows and Usage:**
```
docs/data-lineage/
├── onboarding/
│   ├── onboarding_lineage_flow.tsv         (How CDEs move through onboarding pipelines, 17 columns)
│   └── onboarding_cde_usage.tsv            (Who within onboarding consumes CDEs, 8 columns)
├── payments/
│   ├── payments_lineage_flow.tsv
│   └── payments_cde_usage.tsv
├── anti_fraud/
│   ├── anti_fraud_lineage_flow.tsv
│   └── anti_fraud_cde_usage.tsv
├── collection/
│   ├── collection_lineage_flow.tsv
│   └── collection_cde_usage.tsv
├── data-governance/
│   ├── cde_standards.md (3-sheet model standards)
│   ├── data_quality_rules.md
│   └── transformation_types.md (reference for transformation_type values)
└── compliance/
    ├── pii_handling_policy.md
    └── data_retention_policy.md
```

### Governance Model

| Artifact | Owner | Update Frequency | Scope |
| --------- | -------- | -------------------- | ------- |
| `master_cde_registry.tsv` | Data Governance Team | As new CDEs discovered; changes trigger business_context re-review | All CDEs across enterprise |
| `{business_context}_lineage_flow.tsv` | Business_Context Technical Lead | As pipelines are added/modified | Only pipelines for this business_context |
| `{business_context}_cde_usage.tsv` | Business_Context Product Manager | As consuming systems change | Only consumers within this business_context |

### File Naming Conventions

- **Master registry:** `master_cde_registry.tsv` (always singular, always lowercase)
- **Business_context flows:** `{business_context}_lineage_flow.tsv` (business_context name lowercase, consistent across all files)
- **Business_context usage:** `{business_context}_cde_usage.tsv`
- **Valid business_context names:** onboarding, payments, anti_fraud, collection, customer_service, risk_management (lowercase, underscores for multi-word, no dashes)

## Tools and Automation

### Recommended Tools
- **Spreadsheet editors**: Excel, Google Sheets (with TSV import/export)
- **Validation**: Python script to validate format, uniqueness, SLA compatibility
- **Version control**: Commit TSV files to git with commit messages noting CDE additions
- **Documentation generation**: Python script to generate data dictionary from CDE spreadsheet

### Validation Script Pattern
```python
# Check lineage_key uniqueness
assert len(df['lineage_key'].unique()) == len(df['lineage_key'])

# Validate CDE ID format
valid_cde_ids = df[df['is_cde'] == 'Yes']['cde_id'].str.match(r'CDE-[A-Z]{3,4}-\d{3}')
assert valid_cde_ids.all()

# Ensure upstream → downstream consistency
```

