# MCP server templates

Copy a template into the repo root as `.mcp.json` (or merge its `mcpServers`
entry into the existing one). The file holds **no secrets**, so it is safe to
commit.

| Template | Server | Notes |
| --- | --- | --- |
| `postgres.mcp.json` | `@modelcontextprotocol/server-postgres` (via `npx`) | Read-only by design (queries run in a read-only transaction). npm marks the package deprecated but it still works |
| `trino.mcp.json` | [`tuannvm/mcp-trino`](https://github.com/tuannvm/mcp-trino) | Go binary (`brew install tuannvm/mcp/mcp-trino`). Read-only by default. Only the password is secret; host, user and catalog sit in `env` as placeholders. Also reaches Hive tables through the `hive` catalog |
| `maxcompute.mcp.json` | Alibaba's remote MaxCompute MCP | No secret: browser OAuth. Replace `<region-id>`, then `claude mcp login maxcompute`. Write SQL needs `mode=write` and your confirmation |

Why not `uvx postgres-mcp`: on 2026-10-28 its current releases could not be
installed (the pinned `pglast==7.2.0` did not resolve), `uvx` fell back to the
old 0.1.0, which has no `--access-mode` flag, and an unpinned `mcp` 2.x crashed
it on import. Both showed up only as `CONNECTION_CLOSED` in `/mcp`. Re-check
before switching back.

Follow-up: decide whether to replace the deprecated
`@modelcontextprotocol/server-postgres` with a maintained server such as
`@bytebase/dbhub`. Nothing needs doing before then, because the current setup
works. Check that the replacement is read-only by default and can take the
connection string from an environment variable, which would also keep the URL
out of the process arguments.

## Where the secret lives

Claude Code does **not** load `.env` by itself. `.mcp.json` expands `${VAR}`
and `${VAR:-default}` in `command`, `args`, `env`, `url` and `headers` from the
environment of the Claude Code process. Three ways to supply the value, safest
first.

1. **Recommended: read `.env` inside the server command.** The template does
   this. It pulls only `POSTGRES_MCP_URI` out of the repo's `.env` and hands it
   to the server as its connection argument (the URL is then visible in the
   server's process arguments to other local users, as `ps` shows):

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
   with `"args": ["-y", "@modelcontextprotocol/server-postgres", "${POSTGRES_MCP_URI}"]`
   (and `"command": "npx"`) in `.mcp.json`:

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

## Servers not covered

OSS and Hive have no dedicated MCP server in these templates: Hive is reached
through the Trino `hive` catalog, and no OSS server has been evaluated. The
Trino and MaxCompute templates are built from each project's documentation and
have not been run against a live cluster, so check `/mcp` after copying.
