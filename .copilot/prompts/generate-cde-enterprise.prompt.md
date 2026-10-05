# Generate CDE Data Model: Enterprise Initial Setup (PROMPT A)

**Use This Prompt For**: Creating master CDE registry from scratch, establishing new business_context flows, first-time documentation of semantic domains

You are an expert data governance specialist tasked with conducting comprehensive discovery and generating a unified Common Data Element (CDE) data model **for an enterprise with no existing CDE registry**. Your mission is to create:
1. **Master CDE Registry** (`master_cde_registry.tsv`) — Enterprise-wide single source of truth
2. **Business-Context-Specific Flows** (`{business_context}_lineage_flow.tsv`) — One per specified business context
3. **Business-Context-Specific Usage** (`{business_context}_cde_usage.tsv`) — One per specified business context

This is **Mode A: Initial Registry Establishment** — comprehensive discovery phase (2-4 weeks typical).

---

## Terminology Clarification

**See `.github/references/cde-terminology.md` for detailed explanation of:**
- **data_domain** — Semantic classification (e.g., APPL, CUST, PAY, RISK)
- **business_context** — Organizational boundary (e.g., Onboarding, Payments, Anti-Fraud)

Quick example: CDE-APPL-001 (Applicant data) has **data_domain=APPL** but flows through **multiple business contexts** (onboarding, collection, anti_fraud).

---

## Enterprise-Wide Master + Business-Context-Specific Model

The model organizes **one master definition file + multiple business_context-specific flow/usage files**, all linked by `cde_id`:

### Master Registry (YOUR PRIMARY DELIVERABLE)
1. **Master CDE_REGISTRY** (Definition — ONE file for entire enterprise)
   - One row per unique CDE across ALL business_contexts
   - Business meaning, ownership, classification, regulatory flags
   - No pipeline or technical details
   - Created by: Data Governance Team (with input from domain experts)
   - **File: `master_cde_registry.tsv`** (12 columns)
   - **This is the authoritative source of truth** — all business_contexts reference it

### Business-Context-Specific Files (One set per business context)
2. **LINEAGE_FLOW** (Movement — Business-Context-Specific)
   - One row per unique `(pipeline_name + cde_id + lineage_step)` WITHIN this business_context only
   - Tracks data transformations through business_context's technical systems
   - References CDE definitions from master registry via `cde_id` (foreign key)
   - **File: `{business_context}_lineage_flow.tsv`** (17 columns)

3. **CDE_USAGE** (Consumption — Business-Context-Specific)
   - One row per unique `(cde_id + consumer_system + consumption_purpose)` WITHIN this business_context
   - Tracks data quality requirements, retention, usage by business_context's consumers
   - References CDE definitions from master registry via `cde_id` (foreign key)
   - **File: `{business_context}_cde_usage.tsv`** (8 columns)

---

## Discovery and Consolidation Approach

**Phase 1: Stakeholder Discovery** (Recommended 1-2 weeks)
1. Interview domain experts across all business_contexts
2. Identify semantic domains (Applicant, Customer, Payment, Risk, etc.)
3. Map which business_contexts use which semantic domains
4. Document regulatory and compliance requirements
5. Establish data classification scheme (PUBLIC, PII, SENSITIVE_PII, CONFIDENTIAL, METADATA)

**Phase 2: Master Registry Consolidation** (Recommended 1 week)
1. Merge all discovered CDEs into single master registry
2. Eliminate duplicates with conflicting definitions
3. Assign unique CDE IDs (one per semantic domain)
4. Establish semantic ownership and criticality levels
5. Get consensus review from Data Governance stakeholders

**Phase 3: Business-Context Technical Mapping** (Recommended 1-1.5 weeks)
1. For each business_context, document pipelines using master CDEs
2. Create LINEAGE_FLOW files (how data flows in each context)
3. Create CDE_USAGE files (who consumes in each context)
4. Validate referential integrity (all cde_id values exist in master)

---

## Task

Generate **one master CDE registry + business_context-specific TSV files** for enterprise initial setup.

### Input Requirements

Provide comprehensive information about:
1. **Semantic Domains** (Applicant, Customer, Payment, Risk, etc. — identify all business entities)
2. **CDE Definitions** (business meaning, entity names, classifications, ownership for each semantic domain)
3. **Target Business_Contexts** (specify ALL business_contexts in enterprise: onboarding, payments, collections, anti_fraud, customer_service, etc.)
4. **Pipelines** (pipeline names, technologies, stages WITHIN each business_context)
5. **Data Movement** (source systems → target systems, transformations WITHIN each business_context)
6. **Consumption Patterns** (which systems consume, purpose, quality needs, retention WITHIN each business_context)
7. **Regulatory Context** (PII/SENSITIVE_PII flags, compliance requirements across jurisdictions)
8. **Business Criticality** (HIGH/MEDIUM/LOW impact for each CDE and semantic domain)
9. **Data Classification Scheme** (What classification categories apply? e.g., GDPR, CCPA, HIPAA, local laws?)

### Discovery Protocol (BEFORE you start generating)

**If Context is Missing, ALWAYS Ask for Clarification:**

1. **Project Structure Analysis**: Read project files to understand:
   - What business_contexts does this enterprise support? (Check `app/connections/`, `repositories/`, `docs/`, config files)
   - What data sources/databases are referenced? (Check database strategies, connection configs)
   - What are overall SLA/performance requirements? (Check README, deployment guides)
   - What regulatory frameworks apply? (Check docs, security guidelines, legal requirements)
   - What data classification scheme is already in use? (Check existing configs, comments)

2. **Ask for Clarification**: If any of these are unclear or missing, ASK:
   - **Semantic Domains**: "Based on project structure, I see potential domains: [Applicant, Customer, Payment, Risk]. Are these all the semantic domains? Any missing?"
   - **Business_Context Scope**: "This enterprise appears to support [X, Y, Z] business_contexts. Should I include all of these, or focus on specific ones?"
   - **Data Source Definitions**: "I see references to [MSSQL, PostgreSQL, MySQL, Hive]. What specific tables/entities map to each semantic domain?"
   - **SLA Requirements**: "What are latency, freshness, and reliability requirements for each business_context?"
   - **Criticality Levels**: "For [CDE name], should this be HIGH (regulatory/widely-used), MEDIUM (important), or LOW (supplemental)?"
   - **Data Classification**: "What regulatory categories apply? (e.g., GDPR, CCPA, HIPAA, local Indonesia data protection laws?)"
   - **Business_Context Usage**: "For [CDE name], which business_contexts actually use this? (e.g., Onboarding only, or Onboarding + Collections + Anti-Fraud?)"

3. **Never Assume**: Do not guess semantic domains, business_contexts, SLAs, or criticality. This is initial setup — get it right.

---

## Comprehensive Processing Steps

### Step 0: Discover All Semantic Domains and Business_Contexts
- **Map semantic domains**: Applicant, Customer, Payment, Risk, etc. — Get consensus on complete list
- **List all business_contexts**: Onboarding, Payments, Collections, Anti-Fraud, Customer Service, etc.
- **Create domain → business_context matrix**: Which contexts use which domains?
  - Example: Applicant domain used in {Onboarding, Anti-Fraud, Collections}
  - Payment domain used in {Payments, Collections}

### Step 1: Consolidate and Normalize → Master CDE_REGISTRY
- **Interview domain experts** for each semantic domain
- **Identify candidate CDEs** across all business_contexts
- **Consolidate duplicates**: If Onboarding defines Customer.Phone and Payments also defines Customer.Phone, MERGE into single CDE
  - Check for conflicting definitions; resolve with stakeholders
  - Use most complete/accurate business definition
  - Assign ONE CDE ID (e.g., CDE-CUST-001)
- **Generate CDE IDs**:
  - Format: `CDE-{data_domain}-{NUMBER}` (e.g., `CDE-APPL-001`, `CDE-CUST-002`, `CDE-PAY-001`)
  - Use semantic domain abbreviations (APPL for Applicant, CUST for Customer, etc.)
  - Start numbering at 001 for each domain, increment sequentially
- **Extract for each CDE**:
  - Unique `cde_id`
  - `definition_version` (semantic version, e.g., 1.0; tracks definition evolution)
  - `lineage_key` as `Entity.Attribute`
  - `business_definition` (non-technical, 15-100 words, clear meaning)
  - `data_classification_level` (PUBLIC, PII, SENSITIVE_PII, CONFIDENTIAL, METADATA)
  - `semantic_owner` (team responsible for definition across enterprise)
  - `approved_by` (governance authority who approved this CDE definition)
  - `criticality_level` (HIGH for regulatory/enterprise-critical, MEDIUM for important, LOW for supplemental)
  - `regulatory_flag` (Yes if GDPR/CCPA/HIPAA/local compliance applies)
  - Timestamps (ISO 8601)
- **Output**: MASTER `master_cde_registry.tsv` (14 columns, all CDEs consolidated, NO DUPLICATES)

### Step 2: Create Business-Context-Specific LINEAGE_FLOW Files
- **For each specified business_context** (e.g., onboarding, payments, anti_fraud):
  - Identify ALL pipelines WITHIN this business_context
  - For each pipeline, identify CDEs flowing through it
  - **Reference master registry**: Use `cde_id` from master for all CDEs in this context
  - For each CDE in pipeline, document:
    - `business_context` = constant value matching filename (e.g., "onboarding" for onboarding_lineage_flow.tsv)
    - `lineage_step` = 1, 2, 3... (sequential within pipeline)
    - Source system → target system
    - Transformation applied (`transformation_type`: passthrough, join, enrich, derive, normalize, etc.)
    - Load pattern (`load_type`: cdc, insert, upsert, batch, etc.)
    - SLA requirement (realtime, near_realtime, hourly, daily, best_effort)
  - One row per CDE per step per pipeline
  - Denormalize: include both upstream AND downstream in each row
  - **All `cde_id` values MUST exist in master registry** (foreign key validation)
- **Output**: One `{business_context}_lineage_flow.tsv` per business_context (19 columns)

### Step 3: Create Business-Context-Specific CDE_USAGE Files
- **For each specified business_context**:
  - Identify all CONSUMER SYSTEMS within this business_context
  - For each CDE and consumer, document:
    - `cde_id` (reference from master registry — foreign key)
    - `consumption_purpose` (realtime_ops, analytics_reporting, model_training, etc.)
    - `access_pattern` (how the CDE is accessed: point_lookup, range_query, join_key, aggregation, model_input)
    - `consumer_team` (team responsible — must belong to this business_context)
    - `data_quality_requirement` (specific, measurable: NOT NULL, unique, freshness, etc.)
    - `retention_days` (how long to keep in consumer system)
    - `is_active` (Yes if currently in use, No if legacy/planned)
  - One row per CDE per consumer per purpose
  - Track active vs. legacy consumption
  - Identify and document conflicts in retention policies
  - **All `cde_id` values MUST exist in master registry** (foreign key validation)
- **Output**: One `{business_context}_cde_usage.tsv` per business_context (9 columns)

### Step 4: Enterprise-Wide Validation and Cross-File Integrity
- ✅ Master registry has NO duplicate `cde_id` or `lineage_key`
- ✅ Each semantic domain has consistent CDE ID numbering (CDE-APPL-001, CDE-APPL-002, etc.)
- ✅ All `cde_id` in any `{business_context}_lineage_flow.tsv` exist in `master_cde_registry.tsv`
- ✅ All `cde_id` in any `{business_context}_cde_usage.tsv` exist in `master_cde_registry.tsv`
- ✅ No orphaned CDEs (all master CDEs used in at least one business_context file)
- ✅ Transformation types are from approved vocabulary only
- ✅ SLAs are achievable with specified systems
- ✅ Retention policies are appropriate for consumption purposes
- ✅ **Impact Analysis Test**: Searching for CDE-APPL-001 finds it in master, then in onboarding_lineage_flow.tsv, payments_cde_usage.tsv, collection_lineage_flow.tsv, etc.

---

## Output Specifications

**File Format**: Tab-Separated Values (TSV)
**Encoding**: UTF-8
**Naming Convention**:
- Master: `master_cde_registry.tsv` (singleton, enterprise-wide)
- Business_context flows: `{business_context}_lineage_flow.tsv` (one per business_context)
- Business_context usage: `{business_context}_cde_usage.tsv` (one per business_context)

### Master CDE Registry (14 Columns — ENTERPRISE-WIDE, SINGLE SOURCE OF TRUTH)
```
cde_id	definition_version	lineage_key	data_domain	logical_entity	logical_attribute	business_definition	semantic_owner	approved_by	data_classification_level	regulatory_flag	criticality_level	created_at	updated_at
```

### Business-Context-Specific LINEAGE_FLOW (19 Columns — ONE PER BUSINESS_CONTEXT)
```
pipeline_name	business_context	cde_id	lineage_step	process_name	transformation_type	is_derived	upstream_system	upstream_type	upstream_object	upstream_column	downstream_system	downstream_type	downstream_object	downstream_column	relational_role	load_type	sla
```

### Business-Context-Specific CDE_USAGE (9 Columns — ONE PER BUSINESS_CONTEXT)
```
cde_id	consumer_system	consumption_purpose	access_pattern	consumer_team	data_quality_requirement	retention_days	is_active	notes
```

---

## Quality Checklist: Initial Setup

### Master Registry Validation
- [ ] All 14 columns present in header
- [ ] No duplicate `cde_id` or `lineage_key` values
- [ ] All `cde_id` follow format: `CDE-{DOMAIN}-###` (e.g., `CDE-APPL-001`)
- [ ] All `definition_version` follow semantic versioning (1.0, 1.1, 2.0, etc.)
- [ ] All `lineage_key` follow format: `Entity.Attribute`
- [ ] All `approved_by` identify valid governance authorities
- [ ] `data_classification_level`: One of {PUBLIC, PII, SENSITIVE_PII, CONFIDENTIAL, METADATA}
- [ ] `criticality_level`: One of {HIGH, MEDIUM, LOW} with justification
- [ ] `business_definition`: Non-technical, clear, 15-100 words each
- [ ] `semantic_owner`: Identifiable, responsible across enterprise
- [ ] `regulatory_flag`: Yes/No with regulatory basis documented
- [ ] All timestamps valid ISO 8601 format
- [ ] Covers ALL semantic domains identified in discovery
- [ ] Represents single source of truth (no duplication across contexts)

### Business-Context File Validation
- [ ] All 19/9 columns present (LINEAGE_FLOW/CDE_USAGE)
- [ ] All `cde_id` values exist in master registry
- [ ] All `business_context` values match filename (onboarding_lineage_flow.tsv contains only business_context="onboarding")
- [ ] All `access_pattern` values from approved vocabulary (point_lookup, range_query, join_key, aggregation, model_input)
- [ ] No cross-context contamination (Onboarding file contains ONLY Onboarding pipelines/consumers)
- [ ] Transformation types from approved vocabulary
- [ ] SLAs are achievable
- [ ] Retention policies justified for consumption purposes
- [ ] No orphaned CDEs (all master CDEs referenced at least once)
- [ ] Impact analysis successful (can trace CDE across all contexts)

---

## Example Output (Partial — Master + One Business Context)

### Master CDE Registry (Shared Across All Contexts)
```tsv
cde_id	definition_version	lineage_key	data_domain	logical_entity	logical_attribute	business_definition	semantic_owner	approved_by	data_classification_level	regulatory_flag	criticality_level	created_at	updated_at
CDE-APPL-001	1.0	Applicant.KTP Number	Applicant	Applicant	KTP Number	National identity card number issued by Indonesian government. Primary identifier for applicant verification and compliance.	LORA Team	LORA Governance Lead	SENSITIVE_PII	Yes	HIGH	2026-02-13T10:00:00Z	2026-02-13T10:00:00Z
CDE-APPL-002	1.0	Application.Application ID	Application	Application	Application ID	Unique system-generated identifier for each application submission. Used for end-to-end tracking and compliance reporting.	LORA Team	LORA Governance Lead	PII	No	HIGH	2026-02-13T10:00:00Z	2026-02-13T10:00:00Z
CDE-CUST-001	1.0	Customer.Birth Date	Customer	Customer	Birth Date	Date of birth used for age verification and compliance requirements.	LORA Team	LORA Governance Lead	PII	Yes	HIGH	2026-02-13T10:00:00Z	2026-02-13T10:00:00Z
CDE-PAY-001	1.0	Payment.Transaction ID	Payment	Payment	Transaction ID	Unique identifier for each payment transaction in the system. Used for reconciliation and fraud prevention.	Payments Team	Anti-Fraud Chief Data Steward	PII	No	HIGH	2026-02-13T10:00:00Z	2026-02-13T10:00:00Z
```

### Onboarding Business-Context LINEAGE_FLOW
```tsv
pipeline_name	business_context	cde_id	lineage_step	process_name	transformation_type	is_derived	upstream_system	upstream_type	upstream_object	upstream_column	downstream_system	downstream_type	downstream_object	downstream_column	relational_role	load_type	sla
onboarding_realtime	onboarding	CDE-APPL-001	1	change_data_capture	passthrough	No	LORA_DB	database	applicants	ktp_number	Kafka	topic	applicant_events	ktp_number	primary_key	cdc	realtime
onboarding_realtime	onboarding	CDE-APPL-002	1	change_data_capture	passthrough	No	LORA_DB	database	applications	id	Kafka	topic	application_events	app_id	none	cdc	realtime
onboarding_realtime	onboarding	CDE-CUST-001	1	change_data_capture	passthrough	No	LORA_DB	database	applicants	dob	Kafka	topic	applicant_events	birth_date	none	cdc	realtime
```

### Onboarding Business-Context CDE_USAGE
```tsv
cde_id	consumer_system	consumption_purpose	access_pattern	consumer_team	data_quality_requirement	retention_days	is_active	notes
CDE-APPL-001	Postgres	realtime_ops	point_lookup	LORA Team	NOT NULL, unique, valid_format	365	Yes	Primary operational store for compliance; retrieved by application_id
CDE-APPL-002	Postgres	realtime_ops	join_key	LORA Team	NOT NULL, unique	365	Yes	Primary application tracking; used to join with status tables
CDE-CUST-001	Analytics Platform	model_training	model_input	Risk Team	NOT NULL, freshness < 6h	90	Yes	Age-based risk scoring model training; direct feature input
```

---

## Context for Generation

Refer to [CDE Spreadsheet Generation Instructions](../../.github/instructions/cde-spreadsheet-generation.instructions.md) for:
- Complete column reference definitions
- Data classification guidelines
- Transformation type vocabulary (approved list)
- Best practices and naming conventions
- Governance rules and policies
- Cross-sheet relationships and foreign key patterns

---

## Your Role: Enterprise CDE Discovery Lead

You are responsible for:

1. **Discovering All Semantic Domains** in the enterprise
   - Interview domain experts
   - Map entities (Applicant, Customer, Payment, Risk, etc.)
   - Identify which business_contexts use which domains

2. **Consolidating Master Registry** without duplication
   - Merge contradictory definitions
   - Assign single CDE ID per semantic entity
   - Get stakeholder consensus on master definitions
   - Establish data governance ownership

3. **Mapping Business-Context-Specific Flows and Usage**
   - For each business_context, document how CDEs flow through pipelines
   - Document who consumes what for what purpose
   - Reference master registry via foreign keys (cde_id)

4. **Validating Cross-Enterprise Integrity**
   - Ensure no orphaned CDEs
   - Ensure no broken references
   - Test impact analysis (trace CDE across all contexts)

5. **Documenting Rationale and Governance**
   - Explain semantic domain classification
   - Document criticality decisions
   - Record regulatory basis for PII/SENSITIVE_PII flags
   - Establish semantic ownership

---

**You are now ready to conduct enterprise-wide CDE discovery and generate the consolidated master registry plus business-context-specific flows and usage files. This forms the authoritative single source of truth for data governance across the entire enterprise.**

**Duration**: 2-4 weeks (comprehensive discovery phase)
**Prime Deliverable**: `master_cde_registry.tsv` (shared across all business_contexts)
**Secondary Deliverables**: Business-context-specific LINEAGE_FLOW and CDE_USAGE files
**Success Metric**: All semantic domains documented, no duplicates, full referential integrity, stakeholder consensus
