---
type: Deployment Type
title: out-of-repo
description: Changes the repo cannot show (DataWorks, Airflow, Vault, MaxCompute, Kubernetes config, other); always asked, one row per answer.
tags: [bast, ddcl, out-of-repo]
generated:
  by: claude-code/sonnet-5.5
  at: 2026-10-12T23:22:08+07:00
status: draft
---

- **Detected by:** always asked ("Any changes outside this repo?"). Covers DataWorks nodes, Airflow DAGs or Variables, MaxCompute, Vault secrets, Kubernetes config, and anything else the repo cannot show.
- **Row:** Test Scenario cell: `<action> <platform>` with the group information as bullets (workspace or host, nodes or objects, and so on, using the [row format](/deployment/row-format.md) label rules). Capture Screen cell: an upload placeholder for what Data Ops needs to see, such as `[Upload screenshot: DataWorks pipeline to be deployed]`, see [Capture Screen](/deployment/capture-screen.md). If the user gives only a platform, add `⚠ TO CONFIRM: exact object and change`.
- **Needs:** none from the repo docs.
- If the answer is none, write nothing: no row and no "no changes" line. A negative statement in the DDCL section only makes Data Ops ask why it is there.
