# What to extract

Cover each dimension for **all** repos first (this is the common layer), then note where a type differs. The inventory script fills most of the facts; the rest comes from sampling a few files.

| # | Dimension | From the inventory | Sample by reading |
| --- | --- | --- | --- |
| 1 | **Repo layout** | `layout.*` (src/ or app/, main.py, dags/, release/, scratch/, legacy/, docs/, CLAUDE.md), top-level names | module structure under `src/`/`app/` (config, connections, repositories, services, utils), where entrypoints live |
| 2 | **Naming** | repo names, top-level folders | module, function, class, constant, env var names; test file names; branch/tag/image names from `git branch -r`, workflows |
| 3 | **Packaging and Python version** | `packaging.*` (requires-python, lock file, backend, build backend, requirements files, conda env) | whether `.python-version` agrees with `requires-python` and the Dockerfile base |
| 4 | **Config and secrets** | `config_secrets.*` (env template, dotenv, pydantic-settings, os.environ, Airflow Variable/Connection, tracked secret-like files, gitignore of `.env`) | how a settings object is built, where defaults live, how secrets reach the container (env file, mounted file, Airflow connection). Never open `.env` or credential files |
| 5 | **Lint and typing** | `lint_typing.*` (ruff, mypy, pyrefly, line length, target version, pre-commit) | whether the config matches the shared templates; how strict typing is |
| 6 | **Tests** | `tests.*` (dir, file count, conftest, pytest config) | what is tested (units, repositories with fakes, API routes), fixtures style, any integration/smoke tests |
| 7 | **Docker** | `docker.*` (base, digest pin, multi-stage, user, EXPOSE, HEALTHCHECK, CMD/ENTRYPOINT, install tool, uv pin, dockerignore, compose) | layer order, how the app is installed, where config comes in |
| 8 | **CI and deployment** | `ci.workflows[]` (triggers, docker build, provenance false, login action, permissions, concurrency, lint/test run) | tags pushed per branch, how the image is run (Kubernetes, Airflow image operator, docker run), what the run summary says. **Read deploy and DAG-sync workflows in full** (`deploy-*`, `sync-dags*`): they hold the deployment contract (shared reusable workflows, inputs, branch-to-target mapping, secret names) that the inventory flags only by file name. If a shared workflow lives in a repo you cannot read, record the call shape and mark the inside as Unknown |
| 9 | **Logging and errors** | (none) | logger choice and setup, log level from env, exit codes for one-shot jobs, retry/backoff and shutdown handling for long-running ones |
| 10 | **Docs and release hygiene** | `layout.has_readme`, `has_claude_md`, `has_release_dir` | README sections, `release/<TICKET>/` and `scratch/` use, changelog conventions |

## Type-specific things to look for (only if the type differs)

- **airflow-job**: the one-shot entrypoint and exit-code contract, how the image is invoked by the operator, how arguments and Variables/Connections reach it, the `dags/` layout, whether the image has no `EXPOSE` or health port.
- **fastapi-service / flask-service**: app factory or module-level app, router/layer layout, health and readiness route, server command and workers, request/response models, API tests with a test client, port and `EXPOSE`.
- **consumer**: client library and group handling, dead-letter or retry handling, health port, offset/commit policy, idempotency, and whether the repos handle shutdown signals at all (record it only if some do).
- **streamlit / ui**: page layout, auth, port and CMD.
- **crawler-batch**: scheduling mechanism, rate limiting and retries, output sink, idempotent re-run.
- **agent-mcp**: tool/agent module layout, prompt/config files, how model credentials are supplied.

If a type has fewer than 3 repos it is **thin**: write a short paragraph of what is distinctive and do not propose a scaffold.

## What never goes into the standards

Hosts, database or table names, bucket names, registry credentials, tokens, people's names, ticket keys (except as provenance), customer data. Describe the pattern instead ("endpoint host comes from an env var named `<SERVICE>_HOST`").
