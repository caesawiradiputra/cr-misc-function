# Repository Analysis Checklist

Work through these in order. Skip categories that don't apply (e.g. a library
has no runbook-worthy operations). The goal isn't to read every file — it's
to answer each question below with something you actually verified, not
something you assumed from the project name.

## 0. Scope boundary (check before anything else)

Look at the top-level layout before diving into any one part of it. If you
see sibling directories like `api/`, `batch/`, `shared/`, `infra/` — each
with their own entry point, dependency manifest, or Dockerfile — this is
probably a monorepo holding multiple independent services, not one system.
Identify the distinct services and confirm which ones the request actually
covers before analyzing further; documenting an unrelated sibling wastes
effort and produces a page nobody asked for.

## 1. Existing documentation (read first, trust selectively)

Check for `README.md`, `AGENTS.md`, `CLAUDE.md`, `docs/`, and any
`ARCHITECTURE.md` or `RUNBOOK.md`. These often already answer "purpose,"
"architecture," and "conventions" questions cheaply — but verify any claim
that would surprise you against the actual code before repeating it.
Existing docs go stale; code doesn't lie about its current behavior.

## 2. Purpose and business context

- What business problem does this solve? Look for domain terms in code
  comments, model/table names, and any existing business-facing docs.
- Who are the users or consumers — another team, an external system, an
  end user? Look at entry points (API routes, CLI commands, DAG triggers,
  consumer topics) to see who calls in.
- What triggers a run — a schedule, an event, a manual invocation?

## 3. Architecture and processing flow

- What are the major components/steps, and in what order do they run?
  For pipelines/DAGs, the step registration or task dependency graph
  usually gives you this directly.
- Where does data enter and leave the system boundary? This is your
  inputs/outputs section — trace it from the first read to the last write.
- What does failure/retry look like structurally (checkpointing, retries,
  idempotency) — readers evaluating reliability will ask this.

## 4. Configuration

- What varies by environment (env vars, config files, feature flags)?
  Only document knobs an operator might actually need to change — not
  every constant in the codebase.
- Where do secrets/credentials come from (vault, env, secrets manager)?
  Name the mechanism, never the actual values.

## 5. Data: databases and tables

- What are the persistent stores (Postgres, a warehouse, object storage)?
- For each major table: what does it hold, who writes it, who reads it,
  and roughly how long does data live there? Look at ORM models,
  migrations, or schema files rather than guessing from table names.
- Distinguish tables that are operationally important (an operator might
  query them to diagnose an issue) from purely internal ones — only the
  former need to be named in ops-facing docs.
- For data-engineering/ETL systems, trace data through its full lifecycle,
  not just in/out: where does it land temporarily (a PVC, a staging table,
  a queue), where does it end up persistently, and what actually deletes or
  archives it, and when? Cleanup logic and retention config are often the
  only place this is stated explicitly.

## 6. Integrations

- What external systems does this talk to (other internal services,
  third-party APIs, message queues, shared storage)? For each: is it
  inbound, outbound, or both, and what protocol/auth does it use?
- Which integrations are load-bearing (system breaks without them) vs.
  best-effort (failures are logged and swallowed)? Check error-handling
  code around each integration call — a bare `except` that logs and
  continues is best-effort; an unhandled exception that aborts the run is
  load-bearing. This is exactly what the runbook's failure-impact/recovery
  columns need.

## 7. Monitoring and operations

- What logging/metrics/alerting already exists? Look for logging config,
  dashboards-as-code, alert definitions, or notification integrations
  (Slack/Chat webhooks, PagerDuty, etc.).
- What does a healthy run look like, concretely enough that someone could
  check it (e.g. "a new partition appears in table X within Y minutes")?
- Are there known failure modes already handled in code (retry logic,
  specific exception handling, alerting on specific conditions)? These are
  strong hints for what belongs in the runbook's "common issues" section —
  the code already tells you what the authors expected to go wrong.

## 8. Ownership metadata

Check for `CODEOWNERS`, team labels in CI config, PR templates, or
on-call/paging config (e.g. a PagerDuty/Opsgenie routing file) — these
sometimes name a business owner, technical owner, or support team directly.
This information is frequently just absent from the repo. Don't guess a
name or team to fill the gap; mark it Unknown in the Operational Ownership
table (see `references/page-templates.md`) and let the user or a
follow-up conversation fill it in.

## 9. Deployment and environments

- How does this get deployed (CI/CD pipeline, container orchestration,
  manual steps)? What environments exist (dev/staging/prod, or
  SIT/UAT/production)?
- Is there a rollback path, and does it need any manual steps?

## Verification discipline

For anything you're not sure about — especially business purpose and
"why" questions that aren't answered directly in code — say so to the user
rather than filling the page with a plausible-sounding guess. A page that
honestly says "confirm with the X team" in one spot is more trustworthy than
one that quietly guesses everywhere.
