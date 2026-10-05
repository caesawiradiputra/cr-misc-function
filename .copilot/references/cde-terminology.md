---
description: Shared terminology definitions for CDE (Common Data Element) prompts and instructions
---

# CDE Terminology Reference

## Critical Distinction: data_domain vs business_context

Two terms used throughout CDE documentation must not be conflated:

### data_domain

**Semantic classification** of what a CDE represents (e.g., Applicant domain, Customer domain, Payment domain)

- Used in `cde_id` format: `CDE-{data_domain}-{NUMBER}`
- Examples: APPL (Applicant data), CUST (Customer data), PAY (Payment data), RISK (Risk data)
- The CDE itself belongs to a semantic domain based on the business entity it describes
- Represents **WHAT the data is** at semantic level

### business_context

**Organizational or operational boundary** that manages pipelines and usage patterns

- Examples: Onboarding team, Payments team, Anti-Fraud team, Collections team
- Used in file naming and directory structure
- Examples: `onboarding_lineage_flow.tsv`, `payments_cde_usage.tsv`, `anti_fraud_lineage_flow.tsv`
- The business context is where a CDE is used/managed, which may be different from its semantic domain
- A single CDE (e.g., CDE-CUST-001) can appear in **multiple business contexts**
- Represents **WHERE and HOW the data is used** operationally

---

## Example: Understanding the Distinction

**Scenario**: Customer KTP Number

- **CDE ID**: `CDE-APPL-001` (belongs to **APPL** data_domain)
- **Lineage Key**: `Applicant.KTP Number` (semantic definition)
- **Data Domain**: APPL (Applicant entity - what it is)
- **Appears in business_contexts**:
  - `onboarding_lineage_flow.tsv` (used by Onboarding team)
  - `collection_lineage_flow.tsv` (used by Collections team)
  - `anti_fraud_lineage_flow.tsv` (used by Anti-Fraud team)

**Key Point**: One CDE (one row in master registry) flows through multiple business contexts, but the semantic definition stays constant.

---

## Model Architecture

The CDE model uses:

1. **Master Registry** (one file, enterprise-wide)
   - One row per unique CDE
   - Defined once, referenced everywhere
   - Semantic ownership, business meaning, classification

2. **Business-Context-Specific Files** (multiple sets)
   - LINEAGE_FLOW: How data moves through this business_context's systems
   - CDE_USAGE: How this business_context consumes CDEs
   - Both reference master via `cde_id` (foreign key)

This separation keeps semantics consistent while allowing operational flexibility across teams.
