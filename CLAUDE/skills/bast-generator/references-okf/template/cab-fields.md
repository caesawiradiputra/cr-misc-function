---
type: Template Cell Group
title: CAB fields filled by the engineer
description: Deployment Methods PIC, and the source-code reference (repository, PR, branch) in CAB Checklist item 4.
tags: [bast, template, engineer-owned, cab]
generated:
  by: claude-code/sonnet-5.5
  at: 2026-10-12T23:22:08+07:00
status: draft
---

| Anchor | Fill | Source |
| --- | --- | --- |
| **CAB → Deployment Methods → PIC**: right of the `PIC` label (the cell holding `mention @`) | `mention` for the user | `atlassianUserInfo` |
| **CAB Checklist, item 4 "Source Code Repository sesuai CAB Scope"**: the last empty paragraph in that item's first cell | One block, once per BAST: `Repository:` GitHub URL, `PR:` link (`#NNN`), `Branch:` name. Leave the Lulus/Tidak and Reviewer Comment columns untouched. | `git remote get-url origin`, release `CHANGELOG.md`, `gh` or the merge commit |

Everything else in the CAB Checklist stays untouched, see [Left untouched](/template/left-untouched.md).
