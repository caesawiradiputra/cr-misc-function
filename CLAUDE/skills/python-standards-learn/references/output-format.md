# Output format: an OKF bundle

The standards are an Open Knowledge Format (OKF v0.2) bundle, written by following the `okf-writer` skill (`~/.claude/skills/okf-writer/SKILL.md`: read it before writing, run its spec check, use its templates in `assets/`, lint with its `okf_lint.py`). OKF fits because an agent should open the index, then read only the area it needs, and see where each rule came from and whether anyone reviewed it.

Default location: `docs/standards/` in the template repo (the bundle root).

```text
docs/standards/
  index.md             okf_version "0.2"; map of everything below
  log.md               change history, newest date first
  migration.md         deviations per repo (what each repo still does differently)
  evidence.json        inventory snapshot that `refresh` diffs against (not a concept; no frontmatter)
  evidence.json        the inventory snapshot `refresh` diffs against (not a concept)
  common/              rules for ALL Python project types, one concept per area
    layout.md
    naming.md
    packaging.md
    config-and-secrets.md
    lint-and-typing.md
    tests.md
    docker.md
    ci-and-deployment.md
    logging.md
    docs-and-release.md
  types/               ONLY the delta from common, one concept per type
    airflow-job.md
    fastapi-service.md
    consumer.md
    ...
```

Skip an area file that has no rule. Do not add per-type copies of an area.

## Concept frontmatter

Follow `okf-writer`'s `assets/concept.md`, with these choices:

| Field | Common area file | Type delta file | `migration.md` |
| --- | --- | --- | --- |
| `type` | `Standard` | `Project Type` | `Migration List` |
| `title` | `Common: <Area>` | `<Type> (delta from common)` | `Deviations to migrate` |
| `tags` | `[common, <area>]` | `[type, <type-name>]` | `[migration]` |
| `status` | `draft` until a person reviews it (never set `verified` yourself) | same | same |
| `sources` | one entry per repo consulted for this file: `id`, `resource` (the repo path relative to `~/repo`), `title` | same | same |

The concept's own `resource` is omitted (these are abstract concepts). A `sources[].resource` is a repo path relative to `~/repo`, a document path, or `decision:{date}` for a choice the user made in the session. Cite only sources the body uses (a footnote for each). Set `stale_after` about 6 months after the date learned, because repos change.

## Body of a common area file

A short paragraph (what the area covers, how many repos were read), then one block per rule. IDs are stable so type files, `compare` and reviews can cite them: `C-<AREA>-<NN>` (`LAYOUT`, `NAME`, `PKG`, `CFG`, `LINT`, `TEST`, `DOCKER`, `CI`, `LOG`, `DOCS`).

```markdown
## C-CFG-01 Configuration comes from the environment

**Rule:** Read configuration from environment variables through one settings module; commit a `.env.template` listing key names only.
**Why:** The same image runs in every environment; secrets never enter git or the image.
**Basis:** observed. 11 of the 12 repos that have config (learned YYYY-MM-DD).[^src1]
**Variants:**
- Airflow Variables and Connections. *Use when* the value is read inside a DAG, not inside the image.
```

`Basis` is required and is one of: `observed` (with `n of N`, N being the repos that have the thing), `authoritative` (names the document), `user-decided` (with the date), `best-practice` (no repo shows it; say so) or `seen-once` (needs a yes). Combine when more than one applies. Omit `Variants` when empty. Deviations are not repeated here; they live in `migration.md`. Cite sources with a footnote whose label matches a `sources[].id`.

## Body of a type delta file

```markdown
Applies on top of the common standards ([index](/index.md)). Only differences are listed.
**Repos:** {names} ({n} active). **Status:** full | thin.

## Adds
### T-<TYPE>-<AREA>-<NN> <title>
(same block format as a common rule)

## Overrides
### T-<TYPE>-DOCKER-01 overrides [C-DOCKER-03](/common/docker.md)
Why this type differs (the technical reason).

# Scaffold
Files the `scaffolds/<type>/` overlay adds or replaces, and the dependencies it installs.
```

A thin type has `Status: thin` and a short paragraph, and no `# Scaffold`. A type file never restates a common rule; it links to it.

## `index.md`

Bundle root only carries `okf_version: "0.2"`. Groups: `Common standards`, `Project types` (with status), `Migration`. Each link has a one-line description. Start with two sentences: what the bundle is and "read the common file for the area you need, then the type file for the project type".

## `log.md`

One `## YYYY-MM-DD` heading per run, entries starting **Add**, **Update** or **Refresh**, which repos were read, what changed, "Unverified" for new content.

## Writing rules

- Plain, specific, checkable. A rule a reviewer can test beats advice.
- Object names, paths and commands in backticks. English technical terms.
- The common layer is the single source of truth: no restating, only linking.
- Patterns only: no hosts, table names, secrets or people's names. Repo names appear only in `sources`, the `Repos:` line of a type file and `migration.md`, and only when the target repo is private (check `gh repo view --json isPrivate`); in a public repo use placeholders such as `repo-a`.
- Quote free-text frontmatter values (`title`, `description`, `sources[].resource` and `title`) as double-quoted strings: an unquoted value containing `: ` is invalid YAML even though `okf_lint.py` accepts it.
- Markdown hygiene: a blank line around every heading and list, `**Rule:**`/`**Why:**`/`**Basis:**` each as its own paragraph (consecutive lines merge when rendered), no double blank lines, American spelling, and `Basis`/footnote ids that are real words.
- Spell check: put general Python and Docker terms in a root `cspell.json` and project or domain words in `docs/standards/cspell.json` (importing the root one), and ignore `evidence.json`.
- Fix every error from `okf_lint.py`, the YAML parse and the markdown lint before reporting.
