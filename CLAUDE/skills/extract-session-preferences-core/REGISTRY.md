# Preference registry

An evidence ledger kept by the `extract-session-preferences-core` skill. It records every
preference the skill has seen, saved or not, so a candidate can build evidence across
sessions and repos and be promoted (PROJECT -> DOMAIN -> GLOBAL) with the user's approval.
It changes no behavior by itself: only the place named in `Saved in` does.

The data lives in `~/.claude/preference-registry/` (personal, never committed). This file
is copied there as `README.md`. Do not edit the CSVs by hand; use the helper.

```text
~/.claude/preference-registry/
├── registry-shared.csv    approved GLOBAL and DOMAIN records
├── registry-project.csv   PROJECT records, candidates, unresolved conflicts
├── registry-archive.csv   dropped, superseded and retired records
└── README.md
```

A record's `Scope` is its intended scope, not the file it sits in: a DOMAIN candidate stays
in the project file until the user approves it and it is written at that scope.

## Columns

| Column | Meaning |
| --- | --- |
| `ID` | Stable `P-nnn`, never reused, unchanged by promotion or archive |
| `Type` | `positive` or `negative` rule |
| `Category` | Free label, for example `testing` or `docs` |
| `Preference` | One actionable, normalized rule |
| `Keywords` | 3-6 lowercase tags, separated by `;` |
| `Scope` | `GLOBAL`, `DOMAIN` or `PROJECT` (SESSION items are never stored) |
| `Status` | `candidate`, `approved`, `saved`, `conflict`, `dropped`, `superseded` |
| `Confidence` | `High`, `Medium` or `Low` |
| `First seen`, `Last seen` | Dates of independent evidence |
| `Seen` | Number of independent sessions |
| `Session IDs` | Dedup keys, separated by `;` (legacy imports have none) |
| `Repos`, `Domains` | Where the evidence came from, separated by `;` |
| `Evidence` | Short provenance |
| `Explicit evidence` | `yes` when the user stated, corrected or confirmed it |
| `Intended location` | Where the rule should be written |
| `Saved in` | Where it was actually written; required for `saved` |
| `Conflict` | Description of unresolved conflicting evidence |
| `Review trigger` | Why the record needs a second look |

`approved` means the user agreed but nothing is written yet. A row is never proof that a
rule exists in configuration.

## Helper commands

```bash
R=~/.claude/skills/extract-session-preferences-core/registry.py
python3 $R find --keywords confluence,edit-safety [--text "..."] [--repo R] [--domain D] [--archive]
python3 $R add --preference "..." --keywords a,b,c --scope PROJECT --session ID [--repo R] [--explicit]
python3 $R update P-012 --sighting --session ID --repo R [--explicit]
python3 $R update P-012 --status saved --saved-in "where it was written"
python3 $R update P-012 --conflict "what contradicts it"
python3 $R promote P-012 --to DOMAIN --saved-in "where the wider rule was written"
python3 $R archive P-012 --reason "why" --status dropped
python3 $R report
```

- `add` refuses a near-duplicate and shows the existing record; use `--force` only for a
  genuinely different rule.
- `update --sighting` counts each session once. Scope changes only through `promote`.
- `promote` validates the record (approved or saved, no conflict) and the destination,
  and keeps the original row if the move fails.
- `report` lists conflicts, records eligible for promotion, inferred-only candidates,
  approved-but-unwritten rules and records whose intended scope is wider than where they
  are saved. Eligibility is a proposal only.

The helper uses only the standard library and runs on Python 3.9 and newer. Set
`PREF_REGISTRY_DIR` to use another folder (tests do).
