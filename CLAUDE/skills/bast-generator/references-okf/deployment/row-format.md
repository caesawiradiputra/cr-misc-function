---
type: Rule
title: DDCL row format
description: Layout, label-choice and counting rules for one DDCL Production row (Test Scenario cell).
tags: [bast, ddcl, format]
generated:
  by: claude-code/sonnet-5.5
  at: 2026-10-12T23:22:08+07:00
status: draft
---

# Granularity

One row per action. One script that does several things is one row; a "Steps" line is added only when the steps are not obvious from the script. Several objects touched by the same action are listed inside the row, not split. A row's "Test Scenario" cell is the action plus the objects it touches. The PIC cell of each filled row is the user (a mention from `atlassianUserInfo`). Leave an unused spare row empty.

# Layout

Data-platform rows (Postgres, MSSQL, ODPS/MaxCompute, Holo, and similar) use this layout in the Test Scenario cell:

```text
Execute script in <platform>:
- <Host | Workspace>: <value>
- <Database | Schema>: <value>
- (optional) <Schedule | Notes>: <value>
- <Tables | Nodes | Objects>:
  - <name>
    - (optional nested) <Columns | Variables | ...>: <value>
- (optional, only when not obvious from the scripts) Steps: (a) ..., (b) ..., (c) ...
```

**Every `A | B` above is a choice, not literal text.** Pick exactly one label per line and write only that label. Never write a slash-joined label such as `Workspace / Host`.

| Position | Rule |
| --- | --- |
| Verb | `Execute script` when a script is run. For any other action use the verb that fits (`Deploy`, `Publish`, `Create`, `Update`, `Trigger`, `Restart`, `Set`, `Grant`, and so on). |
| Platform | The real platform name (`Postgres`, `MSSQL`, `ODPS`, `Holo`), never the list. |
| Host or Workspace | `Host` for Postgres and MSSQL. `Workspace` for ODPS (and other workspace-based platforms such as DataWorks). Holo: `Host` unless the repo docs say otherwise. |
| Database or Schema | `Database` when the platform has one (Postgres, MSSQL, Holo). For ODPS use `Project`-style naming from the repo docs, else `Schema`. Put a schema in the object name (`public.additional_attributes_s1`) instead of a second line. |
| Schedule or Notes | `Schedule` when the action has one (cron, DataWorks schedule). Otherwise `Notes` if there is something worth saying, else omit the line. |
| Tables, Nodes or Objects | `Tables` for SQL tables and views, `Nodes` for DataWorks or Airflow nodes, `Objects` when they are mixed or something else (functions, procedures). |
| Nested detail | `Columns` when columns change, `Variables` for S1 variables (rows in `additional_attributes_s1`), otherwise a fitting label. |

**The table gives examples, not a closed list.** The change types, objects, platforms and actions a ticket can involve are open-ended: views, functions, stored procedures, indexes, permissions, DAGs, jobs, files, config keys, secrets, topics, dashboards, and things not named here. Apply the same principle to all of them: pick the one label a Data Ops engineer would naturally use for that platform and that kind of object (`Host` vs `Workspace`, `Tables` vs `Nodes` vs `Objects`, `Columns` vs `Variables` vs `Keys`, and so on), write only that label, and never copy a slash-joined placeholder. When nothing in the table fits, choose a plain descriptive label and mention the choice in the preview so the user can correct it.

# Other rules

- **Do not put the script path in the row.** Data Ops does not check the repo directly, so a repo path is noise to them. Name the action and the objects it touches instead.
- **Use the proper word for the count.** A label is singular when its list has one item and plural when it has several (`Table` / `Tables`, `Node` / `Nodes`, `Object` / `Objects`, `Column` / `Columns`, `Variable` / `Variables`).
- **Backups** are left out by default, see [Skip backups by default](/deployment/skip-backups.md).
- Drop a line that does not apply; never leave an empty label.
- List every object the action touches under the tables, nodes or objects list, including ones it creates (for example a new table), with a short marker such as `(created)`.
- **Skip the "Steps" line when the steps are obvious from the files or scripts.** Data Ops can read the script, so a Steps line that only restates it (for example "update the variable, then verify with a SELECT") is noise. Add it only when the order or intent is not evident from the script itself: manual actions outside the script, a required order across several scripts or platforms, a condition or wait between actions, or a step that must be run by hand. When unsure, leave it out.
- Non-data-platform rows ([image-release](/deployment/types/image-release.md), [kubernetes-deploy](/deployment/types/kubernetes-deploy.md), [airflow-image-variable](/deployment/types/airflow-image-variable.md), [out-of-repo](/deployment/types/out-of-repo.md)) keep the same bullet style with their own labels.

Repo-level facts (cluster, namespace, DB host, and so on) come from the repo's `## Deployment Targets` doc section, never from this bundle. Fields are listed under "Needs" for each type; missing ones are asked once, then the skill offers to add the section to the repo's `CLAUDE.md`.
