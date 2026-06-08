# Generate CDE Spreadsheet

Generate a unified CDE spreadsheet covering: Master Registry + Business-Context-Specific Lineage Flows + CDE Usage patterns. Produces TSV files ready for Excel or Google Sheets.

## Context: $ARGUMENTS

If `$ARGUMENTS` specifies scope (business context, domain, or system), use that. Otherwise, ask for the scope.

---

## Clarification Protocol (Run First)

Before generating any files:

1. **Read existing project files**:

   ```powershell
   # Check if CDE files already exist
   Test-Path "docs\cde\master_cde_registry.tsv"
   Get-ChildItem -Path "docs\cde" -Filter "*.tsv" -ErrorAction SilentlyContinue
   ```

2. **Ask for missing information** (do not assume):
   - Which business_contexts are in scope?
   - What semantic domains exist (Applicant, Customer, Payment, Risk, etc.)?
   - Are there existing pipelines to document?
   - What data classification requirements apply?
   - What's the target Python version? (for code examples)

---

## Output: 3-File CDE Model (per business_context)

### File 1 — Master CDE Registry (Enterprise-Wide)

**Filename**: `docs/cde/master_cde_registry.tsv`
**Format**: 12-column TSV
**One row per unique CDE** across all business_contexts

| Column | Type | Rules |
| --- | --- | --- |
| `cde_id` | `CDE-{DOMAIN}-{SEQ}` | Unique, sequential per domain |
| `data_domain` | String | `APPL`, `CUST`, `PAY`, `RISK`, etc. |
| `lineage_key` | `{Entity}.{Attribute}` | e.g., `Applicant.KTP Number` |
| `business_name` | String | Human-readable name |
| `definition` | String | Business definition (no technical detail) |
| `data_type` | String | `STRING`, `INTEGER`, `DECIMAL`, `DATE`, `BOOLEAN` |
| `data_sensitivity` | Enum | `PUBLIC`, `INTERNAL`, `PII`, `SENSITIVE_PII`, `CONFIDENTIAL`, `METADATA` |
| `is_pii` | Boolean | `TRUE` / `FALSE` |
| `is_regulatory` | Boolean | `TRUE` / `FALSE` |
| `business_criticality` | Enum | `HIGH`, `MEDIUM`, `LOW` |
| `data_owner` | String | Owning team/domain |
| `notes` | String | Optional context |

### File 2 — Lineage Flow (Per Business Context)

**Filename**: `docs/cde/{business_context}_lineage_flow.tsv`
**Format**: 17-column TSV
**One row per unique `(pipeline_name + cde_id + lineage_step)`**

Key columns:

- `business_context` — Context name (e.g., `onboarding`)
- `pipeline_name` — Pipeline identifier
- `cde_id` — **Foreign key** → must exist in master registry
- `lineage_step` — Integer step number within pipeline
- `source_system` — Source table/system
- `target_system` — Target table/system
- `transformation_type` — **Approved only**: `passthrough`, `cast`, `normalize`, `join`, `enrich`, `aggregate`, `derive`, `constant`, `upsert`
- `transformation_detail` — Specific rule (e.g., "normalize to E.164 format")
- `source_field` — Source column name
- `target_field` — Target column name
- `is_pii_in_flight` — Boolean
- `encryption_required` — Boolean
- `sla_minutes` — Processing SLA
- `data_quality_check` — Validation rule applied
- `error_handling` — Error strategy
- `dependencies` — Upstream dependencies
- `notes` — Optional

### File 3 — CDE Usage (Per Business Context)

**Filename**: `docs/cde/{business_context}_cde_usage.tsv`
**Format**: 8-column TSV
**One row per unique `(cde_id + consumer_system + consumption_purpose)`**

| Column | Description | Example |
| --- | --- | --- |
| `business_context` | Context name | `onboarding` |
| `cde_id` | FK → master registry | `CDE-APPL-001` |
| `consumer_system` | Consuming system | `CRM_System` |
| `consumption_purpose` | Why it's used | `Identity verification` |
| `data_quality_requirements` | Specific, measurable rules | `Must match national ID format XX.XXXX.XXXX` |
| `retention_policy` | How long kept | `7 years (regulatory)` |
| `access_pattern` | Access method | `Real-time API`, `Batch nightly`, `On-demand query` |
| `notes` | Optional | |

---

## Processing Steps

1. **Load existing registry** (if `master_cde_registry.tsv` exists)
   - Extract all current `cde_id` values and sequences
   - Continue from existing max sequence per domain

2. **Extract CDEs from project**
   - Identify data entities from code (models, repositories, schemas)
   - Map to semantic domains (APPL, CUST, PAY, RISK)
   - Normalize to `{Entity}.{Attribute}` format for `lineage_key`

3. **Map lineage flows**
   - Identify pipelines per business_context
   - Document each transformation step with approved types
   - Assign SLA values from project docs/configs

4. **Document consumption patterns**
   - Identify which systems consume which CDEs
   - Capture quality requirements (specific and measurable — not generic)
   - Document retention policies per regulatory context

5. **Validate referential integrity**

   ```text
   For every row in {context}_lineage_flow.tsv:
     → cde_id MUST exist in master_cde_registry.tsv

   For every row in {context}_cde_usage.tsv:
     → cde_id MUST exist in master_cde_registry.tsv
   ```

---

## Governance Rules

- **Master registry = single source of truth**: No CDE defined twice
- **Append-only**: Never delete or modify existing master rows
- **Transformation vocabulary**: Only approved types — never invent new ones
- **Quality requirements**: Must be specific and measurable (e.g., "Must match regex `^[0-9]{16}$`", not just "Must be valid")
- **Retention policy examples**:
  - Operational: `30 days`
  - Analytics: `2 years`
  - Compliance/regulatory: `7 years`

---

## Output Structure

```text
docs/cde/
├── master_cde_registry.tsv          # Enterprise-wide, always present
├── onboarding_lineage_flow.tsv      # Per business_context
├── onboarding_cde_usage.tsv
├── payments_lineage_flow.tsv
├── payments_cde_usage.tsv
├── anti_fraud_lineage_flow.tsv
├── anti_fraud_cde_usage.tsv
└── ...
```

---

## Quality Checklist

- [ ] All `cde_id` values unique in master registry
- [ ] CDE ID sequences correct per domain (CDE-APPL-001, CDE-APPL-002, etc.)
- [ ] All 12 master registry columns populated for every row
- [ ] `transformation_type` uses only approved vocabulary
- [ ] All `cde_id` in context files exist in master (referential integrity)
- [ ] `data_quality_requirements` are specific and measurable
- [ ] `retention_policy` specifies duration and reason
- [ ] No duplicate rows in any file
- [ ] TSV format valid (no extra commas, proper tab delimiters)
- [ ] Files saved to `docs/cde/` directory
