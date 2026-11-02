# Prompt coach: short feedback on each prompt, full review in a local file

Date: 2026-11-02. Status: draft for review. Scope: a `UserPromptSubmit` hook, a stdlib helper
(`coach.py`), the `prompt-coach` skill, local data under `~/.claude/prompt-coach/`, and the
`CLAUDE/` template mirror (code and text only, never data).

## 1. Purpose

The user writes prompts that sometimes have weak grammar or unclear sentences, and wants to get
better at it. The point is not to fix misunderstandings (there are few); it is to practise clear
written English, check that what was meant is what was understood, and carry the habit into
talking with other people.

Goals:

1. **Capture policy.** When the coach is on, prompt text is captured locally after masking,
   with the exceptions in section 4 (skipped prompts are logged without coaching; a pure pasted
   block is logged as a stub holding only its character count). When the coach is off, nothing
   new is written anywhere.
2. After each reply, show a **short** note: how the prompt was understood and a clearer way to
   write it.
3. Keep a **full review** per prompt in a Markdown file: original, context, understanding, other
   possible readings, rewrite, and what to improve.
4. Make repeated habits visible over time (phase 2).

Non-goals: grading or scoring the user; changing how the actual request is answered; coaching
text the user only pasted; uploading anything; a PowerShell port (sessions run in WSL; add it
later if wanted).

Anti-goals (a failure even if it works): a note on every trivial prompt ("yes", "go ahead"); a
rewrite that quietly changes what the user meant; coaching that delays or replaces the answer;
any prompt text, masked or not, ending up in git, Confluence, the Windows sync or a log shared
elsewhere.

## 2. Privacy rules

- **Stored locally and masked.** Data lives in `~/.claude/prompt-coach/` (directory mode `700`,
  files `600`). It is outside every repo, is not part of the logbook sync, and is never committed
  or published. `coach.py` refuses to write when its data directory resolves inside a git
  worktree.
- **What the model sees.** The prompt itself still goes to the model, as every prompt does; that
  cannot be avoided. The coaching text is generated from the same prompt. Masking controls only
  what is **stored**. The user decided this is acceptable.
- **Masking is a best-effort safeguard, not a guarantee that stored text is secret-free.** It
  runs on every field the helper writes, including the understanding and rewrite that Claude
  supplies, so a secret echoed by Claude is masked too. Patterns (regex):
  - `password`, `passwd`, `pwd`, `secret`, `token`, `api_key`, `apikey` assigned a value
    (`key=value`, `key: value`, JSON form);
  - `Bearer <token>` and `Authorization:` header values;
  - URLs with credentials (`scheme://user:pass@host`);
  - JWTs (three base64url parts), PEM private-key blocks;
  - long opaque strings (32 or more hex or base64 characters);
  - cloud access-key shapes (`LTAI...`, `AKIA...`, `ghp_...`, `sk-...`);
  - email addresses and IPv4 addresses.
- **Claude Code's own transcripts are outside this boundary.** It stores each session under
  `~/.claude/projects/` with the prompts as typed (unmasked). The coach does not read, change
  or mask them; masking protects only the coach's own files.
- Ticket keys, repo names, table names and file paths are **kept**: they are the context that
  makes a review useful, and they are not secrets. This is a judgement call (see section 9).
- Masked text is written as `[REDACTED:<kind>]`, so a review still reads.
- **Known limit, shown where the user will see it.** A regex does not catch a secret written in
  ordinary prose, a private hostname, an internal URL without credentials, an account id or
  other business data. The skill and `/prompt-coach status` both print this warning: *Local
  capture may still keep sensitive information that masking does not recognize. Do not use it
  for prompts that contain secrets or data you do not want stored. Switch it off with
  `/prompt-coach off`.* Status also prints the data path.
- **Diagnostics never carry prompt text.** Errors and warnings from the hook and the helper name
  only the error class and the step (for example `mask failed: re.error`), never the input or the
  unmasked value. There is no fallback log. If masking itself raises, that field is replaced by
  `[REDACTED:error]` and nothing unmasked is written.
- A pure pasted block is stored only as the stub `[pasted content, N chars]`: no content, hash,
  first line or any other extract.
- A **metadata-only mode** (length and tags, no text) is a possible later escape hatch; it is not
  part of phase 1.

## 3. Components

| Part | Path | Job |
| --- | --- | --- |
| Hook | `~/.claude/hooks/prompt-coach-capture.sh` | On `UserPromptSubmit`: skip when off, mask and log the prompt, add the coaching instruction to the turn |
| Helper | `~/.claude/skills/prompt-coach/coach.py` | `capture`, `add`, `on`, `off`, `status`, `show`; masking; atomic writes |
| Skill | `~/.claude/skills/prompt-coach/SKILL.md` | What the note and the entry must contain, the tag list, the style rules, the `/prompt-coach` commands |
| Data | `~/.claude/prompt-coach/` | `enabled` flag, `prompts.jsonl` (masked), `YYYY-MM.md` (full reviews) |
| Template | `CLAUDE/skills/prompt-coach/`, `CLAUDE/linux-wsl/hooks/prompt-coach-capture.sh`, `CLAUDE/linux-wsl/settings.json`, `CLAUDE/README.md` | Code and text only |

`coach.py` is stdlib only and must run on Python 3.9 and 3.10+ (global tooling rule). It never
exits non-zero from the hook path.

## 4. Per-turn flow

1. The user sends a prompt. The hook receives `{prompt, session_id, cwd}` on stdin.
2. **Skip rules** (the prompt is still logged, but no coaching is requested, field
   `coach: false`):
   - the coach is off (no `enabled` file): nothing is logged at all;
   - fewer than 4 words after removing pasted blocks;
   - a continuation message (starts with "This session is being continued"), a bare slash
     command, or a message that is only a `<pasted_content>` block.
3. Otherwise `coach.py capture` masks the prompt, appends a line to `prompts.jsonl`
   (`id`, `ts`, `session`, `cwd`, `text`, `coach`) and prints the new `id`.
4. The hook returns `additionalContext` of about 120 words telling Claude to:
   - answer the user exactly as it would without the coach;
   - as the last tool call before the final reply, run `coach.py add` once, passing the entry as
     **JSON on stdin** through a quoted heredoc, never as shell arguments:

     ```bash
     python3 ~/.claude/skills/prompt-coach/coach.py add <<'COACH_JSON_END'
     {"id": "a1b2c3d4", "verdict": "minor", "context": "...", "understanding": "...",
      "alternatives": [], "rewrite": "...", "changes": "...", "tags": ["missing-goal"]}
     COACH_JSON_END
     ```

   - end the reply with the short note (section 5).
5. `coach.py add` reads one JSON object from stdin and applies this contract:
   - **Allowed fields only:** `id`, `verdict`, `context`, `understanding`, `alternatives` (list),
     `rewrite`, `changes`, `tags` (list). An unexpected field rejects the whole entry.
   - **`id`** must match `^[0-9a-f]{8}$` and exist in `prompts.jsonl` (looked up by `id` across
     the single file); otherwise nothing is written. The entry goes into the month file of the
     day it is added.
   - **`verdict`** is one of `clear`, `minor`, `unclear`; each tag is from the fixed list in
     section 6.
   - **Bounds:** each text field is at most 600 characters, `alternatives` at most 3 items, the
     whole entry at most 3000 characters. Over the limit, the field is truncated with `...` and
     the entry is still written; a non-string value or malformed JSON rejects the entry.
   - Quotes, newlines, Unicode and shell metacharacters are literal text, because the JSON never
     passes through a shell command line. The delimiter line is unique so the body cannot end
     the heredoc early.
   - Masking runs on every text field, then the entry is **appended** to the month's file under
     an advisory lock (`fcntl.flock`) and flushed with `fsync`. A reject or failure prints one
     line (error class and step only, exit code 0) and never blocks the turn.

Cost: about 150 extra tokens of context and one Bash call per coached turn. `/prompt-coach off`
removes it entirely.

## 5. The short note (shown in the reply)

At most three lines, at the end of the reply, in English, after a `---` rule:

```text
Prompt coach: I read this as "<one sentence>".
Better: "<clearer version of the user's own sentence>"
Why: <one short reason, or "Alternative reading: <it>. Say which you meant.">
```

The note grows only as far as the prompt needs:

| Prompt | Note |
| --- | --- |
| Clear | One line: `Prompt coach: clear, no change.` |
| Minor wording issue | Two lines: the reading and the rewrite |
| Meaningful ambiguity | Up to three lines: reading, rewrite and the other reading |

- The note names the other reading and asks the user which was meant **only** when the choice
  could change what gets done. A harmless ambiguity goes in the full review, not in the reply.
- A rewrite never implies the task itself was wrong.
- The rewrite keeps the user's meaning. If the rewrite needed a guess, it says "(guess)".
- A prompt in Bahasa gets an English reading and an English rewrite, because the aim is better
  English.
- The note is about wording, never about the user's choices or the task.

## 6. The full review (Markdown file)

`~/.claude/prompt-coach/YYYY-MM.md`, **append-only and oldest first** (entries are added at the
end, so a write never rewrites the file), one entry per prompt. `/prompt-coach show` reads the
file and prints the newest entries first without changing it:

```text
## 2026-11-02 14:05 - <id> - <project folder name>

**Verdict:** clear | minor | unclear
**You wrote:** <masked original>
**Context:** <one or two lines: what the session was doing>
**Understood as:** <my reading, plain words>
**Other readings:** <none, or each reading and what would decide>
**Suggested:** <clearer English version>
**What changed:** <grammar and clarity points, each tagged>
**Tags:** missing-goal, ambiguous-reference
```

Tag list (fixed, so patterns can be counted): `missing-goal`, `missing-subject`,
`ambiguous-reference`, `run-on`, `fragment`, `tense`, `article`, `preposition`, `word-choice`,
`spelling`, `missing-constraint`, `mixed-requests`, `unclear-scope`. A new tag needs a skill
change, not an improvised label.

## 7. Commands

| Command | Effect |
| --- | --- |
| `/prompt-coach on` / `off` | Create or remove the `enabled` flag; takes effect on the next prompt |
| `/prompt-coach status` | On or off, entries this month, the data path, the verdict split, and the masking warning from section 2 |
| `/prompt-coach show [n]` | Print the last n full entries, newest first (default 3) |
| `/prompt-coach patterns [--since DATE]` | Phase 2: count tags and show the most repeated habits with two examples each |

## 8. Phasing

1. **Phase 1 (build now):** hook, `capture`, `add`, `on`, `off`, `status`, `show`, masking with
   tests, skill text, template mirror, settings entry.
2. **Phase 2 (after a week of real data):** `patterns`, and a short weekly summary of repeated
   habits with before and after examples.

## 9. Calls I made (not decided by the user)

- Keep ticket keys, repo names, table names and paths unmasked; mask emails and IPv4 addresses.
- Skip coaching for under 4 words, continuation messages, bare slash commands and pure pasted
  blocks; log them with `coach: false`.
- Pasted blocks are stored as a stub, not in full.
- Bahasa prompts get an English reading and rewrite.
- WSL and bash only; no PowerShell port yet.
- No automatic retention limit; the user can delete month files. A `prune` command can follow.
- **Hook composition.** The prompt-coach hook is added as a second command inside the existing
  `UserPromptSubmit` entry, next to `user-prompt-repo-focus.sh`. Each hook prints its own
  `hookSpecificOutput.additionalContext` JSON and exits 0; the coach hook never reads or alters
  the other hook's output, and a failure in either does not stop the other or the user's turn
  (every path exits 0 with a short timeout, 5 s). That both contexts reach the model is
  **unverified until the live check** in section 10.
- The `settings.json` change takes effect in a new session. The skill's install note and the
  `on` command say so.
- **No permission prompt on the per-turn call.** The `add` call runs on every coached turn, so a
  prompt (or an auto-mode block) each time would make the coach unusable. The hook instruction
  gives the exact absolute command, and `settings.json` gets one `permissions.allow` rule
  scoped to `python3 <home>/.claude/skills/prompt-coach/coach.py add`, matching it character
  for character. Whether the rule matches a command with a heredoc is **unverified until the
  live check**.
- **Pasted-block shape is an assumption.** The stub relies on the hook's `prompt` field carrying
  `<pasted_content …>` tags, which have only been seen in the model-side transcript. If the
  hook receives the raw paste, a full paste would be stored (masked, capped); the live check
  settles it and `classify` is changed to the real shape before the coach is enabled.
- The stored prompt text is capped at 4000 characters, and the log keeps the project folder name
  instead of the working directory path.

## 10. Testing

- Unit tests for masking: each pattern in section 2, a ticket key and a repo name staying
  intact, idempotence (masking twice changes nothing more), a secret in ordinary prose passing
  through (a documented limit, asserted so nobody assumes otherwise), and a forced masking
  failure that writes `[REDACTED:error]` and prints no input. Run on Python 3.9 and 3.12.
- Capture policy tests: with the coach off, no write to `prompts.jsonl` or any month file; a
  short prompt is logged with `coach: false`; a pure pasted block stores only
  `[pasted content, N chars]`; the hook never writes raw prompt text to a fallback log or an
  error message.
- `add` contract tests: quotes, newlines, Unicode and shell metacharacters survive as literal
  text; an invalid or unknown `id`, an unexpected field, a bad verdict or tag and malformed JSON
  are rejected without writing; an oversized field is truncated by the documented rule; a
  helper failure exits 0; a data directory inside a git worktree is refused.
- File order tests: write entries on two dates, check the file is oldest first, and `show`
  returns them newest first without modifying the file.
- Hook tests: feed sample JSON on stdin and check the log line, the skip rules, the off switch
  and that malformed input exits 0.
- Live check in a fresh session after the settings entry is added:
  - send a normal prompt, a short prompt and an unclear prompt, and read the note and the file;
  - confirm that **both** `UserPromptSubmit` contexts reach the model (an `@`-mention of a
    sibling repo triggers the repo-focus hook; the coach note must still appear);
  - force the coach hook to fail (for example make the helper unreadable) and confirm that the
    repo-focus context and a normal answer still arrive;
  - confirm the `add` call runs with no permission prompt;
  - paste a block with a unique marker and confirm only the stub is stored.

## 11. Open points

None that block the build. The largest risks are masking misses on free-text secrets
(documented, shown in `status`, not solvable by regex), the per-turn cost, which the off switch
bounds, and three unverified integration behaviors that the live check settles: composition of
two `UserPromptSubmit` contexts, the permission rule matching the heredoc call, and the shape of
a pasted block in the hook input.

## 12. Revision history

- 2026-11-02: draft. Revised the same day after an external design review: capture policy stated
  once, the masking limit made prominent, `add` takes bounded JSON on stdin, the monthly file is
  append-only and oldest first, hook composition and failure isolation specified, the note
  tiered by how much the prompt needs.
- 2026-11-02: final branch review (a fresh reviewer, after the build) led to wider secret-key
  masking (prefixed and joined keys such as `clientSecret`, quoted values with spaces, an `@` in
  a URL password), masking of any `Authorization:` header value, line splitting that survives
  U+2028/U+2029/U+0085, no `add` while the coach is off, and the transcript note above.
- 2026-11-02: a second review (a stronger model, during planning) added the permission rule for
  the per-turn call, the unverified pasted-block shape, a single-file `id` lookup, and the stored
  prompt cap and project-name field.
