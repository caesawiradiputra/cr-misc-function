---
name: python-standards-learn
description: Learn how the user actually codes and organizes Python projects by reading the repos under ~/repo, then build a standards set (an OKF knowledge bundle) - ONE common rule set shared by every project type plus a small per-type delta (airflow job, FastAPI service, consumer, streamlit, crawler/batch, agent/MCP, ...) - covering folder layout, naming, config and secret handling, tests, lint/typing, Docker and CI/deployment. It compares existing repos against the baseline, adopts the best practice, keeps conditional alternatives as "use when" variants, and proposes scaffold changes for the python template repo. Use whenever the user says "/python-standards-learn", "learn how I code", "learn my project conventions", "standardize my python repos", "baseline rules per project type", "compare this repo to our standard", "refresh the standards", or asks what the common structure of their FastAPI/airflow/consumer repos is, even if they never say "skill" or "standards".
---

# Python Standards Learn

Reads the user's existing Python repos (read-only), distils what they consistently do, and writes a **two-layer standard** as an OKF bundle (`docs/standards/` in the template repo, written by following the `okf-writer` skill):

1. `common/<area>.md`: the rules that apply to every Python project type, one concept per area. Anything shared (naming, config and secrets, lint, typing, tests, Docker and CI basics, repo hygiene) lives here once.
2. `types/<type>.md`: per type, **only what differs** from common (extra folders, entrypoint, `Dockerfile` CMD, health endpoint, type-specific tests). A per-type file never repeats a common rule; it links to it by ID.

Why two layers: a rule written in three places drifts in three ways. Centralising keeps each rule in one place, and a type file stays short enough to read in a minute. Why OKF: an agent opens `index.md`, reads only the area it needs, and can see each rule's sources and whether a person has reviewed it.

Reference files (read when the step says so): `references/dimensions.md` (what to extract), `references/decision-rules.md` (adopt, variant or drop), `references/output-format.md` (the OKF bundle layout and rule format). Script: `scripts/inventory.py`. Writing the bundle also uses `~/.claude/skills/okf-writer/` (its `SKILL.md`, `assets/` and `scripts/okf_lint.py`).

## Hard rules

1. **Read-only on the analysed repos.** Never check out, pull, edit, or run their code. Use `git log`/`show`/`ls-files`. The script and your own commands must not write inside any repo.
2. **No secrets, no values.** Never open `.env`, credential or key files. Record the *mechanism* (env var, `.env.template`, mounted file, Airflow Variable) and key *names* at most. No hosts, table names, tokens, or people's names go into the standards. Repo names appear only in `sources`, the `Repos:` line of a type file and `migration.md`, and only if the target repo is private (`gh repo view --json isPrivate`); otherwise use placeholders such as `repo-a`.
3. **Authoritative sources win over old repos.** The existing Docker Image CI standard (`cr-misc-function/docs/guidelines/DOCKER-IMAGE-CI-STANDARD.md`), the shared `ruff.toml`/`mypy.ini` templates and the user's `~/.claude/CLAUDE.md` rules are the starting baseline. A repo that conflicts is recorded as a *deviation to migrate*, not as evidence for a new rule.
4. **Evidence, then the user decides contested items.** Every rule carries its evidence (`n of N repos`, where N is the repos that have the thing, and recency) and a `Basis`. Anything that is not clear-cut (see `references/decision-rules.md`) is shown to the user and waits for a yes. Do not silently pick between two real alternatives.
5. **Common first.** Put a rule in a type doc only if at least one type genuinely differs from the common choice. When types differ for a technical reason, that reason is the rule.
6. **No write before approval, no commit.** Show the proposal, wait for an explicit yes per part (common, each type, scaffold changes), write only under the standards folder, show `git diff`, leave it uncommitted.
7. **OKF rules apply to the bundle.** New files are `status: draft`; `generated` names the tool; `verified` is added only when the user says they reviewed that file, never by you. Follow `okf-writer` for frontmatter, `index.md`, `log.md` and linting. `SKILL.md` files themselves are not OKF.

## Modes

- `learn` (default): build or rebuild the standards from the repos.
- `refresh`: re-run the inventory, diff it against `docs/standards/evidence.json`, and propose only what changed (new patterns, rules now contradicted, types that appeared, deviations that were fixed).
- `compare <repo>`: run `inventory.py` on that one repo path, then audit it against common plus its type file and list gaps. Writes nothing.

## Steps

### 1. Inventory

Run the script (it is deterministic and read-only, and works on Python 3.9 and 3.12):

```bash
python3 ~/.claude/skills/python-standards-learn/scripts/inventory.py ~/repo --out <scratchpad>/inventory.json
```

It finds projects (a folder with `pyproject.toml`, a `Dockerfile` or `requirements.txt`; its subfolders are part of it, not separate repos), collects facts per repo (layout, packaging, lint/typing, tests, Docker, CI, config and secret handling, git recency) and suggests one or more types with the signals behind them. If the user named repos, pass those paths instead of `~/repo`.

### 2. Confirm the classification

Print one table: repo, suggested type(s), signals, last commit, and a `?` where `needs_confirmation` is true (unclear type, several types, or several Dockerfiles: a repo that builds two images, such as a web image and a job image, can belong to two types). Apply the user's exclusions by repo name or path when you aggregate, and verify the totals afterwards (a nested folder or an excluded repo's subfolder must not be counted). Ask the user to correct types, name repos to **exclude** (abandoned, experiments, not Python apps such as pure YAML or dbt repos), and add types the script cannot see. Repos with no commit in 12 months count as *stale* (weight lower, see decision rules). Do not analyse further until the user confirms.

### 3. Build the common baseline

Read `references/dimensions.md` and `references/decision-rules.md`. Start from the authoritative sources (hard rule 3). For each dimension, compare the facts of **all** confirmed repos regardless of type. Decide each point as *adopt*, *variant (use when ...)* or *drop (migrate)*. Where the repos broadly agree, that is a common rule. Where they split along type lines, it is not common: hold it for step 4.

For anything the inventory facts cannot settle (naming style, module layout inside `src/` or `app/`, how config objects are built, logging setup, how tests are organised), sample a few files from the two or three most recently active repos and the oldest repo, and read them. Sampling is read-only and proportionate: a handful of files per repo, not whole trees.

### 4. Build the per-type deltas

For each confirmed type, take only the points where that type differs from common for a reason (for example a web service exposes a port, an Airflow job is a one-shot with no `EXPOSE`). Keep each rule's `Basis` honest: a practice no repo follows is a proposal and needs the user's yes before it becomes a rule. Note types with fewer than 3 active repos as *thin*; they get a short paragraph instead of a scaffold proposal.

### 5. Propose

Print, in this order, then wait:

1. **Classification and exclusions** as confirmed.
2. **Common rules**, in the format of `references/output-format.md`, with evidence.
3. **Per-type deltas**, one block per type, only differences.
4. **Contested items**: each with the options, the evidence for each, and your recommendation, as a short question.
5. **Variants kept** ("use when ..."), **drops** (deviations to migrate, with repo names), and **seen once** (needs a yes).
6. **Scaffold proposal**: which files in the user's Python template repo (find its checkout under `~/repo`) would change for common, and which `scaffolds/<type>/` overlays would be added, as a file list plus diff. Common rules map to the base template; type deltas map to overlays.

### 6. Write

After an explicit yes (each part has its own):

1. Read `~/.claude/skills/okf-writer/SKILL.md` and run its spec check (`okf_watch.py check --max-age 14`); if the spec changed, tell the user before writing.
2. Write the bundle under `docs/standards/` in the template repo following `references/output-format.md`: `common/<area>.md`, `types/<type>.md`, `migration.md`, then update `index.md` and add the `log.md` entry. Read an existing file before overwriting it (check state before writing), and keep any `verified` entry and extra keys you do not own.
3. Save the inventory as `docs/standards/evidence.json` (paths made relative to `~/repo`, remote URLs dropped) so `refresh` can diff against it. Lint: `python3 ~/.claude/skills/okf-writer/scripts/okf_lint.py docs/standards` and fix every error. The OKF linter reads frontmatter leniently, so also check what editors and other consumers will see: parse every frontmatter block with a real YAML parser (`uv run --with pyyaml python ...`), run a markdown linter (`uvx --from pymarkdownlnt pymarkdown --disable-rules MD013,MD041,MD024 --enable-extensions front-matter scan docs/standards`), and check the editor's spell-check diagnostics if an IDE is attached. Fix the generator or text, not the symptoms.
4. Write scaffold changes only for what was approved, on a work branch if the repo is on its main branch, never on `master`/`dev` directly.
5. Show `git diff --stat` and `git diff` for the standards. Leave everything uncommitted.
6. Offer two lines for the repo's `CLAUDE.md` pointing at the bundle ("read `docs/standards/index.md` first, then only the files the task needs"); add them only after a yes.

### 7. Report

State what was written, the lint result and trust summary from the linter, how many repos fed each rule, which rules are common versus per-type, the deviations that repos still have (`migration.md`), and anything left unconfirmed. If this skill file or its references were changed, remind the user that `~/.claude` changes are mirrored into `cr-misc-function/CLAUDE/skills`.

## `compare <repo>` output

Gaps against common first (by rule ID), then gaps against the type doc. Each gap has the rule ID, what the repo does, and the fix. No writes.

## Failure handling

- Script finds no repos: ask for a root path.
- A repo cannot be read or is not a git repo: list it as skipped and carry on.
- Fewer than 3 repos of a type: keep the type as thin (a short note), do not invent a scaffold.
- Standards already exist: switch to `refresh`, read the existing bundle first, and show only the changes (add a `log.md` entry).
- The user declines a part: write nothing for that part and offer to adjust.
