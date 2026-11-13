# Classification rules

## Roles per repo

The branch model is not universal. `collect.py` detects roles per repo:

- `prod`: the target of `origin/HEAD`, else `master`, else `main`.
- `integration`: `dev`, else `develop`.
- `sit`: `sit` when present.

No `integration` role means integration checks fall back to `prod` ancestry and are reported as low confidence. Clones and worktrees of the same remote are collapsed (`duplicate_of`).

## Branch classes

Only branches the user owns are classified: a PR by the user (`gh pr list --author @me`), or a tip commit by the repo's `user.email`.

| Class | Meaning |
| --- | --- |
| `merged` | PR merged into integration or prod, or (no PR) ancestor of them. Hidden. |
| `no_unique_commits` | Nothing ahead of integration. Hidden. |
| `in_sit_only` | PR merged into `sit` only. Still in testing, not done. |
| `open_pr` | PR open. |
| `closed_unmerged` | PR closed without merge. Cancel candidate; ask. |
| `pushed_no_pr` | Pushed, never PR-ed. Often the forgotten pre-Claude work. |
| `local_only` | Never pushed. At risk of being lost. |

PR state wins over git ancestry because `dev` takes squash merges, which a plain "is it merged" git check cannot see. Ancestry is only the fallback when `gh` is missing or failed (`pr_source` not `gh`), and the report shows the confidence.

## Age bands

Age is days since the latest of the branch's last commit and its PR's last update.

- Ticket in a logbook testing stage (`other_court` in `~/.claude/logbook/config.json`): the logbook's `followup_days` (default 7/14/30) give `watch`, `chase`, `stalled`. The age used is the smaller of the branch age and the days since the last logbook row.
- Everything else: under 14 days `active`, 14 to 55 `stale`, 56 and more `stalled`.

`active` and `merged` rows are not shown as a to-do.

## Decisions

`state.json` (in the report folder) keeps the user's answer per `repo::branch`: `waiting`, `cancelled` or `unknown`, with a date and note. A decision does not hide the row; it shows the answer and its date. Re-ask when the branch class changes or the decision is older than the stalled threshold.

## Documentation drift

1. **Releases:** each of the latest first-parent commits on `prod` is a release (merge or squash alike). Flag a release from the last 90 days when `README.md` or `CLAUDE.md` is not in `git diff --name-only <release>^ <release>`.
2. **Branches ahead of integration:** flag when `README.md` or `CLAUDE.md` is not changed since the merge-base with integration. A branch is "ready for PR" when it has an open PR or a `release/<TICKET>/CHANGELOG.md`; a bump of the version line alone counts as an update.
3. **Version line:** `Version: x.y.z` (and optional `Updated: YYYY-MM-DD`) in both files. Flag a missing line, and a value that differs from `pyproject.toml` or `package.json`.
4. **Older than release:** the file's last commit date is before the latest release date.

No tags are needed: 18 of 20 surveyed repos had none, and deploy dates live in the CAB register, not in git.

## Not checked, never "none"

The report lists what could not be checked: no GitHub remote, `gh` failure, PR list at its limit, no integration branch, old fetch, repos not in the logbook `repo_paths`, non-git folders. Report these as "not checked".
