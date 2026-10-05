# What to extract from a sample BAST

Fill this in for each sample, from the cells the engineer owns. Record structure and style, not values. Every item below ends as either a reusable pattern or "not present".

## Description Requirement

- Language and register (for example Bahasa, formal).
- Structure: a summary paragraph only, or summary plus a change list; how many paragraphs.
- What the summary always covers (why, what changes, what it affects).
- How the deployment change is described (which objects are named, whether unchanged parts are stated).
- Rough length (short, medium, long).

## DDCL Production rows

- What one row usually covers (one script, one platform, one action).
- Which lines the row uses (host or workspace, database or schema, schedule or notes, tables, nodes, objects, nested columns or variables) and in what order.
- Which objects are listed for this repo's kind of change, and which are left out.
- Whether a Steps line appears, and whether it added anything the script did not already show.
- Whether the PIC column is filled and with whom (role only, not the name).
- Rows for out-of-repo work (DataWorks, Airflow, Vault, and so on): how they are worded.

## Scenario Test

- The scenarios listed for this kind of change, generalized (for example "generate the payload for the changed variable").
- Wording style (short noun phrase or full sentence).
- Whether Capture Screen holds text or images (record only the type).

## Fields

- Type, Scope, Directorate and Department values, only if they are the same across the samples.
- Which optional cells the engineer consistently fills or leaves empty.

## Things to ignore

- Spec tables in the description (new-variable name, description, source data, example query, "Is mandatory", "Result", "Tujuan"): these are copied from the Jira description or requirement PDF and are deliberately not reproduced by the generator, which lists the changed variables instead.
- The repo link, branch or PR reference in the CAB Checklist: the generator fills it from git, not from a convention.
- Hosts, database names, table names, variable names, dates, people, ticket keys, screenshots, attachments, and any full sentence that would only make sense for that one ticket.
- Anything owned by Data Ops, the user, CAB or IT (Approver, CAB, PAT, UAT, Approval, Implementation).

## Recording format (per sample, internal)

```text
Sample: <ticket key>   Change kind: <e.g. S1 variable update, schema change, pipeline change>
Description: <structure + style notes>
DDCL: <row structure + objects listed + Steps yes/no + PIC role>
Scenario Test: <scenarios, generalized>
Fields: <consistent values>
Conflicts with current rules: <list, or none>
```
