# Safety

The skill must never see secrets or package contents. Prose rules drift, so the enforcement is in code.

## What `collect.py` enforces

- `git()` runs only these sub-commands: `rev-parse`, `log`, `for-each-ref`, `status`, `stash list`, `remote`, `config`, `merge-base`, `rev-list`, `symbolic-ref`, `diff` (only `--name-only` or `--name-status`), `ls-files`, `grep -c`, `tag`, `worktree`. Arguments that print content (`-p`, `--patch`, `-u`, `--cc`, `show`, `--textconv`, `--ext-diff`) raise an error.
- `git grep -c` (TODO counts) returns per-file counts only and excludes secret-looking and package paths by pathspec.
- `read_allowed()` opens only `pyproject.toml`, `package.json`, `README.md`, `CLAUDE.md`, `uv.lock`, `requirements.txt`, `environment.yml`, never inside a skipped directory. Parsing picks fixed keys; nothing else from the file is copied, so an index URL with a credential never reaches the report.
- Untracked and modified paths are listed by name; names that look like secrets (`.env*`, `*.pem`, `*.key`, `*secret*`, `token*.json`, ...) are counted but not shown.
- A remote URL with embedded credentials has them stripped.
- `FILES_OPENED` is written to the JSON, so a run can be audited.
- `gh pr list` reads PR titles only, never bodies or diffs.

## What is still exposed

Commit subjects, branch names, PR titles and file names are shown. A secret pasted into one of those would appear. Treat the saved report as internal.

## Where output goes

`render.py` writes under `<umbrella>/knowledge/` and refuses a path inside a git work tree (it falls back to `~/.claude/umbrella-review/<name>/`). The umbrella itself is not versioned, so the reports have no backup. Logbook data is joined at read time and only status, date and a task excerpt reach the report; nothing is copied into a repo or into the skill's mirror.

## Test

`tests/test_umbrella_review.py` in `cr-misc-function` builds throwaway repos with canary strings in `.env`, `token.json`, `node_modules/`, `.venv/`, a commit diff and a stash, runs both scripts, and asserts that no canary appears in the JSON or the report, that `files_opened` is a subset of the allow-list, and that every git call matches the allow-list.
