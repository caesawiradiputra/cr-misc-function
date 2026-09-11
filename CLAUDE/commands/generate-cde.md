---
model: opus
---

# Generate CDE (Mode A — Initial Setup)

Build an enterprise CDE (Common Data Element) data model from scratch. Use this for creating a master CDE registry when none exists yet.

**Mode A: Initial Registry Establishment** — comprehensive discovery phase (2-4 weeks typical).

## Context: $ARGUMENTS

If `$ARGUMENTS` specifies business contexts, systems, or domain areas, use that as input. Otherwise, run the discovery protocol below.

---

## Terminology

- **data_domain** — Semantic classification of the CDE (e.g., `APPL`, `CUST`, `PAY`, `RISK`)
  - Describes WHAT the data is semantically
  - Example: `APPL` = Applicant data, `CUST` = Customer data
- **business_context** — Organizational boundary where data flows (e.g., `onboarding`, `payments`, `anti_fraud`)
  - Describes WHERE/WHO uses the data
  - Same CDE can appear in multiple business_contexts

**Key example**: `CDE-APPL-001` (Applicant KTP Number) has `data_domain=APPL` but flows through `onboarding`, `collection`, and `anti_fraud` business_contexts.

---

## Output Files

1. **`master_cde_registry.tsv`** — Enterprise-wide single source of truth (12 columns)
2. **`{business_context}_lineage_flow.tsv`** — Data movement per context (17 columns)
3. **`{business_context}_cde_usage.tsv`** — Data consumption per context (8 columns)

---

## Discovery Protocol

**Before generating any files**, analyze the project and ask for missing information:

1. Read project files to understand:
   - What business_contexts does this enterprise support?
   - Check: `app/connections/`, `repositories/`, `docs/`, config files
   - What data sources/databases are referenced?
   - Check: database strategies, connection configs

2. Ask for clarification if any of these are missing:
   - List of all semantic domains (Applicant, Customer, Payment, Risk, etc.)
   - List of all business_contexts in scope
   - Pipelines within each business_context
   - Data classification requirements (PII, SENSITIVE_PII, CONFIDENTIAL)
   - Regulatory context (GDPR, local laws, compliance flags)

---

## Master CDE Registry Format (12 columns, TSV)

| Column | Description | Example |
| --- | --- | --- |
| `cde_id` | Unique ID: `CDE-{DOMAIN}-{SEQ}` | `CDE-APPL-001` |
| `data_domain` | Semantic domain code | `APPL` |
| `lineage_key` | `{Entity}.{Attribute}` | `Applicant.KTP Number` |
| `business_name` | Human-readable business name | `Applicant KTP Number` |
| `definition` | Business definition | `National ID card number...` |
| `data_type` | Data type | `STRING` |
| `data_sensitivity` | Classification | `SENSITIVE_PII` |
| `is_pii` | PII flag | `TRUE` |
| `is_regulatory` | Regulatory flag | `TRUE` |
| `business_criticality` | Impact level | `HIGH` |
| `data_owner` | Owning team/domain | `Credit Risk` |
| `notes` | Additional context | `` |

**CDE ID Sequence**: Each domain has its own sequence starting at 001. Example: `CDE-APPL-001`, `CDE-APPL-002`, `CDE-CUST-001`, `CDE-PAY-001`.

**Data sensitivity values**: `PUBLIC`, `INTERNAL`, `PII`, `SENSITIVE_PII`, `CONFIDENTIAL`, `METADATA`

**Business criticality values**: `HIGH`, `MEDIUM`, `LOW`

---

## Lineage Flow Format (17 columns, TSV)

One row per unique `(pipeline_name + cde_id + lineage_step)` per business_context.

Key columns:

- `business_context` — Which context this flow belongs to
- `pipeline_name` — Name of the data pipeline
- `cde_id` — Foreign key → must exist in `master_cde_registry.tsv`
- `lineage_step` — Step number (1, 2, 3...)
- `source_system` — Source system/table
- `target_system` — Target system/table
- `transformation_type` — From approved vocabulary only
- `sla_minutes` — Processing SLA

**Approved transformation_type values** (no others allowed):
`passthrough`, `cast`, `normalize`, `join`, `enrich`, `aggregate`, `derive`, `constant`, `upsert`

---

## CDE Usage Format (8 columns, TSV)

One row per unique `(cde_id + consumer_system + consumption_purpose)` per business_context.

Key columns:

- `business_context` — Which context this usage belongs to
- `cde_id` — Foreign key → must exist in `master_cde_registry.tsv`
- `consumer_system` — System consuming this CDE
- `consumption_purpose` — Why this system uses it
- `data_quality_requirements` — Specific, measurable quality rules
- `retention_policy` — How long data is kept
- `access_pattern` — How data is accessed (batch, real-time, etc.)

---

## Discovery Phases

### Phase 1 — Stakeholder Discovery (1-2 weeks)

1. Identify all semantic domains across business_contexts
2. Map which business_contexts use which semantic domains
3. Document regulatory and compliance requirements
4. Establish data classification scheme

### Phase 2 — Master Registry Consolidation (1 week)

1. Merge all discovered CDEs into single master registry
2. Eliminate duplicates and conflicting definitions
3. Assign unique CDE IDs per domain sequence
4. Get consensus from Data Governance stakeholders

### Phase 3 — Business-Context Mapping (1-1.5 weeks)

1. For each business_context, document pipelines using master CDEs
2. Create `{context}_lineage_flow.tsv` files
3. Create `{context}_cde_usage.tsv` files
4. **Validate referential integrity**: all `cde_id` in context files must exist in master

---

## Governance Rules

- **Master registry is single source of truth**: CDE-APPL-001 defined once, referenced everywhere
- **Append-only for business_context files**: never modify master definitions
- **Transformation vocabulary**: only approved types — never invent new ones
- **Cross-context semantics**: different contexts may apply different technical transforms to the same CDE, but must NOT alter the business definition from master

**Foreign key validation:**

```text
All cde_id in {context}_lineage_flow.tsv → must exist in master_cde_registry.tsv
All cde_id in {context}_cde_usage.tsv → must exist in master_cde_registry.tsv
```

---

## Output Location

Save to `docs/cde/`:

```text
docs/cde/
├── master_cde_registry.tsv
├── onboarding_lineage_flow.tsv
├── onboarding_cde_usage.tsv
├── payments_lineage_flow.tsv
├── payments_cde_usage.tsv
└── ... (one set per business_context)
```
