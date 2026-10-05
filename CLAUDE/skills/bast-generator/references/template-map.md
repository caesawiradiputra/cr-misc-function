# Template map: `BAST DATA`

Template page ID `<BAST_TEMPLATE_PAGE_ID>`. This lists each cell of the template, who owns it, and what fills it. Locate cells in the **copy** by their anchor text, then take the `data-local-id` from the copy you just read. A server-side `copyConfluenceContent` preserved every id (short and UUID-style) on PROJ-1845, but a page copied another way may not, so never reuse ids from memory or from the template read.

Lozenges such as `DI ISI OLEH IT QA` and `DI ISI OLEH engineer` stay as they are; they are part of the template.

## Filled by this skill

| Section / anchor text | Fill | Source |
| --- | --- | --- |
| **DESCRIPTION REQUIREMENT** — the cell holding the prompt `Isi dengan informasi dari kebutuhan perubahan system baru/enhancement...` | Replace the prompt with a Bahasa summary of the requirement (one short paragraph: why, what field/variable, effect), then a "Perubahan pada deployment" bullet list of what the deployment will actually change (objects touched, what stays unchanged, what is not affected such as app code, image or schema) | IN description (else DA) for the summary; release folder scripts and changed paths for the deployment changes. Not copied verbatim. |
| **Epic Key** — the cell holding `Isi dengan copas url epic` | One inline-card link per ticket, e.g. `https://<ATLASSIAN_SITE>.atlassian.net/browse/PROJ-1845` and its IN clone | Jira keys |
| **Requester Name** — the cell to the right of the `Requester Name` label | A `mention` span for the requester | IN `reporter.accountId`, or leave empty |
| **PROJECT TEAM → Engineer** — right of the `Engineer` label | `mention` for the user | `atlassianUserInfo` |
| **PROJECT TEAM → User** — right of the `User` label | `mention` for the requester (same as above) | IN reporter, or empty |
| **Directorate** — the three checkbox cells right of the `Directorate` label | Tick the one matching the IN Directorate (`RISK` → `Risk n Collection`) | IN `customfield_10042` |
| **Departement** — right of the `Departement` label | Text value | IN `customfield_10043` |
| **Type** — the two checkbox cells under the `Type` header | Tick the one matching the IN Type Dev (`Data Analytic` → `Data Analytic`) | IN `customfield_10052` |
| **Scope** — checkbox cell under the `Scope` header | Tick `Internal <COMPANY>` (default) | fixed |
| **CAB → Deployment Methods → PIC** — right of the `PIC` label (the cell holding `mention @`) | `mention` for the user | `atlassianUserInfo` |
| **DDCL Production/Data Operasional** — the "Test Scenario" column of the numbered table under that header | One row per deployment action (see `deployment-types.md`). Fill the Test Scenario column, and put `mention` for the user in the PIC column of each filled row. Fill the Capture Screen column per `deployment-types.md`: `[Attach file: <script file name>]` on repo-script rows, detail plus `[Upload screenshot: …]` on out-of-repo rows; leave unused rows empty. The files themselves are attached by hand (the MCP cannot upload attachments). Add rows if there are more actions than template rows. | release folder, repo docs, user answers |
| **CAB Checklist, item 4 "Source Code Repository sesuai CAB Scope"** — the last empty paragraph in that item's first cell | One block, once per BAST: `Repository:` GitHub URL, `PR:` link (`#NNN`), `Branch:` name. Leave the Lulus/Tidak and Reviewer Comment columns untouched. | `git remote get-url origin`, release `CHANGELOG.md`, `gh` or the merge commit |
| **Scenario Test & Capture** — the "Test Scenario" and "PIC" columns | Inferred scenarios; PIC = the user | release folder |

## Left untouched (owned by others)

| Section | Owner |
| --- | --- |
| Email User; Approver Requester; Email PMO (kept from template) | IT QA / requester |
| Project Team → Data Operasional/Delivery | Data Ops |
| CAB: Deployment Methods (checkboxes), Date, Time, Scale; PAT dates and PIC; IT Change Management (leads CAB, Date CAB); Result CAB; Approver CAB; Notes CAB | IT Change Management |
| Scenario Test → Capture Screen | Engineer, by hand (the MCP cannot upload attachments) |
| UAT & Capture; Scenario PAT & Capture; Approval BAST | User |
| Implementation Detail | Data Ops |
| CAB Checklist (everything except the source-code reference in item 4); Copyright notice | IT / template |

## Template prompts that must disappear from filled cells

After filling, none of these strings may remain in a cell listed under "Filled by this skill":

- `Isi dengan informasi dari kebutuhan perubahan system baru/enhancement yang di minta oleh user/it`
- `Isi dengan copas url epic`
- `mention @`
- the sample date `January 21, 2022` (only if that cell was meant to be filled; the CAB and PAT date cells are intentionally left as template)
