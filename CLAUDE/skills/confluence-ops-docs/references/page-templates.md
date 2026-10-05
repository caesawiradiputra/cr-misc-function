# Page Templates

Use these as starting structures, not rigid schemas — drop a section if
there's nothing real to say (never pad it), and add one if the system has
something important that doesn't fit elsewhere. Word counts are a rough
"this should be a 3-8 minute read" guide, not a target to hit exactly.

Every page/section needs a one-line "who this is for" in your own head
before you write it — it doesn't need to appear in the output, but if you
can't state it, you'll end up writing to no one in particular.

## Overview (~500-900 words)

**Audience**: business stakeholders, product managers, anyone who needs to
understand what the system does but never touches it directly.

```markdown
# {System} — Overview

## What is {System}?
[Plain-language description of the business problem it solves. No component
names, no library names.]

## Who uses it / who it serves
[Consuming teams, downstream systems, or end users — and what they get from it]

## Key use cases
1. [Use case in business terms]
2. ...

## Components
| Component | Purpose | Owner/Team |
| --- | --- | --- |
| ... | ... | ... |

(Omit this table for single-component systems.)
```

## Architecture, Data & Integrations (~900-1500 words)

**Audience**: architects, technical stakeholders from other teams, anyone
evaluating how this system fits into the broader landscape — not the
maintainers themselves (they have the code).

```markdown
# {System} — Architecture, Data & Integrations

## Processing flow
[Diagram or ordered description of the major steps/components and how data
moves between them — named by role, not by function/class name]

## Inputs and outputs
| Direction | What | Source/Destination | Format/Frequency |
| --- | --- | --- | --- |

## Data lifecycle
[For anything data-engineering/ETL shaped, trace data through its full
life rather than stopping at input/output:]
| Stage | Where | Retention |
| --- | --- | --- |
| Source | ... | ... |
| Temporary/working | ... | ... |
| Persistent | ... | ... |
| Archive | ... | ... |
| Cleanup | [what removes it, and when] | ... |

(Omit stages that don't apply — a stateless API has no archive/cleanup row.)

## Key databases and tables
| Table | Holds | Written by | Read by | Notes |
| --- | --- | --- | --- | --- |

## Integrations and critical dependencies
| System | Direction | Purpose | Failure impact | Recovery |
| --- | --- | --- | --- | --- |

(Failure impact = what breaks, and how badly, if this dependency is down.
Recovery = what restores it — auto-retry, manual restart, nothing needed.
This is the table an on-call engineer checks first when triaging an
incident, so favor precision here over everywhere else on this page.)

## Configuration
Group by who would actually change each setting — a business analyst
changing a threshold and a platform engineer changing a resource limit are
different audiences, even though both are "configuration":

- **Business configurable** — settings a non-engineer might reasonably
  request a change to (thresholds, schedules, business rules)
- **Operator configurable** — settings an operator changes to affect
  behavior without a deploy (feature flags, retry limits)
- **Deployment configurable** — settings that differ by environment
  (endpoints, resource limits, credentials source)
- **Runtime configurable** — settings read fresh on each run/request
  rather than fixed at deploy time, if that distinction matters here

Omit any category with nothing real in it — most systems don't need all
four.
```

## Operations & Runbook (~900-1500 words)

**Audience**: on-call engineers and operators — people who need this page
open *while something is happening*, not people building a mental model.
Write for scanning under pressure: short sections, concrete steps, no prose
throat-clearing.

```markdown
# {System} — Operations & Runbook

## Operational ownership
| Field | Value |
| --- | --- |
| Business owner | ... |
| Technical owner | ... |
| Support team | ... |
| Repository | ... |
| Deployment | ... |
| Scheduler | ... |
| SLA | ... |
| Criticality | ... |
| Escalation contacts | ... |

(This table is often only partially answerable from the repo — see
"Evidence-based documentation" in SKILL.md. Mark fields you can't verify as
Unknown rather than guessing; a partially-filled ownership table someone can
complete in five minutes beats a fully-filled one that's wrong.)

## Health checks
[What "working" looks like, concretely — a dashboard, a query, a log line]

## Monitoring and alerts
[What's monitored, where alerts go, what an alert means]

## Common issues
### [Symptom]
- **Likely cause**: ...
- **Check**: [specific dashboard/query/log]
- **Fix**: [specific action]

(3-6 scenarios, prioritized by how often they actually happen or how bad
they are if missed — not an exhaustive list of every conceivable failure.)

## Scheduled maintenance
[Anything that runs on a cadence and needs occasional attention]

## Escalation
[Who to contact, in what order, for what class of problem]
```

## Onboarding Guide (~600-1000 words)

**Audience**: someone joining the team or picking up ownership, in their
first week. This page's job is to shorten the time before they're
productive — it's a guided path through the other pages, not a summary of
them.

```markdown
# {System} — Onboarding Guide

## Start here
[1-2 sentence orientation + link to the Overview page]

## Access and setup
- [ ] [Specific permission/credential/tool access to request, and from whom]

## First week checklist
- [ ] Read [Architecture, Data & Integrations](link) — focus on [the part
      that matters most]
- [ ] [Shadow a deploy / watch a run / whatever the real onboarding ritual is]
- [ ] [Any hands-on task that builds real understanding fast]

## Who to ask
| Question about | Ask |
| --- | --- |
```

## Reference (multi-service systems only, ~500-900 words)

**Audience**: someone already inside the docs, trying to reorient across
several child pages.

```markdown
# {System} — Reference

## Glossary
| Term | Meaning |
| --- | --- |

## Service comparison
| Service | Purpose | Type | Owner |
| --- | --- | --- | --- |

## Related pages
[Links to every page in the hierarchy]
```
