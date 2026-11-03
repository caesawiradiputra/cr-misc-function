# Bruno Collection Generator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A `bruno-collection` skill that reads a FastAPI repo's source and writes one Bruno collection (fixed and random request per endpoint, `LOCAL`, `DEV` and `PROD` environments, optional token workflow), keeps it add-only on re-runs, documents it as an OKF bundle, and scans collections for plain-text secrets without ever printing a secret.

**Architecture:** One stdlib CLI (`bruno_collection.py`: `discover`, `generate`, `sync`, `scan`) over small modules in `scripts/`: AST discovery, a value/constraint contract, identity and add-only planning, rendering, the OKF docs writer, and the scanner. Discovery returns plain dataclasses; nothing imports or runs the target repo. Claude edits collections in chat by the skill's rules (`SKILL.md`); the CLI does the mechanical parts.

**Tech Stack:** Python 3.9 and 3.10+ (stdlib only), Node (tests only, for the mock `bru` harness), pytest, ruff, mypy, Pydantic v1/v2 (tests only, to validate random payloads).

**Spec:** `docs/superpowers/specs/2026-11-02-bruno-collection-design.md` (read it first; this plan records only decisions the spec leaves open). Branch `feat/bruno-collection` from `dev`, created only when the user says so.

## Global Constraints

- Helper under `~/.claude` runs on the WSL system `python3` (3.9) and 3.10+: `from __future__ import annotations`; no `match`, no `zip(strict=)`, no runtime `X | None`. Verify with `uv run --offline --no-project --python 3.9 --with pytest pytest tests/test_bruno_*.py` and on 3.12.
- The skill never imports or runs the target repo, never reads `.env*`, `token.json` or `settings.local.json`. The target's source is parsed with the running interpreter; syntax it cannot parse is reported as skipped.
- Environments `LOCAL`, `DEV` and `PROD` with identical variable names. `baseUrl`: `LOCAL` from the VS Code launch settings (Task 3b), placeholders `https://<dev-host>` and `https://<prod-host>` for the others, with a `description` that mentions any proxy path prefix; proxy or load balancer details are notes only until the user supplies an nginx sample; every secret variable has `secret: true` and no value. The route prefix stays in the URL: `{{baseUrl}}/prefix/path`.
- Names: config variables `camelCase`; runtime variables `snake_case`, `random_<field>` for fake data; captured token `access_token_<env lowercase>` copied to `access_token`; request and file name `<Verb> <resource> (fixed|random)`; header `apikey: {{apiKey}}`, bearer `Authorization: Bearer {{access_token}}`.
- Token scripts, verbatim: post-response `bru.setVar("access_token_" + bru.getEnvName().toLowerCase(), res.body.access_token);`; collection-level before-request `bru.setVar("access_token", bru.getVar("access_token_" + bru.getEnvName().toLowerCase()));`. Never `bru.setEnvVar` or `bru.setCollectionVar`.
- Scan report: one line per finding, `file:line  kind  length`; no character of a value, no file line, paths relative or `<path-redacted:N>`; non-zero exit on a finding or on **scan incomplete**; no debug mode.
- Random values: marker prefix `TEST_` on strings, `999` style prefixes on identifiers; unsupported constraints give a visible `TODO` and an **incomplete** line in the report, never a guessed value.
- Output root default `/mnt/c/Users/<WINDOWS_USERNAME>/Documents/bruno/<repo-name>/`; the repo is public, so no company hosts, names or real values in the skill, tests or examples (a guard test greps for them).
- Add-only: an existing file is never overwritten, a collision writes neither side, nothing is deleted or renamed.
- Commit nothing: the user commits only when asked, so each task ends with a `git status` checkpoint. Never `git add -A`. Markdown follows the global style.

## Review Focus

Inputs the spec implies but its sections do not test; each is pinned by a test in the task that owns the code.

1. A sample value from a docstring that breaks YAML or injects Bruno syntax (`: `, `"`, newline, `#`, `{{secret}}`): quoted safely; Bruno has no escape for `{{` (Task 0), so a value containing `{{` is never written: it becomes a `TODO` and is listed in the report. Task 6.
2. A target repo with a syntax error, newer-than-interpreter syntax, or a symlink that leaves the repo: skipped and listed, never a crash or a read outside the repo. Task 1.
3. An existing output folder: a `generate` into a non-empty folder with no `docs/`, or a `sync` whose `docs/` is missing or hand-corrupted, refuses with a report and writes nothing. Task 8.
4. Starlette path converters (`{file_path:path}`), trailing slashes, a repo name with spaces or `..`, and names that are invalid or ambiguous on the Windows disk the output goes to (`:*?"<>|`, names differing only in case): identity, URL (`:file_path`), folder and file names stay safe. Tasks 5 and 6.
5. A scan target with a CRLF or BOM file, a huge file, and a symlink out of the folder: still no value in the report; the huge file and the symlink are **scan incomplete**, not followed. Task 9.

## Verified in Task 0 (2026-11-02, Bruno 4.3.0) and still open

Recorded in `references/bruno-format.md`; the generator follows that file, not the reference collection. Task 0 confirmed in the real app: bodies, path and query parameters, disabled parameters, the flat `auth` block (the nested form does **not** work), request-level scripts under `runtime.scripts` with type `after-response`, collection-level scripts under `request.scripts`, `req.setBody`, token isolation (including a missing token without a restart), and the hidden `docs` folder. Bruno has **no escape for `{{`**.

Still open: that the Bruno CLI cannot switch environments inside one run (not installable here; Task 11 covers it) and a one-line confirmation of the flat versus nested `auth` order.

## File Structure

| Path | Responsibility |
| --- | --- |
| `CLAUDE/skills/bruno-collection/SKILL.md` | Rules for Claude: workflows, naming, secrets, scan-only rule |
| `CLAUDE/skills/bruno-collection/references/bruno-format.md` | Verified Bruno schema and semantics, pinned version (Task 0) |
| `scripts/bruno_collection.py` | CLI: `discover`, `generate`, `sync`, `scan` |
| `scripts/bruno_discover.py` | AST discovery: routes, params, models, auth, token endpoint |
| `scripts/bruno_values.py` | Fixed-value sources and the random constraint contract (JS emitter) |
| `scripts/bruno_launch.py` | `LOCAL` base URL from `.vscode/launch.json` |
| `scripts/bruno_identity.py` | Identity, file names, collisions, add-only plan |
| `scripts/bruno_render.py` | Collection files as text (YAML-safe) and the writer |
| `scripts/bruno_docs.py` | OKF `docs/` writer and reader |
| `scripts/bruno_scan.py` | The secret scanner |
| `tests/test_bruno_*.py`, `tests/support/bruno_loader.py`, `tests/support/bruno_fixtures.py`, `tests/support/bru_mock.js` | Tests; the loader puts `scripts/` on `sys.path`; the fixtures module holds the fixture FastAPI app and the hostile scan files as **text** |

All `scripts/` paths are under `CLAUDE/skills/bruno-collection/`. Modules carry a `bruno_` prefix so none can shadow or duplicate another package (`scan`, `render`, `values` would). Siblings import each other by name (`from bruno_discover import Endpoint`); `bruno_collection.py` does `sys.path.insert(0, str(Path(__file__).resolve().parent))` first, and tests import through `tests/support/bruno_loader.py`, which does the same.

**Fixtures are text, never committed as live files.** `ruff`, `mypy` and the format hook run on the whole repo, `fastapi` is not a dependency here, and GitHub push protection can reject secret-shaped strings. So `tests/support/bruno_fixtures.py` holds the fixture app, the syntax-error module and the hostile scan files as string constants and writes them into `tmp_path` at test time. Symlinks are created in `tmp_path` too. Fake secrets are built by concatenation (`"AKIA" + "ABCD1234" * 2`), as `tests/test_prompt_coach.py` does.

Out of scope for version 1: reading an existing `openapi.json` instead of the code.

---

### Task 0: Verify Bruno (gate, no generator code before it is done)

**Files:** Create `CLAUDE/skills/bruno-collection/references/bruno-format.md`; the user supplies a tiny hand-made collection in a scratch folder.

**Produces:** a table of verified facts with the pinned Bruno version, each marked `verified (app)`, `verified (docs)` or `not possible`. Later tasks cite it.

- [x] **Step 1:** Ask the user for the installed Bruno version (Help, About) and record it as the pinned version.
- [x] **Step 2:** With the user, build a scratch collection in the app with: a `GET` with a path parameter and two query parameters; a `POST` with a JSON body and one with a form body; a header using `{{var}}`; an `auth` block; a collection-level before-request script; a request-level post-response script; `docs` in the `ignore` list with a Markdown folder; `secret: true` environment variables. Copy the saved YAML into the reference file (values replaced by placeholders).
- [x] **Step 3:** Verify and record each: script representation and run order (collection before request); `bru.setVar`, `bru.getVar`, `bru.getEnvName()` in before-request and post-response; a runtime variable set in request A is visible in request B; the token request body format; whether `docs` is hidden; whether the Bruno CLI (`bru run --env`) replays an environment switch inside one run (expected: no); whether a before-request script can set the whole request body (`req.setBody(...)` or the equivalent) and how a JSON body references runtime variables.
- [x] **Step 4:** Gate: every row has a status. Any `not possible` row becomes a design note back to the user before Task 6 starts.

### Task 1: Discovery of routes and prefixes

**Files:** Create `scripts/bruno_discover.py`, `tests/support/bruno_loader.py`, `tests/support/bruno_fixtures.py` (writes into `tmp_path`: a generic app with nested `include_router` prefixes, a dynamic route, a syntax-error module and a symlink that leaves the repo), `tests/test_bruno_discovery.py`.

**Produces:**

```python
@dataclass(frozen=True)
class Source: file: str; line: int
@dataclass
class Endpoint: method: str; path: str; tags: list[str]; function: str; docstring: str | None; params: list[Param]; body: ModelSpec | None; source: Source
@dataclass
class Skipped: source: Source; reason: str
@dataclass
class DiscoveryResult: app_found: bool; endpoints: list[Endpoint]; skipped: list[Skipped]; auth: AuthFinding | None; token: TokenEndpoint | None
def discover(root: Path) -> DiscoveryResult
```

- [ ] **Step 1: tests.** `test_prefix_chain_combined` (app prefix + router prefix + path gives `/api/v1/orders/{order_id}`); `test_methods_and_tags`; `test_add_api_route_found`; `test_dynamic_route_listed_as_skipped_with_file_and_line`; `test_syntax_error_module_skipped_not_crash`; `test_symlink_leaving_repo_not_followed`; `test_three_outcomes`: resolved endpoints, a `not statically resolvable` skip, and an empty repo returns `app_found=False` with the message "no route discovered" (never "no routes exist").
- [ ] **Step 2:** Run, expect FAIL (module missing).
- [ ] **Step 3:** Implement with `ast` only. Walk `*.py` under `root`, skipping `.venv`, `venv`, `node_modules`, `.git`, `legacy` and any symlink that resolves outside `root`. Resolve `include_router` chains across modules by imported name. Never read `.env*`.
- [ ] **Step 4:** Run tests on 3.9 and 3.12, expect PASS. `git status` checkpoint.

### Task 2: Discovery of parameters, models and constraints

**Files:** Modify `scripts/bruno_discover.py`, `tests/support/bruno_fixtures.py`; Test `tests/test_bruno_discovery_params.py`.

**Produces:** `Param(name, location, type_name, required, default, constraints: dict[str, object], example)` with `location` in `path|query|header|body`; `ModelSpec(name, fields: list[FieldSpec], source)` where `FieldSpec` has the same attributes plus `children: ModelSpec | None`, `is_list`, `enum_values`.

- [ ] **Step 1: tests.** `test_query_required_and_optional`; `test_constraints_read` (`min_length`, `max_length`, `ge`, `gt`, `le`, `lt`, `multiple_of`, `pattern`/`regex`, `min_items`, `max_items`); `test_pydantic_v1_and_v2_models_parse` (the fixture has both styles, v1 with `= None` defaults); `test_nested_model_and_list`; `test_enum_and_literal`; `test_path_converter` (`{file_path:path}` keeps the name `file_path`); `test_recursive_model_stops_at_depth_3_and_is_reported`.
- [ ] **Step 2:** Run, expect FAIL. **Step 3:** Implement. **Step 4:** Run, expect PASS; `git status` checkpoint.

### Task 3: Discovery of auth and the token endpoint

**Files:** Modify `scripts/bruno_discover.py`; Test `tests/test_bruno_discovery_auth.py`.

**Produces:** `AuthFinding(kind: Literal["api_key_header","api_key_query","bearer","basic","oauth2_password","none_recognized"], header_name: str | None, source: Source | None)`; `TokenEndpoint(path: str, grant_inputs: list[str], token_field: str, source: Source)`.

- [ ] **Step 1: tests.** One per order in the spec: `test_security_helpers_detected` (`APIKeyHeader`, `HTTPBearer`, `HTTPBasic`, `OAuth2PasswordBearer(tokenUrl=...)`); `test_middleware_header_detected` (the fixture middleware compares `request.headers.get("apikey")` to a configured value); `test_nothing_recognized_is_not_proof` (kind `none_recognized`, report text "no auth pattern recognized, check middleware"); `test_token_endpoint_inputs_and_field` (`username`/`password` or `clientId`/`clientSecret`; `access_token` default when the response model does not say).
- [ ] **Step 2:** FAIL. **Step 3:** Implement. **Step 4:** PASS; `git status` checkpoint.

### Task 3b: `LOCAL` base URL from the VS Code launch settings

**Files:** Create `scripts/bruno_launch.py`; Test `tests/test_bruno_launch.py` (launch files are text written into `tmp_path`).

**Produces:** `local_base_url(root: Path) -> LaunchResult` with `url: str`, `source: Source | None`, `notes: list[str]`.

- [ ] **Step 1: tests.** `test_uvicorn_host_and_port_args` (`--host 0.0.0.0 --port 8000` gives `http://localhost:8000`); `test_hypercorn_bind` (`--bind 0.0.0.0:5000`); `test_python_module_with_port_in_env` (`PORT` in the configuration's `env`); `test_jsonc_comments_and_trailing_commas_parse`; `test_https_only_with_ssl_option`; `test_no_launch_file_gives_placeholder_and_note` (`http://localhost:<port>`); `test_first_matching_configuration_used_and_others_listed`; `test_env_file_never_read_and_other_env_values_never_copied` (a planted fake secret in `env` and an `envFile` path never appear in the result or notes); `test_broken_json_gives_placeholder_and_note_not_a_crash`.
- [ ] **Step 2:** Run, expect FAIL. **Step 3:** Implement with `json` after stripping comments and trailing commas without touching strings. **Step 4:** Run on 3.9 and 3.12, expect PASS; `git status` checkpoint.

### Task 4: Fixed and random values

**Files:** Create `scripts/bruno_values.py`, `tests/support/bru_mock.js`, `tests/test_bruno_values.py`.

**Rule (pinned):** query, path and header values use one runtime variable each, `{{random_<field>}}`; an object **body is written in the Body tab with one variable per top-level field** (a number, bool, list or object is unquoted, its variable holding JSON text), a list body is built with `req.setBody`; a body variable that would share a name with a query, path or header variable gets `random_body_<field>` (superseded 2026-11-03, see the spec's revision history). Variables for nested fields are named from the full field path (`random_address_city`), so two models with the same field name never collide.

**Produces:**

```python
def fixed_value(param: Param | FieldSpec, endpoint: Endpoint) -> FixedResult   # value, origin, todo: bool
def random_js(spec: Param | ModelSpec, name_prefix: str = "random_") -> RandomResult  # script: str, vars: list[str], incomplete: list[Incomplete]
```

- [ ] **Step 1: fixed tests.** `test_fixed_order`: docstring "Example input parameter" block, then `example=`/`examples=`/`schema_extra`/`json_schema_extra`, then the code default, then a visible `TODO` listed in the report.
- [ ] **Step 2: random tests (the constraint contract table in the spec).** `test_supported_constraints_hold` runs the emitted JS 500 times per case **inside one Node process** (the harness takes an iteration count) and validates each payload with the fixture's own Pydantic models (v1 via `pydantic.v1`, and v2), with boundary cases for `min_length`/`max_length` (marker prefix shortened to fit, never over), `ge/gt/le/lt/multiple_of`, date bounds, enums, `min_items`/`max_items`, nested required fields; `test_regex_subset_supported_and_rest_unsupported`; `test_unsupported_or_contradictory_gives_todo_and_incomplete` (`min_length` above `max_length`; the field is `TODO`, `incomplete` names field and reason, no value emitted); `test_marker_prefix_and_no_real_looking_pii`; `test_depth_limit`; `test_body_built_as_one_object_with_lists_and_nested_models`; `test_same_field_name_in_two_models_no_variable_collision`. Tests skip with a clear message when `node` is missing, and the Pydantic validation tests use `pytest.importorskip("pydantic")` (and skip the `pydantic.v1` cases where it is unavailable, for example on Python 3.14). They run in the project env; the offline Python 3.9 run (no Pydantic) covers the rest.
- [ ] **Step 3:** `bru_mock.js` implements `bru.getEnvName/setVar/getVar/getAllVars` and a minimal `req`, following the documented semantics; keep it under 40 lines.
- [ ] **Step 4:** FAIL, implement, PASS on 3.9 and 3.12; `git status` checkpoint.

### Task 5: Identity, file names, collisions and the add-only plan

**Files:** Create `scripts/bruno_identity.py`; Test `tests/test_bruno_identity.py`.

**Produces:**

```python
def identity(ep: Endpoint) -> str            # "GET /prefix/orders/{order_id}" (converter suffix dropped, trailing slash normalized)
def request_names(ep: Endpoint) -> tuple[str, str]   # "Get orders by id (fixed)", "... (random)"
def plan(eps: list[Endpoint], existing: ExistingState) -> Plan   # add: list, collisions: list, conflicts: list, changed: list, disappeared: list, possible_renames: list
```

`ExistingState` is built from the files on disk and the `resource` field of each `docs/requests/` concept (file renames do not create duplicates).

- [ ] **Step 1: tests (spec list).** `test_two_identities_one_file_name_write_neither`; `test_changed_path_is_new_plus_disappeared`; `test_changed_method_same`; `test_possible_rename_is_hint_only`; `test_new_endpoint_whose_file_exists_is_collision_not_overwrite`; `test_same_identity_twice_is_conflict`; `test_duplicate_function_names_do_not_matter`; `test_renamed_request_file_matches_by_resource`; `test_path_converter_and_trailing_slash_same_identity`; `test_names_differing_only_in_case_are_a_collision` (file names are compared case-folded, because the output root is NTFS).
- [ ] **Step 2:** FAIL, implement, PASS; `git status` checkpoint.

### Task 6: Render and write the collection (`generate`)

**Files:** Create `scripts/bruno_render.py`, `scripts/bruno_collection.py` (CLI `discover` and `generate`); Test `tests/test_bruno_render.py`.

**Consumes:** the verified shapes in `references/bruno-format.md` (Task 0). **Produces:** `render_collection(result: DiscoveryResult, name: str) -> dict[str, str]` (relative path to text) and `write_collection(files, out_dir, plan) -> WriteReport`.

- [ ] **Step 1: tests.** `test_layout_matches_spec` (tree in "Output layout", `docs` in the `ignore` list, `.gitignore` ignores `.env*`, `node_modules`, OS files); `test_environments_identical_variable_names_secrets_empty` (for `LOCAL`, `DEV` and `PROD`); `test_local_base_url_comes_from_launch_settings_and_dev_prod_are_placeholders`; `test_base_url_description_mentions_proxy_prefix`; `test_request_urls_use_baseUrl_and_prefix`; `test_fixed_has_no_script_random_has_before_request_script`; `test_auth_header_value_is_a_variable`; `test_yaml_unsafe_sample_values_quoted` (values with `: `, `"`, newline, `#`, leading `-`, and `{{secret}}` come out as one safe scalar, except that a value containing `{{` is replaced by a `TODO` and reported, never written); `test_name_safety` (repo name with spaces, `..`, `/`, and any of `:*?"<>|` becomes a safe folder or file name, never leaves the output root); `test_optional_param_without_example_disabled_in_fixed_filled_in_random` (design call 7); `test_generate_refuses_nonempty_folder_without_docs`; `test_write_never_overwrites`; `test_report_lists_found_written_skipped_todos_auth_placeholders`.
- [ ] **Step 2:** FAIL, implement (string templates, no YAML library), PASS; `git status` checkpoint.

### Task 7: Token workflow and isolation tests

**Files:** Modify `scripts/bruno_render.py`; Test `tests/test_bruno_token.py`.

- [ ] **Step 1: tests.** `test_token_files_only_with_token_endpoint`; `test_token_request_has_no_random_pair_and_inputs_are_secret_env_vars`; `test_scripts_verbatim` (exactly the two lines in Global Constraints); `test_isolation_sequence_in_node` runs the generated scripts against `tests/support/bru_mock.js`: DEV token then DEV request uses it; PROD token then PROD request; back to DEV uses the DEV token; then the same with `LOCAL` as a third environment (`access_token_local`); an environment with no token ends with an empty token and the request does not carry the other environment's token; the mock records no file write and the rendered files contain no token value.
- [ ] **Step 2:** FAIL, implement, PASS. The mock test proves script logic only; the real-app proof is Task 11. `git status` checkpoint.

### Task 8: OKF docs bundle and `sync`

**Files:** Create `scripts/bruno_docs.py`; Modify `scripts/bruno_collection.py` (`sync`); Test `tests/test_bruno_docs.py`.

**Produces:** `write_docs(result, plan, out_dir, model: str, reason: str)`, `read_docs(out_dir) -> ExistingState`. Mechanical concepts (identity as `resource`, request names, parameters, value origins, auth, source `file:line`, variable names without values) are written by the helper; descriptions and the log reason are written by Claude and passed in.

- [ ] **Step 1: tests.** `test_bundle_passes_okf_lint` runs `CLAUDE/skills/okf-writer/scripts/okf_lint.py`; `test_frontmatter_generated_by_and_draft_no_verified`; `test_log_newest_first_with_reason_and_source`; `test_environments_doc_has_no_values`; `test_environments_doc_has_proxy_note_for_dev_and_prod`; `test_sync_adds_only_new_endpoints_and_logs_needs_a_decision`; `test_sync_with_missing_docs_refuses_and_writes_nothing`; `test_sync_with_corrupt_concept_refuses`; `test_sync_never_modifies_existing_files` (hash before and after); `test_pinned_bruno_version_recorded`; `test_request_concept_stores_original_sample_and_schema` (an `original` JSON block with the fixed sample for every parameter and the body, and the schema); `test_token_doc_only_with_token_endpoint_and_has_no_token_values`; `test_generate_and_sync_report_end_with_lint_and_scan_summary`.
- [ ] **Step 2:** FAIL, implement, PASS; `git status` checkpoint.

### Task 9: The secret scanner

**Files:** Create `scripts/bruno_scan.py`; Modify `scripts/bruno_collection.py` (`scan`); Test `tests/test_bruno_scan.py` (hostile files come from `tests/support/bruno_fixtures.py`, fake secrets with unmistakable markers, built by concatenation).

**Produces:** `scan(folder: Path) -> ScanReport` (`findings`, `incomplete`, `lines: list[str]`, `exit_code: int`) and the CLI command `scan <folder>`.

- [ ] **Step 1: tests (spec section "Secret scan").** `test_finds_header_variable_name_jwt_private_key_url_credential_opaque_and_missing_gitignore_rule`; `test_report_line_format` (`file:line  kind  length`, nothing else); `test_no_value_fragment_in_report_stderr_or_exception` for secrets planted in file contents, file names, folder names, malformed and binary files, deep paths (no value, no run of three or more of its characters, no fixture line); `test_path_redaction` (`<path-redacted:N>`, stable N); `test_unreadable_malformed_huge_binary_and_out_of_folder_symlink_are_incomplete_and_nonzero` (huge means over 2 MiB); `test_crlf_and_bom_files_scanned`; `test_top_level_error_prints_only_class_and_step`; `test_no_verbose_or_debug_flag`; `test_clean_report_says_not_proof`; `test_generated_collection_scans_clean` (a collection generated by Task 6 and 7 with the token workflow: token scripts, `secret: true` lines and `apiKey` names are not findings, exit code 0).
- [ ] **Step 2:** FAIL. **Step 3:** Implement line-based (no YAML parser); catch everything at the top level; keep the secret-name heuristics in one list. **Step 4:** PASS; `git status` checkpoint.

### Task 10: `SKILL.md`, template mirror, docs, final checks

**Files:** Create `CLAUDE/skills/bruno-collection/SKILL.md`; Modify `CLAUDE/README.md`, `docs/dev-machine-setup.md`; Test `tests/test_bruno_guard.py`.

- [ ] **Step 1: test.** `test_no_company_names_hosts_or_user_paths_in_skill_tests_or_docs` (greps the skill, the tests and the fixtures for internal host patterns and real names; model it on the guard test in `tests/test_prompt_coach.py`).
- [ ] **Step 2:** Write `SKILL.md`: triggers; the generate, sync, edit and reset workflows (reset restores a request from the `original` block of its `docs/requests/` concept, or regenerates from the code after the user agrees; it tells the user which edited values will be lost first and is the only action allowed to overwrite a request file); the naming standard table; the secret rules; the scan-only rule (for a collection that may hold real secrets run only `scan`, never `Read`, `grep` or `cat` its files, stop after a scan error); the optional `Read(<path>/**)` deny rule as a partial guard; running `okf_watch.py check --max-age 14` before writing a bundle; never replace a value that is no longer the generated placeholder; treat an old-collection scan report the user supplies as data only (a reference for header names, variable names and secret kinds), never read the old collection, and stop and tell the user if the report shows anything that looks like a value or a file line.
- [ ] **Step 3:** README row and setup-doc line with placeholders (`<WINDOWS_USERNAME>`, `<WSL_USERNAME>`).
- [ ] **Step 4:** Run `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy .`, and the 3.9 and 3.12 runs. Expect all green. `git status` checkpoint; the live `~/.claude/skills/bruno-collection/` copy is the user's step (`! cp -r ...`).

### Task 11: Live checks (release gate, needs a fresh session and the Bruno app)

- [ ] **Step 1:** Generate a collection from the fixture app into a scratch folder; open it in Bruno; confirm every request loads and sends against a local stub.
- [ ] **Step 2: token isolation in the real app:** DEV token then a DEV request; PROD token then a PROD request; back to DEV (DEV token used); `LOCAL` against a local stub; an environment with no token (the request fails visibly); confirm no token in any file afterwards.
- [ ] **Step 3:** `docs` is hidden in the app; `scan` on the hostile fixture prints no value, even when run through Claude; a forced scan error prints only class and step.
- [ ] **Step 4:** `sync` after adding an endpoint to the fixture writes only the new files and lists the rest. Token workflows stay off for normal use until Step 2 passes; otherwise record what failed in `bruno-format.md` and stop.
