# Decision rules: adopt, variant, or drop

Apply these to every point where repos differ. The goal is to take the best practice, and keep a second option only when it is a different answer to a different situation, not an older answer to the same one.

## Evidence weight

- **Active repo**: a commit in the last 12 months (`commits_last_12_months > 0`). **Stale repo**: none. Count stale repos at half weight, and never let a stale repo be the only support for a rule.
- **Agreement** is counted among repos that *have the thing at all*. "3 of 5 repos with a Dockerfile" is the right denominator for a Docker rule, not "3 of 30".
- A rule seen in one repo only is "seen once" and needs the user's yes.

## The three outcomes

**Adopt (into common or the type doc)** when any of these holds:

1. It is already stated by an authoritative source (hard rule 3).
2. Most active repos with that thing agree, and it is not weaker than the authoritative source.
3. A minority does it, but it is clearly more robust on a *mechanical* test (see below). A better practice in a few recent repos is still the better practice.

**Variant ("use when ...")** when the difference is explained by a real constraint. Write the condition, not just the alternative. Typical conditions:

- a runtime or library limit (an old Python base because of a pinned dependency, an Airflow version that caps Python),
- a deployment shape (long-running service versus one-shot job: `EXPOSE`, health route, restart policy),
- a platform limit (no outbound network at build time, a vendor image that must be the base).

A variant needs a test the reader can apply ("use when the image must run Python 3.9"). If you cannot state one, it is not a variant.

**Drop (record as a deviation to migrate)** when the difference is drift: an older approach to the same problem, found mostly in stale repos, with no constraint behind it, or one that fails a mechanical test. List the repos so the user can migrate them. Dropping is not deleting evidence: the deviation list is part of the report.

## Mechanical tests (prefer the option that passes more)

- dependencies locked and installed from the lock in CI and in the image
- base image pinned by digest; tool versions pinned
- container runs as non-root; no `.env`/credentials baked in or committed
- config comes from the environment with a committed template of key names
- lint, type check and tests run automatically on pull requests
- registry login via the login action; inputs reach the shell through `env:`
- a health check or documented exit code exists for what the container does
- one way to do it (no parallel `requirements.txt` and `pyproject.toml` for the same deps unless the image needs it)

## Contested items

Ask the user when: the options are close on evidence, the choice changes how a team works (branching, test layout), the winner would contradict a stated preference in `CLAUDE.md`, or adopting it forces many repos to change. Show it as a short question with the evidence and your recommendation (recommendation first), per `AskUserQuestion` style if available.

## Common versus type

Decide at the **common** level first. A point moves to a type doc only when the best answer differs by type for a stated reason. If every type ends up with its own version of the same rule, the rule probably belongs in common with a variant condition, not in five type docs.

## Naming and style rules

Naming (modules, packages, functions, classes, constants, env vars, Docker image and container names, branch and tag names) is almost always common. Derive it from the sampled source, check it against the user's global rules (snake_case functions and variables, PascalCase classes, Google-style docstrings), and record only conventions the repos actually follow.
