---
name: code-review
description: Analyze code for logical bugs, security vulnerabilities, and performance bottlenecks. Outputs a structured markdown table with impact ratings and suggested fixes. Use when the user triggers /code-review, asks for a code review, or wants to inspect code quality. Accepts pasted code blocks, file paths, or staged git diffs as input.
---

# Code Review

Analyze code and produce a structured findings table.

## Trigger

`/code-review` followed by one of:
- A **code block** (pasted directly)
- A **file path** to review
- No argument = review the **currently staged git diff** (`git diff --cached`)

## Review Process

1. **Read** the input (code block, file contents, or git diff output).
2. **Analyze** for three categories:
   - **Logical bugs** — incorrect logic, off-by-one errors, null/undefined handling, race conditions, missing edge cases.
   - **Security vulnerabilities** — injection flaws, hardcoded secrets, insecure deserialization, path traversal, broken auth, SSRF, XSS.
   - **Performance bottlenecks** — N+1 queries, unnecessary allocations, missing indexes, blocking I/O, unbounded loops, redundant computation.
3. **Rate** each finding: High, Med, or Low impact.
4. **Output** the findings table.

## Output Format

```markdown
## Code Review Findings

| # | Impact | Category | Description | Suggested Fix |
|---|--------|----------|-------------|---------------|
| 1 | High   | Security | SQL injection via string concatenation in `query` | Use parameterized queries or ORM |
| 2 | Med    | Logic    | Off-by-one in loop boundary `i <= len(arr)` | Change to `i < len(arr)` |
| 3 | Low    | Perf     | Repeated `len()` call inside loop | Cache length before loop |
```

## Impact Rating Guide

| Rating | Criteria |
|--------|----------|
| **High** | Data loss, security breach, crash in production, incorrect business logic |
| **Med**  | Degraded performance, poor error handling, maintainability risk, subtle bugs |
| **Low**  | Style issues, minor inefficiencies, best-practice deviations |

## Rules

- If no issues found, output: `> No issues found. Code looks clean.`
- Group related findings under the same row when they share a root cause.
- Always include a concrete, actionable **Suggested Fix** (not vague advice).
- When reviewing a git diff, focus only on the changed lines, not the entire file.
- For file paths, read the file first, then review its full contents.
- Keep descriptions concise (one line). Expand only if the user asks for details.