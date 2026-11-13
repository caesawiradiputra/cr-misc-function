---
name: umbrella-review
description: Review and remind. Run from an umbrella folder that holds one or several child git repos (or from a single repo) to see, per repo, what the last work was, which branches were never merged or tested (stalled, cancelled or forgotten), whether README.md and CLAUDE.md were updated for the last release or before a PR to dev, what is pending, and whether the repo has drifted from the standard templates. Read-only, never reads secrets or package folders, saves a dated report and keeps a workspace OKF bundle for knowledge that spans repos. Use whenever the user says "/umbrella-review", "what was I working on here", "what did I do last in these repos", "what is stalled", "which branches were never tested or merged", "are the docs up to date", "is README and CLAUDE.md current before the PR", "review this workspace", "remind me what is pending", "morning review of my repos", or comes back to an umbrella folder after days or weeks, even if they do not name the skill. A ticket board is `/pipeline`; template drift on one repo is `template-sync`.
---

# Umbrella review

The user hands work over for testing, and the testing sometimes never finishes (weeks, months, or it was cancelled and nobody said). Coming back later, they do not remember what the last work was, least of all work from before they used Claude (no changelog exists for it). This skill rebuilds that picture per repo and flags what needs a decision, so nothing sits forgotten.

It is a reviewer and a reminder, not an editor: it never changes a child repo and never fetches.

## How it stays safe

One script, `scripts/collect.py`, does all the reading. Claude reads its JSON, not the repos. This makes the rules mechanical instead of a promise:

- **git:** only an allow-listed set of sub-commands, never anything that prints file or diff content (`-p`, `show`, `stash show`). Only commit subjects, dates, branch names and file *names* leave git.
- **files:** only manifests and docs (`pyproject.toml`, `package.json`, `README.md`, `CLAUDE.md`, ...) are opened, and each open is listed in `files_opened`. `.env*`, keys, tokens, credentials and package folders (`node_modules`, `.venv`, `site-packages`, ...) are never opened. Dependencies come from the manifests and `uv.lock` presence, not from the installed packages.
- **no fetch:** remote state is what the last fetch left. The report says how old that is. Fetch only if the user asks, and ask before each fetch (the corporate proxy can be slow).
- **reports stay out of git:** `render.py` refuses to write inside a git work tree. Logbook data is never copied into any repo.

Details and the test that proves it: `references/safety.md`.

## Workflow

1. **Locate the umbrella.** Use the current folder when it holds git repos (or is one). Otherwise ask which folder.
2. **Collect** (seconds, no network except `gh pr list`):

   ```bash
   python3 ~/.claude/skills/umbrella-review/scripts/collect.py <umbrella> --out /tmp/umbrella-review.json
   ```

   Add `--with-templates` when the user wants best-practice drift too; it runs `template-sync check` per repo. Use the session scratchpad for the JSON when one is given.
3. **Render** the ranked report, save it, and update the state:

   ```bash
   python3 ~/.claude/skills/umbrella-review/scripts/render.py render /tmp/umbrella-review.json
   ```

   It prints the report and saves `<umbrella>/knowledge/reviews/YYYY-MM-DD.md` (or `~/.claude/umbrella-review/<name>/` when the umbrella is inside a git repo). Show the user the top of the report in chat in your own words: what is urgent, then the rest. Do not paste a wall of tables.
4. **Ask about each stalled item** (rows with Decision `ASK`): is it still waiting for the user's testing, cancelled, or unknown? Record each answer so the next run does not ask again:

   ```bash
   python3 ~/.claude/skills/umbrella-review/scripts/render.py decide <state-dir> <repo> <branch> waiting|cancelled|unknown "<note>"
   ```

   `<state-dir>` is the folder the report was saved in (printed as `saved:`, one level up from `reviews/`). Never decide for the user, and never delete or close a branch, PR or ticket from here. For a cancelled branch, offer the cleanup commands and let the user run them.
5. **Doc drift next.** For each branch about to go to `dev` (or a release just made) whose README or CLAUDE.md was not touched, offer to update them (version line, what changed). Do the edit only in the repo's own session, on the user's go-ahead; this skill does not edit.
6. **Last work for old repos.** When a repo has no changelog or release notes for its last work, summarise from the commit subjects and mark it "inferred from git history". Do not read diffs to improve the summary.
7. **Workspace bundle** (only when asked, or offer it once if `knowledge/` has no `index.md`). Use `okf-writer`. Start with one card per child repo (purpose, owner repo for shared things, branch roles, last release, where its docs are), then concepts that span repos (a shared table, a pipeline whose DAG and image live in two repos, a shared Connection). Facts only, `status: draft`; each fact must come from `README.md`, `CLAUDE.md`, a manifest or a release doc already read by the collector. Do not open code or DDL to widen the bundle without telling the user. Add one `log.md` line per review that points to the report.
8. **Propose a logbook row** only if the user did real work in the session (the global logbook rule); a review alone is not logged.

## Reading the report

Classes, age bands and doc-drift rules are in `references/classification.md`. The short version:

- `merged` is done and hidden. `in_sit_only` is still in testing, not done. `open_pr`, `pushed_no_pr` and `local_only` are open work. `closed_unmerged` is a cancel candidate.
- A branch whose ticket is in a testing stage in the logbook (Testing, Ready For Release, Deployment, PAT) uses the logbook's own follow-up days (default 7/14/30); other branches use 14 days (stale) and 56 days (stalled).
- Only the user's branches are listed (their PRs, or tip commits by their git email). Others are counted.
- A line under "Not checked or skipped" means the skill could not look, which is different from "nothing there". Say so that way.

## Version-line convention

The global `CLAUDE.md` asks every repo's `README.md` and `CLAUDE.md` to carry a line `Version: x.y.z · Updated: YYYY-MM-DD`. The report flags files without it, files that disagree with the manifest version, and files last edited before the latest release. If a repo has no such line yet, say it is a convention to adopt, not a failure of the repo.

## Boundaries

- Ticket board and next steps per ticket: `/pipeline`.
- Template drift for one repo, with fixes: `template-sync`.
- Standards audit of one repo: `python-standards-learn compare`.
- Writing the changelog and PR text: `/generate-pr-message`.
