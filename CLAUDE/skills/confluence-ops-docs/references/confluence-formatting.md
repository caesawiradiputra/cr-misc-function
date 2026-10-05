# Confluence Formatting Conventions

These are markdown conventions chosen because they survive Markdown→Confluence
conversion cleanly and because they read well for scanning under pressure
(the runbook use case) as well as leisurely reading (the overview use case).

## Headings

Strict hierarchy: H1 for the page title only, H2 for major sections, H3 for
subsections. Never skip a level (no H1 straight to H3). Confluence's page
tree and "on this page" navigation both derive from heading structure, so a
broken hierarchy shows up as a visibly broken nav, not just a style nit.

## Cross-page links

At the top of every child page, link back to its parent and list sibling
pages:

```markdown
**Related pages**: [Overview](system-overview) | [Architecture](system-architecture) | [Operations](system-operations)
```

At the bottom, a simple previous/next if there's a natural reading order:

```markdown
---
**Previous**: [Overview](system-overview) | **Next**: [Architecture](system-architecture)
```

Omit both for a standalone single page — there's nothing to navigate to.

## Code blocks

Always specify a language, even for plain output:

````markdown
```bash
kubectl logs -n privis job/pull-data
```

```text
[2026-07-06 10:03:12] INFO  pull_data started
```
````

Only include a code block when the reader will actually run or read that
exact text (a runbook command, a real log line, a config snippet). Don't add
code blocks to illustrate architecture — use the processing-flow description
or an ASCII diagram instead.

## Tables

```markdown
| Header 1 | Header 2 |
| --- | --- |
| Data A | Data B |
```

Keep tables narrow enough to read without horizontal scrolling in Confluence's
default page width — if a table needs more than ~4-5 columns, consider
whether it should be two tables or a list instead.

## Callouts

```markdown
> **Note**: Non-critical context worth flagging.

> **Warning**: Something that will cause real harm if missed (data loss,
> outage, security exposure).

> **Tip**: A shortcut or best practice.
```

Use sparingly — a page where every third paragraph is a callout has no
signal left in the noise. Reserve **Warning** for things that are actually
dangerous to get wrong.

## Diagrams

Reach for a diagram when it replaces several paragraphs of prose the reader
would otherwise have to reconstruct in their head — not as decoration.
Diagrams worth generating usually fall into one of these:

- **Processing flow** — ordered steps in a pipeline
- **System context** — this system plus the external actors/systems around
  its boundary
- **Data flow** — how data moves and transforms between components
- **Sequence** — the order of calls/events for a specific scenario worth
  walking through step by step
- **Component relationship** — how internal pieces depend on each other

Prefer simple ASCII for all of them. A processing flow is usually just:

```text
pull_data → prepare_data → run_clustering → export_outputs → sync
```

For branching or multi-system flows, a slightly more elaborate ASCII box
diagram is fine, but don't over-invest — Confluence renders these as
plain text, so intricate box-drawing often looks worse than a short
numbered list. If a diagram is trying to show more than about 6-8
nodes/edges, it's usually clearer as a table or a short ordered list
instead.

Generate at most one diagram per major section unless a second one clearly
earns its place — a page with a diagram after every paragraph stops being
a diagram-supported page and starts being a picture book.

## Lists

Cap bullet lists at around 5 items before splitting into sub-groups or a
table — a 15-item bullet list reads as noise, not structure.

## Spacing

Blank line after every heading, and blank lines before and after code
blocks, tables, and blockquotes. Confluence's markdown importer is picky
about this — missing blank lines around a table is a common cause of a
table rendering as a wall of pipe characters.
