# MCP server templates

Copy a template into the repo root as `.mcp.json` (or merge its `mcpServers`
entry into the existing one). The file holds **no secrets**: values come from
`${VAR}` references, so it is safe to commit.

| Template | Server | Notes |
| --- | --- | --- |
| `postgres.mcp.json` | `postgres-mcp` (via `uvx`) | `--access-mode=restricted` is read-only; drop it only when writes are really needed |

## Where the secret lives

`.mcp.json` expands `${VAR}` and `${VAR:-default}` in `command`, `args`, `env`,
`url` and `headers` from the environment of the Claude Code process. Claude
Code does **not** load `.env` by itself. Pick one source for the value:

1. **`.claude/settings.local.json` `env` block** (gitignored, denied to Claude
   by the `settings.local.json` deny rule):

   ```json
   {
     "env": {
       "POSTGRES_MCP_URI": "postgresql://user:password@host:5432/dbname"
     }
   }
   ```

2. **The shell that starts Claude Code**, for example from a `.env` you
   already keep: `set -a; . ./.env; set +a; claude`. One source of truth, and
   nothing is copied. Use a dedicated variable such as `POSTGRES_MCP_URI` so a
   production `DATABASE_URL` is never picked up by accident.
3. **Source `.env` inside the server command**, so nothing has to be set
   before launch. The server then reads the value straight from `.env`:

   ```json
   {
     "mcpServers": {
       "postgres": {
         "command": "bash",
         "args": ["-c", "set -a; . ./.env; exec uvx postgres-mcp --access-mode=restricted"]
       }
     }
   }
   ```

   `.env` must define `DATABASE_URI`, and the command runs from the repo root.

Use a read-only database user for the MCP connection, and a dev or replica
database rather than production.

## Verify

`claude mcp list` shows a missing-variable warning for any unset `${VAR}`, and
`/mcp` inside a session shows whether the server connected.
