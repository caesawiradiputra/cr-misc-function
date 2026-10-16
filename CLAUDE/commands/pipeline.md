---
description: Show where every open ticket stands (stage, git state, next step) and flag gaps between Jira, git and the logbook
allowed-tools: Bash(python3:*), Bash(git:*), Bash(gh:*)
---

# Pipeline board

Show every open ticket by stage with the next action. Read-only: nothing is written to Jira, git or the logbook without the user's OK.

## Steps

1. Refresh Jira first so the flags are live: run the logbook skill's step 0a (assigned DA tickets with `cache set --track yes --jira-status ... --updated ...`). For each ticket in `PAT`, read the issue changelog and store `--pat-since <date it entered PAT>`.
2. Run the board:

   ```bash
   python3 ~/.claude/skills/logbook/logbook.py pipeline
   ```

3. Show the output as is. For each `!` flag, propose the fix it names (Jira transition by target status, logbook `add`, `Done`, `/clean-gone`) and apply it only after the user confirms, one at a time.
4. A `CAB register not updated since ...` banner means the register file is older than the last CAB session (Monday and Wednesday, 15:00): its flags are hidden, so ask the user to refresh the file first. The "PAT done: propose Done" block is one batched proposal; each Jira transition still needs the user's OK.
5. If the board prints `STALE`, Jira could not be refreshed: say so, do not act on Jira-dependent advice, and offer to retry.
