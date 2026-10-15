# OKF v0.2 in one page

Source: the `SPEC.md` of the Open Knowledge Format repository (Google Cloud, June 2026).
Re-read the spec before relying on a detail; the format can change between minor versions.

## Frontmatter

| Field | Status | Rule |
| --- | --- | --- |
| `type` | Required | Non-empty string; free text, consumers must tolerate unknown values |
| `title`, `description` | Recommended | Display name; one sentence |
| `resource` | Recommended | Canonical URI of the underlying asset; absent for abstract concepts |
| `tags` | Recommended | YAML list of short strings |
| `generated` | Optional | `by` (required) and `at`: who wrote the current content |
| `verified` | Optional | List of `{ by, at }`: who confirmed it (a bare map counts as one item) |
| `status` | Optional | `draft`, `stable` or `deprecated`; absent means `stable` |
| `stale_after` | Optional | Absolute datetime; stale at or after it |
| `sources` | Optional | List with a required `resource`; optional `id`, `title`, `author`, `usage_count`, `last_modified` |

- Extra keys are allowed. Consumers must keep unknown keys when rewriting a file.
- Timestamps are ISO 8601 with an explicit UTC offset.
- Actors: `<producer>/<version>` for tools, `human:<id>` for people, `process:<id>` for jobs.
- Trust tier is derived: no `verified` = unverified; only non-human actors = machine-confirmed;
  any `human:` actor = human-reviewed. Credibility scores are not stored.

## Layout

- A bundle is a folder tree; structure is up to the producer.
- `index.md` and `log.md` are reserved at any level and are never concepts.
- `index.md`: no frontmatter except `okf_version: "0.2"` at the bundle root; headings group
  bulleted links, each with a short description.
- `log.md`: `## YYYY-MM-DD` headings, newest first, prose entries; a leading bold word such
  as **Update** is conventional.
- Links are plain Markdown links; absolute ones start with `/` and are relative to the
  bundle root (recommended). Broken links are tolerated and may mark knowledge not written yet.
- Per-claim attribution: footnotes whose labels match `sources[].id`.
- Conventional body headings: `# Schema`, `# Examples`, `# Computation`.

## Conformance

Every non-reserved `.md` has parseable frontmatter with a non-empty `type`; `index.md` and
`log.md` follow their structure. Consumers must not reject a bundle for missing optional
fields, unknown types or keys, broken links or a missing `index.md`.
