---
name: logbook
description: Track what the user did, for weekly reporting. Adds or updates a row in the personal work logbook CSV (one row per ticket per day), prints a weekly summary, and copies the CSV to the Windows work folder. Use when the user says "/logbook", "log this", "add to my logbook", "catat ke logbook", "weekly report", "what did I do this week", "sync the logbook", or when a task finishes or a PR is opened or merged and a row should be proposed.
---

# Logbook

Personal tracking file used for weekly reporting.

- **Master file:** `~/.claude/logbook/logbook.csv` (WSL side).
- **Windows copy:** `/mnt/c/Users/<WINDOWS_USERNAME>/Documents/Work/Logbook/logbook.csv`.
  Copied only daily or when the user asks, never on every edit.
- **Helper:** `~/.claude/skills/logbook/logbook.py` (stdlib only, run with `python3`).
  Never hand-edit the CSV; use the helper so quoting and the ISO `week` stay correct.

Columns: `date, week, ticket, repo, branch, type, task, status, pr_url, notes`.

## Rules

1. **Propose, don't write silently.** When a task finishes or a PR opens or merges,
   show the row you would add (ticket, task, status) and write it after the
   user's OK. Write immediately only when the user asked for it.
2. **One row per ticket per day.** `add` upserts on `date` + `ticket`; non-empty
   fields overwrite, empty ones keep the old value. Without a ticket, use a
   short slug (e.g. `refactor-logging`) as `ticket`.
3. **Write `task` from the session**, one line, outcome-first (what changed and why),
   not a command log. `type` is `fea`, `fix`, `chore`, `docs`, `refactor` or `ops`.
4. **`status`** follows the work: `In progress`, `PR to dev`, `Merged to dev`,
   `PR to master`, `Released`, `Done`.
5. **Windows copy:** run `sync --daily` the first time the logbook is touched in a
   session (skips if already copied today) and `sync` when the user asks.

## Backfill from git and PRs (preferred source)

To fill a past period, read **commits and PRs, not session transcripts**: transcripts
are tens of MB per week and hold far more noise than signal. Per repo, run
`git log --all --since=<monday> --author="$(git config user.name)" --date=short
--format='%ad|%D|%s'` and, where `gh` works, `gh pr list --author @me --state all`.
Group by ticket key from the branch or subject (`bug-<n>` when there is no key).
Use the ticket's last-activity date, set `status` from merges (merged to `dev` /
`sit` / `master`), and mark tickets with no PR `In progress` with a note to verify.
Commits miss non-code work (meetings, investigations, Confluence pages, reviews),
so ask the user what to add.

## Commands

```bash
python3 ~/.claude/skills/logbook/logbook.py add --ticket PROJ-1234 --repo da-negative-list \
  --branch fea/PROJ-1234 --type fea --task "Added X so Y" --status "PR to dev" \
  --pr-url https://github.com/... --notes "optional"
python3 ~/.claude/skills/logbook/logbook.py week              # current ISO week
python3 ~/.claude/skills/logbook/logbook.py week --week 2026-W41
python3 ~/.claude/skills/logbook/logbook.py sync --daily      # skip if copied today
python3 ~/.claude/skills/logbook/logbook.py sync              # force copy
```

For Google Sheets: File → Import → Upload the Windows copy → "Append to current sheet".
