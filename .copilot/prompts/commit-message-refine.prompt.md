---
name: commit-message-refine
description: Refine and iterate on existing commit messages based on user feedback while maintaining Conventional Commits format.
---

# Refine Commit Message

Iteratively improve an existing commit message based on user feedback while maintaining **Conventional Commits** + **gitmoji** format compliance.

## Your Task

1. **Accept the current message** from the user
2. **Understand the feedback**: Ask clarifying questions if needed
   - "Is the message too long overall, or just the subject line?"
   - "Should we emphasize the refactoring or the logic change?"
   - "Are you unhappy with the type/scope choice?"

3. **Identify what to refine**:

| Feedback | Action |
|---|---|
| "Too long" | Trim subject; remove redundancy; move details to body |
| "Too vague" | Add specific detail; replace generic terms |
| "Wrong type" | Verify against actual change; update if incorrect |
| "Wrong scope" | Narrow or broaden scope; re-evaluate module affiliation |
| "Missing context" | Add 1-2 lines to body explaining WHY |
| "Emphasize X" | Reorder body bullets; highlight as primary change |
| "Add/remove ticket" | Insert or delete Refs/Closes footer lines |

4. **Refine while maintaining format constraints**:
   - Subject ≤72 characters
   - Imperative mood (no past tense: "Added", "Fixes")
   - Lowercase except proper nouns
   - No period at end of subject
   - Blank line between subject and body
   - Body: 2-4 lines explaining WHY, not WHAT

## Refinement Patterns

### Pattern 1: Shorten an Overlong Subject
```
❌ TOO LONG (98 chars):
✨ feat(api-gateway): add request rate limiting with sliding window algorithm and per-user quotas

✅ REFINED (65 chars):
✨ feat(api-gateway): add request rate limiting with quotas
```

Then move specifics to body:
```
- Implement sliding window algorithm
- Apply per-user quota enforcement
- Add Prometheus metrics for monitoring
```

### Pattern 2: Replace Vague Type with Specific Type
```
BEFORE:
🔧 chore(db): update connection pool settings

USER FEEDBACK: "Wasn't this a performance improvement?"

REFINED:
🚀 perf(db): optimize connection pool for throughput

- Increase pool_size from 5 to 10 for high-concurrency scenarios
- Add idle timeout to prevent stale connections
- Benchmark: 2s latency → 200ms latency for user queries
```

### Pattern 3: Separate Primary from Secondary Changes
```
BEFORE:
✨ feat(auth): add two-factor authentication and modernize type hints

AFTER (removes secondary from title):
✨ feat(auth): add two-factor authentication

- Implement SMS and email verification channels
- Modernize type hints to Python 3.10+ union syntax
- Reorganize imports for clarity
```

### Pattern 4: Add Breaking Change Footer
```
BEFORE:
✨ feat(api): replace session dict with SessionConfig object

AFTER:
✨ feat(api): replace session dict with SessionConfig object

BREAKING CHANGE: session dict parameter replaced with SessionConfig dataclass. Update all callers before upgrading to v2.0.
```

## Quick Reference: Common Refinements

**Too Long?**
→ Remove adjectives, use shorter synonyms, move details to body

**Too Vague?**
→ Add specific detail from the diff (e.g., "in login handler", "for bulk orders")

**Wrong Type?**
→ Reconsider: Did behavior change (feat/fix) or just structure (refactor)? Does it improve perf (perf)? Tests (test)?

**Missing Context?**
→ Add 1-2 lines in body explaining WHY the change was needed

**Emphasizing Wrong Thing?**
→ Reorder body bullets; put primary change first; consider swapping type

## Quality Checklist for Refined Message

- [ ] Subject ≤72 characters
- [ ] Gitmoji + type + scope + description present
- [ ] Imperative mood (no past tense)
- [ ] Lowercase except proper nouns
- [ ] No period at end of subject
- [ ] Body explains WHY (if included), not WHAT
- [ ] Body is 2-4 lines max
- [ ] Footer includes ticket refs if applicable
- [ ] BREAKING CHANGE clearly marked if applicable
- [ ] All user feedback addressed
- [ ] Message is still accurate to the diff

## When to Stop Refining

Stop after **2-3 iterations**. If refinement is still unclear:
- Suggest `@commit-message` to regenerate from scratch
- Or suggest `@commit-message-agent` for interactive guidance
- The message may need deeper analysis of the diff

## Example Refinement Session

```
User: Here's my message:
✨ feat(auth): add comprehensive multi-factor authentication support with SMS and email options

User Feedback: Too long, shorten the description

Refined:
✨ feat(auth): add multi-factor authentication support

Explanation: Removed "comprehensive", "SMS and email options" (can be in body if needed for context). Shaved 40 characters, now 61 chars total.
```
