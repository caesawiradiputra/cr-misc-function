---
model: opus
---

# Update CDE (Mode B — Incremental Enhancement)

Perform surgical incremental updates to an **existing** CDE data model. Use this when a master registry already exists and you need to add CDEs, pipelines, consumers, or update transformations.

**Mode B: Incremental Registry Enhancement** — high-velocity updates (2-5 days per CDE).

## Context: $ARGUMENTS

If `$ARGUMENTS` describes the update (e.g., "add payment settlement CDE to payments context"), use that. Otherwise, ask the user what needs to be added or updated.

---

## Prerequisites Check

**Before anything else, verify master registry exists:**

```powershell
Test-Path "docs\cde\master_cde_registry.tsv"
```

- **If NOT exists** → STOP. This is Mode A, not Mode B. Use `/generate-cde` instead.
- **If exists** → Load it as base reference.

---

## Terminology

- **data_domain** — Semantic classification (`APPL`, `CUST`, `PAY`, `RISK`)
- **business_context** — Organizational boundary (`onboarding`, `payments`, `anti_fraud`)

**Mode B rule**: Do NOT redefine semantic domains. You are appending rows, not restructuring the master registry.

---

## Incremental Update Scenarios

### Scenario 1 — Add New CDE to Master Registry

When a new business entity is discovered (e.g., new Payment attribute).

**Process:**

1. Check master: Does `lineage_key = Payment.Settlement Method` already exist?
   - **EXISTS** → Reuse existing CDE ID (no duplication)
   - **NOT EXISTS** → Generate next sequence number (`CDE-PAY-006`, `CDE-PAY-007`, etc.)
2. Append ONE new row to `master_cde_registry.tsv` (all 12 columns populated)
3. Output: Updated master with +1 row

### Scenario 2 — Add New Pipeline to Existing Business_Context

When a new pipeline uses existing CDEs within an existing context.

**Process:**

1. Verify all CDEs referenced by new pipeline exist in master registry
2. Append new rows to `{context}_lineage_flow.tsv` — do not modify existing rows
3. Output: Updated lineage file with +N rows

### Scenario 3 — Add New Consumer/Usage Pattern

When an existing CDE is now consumed by a new system.

**Process:**

1. Verify CDE exists in master registry by `cde_id`
2. Append ONE new row to `{context}_cde_usage.tsv` — do not modify existing rows
3. Output: Updated usage file with +1 row

### Scenario 4 — Modify Transformation for Existing Pipeline Step

When transformation logic changes (e.g., phone normalization now includes validation).

**Process:**

1. Check policy: Does modification violate Cross-Context Transformation Semantics?
   - **Permitted**: Different contexts may transform the same CDE differently
   - **Forbidden**: Transformation cannot contradict master registry business definition
2. Append versioned/updated row — do not delete old row
3. Document reason for change in `notes` column
4. Output: Updated lineage file with clarified row

---

## Processing Steps

### Step 0 — Load and Validate Existing Registry

```powershell
Get-Content "docs\cde\master_cde_registry.tsv"
```

- Extract all existing `cde_id` values
- Check for duplicates
- Get current max sequence number per domain

### Step 1 — Semantic Duplicate Check

Before adding any new CDE:

- Search master for similar `lineage_key` values (e.g., `Payment.*` for payment domain)
- Search for similar `business_name` or `definition`
- Only add if truly new (not already represented by existing CDE)

### Step 2 — Assign Next Sequence Number

```text
Current max: CDE-PAY-005
Next: CDE-PAY-006
```

Sequence is per domain — `CDE-PAY-006` and `CDE-CUST-006` are independent sequences.

### Step 3 — Append (Never Replace)

- **Master registry**: append new CDE rows only
- **Context files**: append new pipeline/usage rows only
- **Never**: modify existing `cde_id` definitions
- **Never**: delete existing rows

### Step 4 — Referential Integrity Validation

After all updates, verify:

```text
Every cde_id in {context}_lineage_flow.tsv → exists in master_cde_registry.tsv ✅
Every cde_id in {context}_cde_usage.tsv → exists in master_cde_registry.tsv ✅
```

---

## Column Reference (Quick)

### Master Registry (12 columns)

`cde_id` | `data_domain` | `lineage_key` | `business_name` | `definition` | `data_type` | `data_sensitivity` | `is_pii` | `is_regulatory` | `business_criticality` | `data_owner` | `notes`

### Lineage Flow (17 columns)

`business_context` | `pipeline_name` | `cde_id` | `lineage_step` | `source_system` | `target_system` | `transformation_type` | `transformation_detail` | `source_field` | `target_field` | `is_pii_in_flight` | `encryption_required` | `sla_minutes` | `data_quality_check` | `error_handling` | `dependencies` | `notes`

### CDE Usage (8 columns)

`business_context` | `cde_id` | `consumer_system` | `consumption_purpose` | `data_quality_requirements` | `retention_policy` | `access_pattern` | `notes`

---

## Approved Transformation Types

`passthrough` | `cast` | `normalize` | `join` | `enrich` | `aggregate` | `derive` | `constant` | `upsert`

**Never invent new types.** Contact Data Governance to extend the vocabulary.

---

## Quality Checklist

- [ ] Checked master registry before adding — no semantic duplicates
- [ ] New CDE IDs follow correct sequence per domain
- [ ] All 12 master registry columns populated for new rows
- [ ] `transformation_type` uses only approved vocabulary
- [ ] Referential integrity verified: all `cde_id` in context files exist in master
- [ ] Existing rows not modified (append-only)
- [ ] No business definition altered for existing CDEs
- [ ] `notes` column documents reason for changes
