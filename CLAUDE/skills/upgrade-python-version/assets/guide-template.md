# Python Upgrade Guide: {project} {from} → {to}

**Prepared:** {date} · **Branch:** `{branch}` · **Status:** {status: Ready / Blocked on dependency decisions / ...}

This upgrade moves `{project}` from Python {from} to {to}. It does **not**
change code structure or behavior:
- The code changes are syntax-only rewrites that produce identical runtime
  objects.
- Version strings in config move to {to}.
- Dependency bumps and behavior-change fixes are listed below for approval,
  and are applied only when marked ✅.

---

## 1. Summary

| Area | Result |
| --- | --- |
| Current Python (declared / deployed) | {e.g. pyproject ^3.8, .python-version 3.9, Docker python3.8} |
| Target Python | {to} |
| Dependencies | {e.g. 2 direct + 1 transitive bump needed, 1 approved} |
| Stdlib / behavior risks | {N breaks, N behavior, N deprecated — or none found} |
| Syntax modernization | {N fixes in N files, N typing imports removed} |
| Structure check | {exit 0/1 + one-line justification} |
| Verification | {compile ✅ · ruff F ✅ · import/OpenAPI ✅ · tests n/a · mypy …} |

## 2. Dependency changes (decision required)

{Paste the check_deps.py table. Then, per bump: what changed upstream that
matters to this project (from the changelog), the risk, and ✅ approved / ⏳
pending / ❌ rejected.}

System packages needed for source builds (Docker and dev machines):
{e.g. `apt install unixodbc-dev` for pyodbc — or "none"}

## 3. Stdlib and behavior risks

{Paste the scan_upgrade_risks.py table. For each row: the decision (applied as
an identical-object replacement / proposed fix below / deprecation only).}

### Proposed behavior-preserving fixes (not applied unless ✅)

| Location | Problem on {to} | Minimal fix | Status |
| --- | --- | --- | --- |
| {file:line} | {…} | {…} | ⏳ |

## 4. Syntax modernization (applied)

{Paste the upgrade_syntax.py output: rules table, items left for review,
deliberately excluded rules.}

Examples of what changed:

```python
# before
from typing import List, Optional, Union


def f(x: Optional[int]) -> Union[List[str], str]: ...


# after
def f(x: int | None) -> list[str] | str: ...
```

## 5. Configuration changes (applied)

| File | Before | After |
| --- | --- | --- |
| pyproject.toml | `{requires-python / python = "^3.8"}` | `{…}` |
| .python-version | `{…}` | `{to}` |
| ruff.toml | `target-version = "{…}"` | `target-version = "py{toNoDot}"` |
| mypy.ini | `python_version = {…}` | `python_version = {to}` |
| Dockerfile | `FROM {…}` | `FROM {…}` |
| .github/workflows/{…} | `python-version: {…}` | `python-version: "{to}"` |

## 6. Verification

{Paste check_structure.py output and justify every "non-annotation code
change" line with the rule that caused it. Then list each check with its
actual result; write "not run — {reason}" rather than omitting a check.}

| Check | Command | Result |
| --- | --- | --- |
| Structure unchanged | `python check_structure.py` | {…} |
| Compiles on {to} | `python -m compileall -q {pkg}` | {…} |
| No new ruff F findings | `ruff check --isolated --select F` | {baseline N → now N} |
| Imports + runtime annotations | `python -c "import …; app.openapi()"` | {…} |
| Tests | `{…}` | {…} |
| mypy | `{…}` | {…} |

## 7. Rollout

1. Install the system packages from section 2 in the Docker image and on dev machines.
2. Rebuild the image on the new base tag; run it in dev/SIT before production.
3. Watch logs for `DeprecationWarning` from section 3's deprecated items.

## 8. Rollback

Everything is in one branch: revert the commit(s), or `git checkout
{base-branch} -- .`, then rebuild the image on the old base tag. No data or
schema migration is involved.
