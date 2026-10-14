---
name: extract-session-preferences-core
description: Review the current conversation and extract the user's durable feedback, working principles, and recurring instructions — not a summary of what was done, but what the user taught Claude about HOW they want future work handled. Produces a categorized report (global vs. domain vs. project vs. session-scoped) and, with the user's confirmation, saves approved durable items to the available memory system and/or CLAUDE.md when the environment provides the required write capability. Use this whenever the user asks to "extract preferences from this conversation," "review this session for durable feedback," "what should you remember from this chat," "save your learnings," "distill this into instructions for next time," or similar requests to reflect on collaboration style — even without the words "memory" or "preferences." Do NOT use this for a plain recap of what was accomplished in the session (that's a normal summary, not an extraction of standing instructions).
---

# Extract Session Preferences

Most of a conversation concerns the task itself. This skill focuses on a
different signal: what the user taught Claude about how future work should
be handled. Extract durable behavioral instructions from corrections,
explicit preferences, repeated feedback, and clearly expressed approvals.
Do not confuse task decisions with standing preferences.

## Why this is harder than it looks

The natural failure mode is treating this like writing meeting minutes —
restating decisions and facts from the conversation. That produces a
summary, which is not what's needed here (the user can already scroll up).
The other failure mode is over-generalizing a one-off project decision
("use JSON between these two functions") into a sweeping global rule
("always use JSON for all data interchange").

The danger is asymmetric: missing a preference costs a repeated correction
next time, which is annoying but cheap. Wrongly promoting a one-off decision
into a standing preference silently distorts unrelated future work, which is
expensive and hard to notice. So this skill should be biased toward
**under-saving, not over-saving** — every step below exists to enforce that
bias.

## A note on timing

This skill mines *how* things were said — tone, a quiet "yes exactly," a
mildly repeated preference, the precise wording of a correction. That's
exactly the kind of low-salience detail a context-compaction summary is
least likely to preserve, since compaction is optimized to keep task
outcomes and decisions, not behavioral signal. If a long session is heading
toward compaction, it's better to run this skill *before* that happens than
to wait until the transcript has already been summarized out from under it.
If the user is running a long working session, it's worth proactively
suggesting a run of this skill rather than waiting to be asked.

## Step 1: Mine the conversation for signal

Read the full conversation (not just the last few turns). First, check
whether the visible history shows signs of already being a post-compaction
summary (a system-inserted recap of earlier turns, a conversation that
"starts" mid-task with no visible opening, explicit compaction markers) —
if so, say so plainly at the top of the report and treat findings sourced
only from the summarized portion as lower confidence by default, since the
summary may have already dropped the implicit signal this skill relies on.
Findings from any raw, unsummarized turns still in view keep their normal
confidence.

Look for:

- Explicit instructions ("always," "never," "from now on," "don't do X")
- Corrections — places Claude did something and the user redirected it
- Outright rejections of an approach Claude proposed or took
- Explicit approvals — "yes exactly," "keep it like this"
- Preferences repeated more than once, even mildly
- Stated preferences about output format, verbosity, tone, terminology
- Opinions about how agents/skills/workflows should be designed

**Preference vs. instruction:** an instruction is an explicit rule the user
states directly ("always give me the full file, not a diff"). A preference
is a recurring tendency inferred from behavior across the conversation.
Represent both as concrete future behavior, not personality traits —
"user dislikes verbose answers" is not useful and not what this skill is
for; "prefer concise answers when scope is clear, expand only on request"
is. Never convert an observation about the user's personality, mood,
intelligence, or habits into a saved preference — only their stated or
demonstrated preferences about how work should be done.

**Behavioral feedback vs. task correction:** not every correction is a
preference. A correction about facts, implementation details, requirements,
or the subject matter of the current task should not be saved as a standing
preference unless it also reveals how the user wants future work handled.

- "That SQL is incorrect; the column is `created_at`." → task correction,
  drop it.
- "When writing SQL for me, always verify column names against the schema
  instead of assuming them." → durable workflow preference, keep it.

Only the second type is a preference candidate. A correction earns a spot
in the report only when it teaches a rule about *how to work*, not when it
just fixes something wrong about the current task's subject matter.

**Indirect feedback** ("don't give me partial answers and then ask if I
want the rest" → generalizes to "give complete solutions when scope is
clear") is real evidence and should be generalized to its underlying
principle rather than quoted verbatim. But it is not equivalent to an
explicit standing instruction — cap it at Medium confidence unless
reinforced elsewhere in the conversation (see confidence scale in Step 3).

**Silence is not approval.** Accepting an unusual choice without pushback
is weaker evidence than it might seem — the user may simply not have
noticed the choice. Only an explicit "yes, that's right" or equivalent
counts as approval evidence; the absence of a correction does not
independently create a preference.

## Step 1b: Check the registry

The registry is a cross-session, cross-repo **evidence ledger**, not the
authoritative configuration: each record points at the `CLAUDE.md` section, skill
or memory where the rule is actually enforced. It lives in
`~/.claude/preference-registry/` as `registry-shared.csv` (approved GLOBAL and
DOMAIN records), `registry-project.csv` (PROJECT records, candidates, conflicts) and
`registry-archive.csv`. Use the helper; never hand-edit the CSVs. Its commands and
columns are in `~/.claude/preference-registry/README.md`.

```bash
python3 ~/.claude/skills/extract-session-preferences-core/registry.py find --keywords a,b --text "short rule" [--repo R] [--domain D] [--archive]
python3 ~/.claude/skills/extract-session-preferences-core/registry.py report        # conflicts, promotion eligibility, gaps
```

**Lookup order** for each candidate from Step 1:

1. `find` by keywords and meaning (shared records rank first).
2. Compare the behavior the rule describes, not the wording. Exact keyword hits alone
   are not a match.
3. No match: it is a new candidate (Step 7 adds it). Search the archive only to look at
   history, a conflict, a dropped rule, or a rule the user restated.

**If a record matches, do not create a duplicate.** A match prevents duplicates; it does
not suppress new evidence:

- Decide whether the evidence is an independent sighting (below) and record it with
  `update --sighting --session <id>`; `Seen` counts each session once.
- Compare the wording. If the new evidence supports a clearer rule, propose a refinement
  to the existing record.
- If it contradicts the rule, mark the record `conflict` and stop promotion until the
  user resolves it.
- A matching GLOBAL record: check refinement or contradiction, then stop.

**Independent sightings.** A sighting is one session in which the user explicitly states,
corrects or confirms the underlying preference.

- Repetition inside one session counts once; the session ID is the dedup key.
- A preference inferred from behavior is not explicit evidence. Silence is not approval.
- Accepting one implementation without confirming the general principle is not a sighting.
- A `dropped` record is not proposed again unless the user restates it or asks to
  reconsider; the restatement is new evidence on the same record, not a new ID.
- A missing record is not evidence against a preference.

The registry never overrides Step 2: eligibility is a proposal, a high `Seen` is
evidence, not permission.

## Step 2: Scope each candidate

Default assumption for every candidate: PROJECT or SESSION, not GLOBAL or
DOMAIN. Promoting something too broad is the expensive mistake (see "Why
this is harder than it looks" above), so scope up only when the evidence
clearly supports it.

**Explicit local language rules out GLOBAL immediately.** If the user
frames something as "for this project," "for this task," "in this
workflow," "for now," "just for this," "in this example," or "for this
document," treat that as strong evidence the instruction is PROJECT or
SESSION — even if the content would plausibly generalize well elsewhere.
Don't override an explicit local scope just because the instruction looks
reusable.

**Promote to GLOBAL only when at least one of these holds:**

1. The user explicitly says the preference should apply going forward
   ("from now on," "always," "in future," "I prefer... generally").
2. The same preference is demonstrated or reinforced across multiple
   independent moments or tasks in the conversation — not merely repeated
   as part of the same request. A user restating "full code please" three
   times while Claude keeps truncating one answer is one instruction, not
   three confirmations; the same preference showing up again on an
   unrelated task later in the conversation is independent evidence.
3. The user explicitly approves the *generalized principle*, not just one
   instance of it.

A single isolated approval, rejection, or implementation decision is not
enough on its own to reach GLOBAL — file it as DOMAIN, PROJECT, or a
Low-confidence candidate instead.

**DOMAIN is not GLOBAL.** A preference scoped to a category of work (e.g.
"when designing Claude skills, prefer single-responsibility over broad
ones") should stay DOMAIN unless the user generalizes it further — it
should not bleed into every future conversation regardless of topic.

**Task choices are not automatically preferences.** The technologies,
formats, models, architectures, tools, or approaches selected during a task
are not durable preferences merely because the user chose or used them
repeatedly within that task. A conversation spent building AI agents doesn't
mean "user prefers AI agents over normal workflows"; five requests for
Markdown output on one project doesn't mean "user always wants Markdown."
Only preserve a choice like this when the user explicitly says it should
apply beyond the current task, or when the "independent moments or tasks"
bar above is clearly met.

**What to keep vs. drop:**

- **Keep:** communication/output-format preferences, coding or
  documentation style preferences, skill/agent design principles,
  recurring quality standards — anything that clears the promotion bar
  above, or is clearly durable within one domain even if not global.
- **Drop:** one-time task requirements, decisions scoped to the current
  project's architecture, specific code/filenames from this session, facts
  only relevant to the task just finished. When genuinely unsure, drop it.

Rejections and approvals both deserve the same check: was the user
reacting to *this instance* or to *the pattern in general*? Only the
latter clears GLOBAL/DOMAIN scope.

### Promotion eligibility (a proposal, never an automatic scope change)

Track evidence, scope and persistence separately: a rule can have strong evidence and
stay PROJECT, and a user can state a global preference once. `Status` says what happened
to it: `candidate`, `approved` (user agreed, not yet written), `saved` (written to the
stated place), `conflict`, `dropped`, `superseded`.

- **New -> PROJECT candidate:** one explicit statement or correction. An inferred
  candidate stays unconfirmed until a second independent sighting that includes at least
  one explicit statement or confirmation.
- **PROJECT -> DOMAIN:** at least two independent sessions, plus either evidence from two
  repositories in the same domain or an explicit statement that it applies generally to
  that domain. The wording must describe domain behavior, not one repo's implementation.
- **DOMAIN -> GLOBAL:** evidence across at least two distinct domains, or an explicit
  statement that it applies across projects. Remove domain terms from the wording.
- **Safety fast-track:** an explicit correction about a consequential or destructive
  mistake triggers an immediate review of a protective rule. Decide its scope from the
  real risk; severity alone never makes it GLOBAL.
- Every scope change and every write needs the user's approval. `promote` moves the
  record without changing its ID, dates or history.

**Conflicts.** A contradiction blocks promotion. Keep both the rule and the conflicting
evidence, do not silently replace the wording, and ask the user to resolve it. An
explicitly superseded rule may be revised after approval with its provenance kept.

**Staleness.** Never expire a preference by age alone. Flag it when its tool, platform,
configuration or project changes, or when the user contradicts it. Archive records of
retired projects.

## Step 3: Normalize each surviving candidate

For each one, write:

- **Type** — positive (do X) or negative (don't do X). Keep negative
  framing when that's how the user actually said it ("don't give partial
  implementations") rather than forcing everything into a positive
  restatement — the negative form is often the more actionable one.
- **Category** (e.g. Response Style, Code Style, Skill Design, Testing)
- **Preference** — one actionable sentence, not a vague value like "be
  helpful." Say exactly what future-Claude should do differently.
- **Evidence** — the moment in the conversation that justified keeping it
- **Confidence:**
  - **High** — explicit standing instruction, or the same preference
    reinforced across multiple independent moments.
  - **Medium** — strongly implied by a clear correction, or an approval
    that plainly refers to the general approach rather than one output.
  - **Low** — a single indirect or ambiguous signal: a one-off approval
    with no other context, an inference from behavior rather than a
    statement, or anything resting on silence/lack of pushback.
  - Low-confidence candidates are never auto-promoted to GLOBAL, regardless
    of how useful they look — see Step 2's promotion rules.
- **Scope** — GLOBAL / DOMAIN / PROJECT / SESSION, per Step 2

## Step 4: Check for conflicts

Compare each GLOBAL/DOMAIN candidate against what's already in `CLAUDE.md`
and the memory system. When two instructions conflict, resolve in this
order:

1. Explicit scope beats inferred scope — an instruction the user marked as
   local ("just for this project") beats a broader instruction that was
   merely inferred, even if the broader one is older.
2. More specific scope beats broader scope — a PROJECT-level instruction
   narrows a GLOBAL default *for that project*; it does not replace the
   GLOBAL default everywhere else.
3. Within the same scope, explicit instruction beats inferred preference.
4. Within the same scope, newer instruction beats older instruction.
5. Never let a local exception get promoted into a global replacement —
   "for this workflow, only return the first node" narrows behavior for
   that workflow; it must not overwrite a GLOBAL "give complete
   implementations" preference.

State any conflict resolution out loud in the report rather than silently
overwriting. If two candidates from this pass express the same underlying
principle, merge them instead of listing near-duplicates.

## Step 5: Produce the report

Always show this, even if some sections end up empty:

```text
# Global Preferences to Add
[Type / Category / Preference / Evidence / Confidence, or "None — explain why"]

# Existing Preferences to Refine
[Existing CLAUDE.md or memory entries that this session's evidence updates
or contradicts, with the proposed rewrite and which conflict rule applied]

# Preferences Not Suitable for Global Configuration
[DOMAIN / PROJECT / SESSION items, each with a one-line reason it stayed local]

# Final Configuration Recommendations
[Clean, consolidated, copy-pasteable configuration, grouped by scope —
GLOBAL, then DOMAIN, then PROJECT. Do NOT include SESSION items here:
SESSION items are shown above for transparency but are not meant to
persist anywhere.]

# Registry Updates
[Registry changes: new candidates, independent sightings to record, conflicts,
refinements, and the `report` promotion-eligibility list with the evidence.]
```

If the conversation genuinely contains no durable signal (e.g. it was purely
task execution with no corrections, approvals, or stated preferences), say so
plainly instead of inventing findings to fill the template.

## Step 6: Save — only with confirmation, and ask where

Never write to CLAUDE.md or the memory system before the user has seen the
report and agreed. Present the approved candidates as a numbered list with
each item's scope, so the user can approve or reject individual items
rather than the whole batch, e.g.:

```text
1. Give complete implementations when scope is clear — GLOBAL
2. Prefer single-responsibility skills over broad ones — DOMAIN: skill design
3. Use structured JSON between these workflow nodes — PROJECT
4. Use this exact model for the comparison — SESSION (not saved)

Save 1 and 2?
```

Once the user picks which items to save, ask (if not already clear) whether
each belongs in:

- **The memory system** — for items shaped like `user`, `feedback`,
  `project`, or `reference` memories. Use the memory system's documented
  format and storage conventions for the current environment; do not
  assume a particular file structure (frontmatter fields, an index file,
  etc.) unless that environment's own documentation specifies it — this
  keeps the skill usable across different Claude environments rather than
  tied to one implementation.
- **CLAUDE.md** (or the current environment's equivalent standing-rules
  file) — for items that read as standing operating rules, added as
  concise, non-redundant entries consistent with the file's existing
  style.
- **Both** — when an item is a rule worth stating explicitly *and* worth
  preserving with the "why" behind it (e.g. tied to a specific incident).

Only write the items the user actually approved — if they push back on one
finding, drop or revise just that one rather than the whole batch.

Never persist sensitive personal information as a standing preference
merely because it appeared in the conversation. Only save it when the user
explicitly asks that specific information be remembered and the target
memory system permits it.

## Step 7: Update the registry

After the user has answered Step 6, update the registry through the helper so the next
session, in any repo, can build on this one. Ask once with the Step 6 question ("Save 1
and 2, and update the registry?"); the registry is a ledger and changes no behavior, so
it needs no per-item decision.

```bash
python3 ~/.claude/skills/extract-session-preferences-core/registry.py add --preference "..." --keywords a,b,c --scope PROJECT --session <id> \
    --repo R --domain D [--explicit] [--evidence "..."]
python3 ~/.claude/skills/extract-session-preferences-core/registry.py update P-012 --sighting --session <id> --repo R [--explicit]
python3 ~/.claude/skills/extract-session-preferences-core/registry.py update P-012 --status saved --saved-in "global CLAUDE.md, Section X"
python3 ~/.claude/skills/extract-session-preferences-core/registry.py promote P-012 --to DOMAIN --saved-in "skill Y"     # only after approval and the write
python3 ~/.claude/skills/extract-session-preferences-core/registry.py archive P-012 --reason "user rejected it" --status dropped
```

- Add a record for every kept candidate that is not SESSION scope, including items the
  user declined to save (`candidate`, or `dropped` with `archive` if they rejected the
  rule itself). One short behavioral rule per record; no task facts, secrets or personal
  details. Pass `--explicit` only when the user said it.
- `add` refuses a near-duplicate and shows the existing record: update that one instead.
- Set `saved` only with `--saved-in`, and only for items actually written in Step 6.
  Approval alone is `approved`.
- Scope changes only through `promote`, after the user approves and the rule has been
  rewritten at the wider scope.
- Use the real session ID (the conversation's session file name) so a re-run in the same
  session is not counted twice.
- Keep keywords to 3-6 lowercase tags and reuse existing ones (`find` shows them).
