# Dev workflow: stages, Jira statuses, git steps and the logbook

How a change moves from assignment to a closed ticket, and what each Claude Code skill or
command does at each step. The logbook uses the same stage words as Jira, so Jira, git and
the weekly report agree. Nothing is committed, pushed, transitioned or logged without the
user's OK; every step below only proposes.

## Stages

Jira order: `Data Analysis` → `Data Development` → `Testing` (UAT) → `Ready For Release`
(CAB) → `Deployment` (CAB approved) → `PAT` (deployed, production assurance test) → `Done`
(no error one week after PAT). `Hold` can occur at any point. The flow is forward-only.

| # | Stage | Jira status | Git / GitHub step | Trigger and tool |
| --- | --- | --- | --- | --- |
| 1 | Assignment | `[BU] Todo` | none | `jira-in-da-sync` |
| 2 | Analysis: brainstorm, design, plan | `Data Analysis` | spec or plan under `release/<TICKET>/` | `jira-ticket-kickoff`, `brainstorming`, `writing-plans` |
| 3 | Develop and SIT | `Data Development` | `fea/` or `fix/` branch off `dev`; optional merge into `sit` | `/commit` |
| 4 | Testing (UAT) | `Testing` | PR open to `dev`, not merged | `/generate-pr-message` (PR 1) |
| 5 | Generate BAST | `Testing` (no change) | PR still open | `bast-generator` |
| 6 | User approval | `Ready For Release` | PR squash-merged into `dev` | merge event prompt |
| 7 | Register CAB | `Ready For Release` (no change) | BAST updated with user capture and approval; `dev` to `master` PR open, may merge directly | `/generate-pr-message` (PR 2), BAST update |
| 8 | CAB approval | `Deployment` | none required (`master` may already be merged) | the user moves the ticket |
| 9 | Deployed, PAT | `PAT` | none | the user moves the ticket |
| 10 | Closed | `Done` | branch cleanup | the board flags 7 or more days in `PAT` |

A merge into `master` is not the release gate and never means deployed: deployment starts
only after CAB approval.

## Logbook statuses

| Logbook status | Weekly page word | Jira status |
| --- | --- | --- |
| `Analysis` | `ANALYST` | `Data Analysis` |
| `Development` | `DEVELOPMENT` | `Data Development` |
| `Testing` | `TESTING` | `Testing` |
| `Ready For Release` | `READY FOR RELEASE` | `Ready For Release` |
| `Deployment` | `DEPLOYMENT` | `Deployment` |
| `PAT` | `PAT` | `PAT` |
| `Done` | `DONE` | `Done` |
| `Fixing` | `FIXING` | none |
| `Hold` | `HOLD` | `Hold` |

Work with no Jira flow (logbook tooling and other personal, non-company work) skips the CAB,
`Deployment` and `PAT` stages: set `Done` once its PR to `master` is merged.

When Jira and the logbook disagree on status, Jira wins; `logbook.py check` reports the
difference and proposes the logbook update.

## Trigger prompts

Each event proposes the next step when it happens and never acts without an OK.

| Event | Prompt |
| --- | --- |
| Assignment cloned (`jira-in-da-sync`) | Start the ticket (kickoff) or leave it |
| Kickoff done | Move Jira to `Data Analysis` or `Data Development`; logbook `Analysis` or `Development` |
| PR to `dev` opened | Jira to `Testing`; logbook `Testing`; offer `bast-generator` |
| BAST generated | Remind to send for UAT; no status change |
| PR to `dev` merged | Jira to `Ready For Release`; logbook `Ready For Release`; offer the `dev` to `master` PR and the BAST update |
| PR to `master` opened or merged | No Jira change; remind that CAB approval moves the ticket to `Deployment` |
| Ticket seen in `Deployment` | Logbook `Deployment` |
| Ticket seen in `PAT` | Logbook `PAT`; note the date, so day 7 is known |
| 7 or more days in `PAT` | Jira and logbook to `Done`; offer `/clean-gone` |

## Precedence rules for the board

1. Jira supplies the recorded status. Git and GitHub evidence only identifies events and
   inconsistencies; it never changes a status by itself.
2. `Hold` wins: a ticket on hold shows only "on hold" and the hold date, with no workflow
   prompts, even if a PR merged meanwhile.
3. Missing or unreadable evidence is shown as `unknown`, and any suggestion that depends on
   it is left out.
4. A ticket with no logbook row is shown from Jira alone.

Design and rationale: `docs/superpowers/specs/2026-10-15-dev-workflow-design.md`.
