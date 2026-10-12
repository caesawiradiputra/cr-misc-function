---
type: Template Cell Group
title: Cells left untouched
description: Template sections owned by Data Ops, the user, CAB and IT; never filled, no placeholders.
tags: [bast, template, ownership]
generated:
  by: claude-code/sonnet-5.5
  at: 2026-10-12T23:22:08+07:00
status: draft
---

Empty means empty: do not put placeholders in these cells. The one exception is the source-code reference in [CAB fields](/template/cab-fields.md).

| Section | Owner |
| --- | --- |
| Email User; Approver Requester; Email PMO (kept from template) | IT QA / requester |
| Project Team → Data Operasional/Delivery | Data Ops |
| CAB: Deployment Methods (checkboxes), Date, Time, Scale; PAT dates and PIC; IT Change Management (leads CAB, Date CAB); Result CAB; Approver CAB; Notes CAB | IT Change Management |
| Scenario Test → Capture Screen | Engineer, by hand (the MCP cannot upload attachments) |
| UAT & Capture; Scenario PAT & Capture; Approval BAST | User |
| Implementation Detail | Data Ops |
| CAB Checklist (everything except the source-code reference in item 4); Copyright notice | IT / template |

Lozenges such as `DI ISI OLEH IT QA` and `DI ISI OLEH engineer` stay as they are; they are part of the template.
