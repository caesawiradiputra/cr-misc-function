---
name: github-actions-templates
description: Start every GitHub Actions workflow from the standard templates in the `cr-misc-function` repo instead of hand-writing one. Use whenever the user is creating a new repository or its CI, asks to add, update, fix or review a `.github/workflows/*.yml` file, says "docker image workflow", "build and push to ACR", "image tag", "sync the DAG to Airflow", "set up CI for this repo", "update the github action", or mentions `docker-image.yml` or `sync-dags.yml`, even if they never name the templates. Picks the matching template and standard, copies it, fills the placeholders, tests it with `gh workflow run`, and reports where the repo's workflow has drifted from the template.
---

# GitHub Actions templates

The workflows that build images and sync DAGs already have a tested standard. A hand-written variant repeats mistakes the standard fixed (a feature branch overwriting `:sit`, a registry rejecting attestations, a token reaching a feature branch). So the rule is: **start from the template, never from a blank file**.

## Where the templates are

The `cr-misc-function` repository (commonly checked out at `~/repo/cr-misc-function/cr-misc-function`; if it is not on disk, read the files with `gh api repos/<owner>/cr-misc-function/contents/<path>` or clone it into the scratchpad).

| The user wants | Template | Standard (read it before changing anything) |
| --- | --- | --- |
| Build a Docker image and push it to ACR | `templates/github-workflows/docker-image.yml` | `docs/guidelines/DOCKER-IMAGE-CI-STANDARD.md` |
| Publish a DAG from a data repo to the Airflow deployment repo | `templates/github-workflows/airflow-dag-sync/` (`sync-dags.yml` or `sync-dags.github-app.yml`, plus `scripts/`) | `docs/guidelines/AIRFLOW-DAG-SYNC-STANDARD.md` |
| Lint, type check and tests for a Python repo | `.github/workflows/python-ci.yml` in the same repo | `CLAUDE.md` of that repo |
| Anything else | No template yet: say so, write it following the hardening rules below, and offer to add it as a template | none |

## Workflow

1. **Read the repo's current state first.** `ls .github/workflows/`, then read the file you will change. Check `git status` (check state before writing). If the repo already has the workflow, this is an *update*: diff it against the template and list the differences before editing.
2. **Pick the template** from the table and read its standard, not only the YAML. The standard's *Why* column explains rules that look optional.
3. **New repo:** copy the template to `.github/workflows/` under the standard's file name, replace every `TODO` and `<PLACEHOLDER>`, and check the repo meets the prerequisites the standard lists (for Docker: a Dockerfile that pins its base image by digest and its tools, `.env*` in `.dockerignore`; for the DAG sync: the `dags/<DAG_EXECUTOR>` plus `dags/<DAG_UTILS>/` layout and the token variant).
4. **Update an existing workflow:** bring it to the template, one concern at a time, and keep the repo's own values (image name, registry, port, health path, DAG names). Do not copy the template over the file blindly. If the template itself is out of date or wrong, fix the template in `cr-misc-function` on its own PR first, then apply it to the repo.
5. **Secrets and tokens:** list the repository, organization or Environment secrets the workflow needs and where they are created. Never write a secret value into a file. For the DAG sync, the write token is an organization secret or an `airflow-sync` Environment secret, never a plain repo secret.
6. **Test before relying on it:** `gh workflow run <file> --ref <branch> [-f image_tag=...]`, then `gh run watch` and read the step summary. A feature-branch run must not move any branch tag. Delete the test tags from the registry afterwards. For the Docker tag logic, the standard also describes a local run of the `Resolve image tags` script.
7. **Report:** which template and standard were used, the placeholders set, secrets still to create, what was tested and what was not, and any drift left in the repo.

## Rules that apply to every workflow

These are the same across the standards; the standard has the reason for each.

- `permissions: contents: read` at the top, and nothing broader unless a job needs it.
- Inputs and ref names reach shell steps only through `env:`, never as `${{ ... }}` inside `run:`.
- Pin third-party actions to a major version at least; use `persist-credentials: false` on checkout when the job does not push.
- `timeout-minutes` on every job and a `concurrency` group (`cancel-in-progress: false` for anything that publishes).
- Write the run summary with `tee -a "$GITHUB_STEP_SUMMARY"` so the log shows the real values too.

## Docker image tags (the part that goes wrong most)

- **No version number in SIT or feature builds.** An empty `image_tag` on a branch named `<type>/<TICKET>-<slug>` becomes `sit-<TICKET>`. Rebuilding the same ticket overwrites its own tag, so a cancelled SRF reserves no version.
- **The production version is chosen only at release** (last production tag plus the bump, when the `dev` to `master` PR merges) and passed explicitly as `image_tag` on the `master` run. An empty `image_tag` on `master`, `dev`, `sit` or a branch without a ticket key fails.
- **No commit-SHA tag.** The commit is in the step summary and the digest is the identity.
- Only `master`, `dev` and `sit` push a branch tag (`latest`, `dev`, `sit`).
- ACR rejects buildx attestations: keep `provenance: false` and `sbom: false`.

## What not to do

- Do not hand-write a new variant of a workflow that has a template.
- Do not change a repo's workflow and the template in the same PR unless the change is the template's own fix; the template lands first.
- Do not run a workflow that pushes to a registry or opens a PR without telling the user which ref, tag and target it will use.
- Do not put real registry names, namespaces or secrets into the template; they are placeholders there and real values only in the target repo.
