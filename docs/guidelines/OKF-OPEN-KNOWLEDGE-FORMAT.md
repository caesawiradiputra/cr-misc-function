# Open Knowledge Format (OKF): Reference and Fit for This Repo

A reference for the Open Knowledge Format (OKF), plus an assessment of where it would, and would not, improve the skills, documents and templates in this repo. Written 2026-10-14 from the sources in section 9. Re-check the spec before relying on a detail here: OKF is young and still changing.

## 1. What OKF is

OKF is a vendor-neutral file format for knowledge that AI agents read. A **bundle** is a folder tree of Markdown files. Each file describes one concept and starts with YAML frontmatter. Google Cloud published it in June 2026, building on the "LLM Wiki" pattern. The version reviewed here is **v0.2**. The canonical home of the spec is the `GoogleCloudPlatform/open-knowledge-format` repository (`SPEC.md`). The older `knowledge-catalog/okf` copy is a frozen snapshot.

It defines no registry, no central authority and no required tooling. Only one frontmatter key is always required.

## 2. The format in brief (v0.2)

### 2.1 Frontmatter

| Field | Status | Rule |
| --- | --- | --- |
| `type` | Required | Non-empty string. Values are not centrally registered; consumers must tolerate unknown types. |
| `title` | Recommended | Display name. |
| `description` | Recommended | One-sentence summary. |
| `resource` | Recommended | Canonical URI of the underlying asset (a table, a file, a page). Absent for abstract concepts. |
| `tags` | Recommended | YAML list of short strings. |
| `generated` | Optional | Map with `by` (required) and `at` (datetime): who wrote the current content. |
| `verified` | Optional | List of `{ by, at }`: who confirmed it. Kept separate from `generated` on purpose. |
| `status` | Optional | `draft`, `stable` or `deprecated`. Absent means `stable`. |
| `stale_after` | Optional | Absolute datetime. The concept is stale at or after that instant. |
| `sources` | Optional | List of entries, each with a required `resource`; optional `id`, `title`, `author`, `usage_count`, `last_modified`. |

Rules that apply everywhere:

- Producers may add extra keys. Consumers must not reject unknown keys and should keep them when rewriting a file.
- Timestamps are ISO 8601 with an explicit UTC offset.
- The actor convention for `by` and `author` is `<producer>/<version>` for tools, `human:<id>` for people and `process:<id>` for automated jobs.
- Trust tiers are derived, not stored: no `verified` means unverified; only non-human actors means machine-confirmed; any `human:` actor means human-reviewed. They are advisory, not access control.
- Credibility scores are deliberately not stored.

### 2.2 Body and layout

- No body section is required. Conventional headings are `# Schema`, `# Examples` and `# Computation`. Per-claim attribution uses Markdown footnotes whose labels match `sources[].id`.
- Folder structure is up to the producer. `index.md` and `log.md` are **reserved** at any level and are never concept documents.
- `index.md` groups bulleted links with short descriptions, so a reader can open one level at a time (progressive disclosure). It normally has no frontmatter, except that the bundle root may carry `okf_version: "0.2"`.
- `log.md` is a date-grouped change history, newest first, with `YYYY-MM-DD` headings and prose entries.
- Links are plain Markdown links. Absolute links start with `/` and are relative to the bundle root (recommended). Links are untyped; the surrounding prose says what the relationship is. Broken links are tolerated because they can stand for knowledge not written yet.
- A `references/` folder is a naming convention for external material.

### 2.3 Conformance

A bundle is conformant when every non-reserved `.md` file has parseable frontmatter with a non-empty `type`, and any `index.md` or `log.md` follows its structure. Consumers must not reject a bundle for missing optional fields, unknown types or keys, broken links or a missing `index.md`.

There is also an optional `type: Attested Computation` for runnable definitions (a `runtime` key, parameters, an executor and an attester). Agents may supply parameter values but must not edit the computation. It is not needed for documentation work.

## 3. What it is good at

- **One concept per file, with a machine-readable header.** An agent can find a table, a rule or a pipeline by `type`, `tags` or `resource` without parsing prose.
- **Progressive disclosure.** `index.md` lets an agent load a map first and open only the concept it needs. That is the same idea this repo's skills use with `references/` files, applied to knowledge instead of procedures.
- **Provenance and freshness built in.** `sources`, `generated`, `verified`, `status` and `stale_after` answer "where did this come from, who checked it, is it still current?", which flat Markdown cannot say.
- **Plain files in git.** Reviewable, diffable, no service to run. A bundle can live in a repo or a subfolder.
- **Tolerant by design.** Extra keys and broken links do not break consumers, so adoption can be gradual.

## 4. Where it fits in this repo

| Asset | Verdict | Reason |
| --- | --- | --- |
| `SKILL.md` files | Do not convert | Claude Code requires its own frontmatter (`name`, `description`). OKF's `type` is not a replacement. Keep skills as they are. |
| `commands/*.md` | Do not convert | Same: they follow the Claude Code command format. |
| Global and repo `CLAUDE.md` | Keep, but link to a bundle | They are instructions loaded every session. Put long reference knowledge in a bundle and point to its `index.md`, so it is loaded only when needed. |
| System and pipeline documentation (`confluence-ops-docs` output) | **Good fit** | Each table, node, workflow, API or business rule is a concept with a `resource`, `sources` and a freshness date. The skill could emit an OKF bundle in the repo, then publish pages from it. |
| CDE registry (`/generate-cde`, `/update-cde`) | **Good fit** | One concept per critical data element, with `resource` pointing at the table or column, `sources` for lineage, and `verified` for a data owner's sign-off. Better provenance than a spreadsheet. |
| `release/<TICKET>/CHANGELOG.md` | Keep | It is a per-release record in a fixed shape that other tooling reads. OKF's `log.md` is similar but not a replacement. |
| `docs/guidelines/*.md` (standards) | Partial | Worth adding `status` and `stale_after`-style fields for freshness; no need for a full bundle. |
| Preference registry (CSV) | Keep CSV, borrow vocabulary | It is a ledger of rows with counters and a lifecycle, not a set of documents. Borrow the actor convention (`human:<id>`), the trust idea (explicit versus inferred evidence) and `status` wording. See section 6. |
| Logbook (CSV) | Keep | Tabular time series, not knowledge documents. |

Short version: OKF helps with **knowledge about the data and systems** the agents work on. It does not help with **instructions to the agent** (skills, commands, `CLAUDE.md`), which already have their own formats.

## 5. Recommended adoption

Start small and measure before converting anything.

1. **Pilot in one repo.** Create `docs/knowledge/` as an OKF bundle for one pipeline: an `index.md`, a `log.md`, and one concept file per table or node. Use the template in section 8.
2. **Point agents at it.** Add two lines to that repo's `CLAUDE.md` (or `AGENTS.md`) saying where the bundle is and to read `index.md` first. Without this pointer nothing loads it.
3. **Teach the existing skills to emit it.** `confluence-ops-docs` and the CDE commands are the natural producers. Add an optional "write an OKF bundle" step; keep the current output as the default until the pilot proves useful.
4. **Fill the trust fields honestly.** `generated.by` is the tool (`claude-code/<model>`), `verified` is added only after a person has reviewed the concept (`human:<id>`), and `stale_after` is set where the source changes on a schedule.
5. **Add a lint check.** The upstream repo documents no validator. A 50-line script that checks frontmatter and a non-empty `type` per file is enough to enforce conformance; add it to CI only for repos that adopt a bundle.

## 6. What to borrow without adopting the format

These cost almost nothing and help even where no bundle exists:

- **Separate "who wrote it" from "who checked it".** Applied to the preference registry as `Explicit evidence` and to docs as a `verified` line.
- **Status and freshness on long-lived documents.** `status: draft|stable|deprecated` and a stale-after date on standards and runbooks, so an out-of-date page is visibly out of date.
- **Footnote-style provenance.** Cite sources next to claims in generated documentation instead of one list at the end.
- **A map file and a change log per documentation folder.** `index.md` plus `log.md` is a cheap convention for any docs folder.

## 7. Limits and caveats

- **Young and single-vendor.** v0.2, published June 2026 by Google Cloud. The format can change between minor versions; a bundle can declare `okf_version` to pin it.
- **No validator upstream.** The repository documents a reference producer agent and an HTML viewer, not a linter.
- **Not an instruction format.** It says what the knowledge is, not how an agent should behave.
- **Verification of this document.** The spec fields in section 2 come from the v0.2 `SPEC.md` as summarised by a fetch tool, not read byte for byte. The wider description comes from secondary articles. Check `SPEC.md` directly before writing a validator or a skill that depends on exact field rules.

## 8. Starter template

Bundle layout:

```text
docs/knowledge/
├── index.md              # map of the bundle; may declare okf_version
├── log.md                # date-grouped change history, newest first
├── tables/
│   └── <table-name>.md   # one concept per file
└── references/           # external material (optional)
```

`index.md`:

```markdown
---
okf_version: "0.2"
---

# <Bundle title>

## Tables

- [<table-name>](/tables/<table-name>.md): one-line description
```

A concept file:

```markdown
---
type: Table
title: <table-name>
description: One sentence on what the table holds and who uses it.
resource: <project>.<schema>.<table-name>
tags: [<domain>, <layer>]
generated:
  by: claude-code/<model>
  at: 2026-10-14T10:00:00+07:00
verified:
  - by: human:<id>
    at: 2026-10-15T09:30:00+07:00
status: stable
stale_after: 2027-01-14T00:00:00+07:00
sources:
  - id: src1
    resource: /references/<source-doc>.md
---

# Schema

| Column | Type | Meaning |
| --- | --- | --- |
| `<column>` | `<type>` | What it means[^src1]. |

# Examples

A short, real example query or row.

[^src1]: Where this claim comes from.
```

`log.md`:

```markdown
# Change log

## 2026-10-14

**Update** Added `<table-name>` and its schema.
```

## 9. Sources

- Spec: [`GoogleCloudPlatform/open-knowledge-format`, `SPEC.md` (v0.2)](https://github.com/GoogleCloudPlatform/open-knowledge-format/blob/main/SPEC.md)
- Repository README: [`GoogleCloudPlatform/open-knowledge-format`](https://github.com/GoogleCloudPlatform/open-knowledge-format)
- Frozen early copy: [`GoogleCloudPlatform/knowledge-catalog`, `okf/`](https://github.com/GoogleCloudPlatform/knowledge-catalog/tree/main/okf)
- Secondary: [heise: Open Knowledge Format](https://heise.de/-11332310), [noqta: Google Cloud OKF](https://noqta.tn/en/news/google-cloud-open-knowledge-format-okf-ai-agents-2026), [dev.to: OKF explained](https://dev.to/turva-dev/open-knowledge-format-okf-explained-4i8b), [GitBook: What is OKF?](https://www.gitbook.com/blog/what-is-okf-open-knowledge-format) (not readable when checked)
