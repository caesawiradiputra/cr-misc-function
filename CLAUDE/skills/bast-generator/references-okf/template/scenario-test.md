---
type: Template Cell
title: Scenario Test & Capture
description: The Test Scenario and PIC columns of the Scenario Test table; scenarios are inferred from the release folder.
tags: [bast, template, engineer-owned]
generated:
  by: claude-code/sonnet-5.5
  at: 2026-10-12T23:22:08+07:00
status: draft
---

Fill the "Test Scenario" and "PIC" columns with inferred scenarios; PIC is the user (`atlassianUserInfo`). Infer from the release folder: a change to an S1 variable gets "Generate Payload to S1", a schema change gets a row that verifies the schema.

Leave Capture Screen empty (the engineer adds it by hand). If nothing can be inferred, leave the section empty rather than inventing scenarios.
