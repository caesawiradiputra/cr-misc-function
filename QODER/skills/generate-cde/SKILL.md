---
name: generate-cde
version: "1.0.0"
updated: "2026-06-18"
related_skills:
  - update-cde
  - generate-cde-spreadsheet
description: Build an enterprise CDE (Common Data Element) data model from scratch. Mode A for initial registry establishment — comprehensive discovery phase. Use when the user triggers /generate-cde or asks to create a CDE registry when none exists yet.
---

# Generate CDE (Mode A — Initial Setup)

Build an enterprise CDE data model from scratch. Use when no master registry exists yet.

**Mode A: Initial Registry Establishment** — comprehensive discovery phase.

## Context

If arguments specify business contexts, systems, or domain areas, use that as input. Otherwise, run the discovery protocol.

## Terminology

> See [_shared/cde-definitions.md](../_shared/cde-definitions.md) for full terminology, column definitions, and governance rules.

- **data_domain** — Semantic classification (`APPL`, `CUST`, `PAY`, `RISK`). Describes WHAT the data is semantically.
- **business_context** — Organizational boundary (`onboarding`, `payments`, `anti_fraud`). Describes WHERE/WHO uses the data. Same CDE can appear in multiple business_contexts.

## Output Files

1. `master_cde_registry.tsv` — Enterprise-wide single source of truth (12 columns)
2. `{business_context}_lineage_flow.tsv` — Data movement per context (17 columns)
3. `{business_context}_cde_usage.tsv` — Data consumption per context (8 columns)

> Full column definitions, enum values, and approved transformation types are in [_shared/cde-definitions.md](../_shared/cde-definitions.md).

## Discovery Protocol

**Before generating any files**, analyze the project and ask for missing information:

1. Read project files: `app/connections/`, `repositories/`, `docs/`, config files
2. Ask for clarification if any are missing:
   - List of all semantic domains
   - List of all business_contexts in scope
   - Pipelines within each business_context
   - Data classification requirements (PII, SENSITIVE_PII, CONFIDENTIAL)
   - Regulatory context

## Master CDE Registry Format (12 columns, TSV)

> Full column definitions with types and rules: see [_shared/cde-definitions.md — Master CDE Registry](../_shared/cde-definitions.md).

**Data sensitivity**: `PUBLIC`, `INTERNAL`, `PII`, `SENSITIVE_PII`, `CONFIDENTIAL`, `METADATA`
**Business criticality**: `HIGH`, `MEDIUM`, `LOW`

> Complete enum reference: see [_shared/cde-definitions.md — Enum Reference](../_shared/cde-definitions.md).

## Lineage Flow Format (17 columns, TSV)

> Full column list and rules: see [_shared/cde-definitions.md — Lineage Flow](../_shared/cde-definitions.md).

One row per unique `(pipeline_name + cde_id + lineage_step)` per business_context.

**Approved transformation_type**: see [_shared/cde-definitions.md — Approved Transformation Types](../_shared/cde-definitions.md).

## CDE Usage Format (8 columns, TSV)

> Full column list: see [_shared/cde-definitions.md — CDE Usage](../_shared/cde-definitions.md).

## Discovery Phases

### Phase 1 — Stakeholder Discovery (1-2 weeks)
Identify all semantic domains, map which business_contexts use which domains, document regulatory requirements.

### Phase 2 — Master Registry Consolidation (1 week)
Merge all discovered CDEs into single master, eliminate duplicates, assign unique CDE IDs per domain sequence.

### Phase 3 — Business-Context Mapping (1-1.5 weeks)
Document pipelines per business_context, create lineage and usage files, validate referential integrity.

## Governance Rules

> Full governance rules: see [_shared/cde-definitions.md — Governance Rules](../_shared/cde-definitions.md).

- **Master registry is single source of truth**: CDE-APPL-001 defined once, referenced everywhere
- **Append-only for context files**: never modify master definitions
- **Transformation vocabulary**: only approved types
- **Cross-context semantics**: different contexts may apply different transforms, but must NOT alter the business definition

**Foreign key validation**: All `cde_id` in context files must exist in master.

## Output Location

> See [_shared/cde-definitions.md — Output Location](../_shared/cde-definitions.md).
