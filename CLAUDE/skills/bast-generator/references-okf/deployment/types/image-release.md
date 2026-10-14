---
type: Deployment Type
title: image-release
description: A change that needs a new image build, turned into a "Build and push image" row.
tags: [bast, ddcl, image]
generated:
  by: claude-code/sonnet-5.5
  at: 2026-10-12T23:22:08+07:00
status: draft
---

- **Detected by:** changed paths under `app/`, `main*.py`, `Dockerfile`, `pyproject.toml` or `uv.lock` (anything that needs a new image build). A change that only touches `release/`, `sql_scripts/` or docs does not need one.
- **Row:** `Build and push image <image_name>:<tag> via <build workflow>`.
- **Needs:** registry, image name, build workflow, image tag. The tag is not stored in a file (in `<k8s-service-repo>` it is a manual `image_tag` input to the GitHub workflow), so ask for it, or read it from the latest workflow run if `gh` is available.
- **Next:** which deployment follows is decided by [Per-repo mapping](/deployment/per-repo-mapping.md): [kubernetes-deploy](/deployment/types/kubernetes-deploy.md) or [airflow-image-variable](/deployment/types/airflow-image-variable.md).
