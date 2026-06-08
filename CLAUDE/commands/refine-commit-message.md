# Refine Commit Message

Iteratively improve an existing commit message based on user feedback while maintaining **Conventional Commits** + **gitmoji** format compliance.

## Your Task

1. **Accept the current message** from the user (paste it in)
2. **Understand the feedback** — ask clarifying questions if needed:
   - "Is the message too long overall, or just the subject line?"
   - "Should we emphasize the refactoring or the logic change?"
   - "Are you unhappy with the type/scope choice?"
3. **Identify what to refine** and apply the appropriate pattern below
4. **Present the refined version** with a brief explanation of changes

---

## Refinement Action Map

| Feedback | Action |
| --- | --- |
| "Too long" | Trim subject; remove adjectives; move details to body |
| "Too vague" | Add specific detail; replace generic terms |
| "Wrong type" | Verify against actual change; update if incorrect |
| "Wrong scope" | Narrow or broaden scope; re-evaluate module |
| "Missing context" | Add 1-2 lines to body explaining WHY |
| "Emphasize X" | Reorder body bullets; highlight as primary change |
| "Add/remove ticket" | Insert or delete Refs/Closes footer lines |

---

## Format Constraints (Always Maintain)

- Subject ≤72 characters total
- Imperative mood: "Add" not "Added", "Fix" not "Fixes"
- Lowercase except proper nouns and acronyms
- No period at end of subject
- Blank line between subject and body
- Body: 2-4 lines explaining WHY, not WHAT
- Footer: `Refs DA-XXXX` or `Closes DA-XXXX`

---

## Refinement Patterns

### Pattern 1 — Shorten Overlong Subject

```text
❌ BEFORE (98 chars):
✨ feat(api-gateway): add request rate limiting with sliding window algorithm and per-user quotas

✅ AFTER (65 chars):
✨ feat(api-gateway): add request rate limiting with quotas

Body:
- Implement sliding window algorithm
- Apply per-user quota enforcement
- Add Prometheus metrics for monitoring
```

### Pattern 2 — Replace Vague Type

```text
❌ BEFORE:
🔧 chore(db): update connection pool settings

Feedback: "Wasn't this a performance improvement?"

✅ AFTER:
🚀 perf(db): optimize connection pool for throughput

- Increase pool_size from 5 to 10 for high-concurrency scenarios
- Add idle timeout to prevent stale connections
```

### Pattern 3 — Separate Primary from Secondary

```text
❌ BEFORE:
✨ feat(auth): add two-factor authentication and modernize type hints

✅ AFTER:
✨ feat(auth): add two-factor authentication

- Implement SMS and email verification channels
- Modernize type hints to Python 3.10+ union syntax
```

### Pattern 4 — Add Breaking Change Footer

```text
❌ BEFORE:
✨ feat(api): replace session dict with SessionConfig object

✅ AFTER:
✨ feat(api): replace session dict with SessionConfig object

BREAKING CHANGE: session dict parameter replaced with SessionConfig dataclass. Update all callers before upgrading to v2.0.
```

---

## Quick Tips

| Problem | Fix |
| --- | --- |
| Too long? | Remove adjectives; use shorter synonyms; move details to body |
| Too vague? | Add specific detail (e.g., "in login handler", "for bulk orders") |
| Wrong type? | Did behavior change? → feat/fix. Just structure? → refactor. Perf? → perf |
| Missing context? | Add 1-2 lines in body: WHY was this change needed |
| Wrong emphasis? | Reorder body bullets; put primary change first |

---

## Quality Checklist

- [ ] Subject ≤72 characters
- [ ] Gitmoji + type + scope + description present
- [ ] Imperative mood (no past tense)
- [ ] No period at end of subject
- [ ] Body explains WHY (if included), not WHAT
- [ ] Body is 2-4 lines max
- [ ] Footer includes ticket refs if applicable
- [ ] BREAKING CHANGE marked if applicable
- [ ] All feedback addressed
- [ ] Message still accurate to the actual diff

---

## When to Stop

Stop after 2-3 iterations. If refinement is still unclear:

- Suggest `/generate-commit-message` to regenerate from scratch
- The message may need deeper analysis of the diff with `git diff --staged`
