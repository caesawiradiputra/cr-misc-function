---
name: clean-gone
version: "1.0.0"
updated: "2026-06-18"
description: Delete local git branches marked [gone] (deleted on remote), including attached worktrees. Use when the user triggers /clean-gone, asks to clean up stale branches, or wants to prune gone branches. Supports --dry-run mode.
---

# Clean Gone Branches

Clean up local branches whose upstream was deleted on the remote (marked `[gone]`), removing any attached worktrees first.

## Argument Routing

| Arguments | Behavior |
| --- | --- |
| *(empty)* | Full flow: fetch -> identify -> confirm -> delete -> report |
| `--dry-run` or `dry-run` | List branches that would be deleted, without actually deleting them |

## Workflow

### Step 1 — Refresh remote tracking state

```powershell
git fetch --prune
```

Without `--prune`, deleted remote branches may not yet show as `[gone]`.

### Step 2 — Identify [gone] branches and worktrees

```powershell
git branch -v
git worktree list
```

- Branches prefixed `+` are checked out in a worktree — the worktree must be removed before the branch can be deleted
- Note the main worktree path (`git rev-parse --show-toplevel`) — never remove it

### Step 3 — Confirm with the user

`git branch -D` discards unmerged commits permanently. Present the list of branches (and any attached worktrees) that will be deleted and **proceed only after the user confirms**.

If no branches are marked `[gone]`, report that no cleanup was needed and stop.

### Step 4 — Remove worktrees and delete branches

```powershell
$root = git rev-parse --show-toplevel

$gone = git branch -v | Select-String '\[gone\]' | ForEach-Object {
    ($_.Line.TrimStart('+', '*', ' ') -split '\s+')[0]
}

foreach ($branch in $gone) {
    Write-Host "Processing branch: $branch"
    $wt = git worktree list | Select-String "\[$([regex]::Escape($branch))\]$"
    if ($wt) {
        $path = ($wt.Line -replace '\s+\S+\s+\[[^\]]+\]$', '')
        if ($path -ne $root) {
            Write-Host "  Removing worktree: $path"
            git worktree remove --force $path
        }
    }
    Write-Host "  Deleting branch: $branch"
    git branch -D $branch
}
```

### Step 5 — Report

Summarize which worktrees and branches were removed (or that nothing needed cleanup).
