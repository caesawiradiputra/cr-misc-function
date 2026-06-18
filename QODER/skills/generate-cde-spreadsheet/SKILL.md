---
name: generate-cde-spreadsheet
version: "1.0.0"
updated: "2026-06-18"
related_skills:
  - generate-cde
  - update-cde
description: Generate a unified CDE spreadsheet covering Master Registry + Business-Context-Specific Lineage Flows + CDE Usage patterns. Produces TSV files ready for Excel or Google Sheets. Use when the user triggers /generate-cde-spreadsheet or asks to create CDE documentation.
---

# Generate CDE Spreadsheet

Generate a unified CDE spreadsheet covering: Master Registry + Business-Context-Specific Lineage Flows + CDE Usage patterns. Produces TSV files ready for Excel or Google Sheets.

## Context

If arguments specify scope (business context, domain, or system), use that. Otherwise, ask for the scope.

## Clarification Protocol (Run First)

Before generating any files:

1. **Read existing project files**: check if CDE files already exist in `docs/cde/`
2. **Ask for missing information** (do not assume):
   - Which business_contexts are in scope?
   - What semantic domains exist (Applicant, Customer, Payment, Risk, etc.)?
   - Are there existing pipelines to document?
   - What data classification requirements apply?

## Output: 3-File CDE Model (per business_context)

> Full column definitions, enum values, and approved transformation types are in [_shared/cde-definitions.md](../_shared/cde-definitions.md).

### File 1 — Master CDE Registry (Enterprise-Wide)

**Filename**: `docs/cde/master_cde_registry.tsv` (12-column TSV, one row per unique CDE)

> Full column definitions: see [_shared/cde-definitions.md — Master CDE Registry](../_shared/cde-definitions.md).

### File 2 — Lineage Flow (Per Business Context)

**Filename**: `docs/cde/{business_context}_lineage_flow.tsv` (17-column TSV)

> Full column list: see [_shared/cde-definitions.md — Lineage Flow](../_shared/cde-definitions.md).

**Approved transformation_type**: see [_shared/cde-definitions.md — Approved Transformation Types](../_shared/cde-definitions.md).

### File 3 — CDE Usage (Per Business Context)

**Filename**: `docs/cde/{business_context}_cde_usage.tsv` (8-column TSV)

> Full column list: see [_shared/cde-definitions.md — CDE Usage](../_shared/cde-definitions.md).

## Processing Steps

1. **Load existing registry** (if `master_cde_registry.tsv` exists) — continue from max sequence per domain
2. **Extract CDEs from project** — identify data entities from code (models, repositories, schemas), map to semantic domains
3. **Map lineage flows** — identify pipelines per business_context, document transformation steps
4. **Document consumption patterns** — identify consumers, capture quality requirements, retention policies
5. **Validate referential integrity** — every `cde_id` in context files MUST exist in master

## Governance Rules

> Full governance rules: see [_shared/cde-definitions.md — Governance Rules](../_shared/cde-definitions.md).

- **Master registry = single source of truth**: No CDE defined twice
- **Append-only**: Never delete or modify existing master rows
- **Transformation vocabulary**: Only approved types
- **Quality requirements**: Must be specific and measurable
- **Retention policy examples**: Operational `30 days`, Analytics `2 years`, Compliance `7 years`

## Quality Checklist

- [ ] All `cde_id` values unique in master registry
- [ ] CDE ID sequences correct per domain
- [ ] All 12 master registry columns populated
- [ ] `transformation_type` uses only approved vocabulary
- [ ] All `cde_id` in context files exist in master (referential integrity)
- [ ] `data_quality_requirements` are specific and measurable
- [ ] `retention_policy` specifies duration and reason
- [ ] No duplicate rows in any file
- [ ] TSV format valid (proper tab delimiters)
- [ ] Files saved to `docs/cde/`
