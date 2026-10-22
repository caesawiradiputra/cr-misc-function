# Idea: a skill that learns and documents my coding preferences

**Status:** idea, not designed or built. Written 2026-10-19 as a "what next to do" item from the DA-1901 session (`da-df4w-pd-monitoring-airflow`).

## Why

A new or modified project of the same kind (Airflow batch pipeline, API, Streamlit app, DataWorks job) should start from the same setup and coding rules, instead of rediscovering them each time. Today the preferences live in scattered places: `~/.claude/CLAUDE.md`, per-repo `CLAUDE.md`, sibling repos (`da-ndf4w-pd-monitoring-airflow` is the reference for Airflow), and corrections given in sessions.

## What the skill would do

1. **Read the evidence** (never session transcripts in bulk, as the logbook rule says): the sibling repos of one kind, their `CLAUDE.md`, `pyproject.toml`, `Dockerfile`, DAG executors, `configs/`, `connection/`, tests, CI workflows, and `git log` / PR review comments.
2. **Extract the preferences** per project kind, each with evidence (file or commit) and a confidence: structure (`src/`, `utils/`, `configs/`, `connection/`, `dags/`), tooling (uv, ruff, mypy, Python version), settings and secrets handling, DAG shape (pod tasks, PVC hand-over, paused on creation, pull policy rule), DB write pattern, OSS usage, naming, logging, tests, CI, release folder.
3. **Report improvements** found in the comparison: defects in the reference code that should not be copied (for example the NDF4W upload that swallows errors, config printed with keys, hardcoded credentials), and rules that differ between repos without a reason.
4. **Write the result** as a per-kind standard (a document in `docs/guidelines/`, like `DOCKER-IMAGE-CI-STANDARD.md`) and, with approval, a project template or scaffold, so a new repo starts from the standard.

## Seed material from DA-1901 (already learned, not yet written down)

- Airflow pipeline layout and DAG rules: four pod tasks through `pod_task`, `max_active_runs=1`, paused on creation, pinned timezone, same image for every task, only the first pod takes the pull policy from the Variable, the others `IfNotPresent`.
- Stages hand files over through `PVCDataManager`; the final task is `99_save_data_to_db`; PostgreSQL via `create_table`; the build bucket copy is the fallback and the dashboard feed.
- `variables.json` holds keys with empty secrets; the sync scripts and workflow are copied from the whitelist repo.
- Python 3.12 is allowed when the model stack needs it; the DAG tests live in a separate Airflow venv.
- Naming: the OSS gold prefix uses underscores (`datamart_reject_reason_df4w_pd_summary`), on purpose.

## Open questions

- Which project kinds first: Airflow pipelines only, or APIs and Streamlit too?
- Output form: guidelines document only, or also a `da-template-*` repo (there is a `da-template-python-repo` already)?
- Where the standard lives and how it is kept current (a changelog line per change, as for the Docker standard).
- Whether it runs on request only, or the kickoff skill (`jira-ticket-kickoff`) loads the standard for a new repo.
