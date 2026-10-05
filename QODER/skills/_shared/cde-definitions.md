# CDE Shared Definitions

Common terminology, column definitions, and governance rules shared across all CDE skills (`/generate-cde`, `/generate-cde-spreadsheet`, `/update-cde`).

## Terminology

- **data_domain** — Semantic classification (`APPL`, `CUST`, `PAY`, `RISK`). Describes WHAT the data is semantically.
- **business_context** — Organizational boundary (`onboarding`, `payments`, `anti_fraud`). Describes WHERE/WHO uses the data. Same CDE can appear in multiple business_contexts.

## Master CDE Registry (12 columns, TSV)

**Filename**: `docs/cde/master_cde_registry.tsv`

| Column | Description | Rules / Example |
| --- | --- | --- |
| `cde_id` | `CDE-{DOMAIN}-{SEQ}` | Unique, sequential per domain. e.g., `CDE-APPL-001` |
| `data_domain` | Semantic domain code | `APPL`, `CUST`, `PAY`, `RISK`, etc. |
| `lineage_key` | `{Entity}.{Attribute}` | e.g., `Applicant.National_ID` |
| `business_name` | Human-readable name | e.g., `Applicant National ID` |
| `definition` | Business definition | No technical detail |
| `data_type` | Data type | `STRING`, `INTEGER`, `DECIMAL`, `DATE`, `BOOLEAN` |
| `data_sensitivity` | Classification enum | `PUBLIC`, `INTERNAL`, `PII`, `SENSITIVE_PII`, `CONFIDENTIAL`, `METADATA` |
| `is_pii` | PII flag | `TRUE` / `FALSE` |
| `is_regulatory` | Regulatory flag | `TRUE` / `FALSE` |
| `business_criticality` | Impact level enum | `HIGH`, `MEDIUM`, `LOW` |
| `data_owner` | Owning team/domain | e.g., `Credit Risk` |
| `notes` | Additional context | Optional |

## Lineage Flow (17 columns, TSV)

**Filename**: `docs/cde/{business_context}_lineage_flow.tsv`

One row per unique `(pipeline_name + cde_id + lineage_step)` per business_context.

Columns: `business_context` | `pipeline_name` | `cde_id` | `lineage_step` | `source_system` | `target_system` | `transformation_type` | `transformation_detail` | `source_field` | `target_field` | `is_pii_in_flight` | `encryption_required` | `sla_minutes` | `data_quality_check` | `error_handling` | `dependencies` | `notes`

## CDE Usage (8 columns, TSV)

**Filename**: `docs/cde/{business_context}_cde_usage.tsv`

One row per unique `(cde_id + consumer_system + consumption_purpose)` per business_context.

Columns: `business_context` | `cde_id` | `consumer_system` | `consumption_purpose` | `data_quality_requirements` | `retention_policy` | `access_pattern` | `notes`

## Approved Transformation Types

`passthrough` | `cast` | `normalize` | `join` | `enrich` | `aggregate` | `derive` | `constant` | `upsert`

Never invent new types. Only these values are valid for the `transformation_type` column.

## Enum Reference

| Field | Allowed Values |
| --- | --- |
| `data_sensitivity` | `PUBLIC`, `INTERNAL`, `PII`, `SENSITIVE_PII`, `CONFIDENTIAL`, `METADATA` |
| `business_criticality` | `HIGH`, `MEDIUM`, `LOW` |
| `data_type` | `STRING`, `INTEGER`, `DECIMAL`, `DATE`, `BOOLEAN` |

## Governance Rules

- **Master registry is single source of truth**: No CDE defined twice. CDE-APPL-001 defined once, referenced everywhere.
- **Append-only**: Never delete or modify existing master rows.
- **Transformation vocabulary**: Only approved types (see above).
- **Cross-context semantics**: Different contexts may apply different transforms, but must NOT alter the business definition.
- **Quality requirements**: Must be specific and measurable.
- **Retention policy examples**: Operational `30 days`, Analytics `2 years`, Compliance `7 years`.

**Foreign key validation**: All `cde_id` in context files must exist in master.

## Output Location

All CDE files are saved to `docs/cde/`:

```text
docs/cde/
+-- master_cde_registry.tsv
+-- {business_context}_lineage_flow.tsv
+-- {business_context}_cde_usage.tsv
+-- ... (one lineage + usage set per business_context)
```
