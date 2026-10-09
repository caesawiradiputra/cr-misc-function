---
name: bast-generator
description: Generate a BAST (Berita Acara Serah Terima) handover page in Confluence for a Data deployment, from a Jira ticket and the repo's release/<TICKET>/ folder. Copies the "BAST DATA" template page, fills the engineer-owned cells (description, epic links, requester, engineer, type/directorate/department, scope, DDCL Production rows, scenario test) and leaves Data Ops, CAB, PAT, UAT, approval and implementation cells empty. Use whenever the user says "create/generate a BAST for PROJ-1234", "buat BAST", "bikin BAST", "berita acara serah terima", or asks for deployment-handover documentation for a ticket, even if they don't say "Confluence".
---

# BAST Generator

Creates one new Confluence page per ticket by copying the `BAST DATA` template and filling only what the engineer owns. It is **create-only**: never edit an existing BAST unless the user explicitly asks.

Reference files (read them when the step says so, not up front):

- `references/template-map.md` — which template cell is filled from what, and how to locate each cell.
- `references/deployment-types.md` — the DDCL row registry (one entry per deployment type; append new types here).

## Hard rules

1. **HTML only.** Read and write the page with `content_format: "html"` / `body.format: "html"`. The template's structure (checkbox task-lists, status lozenges, mentions, panels, the TOC extension, layout sections, nested-expand) cannot be represented in markdown; a markdown round-trip silently drops it.
2. **Copy, never rebuild.** Use `copyConfluenceContent` on the template, then edit the copy. The header image belongs to the template's media collection, so an HTML string rebuilt from the template would lose it.
3. **Empty means empty.** Cells owned by Data Ops, the user, CAB or IT stay untouched. Do not put placeholders in them. The one exception is the source-code reference (repository, PR, branch) in CAB Checklist item 4, which the skill fills once per BAST.
4. **Sweep after edits.** After filling, re-read the copy and confirm no leftover template prompt text remains in a cell you were supposed to fill (for example `Isi dengan copas url epic`, `mention @`, or the sample date `January 21, 2022`).
5. **Preview before create.** The user must see the preview (step 6) and say OK before the copy is made.

## Constants

- Site `cloudId`: `<ATLASSIAN_CLOUD_ID>` (<ATLASSIAN_SITE>.atlassian.net). If a call rejects it, call `getAccessibleAtlassianResources` once.
- Template page ID: `<BAST_TEMPLATE_PAGE_ID>` (the user's own copy of the `BAST DATA` template, in their personal space). Read it live on every run so template changes carry over.
- Destination: the top-level of the user's personal space. Resolve its key with `getConfluencePersonalSpace` (do not hardcode). Use `destinationSpaceKey`, not `parentContentId`.
- Title: `[BAST] <TICKET> - <Jira summary>`.

## Steps

### 1. Identify the ticket and gather Jira data

Take the ticket ID from the user's message. If absent, ask.

- Fetch the ticket with `getJiraIssue` (`view: "full"`; the compact view omits `issuelinks`, `reporter` and custom fields).
- Find the **"clones" link** (`issuelinks` entry of type Cloners, outward issue). That linked issue (e.g. `IN-3295`, a Change Request) is the original request. Fetch it with `view: "full"` too.
- Take from the **clone (IN)** ticket: `reporter` (this is the **requester**, with `accountId`), Directorate (`customfield_10042`), Department (`customfield_10043`), Type Dev (`customfield_10052`), and the description.
- Take from the **DA** ticket: summary, description (fallback if the IN has none), and the Development field (PR state) for the source-repo note.
- If there is no clones link, leave requester, Directorate, Department and Type empty and say so in the preview. Do not guess from comments; approvers named in free-text comments are not parsed.
- Jira descriptions may come back as HTML with `data-local-id` attributes. Strip those attributes before reading the text.
- The BAST description is **not** a verbatim copy of the Jira description. Summarize it in Bahasa (why, which field or variable, effect) and add a "Perubahan pada deployment" bullet list of what the deployment will change, derived from the release-folder scripts and changed paths (step 2). State what stays unchanged and what is not affected (app code, image, schema) when that is true. Always name every added or changed variable in that list. Do not add a spec table (name, description, source, example query) and do not paste the Jira description or the requirement PDF: those are a copy of the requester's text and need not be reproduced.

### 2. Gather repo facts

From the current repo:

- `release/<TICKET>/` — `CHANGELOG.md`, `docs/requirement.md`, and every script under `ddl/`, `config/`, `data/`.
- The changed paths on the ticket branch versus the base (`git diff --name-only <base>...HEAD`). Use the base the repo's docs name (usually `dev`); fetch first (`git fetch --all --prune`) before concluding a branch does not exist.
- The repo's **Deployment Targets** documentation (step 3).
- The **source-code reference** for the CAB Checklist (once per BAST, see `references/template-map.md`): the repo's GitHub URL (`git remote get-url origin`, without the `.git` suffix), the ticket's branch name (from the release `CHANGELOG.md` `Branch:` line, or `git branch --show-current`), and the pull request link (`gh pr list --head <branch> --state all --json url`, or, if `gh` is unavailable or the branch is gone, the `(#NNN)` in the merge commit subject on the base branch, giving `<repo url>/pull/NNN`). Prefer the PR link, since the branch is usually deleted after merge. If none can be found, leave the reference out and say so in the preview.

### 3. Check the repo's deployment-target docs

Deployment facts (cluster, namespace, workload, DB host, DB name, Airflow environment and variable, and so on) belong in the repo, not in this skill and not in per-run prompts.

1. Look in the repo's `CLAUDE.md`, then `README.md`, for a `## Deployment Targets` section. `references/deployment-types.md` lists the fields each deployment type needs.
2. Fields present: use them silently.
3. Fields missing: ask the user only for the missing values, use them for this BAST, and afterwards **offer** (do not write unasked) to add a `## Deployment Targets` section to the repo's `CLAUDE.md`. Never edit both files. Hostnames are the user's decision, since the file is committed.
4. Anything the doc references that does not exist in the repo (for example a manifest file owned by another team): flag it in the `⚠` list and do not act on it.

**Also look for a `## BAST Conventions` section** in the same file (written by the `bast-learn` skill from this repo's older BASTs).

- Found: use it as guidance for structure and wording (description shape, how DDCL rows list this repo's kind of object, Scenario Test wording, usual field values). Follow the structure; never copy values from it. The rules in this skill and in `references/deployment-types.md` win over it if they conflict; say so in the preview. Field values (Directorate, Department, Type, requester) always come from Jira, never from the conventions section.
- Not found: proceed with this skill's defaults and add one line to the report suggesting `/bast-learn` to learn the repo's conventions. Do not stop, and do not search for old BASTs yourself (that is `bast-learn`'s job).

### 4. Build the DDCL Production rows

Read `references/deployment-types.md`. One row per **deployment action**: one script run, or one manual or out-of-repo action, against one platform or database. A script that updates a variable and runs a verify SELECT is **one row**, and a backup step inside it is left out of the row and of the description unless the backup impacts the application or process (see "Skip backups by default" in `references/deployment-types.md`). Write each row in the "Row format" from `references/deployment-types.md` (one host-or-workspace line, one database-or-schema line, an optional schedule or notes line, a tables, nodes or objects list with optional nested columns or variables, and a Steps line only when the steps are not obvious from the scripts; each label is chosen per platform and object type, never a slash-joined placeholder). Do not split a row by SQL verb, and do not add rows for artifacts that are not separate deployment actions.

Then always ask: **"Any changes outside this repo? (DataWorks, Airflow, Vault, MaxCompute, Kubernetes config, other)"**. Add one `out-of-repo` row per answer. If the answer is none, add nothing (no row and no "no changes outside this repository" line).

Anything the repo docs and files cannot answer is written into that row as `⚠ TO CONFIRM: <what is needed>` so the user can spot and fill it. In each filled DDCL row, put the user (`atlassianUserInfo`) in the PIC cell. Fill the Capture Screen cell as described under "Capture Screen" in `references/deployment-types.md`: an `[Attach file: <script file name>]` placeholder on repo-script rows, and group detail plus an `[Upload screenshot: …]` placeholder on out-of-repo rows. Leave unused spare rows empty.

### 5. Build the Scenario Test rows

Engineer-owned. Infer from the release folder (for example, a change to an S1 variable gets "Generate Payload to S1"; a schema change gets a row that verifies the schema). Put the user (`atlassianUserInfo`) in the PIC cell. Leave Capture Screen empty. If nothing can be inferred, leave the section empty rather than inventing scenarios.

### 6. Preview

Print a compact preview and wait for the user's OK:

- Title and destination.
- Each filled cell: label → value (requester, engineer, Type/Directorate/Department, scope, epic links).
- The DDCL rows, exactly as they will appear, with every `⚠` marked.
- What stays empty on purpose.
- Anything unresolved (missing clone link, missing deployment-target docs).

### 7. Create, fill, verify

1. Copy: `executeWrite` with `name: "copyConfluenceContent"`, `contentId: "<BAST_TEMPLATE_PAGE_ID>"`, `title`, `destinationSpaceKey`, top-level `cloudId`.
2. Load the format guide once: `executeRead` `getContentFormatGuide` with `inputs: {toolName: "updateConfluencePage"}`.
3. Read the **copy** (`getConfluenceContent`, `detail: "full"`, `content_format: "html"`). Take its `snapshotToken`. A server-side `copyConfluenceContent` preserves the template's `data-local-id`s, but a page copied some other way (for example by hand in the UI) may regenerate the short 12-hex ids. So locate each cell by its anchor text in the copy you just read (see `references/template-map.md`), and take the `localId` from that read, not from memory.
4. Apply the fills with `updateConfluenceContent` using `edits`: an array of `{"name": "replaceNode", "localId": "<id>", "value": "<html>"}` objects (verified working on PROJ-1845; numeric ids such as `"5"` on checkbox `<li>` items work too). Pass the copy's `snapshotToken`. Run the same array once with `dryRun: true` first and inspect the returned HTML, then repeat with `dryRun` omitted. Replaced nodes get new local ids, so take a fresh `snapshotToken` (from the update result) before any further edit, and re-read the page for current ids before editing a node you already replaced (a stale id is rejected with a 422 `granular_edit_unresolved` and changes nothing). To remove a node use `{"name": "deleteNode", "localId": "<id>"}` (also verified); prefer deleting or replacing the smallest node that holds the text, not the whole cell.
5. Mentions must be `data-type="mention"` spans with `data-user-id` set to an accountId: the requester's from Jira, the engineer's from `atlassianUserInfo` (fetch at runtime, never hardcode). Do not mention anyone else.
6. Tick checkboxes by adding the `checked` attribute to the matching `<input type="checkbox">`.
7. Re-read the copy and run the sweep (hard rule 4). A markdown re-read is acceptable for the text sweep, but it is lossy: inline smart-link cards (the Epic Key links) do not appear in it, so confirm those from the `dryRun` HTML instead of reporting them missing.

### 8. Report

Give the page link and a to-do list of what only the user can do: screenshots for the Scenario Test rows and for each `[Upload screenshot: …]` placeholder, and the script file for each `[Attach file: …]` placeholder (delete the placeholder text once uploaded), every `⚠ TO CONFIRM` line, and the cells intentionally left for Data Ops, the user, CAB and IT. Mention the MCP cannot upload attachments.

Then propose a logbook row (`/logbook`, `ticket` = the ticket key, `type` = `docs`, `task` = "Created the BAST page for <ticket>") and write it after the user's OK.

## Failure handling

- Template unreadable: stop and tell the user. Do not fall back to a hardcoded copy of the template.
- Copy succeeds but an edit fails: report the page link and which cells are still unfilled. Do not delete the copy.
- Never overwrite or edit a page that already has the target title without asking.
