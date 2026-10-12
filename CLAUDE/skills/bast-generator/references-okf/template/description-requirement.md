---
type: Template Cell
title: DESCRIPTION REQUIREMENT
description: The cell holding the "Isi dengan informasi dari kebutuhan perubahan system baru/enhancement..." prompt; filled with a Bahasa summary and a deployment-changes list.
tags: [bast, template, engineer-owned]
generated:
  by: claude-code/sonnet-5.5
  at: 2026-10-12T23:22:08+07:00
status: draft
---

# Anchor

The cell holding the prompt `Isi dengan informasi dari kebutuhan perubahan system baru/enhancement yang di minta oleh user/it`.

# Fill

Replace the prompt with a Bahasa summary of the requirement: one short paragraph (why, which field or variable, effect). Then add a "Perubahan pada deployment" bullet list of what the deployment will actually change: objects touched, what stays unchanged, and what is not affected (app code, image, schema).

# Source

The IN description (else the DA description) for the summary. The release-folder scripts and changed paths for the deployment changes. Not copied verbatim: do not add a spec table and do not paste the Jira description or the requirement PDF.

Always name every added or changed variable in the list. Backups follow [Skip backups by default](/deployment/skip-backups.md).
