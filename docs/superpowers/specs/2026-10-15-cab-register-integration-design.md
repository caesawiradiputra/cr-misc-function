# CAB register integration for the logbook and the pipeline board

Date: 2026-10-15. Status: draft for review. Scope: `CLAUDE/skills/logbook/logbook.py`, its
tests, the logbook skill text and the `/pipeline` command, plus the `CLAUDE/` template mirror.
Builds on `2026-10-15-dev-workflow-design.md` (stage model, Jira wins on status).

## 1. Purpose

The deployment task list kept by the Ops team (the CAB register) holds the dates and outcomes
of stages 6 to 10 of the dev workflow: when a BAST was registered, when the CAB approved it,
when it was deployed, when the PAT window ends. Jira records the status but not those dates,
and the logbook records neither. The user keeps a copy of the register as a CSV and updates it
after each CAB session (Monday and Wednesday, ending 15:00).

Goals:

1. Use the register as the source of truth for **dates** (registered, CAB, planned and real
   deploy, PAT end), while Jira stays the source of truth for **status** (the user moves the
   ticket).
2. Catch forgotten and out-of-order steps: ready for release but not registered, deployed per
   the register but Jira behind, PAT window over but not `Done`.
3. Show CAB work in the weekly report ("CAB this week").

Not in scope: editing the register file, changing Jira or the logbook without the user's OK,
CAB items that cannot be tied to a DA ticket, non-company work.

## 2. Source file

- **Location.** `cab_register` in the logbook `config.json`. When absent, the default is
  `cab-register.csv` in the Windows logbook folder. Resolving the path must never exit the
  helper: `resolve_register_path(cfg)` returns `None` when no path is configured and the
  Windows folder cannot be resolved (today `windows_dir()` exits in that case, which would
  kill `pipeline`, `check` and `week`).
- **Reading.** Read-only, `newline=""`, header-driven. Encoding: try UTF-8 (BOM allowed), then
  cp1252 (Excel's "CSV (comma delimited)" on Windows); the encoding used is shown in the `cab`
  report. Delimiter: detected from the header line among `,`, `;` and tab (an Excel with an
  Indonesian locale writes `;`). CRLF and quoted line breaks inside headers are handled by the
  `csv` module. A short row is padded with empty cells; a fully blank row is skipped. Any
  `OSError`, `UnicodeDecodeError` or `csv.Error` turns the feature off for the run with one
  note naming the cause; the rest of the helper is unaffected.
- **Headers** are matched by normalised name (trim, collapse whitespace and line breaks, case-
  insensitive), so a header wrapped over two lines still matches. Required, because they are
  read: `Column 1` (the sheet's running number), `Status`, `Tanggal Register CAB`, `Nama CAB`,
  `jadwal CAB`, `Deployed Real Date`, `Last PAT Date`, `Status PAT`. Optional, shown when
  present: `TYPE CAB`, `Kategori`, `Deploye Plan Date`. Duplicate headers: the first wins and
  the duplicate is reported. A missing required column is reported by name and the feature is
  off for that run. A missing file turns the feature off with one note.

## 3. Parsing

- **Ticket keys.** Every distinct key matching `(?<![A-Za-z0-9])DA-?\s?(\d{3,5})(?!\d)` in
  `Nama CAB` (case-insensitive), so `DA1234`, `DA 1234` and `[BAST] DA-1234 - title` match and
  `da 12` inside a word does not. The same key repeated in one cell counts once. A row naming
  several keys is linked to each. A row without a key cannot be linked: it is counted (not
  listed) in the data quality report.
- **Which row is current.** `Column 1` is the only ordering used (never file order, never a
  date). A value is a valid number when it is an integer after trimming, optionally written
  with a trailing `.0`. The current row of a ticket is its row with the highest valid number.
  Rows with a blank or invalid number are history only. The ticket's state is **ambiguous**
  (reported; no register stage and no flags for it; history still listed) when two of its
  rows share the highest number, when none has a valid number, or when a lower-numbered row
  has a later CAB date or a later real deploy date than the highest-numbered one (the running
  number then does not follow time and the current row cannot be trusted). Every valid row
  stays in the history for the weekly block.
- **Dates, fixed column formats.** The register date (`Tanggal Register CAB`) is read as
  `M/D/YYYY`; every other date column (`jadwal CAB`, `Deploye Plan Date`, `Deployed Real
  Date`, `Last PAT Date`) is read as `D/M/YY` or `D/M/YYYY`, with a two-digit year meaning
  20YY. A cell that is not a valid date in its column's format is unknown and reported.
  `Closed Date` and `Deploy Plan Time` hold clock times (for example `17:00`) and are ignored.
  A `Deployed Real Date` after today (+07:00) is unknown and reported (a plan, not a fact).
- **The one mixed column.** Some register cells are typed `D/M` instead (for example
  `17/6/2026`, or `3/6/2026` meaning 3 June). Only that column gets a second reading:
  1. Read the cell in its primary format (`M/D`) and, when valid and different, in the swapped
     format (`D/M`). A cell whose day equals its month has one reading.
  2. A reading is plausible when it is on or before the row's CAB date and at most
     `cab_max_lag_days` before it (default 21; a larger configured value is clamped to 26).
  3. Primary plausible: use it. Primary not plausible but swapped plausible: use the swapped
     reading. Neither plausible: unknown, reported.
  4. No CAB date on the row: use the primary reading and mark it `unverified` (in the `cab`
     report and wherever it is printed in the weekly block); it feeds no calculation.
  The two readings of a day-month pair are at least 27 days apart (3 Feb and 2 Mar in a
  non-leap year), so with the window at 26 days or less both can never be plausible together
  and the choice is unique. No "smallest span" heuristic is used: being in order is necessary
  evidence, never proof.
- **Order check.** After parsing, `jadwal CAB` must not be before the register date, the
  planned deploy not before the CAB date, the real deploy not before the CAB date, and `Last
  PAT Date` not before the real deploy. A row that violates the order is reported and the later
  field is treated as unknown.

## 4. Status mapping

The register `Status` values are: `Register CAB`, `Done CAB And Progress Deployment`,
`Onprogress Deployment`, `Closed`, `Pending`, `CAB Ulang`, `OK tp Perlu Rekonfirm`,
`Rollback`, `Cancel`. `Closed` means the registered BAST is deployed, not that PAT is over.
`Status PAT` values seen: `Open`, `Closed`, `NA`, empty.

| Register `Status` (current row) | Stage the ticket is in | Expected Jira status |
| --- | --- | --- |
| `Register CAB`, `Pending`, `CAB Ulang`, `OK tp Perlu Rekonfirm` | waiting for CAB approval or a redo | `Ready For Release` |
| `Done CAB And Progress Deployment`, `Onprogress Deployment` | approved, deploying | `Deployment` |
| `Closed`, PAT not finished (section 5) | deployed, in PAT | `PAT` |
| `Closed`, PAT finished (confirmed or assumed, section 5) | PAT finished | `Done` |
| `Rollback` | deployment undone | `Data Development` or `Bug Fixing` (either is accepted) |
| `Cancel` | cancelled | `Cancel` |
| any other value | unknown | no expectation; reported |

Jira targets checked on 2026-10-15 against the live transition list of existing tickets:
`Data Development`, `Bug Fixing` and `Cancel` are all offered statuses. For `Rollback` the
destination depends on why it was rolled back, so the board never proposes one: it reports
"register says rolled back, Jira is the-status" when Jira is later in the flow. For `Cancel` it
proposes the Jira transition to `Cancel` (never applied without the user's OK). A cancelled
ticket leaves the board: the helper maps the Jira status `Cancel` to the page word `CANCELLED`
(neutral lozenge), the board skips it and `check` ignores it; the logbook gets no new status.

## 5. Precedence

1. **Dates: the register wins, but only when it is fresh and the value is known.** Otherwise
   the helper uses the `pat_since` already in the cache (from the Jira changelog); if neither
   exists the date is unknown and every decision that needs it is suppressed. A stale register
   never substitutes for missing Jira evidence, and the helper never writes register values
   into the cache. PAT fields:
   - **PAT start** = `Deployed Real Date` (unknown when blank; 7 closed rows in the current
     file have none). It is displayed and is not needed for the planned-end logic.
   - **PAT planned end** = `Last PAT Date`, confirmed by the user on 2026-10-15 as the planned
     date of the 7-day window (the data agrees: deploy date plus 7 days in 54 of 61 closed rows).
   - **PAT finished, confirmed** = `Status PAT` is `Closed`, or `NA` (not applicable; see open
     point). No date is needed.
   - **PAT finished, assumed** = the current row is `Closed`, the planned end is known and
     today (+07:00) is on or after it (the window is over on the end date itself), and there is
     no error signal. This is the user's rule: with no error or report, PAT is automatically
     assumed done; the date alone is the evidence, and `Status PAT` `Open` or blank does not
     block it.
   - **Error signals** (only what the helper can compute):
     - the current row's `Status` is `Rollback`, `CAB Ulang` or `Cancel`;
     - a logbook row with status `Fixing` for the ticket dated within the PAT window, from the
       deploy date (`Deployed Real Date`, else `Deploye Plan Date`) to the planned end, both
       inclusive. With no deploy date known only the first signal applies. A `Fixing` row after
       the planned end does not count, so an old fix cannot block the proposal forever.
   - **Missing evidence.** A blank or invalid `Last PAT Date` is no planned end and never
     makes PAT assumed done. When the register says nothing about PAT (no planned end and
     `Status PAT` not `Closed` or `NA`), or is behind Jira (for example the row is still
     `Onprogress Deployment` while Jira is `PAT`), the cached Jira-derived `pat_since` age logic
     applies instead, so the board never goes silent about a long-running PAT.
   - **What the board does.** A ticket with Jira `PAT` and PAT finished (confirmed or assumed)
     is listed in one batched block "PAT done: propose Done", each line showing the register's
     `Status PAT` value and the planned end. With an error signal it is listed as "PAT window
     ended but the-signal" and nothing is proposed. The Jira transition and the logbook row are
     written only after the user's OK (Jira changes are visible to others); the rule removes only
     the question whether PAT succeeded.
2. **Status: Jira wins.** A register stage that differs from the Jira status is reported with
   a suggested fix, never applied. Only the direction "register ahead of Jira" prompts on the
   board (deploys and Jira moves happen between sessions, so "Jira ahead of the register" is
   routine); the opposite appears in the `cab` report as information only.
3. **Staleness.** The register is fresh only if its modification time is at or after the end
   of the last CAB session (equal counts as fresh). `cab_sessions` in `config.json` (default
   Monday and Wednesday, end 15:00) are read in the fixed offset +07:00 (WIB, no daylight
   saving, so no timezone database is needed); the helper computes `now` in that offset and
   does not depend on the system time zone. When stale, all register-dependent flags are
   suppressed and the board and the weekly block print a banner naming the last session
   ("register not updated since the Wednesday 14 Oct session"). Off-schedule (emergency) CABs
   do not move the deadline; the user simply updates the file.

## 6. Components

### 6.0 Data flow and interfaces

- `resolve_register_path(cfg) -> Path | None` (never exits) and `load_register(path, cfg)
  -> Register`: rows, `by_ticket` (`current` row or `None`, `ambiguous` flag, `history`
  list), `problems` (strings), `unlinked` (count), `encoding`, `mtime` (aware datetime in
  +07:00). `None` when the feature is off.
- `last_session_end(now, sessions) -> datetime` and `register_fresh(register, now, sessions)
  -> bool`.
- `cab_info(register, ticket, fixing_dates, now) -> dict | None`: ISO dates, mapped stage,
  `planned_end`, `pat_confirmed`, `pat_assumed`, `error_signal`, `ambiguous`.
- `board_entry(..., cab: dict | None = None, cab_fresh: bool = False)` adds the CAB flags of
  6.2. `derive_board(cache, items, evidence, today, repo_paths=None, register=None, now=None)`
  loads `fixing_dates` from the logbook items and passes `cab_info` per ticket. `render_board`
  prints a CAB line per entry (CAB date, deploy, PAT end), the batched "PAT done" block at the
  top, and the stale banner. `cmd_week` prints the CAB block even when the logbook has no
  entries that week (today it returns early).
- `JIRA_STATUS["Cancel"] = "CANCELLED"` and `STATUS_COLOR["CANCELLED"] = "neutral"`; without
  this a Jira `Cancel` ticket would fall through to `TODO` on the board.

### 6.1 `logbook.py cab` (new, read-only)

Prints the per-ticket CAB view (current row, ISO dates, mapped stage, Jira status from the
cache, "Jira ahead" notes) and a data quality report: encoding and delimiter used, rows
without a ticket key (a count; `--show-unlinked` lists them), unparsable or backwards or
future dates, `unverified` dates, unknown statuses, ambiguous tickets, tickets with several
rows, and rows whose status contradicts their PAT field (for example `Onprogress Deployment`
with `Status PAT` `Closed`). `--ticket DA-n` shows one ticket with its history.

### 6.2 Pipeline board flags (live Jira, register fresh)

- **Not registered for CAB.** Jira `Ready For Release`, the ticket is a `DA-` key (the register links only those), the ticket
  has no register row, and the logbook shows it at `Ready For Release` for at least
  `cab_grace_days` (default 3, counted from the first row of the current run). Without a
  logbook `Ready For Release` row there is no flag. Registration is stage 7, after the status
  starts, hence the grace period; non-Jira work never gets this flag.
- **Register ahead of Jira.** The register stage is `Deployment`, `PAT` or `Done` and Jira is
  earlier (for example register `Closed`, Jira `Deployment`): "deployed per the register, move
  Jira to PAT".
- **PAT done / PAT window ended with a signal** as in section 5.
- **Rollback or Cancel** on a ticket whose Jira status is later in the flow.
- Each board line also shows the CAB date, deploy dates and PAT end when known.

### 6.3 `week` output: "CAB this week"

For the ISO week requested, from every valid register row (not only each ticket's current
one): items registered (`Tanggal Register CAB`), CAB sessions with their items (`jadwal CAB`),
items deployed (`Deployed Real Date`), and PAT windows ending that week (`Last PAT Date`,
only for rows whose status is `Closed`, so rollbacks, cancels and superseded rows are not
listed), each listed by ticket key. A ticket with a bugfix or emergency row appears once per
row. Unverified dates are marked. Weeks with nothing print nothing. Unlinked rows are counted.
When the register is stale the block starts with the stale banner.

### 6.4 `check`

Adds the "register ahead of Jira", PAT and Rollback or Cancel comparisons of 6.2 to its report
(same rules, same suppression when the register is stale).

## 7. Config

`config.json` gains optional `cab_register` (path), `cab_sessions`
(`{"days": ["Mon", "Wed"], "end": "15:00"}`), `cab_max_lag_days` (default 21, at most 26) and
`cab_grace_days` (default 3); the example config in `CLAUDE/` carries them with placeholders.
Absent keys use the defaults above, and so do malformed values (an empty `days` list, an `end`
that is not `HH:MM`, a non-numeric grace): a config typo never stops `pipeline`, `check` or `week`.

## 8. Error handling

- No register file, an unreadable file, or a missing required column: the feature is off for
  the run, one note is printed, and nothing else changes (section 2).
- A row that cannot be parsed is reported and skipped for that field only.
- The register is never modified; the CSV is opened read-only.

## 9. Testing

- File handling: empty file, header-only file, BOM, CRLF, quoted newlines in headers, `;` and
  tab delimiters, a cp1252 file, short rows, blank trailing rows, extra and duplicate columns,
  a missing required column, an unreadable path, a missing `windows_dir.txt` while `pipeline`,
  `check` and `week` run (they must not exit).
- Header normalisation: wrapped headers, case, extra whitespace.
- Ticket keys: `DA-1234`, `DA1234`, `DA 1234`, `[BAST] DA-1234 - x`, several keys, a repeated
  key, `da 12` inside a word, none.
- Date parsing: fixed column formats; the mixed register column (a typed `D/M` cell, a day
  over 12, a swap plausible only after the swap, neither reading plausible, no CAB date giving
  `unverified`, a cell whose day equals its month); two-digit years; a clock time in `Closed
  Date` is ignored; a future `Deployed Real Date` is unknown; an order violation making the
  later field unknown; the uniqueness property (two readings of any cell are at least 27 days
  apart; a 26-day window never accepts both; a configured value above 26 is clamped).
- Current row per ticket: highest numeric `Column 1`; out-of-order file rows; blank,
  non-numeric, padded and `32.0` numbers; a duplicate highest number or no valid number
  (ambiguous); a lower number with a later CAB or deploy date (ambiguous); history kept in all
  cases.
- Status mapping table including every `Status` value, `Closed` with each `Status PAT` value,
  and an unknown status; rows whose status contradicts their PAT field are reported.
- Precedence: register dates used only when fresh; stale register with no cached `pat_since`
  gives no PAT decision; a cached Jira-derived `pat_since` is used when the register is stale;
  Jira status wins in conflicts; "Jira ahead of the register" does not prompt on the board.
- PAT semantics: planned end reached with `Open`, blank, `Closed` and `NA` and no signal
  proposes `Done` (batched, showing `Status PAT`); the boundary day, the day before and the
  day after; a blank or invalid date never assumes done; `Status PAT` `Closed` or `NA` with no
  date is finished; each error signal alone withholds the proposal; a `Fixing` row inside the
  window blocks, one after the planned end does not; no deploy date known leaves only the
  status signals.
- `Rollback` accepts either Jira status and proposes none; `Cancel` proposes the Jira
  transition; a Jira `Cancel` ticket leaves the board; a missing intermediate date or an
  invalid date affects only its own field and the flags that need it.
- "Not registered" flag: fires after the grace period only for a Jira key at `Ready For
  Release` with a logbook run, not for a non-Jira ticket, not when the register is stale, not
  when a register row exists.
- Staleness: modification time before, exactly at, and after the last session end, for Monday
  and Wednesday sessions, a Friday and a weekend `now`; the +07:00 offset independent of the
  system time zone.
- Weekly block: a busy week, an empty week, a week with no logbook entries but CAB items, a
  ticket with two rows, a `Rollback` row not listed under PAT windows, unverified marker,
  stale banner.
- `cab` report content and `--show-unlinked`; board rendering with CAB lines and the batched
  block.
- Python 3.9 and 3.12 (`uv run --no-project --python X`).

## 10. Rollout

One unit: helper, tests, skill and command text, and the `CLAUDE/` mirror in one PR to `dev`.
No data migration. After the merge the live `~/.claude` files are updated (backup first), the
config gets `cab_register`, and the first `cab` and `pipeline` runs are checked by hand
against the register.

## 11. Open points

One to confirm with the user: `Status PAT` `NA` is treated as "PAT not applicable", which counts
as PAT finished (confirmed). If `NA` instead means PAT was skipped or unknown, it should count
like blank.

Confirmed by the user on 2026-10-15: `Closed` means deployed; the register owns dates and Jira
owns status; the file is left as is and parsed; the weekly "CAB this week" block is wanted;
`Last PAT Date` is the planned date and with no error or report PAT is assumed done at that date.
