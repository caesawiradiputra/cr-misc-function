# Prompt Coach Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Capture each prompt locally with secrets masked, add a short coaching note to each reply, and keep a full review per prompt in a local Markdown file.

**Architecture:** One stdlib helper (`coach.py`) holds masking, the capture policy, the `add` contract and the read commands. A thin bash hook calls its `hook` subcommand on `UserPromptSubmit`, which prints the `additionalContext` JSON. A skill carries the note and entry rules. Data lives in `~/.claude/prompt-coach/`, outside every repo.

**Tech Stack:** Python 3.9 and 3.10+ (stdlib only: `re`, `json`, `fcntl`, `pathlib`), bash, pytest, ruff, mypy.

**Spec:** `docs/superpowers/specs/2026-11-02-prompt-coach-design.md` (read it first; this plan only records decisions the spec leaves open).

## Global Constraints

- The helper runs on the WSL system `python3` (3.9) and on 3.10+. Use `from __future__ import annotations`; no `match`, no `zip(strict=)`, no runtime `X | None`. Verify with `uv run --python 3.9` and `--python 3.12`.
- Data directory: `~/.claude/prompt-coach/`, mode `700`, files `600`; override with env var `PROMPT_COACH_HOME` (tests only). Refuse to write when the directory resolves inside a git worktree.
- Files: `enabled` flag, `prompts.jsonl` (masked), `YYYY-MM.md` (append-only, oldest first).
- Every path that runs from the hook or from `add` exits 0 and prints at most one line naming the error class and the step, never the input or an unmasked value. No fallback log.
- Masked text is written `[REDACTED:<kind>]`. A pure pasted block is stored only as `[pasted content, N chars]`.
- Skip coaching (log with `coach: false`) for: under 4 words after removing pasted blocks, a message starting with "This session is being continued", a bare slash command, a pure pasted block. Coach off: no write at all.
- `add` JSON fields: `id`, `verdict`, `context`, `understanding`, `alternatives`, `rewrite`, `changes`, `tags` only. `id` matches `^[0-9a-f]{8}$` and exists in `prompts.jsonl` (one file; lookup is by `id` across it, with no month window). Text fields at most 600 characters, `alternatives` at most 3 items, whole entry at most 3000 characters.
- Verdicts: `clear`, `minor`, `unclear`. Tags: `missing-goal`, `missing-subject`, `ambiguous-reference`, `run-on`, `fragment`, `tense`, `article`, `preposition`, `word-choice`, `spelling`, `missing-constraint`, `mixed-requests`, `unclear-scope`.
- The per-turn `add` call must run **without a permission prompt**. The hook instruction gives the exact absolute command (`python3 /home/<user>/.claude/skills/prompt-coach/coach.py add <<'COACH_JSON_END_<id>'`, with the home directory expanded at run time), and `settings.json` (template with `<user>` as a placeholder, live with the real path) gets one `permissions.allow` rule scoped to `python3 <that path> add`. The rule and the instruction must match character for character.
- Hook timeout 5 s. Commit nothing: the user commits only when asked, so every task ends with a `git status` checkpoint, not a commit. Never `git add -A`.
- Markdown follows the global style (language on every fence, `| --- |` separators, object names in backticks).

## Review Focus

Failure modes the spec implies but no spec section tests; each gets a test in the task that owns the code.

1. A huge prompt (1 MB paste with no tags): stored text is truncated and masking stays fast. Task 2 and Task 1.
2. Hook stdin that is empty, not JSON, lacks `prompt`, or has a non-string `prompt`: exit 0, nothing written. Task 4 and Task 5.
3. Two sessions capturing at once: no interleaved or lost JSONL lines. Task 2.
4. An entry added in a new month for a prompt captured on the last day of the previous month: the `id` is found and the entry lands in the current month's `.md`. Task 3.
5. Claude's text containing the heredoc delimiter: the delimiter includes the id, so one entry cannot end another's heredoc. Task 4.

## Unverified until Task 8

Treat these as assumptions, not facts, until the live checks pass:

- **Hook composition:** that both `UserPromptSubmit` contexts reach the model.
- **Pasted-block shape:** that the hook's `prompt` field carries `<pasted_content …>` tags. They have only been seen in the model-side transcript; the hook may receive the raw pasted text with no tags, or a placeholder. If so, a full paste would be stored (masked, capped at 4000 characters), which breaks the stub promise.
- **Permission rule:** that a `permissions.allow` prefix rule matches the `add` command with a heredoc, so no prompt appears.

## File Structure

| Path | Responsibility |
| --- | --- |
| `CLAUDE/skills/prompt-coach/coach.py` | Masking, capture policy, `add`, `show`, `status`, `on`, `off`, `hook`, CLI |
| `CLAUDE/skills/prompt-coach/SKILL.md` | Note and entry rules, tag list, commands, privacy warning |
| `CLAUDE/linux-wsl/hooks/prompt-coach-capture.sh` | Fail-soft wrapper around `coach.py hook` |
| `CLAUDE/linux-wsl/settings.json` | Second command in the existing `UserPromptSubmit` entry |
| `tests/test_prompt_coach.py` | All automated tests (imports `coach.py` by path, like `tests/test_okf_watch.py`) |
| `CLAUDE/README.md`, `docs/dev-machine-setup.md` | Skills row, hook row, install note |

The live copies (`~/.claude/skills/prompt-coach/`, `~/.claude/hooks/prompt-coach-capture.sh`, `~/.claude/settings.json`) mirror these in Task 7.

## Calls the plan makes that the spec leaves open

- The `prompts.jsonl` field `cwd` stores only the project folder name (`project`), so a home path never reaches disk.
- The stored prompt text is capped at 4000 characters, then `…[truncated N chars]` (the spec bounds `add` fields but not the stored prompt).
- The spec's `capture` is a function; the CLI subcommand is `hook`, which prints the whole hook JSON, so the bash wrapper holds no logic and needs no `jq`.
- The heredoc delimiter in the instruction is `COACH_JSON_END_<id>`.
- Long hex strings of 32 or more characters, including 40-character git SHAs, are masked as `opaque` (a known false positive).

---

### Task 1: Masking

**Files:**
- Create: `CLAUDE/skills/prompt-coach/coach.py`, `tests/test_prompt_coach.py`

**Interfaces:**
- Produces: `mask(text: str) -> str`; module constant `KINDS: tuple[str, ...] = ("secret", "bearer", "url-credentials", "jwt", "private-key", "opaque", "access-key", "email", "ip", "error")`.

- [ ] **Step 1: Write the failing tests** in `tests/test_prompt_coach.py`. Load the module with `importlib.util.spec_from_file_location` from `CLAUDE/skills/prompt-coach/coach.py` (same pattern as `tests/test_okf_watch.py`). Parametrize `test_mask_hides`:

| Input | Expected output contains | Must not contain |
| --- | --- | --- |
| `password=hunter2` | `password=[REDACTED:secret]` | `hunter2` |
| `{"api_key": "abc123xyz"}` | `[REDACTED:secret]` | `abc123xyz` |
| `Authorization: Bearer abcDEF123` | `[REDACTED:bearer]` | `abcDEF123` |
| `postgres://u:p4ss@db.internal/x` | `[REDACTED:url-credentials]` | `p4ss` |
| a three-part JWT (`eyJ...`) | `[REDACTED:jwt]` | the token |
| a `-----BEGIN PRIVATE KEY-----` block | `[REDACTED:private-key]` | the body |
| 32 hex characters | `[REDACTED:opaque]` | the string |
| `LTAI` + 16 alphanumerics, `AKIA` + 16, `ghp_` + 36, `sk-` + 40 | `[REDACTED:access-key]` | the key |
| `me@example.com` | `[REDACTED:email]` | the address |
| `10.12.3.4` | `[REDACTED:ip]` | the address |

Add `test_mask_keeps` (unchanged output): `DA-1234`, `another-repo`, `release/DA-1234/CHANGELOG.md`, `version 1.7.0`, a 7-character short SHA. Add `test_mask_is_idempotent` (`mask(mask(x)) == mask(x)` for every input above), `test_mask_prose_secret_passes_through` (`"my password is hunter2"` is unchanged: a documented limit, asserted so nobody assumes otherwise), `test_mask_failure_never_leaks` (monkeypatch an internal pattern to raise `re.error`; `mask("secret=abc")` returns `"[REDACTED:error]"` and `capsys` shows no output), and `test_mask_large_input_has_no_catastrophic_backtracking` (1 MB of `"word "` plus one secret, and 200 KB each of `"a"`, `"="`, `":"` and `"eyJ."` repeated, all finish within a generous 20 s bound, which catastrophic backtracking would exceed by orders of magnitude; the secret is still masked).

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_prompt_coach.py -v`
Expected: FAIL (module file missing or `mask` undefined).

- [ ] **Step 3: Implement `mask` and `KINDS` in `coach.py`.** Ordered list of compiled `(kind, pattern, replacement)`; key-value secret keeps the key name and replaces the value; every pattern must be free of nested quantifiers (the 1 MB test guards this). Wrap the loop so any exception returns `"[REDACTED:error]"`.

- [ ] **Step 4: Run to verify pass**

Run: `uv run pytest tests/test_prompt_coach.py -v`
Expected: PASS.

- [ ] **Step 5: Checkpoint:** `git status --short` lists only the two new files for this task (plus the already-untracked files from before).

---

### Task 2: Data directory and capture policy

**Files:**
- Modify: `CLAUDE/skills/prompt-coach/coach.py`, `tests/test_prompt_coach.py`

**Interfaces:**
- Consumes: `mask`.
- Produces:
  - `class CoachError(Exception)`
  - `data_dir() -> Path` (creates with mode `700`; raises `CoachError` inside a git worktree; honors `PROMPT_COACH_HOME`)
  - `is_enabled() -> bool`
  - `classify(prompt: str) -> tuple[str, bool]` returns `(text_to_store, coach)`
  - `capture(payload: dict[str, Any]) -> tuple[str, bool] | None` returns `(id, coach)`, or `None` when the coach is off or the payload is unusable. Appends one line to `prompts.jsonl` with `id` (8 hex), `ts` (ISO, UTC offset), `session`, `project`, `text`, `coach`.

- [ ] **Step 1: Write failing tests** (all use `tmp_path` and `monkeypatch.setenv("PROMPT_COACH_HOME", ...)`):
  - `test_off_writes_nothing`: no `enabled` file, `capture(...)` returns `None`, directory listing unchanged (no `prompts.jsonl`).
  - `test_short_prompt_logged_without_coaching`: `"go ahead"` gives `coach False` and one logged line.
  - `test_continuation_and_slash_command_not_coached`: "This session is being continued…" and `"/logbook"`.
  - `test_pure_pasted_block_stub`: a message that is only `<pasted_content id="x">…secret text…</pasted_content id="x">` stores exactly `[pasted content, N chars]` with N the block's length, and `prompts.jsonl` contains none of the block text.
  - `test_mixed_prompt_stubs_only_the_paste`: own words kept (masked), the block replaced by the stub.
  - `test_logged_text_is_masked_and_project_only`: `password=x` is masked; the line has `project` equal to the folder name and no `/home/` string.
  - `test_large_prompt_is_truncated`: 1 MB prompt stores at most 4000 characters plus the `…[truncated N chars]` marker.
  - `test_refuses_git_worktree`: `PROMPT_COACH_HOME` under a `tmp_path` that holds a `.git` directory raises `CoachError`.
  - `test_modes`: directory `0o700`, files `0o600`.
  - `test_concurrent_capture_keeps_every_line`: 8 threads times 10 captures give 80 valid JSON lines with 80 distinct ids.

- [ ] **Step 2: Run to verify failure** (`uv run pytest tests/test_prompt_coach.py -v`; expected: FAIL on the new tests).

- [ ] **Step 3: Implement the functions above.** Append under `fcntl.flock` on the target file, flush and `fsync`; create files with `os.open(..., 0o600)`. Walk up the parents of `data_dir` looking for `.git` for the worktree refusal. `classify` removes `<pasted_content …>…</pasted_content …>` blocks (regex, `DOTALL`) before counting words.

- [ ] **Step 4: Run to verify pass** (expected: PASS).

- [ ] **Step 5: Checkpoint:** `git status --short`.

---

### Task 3: The `add` contract

**Files:**
- Modify: `CLAUDE/skills/prompt-coach/coach.py`, `tests/test_prompt_coach.py`

**Interfaces:**
- Consumes: `data_dir`, `mask`, `VERDICTS`, `TAGS`.
- Produces: `class EntryError(CoachError)`; `add_entry(raw: str, now: datetime | None = None) -> str` returns the entry id and appends the review (section 6 of the spec) to `YYYY-MM.md`; `lookup_prompt(id: str) -> dict[str, Any] | None` finds the line with that `id` in `prompts.jsonl`.

- [ ] **Step 1: Write failing tests:**
  - `test_add_writes_entry_with_header_and_fields` (header `## YYYY-MM-DD HH:MM - <id> - <project>`, all labelled lines present, **You wrote** comes from the logged, masked prompt, not from the JSON).
  - `test_add_text_survives_literally`: quotes, newlines, emoji, Bahasa text, `$(rm -rf x)`, backticks and the string `COACH_JSON_END` in `understanding`.
  - `test_add_masks_generated_fields`: `understanding` containing `token=abc123` is stored masked.
  - `test_add_rejects` (parametrized, each asserts nothing was written): unknown field; bad `id` format; `id` not in the log; `verdict` `"great"`; tag not in the list; non-string field; malformed JSON; top-level JSON array.
  - `test_add_truncates_oversized_field`: 5000 characters becomes 600 ending in `...`; a 4-item `alternatives` keeps 3; an entry over 3000 characters is shortened by trimming the longest fields first until it fits.
  - `test_add_for_prompt_captured_last_month`: capture with a timestamp of 2026-10-31, add on 2026-11-01 (`now=` argument); the `id` is found and the entry lands in `2026-11.md`, not `2026-10.md`.
  - `test_month_file_is_oldest_first`: two entries on different days appear in write order.

- [ ] **Step 2: Run to verify failure** (expected: FAIL).

- [ ] **Step 3: Implement `add_entry` and `lookup_prompt`.** Validate before any write; build the entry text; append under `flock` like Task 2 (share one `_append(path, text)` helper between both tasks rather than duplicating it).

- [ ] **Step 4: Run to verify pass** (expected: PASS).

- [ ] **Step 5: Checkpoint:** `git status --short`.

---

### Task 4: Commands, the `hook` subcommand and the CLI

**Files:**
- Modify: `CLAUDE/skills/prompt-coach/coach.py`, `tests/test_prompt_coach.py`

**Interfaces:**
- Consumes: everything above.
- Produces: `set_enabled(on: bool) -> str`; `status() -> str`; `show(n: int = 3) -> str` (newest first, does not modify the file); `hook_output(stdin_text: str) -> str` (the hook JSON string, or `""`); `main(argv: list[str]) -> int` with subcommands `hook` (stdin), `add` (stdin), `on`, `off`, `status`, `show [n]`. `main` returns 0 for `hook` and `add` in every case.

- [ ] **Step 1: Write failing tests:**
  - `test_on_off_toggle_flag`: `set_enabled(True)` creates only the `enabled` file and returns `"prompt-coach: on (takes effect on the next prompt)"`; `set_enabled(False)` removes it and returns `"prompt-coach: off"`; repeating either is harmless.
  - `test_status_reports_path_counts_and_warning`: output has the data path, entries this month, the verdict split, and the exact warning sentence from the spec ("Local capture may still keep sensitive information…").
  - `test_status_explains_a_refused_directory`: with `PROMPT_COACH_HOME` inside a git worktree, `status()` prints the refusal reason instead of failing silently, while `hook_output` still returns `""`.
  - `test_show_is_newest_first_and_read_only`: file bytes identical before and after.
  - `test_hook_output_for_coached_prompt`: valid JSON with `hookSpecificOutput.hookEventName == "UserPromptSubmit"`; `additionalContext` contains the logged id, `COACH_JSON_END_<id>`, `Prompt coach:`, the three tiers (clear, two lines, three lines), the instruction to answer exactly as without the coach, and the last-tool-call instruction. It also contains the exact command string `python3 <expanduser("~/.claude/skills/prompt-coach/coach.py")> add <<'COACH_JSON_END_<id>'` (the test computes the path the same way and compares). Under 200 words.
  - `test_hook_output_empty_when_off_or_uncoached`: returns `""` when off, and for a skipped (short) prompt.
  - `test_hook_survives_bad_input` (parametrized): `""`, `"not json"`, `"{}"`, `'{"prompt": 5}'`, `'{"prompt": null}'` all give `""`, write nothing, and `main(["hook"])` returns 0.
  - `test_main_add_failure_exits_zero_and_prints_one_line`: bad JSON on stdin gives return code 0 and one line that names the error class and not the input.

- [ ] **Step 2: Run to verify failure** (expected: FAIL).

- [ ] **Step 3: Implement the functions and `main`.** Read `sys.stdin` as UTF-8 with `errors="replace"`. `main` wraps each subcommand in one `try/except Exception` that prints `prompt-coach: <ErrorClass> in <step>` and returns 0 for `hook` and `add`; `on`, `off`, `status` and `show` return 1 on error so a person sees the failure. Keep `if __name__ == "__main__": raise SystemExit(main(sys.argv[1:]))`.

- [ ] **Step 4: Run on both Python versions, plus lint**

Run:
`uv run pytest tests/test_prompt_coach.py -v`
`uv run --no-project --python 3.9 --with pytest pytest tests/test_prompt_coach.py -q`
`uv run --no-project --python 3.12 --with pytest pytest tests/test_prompt_coach.py -q`
`uv run ruff check CLAUDE/skills/prompt-coach tests/test_prompt_coach.py && uv run ruff format --check CLAUDE/skills/prompt-coach tests/test_prompt_coach.py && uv run mypy CLAUDE/skills/prompt-coach/coach.py tests/test_prompt_coach.py`
Expected: all pass, no lint or type errors. `--no-project` is needed because the repo pins `requires-python >=3.11,<3.12`; there is no `conftest.py` to bypass. If `--python 3.9` cannot resolve a test dependency, run the test file with the system `python3 -m pytest` and say so.

- [ ] **Step 5: Checkpoint:** `git status --short`.

---

### Task 5: The bash hook wrapper

**Files:**
- Create: `CLAUDE/linux-wsl/hooks/prompt-coach-capture.sh`
- Modify: `tests/test_prompt_coach.py`

**Interfaces:**
- Consumes: `coach.py hook` (stdin JSON, stdout hook JSON).
- Produces: an executable script that always exits 0, within 5 s, with stderr discarded.

- [ ] **Step 1: Write failing tests** that run the script with `subprocess.run(["bash", script], input=..., env={**os.environ, "PROMPT_COACH_HOME": str(tmp_path), "PROMPT_COACH_SCRIPT": coach_py})`:
  - coach on, normal prompt: stdout parses as JSON and `additionalContext` mentions the id found in `prompts.jsonl`.
  - coach off: stdout empty, exit 0, no `prompts.jsonl`.
  - `PROMPT_COACH_SCRIPT` pointing at a missing file: stdout empty, exit 0 (helper missing is silent).
  - helper that exits 1 (a stub script in `tmp_path`): exit 0, stdout empty.
  - helper that sleeps 10 s: the wrapper returns within 6 s with exit 0 (uses `timeout 5`).

- [ ] **Step 2: Run to verify failure** (expected: FAIL, script missing).

- [ ] **Step 3: Write the script** following the header-comment style of `user-prompt-repo-focus.sh`: resolve `${PROMPT_COACH_SCRIPT:-$HOME/.claude/skills/prompt-coach/coach.py}`, return silently when it is missing, then `timeout 5 python3 "$script" hook 2>/dev/null` and `exit 0` on every path. No `jq`, no other logic.

- [ ] **Step 4: Run to verify pass** (`uv run pytest tests/test_prompt_coach.py -v`; expected: PASS). `chmod +x` the script and run `shellcheck` if installed.

- [ ] **Step 5: Checkpoint:** `git status --short`.

---

### Task 6: Skill text, template wiring and docs

**Files:**
- Create: `CLAUDE/skills/prompt-coach/SKILL.md`
- Modify: `CLAUDE/linux-wsl/settings.json`, `CLAUDE/README.md`, `docs/dev-machine-setup.md`

**Interfaces:**
- Consumes: the final command names from Task 4.

- [ ] **Step 1: Write `SKILL.md`** (frontmatter `name: prompt-coach`, a description that triggers on `/prompt-coach`, "coach my prompts", "show my prompt reviews", "turn the prompt coach on or off"). Sections: what it does; the privacy warning verbatim; the note tiers (section 5 of the spec) with one example each; the full-entry field list and the fixed tag list; how to call `coach.py add` (the heredoc form with `COACH_JSON_END_<id>`); the commands table from section 7; rules (answer exactly as without the coach, English only, never change the user's meaning, say "(guess)" when the rewrite guesses, no note on skipped prompts). Phase 2 `patterns` is listed as not built.

- [ ] **Step 2: Add the hook to the template settings:** a second `{"type": "command", "command": "bash ~/.claude/hooks/prompt-coach-capture.sh", "timeout": 5, "statusMessage": "Prompt coach"}` inside the existing `UserPromptSubmit` entry's `hooks` array, after the repo-focus command. Add one `permissions.allow` rule scoped to the `add` command, `Bash(python3 /home/<user>/.claude/skills/prompt-coach/coach.py add:*)` (placeholder `<user>` in the template; confirm the exact rule syntax against the existing entries and the Claude Code docs before writing it). Validate the JSON with `python3 -m json.tool`.

- [ ] **Step 3: Update docs.** `CLAUDE/README.md`: a `prompt-coach` row in the Skills table and `prompt-coach-capture.sh` in the `linux-wsl/hooks/` tree line. `docs/dev-machine-setup.md`: one short subsection (copy the skill and hook, add the settings entry, run `/prompt-coach on` after a new session starts; data stays out of the repo).

- [ ] **Step 4: Verify:** `python3 -m json.tool CLAUDE/linux-wsl/settings.json > /dev/null` succeeds; `grep -n "prompt-coach" CLAUDE/README.md docs/dev-machine-setup.md` shows the new lines; check the changed Markdown for the style rules (languages on fences, `| --- |`).

- [ ] **Step 5: Checkpoint:** `git status --short` lists only the files named in this plan.

---

### Task 7: Install dormant in the live `~/.claude`

**Files:**
- Create: `~/.claude/skills/prompt-coach/` (copy of the template skill), `~/.claude/hooks/prompt-coach-capture.sh`
- Modify: `~/.claude/settings.json`

- [ ] **Step 1: Check state first.** `ls ~/.claude/skills/prompt-coach ~/.claude/hooks/prompt-coach-capture.sh` must show both missing; read `~/.claude/settings.json` `hooks.UserPromptSubmit` and `permissions.allow` before editing; run `git -C ~/.claude rev-parse --is-inside-work-tree` (checked 2026-11-02: not a repo; if it ever is, the coach would refuse to write, so stop and tell the user).

- [ ] **Step 2: Copy** the skill folder (without `__pycache__`) and the hook script; `chmod +x` the hook. Add the same hook command and the `add` allow rule (with the real home path) to the live `settings.json` with a targeted edit; validate the JSON.

- [ ] **Step 3: Verify the install is dormant:** `diff -r CLAUDE/skills/prompt-coach ~/.claude/skills/prompt-coach` is empty; there is no `~/.claude/prompt-coach/enabled`; `echo '{"prompt":"this is a test prompt for the coach","session_id":"s","cwd":"/tmp/x"}' | bash ~/.claude/hooks/prompt-coach-capture.sh` prints nothing and creates nothing.

- [ ] **Step 4: Checkpoint:** `git status --short`; the live files are outside the repo, so nothing new appears there.

---

### Task 8: Live checks and the enable gate (manual, fresh session)

The user starts the fresh session (hooks and settings are read at startup). The coach stays off until every check passes.

- [ ] **Step 1: Turn it on for the test:** in the fresh session run `/prompt-coach on`, then confirm `/prompt-coach status` shows on, the data path, and the warning.

- [ ] **Step 2: Three prompts and their results:**
  - a clear prompt: reply ends with `Prompt coach: clear, no change.`; one entry in `~/.claude/prompt-coach/2026-11.md` with verdict `clear`;
  - a short prompt (`go ahead`): no note; a `prompts.jsonl` line with `coach: false`; no entry;
  - an unclear prompt with two plausible readings: a note of up to three lines naming the other reading; an entry with that reading under **Other readings**.

- [ ] **Step 3: Composition check (release gate).** Send a prompt that `@`-mentions a sibling repo. Expected: the repo-focus context takes effect (Claude reports the repo's git state) **and** the coach note appears. If only one arrives, run `/prompt-coach off`, stop, and record the finding; do not enable.

- [ ] **Step 4: Failure isolation (release gate).** `chmod 000 ~/.claude/skills/prompt-coach/coach.py`, send an `@`-mention prompt in the same session. Expected: the answer and the repo-focus context still arrive and there is no coach note and no error. Restore with `chmod 644`.

- [ ] **Step 5: Permission gate.** Across Step 2 and Step 3, the `coach.py add` call ran with **no permission prompt and no classifier block**. A prompt on every turn makes the coach unusable: if one appears, run `/prompt-coach off`, record the exact prompt text, and fix the allow rule or the command string before enabling again.

- [ ] **Step 5b: Allow-rule breadth gate.** The rule is a prefix rule on `python3 <path> add`. With a throwaway test (not the real data), ask Claude Code to run `python3 <path> add; echo hi` and `python3 <path> add $(date) <<'X'` style variants: each must **prompt** (extra commands must not ride on the rule). If one runs silently, the rule is broader than intended: remove it and report.

- [ ] **Step 6: Paste gate.** Paste a block that contains a unique marker (for example `ZZ-MARKER-4471`) as its own message in the way you normally paste, then run `grep -c ZZ-MARKER-4471 ~/.claude/prompt-coach/prompts.jsonl ~/.claude/prompt-coach/*.md`. Expected: `0` everywhere, and `prompts.jsonl` holds `[pasted content, N chars]`. If the marker is found, the hook receives the paste without tags: run `/prompt-coach off`, and change `classify` to the real shape (inspect it by dumping only the prompt's first 40 characters and its length) before enabling again.

- [ ] **Step 7: Privacy spot check.** `grep -c "password\|token=" ~/.claude/prompt-coach/prompts.jsonl` after sending one prompt containing `password=hunter2`; expected: the line holds `[REDACTED:secret]` and not `hunter2`. `git -C ~/repo/cr-misc-function/cr-misc-function status --short` shows no coach data.

- [ ] **Step 8: Decide.** All steps pass: leave it on and tell the user. Any failure: `/prompt-coach off`, report the failing step and its output, and fix before enabling again.

---

## Self-review notes

- **Spec coverage:** capture policy (Tasks 2, 4), masking and limits (1, 6), the `add` contract (3), append-only order and `show` (3, 4), hook composition and failure isolation (5, 8), note tiers (6, 8), commands (4, 6), template mirror and docs (6), tests on 3.9 and 3.12 (4), live gate (8). Phase 2 `patterns` is out of scope by the spec.
- **Review by a stronger model (2026-11-02)** found two gaps and three smaller issues, all fixed above: the per-turn `add` call needed a scoped allow rule and an exact command string (Tasks 4, 6, 7; gate in Task 8); the pasted-block stub rested on an unchecked assumption about the hook's input (listed under "Unverified", gate in Task 8); the month-window lookup contradicted the single-file spec (now a lookup by `id` across `prompts.jsonl`); a refused directory could fail silently (`status` now explains it, Task 7 checks it); and the 3.9 and 3.12 commands needed `--no-project`. The wall-clock assertion on masking was replaced with a generous no-backtracking bound.
- **Names used across tasks:** `mask`, `KINDS`, `CoachError`, `EntryError`, `data_dir`, `is_enabled`, `classify`, `capture`, `lookup_prompt`, `add_entry`, `set_enabled`, `status`, `show`, `hook_output`, `main`.
- **Deliberate differences from the spec** are listed under "Calls the plan makes": `project` instead of `cwd`, the 4000-character cap, the `hook` subcommand, the id-suffixed delimiter and the SHA false positive.
