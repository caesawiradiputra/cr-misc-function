---
name: jira-ticket-kickoff
description: Set up or resume a working session for a change, whether or not it has a JIRA ticket. With a ticket ID (e.g. "set up a session for DA-1234", "start work on DA-1234", "resume DA-1234"), fetches and analyzes the requirement via the Atlassian MCP tools, then either syncs dev and creates the fea/fix branch + release/<TICKET-ID>/ folder (fresh) or checks out the existing branch and gives a progress recap (resume, if one already exists). Without a ticket - a quick fix, refactor, tuning, or other own-initiative change, often pasted directly into the prompt as a brief description or spec - skips the JIRA fetch, asks a few targeted clarifying questions to fill the gaps, then does the same branch/release-folder setup keyed by a slug instead of a ticket ID. Use this whenever the user gives a bare ticket ID, asks to start/resume/kick off ticket work, or describes an ad-hoc change (fix/refactor/tuning/etc.) they want to start working on - even without a ticket and even if they don't spell out all the steps.
---

# JIRA Ticket Kickoff

Bootstraps or resumes a working session around one change. First decide which of three paths applies, then follow it end to end.

## Step 0: Decide the path

- Look for a ticket ID pattern (`[A-Z]+-\d+`, e.g. `DA-1234`) in the user's message.
  - Phrased as a **recheck** (e.g. "recheck DA-1234", "any requirement updates on DA-1234", "did the IN- ticket change", "re-run the requirement check for DA-1234") → go straight to **Path D: Recheck requirement only** — skip Step 2 and the full fresh/resume flow entirely.
  - Otherwise, **found** → go to **Step 1: Fetch the JIRA ticket**, then **Step 2** decides Path A (fresh) vs Path B (resume).
  - **Not found**, and the user is instead describing a change directly (a quick fix, refactor, tuning, or other own-initiative work, however brief) → go straight to **Path C: No ticket**.
- If it's genuinely unclear which of these the user means, ask.
- If the user pastes a description *alongside* a real ticket ID, still fetch JIRA (it stays authoritative) but carry the pasted text forward as extra context for the brainstorming step.
- Repeating a plain "resume DA-1234" (no recheck phrasing) re-runs the whole Path A/B flow from scratch every time — the fetch, the branch checkout, the recap. That's harmless (nothing destructive re-triggers — Step 5b already leaves an existing release folder alone) but it's the expensive way to ask "did the requirement change." Use Path D for that instead.

## Step 1: Fetch and analyze the JIRA ticket

Do this before any git decision — the branch slug/type in Path A and the acceptance-criteria comparison in Path B both depend on it.

Call `mcp__plugin_atlassian_atlassian__getJiraIssue` with:
- `cloudId`: `"bfifinance.atlassian.net"` (the site hostname — try this directly first; only fall back to `getAccessibleAtlassianResources` if the call fails)
- `issueIdOrKey`: the ticket ID
- `fields`: the array `["summary", "description", "issuetype", "status", "priority", "labels", "comment", "issuelinks", "attachment"]` — pass it as an actual array, not a comma-separated string. This tool has no "default fields plus extras" behavior: passing `fields` at all replaces its normal default set entirely, so a typo or a dropped entry here means that field silently isn't in the response — there's no error to catch it.
- `responseContentFormat`: `"markdown"`

From the response, extract summary/title, issue type, description, acceptance criteria (parsed out of the description body), status, priority, labels. Everything you claim later must trace back to a field in this response — don't infer requirements that aren't there.

**On attachments — this MCP cannot retrieve or read attachment content, PDF or otherwise.** The `attachment` field only returns metadata: filename, size, and upload date. There's no Atlassian MCP tool here that downloads attachment bytes (the generic `fetch` tool only resolves Jira/Confluence ARIs, not attachment content URLs), and don't try routing an attachment URL through a generic web-fetch tool either — it needs Jira auth that tool won't have, and a failed or blank fetch there is easy to mistake for "nothing's there." Requirement content can live in an attached PDF/doc just as easily as in the description field, so treat attachment metadata as something to track and diff, the same way Step 1b tracks linked tickets: record filename + size + date for every attachment on both the `DA-` ticket and any linked `IN-` ticket, and if that list ever changes from what's on file, that's a signal worth surfacing even though the content itself is opaque to you.

### Step 1b: Check related tickets — the requirement may live elsewhere

A ticket assigned to the user (`DA-` prefix) is often a slice of a bigger initiative tracked under a different prefix (commonly `IN-`), and the `IN-` ticket is sometimes where the requirement actually gets updated — the `DA-` ticket's own description can go stale without anyone editing it. Don't skip this just because the `DA-` ticket's description looks complete; the whole risk is that it looks complete but isn't current.

This step must always end with a visible, explicit line of output — either the related tickets found, or a plain statement that none were found. Never let it fall through silently: a silent skip is indistinguishable from "the check ran and found nothing," which is precisely the failure mode this step exists to prevent.

- Look for an `issuelinks` key in the Step 1 response.
  - **Key absent entirely** (not even `"issuelinks": []`) — don't assume this means "no links." It's ambiguous between "genuinely no links" and "the field wasn't returned." Re-fetch once with `fields: ["*all"]` to check for certain before concluding either way, then say explicitly which it was ("no linked tickets" vs. "issuelinks came back empty even with `*all` — worth checking directly in the JIRA UI").
  - **Key present with entries** — read the linked issue keys from it.
  - **Key present but empty (`[]`)** — genuinely no linked tickets; state that plainly and move on.
- For any linked key matching `IN-\d+`, fetch it too via `getJiraIssue` (same `fields`/`responseContentFormat` as Step 1).
- Compare its description/comments against the `DA-` ticket's description:
  - If the `IN-` ticket has requirement detail the `DA-` ticket lacks, or appears to supersede/contradict something in the `DA-` ticket, treat the `IN-` ticket as authoritative for that part and **say so explicitly** — don't silently merge the two into one description and don't pick one to discard quietly.
  - If they're consistent, note that alignment briefly rather than staying silent about it.
- Other linked tickets (other `DA-`s, "duplicates", "blocks", etc.) — just list the keys/relationship for awareness, don't fetch them, unless the user asks.
- If there are multiple `IN-` links and it's unclear which is the live one, ask the user instead of guessing.

## Step 2: Check whether a branch for this ticket already exists

```powershell
git branch --list "*<TICKET-ID>*"
```

- **Match found** → the ticket is already in progress → **Path B: Resume**. Do not run the dev sync script — the user's branch and commits are the source of truth now, not `dev`.
- **No match** → **Path A: Fresh**.

## Path A: Fresh JIRA kickoff

### Step 3a: Derive branch type and slug

- **fea/ vs fix/ vs refactor/ vs perf/**: from `issuetype` (Bug/Defect → `fix/`; Story/Task/Feature/Improvement → `fea/`). Ask if genuinely ambiguous.
- **Slug**: from the summary — lowercase, non-alphanumeric runs collapsed to single hyphens, trimmed, capped around 40 characters at a word boundary.
- Resulting branch name: `fea/<TICKET-ID>-<slug>`, e.g. `fea/DA-1234-add-reject-tracking`.

### Step 4a: Sync the dev branch

Check `git status --porcelain` first. If dirty, stop and ask the user to commit or stash before running the sync script.

```powershell
powershell -File ".\scripts\powershell\git-check-sync-set-dev.ps1" -Force
```

Run from the target repo's root. `-Force` is required since this session can't answer the script's interactive confirmation prompt.

- Exit code `0` — `dev` synced and checked out. Continue.
- Exit code `2` — `dev` has diverged from `master`; script shows the diff and restores the original branch. Stop and show the user the diff summary.
- Anything else — surface the script's error output.

### Step 5a: Create the ticket branch

```powershell
git checkout -b <branch-name> dev
```

### Step 6a: Scaffold the release folder

```powershell
New-Item -ItemType Directory -Path "release\<TICKET-ID>\ddl"    -Force
New-Item -ItemType Directory -Path "release\<TICKET-ID>\data"   -Force
New-Item -ItemType Directory -Path "release\<TICKET-ID>\config" -Force
New-Item -ItemType Directory -Path "release\<TICKET-ID>\docs"   -Force
```

Only folders — no `CHANGELOG.md` yet (`/generate-pr-message` creates/updates that later). Write the fetched requirement into `release/<TICKET-ID>/docs/requirement.md`:

```markdown
# <TICKET-ID>: <Summary>

**Type:** <issue type>
**Status:** <status>
**Priority:** <priority>
**JIRA:** https://bfifinance.atlassian.net/browse/<TICKET-ID>

## Description

<description, converted from the markdown response>

## Acceptance Criteria

<extracted list, or "Not explicitly stated in the ticket">

## Related Tickets

<from Step 1b: linked IN- ticket(s) fetched, with a note on whether their content added to / superseded / matched the DA- description; other linked tickets listed by key and relationship only. "None linked" if Step 1b found nothing.>

## Attachments

<one line per attachment, per ticket: `<TICKET-ID>: <filename> (<size>, added <date>)`. "None" if a ticket has no attachments. This list is the baseline Path D diffs future rechecks against — a PDF/doc can carry requirement content this skill can't read, so a changed filename, size, or count later is itself the signal, even without knowing what's inside.>
```

### Step 7a: Summarize and brainstorm — don't jump to a plan

Present a short summary: what the ticket asks for, the acceptance criteria, anything pulled from a linked `IN-` ticket that changes the picture, and anything ambiguous or worth double-checking against the codebase.

Then invoke `superpowers:brainstorming`, using this summary (plus any pasted extra context from Step 0) as the seed intent. Don't produce an implementation plan yet — that's `superpowers:writing-plans`, later.

## Path B: Resume in-progress JIRA work

### Step 4b: Check out the existing branch

If more than one branch matched in Step 2, ask which one. Otherwise: check `git status --porcelain` first — if there are uncommitted changes that don't belong to the ticket branch, stop and ask before switching. If not already on it, `git checkout <branch-name>`.

Do not touch `dev`, `master`, or run the sync script — the ticket branch is already diverged from `dev` by design.

### Step 5b: Leave the release folder alone

If `release/<TICKET-ID>/` doesn't exist yet, scaffold it and write `requirement.md` as in Step 6a. If it already exists, don't touch it — don't overwrite `requirement.md`, and don't touch anything already dropped into `ddl/`, `data/`, `config/`, or `docs/`.

### Step 6b: Progress recap instead of brainstorming

```powershell
git log origin/dev..HEAD --oneline
git diff origin/dev...HEAD --stat
```

Cross-reference the commits/diff against the acceptance criteria from Step 1 (and Step 1b's related-ticket check) — call out what looks addressed, what looks untouched, any mismatch worth flagging. Since work on this ticket may have started before a requirement update landed, re-check any linked `IN-` ticket from Step 1b for changes since — if it's moved on from what `release/<TICKET-ID>/docs/requirement.md` has recorded, flag the drift explicitly rather than assuming the original requirement still holds. Hand the conversation back with a status-oriented question (what's left, blockers, how testing is going) rather than invoking `superpowers:brainstorming` — this is a check-in, not a design discussion, unless the recap surfaces a genuinely new question (a requirement drift like this counts as one).

## Path C: No ticket — ad-hoc change

Quick fixes, refactors, tuning, or other own-initiative changes rarely come with a JIRA ticket or a full spec — often just a line or two pasted into the prompt. Treat the thinness of the spec as the main risk here, not the git mechanics.

### Step 1c: Take the pasted description as the seed

Use whatever the user gave — a sentence, a paragraph, a rough spec — as the starting point. Don't wait for something more formal.

### Step 2c: Ask targeted clarifying questions before anything else

Because there's no ticket to fall back on for missing detail, ask a small number of pointed questions before touching git — not an exhaustive interrogation, just enough to remove the biggest ambiguities:

- What's the scope — which files/areas/services does this touch?
- What's the risk or blast radius — anything that could break if this goes wrong?
- What does "done" look like — how will you know it's finished/correct?
- Anything the description implies but doesn't state (e.g. "tune this query" — tune for what: latency, memory, lock contention)?

Skip any question the pasted description already answers. Fold the answers into the working spec you'll carry forward — this is the "more brainstorming" the thin-spec case needs, done by you before handing off, not deferred.

### Step 3c: Derive branch type and slug

- **Type** — `fea/`, `fix/`, `refactor/`, or `perf/` — from the description and the answers above. Ask directly if it's not obvious (e.g. "is this a fix, a refactor, or perf tuning?").
- **Slug** — derive from the description, but confirm or let the user edit it: there's no authoritative summary field to lean on the way JIRA provides one.
- Resulting branch name: `<type>/<slug>`, e.g. `refactor/repository-cleanup` or `perf/tune-order-query`.
- If you're already on a branch that looks like it's this same change, don't create a duplicate — check with the user before branching.

### Step 4c: Sync the dev branch

Same as Step 4a: dirty-check first, then run the sync script with `-Force` from the repo root.

### Step 5c: Create the branch

```powershell
git checkout -b <type>/<slug> dev
```

### Step 6c: Scaffold the release folder, keyed by slug

```powershell
New-Item -ItemType Directory -Path "release\<slug>\ddl"    -Force
New-Item -ItemType Directory -Path "release\<slug>\data"   -Force
New-Item -ItemType Directory -Path "release\<slug>\config" -Force
New-Item -ItemType Directory -Path "release\<slug>\docs"   -Force
```

Write `release/<slug>/docs/spec.md` (not `requirement.md` — there's no JIRA source, so don't imply there is one):

```markdown
# <slug>: <short title>

**Type:** <Feature/Fix/Refactor/Perf>
**Source:** Ad-hoc — no JIRA ticket

## Description

<the pasted description, plus the clarifying answers from Step 2c, written up as the working spec>
```

### Step 7c: Brainstorm with the enriched context

Present the working spec (pasted description + your clarifying answers) as a short summary, then invoke `superpowers:brainstorming` with it as the seed — same as Step 7a, just with a spec you helped assemble instead of one JIRA already had written down. Still no implementation plan yet.

## Path D: Recheck requirement only

For when you're already deep into a ticket — possibly in another repo's session entirely — and just want to know whether the requirement moved, without redoing the branch checkout or the full commit recap. This is the cheap, repeatable way to answer "did anything change," and it's safe to run as many times as you want: it never touches git and never overwrites what's already recorded.

### Step 1d: Confirm there's something to recheck against

Look for `release/<TICKET-ID>/docs/requirement.md`. If it doesn't exist, there's no prior snapshot to diff against — tell the user and fall back to Step 1/Path A instead (this is effectively a first kickoff, not a recheck).

### Step 2d: Re-fetch fresh

Run Step 1 and Step 1b exactly as written — always a live re-fetch, never trust a cached read, since a stale check is the whole failure mode being fixed here.

### Step 3d: Diff against what's recorded

Compare the freshly-fetched `DA-` description and any linked `IN-` ticket content against what's currently written in `requirement.md`'s Description / Related Tickets sections. Call out plainly:
- What's new or changed (and where — the `DA-` ticket itself, or the linked `IN-` ticket)
- What's unchanged
- Anything that now reads as a conflict with work already committed on the branch (worth a quick `git log`/`git diff` glance if the drift looks substantial — but that's a targeted look, not the full Step 6b recap)

### Step 3d-ii: Diff the attachment list — a required step, not an optional extra

This is its own checkpoint, not a footnote to Step 3d: Path D exists because a description-level diff alone already missed a real drift once (an updated requirement that only showed up in an attachment). Skipping this half of the comparison reproduces that exact failure. Every Path D run must end with an explicit line about attachments — never leave it out of the report just because the description-level diff already found something else to talk about.

Diff the freshly-fetched `attachment` metadata (on both the `DA-` ticket and any linked `IN-` ticket) against `requirement.md`'s Attachments section:
- **`requirement.md` has no Attachments section** (it predates this skill revision, or was never scaffolded with one) — don't skip the check because there's nothing to compare against. Report the current attachment list as a first-time baseline instead, say so explicitly, and add the section via Step 4d so the next recheck has something real to diff.
- **Count, filenames, or dates changed** — since attachment content is opaque to this skill, don't try to guess what changed inside the file. Say plainly which attachment(s) are new/changed/removed and on which ticket, and ask the user to open it and check manually, or paste the relevant updated content directly.
- **Unchanged** — say so anyway, in one line. A recheck that mentions nothing about attachments is indistinguishable from one that forgot to check them.

### Step 4d: Record the drift, don't silently overwrite

If there's drift — in the description, a linked ticket, or the attachment list — ask whether to append a dated section to `requirement.md`:

```markdown
## Requirement Update — <date>

<what changed and where it came from (DA- ticket edit, linked IN- ticket, or an attachment that needs manual review) — include a refreshed Attachments list if it changed>
```

Append only — never edit or delete the original Description/Acceptance Criteria/Related Tickets/Attachments sections. That original text is the record of what the requirement said when the branch was created; the point of Path D is to layer updates on top where they're visible, not to quietly rewrite history. If there's no drift at all, just say so — no file changes needed.

No branch operations, no brainstorming hand-off — this path ends at reporting the drift (and the update note, if the user wants it recorded).

## Pre-completion checklist

- [ ] Path chosen correctly: recheck phrasing → Path D; ticket ID present (not a recheck) → JIRA path (A or B); absent + change described directly → Path C
- [ ] Path A/B: ticket data fetched via the Atlassian MCP tool — nothing in the summary invented
- [ ] Path A/B/D: `fields` passed as an array including `issuelinks` and `attachment`; Step 1b produced a visible "found" or "none found" statement — never a silent skip; an absent `issuelinks` key was double-checked with `fields: ["*all"]` before being read as "no links"; any linked `IN-` ticket fetched and reconciled against the `DA-` ticket, with agreement/conflict called out explicitly rather than silently merged
- [ ] Path A/B: attachment metadata (filename/size/date) recorded in `requirement.md`'s Attachments section for the `DA-` ticket and any linked `IN-` ticket — never attempted to read attachment content, since no tool here can retrieve it
- [ ] Path A: existing-branch check ran before any dev sync; working tree was clean before the sync script ran; branch type/slug derived from JIRA data
- [ ] Path B: dev/master untouched; existing `release/<TICKET-ID>/` contents left alone; recap grounded in actual `git log`/`git diff` output; linked `IN-` ticket re-checked for drift since the branch was created
- [ ] Path C: clarifying questions asked and answered *before* branching; `spec.md` (not `requirement.md`) written from the assembled spec; type/slug confirmed with the user, not assumed
- [ ] Path D: re-fetched live rather than reasoning from memory; drift (if any) diffed against the existing `requirement.md`, not just re-summarized from scratch; attachment list diffed too, with any count/filename/date change flagged for manual review rather than guessed at; any update appended, original sections left untouched; no git or folder operations performed
- [ ] Session ends at a brainstorming discussion (Path A/C), a progress check-in (Path B), or a drift report (Path D) — never at a plan or code change
