---
description: Update the ticket handover inventory and propose the Jira handover comment
allowed-tools: Bash(python3:*), Bash(git:*), mcp__plugin_atlassian_atlassian__getJiraIssue, mcp__plugin_atlassian_atlassian__executeRead, mcp__plugin_atlassian_atlassian__addOrEditJiraIssueComment
---

Run the `handover` skill for the current ticket.

1. Resolve the ticket from the branch name (`git branch --show-current`); ask when there is none.
2. Run `python3 ~/.claude/skills/handover/handover.py check --ticket <TICKET>` and show what it
   lists.
3. Ask once: "any objects touched outside this session?" and record each answer with `add --state
   touched` and a `note`.
4. Run the posting procedure of the skill: resolve a pending post, `changed`, show the rendered
   text, and post only after the user's OK.
5. When Jira reads `Done`, offer the final post and `close`.
