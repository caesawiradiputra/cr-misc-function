# Bruno collection generator: design

Status: draft for review, 2026-11-02. Nothing is built yet.

## Intent and why

The user keeps API collections by hand, mostly for Bruno (some for Postman). Two problems:

1. Writing one request per endpoint, per repo, is slow and repetitive.
2. Some existing collections hold secrets in plain text inside the requests, so the repo cannot be shared safely. The user decided to recreate the collections from scratch with this skill, so the skill is not given access to the old repo.

This skill, `bruno-collection`, reads a repo's code and writes a ready-to-use Bruno collection, one collection per repo. It also scans Bruno collections for plain-text secrets, so the user can check a collection before it is committed or shared.

The reference is a hand-made Bruno collection in the user's Windows documents folder. It is a small example of the format: a root `opencollection.yml`, an `environments/` folder, one folder per environment with a `folder.yml`, and request files.

## Goals

- **One collection per repo**, named after the repo, with one request per endpoint and per mode.
- **Two modes per endpoint**, as two separate requests:
  - `fixed`: literal sample values.
  - `random`: values generated at send time (fake data).
- **Three Bruno environments, `LOCAL`, `DEV` and `PROD`**, with identical variable names. `LOCAL` points at the app as the repo's VS Code launch settings run it; the `DEV` and `PROD` hosts are placeholders. Secrets are secret variables with no value.
- **A token request when the code declares a token endpoint**, with the token captured per environment (see "Tokens captured from a response"), so a DEV token is never sent to PROD or the other way round.
- **Endpoints come from the repo's code.** FastAPI is the first and only framework in version 1.
- **Naming standard** (below) applied to everything the skill generates, so generated and cleaned-up collections look the same.
- **Secret scan** for Bruno collections (read-only, and its report never contains any part of a secret value).
- **Maintained through Claude chat sessions.** After the first generation, logic changes, new requests and request updates are made by Claude following the skill's rules. The user edits only values, directly in Bruno.
- **A documentation and change log per collection**, in a `docs/` folder inside the collection, written as an OKF bundle (see "Documentation and change tracking").

## Non-goals

- No other frameworks in version 1 (Flask, Django and others come later, one discovery module each).
- No sending requests, no real credentials, no contact with any live service.
- No Postman in version 1: it is neither generated nor scanned. It can be added later.
- No migrating or rewriting existing collections. The old collections are recreated from scratch by the skill, and the skill does not read the old repo. The scan reports; the user cleans.
- No reset button or reset script inside Bruno in version 1. Resetting a request to its original values and schema is done in a Claude chat session from the stored original (see "Re-running and maintaining a collection").
- No tracking of edits made by hand in Bruno. The docs record only changes made through the skill, and the add-only rule means a hand edit is never overwritten.
- No test assertions. The token capture script is the only post-response script.
- No token refresh or expiry handling in version 1: an expired token fails visibly and the user runs the token request again.
- Bruno's built-in OAuth2 auth is not used in version 1. It stays an option for APIs with a standard flow.

## Anti-goals (a failure even if it works)

- A scan report, log or chat message that shows any character of a secret value, or any line of a scanned file.
- A real secret ever written to a generated file, a log or the report. This includes tokens: they live only in runtime variables, never in an environment or collection file.
- Random data that looks like real personal data. Random values carry an obvious test marker.
- Running the target repo's code. The skill reads source only: it never imports the app, never starts it, never reads `.env*`.

## Decisions by the user

| Topic | Decision |
| --- | --- |
| Granularity | One collection per repo |
| Requests | One for each endpoint in the repo's code |
| Modes | Every endpoint has a fixed and a random mode |
| Environments | `LOCAL`, `DEV` and `PROD` as Bruno environments, not folders (`LOCAL` added later by the user: it follows the VS Code launch settings) |
| Proxy or load balancer | `DEV` and `PROD` may sit behind nginx or another proxy; recorded as notes for now, the user will provide an nginx sample later |
| Host addresses | Left as placeholders |
| Framework | FastAPI first |
| Naming | The standard below, recorded as the skill's standard |
| Scan | A leftover-secret scan for Bruno collections is part of the skill; Postman is dropped from version 1 |
| Tokens | In version 1: a token request and per-environment capture (below) |
| Re-running | Add-only: new endpoints get files, existing files are never overwritten |
| Maintenance | Changes (logic, new or updated requests) go through Claude chat sessions; the user edits only values |
| Documentation | A `docs/` folder per collection, as an OKF bundle if it helps (it does: see below) |
| Resetting a request | Option C: the original sample and schema are kept in `docs/requests/`, and a chat action restores a request from them; no in-Bruno script in version 1 |
| Scan fixes | Report-only; the report shows no character of any value |

## Calls made by the author (reject any of them)

1. **Format:** the `opencollection.yml` format used by the reference, not `.bru` files.
2. **Two requests per endpoint**, named `... (fixed)` and `... (random)`, so the mode is chosen by choosing the request.
3. **Source reading is static** (Python `ast`), not by importing the app. The sample repo fails at import without its secrets and opens database and search connections, so importing is unsafe. Reading an existing `openapi.json` instead is **out of scope for version 1**.
4. **Output location:** `<output root>/<repo-name>/`, default output root `/mnt/c/Users/<WINDOWS_USERNAME>/Documents/bruno/`, outside the repo. The user can name another root.
5. **Random values per request**, in a small `before-request` script on each random request, not one large collection-level script as in the reference. Fixed requests carry no script of their own.
6. **The auth header is always added** when the skill finds one, in both environments, even if the code checks it only in production.
7. **All parameters are included** in both modes. Optional ones with no example value are added disabled in fixed mode and filled in random mode.
8. **The scan is report-only** (it never edits a file). Decided by the user.
9. **"Except the value itself" means** environment values (hosts), secret values, and any sample value the user has typed over a generated one. Claude never replaces a value that is no longer the generated placeholder, and never reads or prints a secret value. (This is the author's reading of the user's words.)
10. **Location in this repo:** `CLAUDE/skills/bruno-collection/` with a stdlib-only helper (Python 3.9 and newer), mirrored to `~/.claude/skills/`, tests under `tests/`. The repo is public, so no company hosts, names or real values appear in the skill, its tests or its examples.

## Behaviour

### Discovery (FastAPI)

- Find the `FastAPI(...)` app, then follow `include_router(...)` calls across modules and **combine prefixes along the chain** (for example an app-level router prefix plus a route prefix plus the route path).
- Read each `@router.get/post/put/patch/delete(...)` and `add_api_route`. Take method, path, tags, the function name, the docstring, and the parameters.
- Parameters: path, `Query(...)`, `Header(...)`, `Body(...)` and Pydantic request models (including nested models and lists). Read type, required or optional, defaults, and constraints (`min_length`, `ge`, `le`, regex, enums).
- Routes registered dynamically, or things the reader cannot resolve (aliases, conditional registration, prefixes that are not literals), are **listed as skipped** with file and line. The skill never guesses.
- The report separates three outcomes and never lets one stand for another:
  - **Found and resolved:** the endpoint is generated.
  - **Found but not statically resolvable:** listed with file, line and reason; nothing is generated for it.
  - **No route discovered:** says only that the reader found none. It is not proof that the repo has none.
- Both Pydantic v1 and v2 style models must parse (the sample uses v1 with `= None` defaults).

### Fixed mode

Sample values come from, in order:

1. An "example input" block in the route's docstring (the sample repo has one per route).
2. `example=` or `examples=` on `Query`, `Body` or `Field`, and `Config.schema_extra` / `json_schema_extra` on models.
3. A default value in the code.
4. A visible `TODO` placeholder. The report lists every `TODO`. A sample value that contains `{{` is never written (Bruno has no escape, and it resolves nested placeholders): it becomes a `TODO` and is reported.

### Random mode

- Values come from the declared type and constraints: strings, integers, floats, booleans, dates and datetimes, UUIDs, enums (pick a member), lists, nested models.
- Strings carry a test marker prefix (for example `TEST_`), numbers and identifiers stay visibly synthetic, as the reference does with its `999` and `TEST` prefixes.
- Query, path and header values are stored as runtime variables named `random_<field>` (nested fields use the full field path) and used through `{{random_<field>}}`. The body of an object-body request is written in the Body tab with one variable per top-level field (`"customer_id": "{{random_customer_id}}"`; a number, bool, list or object is unquoted and its variable holds JSON text), so the body shown is the body sent and the user can edit it. A body field whose name equals a query, path or header parameter gets `random_body_<field>`, so one never overwrites the other. A list body, or a model body together with embedded fields, is built as one object with `req.setBody` (the Body tab shows a shape preview). The random helper functions are repeated at the top of each request script (the desktop app does not share functions between collection and request scripts).
- Limit to state in the report: random values prove the request shape and validation, not real results (invented identifiers usually return nothing).

**Constraint contract.** A random value either satisfies every declared constraint the generator supports, or the report says it could not. It is never a guessed value that may violate a constraint.

| Constraint | Version 1 |
| --- | --- |
| `min_length`, `max_length` (strings, lists as `min_items`, `max_items`) | Supported; the test marker prefix is shortened or dropped to fit, never to exceed `max_length` |
| `ge`, `gt`, `le`, `lt`, `multiple_of` | Supported |
| Date and datetime bounds (`gt`, `lt`, `ge`, `le`) | Supported |
| Enums and `Literal` | Supported |
| Nested models and required nested fields | Supported, to a depth limit (3); a deeper or recursive model is reported |
| Regex `pattern` | Only a small subset (literals, character classes, simple quantifiers, anchors); anything else is unsupported |
| Unsupported or contradictory constraints (for example `min_length` above `max_length`) | The field gets a visible `TODO`, the request is marked **incomplete** in the report with the field name and reason |

**Acceptance test:** generated random payloads are validated against the fixture's own Pydantic models (v1 through `pydantic.v1`, and v2), including boundary cases for each supported constraint. Unsupported constraints must produce the `TODO` and the report line, never a value.

### Authentication

Detected, in this order, with the file and line reported:

1. FastAPI security helpers: `APIKeyHeader`, `APIKeyQuery`, `HTTPBearer`, `HTTPBasic`, `OAuth2PasswordBearer`.
2. A dependency or middleware that reads a named header and compares it to a configured value (the sample repo does this in a logging middleware, with the header name `apikey`, checked only when the environment is production).
3. No recognized pattern: no header is added, and the report says "no auth pattern recognized, check middleware". This is not proof that the API has no auth.

The header name stays as the API expects it. Only the value is a variable (for example `apikey: {{apiKey}}`). For a bearer scheme backed by a token endpoint the value is `Bearer {{access_token}}` (see "Tokens captured from a response").

### Tokens captured from a response

Applies only when discovery finds a token endpoint (for example `OAuth2PasswordBearer(tokenUrl=...)` and the route at that URL). If none is found, none of this is generated.

- **One token request**, `auth/Get token`, not a fixed/random pair. Its credentials are never random: invented credentials cannot succeed. The credential inputs the route declares (for example `username` and `password`, or `clientId` and `clientSecret`) become **secret environment variables with no value** in `DEV` and `PROD`, and the request refers to them as `{{...}}`.
- **Capture:** the request's post-response script saves the token under a name that carries the environment, as a runtime variable:

  ```javascript
  bru.setVar("access_token_" + bru.getEnvName().toLowerCase(), res.body.access_token);
  ```

  So `LOCAL` writes `access_token_local`, `DEV` writes `access_token_dev` and `PROD` writes `access_token_prod`. The field name (`access_token`) comes from the route's response model; `access_token` is the default when the model does not say.
- **Use:** one collection-level `before-request` script copies the active environment's token into the name every request uses:

  ```javascript
  bru.setVar("access_token", bru.getVar("access_token_" + bru.getEnvName().toLowerCase()));
  ```

  Requests then send `Authorization: Bearer {{access_token}}` (or the scheme the code declares) and carry no script of their own.
- **Why this shape:** a runtime variable is one value per name and has the highest precedence, so a single `access_token` fetched in PROD would overwrite the DEV token and the next DEV request would send a **PROD token to the DEV host**. Bruno has no confirmed way to build a variable name inside `{{ }}`, so the suffix is built by script.
- **Failure is visible:** if the active environment has no token yet, the copy yields nothing and the request fails with a missing token, instead of sending the other environment's token.
- **Not used:** `bru.setEnvVar` (writes into the environment file) and `bru.setCollectionVar` (saves to disk), because either could put a token in a file.
- The lowercased environment name must match the suffix, so the environment names in the naming standard are the only place where an environment name appears in a variable name.

**Behavioral tests for token isolation** (two layers, because they prove different things):

1. **Automated script test.** Run the generated scripts in Node against a small mock `bru` object (`getEnvName`, `setVar`, `getVar`) that follows Bruno's documented semantics, through this sequence: fetch a DEV token and send a DEV request; switch to PROD, fetch a PROD token, send a PROD request; switch back to DEV and confirm the DEV token is used; start an environment with no token and confirm the request ends with no token (a visible failure), never the other environment's token; confirm nothing was written to any file. This proves the script logic, not Bruno itself. The test is skipped with a clear message when Node is not installed.
2. **Live check in the real Bruno app** (a release gate, like the prompt coach's live checks): the same five steps by hand, using a local stub token endpoint. Environment switching is state inside the running app. The Bruno CLI starts a fresh process per run, so it very likely cannot replay the sequence (to be confirmed in milestone 0).

### Environments

`environments/LOCAL.yml`, `environments/DEV.yml` and `environments/PROD.yml`, same variables in all three:

| Variable | Value | Secret |
| --- | --- | --- |
| `baseUrl` | `LOCAL`: from the VS Code launch settings (below), for example `http://localhost:5000`; `DEV` and `PROD`: placeholders such as `https://<dev-host>` and `https://<prod-host>` | no |
| the auth variable, for example `apiKey` | empty | yes |
| token request inputs, for example `clientId`, `clientSecret` (only when a token endpoint exists) | empty | yes |

The route prefix from the code stays in the request URL (`{{baseUrl}}/prefix/path`). The `baseUrl` variable carries a `description` saying it is the URL as clients reach it, including any proxy path prefix.

**`LOCAL` base URL from the VS Code launch settings.** Discovery reads `.vscode/launch.json` (JSON with comments and trailing commas, so a small tolerant reader). It picks the first run configuration that starts the discovered app (`uvicorn`, `hypercorn`, `fastapi dev`, `gunicorn` or `python -m <module>`), and reads the host and port from its arguments (`--port`, `--host`, `--bind host:port`) and, when the configuration sets them, from `HOST` and `PORT` keys of its `env`. `0.0.0.0` becomes `localhost`; the scheme is `https` only when an SSL option is present. If nothing is found, `baseUrl` is `http://localhost:<port>` and the report says so. Other matching configurations are listed in the report, not used. The launch file's `envFile` is never read and no other `env` value is copied, because those can hold secrets.

**Proxy and load balancer notes (open).** `DEV` and `PROD` may be served through nginx or another proxy or load balancer, which can add a path prefix, strip one, terminate TLS, or enforce a key before the app sees the request. This is not designed yet. Until the user provides an nginx sample, `docs/environments.md` carries an explicit note for `DEV` and `PROD` ("proxy or load balancer: unknown, fill from the nginx configuration"), the `baseUrl` description mentions the path prefix, and the final report lists it as something to fill. When the sample arrives, extend this design (for example how a stripped or added prefix maps to `baseUrl`).

**Corporate Apigee gateway (open, noted 2026-11-03).** The user will run the generated requests through the corporate Apigee API gateway, details to follow. Apigee typically adds its own path prefix (the API proxy base path), its own credential (an API key or an OAuth token issued by the gateway, which may differ from the app's own auth) and may rewrite or reject headers. None of this is designed yet: the generator keeps the app's own route prefix and auth, `docs/environments.md` carries a note for `DEV` and `PROD` ("gateway: Apigee, base path and credential unknown, fill when known"), and the report lists it. When the details arrive, extend this design (gateway base path in `baseUrl`, a gateway key or token variable per environment).

### Output layout

```text
<output root>/<repo-name>/
├── opencollection.yml
├── .gitignore                 ← ignores .env*, node_modules, OS files
├── environments/
│   ├── DEV.yml
│   └── PROD.yml
├── auth/                      ← only when a token endpoint exists
│   ├── folder.yml
│   └── Get token.yml
├── <tag or resource>/
│   ├── folder.yml
│   ├── Get <resource> (fixed).yml
│   └── Get <resource> (random).yml
└── docs/                      ← OKF bundle: documentation and change log
    ├── index.md
    ├── log.md
    ├── environments.md
    ├── auth/token.md          ← only when a token endpoint exists
    └── requests/<method>-<path-slug>.md
```

`opencollection.yml` lists `docs` in its Bruno `ignore` list (next to `node_modules` and `.git`, as the reference does) so Bruno does not show it. Whether Bruno honours that for a folder of Markdown files is to be checked.

### Endpoint identity and collisions

- **Identity** of an endpoint is its HTTP method plus the **full resolved path** with path parameter names kept (for example `GET /prefix/orders/{order_id}`). The identity is stored as `resource` in the endpoint's `docs/requests/` concept and is how sync matches code to the collection, so a user renaming a request file in a chat session does not create a duplicate.
- **File names** come from the identity and the mode. If two different identities map to the same file name (for example two paths that slug the same way), **neither is written**: the report lists both with source `file:line` and "needs a naming decision". A collision is never resolved by overwriting, skipping one silently, or inventing a suffix.
- **Changed identity** (method or path changed) is a **new endpoint** plus a **disappeared endpoint**. If the function name and parameters match, the report may suggest "possible rename" as a hint only. Nothing is deleted or renamed.
- **Duplicate operation names** in the source do not matter for identity. Only method plus path does. Two routes with the same identity are reported as a conflict.
- **Tests:** two endpoints that slug to one file name; a changed path; a changed method; a new endpoint whose file name already exists; the same identity declared twice.

A final report lists (the token request and the `auth` finding included): endpoints found, requests written, endpoints skipped (with reason), `TODO` placeholders, where auth was found, and the placeholders the user must fill in.

### Naming standard

| Item | Convention | Example |
| --- | --- | --- |
| Environment names | Uppercase, short, the team's names; more can be added later with the same variables | `LOCAL`, `DEV`, `PROD` |
| Variable names | Identical in every environment; only the value changes; never contain the environment name | `baseUrl` in both |
| Config variables | `camelCase`, named by what the value is | `baseUrl`, `apiKey`, `bearerToken`, `clientId`, `clientSecret`, `dbPassword` |
| More than one service | Prefix with the service | `ordersApiKey`, `billingApiKey` |
| Runtime variables set by scripts | `snake_case`; `random_` prefix for generated fake data; a plain name for a value captured from a response | `random_id_number`, `access_token` |
| Captured token per environment (the only name with an environment in it) | `<name>_<env, lowercase>` | `access_token_dev`, `access_token_prod` |
| Header names | Exactly as the API expects | `apikey: {{apiKey}}` |
| Collection | The repo name | `<repo-name>` |
| Folders | One per tag or resource | `orders` |
| Requests and files | `<Action> <resource> (fixed\|random)`; the file name equals the request name; the method is not repeated when the path ends in an action word (`get`, `list`, `create`...), e.g. `/phone/api/get_by_priority` gives `Get phone by priority`; other paths use `<Method> <resource>` | `Get orders by id (fixed)` |

### What is a secret

- **Secret variable, empty in every file:** API keys, tokens, passwords, client secrets, cookies, and any URL that carries a credential or a signature.
- **Normal environment variable:** anything that differs per environment and is not secret (host, identifiers).
- **Stays in the request:** constant sample inputs.
- Bruno marks secrets with `secret: true`; the value is kept by the app outside the collection folder.
- A real host is not a secret, but in a public repo it stays a placeholder.

### Secret scan

`scan <folder>` reads Bruno files (`.yml`, `.bru`, environments) and reports, read-only. The script reads the files on the user's machine; only its report reaches the chat.

**Report format:** one line per finding, `file:line  kind  length`. Nothing else.

- **No character of any value** is printed, not even the first or last. For a short key even two characters reveal too much. The report gives the kind and the length only.
- **No line and no surrounding text** from a scanned file is ever printed.
- **Paths:** a path is printed relative to the scanned folder, and only when every segment passes a path check (no JWT-shaped, key-assignment-shaped or long opaque segment, no `user:password@`). A path that fails is printed as `<path-redacted:N>`, where `N` is a stable index the user can map to the file in their own shell. A path is never printed from an error message.

**What it looks for:**

- Auth or key headers (`Authorization`, `apikey`, `X-API-Key` and similar) whose value is not a `{{variable}}`.
- Variables named like secrets (`key`, `token`, `secret`, `password`, `pass`, `credential`) that hold a non-empty value or are not marked secret.
- Bearer tokens, JWT-shaped strings (`eyJ...`), private-key blocks, URLs with credentials, long opaque strings.
- A missing `.gitignore` rule for `.env*`.

**Failure contract.** The guarantee holds on every path, not only the normal report:

- Exceptions, tracebacks, parser errors and debug output never include scanned content, a matching line, an excerpt or a value fragment. The script catches everything at the top level and prints only a generic error class and step (for example `scan error: parse, file index 7`).
- A file that cannot be read or parsed safely (binary, malformed, too large, bad encoding) is reported as **scan incomplete**, with its index and the generic reason. The final summary then says "incomplete", and the exit code is non-zero. Such a file is never counted as clean.
- There is no verbose or debug mode that prints content.
- There is no fallback to reading the collection in chat: after a scan failure, Claude reports the generic error and stops, and the user decides.

**Behaviour:** it exits non-zero when it finds something or when the scan is incomplete, and suggests the variable name from the naming standard. It cannot recognize a secret in an unusual shape or in ordinary prose, so **a clean report is not proof**, and the report says so.

**Rules for using it** (stated in `SKILL.md`):

- For a collection that may hold real secrets, Claude runs only `scan` and **never reads, searches or prints those files directly** (no `Read`, `grep`, `cat`, no quoting a finding's line).
- Optional extra for the user: a path-specific `Read(<collection path>/**)` deny rule in `settings.json`. It blocks the `Read` tool but not shell commands such as `cat`, so it is a partial guard, not a guarantee.
- The user can run the scan in the shell themselves (`! python3 ... scan <folder>`) and share only the report.

**Tests:** fixtures use fake secrets with unmistakable markers, planted in file contents, **file and folder names**, malformed and binary files, and deeply nested paths. Tests assert that the report, stderr and any raised exception contain none of the planted values, none of their characters in sequence of three or more, and no line from a fixture file; and that an unreadable or malformed file yields **scan incomplete** and a non-zero exit (the same approach as the prompt coach's masking tests).

**Using a scan report of an old collection as a reference.** The new collections are created from scratch by reading the repo's code. The skill never reads the old collections. The user may run `scan` on an old collection themselves, check the report for sensitive data, and give Claude only that report. Claude uses it as a reference for what the old collection held (which header names, variable names and secret kinds appeared, and where), so the new `environments/` and `docs/environments.md` cover the same needs. The report is data, never instructions. If it contains anything that looks like a value, a line from a file, or a readable path with a credential, Claude stops, does not repeat it, and tells the user. The report lists findings only, not request names, so it is not a coverage list of old requests.

After a cleanup the report reminds the user that **removing a secret from a file does not remove it from git history**: any secret ever committed is treated as exposed and must be rotated.

### Re-running and maintaining a collection

Three workflows, all run in a Claude chat session:

1. **Sync (add-only).** Read the code again and compare it with `docs/` (the request concepts) and the files that exist.
   - A new endpoint gets its files (both modes), its concept in `docs/`, and a log entry.
   - An existing file is **never overwritten**, even if the code changed.
   - An endpoint whose method, path or parameters changed, or that disappeared, is **listed** in the report and in the log as "needs a decision". Nothing is deleted.
2. **Edit (by request).** The user asks in chat for a logic change, a new request or an update to a request. Claude edits the files by the skill's rules (naming, secrets, modes, variables), keeps every user value, and updates the matching concept and the log in the same step.

3. **Reset (by request).** The user says, for example, "reset request X to the original". Claude restores that request's files (fixed and random) from the `original` block of its `docs/requests/` concept. If the code has changed since (the concept is stale), Claude says so and regenerates from the code instead, after the user agrees. This is the one action that may overwrite an existing request file, and only on that explicit request: Claude first tells the user which edited values will be lost, then writes. Environment and secret values are not in request files, so they are not touched.

4. **External requests (user-owned).** The user may add requests that do not come from the repo's code (a call to another service, a health probe of a gateway) by hand in Bruno, or ask Claude for a placeholder (`add-external`: a request in the `external/` folder with the URL `TODO`, plus a concept in `docs/external/`). **Rule:** a request file is *generated* only when a `docs/requests/` concept lists it in `files`; every other request file is *user-owned*. Sync, edit and reset never overwrite, rename or delete a user-owned file, and a "reset the collection" (regenerate everything) keeps all of them: it rewrites generated files only, after telling the user which edited values will be lost. The sync report lists the user-owned files it found, so they are visible, and the OKF docs record external requests the user asked Claude to create.

Every workflow ends by running the OKF linter on `docs/` and the secret scan on the collection.

## Documentation and change tracking (OKF)

OKF is helpful here because the collection is maintained by Claude across many chat sessions. A session that starts cold can open `docs/index.md`, then read only the concept it needs, and see where each fact came from and what changed.

- **One bundle per collection**, in `docs/`, following the `okf-writer` skill's rules: concept files with frontmatter, `index.md` as the map, `log.md` as the change history, linted with its `okf_lint.py`. Run its spec check (`okf_watch.py check --max-age 14`) before writing a bundle.
- **Concepts:**
  - `requests/<method>-<path-slug>.md`: one per endpoint, covering both modes, with an `original` block (fenced JSON): the generated fixed sample for every parameter and the body, and the schema (field names, types, constraints, required or optional), so a request can be reset. Resource `GET /prefix/path`, the request names, the parameters and where each fixed or random value comes from, the auth used, and the source `file:line` in the repo.
  - `environments.md`: variable names, which are secret, who fills each one, and which request uses them. **Never any value.**
  - `auth/token.md`: the token request, the per-environment variable names and the copy script.
- **`log.md`:** newest date first. Each entry says what changed (request names), why (the user's request in chat, or "new endpoint found by sync"), and the source. Sync and edit both append to it.
- **Provenance:** `generated.by` is `claude-code/<model>`, new content is `status: draft`, and `verified` is added only when the user says they reviewed that concept (okf-writer rules). Editing a verified concept leaves its old `verified` entry and the report says the review no longer covers the new text.
- **No sensitive data in the docs**: placeholders for hosts, no values, no tokens. The docs sit with the collection outside this public repo, but the rule is the same.

## Constraints

- Python helper uses only the standard library and runs on Python 3.9 and newer. The target repo's source is parsed with the interpreter running the helper, so syntax newer than that interpreter is reported as skipped, not as an error.
- WSL/bash. The skill never reads `.env*`, `token.json`, or `settings.local.json`.
- Markdown follows the repo's style (fenced languages, `| --- |` separators, names in backticks).
- Checked in Bruno's documentation while writing this design: `bru.setVar` creates runtime variables (temporary, highest precedence), `bru.getEnvName()` returns the active environment name, and `bru.setEnvVar` / `bru.setCollectionVar` persist to disk. Not confirmed: building a variable name inside `{{ }}`, and whether `bru.setEnvVar` keeps a value out of the file when the variable is marked secret.
- **Plan milestone 0 is a gate: verify Bruno before any generator code.** Against a pinned Bruno version (recorded in the skill and in each collection's `docs/`), confirm and write down, with a tiny hand-made collection opened in the real app: the exact YAML for path parameters, query parameters, JSON and form bodies, headers and the `auth` block; how collection-level and request-level scripts are represented and in what order they run; that `bru.setVar`, `bru.getVar` and `bru.getEnvName()` behave as assumed in each script context (before-request, post-response); that runtime variables are visible to later requests; the token request's body format and post-response script structure; and whether `docs` in the ignore list hides a Markdown folder. The reference shows only `GET` requests with query parameters, so none of the rest is confirmed by it. Nothing in the generator may be built on an assumption this milestone has not confirmed."

## Left to the builder

- Module split and test layout (use a small generic FastAPI fixture app in the tests, not a real company repo).
- The exact YAML field layout for bodies, path parameters and scripts, after checking the documentation.
- Heuristics for the "name looks like a secret" list, kept in one place so they are easy to extend.
- How the report is worded.
- Which `docs/` files the helper writes mechanically (parameters, sources, names) and which text Claude writes (descriptions, the reason in `log.md`).
- Whether the collection-level script is written into `opencollection.yml` like the reference or kept elsewhere, after checking the schema.
- How token responses that are not `access_token` JSON (other field names, other flows) are handled; version 1 may report them as skipped.

## Questions for the user

No open design questions. The Bruno details listed in "Plan milestone 0" are **verification tasks** that the plan must track, not facts the design assumes are settled. The earlier questions are decided: re-running is add-only, the scan is report-only and Bruno-only (Postman dropped). Call 9 is the author's reading of "except the value itself"; reject it if it is wrong.

## Revision history

- 2026-11-02: first draft with the user's decisions (environments, modes, tokens, add-only sync, OKF docs, Bruno-only report-only scan).
- 2026-11-02: external design review (APPROVE WITH CHANGES, F-01 to F-06) applied: scanner failure contract and path rule (F-01), Bruno verification as plan milestone 0 (F-02), two-layer token isolation tests (F-03; the review's "real Bruno switching test" became an automated mock test plus a live check, because the CLI very likely cannot switch environments inside one run; milestone 0 confirms it), endpoint identity and collision policy (F-04), random constraint contract (F-05), three-state discovery report (F-06).
- 2026-11-02: second review (APPROVE, ready for the implementation plan). The "no open questions" line now points to milestone 0 as verification tasks. The four plan gates it names: milestone 0 recorded, scanner non-disclosure on all failure paths, live token-isolation check before token workflows are used, add-only sync proven never to overwrite or silently resolve a collision.
- 2026-11-02: the user will recreate the collections from the repo's code and may give Claude a scan report of an old collection (made and checked by the user) as a reference. Added "Using a scan report of an old collection as a reference" under the secret scan.
- 2026-11-02: plan self-review (strongest model) applied: random bodies are built as one object; `openapi.json` reading is out of scope for version 1; the output goes to an NTFS disk, so names are compared case-folded and invalid characters are replaced.
- 2026-11-02: plan Task 0 done in Bruno 4.3.0 (see `CLAUDE/skills/bruno-collection/references/bruno-format.md`). Findings that change the design: the nested `auth` form does not work (flat form only); Bruno has no escape for `{{`, so such sample values become `TODO`; token isolation holds, including a missing token without a restart.
- 2026-11-02: the user added a `LOCAL` environment whose base URL follows the repo's VS Code launch settings, and said `DEV` and `PROD` may sit behind nginx or another proxy (recorded as notes; an nginx sample will come later). Environments, token variable names, naming standard and a new `LOCAL` base URL paragraph updated; plan gets Task 3b.
- 2026-11-03: the user asked for a way to reset a changed request to its original values and schema; chose option C (original kept in `docs/requests/`, reset by a chat action). An in-Bruno script (option B) is not in version 1.
- 2026-11-03: the user tested the skill on a real repo and changed it (reviewed and committed): object bodies are written in the Body tab with `random_<field>` variables; each request gets a `docs` section (Bruno Docs tab) from the code; action-style paths are named `<Action> <resource>`; discovery follows a router mounted in a function the app module calls (depth 4); the sync log no longer repeats a decision it already holds. Review fixes: a body field that shares a name with a query or path parameter gets `random_body_<field>`; `return_keys` ignores nested functions. Known consequence: two methods on one action-style path (`GET` and `POST /orders/export`) now map to one file name and are reported as a collision.
