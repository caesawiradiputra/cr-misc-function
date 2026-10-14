---
type: Deployment Type
title: kubernetes-deploy
description: Rolling a new image out to a Kubernetes workload, one row with cluster, namespace and workload.
tags: [bast, ddcl, kubernetes]
generated:
  by: claude-code/sonnet-5.5
  at: 2026-10-12T23:22:08+07:00
status: draft
---

- **Detected by:** an [image-release](/deployment/types/image-release.md) row exists and the [per-repo mapping](/deployment/per-repo-mapping.md) selects Kubernetes.
- **Row:** Test Scenario cell: `Deploy <platform, e.g. ACK>` with the group information as bullets (`Cluster`, `Namespace`, `Deployments`). Capture Screen cell (a change outside the repo, see [Capture Screen](/deployment/capture-screen.md)): the image detail (`Edit Image:` with `Repository` and `Version Tag`) plus an upload placeholder such as `[Upload screenshot: workload showing the new image tag]`.
- **Needs:** cluster, namespace, workload name, manifest owner, image repository, image tag.
