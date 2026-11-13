# Changelog — umbrella-review-skill: Umbrella review skill and docs version line

**Ticket:** none (own-initiative tooling change, keyed by slug)
**Branch:** feat/umbrella-review-skill

All notable changes for this change are documented here. Newest entry on top.

---

## [Unreleased] — 2026-11-13

**Type:** Feature

### 📝 Summary

Adds the `umbrella-review` Claude Code skill to the `CLAUDE/` template. Run from an
umbrella folder that holds child git repos, it reports per repo what the last work was,
which of the user's branches never reached `dev` or `master` (stalled, cancelled or
forgotten), whether `README.md` and `CLAUDE.md` moved with the last release or with a
branch ahead of `dev`, and what is pending. It is read-only and never fetches.

All reading is done by one stdlib-only Python collector, so the sensitive-file rules are
enforced in code: an allow-list of git sub-commands (none that print file or diff
content), an allow-list of readable file names, and a skip list for `.env*`, keys,
tokens and package folders. A renderer turns the collector's JSON into a ranked report,
saves it outside any git work tree, and keeps the user's waiting/cancelled/unknown
decisions in a state file.

The change also adds a "Docs version line" convention to the global `CLAUDE.md`
template (`Version: x.y.z · Updated: YYYY-MM-DD` in `README.md` and `CLAUDE.md`), which
the skill checks, and applies it to this repo's own two files.

### 🎯 Objectives

- Rebuild, per repo, the picture of the last work after a gap, including work from before
  Claude-written documentation existed.
- Surface handed-over work whose testing never finished, using PR state first (`dev`
  takes squash merges, so git ancestry alone misreports) and the logbook's follow-up days.
- Keep `README.md` and `CLAUDE.md` close to the point the work counts as done.
- Make "never read secrets or package folders" mechanical and testable.

### 📋 Changes Made

**Files Added**

- `CLAUDE/skills/umbrella-review/SKILL.md` — workflow, safety summary, report reading
- `CLAUDE/skills/umbrella-review/references/classification.md` — branch classes, age
  bands, doc-drift rules, branch-role detection
- `CLAUDE/skills/umbrella-review/references/safety.md` — what the collector enforces and
  what is still exposed (commit subjects, branch names, PR titles)
- `CLAUDE/skills/umbrella-review/scripts/collect.py` — read-only collector (Python 3.9+)
- `CLAUDE/skills/umbrella-review/scripts/render.py` — report, state file, `decide` and
  `status` sub-commands
- `tests/test_umbrella_review.py` — tests on throwaway repos

**Files Modified**

- `CLAUDE/CLAUDE.md` — adds the "Docs version line" rule
- `CLAUDE/README.md` — adds the `umbrella-review` row to the skills table
- `README.md`, `CLAUDE.md` — add the version line (`0.1.0`, matching `pyproject.toml`);
  `README.md` also lists the skill
- `docs/dev-machine-setup.md` — optional "Umbrella review skill" section and a
  verification-checklist line

**Key Implementations**

1. **Git guard** (`collect.py`, `git()`): only an allow-listed set of sub-commands;
   arguments such as `-p`, `show`, `--textconv` raise an error; `diff` only with
   `--name-only` or `--name-status`; `stash` only as `stash list`.
2. **File guard** (`collect.py`, `read_allowed()`): opens only manifests, `README.md`,
   `CLAUDE.md` and similar names, never inside a skipped folder, and records each open in
   `files_opened`.
3. **Branch classification** (`collect.py`): PR state from `gh pr list --author @me`
   first, ancestry only as a low-confidence fallback; classes `merged`, `in_sit_only`,
   `open_pr`, `closed_unmerged`, `pushed_no_pr`, `local_only`; testing-stage tickets use
   the logbook's follow-up days, other branches 14 and 56 days.
4. **Doc drift** (`collect.py`): per release (first-parent commits on the production
   branch) and per branch ahead of the integration branch, plus the version line against
   `pyproject.toml` or `package.json`.
5. **Report output** (`render.py`): refuses to write inside a git work tree and falls
   back to `~/.claude/umbrella-review/<name>/`.

### 📂 Release Artifacts

- **Docs:** none beyond this changelog.

### 🧪 Testing Performed

`tests/test_umbrella_review.py` (10 cases) builds throwaway git repos and checks:

- planted canary strings in `.env`, `token.json`, `node_modules/`, `.venv/`, a commit
  diff and a stash never reach the collector JSON or the report;
- `files_opened` contains only allow-listed names outside skipped folders;
- the git guard rejects `show`, `log -p`, a content `diff`, `stash show -p` and `push`;
- every real `git` call made by a run is on the allow-list;
- an unmerged branch is classified with its ticket, a stash is listed, roles are detected;
- the report folder falls outside a git work tree; a decision is persisted;
- the `Version:` line parses in three formats.

Also run: both scripts on Python 3.9 and 3.14, `ruff check`, `ruff format --check`, `mypy`
and the full `pytest` suite (692 passed).

### 💥 Breaking Changes

None. New files only, plus additive documentation.

### 📦 Dependencies

No new dependencies. The scripts use the standard library; the skill calls `git`, and
`gh` when available.

### 🔍 Code Review Notes

- Not exercised yet: the workspace OKF bundle mode (documented in `SKILL.md`, delegated to
  `okf-writer`) and the `--with-templates` flag against many repos.
- The version-line convention is new; no other repo carries it yet, so the first reviews
  will flag them all by design.
- Reports contain commit subjects, branch names and PR titles; treat them as internal.
- This repo has no `release/` folder on `dev` yet; this is its first, keyed by slug
  because there is no ticket.

---

**Author:** caesaramBFI
**Reviewed By:** [To be filled after review]
