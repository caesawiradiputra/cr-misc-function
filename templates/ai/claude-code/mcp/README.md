# MCP server templates

Copy a template into the repo root as `.mcp.json` (or merge its `mcpServers`
entry into the existing one). The file holds **no secrets**, so it is safe to
commit.

| Template | Server | Notes |
| --- | --- | --- |
| `postgres.mcp.json` | `postgres-mcp` (via `uvx`) | `--access-mode=restricted` is read-only; drop it only when writes are really needed |

## Where the secret lives

Claude Code does **not** load `.env` by itself. `.mcp.json` expands `${VAR}`
and `${VAR:-default}` in `command`, `args`, `env`, `url` and `headers` from the
environment of the Claude Code process. Three ways to supply the value, safest
first.

1. **Recommended: read `.env` inside the server command.** The template does
   this. It pulls only `POSTGRES_MCP_URI` out of the repo's `.env` and hands it
   to the server as `DATABASE_URI`:

   - Only the MCP server process gets the value. Claude's Bash tool and the
     rest of the session never see it, and nothing has to be set before
     launching `claude`.
   - `.env` is parsed with `grep`, not sourced, so other variables are not
     exported and a value with spaces or `$` cannot run as shell code.
   - Add `POSTGRES_MCP_URI=postgresql://user:password@host:5432/dbname` to the
     repo's `.env`. Use a dedicated variable so a production `DATABASE_URL` is
     never picked up by accident. The server starts from the repo root, so
     `.env` is found there.
   - Needs `bash`, so on native Windows run Claude Code from WSL or Git Bash.

2. **`.claude/settings.local.json` `env` block** (gitignored, denied to Claude
   by the `settings.local.json` deny rule). Use it when there is no `.env`,
   with `"env": {"DATABASE_URI": "${POSTGRES_MCP_URI}"}` in `.mcp.json`:

   ```json
   {
     "env": {
       "POSTGRES_MCP_URI": "postgresql://user:password@host:5432/dbname"
     }
   }
   ```

   This is a second copy of the secret, and the value reaches the whole Claude
   Code process. Check with `claude mcp list` that the variable expands.

3. **Export it in the launching shell** (`set -a; . ./.env; set +a; claude`).
   Avoid it: every variable in `.env` is exported to Claude's Bash tool and all
   child processes, and the `Read(**/.env)` deny rule does not stop `env` or
   `echo $VAR`.

Use a read-only database user for the MCP connection, and a dev or replica
database rather than production.

## Verify

`claude mcp list` shows a missing-variable warning for any unset `${VAR}`, and
`/mcp` inside a session shows whether the server connected.
