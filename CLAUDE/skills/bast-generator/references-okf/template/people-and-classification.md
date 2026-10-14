---
type: Template Cell Group
title: People and classification cells
description: Requester, Engineer, User, Directorate, Departement, Type and Scope cells, each with its anchor, fill and Jira source.
tags: [bast, template, engineer-owned, jira]
generated:
  by: claude-code/sonnet-5.5
  at: 2026-10-12T23:22:08+07:00
status: draft
---

Field values (Directorate, Department, Type, requester) always come from Jira, never from a conventions section. Without a clones link, leave requester, Directorate, Department and Type empty and say so in the preview.

| Anchor | Fill | Source |
| --- | --- | --- |
| **Requester Name**: cell right of the `Requester Name` label | A `mention` span for the requester | IN `reporter.accountId`, or leave empty |
| **PROJECT TEAM → Engineer**: right of the `Engineer` label | `mention` for the user | `atlassianUserInfo` |
| **PROJECT TEAM → User**: right of the `User` label | `mention` for the requester (same as above) | IN reporter, or empty |
| **Directorate**: the three checkbox cells right of the `Directorate` label | Tick the one matching the IN Directorate (`RISK` → `Risk n Collection`) | IN `customfield_10042` |
| **Departement**: right of the `Departement` label | Text value | IN `customfield_10043` |
| **Type**: the two checkbox cells under the `Type` header | Tick the one matching the IN Type Dev (`Data Analytic` → `Data Analytic`) | IN `customfield_10052` |
| **Scope**: checkbox cell under the `Scope` header | Tick `Internal <COMPANY>` (default) | fixed |

Mentions are `data-type="mention"` spans with `data-user-id` set to an accountId: the requester's from Jira, the engineer's from `atlassianUserInfo` (fetch at runtime, never hardcode). Do not mention anyone else. Tick a checkbox by adding the `checked` attribute to its `<input type="checkbox">`.
