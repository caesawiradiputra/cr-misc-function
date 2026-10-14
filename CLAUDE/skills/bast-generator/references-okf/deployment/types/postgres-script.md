---
type: Deployment Type
title: postgres-script
description: SQL scripts under release/<TICKET>/ddl/<platform>/, config/ or data/, turned into one "Execute script in Postgres" row.
tags: [bast, ddcl, postgres]
generated:
  by: claude-code/sonnet-5.5
  at: 2026-10-12T23:22:08+07:00
status: draft
---

- **Detected by:** script files under `release/<TICKET>/ddl/postgres/` (or another `ddl/<platform>/`, `config/`, `data/` folder holding SQL).
- **Row:** the [row format](/deployment/row-format.md) with `Postgres`, listing the tables and variables the script touches (parsed from the SQL). Add a "Steps" line only when the script's steps are not obvious from reading it; if you do, build it from the script:
  - `CREATE TABLE ... AS SELECT` used as a backup → skipped, see [Skip backups by default](/deployment/skip-backups.md); a `CREATE TABLE ... AS SELECT` that builds a real table is a step naming that table
  - `UPDATE <table> ... WHERE attribute_name = '<x>'` → "(b) update <table>, variable <x>"
  - `ALTER TABLE` / `CREATE` / `INSERT` / `DELETE` → one step each, naming the object
  - a trailing `SELECT` → "(c) verify with SELECT"
- **Capture Screen:** `[Attach file: <script file name>]`, see [Capture Screen](/deployment/capture-screen.md).
- **Needs:** DB host, DB name, schema.
- **Note:** several scripts on the same database that the user runs as one action merge into one row.
