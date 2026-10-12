---
type: Rule
title: Capture Screen cell
description: What goes in the Capture Screen cell of a DDCL row: script attachment placeholder or screenshot placeholder.
tags: [bast, ddcl, capture-screen]
generated:
  by: claude-code/sonnet-5.5
  at: 2026-10-12T23:22:08+07:00
status: draft
---

- **Out-of-repo changes** get group detail that does not fit the Test Scenario cell (for example an image repository and tag) and a placeholder of the form `[Upload screenshot: <what to capture>]`, for example the DataWorks pipeline that will be deployed.
- **Rows for scripts that live in the repo** (Postgres scripts and similar) get a placeholder for the script file itself, `[Attach file: <script file name>]`, because Data Ops does not check the repo, so the file is attached to the row. Repo-script rows do not get a screenshot placeholder.
- The placeholder is a reminder for the engineer and is deleted after the file or screenshot is uploaded (the MCP cannot upload attachments).
- Anything unknown becomes `⚠ TO CONFIRM: <what>` inside the row.
