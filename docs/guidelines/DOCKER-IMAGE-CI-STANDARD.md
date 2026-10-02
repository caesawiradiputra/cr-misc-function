# Docker Image CI Standard

The standard `Docker Image CI` GitHub Actions workflow for BFI data repositories that build an image and push it to the Alibaba Cloud Container Registry (ACR). The template is [`templates/github-workflows/docker-image.yml`](../../templates/github-workflows/docker-image.yml).

First used and tested in `da-negative-list` (PR #60, 2026-10-02). Every rule below exists because of something that broke or could break, noted in the *Why* column.

## 1. Adopting it in a repository

1. Copy the template to `.github/workflows/docker-image.yml`.
2. Set `IMAGE_NAME` and replace the `TODO` lines in the *Image build summary* step (port, health path, env vars).
3. Make the Dockerfile meet section 4.
4. Dispatch the workflow from a branch (section 6) and check the run before relying on it.
5. Decide on the layer cache (section 5).

## 2. Rules

| # | Rule | Why |
| --- | --- | --- |
| 1 | Only `master`, `dev` and `sit` push a mutable branch tag (`latest`, `dev`, `sit`). Every other branch pushes only `<image_tag>` and `<short SHA>`. | An earlier version mapped "any other branch" to `sit`; a run from a feature branch overwrote the `:sit` image. |
| 2 | Always push a 7-character commit SHA tag. | Any image can be traced back to its commit. |
| 3 | `permissions: contents: read`. | The job only checks out code; it authenticates to ACR with its own secrets. |
| 4 | Workflow inputs reach the shell only through `env:`, never as `${{ ... }}` inside a `run:` script. | A crafted input could otherwise inject shell commands. |
| 5 | Validate `image_tag` against `^[A-Za-z0-9_][A-Za-z0-9._-]{0,127}$` before building. | A bad tag otherwise fails only after the whole build. |
| 6 | `concurrency` group per ref and tag, `cancel-in-progress: false`. | Two runs with the same tag would race on the same registry tags. |
| 7 | `timeout-minutes: 30`. | A hung registry call can otherwise run for hours. |
| 8 | The `environment` input is informational only. | It labels the run and the summary but changes nothing in the build; people assume it selects configuration. |
| 9 | Use `docker/login-action`, not a hand-written `docker login`. | It logs out when the job ends, so credentials do not remain on the runner. |
| 10 | Build and push with `docker/build-push-action` and set `provenance: false` and `sbom: false`. | ACR rejects the attestation manifest buildx attaches by default: `denied: unknown manifest class for application/vnd.oci.empty.v1+json`. |
| 11 | Write the run summary through `tee -a "$GITHUB_STEP_SUMMARY"`, including the image digest and a complete local run command (`docker login`, then `docker run -d --name <image>_<tag>[-<env>] -p ... --env-file .env <image>:<tag>`). The container name is the image name and tag, plus `-<env>` unless the environment is `prod`, and without repeating the environment when the tag already ends with it (`v2.0` on `sit` gives `negative-list_v2.0-sit`, and so does `v2.0-sit`). | The digest lets a deployment pin an exact image: `<image>@sha256:...`. Writing only to the summary file leaves the step log showing the script source with unexpanded `${...}` and no output; `tee` prints the real values to the log as well. |
| 12 | Cache `scope` per image. | Without it, several images built in one repository (a matrix) share one cache and evict each other. |

Application configuration is never baked into the image or generated in CI; it is supplied at run time.

## 3. Tags

| Branch | Tags pushed |
| --- | --- |
| `master` | `<image_tag>`, `<short SHA>`, `latest` |
| `dev` | `<image_tag>`, `<short SHA>`, `dev` |
| `sit` | `<image_tag>`, `<short SHA>`, `sit` |
| any other branch | `<image_tag>`, `<short SHA>` |

Use an explicit `image_tag` (for example `1.4.0`) for anything a deployment will reference. Branch tags move; the version tag and the digest do not.

## 4. Dockerfile requirements

- **Pin the base image by digest**, keeping the tag for readability: `FROM repo/image:tag@sha256:<digest>`. A floating tag can be rebuilt on a newer OS without any code change. Example: `tiangolo/uvicorn-gunicorn:python3.9` was rebuilt on Debian 13, where `apt-key` no longer exists, and broke an `apt-key add` step that built fine on `python3.8`. Look up the digest of a tag on Docker Hub, then build and test before replacing it.
- **Pin tool versions**, for example `pip install uv==<version>`, so a new release of the tool cannot change the build.
- **Order layers for caching:** copy the dependency manifests (`pyproject.toml`, `uv.lock`) and install dependencies before copying the application code.
- **No `.env` files in the image.** Keep `.env*` in `.dockerignore`.
- Optional: mirror the base image into the BFI registry. Docker Hub limits anonymous pulls per IP address and GitHub runners share IP addresses. This has not been hit yet.

### 4.1 When to upgrade the pinned `uv` (and the base image digest)

Pinning stops a tool release from silently changing a build, but a pin that is never moved goes stale. The `uv` version in the Dockerfile (`pip install uv==<version>`) is a deliberate choice, changed on purpose, not by accident.

**Upgrade it when:**

| Trigger | What to do |
| --- | --- |
| The version that writes `uv.lock` on developer machines is newer than the Dockerfile's. Run `uv --version` and compare it with the Dockerfile pin. | Raise the Dockerfile pin to match. `uv.lock` records a format `version` and `revision` (`da-negative-list` was `version = 1`, `revision = 3`, written by uv 0.12.12). An older uv in the image may fail to read or may rewrite a lock written by a newer one, and `uv sync --frozen` should fail the build loudly. |
| A security advisory or a bug that affects the build or the lock resolution. | Upgrade promptly. |
| A uv feature or fix the repository needs. | Upgrade as part of that change. |
| A scheduled review, for example once a quarter (or when you revisit the base-image digest). | Check the latest release, read the release notes for lock-format or behaviour changes, and decide. If nothing needs it, leave the pin alone. |
| The base image's Python changes (for example 3.8 to 3.9). | Re-check that the pinned uv still installs on the new Python and re-test the whole build. |

**Do not** upgrade `uv` to the newest release just because it exists. A new release can change resolution, lock format or defaults, and you do not want that mixed into an unrelated change.

**How to upgrade, safely:**

1. Check that the release can be installed on the image's Python: its `requires_python` on PyPI must allow it. This matters most for old Python base images (both `0.12.12` and `0.12.22` allowed `>=3.8` when this was written).
2. Change the pin in the Dockerfile, and update the version on your developer machines to the same one (`uv self update`, or install the same version).
3. Run `uv lock --check`. If the lock needs regenerating, do that in the same change and review the diff of `uv.lock`: the runtime package versions must not move unless you intend it.
4. Build the image, start the container and call its health endpoints (a successful build alone has not been enough: a fresh resolve once produced an image that built but failed on import).
5. Dispatch the workflow from the branch and check the run (section 6).

Apply the same discipline to the **base image digest**: update it on purpose, after reading what changed in the image (OS release, Python patch version), and re-run the full build and container check.

## 5. Layer cache (optional)

The template caches layers in the GitHub Actions cache (`type=gha`). Measured in `da-negative-list`:

| Run | Total time |
| --- | --- |
| No cache (cold) | 93 s |
| First run with cache (fills it) | 103 s |
| Second run, nothing changed (best case) | 83 s |

Everything built in the Dockerfile was reused in the second run, yet the saving was only about 10 s because pulling the base image and pushing layers dominate and are not cached. The cache therefore pays off only where the apt and dependency-install layers are slow.

**The cache is scoped to the branch.** GitHub lets a run restore only caches created on its own branch or on the repository's default branch (for pull requests, also the base branch). A run on `sit` cannot use a cache written on `dev`, `master` or a feature branch. So the first run on each branch is a cold build that also writes the cache: in `da-negative-list` the first run on `sit` reused no layers, its cache export alone took 71 s, and the run took 144 s against 93 s without a cache. Later runs on the same branch hit the cache as long as the Dockerfile and the lock file are unchanged. A cache shared by all branches would have to live in a registry (`type=registry`); that has not been tried against ACR, which already rejects some OCI manifest types (see rule 10).

To decide for a repository: dispatch twice with the same tag and compare job durations. If the saving is small, delete the `cache-from` and `cache-to` lines; keeping `build-push-action` and the flags above is still worthwhile. A code-only commit rebuilds only the last layers, and a change to the lock file rebuilds the dependency layer.

## 6. Testing the workflow on a branch

`workflow_dispatch` runs the workflow file from the branch you select, so a work branch can be tested before merging:

```bash
gh workflow run docker-image.yml --ref <branch> -f image_tag=<test-tag> -f environment=dev
```

- A feature branch pushes only `<test-tag>` and `<short SHA>`; no branch tag moves.
- Delete the test tags from the registry afterwards.
- Check the job summary for the tags and digest.

To check the tag logic without running anything, extract the `Resolve image tags` script and run it locally with different `REF_NAME`, `INPUT_IMAGE_TAG` and `COMMIT_SHA` values.

## 7. Known follow-ups

- This repository's own `.github/workflows/docker-image.yml` still follows the older convention (no hardening, branch tag for any branch) and there is no Dockerfile in the repository. Align or remove it.
- The older inline workflow in `GITHUB-WORKFLOW-CONSOLIDATED.md` section 3 predates this standard; the standard takes precedence.
- `GITHUB-WORKFLOW-STANDARDIZATION copy.md` duplicates the other workflow guides and carries a third version of the workflow; consider removing it.
