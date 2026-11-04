# Bruno format: verified facts (plan Task 0)

Pinned version: **Bruno 4.3.0** (desktop app on Windows; reported by the user on 2026-11-02).

Status words: `docs` = read in Bruno's documentation only; `app` = confirmed by opening a test collection in the real app and reading what a local echo stub received; `pending` = not checked yet; `not possible` = checked and does not work (a design note goes back to the user before Task 6).

Test collection: `_verify` in the user's Windows `bruno` folder (not in this repo). The echo stub is local only and uses fake data only.

## Collection layout

| Fact | Status | Notes |
| --- | --- | --- |
| Root file `opencollection.yml`; environments in `environments/<NAME>.yml`; folders have `folder.yml`; request files are `.yml` | app | All loaded; the folder `group` with a `folder.yml` showed its request |
| Environment file: `name:` plus `variables:`; a secret variable has `secret: true` and no value; the user types the value in the app | app | `{{apiKey}}` and `{{clientSecret}}` resolved from values typed in the app |
| `docs` in `extensions.bruno.ignore` hides a Markdown folder | app | The `docs/` folder is not shown in the sidebar |

## Request file

| Fact | Status | Notes |
| --- | --- | --- |
| Top-level blocks `info` (name, type `http`, seq), `http`, `runtime`, `settings` | app | |
| `http.params` is one list of `name`, `value`, `type: query` or `type: path`; a path parameter is written `:item_id` in the URL | app | Request A sent `/api/items/42?limit=5&tag=x` |
| A parameter with `disabled: true` is not sent | app | `optional_unused` was absent |
| Headers: list of `name`, `value` | app | `apikey` sent from `{{apiKey}}` |
| JSON body: `body.type: json`, `body.data` as a text block; `Content-Type: application/json` is added by the app | app | Request B |
| Form body: `body.type: form-urlencoded`, `body.data` as a list of `name`, `value` | app | Request C, sent as `field_one=...&field_two=2` |
| Multipart form body shape | pending, out of scope for version 1 | |
| `auth` block, **flat form**: `auth: {type: bearer, token: "{{access_token}}"}` | app (inferred from send order G then H: the flat request sent the token) | Request G; confirm with the user if in doubt |
| `auth` block, **nested form**: `bearer: {token: ...}` | app: **does not work** (header sent as `Bearer` with an empty token) | Request H; use the flat form only |
| `auth: inherit` | app | Requests A to E and I |
| When the app saves a request it keeps the layout and adds `settings` defaults (`timeout: 0`, `followRedirects: true`, `maxRedirects: 5`, `forwardAuthorizationHeader: true`) | app | Request B after a user edit; the generator should write these defaults |

## Scripts and variables

| Fact | Status | Notes |
| --- | --- | --- |
| Request-level scripts live under `runtime.scripts`; the post-response type is `after-response` | app | Request E captured the token |
| Collection-level scripts live under `request.scripts` in `opencollection.yml` | app | The collection `before-request` script ran for request F, which has no script of its own |
| `bru.setVar`, `bru.getVar`, `bru.getEnvName()` work in `before-request` and `after-response` | app | |
| A runtime variable set by request E is visible to request F | app | |
| A variable set in a before-request script is used by `{{...}}` in the **same** request's headers | app | Request D: `X-Random-Name` equals the body name |
| `req.setBody(object)` in a before-request script sets a JSON body | app | Request D sent compact JSON with nested objects and a list |
| Token isolation with both tokens present: DEV token in DEV, PROD token in PROD, DEV token again after switching back | app | Sequence E, F in DEV; E, F in PROD; F in DEV |
| After an app restart, `access_token_prod` missing: request F carries the literal text `Bearer {{access_token}}` (a visible failure, no token from another environment) | app | The restart cleared all runtime variables |
| Missing token in the new environment **without a restart**: DEV E then F (token `tok-dev-4`), switch to PROD, F without E | app | F carried the literal `Bearer {{access_token}}`. The collection script's `bru.setVar("access_token", undefined)` does not keep the stale DEV token. Token isolation holds |
| Collection script before request script order | not needed | No script in the design depends on it |
| `{{` inside a sample string value can be escaped | **not possible** (no escape in Bruno's docs; interpolation is recursive, so a variable value containing `{{x}}` is resolved too) | Policy: a code-derived sample value containing `{{` is never written; it becomes a `TODO` and is listed in the report |
| The Bruno CLI (`bru run --env`) cannot switch environments inside one run | pending; the CLI is not installed here | The live check covers it |

## Reported by the user's test on a real repo (2026-11-03, not re-checked here)

| Fact | Status | Notes |
| --- | --- | --- |
| A request-level `docs:` block (Markdown, `docs: \|-`) shows in the Docs tab | app, confirmed by the user (2026-11-03) | The generator writes it after `settings` |
| An unquoted `{{random_x}}` inside the JSON body text is replaced by the variable's value, so a number or list keeps its JSON type | app, reported by the user; the user's reply "confirm for unquoted variable" was read as a confirmation | The variable holds JSON text (`JSON.stringify`) |
| In the desktop app a request script does not see a plain function declared in the collection-level script (the CLI did) | app, reported by the user | See the probe below |
| Probe `_verify_helpers`, Bruno 4.3.0, 2026-11-03: a plain function: not visible; `globalThis.__lib` set in the collection script: **visible**; a variable holding a function's source: ok, and `eval` and `new Function` on it: ok; `require("./lib/helpers.js")` of a collection file: ok | app, run by the user | The generator shares the helpers through `globalThis.__lib` (no `eval`, no `require`, no dependency on the app's mode). Not checked in the Bruno CLI |

## Still open

- The Bruno CLI cannot switch environments inside one run: not checkable here (the CLI is not installed). The live check in plan Task 11 covers it.
- Request G (flat `auth`) versus H (nested `auth`) was inferred from the order the user sent them. A one-line confirmation closes it.
