---
name: confluence-ops-docs
description: Generate and maintain business- and operations-oriented documentation for Confluence by analyzing a codebase or project — covering purpose, architecture, processing flow, configuration, major inputs/outputs, key databases/tables, integrations, monitoring, and runbook procedures. Organizes output into a parent/child page hierarchy when the system is complex enough to warrant it, or a single page when it isn't. Use this whenever the user asks for system documentation, Confluence pages, operational documentation, architecture overviews, runbooks, onboarding guides, or any documentation "derived from" or "based on" an existing codebase or project — even if they never say the word "Confluence" (e.g. "document this pipeline for the ops team", "write up how this system works for new hires", "I need a runbook for this service", "can you draft an architecture overview for stakeholders").
tools:
  - Read
  - Grep
  - Glob
  - Bash
  - Write
  - Edit
---

# Confluence Operations Documentation

## Purpose

Produce documentation that lets someone who has never opened the codebase — a
new hire, an on-call engineer at 3am, a product manager, an auditor — understand
what the system does and how to operate it, without reading source code.

This is fundamentally different from code documentation (docstrings, README
dev-setup instructions, architecture decision records for engineers). Those
already exist or belong elsewhere. This skill writes for people who will never
open the repository.

## Audience-first principle

Before writing anything, decide who reads this page and what they need to *do*
after reading it. A business stakeholder needs to know what the system
accomplishes and what it costs to change. An on-call engineer needs to know
what to check first when it breaks. A new hire needs to know where to start
and who to ask. None of them need to know how a function is implemented.

This single question — "what does the reader need to do?" — resolves most
judgment calls about what to include. If a detail doesn't change what the
reader would do next, leave it out, even if it's true and even if it's
interesting.

### Audience priority

Enterprise systems often have several plausible audiences pulling in
different directions. When a piece of information would help one audience
but is irrelevant noise to another, resolve the conflict using this
priority order — highest first:

1. Operators (the people running it day to day)
2. Production support / on-call
3. New team members
4. Business stakeholders
5. Developers who already work on the code

Developers are last deliberately: they already have the source, the
README, and the docstrings. If a detail benefits only someone who could
just read the code, it doesn't belong here — that's the strongest signal
that something has drifted into implementation detail.

### Bias: what to include vs. exclude

When deciding whether something belongs in the page, prefer:

- **Outcomes over mechanisms.** "Contracts outside a branch's radius are
  flagged and excluded from ranking" over "the code checks `is_no_cluster`
  and filters the DataFrame."
- **Named systems over internal modules.** "Reads assignment history from
  Postgres" over "calls `ClusterSelectionRepo.fetch_history`."
- **Operator-facing knobs over code-level config.** An environment variable
  that changes pipeline behavior belongs here; an internal constant that
  only affects code structure doesn't.
- **Stable facts over recent implementation choices.** Document what the
  system does today, not the history of how it got there — that's what git
  history and PR descriptions are for.
- **Business/domain terms over code identifiers.** If the codebase says
  `pv_cluster_selection` but the business calls it "the rotation history,"
  introduce the business term and mention the table only where a reader would
  actually need to query it (e.g. in a runbook step).

A useful test: if you had to redact all class names, function names, and file
paths from the page, would it still make sense and still be useful? If not,
it's leaning too far into implementation.

Exception: runbook steps that name actual commands, table names, dashboard
URLs, or file paths are not implementation detail — they're the whole point.
Precision matters exactly where the reader will act on the page directly.

### Exclusions

Don't document, unless it's operationally significant enough to override the
default (e.g. a "helper" that happens to be the thing on-call restarts):

- helper classes and utility functions
- internal libraries and private APIs
- implementation algorithms
- test infrastructure

This skill also doesn't produce artifacts that belong to a different job
entirely — resist generating these even if they'd be easy to derive from the
repo:

- ER diagrams, UML, or Mermaid diagrams (this skill's diagrams stay ASCII —
  see `references/confluence-formatting.md`)
- Function-level API reference documentation
- Raw SQL schema dumps
- Kubernetes manifest explanations

If the user's request is really for one of those, it's a different task —
say so rather than folding it into the Confluence pages.

## Evidence-based documentation

Repositories don't always contain enough information to answer every
question this skill wants to answer — who owns a system, what its SLA is,
why a design decision was made. Guessing to fill the gap is worse than
leaving it acknowledged, because a wrong fact is trusted right up until it
causes a bad decision, while an acknowledged gap gets fixed.

For anything non-obvious, keep track of whether it's:

- **Verified** — directly supported by source code, configuration,
  deployment manifests, tests, or existing documentation you cross-checked
  against the code.
- **Inferred** — your best reading of the evidence, but not stated
  outright anywhere (e.g. inferring an SLA from a retry/timeout config).
  Mark it as inferred in the text, e.g. "*(inferred from retry
  configuration)*".
- **Unknown** — not determinable from the repository at all (ownership,
  business justification, on-call rotation). Write "Unknown — confirm with
  [the team/role most likely to know]" rather than omitting the field
  silently or guessing a plausible-sounding answer.

This applies with the most force to the Operational Ownership fields (see
`references/page-templates.md`) and to any business "why" — those are the
fields most likely to be genuinely absent from a codebase. Don't
reverse-engineer undocumented business intent from implementation alone —
if the *why* behind a rule can't be verified, document the observable
behavior and mark the business rationale itself as Unknown, rather than
inventing a plausible-sounding reason.

### Repository confidence

After analyzing the repository, assess — and state, near the top of the
output — how complete the resulting documentation can realistically be:

- **High** — the repository is self-contained, major architecture is
  discoverable, and operational information (ownership, monitoring,
  runbook material) is actually present.
- **Medium** — core behavior is clear, but some ownership or operational
  details are missing.
- **Low** — the repository appears incomplete, external systems are
  undocumented, or important assumptions remain Unknown.

If confidence is Low, say so plainly and recommend a follow-up with the
project owner rather than letting the page's polish imply more certainty
than the underlying evidence supports.

## Documentation maintenance

Write pages that survive the system's normal rate of change without going
stale. A page that has to be rewritten after every minor refactor will
simply not get rewritten, and then it's actively misleading.

Prefer documenting things that only change on a business or architectural
decision, not on a code change:

- responsibilities and interfaces, over the internals behind them
- operational behavior and contracts, over the code that enforces them
- business terminology, over whatever the current code happens to call
  something

When a detail is tightly coupled to implementation and likely to change
often (a specific retry count, a specific batch size, a specific internal
queue name), summarize the behavior it produces rather than enumerating the
current value — "retries transient failures with backoff" ages better than
"retries 3 times with a 2s/4s/8s backoff," unless the exact numbers are
something an operator would need to act on.

## Workflow

1. **Determine scope.** If the user names a system or points at a directory,
   use that. Otherwise infer scope from the current project. Watch
   specifically for a monorepo boundary: a repo with sibling directories
   like `api/`, `batch/`, `shared/`, `infra/` usually holds multiple
   independent services, not one system. In that case, identify the
   distinct services first, decide which ones the request actually covers,
   and don't document unrelated siblings just because they're nearby in the
   tree. If it's not obvious which services are in scope, ask before
   generating anything — a wrong guess here wastes the entire rest of the
   workflow.

2. **Analyze the repository.** Read `references/repo-analysis-checklist.md`
   for what to look for and where. Don't skip this — the quality of the
   output is bounded by how well you actually understand the system, not by
   how well you can imitate documentation structure.

3. **Decide: one page or a hierarchy.** See "Deciding hierarchy vs. single
   page" below.

4. **Draft content.** Read `references/page-templates.md` for the section
   templates and what each one needs to cover. Fill them from what you
   learned in step 2 — don't invent details you didn't verify against the
   code or its existing docs.

5. **Format for Confluence.** Read `references/confluence-formatting.md` for
   markdown conventions (tables, code blocks, callouts, cross-page links).

6. **Run the quality checklist** (bottom of this file) before presenting the
   result.

## Deciding hierarchy vs. single page

Default to a **single page**. Split into a parent/child hierarchy only when
splitting actually helps a reader, which is usually one of:

- **Multiple audiences need very different depth.** A business stakeholder
  skimming "what is this" would have to scroll past three pages of runbook
  steps to get there. Splitting lets each reader land on the page written
  for them.
- **Multiple services share context.** If the system has several
  deployable components (e.g. an API plus a batch job plus a consumer) that
  share business purpose and architecture but differ in how they're run and
  operated, put the shared material in a parent page and give each service
  its own child.
- **The content is genuinely long.** As a rough guide, if the single-page
  draft is pushing past ~2500-3000 words, it's a candidate for splitting —
  but don't split a merely detailed page just to hit a page count if the
  reader still only wants one thing from it.

If none of those apply, one well-organized page with clear headings beats a
maze of five thin pages a reader has to click through. Splitting has a real
cost — cross-references go stale, and readers must find the right child page
before they find their answer.

### Default hierarchy shape (when a split is warranted)

- **Overview** (parent) — purpose, business context, who uses it, key use
  cases. Shared across all services/components if there are several.
- **Architecture, Data & Integrations** — architecture and
  processing-flow diagram, major inputs/outputs, data lifecycle, key
  databases/tables, and integrations with external systems. One per
  service if services differ architecturally; shared if they don't.
- **Operations & Runbook** — configuration reference, operational
  procedures, monitoring, common failure scenarios, escalation path.
  Almost always per-service, since operating one service rarely helps you
  operate another.
- **Onboarding Guide** — for someone new to the system: what to read first,
  access/permissions to request, who to ask. Written as a guided path
  through the other pages, not a duplicate of their content.
- **Reference** (only for multi-service systems) — shared glossary and a
  service comparison table, so a reader lost across several child pages has
  one place to reorient.

This shape is a starting point, not a fixed schema — collapse pages that
would be near-empty for this particular system, and add a page if a section
genuinely needs its own (e.g. a system with unusually complex compliance
requirements might warrant a dedicated compliance page).

## Output location and naming

Save to `docs/confluence/` in the project root. For a single page:
`docs/confluence/{system-slug}.md`. For a hierarchy:
`docs/confluence/{system-slug}-overview.md`,
`{system-slug}-architecture-and-data.md`, `{system-slug}-operations.md`,
`{system-slug}-onboarding.md`, and (multi-service only)
`{system-slug}-reference.md`. Use the repo or system name, lowercased and
hyphenated, for `{system-slug}`.

### Respect what already exists

Before writing, check whether the repository already has Confluence-ready
documentation — in `docs/confluence/`, elsewhere in `docs/`, or referenced
from the README. If it does, this is an update, not a fresh generation:

- Preserve terminology, page naming, and structure the team has already
  settled on, even where it differs from this skill's defaults above.
  Consistency with what readers already navigate matters more than matching
  this skill's preferred shape.
- Preserve content that's still accurate; prefer removing stale content
  outright over silently rewriting it into something new.
- Don't rewrite a page purely to match this skill's style — that erases
  manual edits maintainers made for reasons that won't show up in the code.
- If existing documentation conflicts with what the code actually does,
  don't silently resolve it in either direction — state the conflict.
  Sometimes the docs are stale; sometimes the code has a bug the docs
  correctly describe the intent of. Deciding which is a call for the
  project owner, not something to guess past.

## Quality checklist

Before presenting the result, confirm:

- [ ] Every implementation detail you almost included has been asked "does
      this change what the reader does next?" — if not, it's gone.
- [ ] A reader with zero codebase access could act on every runbook step
      (they'd need to already have the described access/dashboard/table
      name, but not need to open the source).
- [ ] No unexplained acronyms or internal jargon on first use.
- [ ] Headings follow a clean hierarchy (H1 → H2 → H3, no skipping).
- [ ] Tables and code blocks are formatted per
      `references/confluence-formatting.md`.
- [ ] If split into a hierarchy, every child links back to its parent and
      siblings, and the split still makes sense (re-check against "Deciding
      hierarchy vs. single page" — don't leave a split that only made sense
      as a first draft).
- [ ] Content matches the actual current state of the repository — nothing
      copied from a stale README or aspirational design doc without
      verifying it against the code.
- [ ] Every inferred or unknown fact is labeled as such, not stated as
      plain fact.

Then step back and check the pages answer these, from a reader's
perspective, without needing to open the source:

- [ ] Do they understand what the system is for?
- [ ] Do they know its inputs and outputs?
- [ ] Do they know its dependencies and which ones are critical?
- [ ] Do they know how it's monitored and what healthy looks like?
- [ ] Do they know how to recover it when something breaks?
- [ ] Do they know the system's limitations?
