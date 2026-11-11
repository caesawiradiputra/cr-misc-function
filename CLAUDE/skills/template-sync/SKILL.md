---
name: template-sync
description: Check whether the current repo applies the standard templates (Docker image CI, Airflow DAG sync, ruff, mypy, VS Code, and the Python scaffold: config.py, log_config.py, folder layout) at their latest version, and bring stale or missing ones up to date while keeping the repo's own values. Differences the repo keeps on purpose are recorded and shown as deliberate. Use whenever the user says "/template-sync", "check the templates", "is this repo up to date with the templates", "does this repo use the latest docker workflow", "update the repo from the templates", "apply the standard config", "template drift", or starts a new repo and asks what standard files it needs, even if they do not name the skill.
---

# Template sync

Four repositories are template sources, each with its own manifest:

- `cr-misc-function`: `templates/manifest.json` (Docker image CI, Airflow DAG sync, `ruff.toml`, `mypy.ini`, VS Code files).
- `da-template-airflow-dags`: `template-docs/template-manifest.json`. **The source of truth for an Airflow DAG repo** (the sync workflow and scripts, the template-managed `common/` modules, CI, the Variable check and docs test, and the `airflow-dags-layout` list). It declares `repo_kind: airflow-dags`, `overrides` (`airflow-dag-sync`) and `excludes` (templates that make no sense in a DAG-only repo: Docker image CI, the Python layout, config and logging templates).
- `da-template-airflow-image`: `template-docs/template-manifest.json`. **The source of truth for an Airflow job-image repo** (`da-<project>-airflow-image`: the `main.py --step/--run-date` entrypoint and `pipelines/_cli.py`, the `/secrets/.env`-aware `config.py`, the Dockerfile, CI with the docs and deny-rules tests, and the `airflow-image-layout` list). It declares `repo_kind: airflow-image` and `excludes` (`python-config`, because the image has its own `airflow-image-config` that also reads the mounted secret file, and `airflow-dag-sync`). The contract it shares with the DAG template is `template-docs/pod-contract.md`.
- `da-template-python-repo`: `docs/standards/template-manifest.json` (`app/configs/config.py`, `app/configs/log_config.py` with its redaction module, and a `python-layout` list of the folders and root files a Python repo should have, each tied to a rule id of `docs/standards/`).

Each `files` template has an integer `version`; its primary file carries a marker line, `# template: <id>@<version>` (`//` in JSON), so a repo records which version it applied. The marker is the first line, except in a file that starts with `---` (a `SKILL.md`: it goes right after that line, as a YAML comment) or `#!` (right after it); `bump` and `stamp` keep that place. The `python-layout` template has no file: its paths are checked live.

**Repo kind and precedence.** The helper recognises an image repo (a folder named `da-*-airflow-image`, or `app/pipelines/_cli.py`; tested first) and a DAG repo (a `.github/workflows/sync-dags.yml` with `DAG_EXECUTOR`, an `*_executor.py` under `dags/`, or a folder named `da-*-airflow-dags`). An older code repo that holds both an image and its DAG (`da-*-airflow` with `dags/`) is still read as a DAG repo until its image moves to a `da-<project>-airflow-image` repo. For an image repo `da-template-airflow-image` is the source of truth, and `cr-misc-function` and `da-template-python-repo` are the fallback (their `docker-image`, `ruff`, `mypy`, `python-logging` and `python-layout` still apply; `python-config` and `airflow-dag-sync` do not). For a DAG repo `da-template-airflow-dags` is the source of truth and `cr-misc-function` is the fallback: a template id the DAG source defines is taken from it only, every other id (ruff, mypy, VS Code) still comes from the fallback sources, and `check` prints `source of truth: ...; fallback: ...`. For any other repo the DAG source is ignored. A `files` template may use `{DAG_UTILS}` in its `dest` (the `common/` modules live in a package named per repo); the helper reads the name from `sync-dags.yml`.

Helper: `python3 ~/.claude/skills/template-sync/scripts/template_sync.py` (stdlib only, Python 3.9 and newer). Sources come from `--source` (repeat it), then `TEMPLATE_SOURCES` (paths separated by `:`), then the four usual checkouts under `~/repo/cr-misc-function/`. For workflow templates this skill defers to `github-actions-templates` (tag rules, hardening, `gh workflow run` test); for the rules behind the Python layout it uses `python-standards-learn` (`compare <repo>` audits a repo against the full standards, beyond what the layout list checks).

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
   | `DRIFT` | (`python-layout`) an expected path is missing, or a forbidden one such as `src/` exists | Fix it, or record it as deliberate (below) |
   | `DELIBERATE` | The repo recorded this difference on purpose | None; show the recorded reason |

3. **Plan before editing.** For each template that needs attention run `diff <id> <repo>` and the template's standard (`standard` in `list`) and sort the differences into: *template changes the repo should take* (new steps, hardening, renamed secrets), and *repo values to keep* (image name, port, health path, DAG names, `target-version`, paths). Show the plan and wait for the user's go-ahead on anything that changes behaviour (tags, secrets, triggers).
4. **Update one template at a time.** Edit the repo file toward the template, keeping the repo's values. Never copy the template over the file blindly. List the new secrets, variables or prerequisites the new version needs (read them from the template's header and the standard), but never write a secret value. Then run `stamp <id> <repo>`, which writes only the marker line.
5. **Deviations.** When a difference is on purpose (a library with `src/`, a repo with no Docker image, a custom pipeline), ask the user whether to keep it. Only when they say so, run `accept <template-id-or-rule-id> <repo> --reason "<why>"`. It appends one bullet to `docs/standards-deviations.md` in the repo (`- \`C-LAYOUT-01\`: installable library (2026-11-04)`), which is reviewed in the PR like any file. Never record a deviation on your own to make the report green. A rule id covers every path tied to that rule; a template id downgrades that template's `STALE` or `UNMARKED`. Re-ask when a template's version moves a lot after the date. `deviations <repo>` lists and validates the file (unknown ids and malformed bullets are reported).
6. **Verify.** Run `check --only <id>` again (it must say `CURRENT`), then the repo's own checks (`ruff`, `mypy`, `pytest`) for config templates. For a workflow, follow `github-actions-templates` step 6 (test from the work branch with `gh workflow run`); say plainly if it was not run.
7. **Report.** Per template: status before and after, what was taken from the template, what was kept, anything still to do (secrets to create, test run). Commit only when the user asks, on the current branch.

### Airflow image repos: the same rule

For a repo of kind `airflow-image` apply the DAG-repo procedure below with `da-template-airflow-image` as the source of truth: before planning edits, check that it really holds what the image repo needs, and copy anything that is only elsewhere into it (a branch and PR there, asking first), then apply it from there. Missing in the image template: a rule or standard goes to `template-docs/` as a sourced note; a workflow or script goes in with a manifest entry (`bump <id> --force`). A change to the pod contract (`template-docs/pod-contract.md`) also needs the DAG template changed; say so in the report. For new image repos, `setup-image-repo` (in the template) is the setup guide; for an existing code repo that still holds its DAG, the move is described in `template-docs/setup.md` of the image template and `template-docs/migrating-dags-from-a-code-repo.md` of the DAG template.

### Airflow DAG repos: complete the source of truth first

Before planning edits for a DAG repo, check that `da-template-airflow-dags` really holds what the repo needs. If
something about DAG repos is only in another place, **copy it into `da-template-airflow-dags`** (a branch and PR there,
asking the user first), then apply it from there; do not apply from the other place.

| Missing in the template repo | Copy from |
| --- | --- |
| A rule or standard (the DAG sync standard, branch flow, secrets rules) | `cr-misc-function` `docs/guidelines/`, as a file in `template-docs/` that says where it came from |
| A workflow, script or config the DAG repo needs | `cr-misc-function` `templates/`, then register it in the template's manifest (`bump <id> --force`) |
| A working rule or a hard-won fact about DAG repos (Airflow 3 target, master-only deploy, no secrets in Variables) | the user's `~/.claude/CLAUDE.md` and the project memory of the DAG repos, written as a short sourced note in `template-docs/` |
| A lesson from the repo being checked (a deliberate deviation worth keeping) | `docs/standards-deviations.md` of that repo, after the user agrees |

Copy only what is generic. Company hosts, registry names and secret values never go into `cr-misc-function` (public); the template repo is
private but still holds no secret values. Note the source and date in the copied file. A fallback template that the DAG source now covers is
added to its `overrides`, so the two cannot drift again.

## Rules

- Read-only until the user agrees to a change; `check`, `diff` and `list` never write.
- `stamp` is run only after the file really matches the template's version. A stamp on a file that was not updated hides drift.
- Keep the repo's own values; the template's `TODO` and placeholder lines are never copied as values.
- Do not touch `legacy/**`, `.env*`, `token.json` or `settings.local.json`.
- Company data (registry names, hosts, tokens) stays in the target repo, never in the template or in this skill.

## Maintaining the registry (in `cr-misc-function`)

- A change to a template file needs a version bump: `bump <id>` raises `version`, rewrites the marker of every file of the template that carries one (they share the version) and recomputes the digest in the source's manifest. `verify` (and `tests/test_template_sync.py`) fail when a template changed without a bump, so a repo is never told it is current when the template moved.
- Put the reason for the bump in the commit message. Template fixes land in `cr-misc-function` on their own PR before they are applied to repos.
- A new template: add its entry to the right manifest with `"version": 0` and `"marker": true` on exactly one file (a `layout` entry has `"kind": "layout"` and an `expect` list instead of files), then `bump <id> --force`. A layout change (a path added or removed) is a change too: `bump` it.
- Template ids are unique across sources; the helper refuses a duplicate.
- Machine setup (winget, WSL, conda) and AI-assistant config are not per-repo and are not in the registry.
