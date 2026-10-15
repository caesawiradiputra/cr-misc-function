---
name: okf-writer
description: Create, update or check an Open Knowledge Format (OKF) bundle, a folder of Markdown concept files with YAML frontmatter plus index.md and log.md, that documents tables, pipeline nodes, business rules, systems or other knowledge an agent should read. Use whenever the user says "write an OKF bundle", "document this as OKF", "knowledge bundle", "put this in docs/knowledge", "add a concept for table X", "update the OKF index or log", "lint the bundle", "convert this reference to OKF", or asks for agent-readable knowledge documentation with provenance and freshness, even if they do not say "OKF". Not for SKILL.md files, slash commands, CLAUDE.md, release CHANGELOG.md files or CSV ledgers; those keep their own formats.
---

# OKF writer

Writes knowledge about data and systems as an OKF v0.2 bundle: one concept per Markdown file, a machine-readable frontmatter header, an `index.md` map and a `log.md` change history. The point is that an agent opens the index, then only the concept it needs, and can see where each claim came from, who checked it and whether it is still current.

Spec summary: `references/okf-v0.2-summary.md`. Templates: `assets/`. Linter: `scripts/okf_lint.py`. Spec watcher: `scripts/okf_watch.py`. Background and fit for this repo: `docs/guidelines/OKF-OPEN-KNOWLEDGE-FORMAT.md` in `cr-misc-function`.

## Hard rules

1. **Facts only, each traceable.** Write only what the sources show (code, DDL, release docs, Confluence pages, query results the user gave you). Never invent a column, a rule, an owner or an example. If a fact is unknown, leave it out or write `Unknown: <what>`; do not guess.
2. **`generated` is the tool, `verified` is a person.** Set `generated.by` to `claude-code/<model>` (for example `claude-code/sonnet-5.5`) and `generated.at` to now with a UTC offset. Add a `verified` entry only when the user says they reviewed that concept, and use their id as `human:<id>`. Never add `verified` yourself, and never copy a `verified` entry onto content you changed.
3. **New content is `status: draft`** until a human has reviewed it. Use `deprecated` for a retired concept and keep the file.
4. **Round-trip unknown keys.** When you edit an existing concept, keep every key you do not own (extra keys, `verified`, `sources`). Change only what the request names.
5. **Edited content is no longer verified.** If you change a concept that has `verified`, say so in the summary: the review no longer covers the new text. Leave the old entry in place and ask the user whether to re-verify.
6. **Read before you write.** Check the bundle for an existing file first (Execution Discipline: check state before writing). Never overwrite a concept the user may have edited; read it and change it in place.
7. **`index.md` and `log.md` are reserved.** They never carry concept keys. Only the bundle-root `index.md` may carry `okf_version: "0.2"`.
8. **No company or personal data in a public repo.** Before writing into a public repository, use placeholders for site names, account ids, internal hostnames and real customer data. Check with `gh repo view --json isPrivate` when unsure.
9. **Object names in backticks, technical terms in English** (global Markdown Style rules), also inside Bahasa prose.

## Keeping up with the spec

OKF is young (v0.2 at the time of writing) and the upstream repository publishes no releases, so the skill watches the history of `SPEC.md`.

```bash
python3 ~/.claude/skills/okf-writer/scripts/okf_watch.py check --max-age 14   # before writing a bundle
python3 ~/.claude/skills/okf-writer/scripts/okf_watch.py status               # age of the last check
python3 ~/.claude/skills/okf-writer/scripts/okf_watch.py ack                  # after the skill matches the spec
```

- **Before writing or updating a bundle**, run `check --max-age 14`. It skips the fetch when the last check is under 14 days old, so it costs nothing on a busy week.
- **Exit code 10 means the spec changed** since the last reviewed commit. Tell the user what changed (the script lists the commits and the compare link) before you write anything, and ask whether to update the skill first.
- **To update the skill after a change:** read the new `SPEC.md` (the compare link shows the diff), then update `references/okf-v0.2-summary.md` (rename it when the major or minor version changes), `scripts/okf_lint.py` and its tests, the templates in `assets/`, and `docs/guidelines/OKF-OPEN-KNOWLEDGE-FORMAT.md` in `cr-misc-function`; mirror the skill into the template. Run `ack` only after that, because `check` keeps reporting the change until you do.
- **A fetch failure (exit 2) is not a reason to stop.** Say the check could not run (the corporate proxy may be unreachable off the office network) and continue with the current rules.
- The state lives in `~/.claude/state/okf-watch.json` and is never committed.

## Workflow

### 1. Scope the bundle

- Ask only what you cannot infer: what the bundle documents, who reads it, and the folder. Default folder: `docs/knowledge/` in the repo.
- If the folder exists, read its `index.md` and `log.md` first and follow its structure, concept types and tag vocabulary instead of inventing new ones.
- Pick one concept per file. Good concepts: a table, a view, a pipeline or DataWorks node, a business rule, an API endpoint, a deployment type, a glossary term. Group files in folders by kind (`tables/`, `rules/`, `pipelines/`).

### 2. Gather the sources

- Read the actual sources for each concept (DDL, code, config, release folder, the page the user pointed at). List them; each becomes a `sources` entry.
- Check the cost before a large read (global rule): prefer local files and targeted queries over whole Confluence pages.

### 3. Write the concept files

Start from `assets/concept.md`.

- `type`: free text, Title Case, reused from the existing bundle when possible (`Table`, `Rule`, `Pipeline Node`, `Deployment Type`).
- `title`, `description` (one sentence), `tags` (short, lowercase), `resource` (the canonical identifier of the asset, such as `project.schema.table`; omit for abstract concepts).
- `generated`, `status: draft`, `sources` with an `id` for each source you cite.
- Body: a short factual paragraph, then conventional headings where they fit (`# Schema`, `# Examples`, `# Computation`). Cite a claim with a footnote whose label matches a `sources[].id`.
- Link other concepts with absolute links (`/tables/other.md`). A link to a concept you have not written yet is allowed; mention it in the summary.
- Set `stale_after` only when the source changes on a schedule or is known to expire; pick a concrete date.

### 4. Update the map and the history

- Add each new concept to the right group in `index.md` with a one-line description. Create `index.md` from `assets/index.md` if the folder has none. Add a group for a new folder.
- Add an entry under today's `## YYYY-MM-DD` heading in `log.md` (newest date first; create the heading if today is not there): what was added or changed and from which sources. Say "Unverified" for new content. Create `log.md` from `assets/log.md` if missing.

### 5. Lint

```bash
python3 ~/.claude/skills/okf-writer/scripts/okf_lint.py <bundle folder>
```

Fix every error. Fix warnings unless there is a reason (a deliberate link to a concept not yet written); report the ones you leave. `--strict` turns warnings into failures, useful in CI.

### 6. Point agents at the bundle

A bundle nobody is told about is never read. Offer to add two lines to the repo's `CLAUDE.md` (or `AGENTS.md`): where the bundle is, and "read `index.md` first, then only the concepts the task needs". Add them only after the user agrees.

### 7. Report

Tell the user, briefly:

- the files created or changed, and the concept count;
- the lint result;
- the trust summary (the linter prints unverified, machine-confirmed and human-reviewed counts);
- anything unknown or left out, and any `verified` entry that no longer covers edited text;
- the logbook row, if the work finished a ticket (propose it, do not write it unasked).

## Updating and checking an existing bundle

- **Update:** read the concept, apply the change, refresh `generated.at` only if you rewrote the content, add a `log.md` entry, run the linter.
- **Check only:** run the linter and summarize; do not edit.
- **Convert an existing reference** (a long Markdown file) into a bundle: split it by concept, keep the wording, record the original path in `sources`, mark everything `draft` and "Unverified" in the log, and keep the original until the user has compared the two.

## What not to do

- Do not convert `SKILL.md`, commands or `CLAUDE.md`: Claude Code requires its own frontmatter there.
- Do not add credibility scores, trust tiers or ratings as fields; they are derived from `verified`.
- Do not create a concept per section of prose; one file per thing that has its own name.
- Do not leave template placeholders (`<...>`) in any file.
