# MCP server templates

Copy a template into the repo root as `.mcp.json` (or merge its `mcpServers`
entry into the existing one). The file holds **no secrets**, so it is safe to
commit.

| Template | Server | Notes |
| --- | --- | --- |
| `postgres.mcp.json` | `@modelcontextprotocol/server-postgres` (via `npx`) | Read-only by design (queries run in a read-only transaction). npm marks the package deprecated but it still works |
| `trino.mcp.json` | [`tuannvm/mcp-trino`](https://github.com/tuannvm/mcp-trino) | Go binary, see [Install mcp-trino](#install-mcp-trino). Read-only by default. Only the password is secret; host, user and catalog sit in `env` as placeholders. Also reaches Hive tables through the `hive` catalog |
| `maxcompute.mcp.json` | Alibaba's remote MaxCompute MCP | No secret: browser OAuth. Replace `<region-id>`, then `claude mcp login maxcompute`. Write SQL needs `mode=write` and your confirmation |
| `mysql.mcp.json` + `dbhub.mysql.toml` | [`@bytebase/dbhub`](https://github.com/bytebase/dbhub) (via `npx`) | Tested 2026-10-30. Copy the TOML to `.claude/dbhub.toml`. Read-only in the TOML (`readonly = true`, `max_rows`). Reads `MYSQL_HOST`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_NAME` from `.env`; rename them to the app's own. Also handles MariaDB |
| `sqlserver.mcp.json` + `dbhub.sqlserver.toml` | `@bytebase/dbhub` (via `npx`) | Tested 2026-10-30. Same layout as MySQL, with `SQLSERVER_*` variables; for a named instance or NTLM login see the DBHub DSN docs. No connection-level read-only exists for SQL Server, so the account's grants are the only hard guard |

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
   - Reuse the variables the app already has (see [Reuse the app's own
     variables](#reuse-the-apps-own-variables)). Only when the app has none for
     that database, add `POSTGRES_MCP_URI=postgresql://user:password@host:5432/dbname`
     to the repo's `.env`. The server starts from the repo root, so `.env` is
     found there.
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
through the Trino `hive` catalog, and no OSS server has been evaluated. Hologres
speaks the PostgreSQL protocol, so use the Postgres template for it. Check
`/mcp` after copying any template. Tested on 2026-10-30: Postgres (two servers; a write attempt was
rejected by the read-only transaction), MySQL and SQL Server (a `SELECT` ran and a
write attempt was rejected by DBHub's read-only mode). Trino reached its host but
the login was rejected, so it is not yet verified; MaxCompute has not been run.

DBHub also supports Oracle, MariaDB and SQLite, and can serve PostgreSQL as a
maintained replacement for the deprecated Postgres server. It reads `DSN` or
`DB_*` variables (and a `.env`) by itself; the templates still read `.env` in
the command with `grep`, so only the named variables reach the server. DBHub's
`--readonly` flag is deprecated, so read-only is set in the TOML.

**Check the account, not only the server.** The two Postgres servers tested
connect as a privileged user, so only the server's read-only
transaction blocks writes. Give the MCP a read-only role whenever possible.

## Install mcp-trino

Homebrew is not available on every machine (not in WSL by default), so install
the release binary. Replace `v4.3.1` and the `4.3.1` in the file names with the
[latest release](https://github.com/tuannvm/mcp-trino/releases), and use
`linux_arm64` on ARM:

```bash
d=$(mktemp -d) && cd "$d"
gh release download v4.3.1 -R tuannvm/mcp-trino \
  -p 'mcp-trino_4.3.1_linux_amd64.tar.gz' -p 'mcp-trino_4.3.1_checksums.txt'
grep linux_amd64 mcp-trino_4.3.1_checksums.txt | sha256sum -c -
tar -xzf mcp-trino_4.3.1_linux_amd64.tar.gz
install -m 755 -D mcp-trino ~/.local/bin/mcp-trino
```

`~/.local/bin` must be on `PATH`. Without `gh`, download the same two files
from the release page. The checksum comes from the same release, so it catches
a corrupt download, not a compromised release.

## Reuse the app's own variables

Before adding a variable only for the MCP, check how the app configures its
database: `config.py` or `settings.py` (a Pydantic `BaseSettings`, `os.getenv`
calls), `.env.template` and `docker-compose*.yml`. If it already reads
`DB_HOST`, `DB_USER`, `DB_PASSWORD` and so on, make the MCP read the same names
from `.env`, so one set of values serves the app and the MCP:

```json
{
  "mcpServers": {
    "postgres": {
      "command": "bash",
      "args": [
        "-c",
        "g(){ grep \"^$1=\" .env | cut -d= -f2- | tr -d '\\r'; }; exec npx -y @modelcontextprotocol/server-postgres \"postgresql://$(g DB_USER):$(g DB_PASSWORD)@$(g DB_HOST):$(g DB_PORT)/$(g DB_NAME)\""
      ]
    }
  }
}
```

Replace the names with the ones the app uses. A password with special
characters must be URL-encoded inside a URL; prefer a server that takes the
parts as separate variables (`mcp-trino` does). If the app's `.env` points at
production or a read-write account, use a read-only account for the MCP
instead and add a new variable for it. Add a new variable only when the app has
none for that connection.

## Read-only by default

Configure each database MCP so it cannot write, unless you ask for write
access. Use every layer the server or driver offers:

| Server | Server-side guard | Driver-level setting |
| --- | --- | --- |
| `@modelcontextprotocol/server-postgres` | Each query runs in a read-only transaction | Add `?options=-c%20default_transaction_read_only%3Don` to the URL (check with a write attempt on a dev database) |
| `mcp-trino` | Read-only by default; leave write queries disabled | None needed |
| MaxCompute remote MCP | Writes need `mode=write`; leave it out | None |
| MySQL, SQL Server and others | Depends on the server; check its flags | MySQL `SET SESSION TRANSACTION READ ONLY` where an init statement is accepted. SQL Server has no connection-level read-only |

The grants of the database account are the only guard that cannot be bypassed
by a setting, so use a read-only account whenever you can. Where a server and
driver offer no read-only option, say so in the setup report rather than
implying it is read-only.

## `.env` with Windows line endings

A `.env` saved with CRLF line endings leaves a trailing `\r` on every value that
`grep` and `cut` read, which showed up as a hostname ending in `\r` and a failed
login (found 2026-10-30). The templates pipe the value through `tr -d '\r'` to
strip it; keep that when you edit the command.
