---
description: 'Master CDE Registry: Enterprise-wide single source of truth for Common Data Element definitions'
applyTo: '**/master_cde_registry.tsv,**/cde_registry.tsv'
---

# CDE Master Registry Instructions

## Overview

The **Master CDE Registry** is the authoritative, enterprise-wide single source of truth for ALL Common Data Element (CDE) definitions. It contains the **business meaning** of each data element but excludes technical transport or pipeline details.

**Key Principle**: One CDE, one definition, referenced everywhere.

---

## Terminology Clarification

**See `.github/references/cde-terminology.md` for detailed explanation of:**
- **data_domain** — Semantic classification (e.g., APPL, CUST, PAY, RISK)
- **business_context** — Organizational boundary (e.g., Onboarding, Payments, Anti-Fraud)

Quick example: CDE-APPL-001 (Applicant.KTP Number) has **data_domain=APPL** and may be referenced by multiple business_context files (onboarding, collections, anti_fraud).

---

## Purpose and Governance

**Purpose**: Document WHAT each data element means from a business perspective

**File**: `master_cde_registry.tsv` (ONE file for entire enterprise)

**One row per**: Unique CDE identified by `cde_id`

**Governance**:
- **Maintained by**: Data Governance team
- **Updated when**: New CDE is discovered across any business context
- **Never duplicate**: Each `cde_id` defined once, referenced by all business_context-specific flow and usage files

**Cross-References**:
- **Business-Context Flows**: See [CDE Lineage Flow Instructions](./cde-lineage-flow.instructions.md)
- **Business-Context Usage**: See [CDE Usage Patterns Instructions](./cde-usage-patterns.instructions.md)

---

## Column Specifications (12 Columns)

| Column | Type | Required | Description |
|--------|------|----------|-------------|
| **cde_id** | String | Yes | Stable CDE identifier (format: `CDE-{data_domain}-{NUMBER}`, e.g., `CDE-APPL-001`) |
| **lineage_key** | String | Yes | Stable logical name (format: `Entity.Attribute`, e.g., `Applicant.KTP Number`) |
| **data_domain** | String | Yes | Semantic classification (Applicant, Customer, Payment, Risk, Order, Account) |
| **logical_entity** | String | Yes | Business entity name (Applicant, Application, Spouse, Vehicle, Customer) |
| **logical_attribute** | String | Yes | Human-readable attribute name (KTP Number, Birth Date, Monthly Income) |
| **business_definition** | String | Yes | Authoritative business meaning in clear, non-technical language (15-100 words) |
| **semantic_owner** | String | Yes | Team or person who defines the meaning (e.g., LORA Team, Risk Team) |
| **data_classification_level** | String | Yes | PUBLIC, PII, SENSITIVE_PII, CONFIDENTIAL, METADATA |
| **regulatory_flag** | String | Yes | Yes/No - Subject to compliance/regulation |
| **criticality_level** | String | Yes | HIGH, MEDIUM, LOW - Business impact level |
| **created_at** | String | Yes | ISO 8601 timestamp of CDE creation |
| **updated_at** | String | Yes | ISO 8601 timestamp of last update |

---

## Data Validation Rules

### cde_id Format
- **Pattern**: `CDE-{data_domain}-{NUMBER}`
- **Examples**: `CDE-APPL-001`, `CDE-CUST-042`, `CDE-RISK-105`
- **data_domain**: Semantic domain abbreviation (3-4 uppercase letters)
  - APPL = Applicant data
  - CUST = Customer data
  - PAY = Payment data
  - RISK = Risk data
- **NUMBER**: Sequential number unique within data_domain (zero-padded to 3 digits)
- **Must be stable**: Never change once assigned

### lineage_key Format
- **Pattern**: `{Entity}.{Attribute}`
- **Examples**: `Applicant.KTP Number`, `Application.Application ID`, `Customer.Email Address`
- **Character set**: Alphanumeric, spaces, hyphens allowed
- **Must be unique**: No duplicate lineage_key across entire registry
- **Represents**: Stable logical name independent of technical column names

### data_classification_level Values
- `PUBLIC` - No access restrictions
- `METADATA` - System or metadata fields
- `PII` - Personally Identifiable Information
- `SENSITIVE_PII` - Highly sensitive PII (SSN, KTP, passport, financial data)
- `CONFIDENTIAL` - Business confidential data

### criticality_level Values
- `HIGH` - Critical to business operations, widely used, regulatory importance
- `MEDIUM` - Important but not critical, used in specific processes
- `LOW` - Supplemental data, limited usage

### regulatory_flag Values
- `Yes` - Subject to compliance (GDPR, CCPA, HIPAA, local regulations)
- `No` - No regulatory constraints

### Timestamp Format
- **ISO 8601**: `YYYY-MM-DDTHH:MM:SSZ`
- **Example**: `2025-06-15T10:30:00Z`

---

## Example Master CDE_REGISTRY

```tsv
cde_id	definition_version	lineage_key	data_domain	logical_entity	logical_attribute	business_definition	semantic_owner	approved_by	data_classification_level	regulatory_flag	criticality_level	created_at	updated_at
CDE-APPL-001	1.0	Applicant.KTP Number	Applicant	Applicant	KTP Number	National identity card number issued by Indonesian government. Primary identifier for applicant verification and compliance.	LORA Team	LORA Governance Lead	SENSITIVE_PII	Yes	HIGH	2026-02-13T10:00:00Z	2026-02-13T10:00:00Z
CDE-APPL-002	1.0	Application.Application ID	Application	Application	Application ID	Unique system-generated identifier for each application submission. Used for end-to-end tracking and compliance reporting.	LORA Team	LORA Governance Lead	PII	No	HIGH	2026-02-13T10:00:00Z	2026-02-13T10:00:00Z
CDE-CUST-001	1.0	Customer.Email Address	Customer	Customer	Email Address	Primary email address for customer contact and account recovery. Validated at registration.	BRAVO Team	LORA Governance Lead	PII	Yes	HIGH	2026-02-13T10:00:00Z	2026-02-13T10:00:00Z
CDE-PAY-001	1.0	Payment.Transaction ID	Payment	Payment	Transaction ID	Unique identifier for each payment transaction in the system. Used for reconciliation and fraud prevention.	Payments Team	Anti-Fraud Chief Data Steward	PII	No	HIGH	2026-02-13T10:00:00Z	2026-02-13T10:00:00Z
```

**Note**: This master registry is **shared across all business_contexts** (Onboarding, Payments, Collection, Anti-Fraud). No duplication. `data_domain` shows SEMANTIC classification (Applicant, Application, Customer, Payment), not the business_context.

---

## CDE ID Sequence Management

### Check Existing Registry First
✅ **Before creating new CDEs**, load existing `master_cde_registry.tsv` from `docs/data-lineage/` directory

### Reuse Existing CDE IDs
✅ **If CDE already exists** in registry (e.g., `CDE-APPL-001`), use that ID in business_context files
❌ **Never create duplicate** CDE with different ID for same logical entity

### Increment Sequence by data_domain
✅ **For new CDEs**, find the highest sequence number within that data_domain:
- If `CDE-APPL-001` and `CDE-APPL-002` exist, next NEW Applicant CDE is `CDE-APPL-003`
- If `CDE-CUST-001` exists, next NEW Customer CDE is `CDE-CUST-002`
- **Format**: Always zero-pad to 3 digits: `CDE-APPL-001` (not `CDE-APPL-1`)

### Preserve Existing Metadata
✅ **Never overwrite** existing CDE definitions unless explicitly instructed by Data Governance
✅ If CDE exists, reference it by ID only in business_context files

### Single Source of Truth
✅ Master registry is **authoritative** for `cde_id` assignments
✅ Once assigned, maintain consistency across all business_contexts

---

## Governance Policies

### Transformation Vocabulary Governance
- **Authoritative Maintainer**: Data Governance team defines and maintains `transformation_type` vocabulary
- **Approved Types**: passthrough, cast, normalize, join, enrich, aggregate, derive, constant, upsert
- **Policy**: Each business_context uses ONLY approved transformation types
- **Why**: Prevents semantic fragmentation where same operation has different names across business_contexts
- **Extension**: New transformation types require Data Governance approval before use

### Cross-Business-Context Transformation Semantics Policy
- **Permitted**: Different business_contexts may apply different technical transformations to the SAME CDE
  - Example: Onboarding normalizes phone to E.164 format; Collections hashes phone for matching
  - Both reference same `CDE-CUST-001` (Customer.Phone) from master registry
- **Not Permitted**: Transformations must NOT alter the business definition from master registry
  - If master defines "Phone = International format per E.164", all transformations must respect that semantic meaning
  - Technical transformations (normalization, hashing, masking) are **independent of business semantics**
- **Governance Check**: Confirm transformation type does not contradict master registry business definition
- **Impact**: Ensures single source of truth for meaning + technical flexibility per context

### CDE Identification Criteria
A data element qualifies as a CDE if it meets:
- ✅ Used in 2+ downstream systems
- ✅ Appears in 2+ logical processes
- ✅ Has enterprise-wide business definition
- ✅ Subject to compliance/regulatory oversight

### Data Sensitivity Classification
- **Risk-based assignment**: Higher sensitivity = more restrictive controls
- **Regulatory requirements**: PII and SENSITIVE_PII require enhanced governance
- **Escalation protocol**: Any PII/SENSITIVE_PII must have documented:
  - Compliance framework (GDPR, CCPA, HIPAA, etc.)
  - Data retention policy
  - Access control specifications

---

## Best Practices

### Master Registry Maintenance
- ✅ **One row per unique CDE** — Single point of definition across entire enterprise
- ✅ **Never duplicate cde_id** — CDE-APPL-001 defined once, referenced everywhere
- ✅ **Stable identifiers** — cde_id should never change over time
- ✅ **Business-focused naming** — Use business terminology, not technical column names
  - ✅ `Applicant.KTP Number` (clear, business-focused)
  - ❌ `app.ktp_num` (too technical)
- ✅ **Clear definitions** — Non-technical, 15-100 words, understandable to business users
- ✅ **Consistent logical names** — Same CDE has same `lineage_key` everywhere
- ✅ **Include all domains** — Registry includes CDEs from all business_contexts
- ❌ **Never leave empty cells** — Use "N/A" only if truly not applicable

---

## Quality Checklist

### Master Registry Validation
- [ ] All 14 columns populated in every row
- [ ] All `cde_id` values globally unique
- [ ] All `cde_id` follow format: `CDE-{DOMAIN}-###` (e.g., `CDE-APPL-001`)
- [ ] All `definition_version` follow semantic versioning (e.g., 1.0, 1.1, 2.0)
- [ ] All `lineage_key` values unique and follow `Entity.Attribute` format
- [ ] Each `lineage_key` represents distinct business concept (no duplicate definitions)
- [ ] All `approved_by` identify valid governance authorities
- [ ] All `data_classification_level` values from approved list
- [ ] All business definitions clear, non-technical, 15-100 words each
- [ ] All `semantic_owner` teams current and identifiable
- [ ] All `criticality_level` justified (HIGH for regulatory/widely-used, etc.)
- [ ] All timestamps valid ISO 8601 format
- [ ] No empty cells in required columns
- [ ] This file is single source of truth (no duplicate registries exist)

### Cross-File Integrity
- [ ] All `cde_id` in business_context LINEAGE_FLOW files exist in master registry
- [ ] All `cde_id` in business_context CDE_USAGE files exist in master registry
- [ ] All `cde_id` consistent across all files (e.g., CDE-APPL-001, not CDE-APP-001)
- [ ] Business definitions consistent with usage in business_context files
- [ ] Impact analysis test: Can find all business_contexts using CDE-APPL-001

---

## File Organization

### Directory Structure
```
docs/data-lineage/
├── master_cde_registry.tsv                 (THIS FILE - Enterprise source of truth)
├── onboarding/
│   ├── onboarding_lineage_flow.tsv         (References master via cde_id)
│   └── onboarding_cde_usage.tsv            (References master via cde_id)
├── payments/
│   ├── payments_lineage_flow.tsv
│   └── payments_cde_usage.tsv
└── (other business_contexts...)
```

### Governance Model

| Aspect | Details |
|--------|---------|
| **Owner** | Data Governance Team |
| **Update Frequency** | As new CDEs discovered; changes trigger business_context re-review |
| **Scope** | All CDEs across entire enterprise |
| **Naming** | `master_cde_registry.tsv` (always singular, lowercase) |

---

## Cross-References

- **Lineage Tracking**: See [CDE Lineage Flow Instructions](./cde-lineage-flow.instructions.md) for pipeline flow documentation
- **Usage Patterns**: See [CDE Usage Patterns Instructions](./cde-usage-patterns.instructions.md) for consumption documentation
- **Generation Prompts**: See [CDE Prompts README](../prompts/README.md) for Mode A (initial setup) vs. Mode B (incremental updates)
