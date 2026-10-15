# Dev workflow: stages, Jira statuses, git steps and the pipeline board

Date: 2026-10-15. Status: draft for review. Scope: the personal Claude Code tooling
(`~/.claude` skills and commands) and its `CLAUDE/` template in this repo.

## 1. Purpose

Two problems to fix:

1. **Forgotten steps.** After a PR opens or merges, the Jira transition, logbook row, BAST
   update or branch cleanup is sometimes missed.
2. **No overview across repos.** With several tickets in flight it is hard to tell which are
   in development, in UAT, waiting for CAB, deploying, in PAT, or finished.

Success: every trigger event prompts for the next step; one command lists every open ticket
and repo by stage with the next action; Jira, git and the logbook use the same stage words.

Not in scope: new tools for Jira or git, changing the branch strategy, automating CAB or
deployment, repos outside the DA ticket flow.

## 2. Standing rules that stay

- Nothing is committed, pushed or opened as a PR unless asked.
- Logbook rows and Jira transitions are proposed first and written after an OK.
- A PR to `dev` is complete when opened (changelog included); `dev` is never force-pushed.
- Personal tooling runs on Python 3.9 and 3.10+; `~/.claude` changes are mirrored into the
  `CLAUDE/` template with placeholders; no internal hosts, ids or logbook data in the repo.

## 3. Stage model

Jira order: `Data Analysis` → `Data Development` → `Testing` (UAT) → `Ready For Release`
(CAB) → `Deployment` (CAB approved) → `PAT` (deployed, production assurance test) → `Done`
(no error one week after PAT). `Hold` can occur at any point.

| # | Stage | Jira status | Git / GitHub step | Trigger and tool |
| --- | --- | --- | --- | --- |
| 1 | Assignment (IN or non-SRF) | `[BU] Todo` | none | `jira-in-da-sync` |
| 2 | Analysis: brainstorm, design, plan | `Data Analysis` | spec or plan under `release/<TICKET>/` | `jira-ticket-kickoff`, `brainstorming`, `writing-plans` |
| 3 | Develop and SIT | `Data Development` | `fea/` or `fix/` branch off `dev`; optional merge into `sit` | `/commit` |
| 4 | Testing (UAT) | `Testing` | PR open to `dev`, not merged | `/generate-pr-message` (PR 1) |
| 5 | Generate BAST | `Testing` (no change) | PR still open | `bast-generator` |
| 6 | User approval | `Ready For Release` | PR squash-merged into `dev` | merge event prompt |
| 7 | Register CAB | `Ready For Release` (no change) | BAST updated with user capture and approval; `dev` to `master` PR open, may merge directly | `/generate-pr-message` (PR 2), BAST update |
| 8 | CAB approval | `Deployment` | none required (`master` may already be merged) | user moves the ticket |
| 9 | Deployed, PAT | `PAT` | none | user moves the ticket |
| 10 | Closed | `Done` | branch cleanup | board flags 7 or more days in `PAT` |

Correction to the current rules: today a PR to `master` moves the ticket to
`Ready to Release`. In this flow `Ready For Release` starts at user approval (stage 6, the
merge into `dev`), and a PR to `master` changes nothing in Jira.

Order of release steps, as the user runs it: the merge into `master` is not the release
gate. The `dev` to `master` PR may merge before CAB approval; deployment itself is a separate
step that starts only after CAB approval (`Deployment`) and ends with `PAT`. The board and
prompts therefore never treat a `master` merge as deployed, and never suggest a deployment
action before the ticket reaches `Deployment`.

Confirmed by the user on 2026-10-15: merging `dev` into `master` does not deploy anything by
itself; deployment is a separate step after CAB approval. Status names: `Data Analysis`,
`Testing`, `Ready For Release`, `Deployment`, `PAT`, `Done`, `Hold` and `[BU] Todo` were seen
on live DA tickets, and the user confirmed that `Data Development` exists. The workflow is
forward-only, in the order of the Jira order line above, from `[BU] Todo` to `Done`.
`Hold` and any unusual backward move are exceptions: the board reports them and prompts
nothing for them.

## 4. Logbook statuses follow the Jira stages

`PR to dev`, `Merged to dev`, `Merged to sit` and `PR to master` are git steps and do not
help the weekly presentation. The logbook uses the Jira stage words; git detail lives in the
board.

| Logbook status | Weekly page word | Jira status | Replaces |
| --- | --- | --- | --- |
| `Analysis` | `ANALYST` | `Data Analysis` | same |
| `Development` | `DEVELOPMENT` | `Data Development` | `In progress`, `Merged to sit` (SIT is internal testing inside development) |
| `Testing` | `TESTING` | `Testing` | `PR to dev` |
| `Ready For Release` | `READY FOR RELEASE` | `Ready For Release` | `Merged to dev`, `PR to master` |
| `Deployment` | `DEPLOYMENT` (new) | `Deployment` | part of `Released` |
| `PAT` | `PAT` (new) | `PAT` | part of `Released` |
| `Done` | `DONE` | `Done` | `Released`, `Done` |
| `Fixing` | `FIXING` | none | same |
| `Hold` | `HOLD` | `Hold` | same |

Decisions:

- Existing `Released` rows follow the exhaustive rule in section 7: a known Jira status
  decides first, an unknown status goes to the user's review list, and a known, conflicting
  Jira status is never overridden with `Done`. A recent or undated row is only flagged
  "check" (section 7).
- When Jira and the logbook disagree on status, **Jira wins** (the user moves the ticket
  there). `check` reports the difference and proposes the logbook update.
- `JIRA_STATUS` changes: `PAT` goes from `DONE` to `PAT`, and `Deployment` is added (it is
  missing today, so `check` silently skips Jira-versus-logbook comparison for those
  tickets). Both also get a `STATUS_COLOR` entry. Only `Done` counts as finished for the
  archive rule (7 days after it became Done). Other Jira words the helper already knows map
  as before: `Bug Fixing` to `FIXING`, `Revisi SRF Data` to `ANALYST`, `In Progress` to
  `DEVELOPMENT`.
- Non-Jira work (slugs, `bug-<n>`) has no Jira flow; its `Done` means the work is finished,
  and `Done` rows for it follow the same archive rule. For logbook tooling and other work
  that is not BFI work, `Done` is set once its PR to `master` is merged: there is no CAB,
  `Deployment` or `PAT` for it.
- "Someone else's court" (follow-up highlight on `LastUpdate`) becomes `TESTING`,
  `READY FOR RELEASE`, `DEPLOYMENT`, `PAT`; `DONE` and `HOLD` are never highlighted.
- Lozenge colours: Confluence status lozenges only accept `neutral`, `purple`, `blue`,
  `red`, `yellow` and `green`. `DEPLOYMENT` takes `blue` and `PAT` takes `purple`; the words
  differ even where a colour repeats. Confirm on the live page after the first publish.
- Jira wins applies in the helper and the instructions, not just in `check`. Places to
  rewrite: the logbook `SKILL.md` lines that say a ticket with rows keeps the logbook
  status (publish step 0a and the tracker description) and the "whichever changed more
  recently" rule; `item_status` in `logbook.py`, which is logbook-first today, becomes
  Jira-first when the cache entry is fresh; and the "Jira is newer / logbook is newer"
  verdict in `check`, which becomes "Jira wins, proposed logbook update".

## 5. Components

### 5.1 `/pipeline` board (new)

A read-only command, implemented as a subcommand of `logbook.py` (`pipeline`), so it reuses
the Jira cache, `config.json` `repo_paths` and the `gh` calls that `check` already makes.

- Input: assigned DA tickets from Jira (refreshed through the same step as the logbook
  publish), local branches and commits per repo, open and merged PRs per repo (`gh`), and
  the logbook.
- Output: tickets grouped by stage in the order of section 3, each line showing ticket,
  repo, Jira status, git state (branch, PR number and state) and the next action.
- Flags, each with the suggested fix and no automatic write:
  - PR merged into `dev` but Jira is still `Testing`.
  - `dev` to `master` PR open or merged while Jira is still `Testing` (the user approval
    step was skipped). An open or merged `master` PR with Jira at `Ready For Release` is a
    normal state and is not flagged.
  - Branch has commits, no PR, Jira still `Data Analysis`.
  - Ticket in `PAT` for 7 or more days (propose `Done`).
  - Ticket in `Hold`, listed separately.
  - Jira status and logbook status differ (Jira wins).
- Reuses the cache rule from the logbook skill: a stale cache is refreshed first.

Precedence rules (the board suggests; it never rewrites Jira):

1. Jira supplies the recorded status. Git and GitHub evidence only identifies events and
   inconsistencies; it never changes a status by itself.
2. `Hold` wins: a ticket on hold shows only "on hold" and the hold date, with no
   workflow prompts, even if a PR merged meanwhile (that is reported as a note).
3. Missing or unreadable evidence gives an explicit `unknown` for that fact, and any
   suggestion that depends on it is left out. Examples: a repo not in `repo_paths`, `gh`
   unavailable, a ticket in `Deployment` with no matching PR (shown, not flagged).
4. A ticket with no logbook row is shown from Jira alone; a logbook row for another repo
   than the PR's repo is reported as a mismatch, not merged.

Two modes:

- **Live:** decided per ticket: that ticket's Jira status was refreshed today; flags and next
  actions are shown for it. A ticket refreshed earlier is marked `(stale)` and gets no
  Jira-dependent flags. The `check` comparison uses a Jira status only when it is fresh
  (within 7 days), the same rule the weekly page uses.
- **Degraded:** Jira could not be reached; cached statuses are shown with the cache date
  (the cache gets a `refreshed` timestamp, set by `cache set`) under a "stale, not verified" banner, and Jira-dependent flags are suppressed. Git and
  PR data are still shown with their own availability note.

PAT age: the date a ticket entered `PAT` comes from the Jira status-change timestamp (the
issue changelog, as the logbook already does for `Hold`). Seven days means seven calendar
days in the local date (Asia/Jakarta). The helper cannot call Jira, so the Claude session
reads the changelog and stores the date with `cache set --pat-since <date>` (the same way
`--hold-since` is stored today). If it is missing, the board shows "PAT date unknown" and
does not propose `Done`.

### 5.1.1 Git evidence to implied status

`pr_stage`, `git_evidence` and the `STAGE` ranks in `check` are rewritten. New `STAGE`
ranks, lowest to highest: `Analysis` 1, `Development` 2, `Testing` 3, `Ready For Release`
4, `Deployment` 5, `PAT` 6, `Done` 7; `Fixing` and `Hold` sit outside the order.

| Git / GitHub event | Implied logbook status |
| --- | --- |
| Branch with commits, no PR | `Development` |
| Merge into `sit` | `Development` |
| PR open to `dev` | `Testing` |
| PR merged into `dev` | `Ready For Release` |
| PR to `master` open or merged | no status implied (returns none) |

`check` compares the implied status with the logbook and Jira by rank and reports only the
case where git implies a higher rank than the recorded status. Jira statuses `Fixing`-like
words (`Bug Fixing`) show as a side state next to the stage the ticket is in, and
`Revisi SRF Data` is grouped with `Data Analysis` on the board.

### 5.2 Trigger prompts

Each event proposes the next step when it happens (at the end of the skill or command that
caused it), and never acts without an OK. There is no prompt store: event prompts fire at
the event, and the board's flags are derived from current state, so an unresolved gap
shows on every run until it is fixed. That repetition is intended, because it is the
reminder; resolving the gap (or moving the ticket to `Hold`) is what stops it.

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

### 5.3 Rule and skill edits

- `~/.claude/CLAUDE.md` "Jira Status on PRs": PR to `dev` moves to `Testing`; merge into
  `dev` moves to `Ready For Release`; PR to `master` changes nothing.
- `/generate-pr-message` "Jira Status Check" phase: same change; the logbook row proposed at
  its last step uses the new status words.
- Also swept for old words (`In progress`, `PR to dev`, `Merged to ...`, `PR to master`,
  `Released`, `Ready to Release`): `generate-pr-message.md` (Jira status check, logbook
  step, checklist), `~/.claude/CLAUDE.md` ("Jira Status on PRs" and the logbook section),
  `jira-ticket-kickoff` (the row it proposes), `bast-generator` (proposes a row without a
  status), the logbook `SKILL.md` status table, examples and the "non-code work finished"
  row, and the same lines in the `CLAUDE/` copies.
- `logbook` skill: new status table, new page words and court sets, the Jira-wins rule, the
  `pipeline` subcommand.
- `jira-ticket-kickoff`, `bast-generator`: their last step proposes the logbook row with the
  new words and names the next trigger.
- Jira transitions: pick the transition by its target status. The expected path is
  forward-only through the Jira order in section 3. When the target is not offered from
  the ticket's current status, report the offered transitions and change nothing (the
  existing rule). Before migrating the live logbook, verify the transitions read-only: list
  the transitions offered on existing tickets that are in `Testing`, `Ready For Release`,
  `Deployment` and `PAT`, and move nothing (a forward-only move on a real ticket cannot be
  undone and Jira changes are proposed first).
- A short workflow doc (this page's table, trimmed) in `docs/guidelines/DEV-WORKFLOW.md`
  for reuse; `CLAUDE/` template files updated the same way, placeholders for company values.

## 6. Data flow

```text
Jira status  --\
git branches  ---+--> logbook.py pipeline --> board + flags --> proposed Jira / logbook updates
GitHub PRs   --/                                        (written only after the user's OK)
logbook CSV  --/
```

Source of truth per fact: ticket status, title and dates come from Jira; PR and branch
state from git and GitHub; task wording and notes from the CSV. Section 4 sets Jira as the
winner for status.

## 7. Migration

The helper rejects any unknown status in `read_rows`, and every command goes through it, so
the moment the new status list is deployed the old CSV cannot be read. The migration
therefore has its own reader and runs in the same sitting as the helper deployment.

1. Back up, with a timestamp: `logbook.csv`, `logbook-archive.csv` and `jira-cache.json`,
   and the live copies of `logbook.py`, the logbook `SKILL.md`, `CLAUDE.md` and
   `generate-pr-message.md`. `~/.claude` is not a git repository, so these copies, not
   git, are what a rollback restores.
2. Refresh Jira for the migration. Publish step 0a skips finished tickets (it queries
   `statusCategory != Done`), so fetch every ticket that has a `Released` row with
   `key in (...)` and store each status with `cache set --jira-status`. The helper cannot
   call Jira, so this is done by the Claude session before the dry run.
3. Dry run: `logbook.py migrate-statuses --dry-run` reads the old files with a plain `csv`
   reader and a `LEGACY_STATUSES` set (not `read_rows`), prints the old-to-new mapping per
   row and the counts per status, and writes nothing. It handles the archive file the same
   way. Words that pass through unchanged: `Analysis`, `Fixing`, `Hold`, `Done` and an
   empty status. Other words: `In progress` to `Development`, `PR to dev` to `Testing`,
   `Merged to sit` to `Development`, `Merged to dev` and `PR to master` to
   `Ready For Release`. `Released` follows the rules below.
4. Rules for `Released`, per ticket (the page uses a ticket's last row, so only the last
   row of a ticket takes the Jira-derived status; its earlier `Released` rows are history
   and become `Done`):
   1. **Jira status known and mapped** (section 4 table): the last row takes that status.
      `Hold`, `Testing`, `Ready For Release`, `Deployment`, `PAT` and `Done` are kept as
      they are. If the row is recent (its own date, the `date` of the ticket's last
      logbook row, within the last 7 days) or has no date, it is flagged "check" in the
      report but keeps the Jira status; a known Jira status is never replaced with `Done`.
   2. **Jira status unknown, or known but without a logbook status:** nothing is guessed
      and nothing is written for the row. It goes to the review list, and the user
      resolves it with `--resolve TICKET=<status>`, naming any status of the new list.
   3. A row under rule 1 that the user disagrees with is changed afterwards with a normal
      `add`.
   The 7-day check concerns only the logbook's own recency and is separate from the
   PAT-age rule in 5.1, which uses the Jira status-change timestamp.
5. After the user's OK, run `migrate-statuses` without `--dry-run`: write the migrated CSV
   to a temporary file, validate it (same row count, every status in the new list, header
   unchanged), and replace the live file atomically.
6. `add` accepts only the new words from then on, so a stale skill text fails loudly
   instead of writing old values.
7. Keep the backups until the first `pipeline` and `check` runs pass. Recovery if either
   fails or the migration was wrong: copy the backed-up CSVs and cache back, and copy the
   backed-up helper and instruction files back, so the old words and the old helper are
   active together again.

## 8. Error handling

- Missing `gh` or no network: the board still lists Jira and local git data and says that PR
  state is unavailable; it never guesses a PR state.
- A repo without an entry in `config.json` `repo_paths`: listed as "not tracked".
- Jira unreachable: use the cache, mark the board with the cache date (degraded mode, section 5.1).
- A ticket with no logbook row: shown from Jira alone.
- All writes keep the helper's existing guards (header check, atomic write).

## 9. Testing

- The helper has no tests today. They are new, live in `tests/test_logbook.py`, load
  `CLAUDE/skills/logbook/logbook.py` by path with `importlib` (the pattern of
  `tests/test_okf_lint.py`) and set `LOGBOOK_PATH` and the other paths before import, or
  reload the module.
- Unit tests for the status table, the page-word map, the court sets, the migration map and
  the stage derivation (stage from Jira status plus git state), including the flags in 5.1.
- A fixture CSV with old words that migrates to the new ones (all passthrough words
  included, archive file included, several `Released` rows for one ticket); `add` rejects
  an old word; the old CSV is unreadable by `read_rows`, readable by the migration.
- `JIRA_STATUS` and `STATUS_COLOR` contain `Deployment` and `PAT`; `check` compares a
  `Deployment` ticket; the git-evidence table in 5.1.1.
- The `refreshed` and `--pat-since` fields in `cache set`.
- Run on Python 3.9 and 3.12 (`uv run --no-project --python X`).
- Migration: `Released` rows with Jira `Hold`, `Testing`, `Ready For Release`,
  `Deployment`, `PAT`, `Done` and an unknown status; rows just inside and just outside the
  7-day cutoff and a row with no date; a recent `Released` row with Jira `Hold` stays
  `Hold` (flagged, never offered a contradicting choice); every `Released` row ends with
  exactly one outcome.
- A requested Jira transition that is not offered: the transitions are reported and the
  ticket is unchanged.
- Degraded mode (Jira down, git and `gh` up): Jira-dependent flags are suppressed.
- Hold precedence: a held ticket with a merged PR, or long in a stage, gets no workflow
  prompt, only a note.
- Dry run of `pipeline` on the live data, compared by hand against the Jira board.

## 10. Rollout order

Two release units:

- **Unit A (one branch, one PR for the repo files):** the status vocabulary. `logbook.py` statuses, maps,
  `check`, tests and the migration command, together with the skill, command and
  `CLAUDE.md` text, the `CLAUDE/` template mirror and the workflow doc. They land together
  because the helper and the instructions must agree on the status words; there is no
  period in which the helper and the active text use different words.
- **Unit B (separate PR, after A):** the `pipeline` subcommand, its tests and its trigger
  prompts. It depends on the new words but can be reviewed and rolled back on its own.

The earlier gate (does a `dev` to `master` merge deploy?) is closed: the user confirmed it
does not.

The PR carries only repo files: the `CLAUDE/` mirror, docs and tests. The live `~/.claude`
edits are not in any PR; they are copied from the mirror to `~/.claude` at the moment of the
migration, after the backup in section 7 step 1.

After A is merged: run the read-only transition check (5.3), then the migration
(section 7) together with copying the helper and instructions into `~/.claude`, then
`check`, then `logbook.py sync`. Unit B adds `pipeline`; its first run is the dry run
against the live data.

## 11. Open points

None. Decisions confirmed by the user on 2026-10-15: a `master` merge does not deploy;
`Released` rows migrate as in section 7; `Data Development` is a real status; transitions
are forward-only; the colours of `DEPLOYMENT` and `PAT` are cosmetic and can be changed in
`STATUS_COLOR` later.
