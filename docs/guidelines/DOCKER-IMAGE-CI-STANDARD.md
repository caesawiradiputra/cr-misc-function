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
| 11 | Write the run summary to `$GITHUB_STEP_SUMMARY`, including the image digest. | The digest lets a deployment pin an exact image: `<image>@sha256:...`. |
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

## 5. Layer cache (optional)

The template caches layers in the GitHub Actions cache (`type=gha`). Measured in `da-negative-list`:

| Run | Total time |
| --- | --- |
| No cache (cold) | 93 s |
| First run with cache (fills it) | 103 s |
| Second run, nothing changed (best case) | 83 s |

Everything built in the Dockerfile was reused in the second run, yet the saving was only about 10 s because pulling the base image and pushing layers dominate and are not cached. The cache therefore pays off only where the apt and dependency-install layers are slow.

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
