---
name: template-sync
description: Check whether the current repo applies the standard templates from the `cr-misc-function` repo (Docker image CI, Airflow DAG sync, ruff, mypy, VS Code settings and extensions) at their latest version, and bring stale or missing ones up to date while keeping the repo's own values. Use whenever the user says "/template-sync", "check the templates", "is this repo up to date with the templates", "does this repo use the latest docker workflow", "update the repo from the templates", "apply the standard config", "template drift", or starts a new repo and asks what standard files it needs, even if they do not name the skill.
---

# Template sync

`cr-misc-function` is the template source. `templates/manifest.json` lists every template with an integer `version`, its files and where each belongs in a repo. The primary file of each template carries a marker line, `# template: <id>@<version>` (`//` in JSON files), so a repo records which version it applied. This skill compares the repo with the registry and updates what is stale.

Helper: `python3 ~/.claude/skills/template-sync/scripts/template_sync.py` (stdlib only, Python 3.9 and newer). It reads the source from `--source`, then `TEMPLATE_SOURCE`, then `~/repo/cr-misc-function/cr-misc-function`. For workflow templates this skill defers to `github-actions-templates` (tag rules, hardening, `gh workflow run` test).

## Workflow

1. **Make "latest" real.** The helper prints the source branch and warns when it is not `dev`, `master` or `main`, or has uncommitted template changes. If the source may be behind, tell the user and ask before `git pull` in it (the network can be slow or blocked); do not fetch silently.
2. **Check.** `check <repo>` (from the repo, `.` works). Show the report as it is. Statuses:

   | Status | Meaning | Action |
   | --- | --- | --- |
   | `CURRENT` | Marker equals the latest version | None. A "N lines differ" note is normally the repo's own values |
   | `STALE` | Marker is older, or a companion file is missing or different | Update (below) |
   | `UNMARKED` | The file exists without a marker | "An older copy" (similar to the template): treat as stale. "A different file": ask before replacing |
   | `AHEAD` | Marker is newer than the source | The source checkout is old; update it first |
   | `NOT-APPLIED` | No such file | Do nothing unless the repo needs it; offer to add it |

3. **Plan before editing.** For each template that needs attention run `diff <id> <repo>` and the template's standard (`standard` in `list`) and sort the differences into: *template changes the repo should take* (new steps, hardening, renamed secrets), and *repo values to keep* (image name, port, health path, DAG names, `target-version`, paths). Show the plan and wait for the user's go-ahead on anything that changes behaviour (tags, secrets, triggers).
4. **Update one template at a time.** Edit the repo file toward the template, keeping the repo's values. Never copy the template over the file blindly. List the new secrets, variables or prerequisites the new version needs (read them from the template's header and the standard), but never write a secret value. Then run `stamp <id> <repo>`, which writes only the marker line.
5. **Verify.** Run `check --only <id>` again (it must say `CURRENT`), then the repo's own checks (`ruff`, `mypy`, `pytest`) for config templates. For a workflow, follow `github-actions-templates` step 6 (test from the work branch with `gh workflow run`); say plainly if it was not run.
6. **Report.** Per template: status before and after, what was taken from the template, what was kept, anything still to do (secrets to create, test run). Commit only when the user asks, on the current branch.

## Rules

- Read-only until the user agrees to a change; `check`, `diff` and `list` never write.
- `stamp` is run only after the file really matches the template's version. A stamp on a file that was not updated hides drift.
- Keep the repo's own values; the template's `TODO` and placeholder lines are never copied as values.
- Do not touch `legacy/**`, `.env*`, `token.json` or `settings.local.json`.
- Company data (registry names, hosts, tokens) stays in the target repo, never in the template or in this skill.

## Maintaining the registry (in `cr-misc-function`)

- A change to a template file needs a version bump: `bump <id>` raises `version`, rewrites the marker and recomputes the digest in `templates/manifest.json`. `verify` (and `tests/test_template_sync.py`) fail when a template changed without a bump, so a repo is never told it is current when the template moved.
- Put the reason for the bump in the commit message. Template fixes land in `cr-misc-function` on their own PR before they are applied to repos.
- A new template: add its entry to `manifest.json` with `"version": 0` and `"marker": true` on exactly one file, then `bump <id> --force`.
- Machine setup (winget, WSL, conda) and AI-assistant config are not per-repo and are not in the registry.
