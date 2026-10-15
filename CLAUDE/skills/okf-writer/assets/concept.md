---
type: <Type, for example Table, Rule, Pipeline Node, Business Rule>
title: <Display name>
description: <One sentence on what this is and who uses it.>
resource: <canonical URI or identifier of the underlying asset; remove this line for an abstract concept>
tags: [<domain>, <layer>]
generated:
  by: claude-code/<model>
  at: <YYYY-MM-DDTHH:MM:SS+07:00>
status: draft
sources:
  - id: src1
    resource: <path or URL the claims come from>
---

<What it is, in two or three sentences. Facts only, each traceable to a source.>

# Schema

| Column | Type | Meaning |
| --- | --- | --- |
| `<column>` | `<type>` | <What it means>[^src1]. |

# Examples

<A short, real example: a query, a row, a call.>

[^src1]: <Where this claim comes from.>
