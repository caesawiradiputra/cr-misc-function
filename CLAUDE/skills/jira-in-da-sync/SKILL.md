---
name: jira-in-da-sync
description: Daily JIRA intake check for the Data Analytics engineer. Scans the tickets assigned to the user on the source boards (IN, the Initiation board, plus other boards such as OTHER whose tickets are scanned in every status) that have no linked PROJ ticket yet, and clones each into a PROJ ticket linked back as Cloners, but only lists tickets older than 6 months for the user to decide on. Remembers a checkpoint per board (the highest ticket number already checked) so later runs skip tickets it has already looked at. Then lists the user's open PROJ tickets still sitting in Backlog / To Do / Data Analysis so they can decide to update the status or resume development. Use whenever the user says "check my IN tickets", "any new IN assigned to me", "scan OTHER too", "clone the new IN to PROJ", "sync IN and PROJ", "morning JIRA check", "what is still in backlog / todo / data analysis", "remind me which tickets are waiting", "cek IN baru", "ada IN yang belum di-clone", or asks for a JIRA status round-up, even if they do not name both boards.
---

# JIRA source boards → PROJ sync and PROJ reminders

Work reaches the engineer on several boards: requesters file SRFs on the Initiation board (`IN`), and other teams file work on their own boards (for example `OTHER`). The engineer works from a clone on the working board (`PROJ`). Nothing creates that clone automatically, so an assigned ticket on a source board can sit unnoticed. This skill does a routine sweep in two parts:

1. **Intake**: for each source board, find tickets assigned to the user with no `PROJ` link, clone the recent ones, and only *list* the old ones.
2. **Reminders**: list the user's open `PROJ` tickets that are waiting at the start of the pipeline, so they can decide whether to move the status or resume the work.

Running twice in a day is harmless: a ticket that already has a `PROJ` link is never cloned again.

## Settings

### Source boards

Each board has its own rules, because the boards are used differently:

| Board | Statuses scanned | Number floor | `PROJ` summary | Type mapping |
| --- | --- | --- | --- | --- |
| `IN` | every status except `Cancel` | `IN-3000` | `SRF - ` + the IN title | `Change Request` → `Task` |
| `OTHER` | **every status**, including Done and Cancel | none | the title unchanged | `Story` → `Task` |

- **Why `IN` skips only `Cancel` and not by category:** `MOVE TO DA`, the status that hands a request to the data team, is a *Done*-category status, so `statusCategory != Done` hides exactly the tickets this skill exists for.
- **Why `OTHER` takes every status:** the user wants all work on that board tracked on `PROJ`, including tickets already finished. A finished ticket still gets its clone; see Step 4.
- **A board that is not in the table** (the user says "also scan XYZ"): use the defaults of `OTHER` (every status, no floor, title unchanged, other types → `Task`). Treat its first scan as a baseline, and offer to add a row to this table so it is scanned every time.
- `PROJ` accepts the types Epic, Task, Sub-task and Bug. Map `Bug` to `Bug` and `Epic` to `Epic`; everything else to `Task`.

### General

| Setting | Value | Why |
| --- | --- | --- |
| `cloudId` | `"<ATLASSIAN_SITE>.atlassian.net"` | Site hostname; try directly, only call `getAccessibleAtlassianResources` if it fails |
| Age cutoff | 6 months, measured on `created`, all boards | An old request may be obsolete or handled elsewhere, so a person decides; the user can name another cutoff |
| Confirmation threshold | more than 5 tickets to clone in one run | A sudden large batch is more likely a filter mistake than real intake, so show the list and ask first |
| Reminder statuses | name matches `backlog`, `to do` / `todo` / `to-do`, or `data analy` (case-insensitive) | The board uses names like `[BU] Todo` and `Data Analysis`, so match by pattern, not exact name |
| Idle flag | not updated for 14 days | A ticket waiting that long is the one most likely to be forgotten |
| State file | `~/.claude/state/jira-in-da-sync.json` | Remembers the checkpoints between runs (see Step 0) |

Start by noting today's date and computing the cutoff date (today minus 6 months). Say the exact date in the report so the user can check the boundary.

## Part 1: Intake

Run Steps 0 to 5 once per source board, then print one combined report. In the steps below, `SRC` is the board being scanned and `N` is a ticket number (the digits of its key).

### Step 0: Load the checkpoints

Checking whether a source ticket has a clone costs one `getJiraIssue` call per ticket, because only that call exposes links. To avoid repeating that work, keep a checkpoint per board: the highest ticket number already examined.

Read the state file (create `~/.claude/state/` if needed). Its shape:

```json
{
  "checked_at": "2026-10-07",
  "projects": {"IN": {"checkpoint": 3324}, "OTHER": {"checkpoint": 4858}},
  "pending": [{"key": "IN-1234", "summary": "...", "created": "2025-02-24", "note": "no PROJ ticket found"}],
  "retry": []
}
```

- **A board with no entry** (first scan of it), or the user says "re-check everything" / "ignore the checkpoint": do a baseline for that board. Look at every ticket assigned to the user (from its floor up), including ones older than the age cutoff, because those are the ones listed for the user's decision. The user may instead paste a list of keys to check; use it as the candidate set.
- **A board with a checkpoint**: only look at what is new since it (Step 1). `pending` holds tickets already listed and still waiting for the user's decision; `retry` holds tickets whose clone only half-succeeded last time.
- **Re-check `pending` once a day.** When `checked_at` is earlier than today, fetch each pending ticket once (`view: "evidence"`) before scanning for new ones. If it now has a `PROJ` link (the user made or linked one by hand), or its status became `Cancel`, drop it from `pending` and report it under `Resolved since last run` with the reason. A rerun on the same day skips this, since nothing is likely to have changed, and so does a dry run. This keeps `pending` from filling up with tickets that were already dealt with.
- An older state file with a flat top-level `checkpoint` and no `projects` belongs to `IN`; read it as `projects.IN.checkpoint`, and write the new shape back.
- The user can say "reset the IN checkpoint to 3000" to move one; write the new value.

### Step 1: Find candidate tickets

`searchJiraIssuesUsingJql` with `fields: ["summary", "status", "created", "issuetype"]`, `view: "compact"`, `maxResults: 100` (page with `nextPageToken` until `isLast`).

Build the JQL from the board's row in Settings:

- Base: `project = "SRC" AND assignee = currentUser()`, then `AND key >= "SRC-<floor>"` if the board has a floor, then the status rule (`AND status != "Cancel"` for `IN`; nothing for a board that takes every status), `ORDER BY created ASC`.
- With a checkpoint N, add `AND (key > "SRC-N" OR assignee CHANGED TO currentUser() AFTER -Wd)` before the `ORDER BY`, where W is the days since `checked_at` plus 2, at least 7.

Why both clauses: `key > SRC-N` catches everything created since the last run. A ticket with a *lower* number can still be reassigned to the user later, and only the `CHANGED` clause sees that. Tickets created already assigned to the user have no assignee change, but the key clause covers them when they are created. The floor clause stays on every query.

Always quote the project key: `IN` is a reserved word in JQL and an unquoted `project = IN` fails with a 400. The compact view does not return `updated` or links, so do not rely on it for those.

### Step 2: Drop the ones that already have a PROJ link

The search cannot return links, so call `getJiraIssue` once per candidate, plus each ticket in `retry`, with `view: "evidence"` and read `fields.issuelinks`. The evidence view is far lighter than `view: "full"` (no comment bodies, attachments or worklogs) and still returns `issuelinks`, `updated`, the status with its category, and the description. A few tickets with inline images are still huge (tens of KB); when the tool saves such a response to a file, read only `fields.issuelinks`, `status` and `created` from it with a short script instead of loading it.

- **Already linked** if any link, of any type, points to a `PROJ-\d+` key. Accept any link type: a ticket linked as "relates to" was still picked up by someone. A ticket with two `PROJ` clones is linked too; mention the second one as a likely accidental duplicate.
- **Clone of another source ticket**: if the only links are `Cloners` to another ticket on the same board (this ticket "clones" `SRC-n`), read that ticket's links. If it has a `PROJ` link, report this ticket as `duplicate of SRC-n (PROJ-x)` and do not clone it.
- Otherwise it is **unlinked**. Never print descriptions in the report.

### Step 3: Check for a ticket that exists without a link, then split by age

People sometimes create the `PROJ` ticket by hand and never link it, and cloning on top of that makes a duplicate. For each unlinked ticket, search `PROJ` before cloning: `project = "PROJ" AND created >= "<source created date>" AND (summary ~ "<distinctive word>" OR ...)`, using words that identify the request (a table or variable name, a `CDS-nnn` id, a product term), not generic ones like "enhancement". Also compare against the other unlinked tickets: two tickets with the same description are probably one request.

- A plausible match: do not clone. List it as `possible existing PROJ-x` with its summary and status, and let the user say "link it" (then create the `Cloners` link as in Step 4.3) or "clone anyway".
- No match: continue.

Then split by age:

- `created` on or after the cutoff: **clone** (Step 4).
- `created` before the cutoff: **stale**. Do not clone. Report key, summary, status, created date, age in months, `updated` date and any link hint to another source ticket (for example "relates to IN-9, Cancel"), and ask which to clone. Add it to `pending` in the state. When the user picks some, run Step 4 on those and remove them from `pending`; if they say to skip one, remove it from `pending` so it stops appearing.

The cutoff uses `created` because that is when the request entered the queue. `updated` is shown because an old ticket with recent activity is probably still live.

### Step 4: Clone

Show the list and ask before creating anything when more than the confirmation threshold qualify, **and always on a baseline run**: a baseline reaches back through history, where a missing link may be a deliberate choice (a request folded into another ticket, a duplicate) that only the user knows. On a normal run with a checkpoint and few tickets, create them straight away: the user asked for this.

For each ticket, in order:

1. **Create** with `createJiraIssue`, `projectKey: "PROJ"`:
   - `summary`: from the board's row in Settings. For `IN` that is `SRF - ` + the title with surrounding whitespace trimmed (do not add a second prefix if it already starts with `SRF -`); for a board with an unchanged title, the title as is. No `CLONE - ` prefix.
   - `issueType`: from the board's type mapping. Ask only if the type is truly ambiguous.
   - `description`: the source description **as HTML** with `contentFormat: "html"`, because descriptions are often tables and Markdown flattens them (a description fetched as Markdown can be written back as Markdown). End with `<p>Cloned from <a href="https://<ATLASSIAN_SITE>.atlassian.net/browse/SRC-1234">SRC-1234</a></p>` using the real key. Every ticket key written into a ticket is a link, never a bare key.
   - `priority` and `labels`: copy when `PROJ` accepts them; drop and mention any that are rejected.
   - Do not copy attachments. This MCP cannot download attachment bytes, so list the filenames on the source ticket and tell the user to re-attach them by hand if the team wants them on the `PROJ` ticket. The evidence view does not list attachments, so fetch this one ticket with `view: "full"` just to read the `attachment` filenames.
2. **Assign** with `editJiraIssue` `fields: {"assignee": {"accountId": "<current user>"}}`. `createJiraIssue` silently ignores its `assignee` argument, so this second call is required. Get the id once from `atlassianUserInfo`.
3. **Link** back. Call `listJiraIssueLinkTypes` once per run to confirm the name (`Cloners`, "clones" / "is cloned by"), then `createJiraIssueLink` through `executeWrite` with `inwardIssue` = the new `PROJ` key and `outwardIssue` = the source key, so it reads "PROJ-xxxx clones SRC-xxxx".

If the source ticket is already Done or Cancelled, it still gets its clone (that is the point of scanning every status), but the clone starts in the board's default status. Do not move it yourself: say in the report that the clone is for finished work and ask whether to move it to Done.

If step 2 or 3 fails after step 1 succeeded, the clone already exists. Report the new key, retry only the failed step, and never create a second ticket to recover. If the link could not be made, the next run would see an unlinked source ticket and clone it again, so put the key in `retry` in the state and call the gap out loudly in the report.

### Step 5: Save the checkpoint

After the run, write the state file: for each board scanned, `projects.<board>.checkpoint` = the highest ticket number among every ticket examined (linked, cloned and stale alike), `checked_at` = today, `pending` = the tickets still awaiting a decision, `retry` = tickets with an unfinished clone. Always write it, even when nothing was cloned, so the next run stays cheap. If the user asked for a dry run or "don't save", leave the file alone and say so.

## Part 2: PROJ reminders

1. `searchJiraIssuesUsingJql` with `jql`: `project = "PROJ" AND assignee = currentUser() AND statusCategory != Done ORDER BY status ASC, created ASC`, `fields: ["summary", "status", "created", "issuetype"]`, `view: "compact"`. Keep the tickets whose status name matches the reminder patterns in Settings. The tickets just cloned in Part 1 will match too: mark them `new`.
2. To find idle tickets, run the same query again for just the matched status names, adding `AND updated <= -14d`. (The compact view does not return `updated`, so the date filter is how idleness is read.) Mark those tickets `IDLE`.
3. Group by status name. Print the exact status names that matched, then one line counting the other open statuses (for example `Not shown: Hold 9, Testing 5, Data Development 4`). This is how the user spots a status that should have been included but did not match.
4. For each group, ask the question the user needs to answer. For `Backlog` / `To Do`: *start it or leave it?* For `Data Analysis`: *is the analysis done so the status can move on, or is it still being worked?* Do not change any status. If the user says which ticket to move, read the available transitions first (names differ per board), then use `transitionJiraIssue`.

## Report

Print the `pending` list as a count plus the keys, not as a full table: it repeats on every run until the user decides, and a long list drowns the new findings. Give titles, dates and notes only when there are three items or fewer, or when the user asks ("show pending"). New findings and anything resolved always get full detail.

Use this order, with one intake block per board, and for an empty section say so in one line instead of dropping it, so silence is never ambiguous:

```text
IN → PROJ intake (floor: IN-3000; age cutoff: <date>; checkpoint: IN-<n> → IN-<m>)
  Cloned: IN-1 → PROJ-10 "SRF - <title>" (Task, <IN status>) — attachments to re-add: <names or none>
  Stale, not cloned (older than 6 months):
    IN-2  "<title>"  created 2025-02-24 (19 mo)  updated 2025-02-28  status Hold  relates to IN-9 (Cancel)
  Possible existing PROJ ticket (not cloned): IN-4 "<title>" ~ PROJ-30 "<title>" (PAT)
  Duplicate of another IN: IN-5 → IN-6 (PROJ-31)
  Resolved since last run: IN-8 now linked to PROJ-40
  Still waiting for your decision: 11 (IN-3, IN-4, ...) — say "show pending" for titles and notes
  Already linked: <n> ticket(s)

OTHER → PROJ intake (all statuses; checkpoint: OTHER-<n> → OTHER-<m>)
  Cloned: OTHER-7 → PROJ-11 "<title>" (Task, was Done — clone is open, move it?)
  ...

PROJ reminders
  [BU] Todo (3)
    PROJ-11  "<title>"  Task  created 2026-09-25  new
    PROJ-12  "<title>"  Epic  created 2026-08-01  IDLE
  Data Analysis (1)
    ...
  Matched statuses: [BU] Todo, Data Analysis. Not shown: Hold 9, Testing 5, ...
  → start/leave the To Do ones? is the Data Analysis one ready to move on?
```

Ticket keys are Markdown links (`[PROJ-11](https://<ATLASSIAN_SITE>.atlassian.net/browse/PROJ-11)`) in the final message, never bare.

### Saving the report

Only when the user asks. Keep one tracker file per month and update its tables in place, so the month reads as the current picture plus a short log, not a pile of per-run reports.

- Path: `/mnt/c/Users/<WINDOWS_USERNAME>/Documents/Work/Jira Intake/<YYYY-MM> intake.md` (native Windows: `C:\Users\<WINDOWS_USERNAME>\Documents\Work\Jira Intake\<YYYY-MM> intake.md`), for example `2026-10 intake.md`. Create the folder if it is missing.
- Read the existing file first and match rows by **ticket key**, so a rerun updates a row instead of duplicating it.
- If the month's file does not exist, create it with the title `# Jira intake — <YYYY-MM>`, a short note that the tables are updated in place, and the five tables below. At a month rollover, copy the rows still `Open` from the previous month's file into the new one, keeping their `First seen`.
- The tables:
  - `Run log`: **append** one row per run: date, run kind (`baseline`, `run`, `run 2` for a second run on the same day), boards, number examined, cloned, resolved by hand, and open after the run.
  - `Needs a decision / decided`: one row per source ticket that was not already linked: ticket, board, title, created, status at scan, finding, `Decision` (`Open`, `Cloned`, `Linked` or `Skipped`), DA ticket, first seen, last update. **Add** a row for each new finding. **Update the row in place** when something changes: set `Decision`, the DA ticket and `Last update` when the user decides or the pending re-check finds a link, and refresh the status and finding if they changed. Never delete a decided row; it is the record of what happened.
  - `Already linked`: **append** a row for each newly examined ticket that already had a DA ticket (source ticket, DA ticket or tickets, first seen).
  - `DA reminders`: **replace** with the latest snapshot and an "as of" date, since it describes the current state, not history. Include the questions to answer and the count of other open statuses.
  - `Notes`: **append** dated one-liners for observations such as a double clone.
- Every ticket key is a Markdown link.
- Keep the file outside any repo: it names real tickets and titles, and the repo that holds this skill is public. The per-domain folders `Work/<Domain>/Jira/` hold one ticket each, while this tracker spans domains and boards, so it has its own `Jira Intake` folder.

## Verified behaviour on this site

Checked against the live tools (2026-10-07). Trust these over assumptions, and re-verify if a call behaves differently.

- `project = IN` unquoted → 400 (reserved word). Quote it.
- Search results (any `view`, with or without `fields`) never include `issuelinks`. `getJiraIssue` returns it with `view: "evidence"` (light) or `"full"` (heavy); `fields`, `fieldsByKeys` and `responseFields` on `getJiraIssue` drop it. The compact search view also omits `updated`.
- IN status `MOVE TO DA` has status category Done; `Cancel` is Done too; `Hold` and the revision status are In Progress. Filtering on category alone drops the whole `MOVE TO DA` set.
- An existing clone shows on the source ticket as `issuelinks[].inwardIssue` = the `PROJ` ticket, link type `Cloners`, inward text "is cloned by".
- `key >= "IN-3000"`, `key > "IN-N"` and `assignee CHANGED TO currentUser() AFTER -Nd` all work in JQL, including combined with `AND` / `OR`. A ticket created already assigned to the user has no `CHANGED` event.
- The `OTHER` board uses the statuses `TODO`, `In Progress` and `Done` and the type `Story`; `PROJ` has no `Story` type.
- `createJiraIssue` takes `issueType` (not `issueTypeName`) and ignores `assignee`.
- IN descriptions come back as HTML; write them back with `contentFormat: "html"`.

## Checklist before finishing

- [ ] State file read first; baseline done only for a board with no checkpoint or when the user asked; the old flat-checkpoint shape migrated to `projects.IN`
- [ ] Project keys quoted in JQL; floor clause on every query for a board that has one; compact view used for the scan; checkpoint query used the `OR assignee CHANGED` clause
- [ ] `IN` skips only `Cancel`; a board that takes every status has no status filter at all; no `statusCategory` filter on any source scan
- [ ] Links fetched per candidate with `view: "evidence"`; any `PROJ-` link of any type counted as linked; clone-of-source-ticket checked against the original
- [ ] Each unlinked ticket searched for an existing hand-made `PROJ` ticket before cloning; baseline run asked first
- [ ] Cutoff date stated; stale tickets listed (and kept in `pending`), not cloned
- [ ] Per-board summary prefix and type mapping applied; a clone of a Done source ticket reported as such, not moved
- [ ] No second clone created for any ticket; partial failures reported with the new key and kept in `retry`
- [ ] Every clone assigned to the user and linked as Cloners, or the gap called out
- [ ] Pending items re-checked for a new link at most once per day (skipped on a same-day rerun); pending printed as a count plus keys
- [ ] Checkpoint saved for each board scanned (or the user asked not to)
- [ ] If a report was saved: the month's tables updated in place by ticket key (one run-log row appended, decided rows kept, reminders replaced), not a new section per run
- [ ] Reminder section printed matched status names and the count of other open statuses; no status changed without the user saying so
