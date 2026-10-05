---
name: update-cde
version: "1.0.0"
updated: "2026-06-18"
related_skills:
  - generate-cde
  - generate-cde-spreadsheet
description: Perform surgical incremental updates to an existing CDE data model (Mode B). Add CDEs, pipelines, consumers, or update transformations to an existing master registry. Use when the user triggers /update-cde or asks to update an existing CDE registry.
---

# Update CDE (Mode B — Incremental Enhancement)

Perform surgical incremental updates to an **existing** CDE data model. Use when a master registry already exists.

**Mode B: Incremental Registry Enhancement** — high-velocity updates.

## Context

If arguments describe the update (e.g., "add payment settlement CDE to payments context"), use that. Otherwise, ask the user what needs to be added or updated.

## Prerequisites Check

**Before anything else, verify master registry exists:**

```powershell
Test-Path "docs/cde/master_cde_registry.tsv"
```

- **If NOT exists** -> STOP. This is Mode A. Use `/generate-cde` instead.
- **If exists** -> Load it as base reference.

## Terminology

> Full terminology, column definitions, and governance rules: see [_shared/cde-definitions.md](../_shared/cde-definitions.md).

- **data_domain** — Semantic classification (`APPL`, `CUST`, `PAY`, `RISK`)
- **business_context** — Organizational boundary (`onboarding`, `payments`, `anti_fraud`)

**Mode B rule**: Do NOT redefine semantic domains. You are appending rows, not restructuring.

## Incremental Update Scenarios

### Scenario 1 — Add New CDE to Master Registry

1. Check master: Does `lineage_key` already exist?
   - **EXISTS** -> Reuse existing CDE ID
   - **NOT EXISTS** -> Generate next sequence number
2. Append ONE new row to `master_cde_registry.tsv` (all 12 columns)

### Scenario 2 — Add New Pipeline to Existing Business_Context

1. Verify all CDEs referenced by new pipeline exist in master
2. Append new rows to `{context}_lineage_flow.tsv`

### Scenario 3 — Add New Consumer/Usage Pattern

1. Verify CDE exists in master by `cde_id`
2. Append ONE new row to `{context}_cde_usage.tsv`

### Scenario 4 — Modify Transformation for Existing Pipeline Step

1. Check: transformation cannot contradict master registry business definition
2. Append versioned/updated row — do not delete old row
3. Document reason in `notes` column

## Processing Steps

### Step 0 — Load and Validate Existing Registry
Extract all existing `cde_id` values, check for duplicates, get max sequence per domain.

### Step 1 — Semantic Duplicate Check
Search master for similar `lineage_key` values and `business_name`/`definition`. Only add if truly new.

### Step 2 — Assign Next Sequence Number
Sequence is per domain — `CDE-PAY-006` and `CDE-CUST-006` are independent.

### Step 3 — Append (Never Replace)
- **Master registry**: append new CDE rows only
- **Context files**: append new pipeline/usage rows only
- **Never**: modify existing `cde_id` definitions or delete rows

### Step 4 — Referential Integrity Validation
Every `cde_id` in context files must exist in master.

## Column Reference (Quick)

> Full column definitions, enum values, and approved transformation types: see [_shared/cde-definitions.md](../_shared/cde-definitions.md).

### Master Registry (12 columns)
> See [_shared/cde-definitions.md — Master CDE Registry](../_shared/cde-definitions.md).

### Lineage Flow (17 columns)
> See [_shared/cde-definitions.md — Lineage Flow](../_shared/cde-definitions.md).

### CDE Usage (8 columns)
> See [_shared/cde-definitions.md — CDE Usage](../_shared/cde-definitions.md).

## Approved Transformation Types

> See [_shared/cde-definitions.md — Approved Transformation Types](../_shared/cde-definitions.md).

Never invent new types.

## Quality Checklist

- [ ] Checked master before adding — no semantic duplicates
- [ ] New CDE IDs follow correct sequence per domain
- [ ] All 12 master registry columns populated for new rows
- [ ] `transformation_type` uses only approved vocabulary
- [ ] Referential integrity verified
- [ ] Existing rows not modified (append-only)
- [ ] No business definition altered for existing CDEs
- [ ] `notes` column documents reason for changes
