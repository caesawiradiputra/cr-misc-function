# Terminal Auto-Approval Patterns

Common safe commands for terminal auto-approval across AI-powered IDEs (Qoder, GitHub Copilot Chat, Cursor, etc.). These patterns let AI agents execute safe read-only and non-destructive commands without requiring user confirmation each time.

## Configuration Format

All VS Code-based IDEs use the same setting path:

```json
"chat.tools.terminal.autoApprove": {
    "command-name": true,
    "command-name": false,
    "/^regex-pattern$/": true,
    "/^regex-pattern$/i": true
}
```

- **Exact match**: `"cd": true` — matches only the exact command name
- **Regex match**: `"/^git (status\\b.*)$/": true` — matches command + arguments
- **Case-insensitive regex**: `"/^pattern$/i": true` — `i` flag for case-insensitive
- **Deny override**: `"rm": false` — explicitly block even if a broader pattern allows it

## Categorization

### Git (Read-Only)

Safe commands that only read repository state:

```jsonc
"git": true,                                  // Allow bare git
"/^git (status\\b.*)$/": true,                // git status, git status --short
"/^git (log\\b.*)$/": true,                   // git log, git log --oneline -10
"/^git (show\\b.*)$/": true,                  // git show, git show HEAD
"/^git (diff\\b.*)$/": true,                  // git diff, git diff --staged
"/^git (ls-files\\b.*)$/": true,              // git ls-files
"/^git (grep\\b.*)$/": true,                  // git grep "pattern"
"/^git (branch\\b.*)$/": true,                // git branch, git branch -a
"/^git (branch\\b.*-(d|D|m|M|-delete|-force)\\b.*)$/": false,  // Block branch delete/force
"/^git (remote\\s+-v\\b.*)$/": true,          // git remote -v
"/^git (tag\\s+-l\\b.*)$/": true,             // git tag -l
"/^git (stash\\s+list\\b.*)$/": true,         // git stash list
"/^git (rev-parse\\b.*)$/": true              // git rev-parse HEAD
```

### Python Tools

Linting, formatting, testing, and package management:

```jsonc
// Linting & formatting
"/^ruff\\s+(check|format)\\b/i": true,        // ruff check . / ruff format .
"/^mypy\\b/i": true,                           // mypy app/
"/^pylint\\b/i": true,                         // pylint app/
"/^flake8\\b/i": true,                         // flake8 app/
"/^black\\s+--check\\b/i": true,              // black --check (dry run only)
"/^isort\\s+--check\\b/i": true,              // isort --check (dry run only)

// Testing
"/^pytest\\b/i": true,                         // pytest tests/
"/^python\\s+-m\\s+pytest\\b/i": true,         // python -m pytest
"/^python\\s+-m\\s+mypy\\b/i": true,           // python -m mypy
"/^python\\s+-m\\s+ruff\\b/i": true,           // python -m ruff

// Package management (safe operations)
"/^pip\\s+(list|show|check|freeze)\\b/i": true, // pip list, pip show, pip check
"/^pip\\s+(install|uninstall)\\b/i": false,     // Block pip install/uninstall (use uv/poetry)
"/^uv\\s+(sync|add|remove|run|lock|pip\\s+list|pip\\s+show)\\b/i": true,
"/^poetry\\s+(install|lock|show|env\\s+info|env\\s+list|check|version|run\\s+(pytest|mypy|ruff))\\b/i": true,
"/^conda\\s+(info|list|env\\s+(list|export))\\b/i": true,
"/^conda\\s+activate\\b/i": true
```

### Node.js Tools

```jsonc
"/^npm\\s+(list|ls|outdated|view|info|version|run)\\b/i": true,
"/^npm\\s+(install|uninstall|ci)\\b/i": false,  // Block npm install (use uv/pnpm)
"/^npx\\b/i": true,                              // Allow npx (commonly used for tools)
"/^pnpm\\s+(list|ls|why|info)\\b/i": true,
"/^yarn\\s+(list|info|why|version|outdated)\\b/i": true,
"/^node\\s+--version\\b/i": true,
"/^npm\\s+run\\b/i": true,                       // npm run build, npm run test
"/^npm\\s+test\\b/i": true                       // npm test
```

### Docker (Read-Only)

```jsonc
"/^docker\\s+(ps|images|version|info|logs|inspect|stats|top|port|history|diff)\\b/i": true,
"/^docker\\s+(build|push|run|exec|rm|rmi|stop|kill|compose)\\b/i": false,
"/^docker\\s+compose\\s+(ps|logs|config|images|top|port|ls)\\b/i": true,
"/^docker\\s+compose\\s+(up|down|build|push|run|exec|restart|stop)\\b/i": false
```

### File System (Read-Only)

Safe navigation and inspection commands:

```jsonc
// Unix
"cd": true,
"ls": true,
"pwd": true,
"cat": true,
"head": true,
"tail": true,
"findstr": true,             // Windows grep equivalent
"wc": true,
"tr": true,
"cut": true,
"cmp": true,
"which": true,
"basename": true,
"dirname": true,
"realpath": true,
"readlink": true,
"stat": true,
"file": true,
"du": true,
"df": true,
"sleep": true,
"nl": true,
"grep": true,
"column": true,
"date": true,
"sort": true,
"tree": true,
"rg": true,                  // ripgrep

// Windows / PowerShell
"/^Get-ChildItem\\b/i": true,
"/^Get-Content\\b/i": true,
"/^Get-Date\\b/i": true,
"/^Get-Random\\b/i": true,
"/^Get-Location\\b/i": true,
"/^Write-Host\\b/i": true,
"/^Write-Output\\b/i": true,
"/^Out-String\\b/i": true,
"/^Split-Path\\b/i": true,
"/^Join-Path\\b/i": true,
"/^Start-Sleep\\b/i": true,
"/^Where-Object\\b/i": true,
"/^Select-[a-z0-9]/i": true,
"/^Measure-[a-z0-9]/i": true,
"/^Compare-[a-z0-9]/i": true,
"/^Format-[a-z0-9]/i": true,
"/^Sort-[a-z0-9]/i": true
```

### Blocklist (Always Deny)

Dangerous commands that should NEVER be auto-approved:

```jsonc
// File deletion
"rm": false,
"rmdir": false,
"del": false,
"Remove-Item": false,
"rd": false,
"erase": false,

// Disk/system operations
"dd": false,

// Process management
"kill": false,
"ps": false,
"top": false,
"Stop-Process": false,
"spps": false,
"taskkill": false,
"taskkill.exe": false,

// Network (potential data exfiltration)
"curl": false,
"wget": false,
"Invoke-RestMethod": false,
"Invoke-WebRequest": false,
"irm": false,
"iwr": false,

// Permission changes
"chmod": false,
"chown": false,
"Set-ItemProperty": false,
"sp": false,
"Set-Acl": false,

// Code execution (injection risk)
"jq": false,
"xargs": false,
"eval": false,
"Invoke-Expression": false,
"iex": false
```

### Regex Deny Overrides

Some commands are safe in simple form but dangerous with certain flags:

```jsonc
"/^column\\b.*-c\\s+[0-9]{4,}/": false,       // column with 4+ column width
"/^date\\b.*(-s|--set)\\b/": false,             // date --set (changes system time)
"/^find\\b.*-(delete|exec|execdir|fprint|fprintf|fls|ok|okdir)\\b/": false,  // find with destructive actions
"/^rg\\b.*(--pre|--hostname-bin)\\b/": false,   // rg with pre-processor (code exec)
"/^sed\\b.*(-[a-zA-Z]*(e|i|I|f)[a-zA-Z]*|--expression|--file|--in-place)\\b/": false,  // sed with edit/file flags
"/^sed\\b.*(/e|/w|;W)/": false,                 // sed with exec/write commands
"/^sort\\b.*-(o|S)\\b/": false,                 // sort with output file
"/^tree\\b.*-o\\b/": false                       // tree with output file
```

## IDE-Specific Configuration

### Qoder / VS Code with GitHub Copilot Chat

Place in `.vscode/settings.json` (workspace) or user settings (global):

```json
{
    "chat.tools.terminal.autoApprove": {
        "cd": true,
        "ls": true
    }
}
```

### Claude Code

Claude Code uses `.claude/settings.json` with a permissions model instead of auto-approve:

```json
{
  "permissions": {
    "allow": [
      "Bash(git status)",
      "Bash(git log*)"
    ],
    "deny": [
      "Bash(rm*)",
      "Bash(curl*)"
    ]
  }
}
```

### Cursor

Cursor uses a similar auto-approve pattern in its settings, under `cursor.terminal.autoApprove`.

## Best Practices

1. **Global vs Workspace**: Put universal rules (cd, ls, blocklist) in user-level settings. Put project-specific tools (poetry, conda, project scripts) in workspace settings.
2. **Deny overrides**: Always put deny rules AFTER allow rules. More specific patterns override broader ones.
3. **Principle of least privilege**: Only auto-approve commands that are safe and non-destructive.
4. **Review regularly**: As tools evolve, review patterns for new dangerous flag combinations.
5. **Test your patterns**: Use the regex tester to verify patterns match intended commands and reject dangerous variants.
6. **Document deviations**: If you deviate from these recommendations, document why in your project's settings file comments.
