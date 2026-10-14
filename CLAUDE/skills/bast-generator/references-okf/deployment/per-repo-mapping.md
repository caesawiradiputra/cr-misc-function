---
type: Mapping
title: Per-repo mapping after an image release
description: Which deployment types follow an image release in each repo.
tags: [bast, ddcl, repos]
generated:
  by: claude-code/sonnet-5.5
  at: 2026-10-12T23:22:08+07:00
status: draft
---

| Repo | After an image release |
| --- | --- |
| `<k8s-service-repo>` | Kubernetes only ([kubernetes-deploy](/deployment/types/kubernetes-deploy.md)). The K8s manifest is owned by another team and is deliberately not in the repo. |

Add a row for each repo when its convention is known. For a repo not listed here, ask the user which of `kubernetes-deploy` and `airflow-image-variable` follow an image release, and offer to record the answer here.
