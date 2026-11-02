---
name: prompt-coach
description: Coach the user's written English prompts. When the coach is on, a hook saves each prompt locally (secrets masked), and after each reply Claude adds a short note (how the prompt was understood, a clearer way to write it, and any other possible reading) while a full review goes to a local Markdown file. Use whenever the user says "/prompt-coach", "prompt coach on", "turn the prompt coach off", "show my prompt reviews", "prompt coach status", "coach my prompts", "help me write better prompts", or when a `Prompt coach is on` instruction arrives in the hook context.
---

# Prompt coach

The user wants to write clearer English prompts, check that what they meant is what was understood, and carry the habit into talking with other people. This skill is the coaching rules; the hook and the helper do the capturing.

Design: `docs/superpowers/specs/2026-11-02-prompt-coach-design.md` in `cr-misc-function`. Helper: `~/.claude/skills/prompt-coach/coach.py` (stdlib only, Python 3.9 and newer).

## Privacy: read this first

> Local capture may still keep sensitive information that masking does not recognize. Do not use it for prompts that contain secrets or data you do not want stored. Switch it off with `/prompt-coach off`.

- Data lives in `~/.claude/prompt-coach/` (mode `700`): `enabled` (the flag), `prompts.jsonl` (masked prompts), `YYYY-MM.md` (full reviews, oldest first). It is outside every repo, never committed, never synced, never published.
- Masking is a best-effort regex for known shapes (passwords and tokens assigned a value, bearer tokens, URLs with credentials, JWTs, private keys, long opaque strings, cloud key shapes, emails, IPv4). It cannot see a secret written in ordinary prose.
- The prompt still goes to the model, as every prompt does. Masking only controls what is **stored** in the coach's own files.
- Claude Code keeps its own session transcripts under `~/.claude/projects/` with your prompts as typed (unmasked). The coach does not touch them; masking protects only `~/.claude/prompt-coach/`.
- Masking can over-mask: any 32-or-more hex run (a 40-character commit SHA) and long mixed-case identifiers may show as `[REDACTED:opaque]`. That is accepted; the safe side is more masking.
- Ticket keys, repo names, table names and paths are kept on purpose: they are the context a review needs.
- A pure pasted block is stored only as `[pasted content, N chars]`. A prompt over 4000 characters is truncated when stored.

## Commands

The user types `/prompt-coach <command>`; run the helper and show its output.

| Command | Run | Effect |
| --- | --- | --- |
| `on` | `python3 ~/.claude/skills/prompt-coach/coach.py on` | Create the flag; takes effect on the next prompt |
| `off` | `python3 ~/.claude/skills/prompt-coach/coach.py off` | Remove the flag; nothing new is written |
| `status` | `python3 ~/.claude/skills/prompt-coach/coach.py status` | State, data path, counts, verdict split and the warning |
| `show [n]` | `python3 ~/.claude/skills/prompt-coach/coach.py show 3` | Last n full reviews, newest first |
| `patterns` | not built | Phase 2: repeated habits by tag |

The first install only takes effect in a new session (settings are read at startup). Only the `add` call is pre-approved in `settings.json`; the other commands may ask for permission.

## When the hook context arrives

With the coach on, each coached prompt brings a `Prompt coach is on` instruction with a prompt `id` and the exact `add` command. Follow it:

1. **Answer the user exactly as you would without the coach.** The coaching never changes the answer, delays it, or replaces it.
2. As the **last tool call** before the final reply, run the `add` command once, with the JSON in the quoted heredoc the instruction gives (never as shell arguments).
3. End the reply with a `---` rule and the short note.

Prompts with no instruction (under four words, continuation messages, pure pastes, coach off) get no note and no entry.

## The short note

At most three lines, in English, after a `---` rule. It grows only as far as the prompt needs:

| Prompt | Note |
| --- | --- |
| Clear | One line: `Prompt coach: clear, no change.` |
| Minor wording issue | Two lines: the reading and the rewrite |
| Meaningful ambiguity | Up to three lines: reading, rewrite and the other reading |

```text
---
Prompt coach: I read this as "update today's logbook row for DA-1234".
Better: "Please update today's logbook row for DA-1234."
Why: Alternative reading: add a new row. Say which you meant.
```

- Ask which reading was meant **only** when the choice would change what you do. A harmless ambiguity goes in the full review, not in the reply.
- The rewrite keeps the user's meaning. If it needed a guess, write `(guess)`.
- A prompt in Bahasa gets an English reading and an English rewrite, because the aim is better English.
- The note is about wording only: never about the user's choices, never implying the task was wrong, never a lecture.

## The `add` entry

Pipe one JSON object to the helper through a heredoc whose delimiter includes the prompt id, as the instruction shows:

```bash
python3 ~/.claude/skills/prompt-coach/coach.py add <<'COACH_JSON_END_a1b2c3d4'
{"id": "a1b2c3d4", "verdict": "minor", "context": "Logbook session",
 "understanding": "Update today's logbook row for DA-1234",
 "alternatives": [], "rewrite": "Please update today's logbook row for DA-1234.",
 "changes": "Added the object and the time frame.", "tags": ["missing-goal"]}
COACH_JSON_END_a1b2c3d4
```

Contract (the helper rejects anything else and writes nothing):

- Fields: `id`, `verdict`, `context`, `understanding`, `alternatives` (list), `rewrite`, `changes`, `tags` (list). No other field.
- `id` is the 8-hex id from the instruction. `verdict` is `clear`, `minor` or `unclear`.
- Each text field is at most 600 characters, `alternatives` at most 3 items, the whole entry at most 3000 characters (longer text is shortened).
- For a `clear` prompt leave `rewrite` and `changes` empty.
- `context`: one or two lines on what the session was doing. `understanding`: your reading in plain words. `alternatives`: each other plausible reading and what would decide between them. `changes`: the grammar and clarity points.
- Tags come only from this list; a new tag needs a change to this skill, not an improvised label: `missing-goal`, `missing-subject`, `ambiguous-reference`, `run-on`, `fragment`, `tense`, `article`, `preposition`, `word-choice`, `spelling`, `missing-constraint`, `mixed-requests`, `unclear-scope`.
- If the helper prints an error, do not retry in a loop. Mention it in one line and continue; a failed entry never blocks the answer.

## What not to do

- Do not change how you answer because of the coaching.
- Do not coach text the user only pasted, and do not store or repeat pasted content.
- Do not put secrets, tokens or passwords in any field, even if the prompt had them.
- Do not create, edit or delete files in `~/.claude/prompt-coach/` by hand; use the helper.
- Do not commit or publish anything from that folder, and do not mention its contents in commit messages or PR text.
- Do not keep a note going after the user turns the coach off.
