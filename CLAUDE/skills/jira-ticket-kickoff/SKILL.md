---
name: jira-ticket-kickoff
description: Set up or resume a working session for a change, whether or not it has a JIRA ticket. With a ticket ID (e.g. "set up a session for PROJ-1234", "start work on PROJ-1234", "resume PROJ-1234"; or an Initiation-board key like "IN-3322", which is first cloned into a PROJ ticket and linked back), fetches and analyzes the requirement via the Atlassian MCP tools, then either syncs dev and creates the fea/fix branch + release/<TICKET-ID>/ folder (fresh) or checks out the existing branch and gives a progress recap (resume, if one already exists). Without a ticket - a quick fix, refactor, tuning, or other own-initiative change, often pasted directly into the prompt as a brief description or spec - skips the JIRA fetch, asks a few targeted clarifying questions to fill the gaps, then does the same branch/release-folder setup keyed by a slug instead of a ticket ID. Use this whenever the user gives a bare ticket ID, asks to start/resume/kick off ticket work, or describes an ad-hoc change (fix/refactor/tuning/etc.) they want to start working on - even without a ticket and even if they don't spell out all the steps.
---

# JIRA Ticket Kickoff

Bootstraps or resumes a working session around one change. First decide which of three paths applies, then follow it end to end.

## Writing links (applies to everything this skill writes)

Every URL goes out as a Markdown link, `[text](https://full-url)`, never as a bare URL. This covers files (`requirement.md`, notes), Jira descriptions and comments, PR bodies, and messages to the user.

- **Ticket keys are links every time they appear in prose you write**, not only the first time: `[PROJ-1234](https://<ATLASSIAN_SITE>.atlassian.net/browse/PROJ-1234)`. This includes "Cloned from", "Refs", "SRF attachments live on", and any "see also" mention. A plain `IN-3323` in a description is wrong.
- **Other URLs get descriptive text**, for example `[Customer API contract](https://...)`, not "click here" and not the raw address as the text.
- **Exceptions:** a URL inside a code block or inline code that is meant to be copied or run (a `curl` example, a `docker run` line) stays as literal text. When the tool returns or requires HTML (for example a description that came back with `appliedContentFormat: html`), use `<a href="https://...">text</a>` instead, since Markdown would not render there.
- Check before saving or sending: search the text you wrote for `http` and for ticket keys (`[A-Z]+-\d+`), and confirm each one sits inside a link.

## Step 0: Decide the path

- Look for a ticket ID pattern (`[A-Z]+-\d+`, e.g. `PROJ-1234`) in the user's message.
  - Phrased as a **recheck** (e.g. "recheck PROJ-1234", "any requirement updates on PROJ-1234", "did the IN- ticket change", "re-run the requirement check for PROJ-1234") → go straight to **Path D: Recheck requirement only** — skip Step 2 and the full fresh/resume flow entirely.
  - Ticket ID has the **`IN-` prefix** (Initiation board, e.g. `IN-3322`) and it is not a recheck → run **Step 0b: Resolve the IN- ticket to its PROJ- clone** first. It ends with a `PROJ-` key; from then on the whole flow (Step 1 onward) runs against that `PROJ-` key, not the `IN-` one.
  - Otherwise, **found** → go to **Step 1: Fetch the JIRA ticket**, then **Step 2** decides Path A (fresh) vs Path B (resume).
  - **Not found**, and the user is instead describing a change directly (a quick fix, refactor, tuning, or other own-initiative work, however brief) → go straight to **Path C: No ticket**.
- If it's genuinely unclear which of these the user means, ask.
- If the user pastes a description *alongside* a real ticket ID, still fetch JIRA (it stays authoritative) but carry the pasted text forward as extra context for the brainstorming step.
- Repeating a plain "resume PROJ-1234" (no recheck phrasing) re-runs the whole Path A/B flow from scratch every time — the fetch, the branch checkout, the recap. That's harmless (nothing destructive re-triggers — Step 5b already leaves an existing release folder alone) but it's the expensive way to ask "did the requirement change." Use Path D for that instead.

## Step 0b: Resolve an `IN-` ticket to its `PROJ-` clone

Requesters submit an SRF on the Initiation board (`IN`). Once it's approved, the engineer clones it into their own working board (`PROJ`) and works from the clone. When the user hands over an `IN-` key, do that clone automatically instead of asking them to do it by hand. Jira has no clone API, so "clone and move" here means: create a new `PROJ` issue carrying the `IN-` ticket's content, and link it back the way Jira's own Clone does. The `IN-` ticket itself is never moved or edited.

1. **Fetch the `IN-` ticket**: `getJiraIssue` with the same parameters as Step 1 (`view: "full"`, markdown), so `issuelinks`, description, and attachment metadata come back.
2. **Look for an existing clone first.** Scan `issuelinks` for any `PROJ-\d+` key (normally the "Cloners" link, but accept any link type to a `PROJ-` ticket). If one exists, say so ("IN-3322 is already cloned as PROJ-1850") and continue with that `PROJ-` key. Never create a second clone. If several `PROJ-` links exist and it's unclear which is the live one, ask.
3. **Check it's approved.** Look at the `IN-` ticket's status. If it doesn't clearly read as approved (e.g. still awaiting approval, rejected, cancelled), stop and ask the user before creating anything. The user said they clone after approval, so an unapproved status is a signal to double-check, not to proceed silently.
4. **Create the clone** with `createJiraIssue`, project `PROJ`:
   - `summary`: `SRF - ` followed by the `IN-` summary, trimmed of leading/trailing whitespace (IN summaries sometimes start with a space). E.g. `IN-3322` " Update customer onboarding flow" → `SRF - Update customer onboarding flow`. No "CLONE - " prefix. If the summary already starts with `SRF - `, don't double it.
   - `description`: the `IN-` description, and end it with a line `Cloned from [IN-3322](https://<ATLASSIAN_SITE>.atlassian.net/browse/IN-3322)` (using the real key). Every other mention of the `IN-` key in text you write into the clone ("Refs IN-3322", "SRF attachments live on IN-3322", a status note) is a link in the same form (see "Writing links" above), never the bare key.
   - Issue type: map from the `IN-` type to the closest `PROJ` type. Use `listJiraProjectIssueTypesMetadata` for `PROJ` if the name doesn't exist there; ask if genuinely ambiguous.
   - `priority` and `labels`: copy when the `PROJ` project accepts them; drop and mention any that are rejected.
   - `assignee`: the current user (the `IN-` ticket's assignee accountId, or `atlassianUserInfo`). `createJiraIssue` silently ignores an assignee argument (verified with IN-3322 → PROJ-1869: the clone came back unassigned), so set it afterwards with `editJiraIssue` `fields: {"assignee": {"accountId": "..."}}`. Also note `createJiraIssue` takes `issueType`, not `issueTypeName`.
   - Do not copy attachments. This MCP can't download attachment bytes, so tell the user which files exist on the `IN-` ticket and that they need to be re-attached on the `PROJ-` clone by hand if the team wants them there.
5. **Link the clone back.** Call `listJiraIssueLinkTypes` once to confirm the clone link type's exact name (Jira's default is `Cloners`, "clones" / "is cloned by"), then `createJiraIssueLink` (via `executeWrite`) with `inwardIssue` = the new `PROJ-` key and `outwardIssue` = the `IN-` key, so it reads "PROJ-xxxx clones IN-xxxx". If the link fails, the clone still exists: report both facts and give the user the key. Don't create a second clone to retry.
6. **Report in one visible line**: `Cloned IN-3322 → PROJ-1850 (linked as clones)`, or `Reused existing clone PROJ-1850`, plus the attachment note if relevant.
7. **Continue as a normal `PROJ-` kickoff.** Run Step 1 against the `PROJ-` key. Step 1b will find the `IN-` ticket through the clone link, so it stays the reconciliation source for later requirement updates. Then Step 2 onward as usual. A fresh clone has no branch, so it is Path A.

## Step 1: Fetch and analyze the JIRA ticket

Do this before any git decision — the branch slug/type in Path A and the acceptance-criteria comparison in Path B both depend on it.

Call `mcp__plugin_atlassian_atlassian__getJiraIssue` with:
- `cloudId`: `"<ATLASSIAN_SITE>.atlassian.net"` (the site hostname — try this directly first; only fall back to `getAccessibleAtlassianResources` if the call fails)
- `issueIdOrKey`: the ticket ID
- `view`: `"full"` — **not** the `fields` array. Verified 2026-09-28 against the live tool schema: on this tool, `fields` only accepts custom-field IDs (e.g. `"customfield_10010"`), not standard field names — passing `["summary", "description", "issuetype", ...]` there does not fetch what it looks like it would. The `view` levels aren't interchangeable either: `"compact"` (the default) and `"evidence"` both omit `description` and `attachment` entirely — confirmed by direct testing, a live fetch under `view: "evidence"` returned no `description`/`attachment` keys at all, while `issuelinks` was present. Only `view: "full"` reliably returns everything this skill needs.
- `responseContentFormat`: `"markdown"`

The `comment` field this tool returns is a count only (`{"total": N}`), never comment bodies, at any view level — use `listJiraIssueComments` if actual comment text is ever needed (not required by the extraction below).

From the response, extract summary/title, issue type, description, acceptance criteria (parsed out of the description body), status, priority, labels. Everything you claim later must trace back to a field in this response — don't infer requirements that aren't there.

**On attachments — this MCP cannot retrieve or read attachment content, PDF or otherwise.** The `attachment` field only returns metadata: filename, size, and upload date. There's no Atlassian MCP tool here that downloads attachment bytes (the generic `fetch` tool only resolves Jira/Confluence ARIs, not attachment content URLs), and don't try routing an attachment URL through a generic web-fetch tool either — it needs Jira auth that tool won't have, and a failed or blank fetch there is easy to mistake for "nothing's there." Requirement content can live in an attached PDF/doc just as easily as in the description field, so treat attachment metadata as something to track and diff, the same way Step 1b tracks linked tickets: record filename + size + date for every attachment on both the `PROJ-` ticket and any linked `IN-` ticket, and if that list ever changes from what's on file, that's a signal worth surfacing even though the content itself is opaque to you.

### Step 1b: Check related tickets — the requirement may live elsewhere

A ticket assigned to the user (`PROJ-` prefix) is often a slice of a bigger initiative tracked under a different prefix (commonly `IN-`), and the `IN-` ticket is sometimes where the requirement actually gets updated — the `PROJ-` ticket's own description can go stale without anyone editing it. Don't skip this just because the `PROJ-` ticket's description looks complete; the whole risk is that it looks complete but isn't current.

This step must always end with a visible, explicit line of output — either the related tickets found, or a plain statement that none were found. Never let it fall through silently: a silent skip is indistinguishable from "the check ran and found nothing," which is precisely the failure mode this step exists to prevent.

- Look for an `issuelinks` key in the Step 1 response.
  - **Key absent entirely** (not even `"issuelinks": []`) — don't assume this means "no links." It's ambiguous between "genuinely no links" and "the field wasn't returned." This should be rare with `view: "full"` (which has consistently returned `issuelinks` as an array, even empty, in testing) — but if it happens, re-fetch once with `fields: ["*all"]` (a separate, still-supported mechanism on this tool, distinct from `view`) to check for certain before concluding either way, then say explicitly which it was ("no linked tickets" vs. "issuelinks came back empty even with `*all` — worth checking directly in the JIRA UI").
  - **Key present with entries** — read the linked issue keys from it.
  - **Key present but empty (`[]`)** — genuinely no linked tickets; state that plainly and move on.
- For any linked key matching `IN-\d+`, fetch it too via `getJiraIssue` (same `view`/`responseContentFormat` as Step 1).
- Compare its description/comments against the `PROJ-` ticket's description:
  - If the `IN-` ticket has requirement detail the `PROJ-` ticket lacks, or appears to supersede/contradict something in the `PROJ-` ticket, treat the `IN-` ticket as authoritative for that part and **say so explicitly** — don't silently merge the two into one description and don't pick one to discard quietly.
  - If they're consistent, note that alignment briefly rather than staying silent about it.
- Other linked tickets (other `PROJ-`s, "duplicates", "blocks", etc.) — just list the keys/relationship for awareness, don't fetch them, unless the user asks.
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
- Resulting branch name: `fea/<TICKET-ID>-<slug>`, e.g. `fea/PROJ-1234-add-reject-tracking`.

### Step 4a: Sync the dev branch

Check `git status --porcelain` first. If dirty, stop and ask the user to commit or stash before running the sync script.

Use the counterpart matching the session's actual reported environment (per the global CLAUDE.md's "detect, don't assume" rule) — never assume Windows just because the PowerShell form is listed first:

```powershell
powershell -File "C:\Users\<WINDOWS_USERNAME>\Documents\Repo\cr-misc-function\cr-misc-function\scripts\powershell\git-check-sync-set-dev.ps1" -Force
```

```bash
bash /home/<user>/repo/cr-misc-function/cr-misc-function/scripts/bash/git-check-sync-set-dev.sh --force
```

Run from the target repo's root. The force flag is required since this session can't answer the script's interactive confirmation prompt (`-Force` on the PowerShell script, `--force` on the bash port).

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
**JIRA:** [<TICKET-ID>](https://<ATLASSIAN_SITE>.atlassian.net/browse/<TICKET-ID>)

## Description

<description, converted from the markdown response>

## Acceptance Criteria

<extracted list, or "Not explicitly stated in the ticket">

## Related Tickets

<from Step 1b: linked IN- ticket(s) fetched, with a note on whether their content added to / superseded / matched the PROJ- description; other linked tickets listed by key and relationship only. Write every ticket key as a link, `[IN-3322](https://<ATLASSIAN_SITE>.atlassian.net/browse/IN-3322)`. "None linked" if Step 1b found nothing.>

## Attachments

<one line per attachment, per ticket: `<TICKET-ID>: <filename> (<size>, added <date>)`. "None" if a ticket has no attachments. This list is the baseline Path D diffs future rechecks against — a PDF/doc can carry requirement content this skill can't read, so a changed filename, size, or count later is itself the signal, even without knowing what's inside.>
```

### Step 6a-i: Ensure the gitignored scratch folder exists

For temporary per-ticket files the user wants to hand over (e.g. the DDL of a source table, sample data, exported schemas), use `scratch/<TICKET-ID>/` at the repo root. Make sure `scratch/` is in the repo's `.gitignore` (add it if missing, with a short comment) and verify with `git check-ignore -v scratch/<TICKET-ID>` before creating `scratch/<TICKET-ID>/`. Tell the user the path. Read from it on request; never commit or copy its contents into `release/` without asking, since anything worth shipping should be written as a proper file under `release/<TICKET-ID>/`.

### Step 6a-ii: Ensure the local Jira documents folder exists

The user keeps each ticket's SRF PDFs and other supporting files outside the repo, in `Documents/Work/{Domain}/Jira/{TICKET-ID} - {Jira Title}/`. Create it for a new ticket so there's a place to drop the files (also run this in Path B if it's missing):

- **Base path**: WSL/bash `/mnt/c/Users/<WINDOWS_USERNAME>/Documents/Work/`; native Windows `C:\Users\<WINDOWS_USERNAME>\Documents\Work\`.
- **`{Domain}`**: the existing folder under `Work/` that matches the repo's umbrella folder (e.g. a repo in the `billing` umbrella maps to a `Billing` domain folder). Look at what exists under `Work/` and match; if none clearly matches, ask rather than inventing a new domain folder.
- **`{Jira Title}`**: the ticket summary as it stands in PROJ (so it includes the `SRF - ` prefix for clones), with characters Windows forbids (`\ / : * ? " < > |`) replaced by a space or dropped, and repeated spaces collapsed. Example: `PROJ-1869 - SRF - Update customer onboarding flow`.
- Check whether a folder starting with `{TICKET-ID}` already exists under `{Domain}/Jira/` first; if so, use it and don't create a second one.
- Create the folder with a `docs` subfolder (`mkdir -p`). Tell the user its path and that this is where to drop the SRF PDFs.

When the user says PDFs have been added there, read them locally. The Read tool's PDF mode needs `pdftoppm`, which isn't installed here, so use `uv run --with pypdf python` with `pypdf.PdfReader(...).pages[i].extract_text()` and collapse whitespace with `re.sub(r'\s+', ' ', text)` (the raw text comes out one word per line). Record what the PDF says in `requirement.md` as an appended dated section. Table-layout PDFs may lose structure, so say so if a table looks garbled.

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

Same as Step 4a: dirty-check first, then run the sync script (PowerShell or bash, matching the session's environment) with its force flag from the repo root.

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

Compare the freshly-fetched `PROJ-` description and any linked `IN-` ticket content against what's currently written in `requirement.md`'s Description / Related Tickets sections. Call out plainly:
- What's new or changed (and where — the `PROJ-` ticket itself, or the linked `IN-` ticket)
- What's unchanged
- Anything that now reads as a conflict with work already committed on the branch (worth a quick `git log`/`git diff` glance if the drift looks substantial — but that's a targeted look, not the full Step 6b recap)

### Step 3d-ii: Diff the attachment list — a required step, not an optional extra

This is its own checkpoint, not a footnote to Step 3d: Path D exists because a description-level diff alone already missed a real drift once (an updated requirement that only showed up in an attachment). Skipping this half of the comparison reproduces that exact failure. Every Path D run must end with an explicit line about attachments — never leave it out of the report just because the description-level diff already found something else to talk about.

Diff the freshly-fetched `attachment` metadata (on both the `PROJ-` ticket and any linked `IN-` ticket) against `requirement.md`'s Attachments section:
- **`requirement.md` has no Attachments section** (it predates this skill revision, or was never scaffolded with one) — don't skip the check because there's nothing to compare against. Report the current attachment list as a first-time baseline instead, say so explicitly, and add the section via Step 4d so the next recheck has something real to diff.
- **Count, filenames, or dates changed** — since attachment content is opaque to this skill, don't try to guess what changed inside the file. Say plainly which attachment(s) are new/changed/removed and on which ticket, and ask the user to open it and check manually, or paste the relevant updated content directly.
- **Unchanged** — say so anyway, in one line. A recheck that mentions nothing about attachments is indistinguishable from one that forgot to check them.

### Step 4d: Record the drift, don't silently overwrite

If there's drift — in the description, a linked ticket, or the attachment list — ask whether to append a dated section to `requirement.md`:

```markdown
## Requirement Update — <date>

<what changed and where it came from (PROJ- ticket edit, linked IN- ticket, or an attachment that needs manual review) — include a refreshed Attachments list if it changed>
```

Append only — never edit or delete the original Description/Acceptance Criteria/Related Tickets/Attachments sections. That original text is the record of what the requirement said when the branch was created; the point of Path D is to layer updates on top where they're visible, not to quietly rewrite history. If there's no drift at all, just say so — no file changes needed.

No branch operations, no brainstorming hand-off — this path ends at reporting the drift (and the update note, if the user wants it recorded).

## Logbook

After the kickoff or resume recap, propose a logbook row for the ticket (`/logbook`:
`status` = `In progress`, `task` from the ticket summary; Path C uses the
slug as `ticket`; `notes` only for a requirement difference or decision worth keeping). Write it after the user's OK. On Path B, update the existing row
instead of adding one. Path D (recheck only) logs nothing.

## Pre-completion checklist

- [ ] Path chosen correctly: recheck phrasing → Path D; ticket ID present (not a recheck) → JIRA path (A or B); absent + change described directly → Path C
- [ ] `IN-` key given: Step 0b ran first: existing `PROJ-` clone checked for before creating; approval status checked; at most one clone created and linked back; attachments not copied and the user told; then the rest of the flow ran against the `PROJ-` key
- [ ] Path A/B: ticket data fetched via the Atlassian MCP tool — nothing in the summary invented
- [ ] Path A/B/D: fetched with `view: "full"` (not the `fields` array — that only accepts custom-field IDs on this tool, not standard field names); Step 1b produced a visible "found" or "none found" statement — never a silent skip; an absent `issuelinks` key was double-checked with `fields: ["*all"]` before being read as "no links"; any linked `IN-` ticket fetched and reconciled against the `PROJ-` ticket, with agreement/conflict called out explicitly rather than silently merged
- [ ] Path A/B: attachment metadata (filename/size/date) recorded in `requirement.md`'s Attachments section for the `PROJ-` ticket and any linked `IN-` ticket — never attempted to read attachment content, since no tool here can retrieve it
- [ ] Path A: existing-branch check ran before any dev sync; working tree was clean before the sync script ran; branch type/slug derived from JIRA data
- [ ] Path A/B: local `Documents/Work/{Domain}/Jira/{TICKET-ID} - {Title}/docs` folder checked for (reused if a `{TICKET-ID}` folder already exists) or created, and the user told where to drop the SRF PDFs
- [ ] Path B: dev/master untouched; existing `release/<TICKET-ID>/` contents left alone; recap grounded in actual `git log`/`git diff` output; linked `IN-` ticket re-checked for drift since the branch was created
- [ ] Path C: clarifying questions asked and answered *before* branching; `spec.md` (not `requirement.md`) written from the assembled spec; type/slug confirmed with the user, not assumed
- [ ] Path D: re-fetched live rather than reasoning from memory; drift (if any) diffed against the existing `requirement.md`, not just re-summarized from scratch; attachment list diffed too, with any count/filename/date change flagged for manual review rather than guessed at; any update appended, original sections left untouched; no git or folder operations performed
- [ ] Links: every URL and every ticket key in text written to a file, a Jira description or comment, or a PR body is a Markdown link (`[PROJ-1234](https://<ATLASSIAN_SITE>.atlassian.net/browse/PROJ-1234)`); none left bare (see "Writing links")
- [ ] Session ends at a brainstorming discussion (Path A/C), a progress check-in (Path B), or a drift report (Path D) — never at a plan or code change
- [ ] Logbook row proposed (Path A/B/C) and written only after the user's OK; none for Path D
