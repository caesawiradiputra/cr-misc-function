---
type: Checklist
title: Template prompts that must disappear
description: Strings that may not remain in any cell the skill was supposed to fill; used for the post-edit sweep.
tags: [bast, template, verification]
generated:
  by: claude-code/sonnet-5.5
  at: 2026-10-12T23:22:08+07:00
status: draft
---

After filling, none of these strings may remain in a cell the skill fills (see [Description requirement](/template/description-requirement.md), [Epic key](/template/epic-key.md), [CAB fields](/template/cab-fields.md)):

- `Isi dengan informasi dari kebutuhan perubahan system baru/enhancement yang di minta oleh user/it`
- `Isi dengan copas url epic`
- `mention @`
- the sample date `January 21, 2022` (only if that cell was meant to be filled; the CAB and PAT date cells are intentionally left as template)
