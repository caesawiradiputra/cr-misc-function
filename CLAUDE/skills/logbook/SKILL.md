---
name: logbook
description: Track what the user did, for weekly reporting. Adds or updates a row in the personal work logbook CSV (one row per ticket per day), prints a weekly summary, and copies the CSV to the Windows work folder. Use when the user says "/logbook", "log this", "add to my logbook", "catat ke logbook", "weekly report", "what did I do this week", "sync the logbook", or when a task finishes or a PR is opened or merged and a row should be proposed.
---

# Logbook

Personal tracking file used for weekly reporting.

- **Master file:** `~/.claude/logbook/logbook.csv` (WSL side).
- **Windows copy:** an export of the master, never edited by hand. Its folder comes from
  `LOGBOOK_WINDOWS_DIR`, or the first line of `~/.claude/logbook/windows_dir.txt`
  (e.g. `/mnt/c/Users/<you>/Documents/Work/Logbook`). `sync` fails with a clear
  message if neither is set, so create `windows_dir.txt` once per machine. `sync` creates
  the last folder but not missing parents (a missing parent is treated as a typo).
- **Helper:** `~/.claude/skills/logbook/logbook.py` (stdlib only, run with `python3`).
  Never hand-edit the CSV; use the helper so quoting, the ISO `week`, the header check
  and the atomic write stay correct. It refuses to write if the header or a row is malformed.

Columns: `date, week, ticket, repo, branch, type, task, status, pr_url, notes`.

## Rules

1. **Propose, don't write silently.** When a reportable outcome occurs (a PR opens or
   merges, a ticket changes stage, a deliverable is finished), show the row you would
   add (ticket, task, status) and write it after the user's OK. Write immediately
   only when the user asked for it. Do not propose after minor intermediate steps, and
   if the ticket already has a row today, propose only a change that matters (new
   status, PR link, a materially different outcome).
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
5. **Windows copy:** `sync` copies only when the master differs from the Windows
   file, so it is safe to run often. Run it the first time the logbook is touched in
   a session and whenever the user asks, not after every edit.

## Backfill from git and PRs (preferred source)

To fill a past period, read **commits and PRs, not session transcripts**: transcripts
are tens of MB per week and hold far more noise than signal. Per repo, run
`git log --all --since=<monday> --author="$(git config user.name)" --date=short
--format='%ad|%D|%s'` and, where `gh` works, `gh pr list --author @me --state all`.
Group by ticket key from the branch or subject (`bug-<n>` when there is no key).
Use the ticket's last-activity date, set `status` from merges using the table above, and mark tickets with no PR `In progress` with a note to verify.
Commits miss non-code work (meetings, investigations, Confluence pages, reviews),
so ask the user what to add.

## Commands

```bash
python3 ~/.claude/skills/logbook/logbook.py add --ticket PROJ-1234 --repo da-negative-list \
  --branch fea/PROJ-1234 --type fea --task "Added X so Y" --status "PR to dev" \
  --pr-url https://github.com/... --notes "optional"
python3 ~/.claude/skills/logbook/logbook.py week              # current ISO week
python3 ~/.claude/skills/logbook/logbook.py week --week 2026-W41
python3 ~/.claude/skills/logbook/logbook.py sync              # copy if the master changed
```

For Google Sheets: File → Import → Upload the Windows copy → "Append to current sheet".
