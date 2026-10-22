# Ticket handover inventory

Date: 2026-10-16. Status: draft for review. Scope: a new `handover` skill and helper under
`CLAUDE/skills/handover/`, a `/handover` command, small additions to the kickoff skill,
`/commit`, `/generate-pr-message`, `bast-generator` and the global `CLAUDE.md`, plus the
`CLAUDE/` template mirror. Builds on `2026-10-15-dev-workflow-design.md` (stages and triggers).

## 1. Purpose

If the main PIC of a ticket is sick or on leave, the person who takes over must be able to see
**where the change lives and what is in progress**, quickly. Git shows the code, but much of this
team's work lives outside git: DataWorks nodes, tables in databases, Flink jobs, cloud storage.
Those objects leave no trace in a branch, and a repo with no remote is invisible to everyone else.

The handover is therefore **an inventory of the platforms and objects a ticket touches**, with
the environment and a state, kept from the start of development and published as one Jira comment.
It records **where to look, not what changed**: the replacement opens the object and reads it.

Goals:

1. A current list of the objects a ticket touches, with enough locator detail to open each one
   (workspace, workflow and node; database type, host, database, schema and table; bucket and
   prefix; job name).
2. A single Jira comment that gives the gist and the links, kept up to date in place.
3. Cheap to maintain: recorded during the work, published only at moments that already exist
   (commit, PR, `/handover`), so it costs a line or two of tool calls and one extra prompt.

Not in scope: describing or diffing what changed, reading any platform back, detecting changes
made directly in a console, finding other tickets that touch the same object, personal work
without a company ticket (nothing starts or posts automatically for it; `/handover` can be run by
hand), and rewriting the Jira description (it stays the requirement). The hosts and names in the
Jira comment are visible to everyone who watches the ticket; that is accepted, because the
comment lives in the company Jira and the repositories involved are private.

## 2. The two files

Committed content and posting bookkeeping are kept apart, so that bookkeeping never dirties the
working tree, never lands on `dev` after a squash merge, and never needs a commit of its own.

### 2.1 The inventory: `release/<TICKET>/docs/HANDOVER.md` (committed)

Created at kickoff, committed on the branch and maintained for the whole development. It is the
source of truth for the objects and notes. The PR to `dev` is final when it is opened, so it
already holds everything; production objects are normally in it from the start, because the
production change is written into `release/<TICKET>/ddl` during development.

```markdown
# Handover: <TICKET>

- Branch: `fea/<TICKET>-short-name`

## Objects

| Platform | Locator | Object | Env | State | Plan | Source |
| --- | --- | --- | --- | --- | --- | --- |
| DataWorks | workspace W / workflow F | node N | dev | touched | `release/<TICKET>/docs/plan.md` | `scratch/<TICKET>/dataworks/N` |
| Hologres | host H / database D / schema S | table T | dev | planned | `release/<TICKET>/docs/plan.md` | - |

## Notes

- Short free lines: who to ask, what is blocked, what to check first.
```

- **Platform** is a short fixed vocabulary (`DataWorks`, `Hologres`, `Hive`, `MaxCompute`,
  `Postgres`, `MySQL`, `Trino`, `Flink`, `OSS`, `Airflow`, `Kafka`, `Other`), compared
  case-insensitively and stored in this casing.
- **Locator** is the path to the container, written the same way each time so the key is
  stable. DataWorks: `workspace W / workflow F`. Databases: `host H / database D / schema S`
  (omit what the engine does not have). Object storage: `bucket B`. Jobs: `project P`.
- **Object** is the thing itself with its type word: `node N`, `table T`, `view V`, `job J`,
  `prefix P`, `topic K`.
- **Env** is the environment the artifact targets: `dev`, `sit`, `uat` or `prod`. The same object
  in another environment is another row.
- **State** is `planned` or `touched` (section 3).
- **Plan** lists the plan, spec or kickoff files that name the object; **Source** lists the
  change artifacts in `release/` or `scratch/`. Both are lists of repository-relative paths with
  forward slashes and no `..`, separated by `; `. The helper normalises equivalent spellings
  (`./a//b`, backslashes) and rejects a path that escapes the repository. `add --source` appends
  to the list. Neither column is published to Jira.
- **The key** of a row is `(Platform, Locator, Object, Env)`, compared case-insensitively with
  whitespace collapsed; the first spelling given is stored. Adding an existing key updates it
  instead of adding a second row.
- **Cell rules.** A `|` inside a cell is written `\|`; a newline in any value is rejected.
- **No secrets.** Hosts and names only. The helper rejects a value that looks like a credential:
  an assignment such as `password=...`, `pwd:`, `token=...`, `secret=...`, `api_key=...`,
  `access_key=...`, or a URL with `user:pass@`. A bare word is not enough: a table called
  `token_log` or `password_reset` is accepted. `--allow-secret-like` overrides a false positive.
- `<TICKET>` is a Jira key or a slug made of letters, digits, dot, underscore and hyphen, and
  nothing else (no slash, no `..`, not empty). It is validated before it is used to build a path.

### 2.2 The local state: `scratch/<TICKET>/handover.state.json` (not committed)

`scratch/` is gitignored (the kickoff skill makes sure of it), so this file never shows in
`git status` and never travels with the branch. It holds only posting bookkeeping and the links
that are known after the branch was committed:

```json
{
  "comment_id": "10123",
  "posted_fingerprint": "<sha256>",
  "posted_date": "2026-10-16",
  "posting": { "state": "idle" },
  "closed": false,
  "pr": "<url or empty>",
  "bast": "<url or empty>"
}
```

`posting` is `{"state": "pending", "approved": "<sha256>", "since": "<date>"}` while a post is in
progress. The file contains no secrets. If it is missing (a new machine, a replacement PIC), the
helper treats the ticket as never posted and the caller rebuilds it from Jira: find the marker
comment (6.2), read its `Fingerprint:` footer and run `adopt`.

## 3. States

| State | Rule |
| --- | --- |
| `planned` | The object is named in a written plan, spec or kickoff file list (a draft counts), and no change artifact exists yet. |
| `touched` | A change artifact for the object exists (Claude wrote or edited a file that creates or alters it: DDL, an edited node copy, a Flink job, a config), or the user reported applying or saving the change on the platform. |

- Not touched, and not recorded: a comment, a TODO, reading an object, searching `scratch/`, or
  looking at its production DDL. Pure exploration leaves no line.
- A draft plan creates `planned` lines because the user wants the intended scope visible from
  the first plan. The cleanup is mechanical: when a plan source is synchronised (`plan-sync`,
  section 5), a `planned` line that no plan source names any more is removed.
- `planned` becomes `touched` when the artifact appears. A `touched` line is never removed by a
  plan synchronisation, even if the plan stops naming it; it is removed only by hand.
- A row removed by hand with `remove` returns at the next `plan-sync` if a plan still names it;
  to make a removal stick, change the plan.
- `touched` does not claim that the change is applied. An "applied" state is deliberately not
  tracked; the user's report that it was applied is what sets `touched` for an object that has
  no file.

## 4. Triggers

Recording is silent, local and free of approval. Posting to Jira is always proposed first and
written after the user's OK, like every other Jira write. A merge into `dev` is not a trigger.

| Event | Action |
| --- | --- |
| Kickoff creates the branch (Jira-key paths A and B; not the slug path C) | `handover init`: the file with the branch and an empty table; no Jira post. |
| A plan or spec for the ticket is written, revised or approved | The model reads the plan, prints the objects it extracted on one line (a typo would otherwise create a ghost row), lists them in a small JSON file, and runs `handover plan-sync --source <plan path> --objects-file <file>`. Silent. |
| Claude creates or edits a change artifact for the ticket | `handover add --state touched --source <path>` for the object it changes. Silent. |
| The user says a change was applied or saved on a platform | `handover add --state touched`, plus `handover note` saying it was reported by the user. Silent. |
| `/commit` | `HANDOVER.md` is committed with the other changed files. Run `handover check` and `handover changed`; if the inventory changed since the last post, add one line to the commit review: "inventory changed (+n): update the Jira handover?". The post itself runs **after** the commit succeeded, so a post never describes uncommitted state. |
| `/generate-pr-message`, for both PRs (feature to `dev`, `dev` to `master`) | Same prompt, using the Jira status the PR flow already reads. When the PR URL is known (the user pastes it, or `gh pr list --head <branch>` returns it) run `handover set --pr`. |
| The Jira status is read as `Done` at `/generate-pr-message` or `/handover` | The final post (section 6.3). |
| `/handover` | Rebuild: `handover check`, ask once "any objects touched outside this session?", then the same prompt. |

Plan and edit events never prompt. When nothing changed since the last post there is no prompt.
The posting step is batched into the turn that already runs the commit or the PR step. `/commit`
reads Jira only after the user accepts a post, to fill the status line; it never reads Jira just
to look for `Done`.

## 5. The helper: `CLAUDE/skills/handover/handover.py`

Stdlib only, Python 3.9 and 3.10+, like `logbook.py`. It owns both file formats so the model
never edits them by hand, and it makes the behaviour testable. Every command takes `--repo PATH`
(default: `git rev-parse --show-toplevel` from the current directory; it refuses to run outside a
repository), because the session starts in an umbrella folder above the repositories.

```text
handover.py init --ticket T --branch B
handover.py add --ticket T --platform P --locator L --object O --env E --state planned|touched [--source PATH] [--allow-secret-like]
handover.py remove --ticket T --platform P --locator L --object O --env E
handover.py plan-sync --ticket T --source PATH --objects-file FILE [--allow-empty]
handover.py note --ticket T --text TEXT [--allow-secret-like]
handover.py set --ticket T [--branch B] [--pr URL] [--bast URL]
handover.py show --ticket T
handover.py check --ticket T
handover.py render --ticket T --jira-status S --date D
handover.py changed --ticket T [--jira-status S]
handover.py begin-post --ticket T
handover.py abort-post --ticket T
handover.py mark-posted --ticket T --comment-id ID
handover.py adopt --ticket T --comment-id ID --fingerprint FP
handover.py close --ticket T
handover.py reopen --ticket T
```

- `add` upserts by key; `planned` never overwrites `touched`; a `touched` add appends its source.
- `plan-sync` reconciles one plan source. `--objects-file` is a JSON list of the objects that
  source names now (`platform`, `locator`, `object`, `env`), validated like `add`. For each
  listed object it adds a `planned` row, or adds the source to the `Plan` cell of an existing
  row. For each row whose `Plan` cell contains the source but is no longer listed, it removes the
  source from that cell; a `planned` row left with an empty `Plan` cell is removed, a `touched`
  row is kept. A row still named by another plan source stays. The helper cannot read free text,
  so the model reads the plan and builds the list; if the plan cannot be read, the model does
  not call `plan-sync`, so nothing is deleted. An empty list would remove every `planned` row
  of that source, so it is refused unless `--allow-empty` is given. The whole file is validated
  before any row is touched: a malformed file, an invalid platform or environment, a value that
  looks like a credential, or a duplicate key in the list is rejected and the inventory is left
  unchanged.
- `note` appends one line to `Notes` after the same credential check. `set --branch` changes the
  branch line of the inventory; `--pr` and `--bast` are stored in the local state.
- `check` is a deliberately narrow safety net. It scans `release/<TICKET>/{ddl,flink,config,data}`
  and everything under `scratch/<TICKET>/` (the change artifacts and the dev forms of objects
  that live outside git) and lists the files whose path appears in no `Source` cell. Its output
  names the directories it scanned. Files tracked elsewhere in the repository (application
  code, DAGs, scripts) are already in git and are not part of the scan. It does not guess
  objects from file contents; it reports the path so Claude can add the line.
- `render` groups by platform and ends with the branch, the PR, the BAST link and the path of
  `HANDOVER.md`, includes the `Notes` lines, and ends with a footer line
  `Fingerprint: <first 12 hex characters>` that lets a later reader tell which version a Jira
  comment holds. It prints a compact form (counts per platform and the file link) when there are
  more than 25 objects. The Jira status and the date are **arguments**: the caller reads the
  status from Jira at posting time, so the helper never talks to Jira and never caches a status.
  If the status cannot be read, the caller passes `unknown`.
- **Fingerprint.** SHA-256 of the rendered body **without** the date line, the Jira status
  line and the fingerprint footer, with rows sorted and whitespace normalised. The published
  fields are therefore exactly: each row's platform, locator, object, env and state, the branch,
  the PR link, the BAST link, the `Notes` lines and the compact-or-full form. `Plan` and `Source`
  do not change it. Any change to a published field changes it; reordering equivalent rows does
  not. A footer holds only the first 12 hex characters, so footers are compared by that prefix.
- `changed` prints one word, with this precedence: `pending` (a post is in progress, recovery
  first), `closed`, `changed` (the fingerprint differs from the posted one, or nothing was ever
  posted and the inventory is not empty), or nothing. With `--jira-status S` where S is not
  `Done` and the ticket is closed, it reopens the ticket first (clears `closed`) and then
  evaluates as above, so a ticket that returns to development is tracked again. When the state
  file is missing it prints `no-state`.
- `begin-post` computes the fingerprint of the inventory at that moment and stores it as the
  approved one; it must run in the same step as the proposal the user approved, with no edit in
  between. `mark-posted` records **that approved fingerprint**, never a recomputed one, and
  refuses when no post is pending. The stored "posted" fingerprint therefore always describes
  what Jira holds. `abort-post` sets the state back to idle and changes nothing else. `adopt`
  stores a comment id and the fingerprint read from a Jira comment footer, to rebuild a missing
  state file.
- `close` refuses while a post is pending and while the fingerprint differs from the posted one.
  It accepts when the fingerprint matches, or when the inventory has no rows and no notes (there
  is nothing to publish). `reopen` clears `closed` unconditionally.
- A hand-edited file is tolerated: unknown lines are kept, a malformed table row is reported by
  line number and never dropped or rewritten, and a missing file is a clear error (run `init`).
  Valid edits to other rows still proceed. Every write command rewrites the file atomically
  (temporary file, then replace) and preserves unknown lines, malformed rows, the `Notes` section
  and line endings. After a merge conflict in the table, take the branch tip and run `check`.

## 6. The Jira comment

### 6.1 Content and tool

- One comment per ticket, created at the first approved post and **edited in place** afterwards
  with `addOrEditJiraIssueComment` (it takes an optional comment id to edit and returns the id of
  the comment; the exact parameter names are confirmed against the tool schema in the plan).
- The first line is a stable marker, `Handover inventory for <TICKET> (edited in place)`. It is
  how the comment is found again if the stored id is lost (6.2).
- Body: the marker line, the update date, the status line (the Jira status passed by the caller and
  the count of `planned` and `touched` objects), the objects grouped by platform, the `Notes`
  lines, the branch, PR and BAST links, the path of `HANDOVER.md`, and the fingerprint footer.
  Links follow the kickoff skill's "Writing links" rules.
- The description is never edited. There is no attachment.
- If Jira is unreachable or the ticket has no Jira key, the files are still updated, the post is
  skipped with one note, and the next trigger retries.

### 6.2 Posting and recovery

A post is two-phase so that a crash between the Jira write and the local bookkeeping can neither
create a duplicate comment nor publish text the user has not approved:

1. Show the proposed text and wait for the user's OK.
2. `begin-post` records the pending state with the fingerprint of the text just shown.
3. Find the target comment: the stored id; with no stored id, **list the ticket's comments and
   take the newest whose first line is the marker** (this search always precedes a create, so a
   new machine or a lost state file never produces a second comment). Edit that comment, or
   create one only if no marker comment exists. If the edit is refused (a replacement PIC
   usually cannot edit another author's comment) or the id no longer exists, create a new marker
   comment with the same approved text; from then on that comment is the target, and searches take
   the newest marker comment. The tool's result is the authority on whether the write worked.
4. `mark-posted --comment-id ID` stores the id, the date and the **approved** fingerprint recorded
   in step 2 (not a new calculation) and sets the state to idle.

If the process stops between steps 3 and 4, the next trigger sees `pending` from `changed`.
Recovery **verifies** the earlier write and never publishes anything on its own:

1. Locate the comment: the stored id, else the newest marker comment. A stored id that no longer
   exists counts as not found.
2. If a comment is found, read its body and its `Fingerprint:` footer. When the footer equals
   the approved fingerprint, the earlier write landed: run `mark-posted` with that id (no Jira
   write), which records the approved fingerprint, and continue. When it differs, the approved
   write did not land.
3. If no comment is found, or the approved write did not land, run `abort-post` and treat the
   current inventory as a new proposal: show the current text, ask for the user's OK, and post
   it with the same two-phase flow.
4. After step 2, the stored posted fingerprint is the approved one, so if the inventory changed
   in the meantime `changed` reports the difference and the ordinary prompt follows: newer
   content always goes through approval and is never recorded as posted.

A comment carrying the marker is never duplicated by a retry, and text the user did not approve
is never written.

### 6.3 Final post at `Done`

When the caller reads Jira `Done` at `/generate-pr-message` or `/handover`:

1. If `changed` reports a difference, propose one final post (the same two-phase flow); after it
   succeeds, run `close`.
2. If nothing changed, run `close` straight away, without a prompt. `close` itself refuses while
   a post is pending or unpublished changes remain (section 5), so it cannot hide required work.
3. A closed ticket stays quiet for every later prompt, until Jira shows it is no longer `Done`:
   the next `changed --jira-status S` reopens it (a rollback or a defect after release).
4. If the user declines or Jira is unavailable, the ticket stays open. The final post is offered
   again only at the next `/handover`; `/generate-pr-message` stays silent about it.

### 6.4 Order of operations at a trigger

`/commit`, `/generate-pr-message` and `/handover` follow the same order, so the three behave alike:

1. **Resolve a pending post** (6.2): verify and adopt, or abort. Nothing is written to Jira
   without approval.
2. **Compare** the current inventory with the stored posted fingerprint (`changed`, passing the
   Jira status when it is known).
3. **Jira status not `Done`, or not read (`/commit`):** if the inventory changed, show the
   one-line prompt; with no change, say nothing.
4. **Jira status `Done` (`/generate-pr-message`, `/handover`):** apply the final-post policy of
   6.3. A fresh proposal produced by step 1 is the final post. If the inventory is unchanged,
   `close` immediately. If the user declined or Jira failed earlier, `/handover` is the only
   trigger that offers it again.
5. **`close`** runs only when its preconditions hold (section 5).

## 7. Where the rules live

- A new section in the global `CLAUDE.md` ("Ticket Handover") states the triggers and that
  recording is silent while posting is proposed. It is mirrored into `CLAUDE/CLAUDE.md`.
- `jira-ticket-kickoff` runs `handover init` in its branch step for Jira-key tickets, and its
  resume path (B) reads `HANDOVER.md` first (section 11). It also makes sure `scratch/` is
  ignored, as it does today.
- `bast-generator` reads the inventory as a scope checklist and records the BAST page link
  with `handover set --bast` (section 11).
- `/commit` gains the check-and-prompt step and the allowed tool `Bash(python3:*)`; the Jira
  write after an accepted post uses the Atlassian tools, so those are added to its allowed
  tools too. `/generate-pr-message` gains the same step and `handover set --pr`. The plan step
  relies on the global rule, because `writing-plans` belongs to a plugin that is not edited here.
- The dev workflow guide's trigger table gets a "handover" column or section.

## 8. Error handling

- No inventory file for a ticket: the commit and PR steps skip the prompt and say so once.
- A value that looks like a credential: `add` and `note` refuse it and name the field.
- A malformed table row or unknown line: reported by line number and never discarded or rewritten;
  valid edits to the rest of the file still proceed atomically.
- An unreadable plan source: the model does not call `plan-sync`, so no row is removed.
- A ticket id with a path separator or `..`, or a value with a newline: refused before anything
  is built or written.
- A stopped post: the pending state is found by the next trigger and recovered (6.2).
- An edit refused by Jira permissions: a new marker comment is created (6.2).
- `close` while a post is pending or unpublished changes remain: refused with the reason.
- Not inside a repository: the helper refuses and says which directory it looked at.
- The helper never talks to Jira or any platform; posting is done by the model with the
  Atlassian tools after the user's OK.

## 9. Testing

- Parsing and writing: an empty file, a table with several rows, hand-edited cells, a malformed
  row (kept and reported), unknown lines preserved, CRLF, a `|` escaped inside a cell, a newline
  rejected.
- Keys: `Table T` and `table  t` are one row; the same object in `dev` and `prod` are two;
  `Plan` and `Source` lists with several paths, `add --source` appending, `check` matching any.
- `add` upsert by key; `planned` never downgrades `touched`; `remove`; `remove` followed by a
  `plan-sync` that still names the object brings the row back.
- `plan-sync`: a draft plan adds `planned` rows; a revised plan removes the rows it no longer
  names; a row still named by another plan source stays; a `touched` row is never removed; an
  empty list is refused without `--allow-empty`; a malformed objects file, an unknown platform
  or a duplicate key changes nothing; the `Plan` cell of a `touched` row is updated but the row
  stays.
- Secret check: `password=x`, `token: abc`, `api_key=...` and a `user:pass@` URL are refused, in
  `add` and in `note`; `token_log`, `password_reset` and `secret_santa` are accepted; the override
  flag works.
- `check`: files with and without a matching `Source`, nested `scratch/` paths, an absent
  folder, and it names the directories it scanned.
- `render`: grouping by platform, the compact form above 25 objects, links, stable order, the
  footer.
- Fingerprint: `changed` after an add, after a state change, after a PR or BAST link update,
  after a branch change and after a `note`; not after a `Source` or `Plan` change, a date change
  or a Jira status change passed to `render`; unchanged after `mark-posted`; unchanged when only
  the order of insertion differs; footers compared by their 12-character prefix.
- State and lifecycle: `changed` prints `pending` before `closed` when both hold, `closed` after
  `close`, `reopen` clears it, and `changed --jira-status "Data Development"` on a closed ticket
  reopens it; a changed inventory at `Done`, an unchanged one, and a declined or failed final
  post (offered again only by `/handover`). A missing state file prints `no-state`, and `adopt`
  rebuilds it. After `mark-posted`, `git status` shows a clean tree, because the state file is
  ignored.
- Recovery by failure injection, for the first post and for an edit: stop after the Jira write,
  leave the post pending, then verify the four outcomes of section 6.2: the comment found with a
  matching footer is adopted and marked posted with no write; a comment with a different footer,
  or none, leads to a fresh proposal that needs approval; an inventory change after the crash is
  never published without approval; no second comment is ever created while a marker comment
  exists. In particular: approve version A, the Jira write lands, the process stops, the inventory
  becomes B, recovery runs: the stored posted fingerprint is A's, `changed` reports B, and B is not
  published until approved. `mark-posted` refuses when no post is pending and never stores a
  recomputed fingerprint; `abort-post` leaves everything else unchanged.
- A create always follows a marker search: with no stored id and an existing marker comment, the
  comment is adopted, not duplicated; an edit refused for another author's comment falls back to
  a new marker comment, and later searches take the newest.
- `close`: refused while pending and while changes are unpublished; accepted after a successful
  final post, for an unchanged inventory, and for an empty inventory that was never posted.
- Order of operations (6.4) with Jira `Done`: pending recovery with an unchanged inventory closes
  without a prompt; with a changed inventory it proposes the final post; a declined final post is
  offered again only by `/handover`, not by `/generate-pr-message`.
- Validation and preservation: ticket ids such as `../x`, `a/b` and empty are refused; paths
  outside the repository are refused; a file with malformed rows, unknown lines and `Notes`
  survives every write command unchanged apart from the intended edit, and valid edits still
  succeed when another row is malformed.
- Repository discovery: the helper run from the umbrella folder, from a subdirectory and outside
  any repository.
- Skill and command text sweeps (the triggers and the "proposed, then OK" rule are present;
  the kickoff resume path reads `HANDOVER.md` first; `bast-generator` compares its scope with
  the inventory and records the BAST link; `/commit` and `/generate-pr-message` run the check for
  both PR targets, and `/commit` lists the tools it needs), and the config-free install path.
- Python 3.9 and 3.12 (`uv run --no-project --python X`).

## 10. Rollout

One unit: helper, tests, skill, command, the small additions to the kickoff skill (init and
resume), `bast-generator`, `/commit` and `/generate-pr-message`, the global rule, the trigger
table and the status note in the dev workflow guide, and the `CLAUDE/` mirror, in one PR to
`dev`. The `/pipeline` flag (section 11.2) is a separate follow-up. No data migration. After the
merge the live `~/.claude` files are updated (backup first). The first real use is on the next
ticket, at kickoff; for a ticket already in flight the user can run `/handover` once to create
the files from what exists.

## 11. Integration with the dev cycle

The handover rides on the stages, statuses and triggers of the dev workflow
(`2026-10-15-dev-workflow-design.md`). It adds no stage and no Jira status of its own, and it
never moves a ticket; it only records and publishes where the work lives.

### 11.1 Stage by stage

| # | Stage (Jira status) | Handover action | Other tools in the same step |
| --- | --- | --- | --- |
| 1 | Assignment (`[BU] Todo`) | None: no branch or ticket folder yet. | `jira-in-da-sync` clones the IN ticket. |
| 2 | Analysis (`Data Analysis`) | Kickoff runs `init`. Objects named in the spec and plan are synchronised as `planned`, silently. Committing the spec or plan raises the first post prompt, so a replacement sees the intended scope early. | `jira-ticket-kickoff`, `brainstorming`, `writing-plans`, `/commit`. |
| 3 | Develop and SIT (`Data Development`) | Every change artifact Claude writes or edits adds or upgrades an object to `touched`, silently. A user report such as "applied the DDL in dev" does the same. `/commit` prompts when the inventory changed. | `/commit`, the logbook row (status `Development`). |
| 4 | Testing, UAT (`Testing`) | PR to `dev` opened: `set --pr` once the URL is known, then the post prompt in the same turn as the Jira move to `Testing`. | `/generate-pr-message`, the Jira status check, the logbook row (`Testing`). |
| 5 | Generate BAST (`Testing`) | `bast-generator` compares its scope rows with the inventory and lists any object in one but not the other; it records the BAST page link with `set --bast`. | `bast-generator`. |
| 6 | User approval (`Ready For Release`) | None: a merge is not a trigger, and the committed file is already final in `dev` with the squash. | The Jira move to `Ready For Release`, the logbook row. |
| 7 | Register CAB (`Ready For Release`) | PR `dev` to `master`: the same check and prompt. Production objects are normally already in the inventory; an object found late is added on the next work branch. | `/generate-pr-message` (PR 2), the BAST update, the CAB register. |
| 8 | CAB approval (`Deployment`) | Nothing automatic. | The user moves the ticket; the board reads the register. |
| 9 | Deployed, PAT (`PAT`) | If the user reports an object deployed to prod that has no `prod` row, `/handover` adds it on the next work branch. | The register's deploy and PAT dates. |
| 10 | Closed (`Done`) | The final post lifecycle runs (section 6.3): one last post if the inventory changed, then `close`. The committed file stays in `release/<TICKET>/docs/` as the record of what the change touched. | The logbook archives the ticket 7 days after `Done`. |

After the squash merge no handover command writes to `dev`: the posting bookkeeping lives in the
ignored state file, so the committed file changes only when an object is genuinely added, and
that goes on the next branch for the ticket (a follow-up branch if none exists), by the branch
rules.

Silent steps (plan, edit, user report) never touch Jira. A post is only ever proposed at a
commit, a PR, or `/handover`, and is batched into the turn that already runs that step, so it
adds a prompt line and one write call, not a separate turn.

### 11.2 Touch points with the other tools

- **Kickoff, resume path (B).** When a ticket is resumed, whether by the same PIC after a break
  or by a replacement, the recap reads `HANDOVER.md` first: the branch, the object table
  (with `planned` versus `touched`), the notes and the result of `handover check`; the state
  file, when present, supplies the PR and BAST links, otherwise they are rebuilt from the Jira
  comment. That is the take-over, not a separate procedure.
- **`/commit` and `/generate-pr-message`.** Each runs `handover changed` and `handover check`.
  The prompt is one line in the existing review output.
- **`bast-generator`.** The inventory is the cross-check for the BAST scope: an object in the
  inventory that is missing from the BAST, or a BAST row with no inventory line, is listed for
  the user. It does not edit the BAST from the inventory.
- **Logbook.** Untouched. The logbook row is the weekly-report line; the handover is the object
  list. Neither reads the other. A logbook `notes` entry may say "see the handover".
- **CAB register.** The register records what Ops deploys and when; the inventory records what
  the ticket touches. They are compared by a person, not by the helper.
- **`/pipeline` board.** Follow-up, not in this unit: show `handover: posted | changed |
  missing` per ticket and flag a ticket past `Data Development` that has no file. The board
  would read the file from the checkout of the branch, or with `git show origin/<branch>:`
  when that branch is not checked out.

### 11.3 Taking over a ticket

1. Open the Jira handover comment: status, objects by platform, branch and PR links.
2. Check out the branch and run the kickoff resume path, or `handover show --ticket T`.
3. Open the objects in the platforms using the locators in the table (workspace, workflow and
   node; host, database, schema and table).
4. Read the `Notes` section for blockers and who to ask, and run `handover check` for any file
   with no inventory line.
5. Continue the same file: the replacement's Claude session records new objects the same way. The
   first post finds the marker comment, adopts it, and if Jira refuses the edit (another author's
   comment) creates the replacement's own marker comment, which later posts keep editing.

## 12. Open points

None. Confirmed by the user on 2026-10-16: the handover records objects and where they live,
not what changed; it is created and maintained from the start of development; the states are
`planned` and `touched` with the rules above; recording happens on plans, edits, commits and
PRs; the Jira post is prompted only at commit, PR and `/handover`, with the OK each time; one
comment edited in place; the inventory is committed on the branch; a draft plan already creates
`planned` lines.
