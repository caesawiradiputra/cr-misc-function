---
type: Rule
title: Skip backups by default
description: A backup or snapshot step is left out of the row, its objects, its Steps line and the BAST description unless it impacts the application or process.
tags: [bast, ddcl, backup]
generated:
  by: claude-code/sonnet-5.5
  at: 2026-10-12T23:22:08+07:00
status: draft
---

A backup or snapshot step (for example `CREATE TABLE ..._backup AS SELECT`) and the backup table itself are left out of the row's objects, its Steps line, and the BAST description.

Include them only when the backup impacts the application or process:

- the application or a pipeline reads the backup,
- the backup is large or slow enough to affect production, or
- Data Ops must run it as a required rollback step.

When unsure, leave it out and mention in the preview that a backup was skipped so the user can ask for it.
