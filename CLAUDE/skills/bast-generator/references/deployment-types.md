# Deployment type registry

Each entry defines how one kind of deployment action becomes **one DDCL Production row**. To support a new deployment type later, append an entry here; `SKILL.md` needs no change.

A row's "Test Scenario" cell is the action plus the objects it touches (and steps only when they are not obvious from the scripts). The PIC cell of each filled row is the user (a mention from `atlassianUserInfo`). Leave an unused spare row empty.

**Capture Screen.** Changes outside the repo get: group detail that does not fit the Test Scenario cell (for example an image repository and tag) and a placeholder of the form `[Upload screenshot: <what to capture>]`, for example the DataWorks pipeline that will be deployed. Rows for scripts that live in the repo (Postgres scripts and similar) get a placeholder for the script file itself, `[Attach file: <script file name>]`, because Data Ops does not check the repo, so the file is attached to the row. Repo-script rows do not get a screenshot placeholder. The placeholder is a reminder for the engineer and is deleted after the screenshot is uploaded (the MCP cannot upload attachments). Anything unknown becomes `⚠ TO CONFIRM: <what>` inside the row.

Granularity rule: **one row per action**. One script that does several things is one row; a "Steps" line is added only when the steps are not obvious from the script. Several objects touched by the same action are listed inside the row, not split.

## Row format

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

Other rules:

- **Do not put the script path in the row.** Data Ops does not check the repo directly, so a repo path is noise to them. Name the action and the objects it touches instead.
- **Use the proper word for the count.** A label is singular when its list has one item and plural when it has several (`Table` / `Tables`, `Node` / `Nodes`, `Object` / `Objects`, `Column` / `Columns`, `Variable` / `Variables`).
- **Skip backups by default.** A backup or snapshot step (for example `CREATE TABLE ..._backup AS SELECT`) and the backup table itself are left out of the row's objects, its Steps line, and the BAST description. Include them only when the backup impacts the application or process, for example the application or a pipeline reads the backup, the backup is large or slow enough to affect production, or Data Ops must run it as a required rollback step. When unsure, leave it out and mention in the preview that a backup was skipped so the user can ask for it.
- Drop a line that does not apply; never leave an empty label.

- List every object the action touches under the tables, nodes or objects list, including ones it creates (for example a new table), with a short marker such as `(created)`. Backup tables are not listed unless they meet the exception in "Skip backups by default".
- **Skip the "Steps" line when the steps are obvious from the files or scripts.** Data Ops can read the script, so a Steps line that only restates it (for example "update the variable, then verify with a SELECT") is noise. Add it only when the order or intent is not evident from the script itself: manual actions outside the script, a required order across several scripts or platforms, a condition or wait between actions, or a step that must be run by hand. When unsure, leave it out.
- Non-data-platform rows (`image-release`, `kubernetes-deploy`, `airflow-image-variable`, `out-of-repo`) keep the same bullet style with their own labels from the entries below.

Repo-level facts (cluster, namespace, DB host, and so on) come from the repo's `## Deployment Targets` doc section, never from this file. Fields are listed under "Needs" for each type; missing ones are asked once, then the skill offers to add the section to the repo's `CLAUDE.md`.

## Per-repo mapping

| Repo | After an image release |
| --- | --- |
| `<k8s-service-repo>` | Kubernetes only (`kubernetes-deploy`). The K8s manifest is owned by another team and is deliberately not in the repo. |

Add a row for each repo when its convention is known. For a repo not listed here, ask the user which of `kubernetes-deploy` and `airflow-image-variable` follow an image release, and offer to record the answer here.

## Types

### postgres-script

- **Detected by:** script files under `release/<TICKET>/ddl/postgres/` (or another `ddl/<platform>/`, `config/`, `data/` folder holding SQL).
- **Row:** the Row format above with `Postgres`, listing the tables and variables the script touches (parsed from the SQL). Add a "Steps" line only when the script's steps are not obvious from reading it; if you do, build it from the script:
  - `CREATE TABLE ... AS SELECT` used as a backup → skipped (see "Skip backups by default"); a `CREATE TABLE ... AS SELECT` that builds a real table is a step naming that table
  - `UPDATE <table> ... WHERE attribute_name = '<x>'` → "(b) update <table>, variable <x>"
  - `ALTER TABLE` / `CREATE` / `INSERT` / `DELETE` → one step each, naming the object
  - a trailing `SELECT` → "(c) verify with SELECT"
- **Needs:** DB host, DB name, schema.
- **Note:** several scripts on the same database that the user runs as one action merge into one row.

### image-release

- **Detected by:** changed paths under `app/`, `main*.py`, `Dockerfile`, `pyproject.toml` or `uv.lock` (anything that needs a new image build). A change that only touches `release/`, `sql_scripts/` or docs does not need one.
- **Row:** `Build and push image <image_name>:<tag> via <build workflow>`.
- **Needs:** registry, image name, build workflow, image tag. The tag is not stored in a file (in `<k8s-service-repo>` it is a manual `image_tag` input to the GitHub workflow), so ask for it, or read it from the latest workflow run if `gh` is available.

### kubernetes-deploy

- **Detected by:** an `image-release` row exists and the repo mapping (above) selects Kubernetes.
- **Row:** Test Scenario cell: `Deploy <platform, e.g. ACK>` with the group information as bullets (`Cluster`, `Namespace`, `Deployments`). Capture Screen cell (this is a change outside the repo, see "Capture Screen" above): the image detail (`Edit Image:` with `Repository` and `Version Tag`) plus an upload placeholder such as `[Upload screenshot: workload showing the new image tag]`.
- **Needs:** cluster, namespace, workload name, manifest owner, image repository, image tag.

### airflow-image-variable

- **Detected by:** the repo mapping selects Airflow, or the user says the image is consumed by Airflow.
- **Row:** `Update Airflow Variable <name> to image <tag> (<environment>)`.
- **Needs:** Airflow environment, variable name.

### out-of-repo

- **Detected by:** always asked ("Any changes outside this repo?"). Covers DataWorks nodes, Airflow DAGs or Variables, MaxCompute, Vault secrets, Kubernetes config, and anything else the repo cannot show.
- **Row:** Test Scenario cell: `<action> <platform>` with the group information as bullets (workspace or host, nodes or objects, and so on, using the label rules above). Capture Screen cell: an upload placeholder for what Data Ops needs to see, such as `[Upload screenshot: DataWorks pipeline to be deployed]`. If the user gives only a platform, add `⚠ TO CONFIRM: exact object and change`.
- **Needs:** none from the repo docs.
- If the answer is none, write nothing: no row and no "no changes" line. A negative statement in the DDCL section only makes Data Ops ask why it is there.

## Adding a type

Append `### <type-name>` with the same four fields: Detected by, Row, Needs, and any Note. Keep one action per row.
