---
name: handover
description: Keep a per-ticket inventory of the platforms and objects a ticket touches (DataWorks nodes, tables, Flink jobs, cloud storage) so a replacement can take over, and post it as one Jira comment. Use for "/handover", "update the handover", "handover for PROJ-1234", "who takes over", and at the moments below: a plan or spec names objects, a change artifact is written or edited, the user reports applying a change, a commit, a PR.
---

# Ticket handover

If the main person on a ticket is away, whoever takes over must see where the change lives, above
all for work outside git. The handover is an inventory of platforms and objects with an
environment and a state (`planned` or `touched`). It records where to look, not what changed.

## What it is

- `release/<TICKET>/docs/HANDOVER.md` (committed): branch, an `Objects` table
  (`Platform | Locator | Object | Env | State | Plan | Source`) and `Notes`.
- `scratch/<TICKET>/handover.state.json` (git-ignored): the Jira comment id, the last posted
  fingerprint, the posting state, and the PR and BAST links.
- Helper: `python3 ~/.claude/skills/handover/handover.py <command> --ticket <TICKET> [--repo <path>]`.
  It is local and never talks to Jira or a platform. `--repo` defaults to the git top level of the
  current directory; pass it when the session starts in a folder above the repository.

Kickoff runs `handover.py init --ticket T --branch B` once per Jira-key ticket.

Commands: `init`, `add`, `remove`, `plan-sync`, `note`, `set` (`--branch`, `--pr`, `--bast`),
`show`, `check`, `render`, `changed`, `begin-post`, `abort-post`, `mark-posted`, `adopt`,
`close`, `reopen`.

## Recording (silent, no approval)

Recording touches only local files, so it never prompts.

1. **A plan or spec for the ticket is written, revised or approved.** Read it, print the objects
   you extracted on one line (a typo would create a ghost row), write them to a small JSON file in
   the scratchpad (`[{"platform", "locator", "object", "env"}]`), then run
   `handover.py plan-sync --ticket T --source <plan path> --objects-file <file>`.
2. **You write or edit a change artifact.** `handover.py add --ticket T --platform P --locator L
   --object O --env E --state touched --source <repo-relative path>`.
3. **The user says a change was applied or saved on a platform.** `add --state touched` plus
   `note` saying it was reported by the user.
4. **At each commit and PR,** ask once: "any objects touched outside this session?" and record
   the answer the same way.

What does not count: comments, TODOs, reading or querying an object. Locators: DataWorks
`workspace / workflow / node`; databases `host / database / schema / table`; Flink `job`;
OSS `bucket / prefix`. Never record secrets (the helper refuses assignments such as `password=`,
`token:` or a URL with credentials; `--allow-secret-like` overrides after a look).

## Posting (proposed, then the user's OK)

Triggers: `/commit` (after the commit succeeded), `/generate-pr-message` (both PRs: feature to
`dev` and `dev` to `master`) and `/handover`. A merge is not a trigger.

1. Resolve a pending post first (Recovery below).
2. `handover.py changed --ticket T [--jira-status S]`. Empty output: say nothing. `changed`: show
   `handover.py render --ticket T --jira-status <read from Jira> --date <today>` and ask.
   `no-state` with content to publish counts as changed; `closed` stays quiet.
3. After the user's OK: `begin-post`. Find the target comment: the stored `comment_id`, else list
   the ticket's comments (`listJiraIssueComments`, via the Atlassian read tool) and take the newest
   whose first line is `Handover inventory for <TICKET> (edited in place)`. Edit it with
   `addOrEditJiraIssueComment` (pass the comment id), or create one only if no marker comment
   exists. If the edit is refused (another author's comment) or the id is gone, create a new marker
   comment with the same approved text.
4. `mark-posted --comment-id <id the tool returned>`. It stores the approved fingerprint, not a
   recomputed one.

The Jira description is never edited. If Jira is unreachable, the files are still updated, the
post is skipped with one note, and the next trigger retries. Posting after the user's OK only;
recording is silent.

## Recovery

When `changed` prints `pending`, a post stopped between the Jira write and `mark-posted`. Never
publish unapproved text:

1. Locate the comment: stored id, else the newest marker comment. A missing id counts as not found.
2. If found, read its `Fingerprint:` footer. Equal to the approved fingerprint in the state file
   (`posting.approved`, compared on the first 12 hex): run `mark-posted` with that id (no Jira
   write). Different: the approved write did not land.
3. Not found, or not landed: `abort-post`, show the current text as a new proposal, ask, and post
   with the two-phase flow.
4. If the inventory changed meanwhile, `changed` reports it and the ordinary prompt follows.

A lost state file: `adopt --comment-id ID --fingerprint <footer>` rebuilds it from a marker comment.

## Done and reopening

When Jira reads `Done` at `/generate-pr-message` or `/handover`: if `changed` reports a difference,
propose one final post, then `close`; if nothing changed, `close` straight away (it refuses while a
post is pending or changes are unpublished). A closed ticket stays quiet until Jira leaves `Done`:
`changed --jira-status S` reopens it, and `reopen` does it by hand. If the user declines, the ticket
stays open and only `/handover` offers it again.

## Taking over

1. Open the Jira handover comment: status, objects by platform, branch and PR links.
2. Check out the branch and resume with the kickoff skill (it reads the inventory first), or run
   `handover.py show`.
3. Open the objects with the locators in the table.
4. Read `Notes` for blockers and who to ask; run `handover.py check` for files with no inventory line.
5. Continue the same file. The first post finds the marker comment; if Jira refuses the edit, a new
   marker comment is created and edited from then on.

## Rules

- Personal slug work (no Jira key) gets no automatic `init`.
- `check` scans `release/<T>/{ddl,flink,config,data}` and `scratch/<T>/`, and skips
  `scratch/<T>/docs/`, `CONTEXT.md` and the state file (samples and indexes, not change artifacts).
- Nothing is committed, pushed or posted without the user's OK.
