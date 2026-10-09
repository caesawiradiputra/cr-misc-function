---
name: logbook
description: Track what the user did, for weekly reporting. Adds or updates a row in the personal work logbook CSV (one row per ticket per day), prints a weekly summary, and copies the CSV to the Windows work folder. Use when the user says "/logbook", "log this", "add to my logbook", "catat ke logbook", "weekly report", "what did I do this week", "sync the logbook", or when a task finishes or a PR is opened or merged and a row should be proposed.
---

# Logbook

Personal tracking file used for weekly reporting.

- **Master file:** `~/.claude/logbook/logbook.csv` (WSL side), plus `logbook-archive.csv`
  (old finished work) and `config.json` (Jira base URL, PIC, repo → project names,
  Confluence page ids) in the same folder.
- **Windows copy:** an export of the master, never edited by hand. Its folder comes from
  `LOGBOOK_WINDOWS_DIR`, or the first line of `~/.claude/logbook/windows_dir.txt`
  (e.g. `/mnt/c/Users/<you>/Documents/Work/Logbook`). `sync` fails with a clear
  message if neither is set, so create `windows_dir.txt` once per machine. `sync` creates
  the last folder but not missing parents (a missing parent is treated as a typo).
- **Helper:** `~/.claude/skills/logbook/logbook.py` (stdlib only, run with `python3`).
  Never hand-edit the CSV; use the helper so quoting, the ISO `week`, the header check
  and the atomic write stay correct. It refuses to write if the header or a row is malformed.

Columns: `date, ticket, repo, type, task, status, notes`. The week is derived from
`date` (ISO week), never stored; in Sheets use `=ISOWEEKNUM(A2)`.

`notes` is **not** a PR link or a progress log. It holds Jira context that differs
from or adds to the original ticket or requirement: a scope change, a decision and its
reason, a concern, or the outcome of a discussion. Leave it empty when there is
nothing like that, keep it to one or two sentences, and don't restate the requirement.

## Rules

1. **Propose, don't write silently.** When a reportable outcome occurs (a PR opens or
   merges, a ticket changes stage, a deliverable is finished), show the row you would
   add (ticket, task, status) and write it after the user's OK. Write immediately
   only when the user asked for it. Do not propose after minor intermediate steps, and
   if the ticket already has a row today, propose only a change that matters (new
   status or a materially different outcome).
2. **One row per ticket per day.** `add` upserts on `date` + `ticket`; non-empty
   fields overwrite, empty ones keep the old value. Without a ticket, use a
   short slug (e.g. `refactor-logging`) as `ticket`.
3. **Write `task` from the session**, one line, outcome-first (what changed and why),
   not a command log. `type` must be one of `fea`, `fix`, `chore`, `docs`, `refactor`,
   `ops`; the helper rejects anything else.
4. **`status`** must be one of the values below; the helper rejects anything else.

   | State | `status` |
   | --- | --- |
   | Work started, no PR yet | `In progress` |
   | PR open to `dev` | `PR to dev` |
   | PR merged into `dev` | `Merged to dev` |
   | PR merged into `sit` | `Merged to sit` |
   | PR open `dev` → `master` | `PR to master` |
   | Merged into `master` / deployed | `Released` |
   | Non-code work finished (docs, BAST, analysis) | `Done` |
   | Analysis / exploring, no code yet | `Analysis` |
   | Fixing a defect found after release or testing | `Fixing` |
   | Blocked or on hold | `Hold` |
5. **Windows copy:** `sync` copies the master and archive CSVs, each only when it differs
   from the Windows file, so it is safe to run often. Run it the first time the logbook is touched in
   a session and whenever the user asks, not after every edit.

## Archive and weekly Confluence page

The page layout follows the user's old "Weekly DA Interface" tracker: one row per
ticket (not per day), columns `#, Start Date, Project, To Do, Status, PIC, JIRA,
LastUpdate`. It is **generated** from the CSVs, only when the user asks (for the weekly
meeting), never after each edit. Manual edits on the page are overwritten, so tell the
user to change rows through the logbook instead.

How a ticket becomes a row: `Start Date` = the Jira **created date** (of the linked IN ticket when
there is one, else of the DA ticket; the first logbook date only when there is no Jira ticket),
`LastUpdate` = its last logbook date,
`Status` = the latest status mapped to the page words (`In progress` → `DEVELOPMENT`,
`PR to`/`Merged to dev`/`sit` → `TESTING`, `PR to master` → `READY FOR RELEASE`,
`Released`/`Done` → `DONE`, `Analysis` → `ANALYST`, plus `FIXING` and `HOLD`), `Project`
from `config.json` `projects` (repo name when unmapped). `To Do` is the latest `task` in
bold, followed by **collapsed expands** (`Description` first: a one or two sentence summary of the SRF/requirement) that keep rows compact (the same pattern as the
user's old tracker): `Task List` (only when the ticket has rows on several days: one dated
line per day) and `Update` (only when a row has `notes`: dated entries split by a divider).

Age highlighting follows **whose court the ball is in**, so it shows what to act on:
- **Your court** (`TODO`, `ANALYST`, `DEVELOPMENT`, `FIXING`): the `Start Date` cell is filled by how
  long the work has been open (today minus the start date): 30+ days light yellow `#FFFAE6`,
  60+ days yellow `#FFF0B3`, 90+ days dark red `#FF8F73` (`aging_days` in `config.json`).
- **Someone else's court** (`TESTING`, `READY FOR RELEASE`; `other_court` in `config.json`): the
  `LastUpdate` cell is filled by how long nothing has moved (today minus the last update), so it
  is clear when to follow up with the counterpart: 7+ days light yellow, 14+ yellow, 30+ dark red
  (`followup_days` in `config.json`).
- `DONE` and `HOLD` rows are never highlighted.

Assigned DA tickets with no logbook row are listed too, with the Jira title, the Jira
status mapped to the page words (`[BU] Todo`/`TODO` → `TODO`, `Data Analysis` → `ANALYST`, ...) and the
Jira updated date as `LastUpdate`.

Layout follows what the user set on the live page: no `#` column (Confluence's automatic
row numbers are on), fixed column widths, centered table, bold status lozenges, dates shown
as "October 5, 2026". If the user changes the layout on the page again, read the page's HTML
first and update `COL_WIDTHS` / `TABLE_OPEN` in `logbook.py` to match, or the next publish
resets it.

Publish procedure (run only when the user asks to publish / "update the weekly page"):

0a. **List the assigned DA tickets** (so work not started yet is tracked too). Run
   `searchJiraIssuesUsingJql` with `project = DA AND assignee = currentUser() AND statusCategory != Done`
   (fields `summary`, `status`, `created`, `updated`, `issuelinks`; `view: full`). Only DA tickets
   are listed: open IN/TDF tickets with no DA clone yet belong to `jira-in-da-sync`, and an IN/TDF
   ticket that already has a DA clone only supplies the `--source` key and start date. For each ticket
   run `cache set --track yes --ticket DA-n --summary ... --jira-status "<Jira status>" --updated
   <date> --project <name>` (plus `--created`/`--source`/`--description` as in step 0). Cached
   tickets that are no longer in the result (done, reassigned) get `cache set --track no`. A ticket
   with logbook rows keeps the logbook status; the Jira status only drives rows with no logbook row.
   Mention any ticket whose Jira status disagrees with its logbook status. For a ticket whose Jira
   status is `Hold`, read its changelog (`getJiraIssue` with `expand: changelog`, newest first) and
   record `--before-hold "<status it had before the latest move to Hold>" --hold-since <date of that
   move>` so the hold page can show what it was before it was paused.
0. **Refresh the Jira data** (`jira-cache.json`, never typed by hand). Run `cache missing`; for each
   listed Jira key fetch it with `searchJiraIssuesUsingJql` (`key in (...)`, fields `summary`,
   `created`, `issuelinks`, `description`, `view: full`). The linked ticket of type "Cloners" that
   starts with a different project (usually `IN-`) is the `--source`; `--created` is the created
   date of that IN ticket (fetch it too), or of the DA ticket when nothing is linked. Write the
   `--description` yourself in 1-2 sentences: what the SRF asks for and why, not a copy of the
   ticket, in English. Save with `cache set --ticket ... --created ... --source ... --description ...`.
   For work with no Jira ticket (`bug-<n>`, slugs), write the description from commit bodies and
   leave out `--created`. Existing entries are reused; refresh one only if the user says the Jira
   text changed. For logged tickets the page status comes from the logbook; only rows with no logbook row use the mapped Jira status (step 0a).
1. `archive --dry-run` and show the tickets (finished and idle for more than 7 days: last
   logbook date, or for Jira-only tickets the Jira updated date once Jira shows them done). After
   the user's OK, `archive` moves them to `logbook-archive.csv`. Unfinished work is never archived,
   however old.
2. `publish main --out <scratchpad>/main.html`, `publish hold --out <scratchpad>/hold.html`, and for
   each year that has archived work `publish archive --year <YYYY> --out <scratchpad>/archive-<YYYY>.html`
   (HTML only; the helper never talks to Confluence). Every page is ordered by project (A-Z),
   then most recently updated first.
3. Pages live in the user's personal space, in the `Logbook` folder: the main page
   `Weekly DA Interface` (active work, no `HOLD`), and under it two kinds of **child** page:
   `Weekly DA Interface - On Hold` (paused tickets, with an extra `Before Hold` column showing the
   status before the hold and the date it began) and one `Weekly DA Interface - Archived - <YYYY>` per
   year (children follow their parent if the page is copied or the user changes team). Ids are in
   `config.json` under `confluence` (`main_page_id`, `hold_page_id`, `archive_pages` keyed by year). Read the page's current version, then
   replace its body with the new HTML (`updateConfluenceContent`), and say the whole body
   is replaced. The HTML uses native elements (dates, status lozenges, a mention for the
   PIC, Jira smart-link cards), so the page looks like the user's old tracker.
4. **A new year with no archive page yet:** create it as a child of `main_page_id`
   (`createConfluenceContent` with `parent.parentContentId`), seeded from
   `publish archive --year <YYYY>`, and record its id in `archive_pages`. **A new tracker
   page** (another team, or a restart): copy the `Weekly DA Interface TEMPLATE` page
   (`weekly_template_page_id`, in the `Template` folder) with `copyConfluenceContent`, then
   publish into the copy. `publish main --empty` prints just the header table.
5. Read the page back to confirm the table rendered, report the links, and run `sync`.

## Backfill from git and PRs (preferred source)

To fill a past period, read **commits and PRs, not session transcripts**: transcripts
are tens of MB per week and hold far more noise than signal. Per repo, run
`git log --all --since=<monday> --author="$(git config user.name)" --date=short
--format='%ad|%D|%s'` and, where `gh` works, `gh pr list --author @me --state all`.
Group by ticket key from the branch or subject (`bug-<n>` when there is no key).
Use the ticket's last-activity date, set `status` from merges using the table above, and mark tickets with no PR `In progress`, telling the user in chat to verify them (not in `notes`).
**Where `notes` come from.** For tickets that have a `release/<TICKET>/` folder, read these
(they are already written, so this costs far less than a transcript), newest first:
`CHANGELOG.md` (summary, "Breaking Changes", "Code Review Notes", follow-up entries),
`docs/requirement.md` (dated "Requirement Update" and "Decision" sections, which record
requests that never reached Jira), and design docs with a "Decisions" table. Add a `notes`
entry only for something that differs from or adds to the original ticket: a new request
and its date, a decision and why, or a concern or known gap. Write it in one or two sentences
on the day it happened (use `add --date` so a ticket gets one row per day with its own note),
and skip anything the task line already says. Commit bodies are a second source when there
is no release folder. Show the proposed notes to the user before writing them.

Commits miss non-code work (meetings, investigations, Confluence pages, reviews),
so ask the user what to add.

## Commands

```bash
python3 ~/.claude/skills/logbook/logbook.py add --ticket PROJ-1234 --repo da-negative-list \
  --type fea --task "Added X so Y" --status "PR to dev" \
  --notes "Decided to keep the old key: downstream reports join on it"
python3 ~/.claude/skills/logbook/logbook.py rename <slug> PROJ-1234   # a slug that later got a Jira key (rows, archive, cache)
python3 ~/.claude/skills/logbook/logbook.py week              # current ISO week
python3 ~/.claude/skills/logbook/logbook.py week --week 2026-W41
python3 ~/.claude/skills/logbook/logbook.py sync              # copy CSVs if they changed
python3 ~/.claude/skills/logbook/logbook.py archive --dry-run # then without --dry-run
python3 ~/.claude/skills/logbook/logbook.py publish main --out /path/main.html
python3 ~/.claude/skills/logbook/logbook.py publish archive --out /path/archive.html
```

For Google Sheets: File → Import → Upload the Windows copy → "Append to current sheet".
