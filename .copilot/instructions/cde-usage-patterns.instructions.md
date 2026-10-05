---
description: 'CDE Usage Patterns: Business-context-specific documentation of who consumes CDEs and how'
applyTo: '**/*_cde_usage.tsv,**/usage/**/*.tsv'
---

# CDE Usage Patterns Instructions

## Overview

**CDE_USAGE** documents WHO uses each Common Data Element (CDE) within a specific business context, HOW they use it, and WHAT they need. It tracks consumption patterns, data quality requirements, and retention policies.

**Key Principle**: One row per CDE per consumer per consumption purpose, all referencing master CDE definitions.

---

## Purpose and Foreign Key Relationship

**Purpose**: Document WHO consumes CDEs in a specific business context and WHAT they need

**File**: `{business_context}_cde_usage.tsv` — One file per business context
- Examples: `onboarding_cde_usage.tsv`, `payments_cde_usage.tsv`, `anti_fraud_cde_usage.tsv`

**One row per**: Unique combination of `(cde_id + consumer_system + consumption_purpose)` within this business_context

**Foreign Key Relationship**:
- ✅ Every `cde_id` in CDE_USAGE MUST exist in `master_cde_registry.tsv`
- ✅ CDE_USAGE documents CONSUMPTION of a CDE in this business_context
- ✅ CDE **definition** stays in master registry (not duplicated here)

**Cross-References**:
- **Master Registry**: See [CDE Master Registry Instructions](./cde-master-registry.instructions.md)
- **Lineage Flow**: See [CDE Lineage Flow Instructions](./cde-lineage-flow.instructions.md)

---

## Column Specifications (8 Columns)

| Column | Type | Required | Description |
|--------|------|----------|-------------|
| **cde_id** | String | Yes | Foreign key to master CDE_REGISTRY. Links usage to CDE definition |
| **consumer_system** | String | Yes | System consuming the CDE (Postgres, Redis, Analytics Platform, ML System) |
| **consumption_purpose** | String | Yes | Why needed: realtime_ops, analytics_reporting, model_training, fraud_detection, caching |
| **consumer_team** | String | Yes | Team responsible for consumption (Risk Team, Analytics Team, Engineering Team) |
| **data_quality_requirement** | String | Yes | Quality SLA: NOT NULL, unique, valid_format, freshness < X, completeness > Y% |
| **retention_days** | Integer | Yes | How many days to retain in consumer system |
| **is_active** | String | Yes | Currently active consumption? (Yes/No) |
| **notes** | String | No | Additional context or special requirements |

---

## Data Validation Rules

### cde_id
- **Must exist**: In `master_cde_registry.tsv` (foreign key validation)
- **Format**: `CDE-{DOMAIN}-###` (e.g., `CDE-APPL-001`)

### consumer_system Format
- **Pattern**: Human-readable system name
- **Examples**: `Postgres`, `Redis`, `Analytics Platform`, `ML Training Pipeline`, `Flink State Store`
- **Be specific**: Not "Database" but "Postgres Operational Store"

### consumption_purpose Format
- **Pattern**: Lowercase with underscores
- **Examples**:
  - `realtime_ops` - Operational queries in production
  - `analytics_reporting` - BI dashboards and reports
  - `model_training` - ML model training data
  - `fraud_detection` - Real-time fraud scoring
  - `caching` - Performance optimization cache
  - `compliance_audit` - Regulatory audit trail
  - `customer_support` - Support team lookup tools

### access_pattern Format (Controlled Vocabulary)
- **Pattern**: Lowercase with underscores — standardized terms to document consumption patterns
- **Approved Values**:
  - `point_lookup` - CDE retrieved by single key/filter (e.g., "get user by ID", "retrieve account by number")
  - `range_query` - CDE queried with range conditions (e.g., "dates between X and Y", "amounts > threshold")
  - `join_key` - CDE used to join/correlate multiple datasets (e.g., "join on customer_id", "match on KTP")
  - `aggregation` - CDE used in group-by, count, sum, or statistical operations
  - `model_input` - CDE fed directly to ML model as feature or training data
- **Governance**: Only use approved vocabulary. New patterns require Data Governance approval to maintain consistency
- **Purpose**: Reduces schema drift, helps identify access patterns for performance tuning, documents consumption semantics for lineage tools

### consumer_team
- **Pattern**: Human-readable team name
- **Examples**: `LORA Team`, `Risk Team`, `Analytics Team`, `Engineering Team`, `Customer Support`
- **Must belong**: To this business_context (no cross-context consumers)

### data_quality_requirement Values
- **Comma-separated list** of specific, measurable requirements
- **Examples**:
  - `NOT NULL, unique` - Field must exist and be unique
  - `valid_email_format` - Must match email regex
  - `completeness > 99%` - At least 99% of records populated
  - `freshness < 1min` - Data updated within 1 minute
  - `freshness < 6h` - Data updated within 6 hours
  - `valid_format` - Follows expected format (e.g., E.164 for phone)
- **Be specific**: Not "good data" but measurable constraints

### retention_days
- **Positive integer**: Number of days to keep in consumer system
- **Examples**:
  - `1` - Realtime cache (1 day)
  - `90` - Model training data (3 months)
  - `365` - Operational data (1 year)
  - `1825` - Analytics/compliance (5 years)
  - `2555` - Long-term compliance (7 years, common for financial regulations)
- **Consider**: Balance between business need and storage/compliance costs

### is_active Values
- `Yes` - Currently in use, active consumption
- `No` - Legacy consumption (deprecated) or planned consumption (not yet active)

---

## Example CDE_USAGE

### Onboarding Business Context

**File**: `onboarding_cde_usage.tsv`

```tsv
cde_id	consumer_system	consumption_purpose	access_pattern	consumer_team	data_quality_requirement	retention_days	is_active	notes
CDE-APPL-001	Postgres	realtime_ops	point_lookup	LORA Team	NOT NULL, unique, valid_format	365	Yes	Primary operational store for compliance; retrieved by application_id
CDE-APPL-001	Redis	caching	point_lookup	Engineering Team	NOT NULL	1	Yes	Realtime lookup cache for fraud score computation
CDE-APPL-001	Analytics Platform	analytics_reporting	aggregation	Analytics Team	completeness > 99%, valid_format	2555	Yes	Long-term compliance and audit reporting (7 years regulatory requirement)
CDE-APPL-002	Postgres	realtime_ops	join_key	LORA Team	NOT NULL, unique	365	Yes	Primary application tracking; used to join with status tables
CDE-APPL-002	Kafka	downstream_event_stream	model_input	Flow Platform	NOT NULL	30	Yes	Event stream for orchestration and model feature engineering
CDE-CUST-001	Analytics Platform	model_training	model_input	Risk Team	NOT NULL, freshness < 6h	90	Yes	Age-based risk scoring model training; direct feature input
CDE-CUST-001	Redis	caching	range_query	Engineering Team	NOT NULL, freshness < 1min	1	Yes	Real-time age verification; queried with date ranges
```

**Note**: All `cde_id` values reference entries in `master_cde_registry.tsv`. This file contains **only Onboarding business_context consumers**.

---

## Multiple Consumers Pattern

**One CDE, Multiple Consumers with Different Requirements**

```
CDE-CUST-001 (Customer.Email Address)

Postgres (realtime_ops):
├─ Purpose: Operational queries, customer lookup
├─ Quality: NOT NULL, valid_email_format
├─ Retention: 365 days
└─ Team: LORA Team

Redis (caching):
├─ Purpose: Performance optimization, fast lookup
├─ Quality: NOT NULL, freshness < 1min
├─ Retention: 1 day (cache TTL)
└─ Team: Engineering Team

Analytics Platform (analytics_reporting):
├─ Purpose: BI dashboards, compliance reporting
├─ Quality: completeness > 99%, valid_format
├─ Retention: 2555 days (7 years compliance)
└─ Team: Analytics Team

ML Training Pipeline (model_training):
├─ Purpose: Customer churn prediction model
├─ Quality: NOT NULL, freshness < 6h
├─ Retention: 90 days (model retraining window)
└─ Team: Risk Team
```

**Key Insight**: Same CDE consumed by 4 different systems with 4 different retention policies and quality requirements, all documented as separate rows in CDE_USAGE.

---

## Best Practices

### CDE_USAGE Maintenance
- ✅ **One row per consumer per purpose** — Multiple teams can consume same CDE for different purposes
- ✅ **Specific quality requirements** — Not generic "good data" but measurable rules (NOT NULL, unique, freshness)
- ✅ **Appropriate retention** — Balance between business need and storage/compliance costs
- ✅ **Track active state** — Distinguish active from legacy or planned consumption
- ✅ **Reference master** — All `cde_id` must exist in `master_cde_registry.tsv`
- ✅ **Business_context scope** — Include ONLY this business_context's consumers

### Quality Requirements Guidelines
- ✅ **Be measurable**: `completeness > 99%` not "mostly complete"
- ✅ **Be specific**: `freshness < 1min` not "pretty fresh"
- ✅ **Use standard constraints**: NOT NULL, unique, valid_format, valid_email_format
- ✅ **Include thresholds**: `completeness > 95%`, `freshness < 6h`
- ❌ **Avoid vague**: "good quality", "accurate data", "clean data"

### Retention Policy Guidelines
- ✅ **Operational data**: 1-365 days (typical)
- ✅ **Analytics/BI**: 365-1825 days (1-5 years)
- ✅ **Compliance/Audit**: 1825-2555 days (5-7 years, regulatory requirements)
- ✅ **Realtime cache**: 1 day (performance optimization only)
- ✅ **Model training**: 90-365 days (depends on retraining frequency)

### Conflict Detection
- ⚠️ **Watch for**: Same CDE with conflicting retention within same business_context
  - Example: Consumer A says 1 day, Consumer B says forever
  - Document reason in notes field if intentional
- ⚠️ **Watch for**: Same consumer system with duplicate consumption purposes
  - May indicate missing distinction in `consumption_purpose` field

---

## Quality Checklist

### CDE_USAGE Validation
- [ ] All 9 columns present (8 required + optional notes)
- [ ] All `cde_id` values exist in `master_cde_registry.tsv` ✅ **CRITICAL: Referential integrity**
- [ ] All `consumer_system` and `consumer_team` identifiable
- [ ] All `consumer_team` belong to this business_context (no cross-context consumers)
- [ ] All `consumption_purpose` clearly describes usage
- [ ] All `access_pattern` values from approved vocabulary (point_lookup, range_query, join_key, aggregation, model_input)
- [ ] All `data_quality_requirement` specific and measurable
- [ ] All `retention_days` positive integers appropriate for purpose
- [ ] All `is_active` accurately reflects current status (Yes/No)
- [ ] No conflicting retention policies within same business_context (unless documented)
- [ ] No empty cells in required columns
- [ ] File contains **only consumers from this business_context**

### Cross-File Integrity
- [ ] Every `cde_id` exists in master registry
- [ ] All `cde_id` consistent format (e.g., CDE-APPL-001)
- [ ] No duplicate rows (same `cde_id + consumer_system + consumption_purpose`)
- [ ] Quality requirements align with master registry data classification
- [ ] Retention policies comply with regulatory flags in master registry

---

## Common Usage Patterns

### Pattern 1: Multi-Tiered Storage
```
CDE-APPL-001 (Applicant.KTP Number)
├─ Hot tier: Redis (1 day, realtime_ops)
├─ Warm tier: Postgres (365 days, operational queries)
└─ Cold tier: Analytics Platform (2555 days, compliance_audit)
```

### Pattern 2: Purpose-Driven Retention
```
CDE-CUST-001 (Customer.Birth Date)
├─ Fraud detection: Redis (1 day, caching)
├─ Risk scoring: ML Pipeline (90 days, model_training)
├─ Customer service: Postgres (365 days, realtime_ops)
└─ Compliance: Analytics Platform (2555 days, compliance_audit)
```

### Pattern 3: Active vs. Legacy Consumption
```
CDE-PAY-001 (Payment.Transaction ID)
├─ Current: Postgres (realtime_ops, is_active=Yes, 365 days)
├─ Legacy: MySQL (analytics_reporting, is_active=No, 1825 days) — Being phased out
└─ Planned: Snowflake (analytics_reporting, is_active=No, 1825 days) — Migration pending
```

---

## File Organization

### Directory Structure
```
docs/data-lineage/
├── master_cde_registry.tsv                 (Master CDE definitions)
├── onboarding/
│   ├── onboarding_lineage_flow.tsv
│   └── onboarding_cde_usage.tsv            (THIS FILE TYPE - Onboarding consumers)
├── payments/
│   ├── payments_lineage_flow.tsv
│   └── payments_cde_usage.tsv              (THIS FILE TYPE - Payments consumers)
└── (other business_contexts...)
```

### Governance Model

| Aspect | Details |
|--------|---------|
| **Owner** | Business_Context Product Manager |
| **Update Frequency** | As consuming systems change within business_context |
| **Scope** | Only consumers and consumption patterns for this business_context |
| **Naming** | `{business_context}_cde_usage.tsv` (lowercase, underscores) |

---

## Cross-References

- **Master Registry**: See [CDE Master Registry Instructions](./cde-master-registry.instructions.md) for CDE definitions
- **Lineage Flow**: See [CDE Lineage Flow Instructions](./cde-lineage-flow.instructions.md) for pipeline documentation
- **Generation Prompts**: See [CDE Prompts README](../prompts/README.md) for Mode A vs. Mode B selection
