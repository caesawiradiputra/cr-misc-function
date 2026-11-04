"""Render a discovered API as Bruno collection files (text) and write them add-only.

Files are plain strings built from templates, no YAML library. Every scalar is
written as a JSON-style double-quoted string, which is valid YAML, so a sample value
with `: `, a quote, a newline or `#` stays one scalar. Bruno has no escape for `{{`,
so a sample value that contains it is never written (see `bruno_values`).
Python 3.9 and newer, stdlib only.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import quote

from bruno_discover import DiscoveryResult, Endpoint, TokenEndpoint
from bruno_identity import (
    ExistingState,
    Plan,
    Planned,
    identity,
    normalize_path,
    plan,
    safe_name,
    windows_safe,
)
from bruno_launch import LaunchResult
from bruno_params import ModelSpec, Param
from bruno_values import (
    HELPERS_SCRIPT,
    fixed_body,
    fixed_value,
    random_js,
    random_request,
)

MODES = ("fixed", "random")
ENVIRONMENTS = ("LOCAL", "DEV", "PROD")
DEV_URL = "https://<dev-host>"
PROD_URL = "https://<prod-host>"
PROXY_NOTE = (
    "proxy or load balancer in front of DEV and PROD: unknown, "
    "fill from the nginx configuration (path prefix, stripped prefix, TLS, key check); "
    "requests may also go through the corporate Apigee gateway (base path and credential not known yet)"
)
PLACEHOLDER_PATH = re.compile(r"\{([^}:]+)(?::[^}]*)?\}")
GITIGNORE = ".env*\nnode_modules/\n.DS_Store\nThumbs.db\ndesktop.ini\n"
SETTINGS = (
    "settings:\n  encodeUrl: true\n  timeout: 0\n  followRedirects: true\n"
    "  maxRedirects: 5\n  forwardAuthorizationHeader: true\n"
)

# auth kind -> (secret variable, header name, header value)
HEADER_AUTH = {
    "bearer": ("bearerToken", "Authorization", "Bearer {{bearerToken}}"),
    "basic": ("basicCredentials", "Authorization", "Basic {{basicCredentials}}"),
}


# ------------------------------------------------------------------ YAML text


def q(text: object) -> str:
    return json.dumps(str(text), ensure_ascii=True)


YAML_WORDS = {"true", "false", "yes", "no", "on", "off", "null", "y", "n"}


def qn(name: str) -> str:
    """A parameter or header name: bare when plainly safe, else quoted."""
    if (
        re.fullmatch(r"[A-Za-z_][A-Za-z0-9_-]*", name)
        and name.lower() not in YAML_WORDS
    ):
        return name
    return q(name)


def block(text: str, indent: int) -> str:
    pad = " " * indent
    body = "\n".join(
        pad + line if line else "" for line in text.rstrip("\n").split("\n")
    )
    return "|-\n" + body


def collection_dir_name(name: str) -> str:
    return windows_safe(safe_name(name))


def var_name(field_name: str) -> str:
    return "random_" + re.sub(r"\W", "_", field_name)


def _text(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (list, tuple)):
        return ",".join(_text(v) for v in value)
    return str(value)


# --------------------------------------------------------------------- auth


@dataclass
class AuthPlan:
    """How requests carry the credential; the value is always a variable."""

    secret: str | None = None  # environment variable that holds it
    header: tuple[str, str] | None = None  # name, value
    query: tuple[str, str] | None = None

    @staticmethod
    def from_discovery(result: DiscoveryResult) -> AuthPlan:
        auth = result.auth
        if auth is None or auth.kind == "none_recognized":
            return AuthPlan()
        if auth.kind == "oauth2_password" and result.token is not None:
            return AuthPlan(None, ("Authorization", "Bearer {{access_token}}"))
        if auth.kind == "api_key_header":
            return AuthPlan("apiKey", (auth.header_name or "apikey", "{{apiKey}}"))
        if auth.kind == "api_key_query":
            return AuthPlan(
                "apiKey", None, (auth.header_name or "api_key", "{{apiKey}}")
            )
        if auth.kind in HEADER_AUTH:
            secret, name, value = HEADER_AUTH[auth.kind]
            return AuthPlan(secret, (name, value))
        # oauth2_password without a usable token endpoint: a pasted bearer token
        secret, name, value = HEADER_AUTH["bearer"]
        return AuthPlan(secret, (name, value))


# ------------------------------------------------------------------ requests


@dataclass
class _Entry:
    name: str
    value: str
    kind: str  # query | path | header | form
    enabled: bool = True


def _path_url(path: str) -> str:
    return PLACEHOLDER_PATH.sub(lambda m: ":" + m.group(1), normalize_path(path))


def _path_names(path: str) -> list[str]:
    return PLACEHOLDER_PATH.findall(normalize_path(path))


@dataclass
class _Built:
    text: str
    todos: list[str] = field(default_factory=list)
    incomplete: list[str] = field(default_factory=list)


def _entries_fixed(ep: Endpoint, ident: str, todos: list[str]) -> list[_Entry]:
    out: list[_Entry] = []
    known = {(p.location, p.name): p for p in ep.params}
    path_params = [
        known.get(("path", n)) or Param(n, "path", "str") for n in _path_names(ep.path)
    ]
    others = [p for p in ep.params if p.location in ("query", "header", "form")]
    for p in [*path_params, *others]:
        res = fixed_value(p, ep)
        if res.todo:
            todos.append(f"{ident}: {p.name} ({res.reason})")
        out.append(_Entry(p.name, _text(res.value), p.location, res.enabled))
    return out


def _entries_random(ep: Endpoint) -> list[_Entry]:
    known = {(p.location, p.name): p for p in ep.params}
    path_params = [
        known.get(("path", n)) or Param(n, "path", "str") for n in _path_names(ep.path)
    ]
    others = [p for p in ep.params if p.location in ("query", "header", "form")]
    return [
        _Entry(p.name, "{{" + var_name(p.name) + "}}", p.location)
        for p in [*path_params, *others]
    ]


def _url(ep: Endpoint, entries: list[_Entry], auth: AuthPlan) -> str:
    query = [e for e in entries if e.kind == "query" and e.enabled]
    pairs = [f"{quote(e.name, safe='')}={quote(e.value, safe='{}')}" for e in query]
    if auth.query:
        pairs.append(f"{quote(auth.query[0], safe='')}={auth.query[1]}")
    suffix = "?" + "&".join(pairs) if pairs else ""
    return "{{baseUrl}}" + _path_url(ep.path) + suffix


RANDOM_MARK = "<random: set by the before-request script>"


def _shape(spec: ModelSpec) -> dict[str, object]:
    """Every field the random script sends (same model walk), values as markers."""
    out: dict[str, object] = {}
    for f in spec.fields:
        value: object = _shape(f.children) if f.children else RANDOM_MARK
        is_list = f.is_list or f.type_name.startswith("list[")
        out[f.name] = [value] if is_list else value
    return out


def _random_script(ep: Endpoint, central: bool) -> tuple[str, list[str]]:
    scripts: list[str] = []
    notes: list[str] = []
    main = random_request(ep, central=central)
    has_body = ep.body is not None or any(p.location == "body" for p in ep.params)
    if main.vars or has_body:
        scripts.append(main.script)
    notes += [f"{i.field}: {i.reason}" for i in main.incomplete]
    for p in ep.params:
        if p.location == "form":
            res = random_js(p, central=central)
            scripts.append(res.script)
            notes += [f"{i.field}: {i.reason}" for i in res.incomplete]
    # path parameters the code did not declare as parameters get a plain id
    declared = {p.name for p in ep.params if p.location == "path"}
    for n in _path_names(ep.path):
        if n not in declared:
            scripts.append(random_js(Param(n, "path", "str"), central=central).script)
    return "".join(scripts), notes


def _cell(text: object) -> str:
    return str(text).replace("|", "\\|").replace("\n", " ")


def _type_label(type_name: str, is_list: bool) -> str:
    label = type_name or "str"
    return f"list[{label}]" if is_list and not label.startswith("list[") else label


def _docs(ep: Endpoint, mode: str) -> str:
    """Markdown for the request's Docs tab; facts from the code only, no sample values."""
    lines: list[str] = []
    if ep.docstring:
        first = ep.docstring.strip().split("\n\n")[0].strip()
        if first and "Example input parameter" not in first:
            lines += [" ".join(first.split()), ""]
    lines.append(f"Handler `{ep.function}` (`{ep.source.file}:{ep.source.line}`).")
    others = [p for p in ep.params if p.location != "body"]
    if others:
        lines += [
            "",
            "### Parameters",
            "",
            "| Name | In | Type | Required |",
            "| --- | --- | --- | --- |",
        ]
        lines += [
            f"| `{_cell(p.name)}` | {p.location} | `{_cell(p.type_name or 'str')}` "
            f"| {'required' if p.required else 'optional'} |"
            for p in others
        ]
    rows = [
        (
            f.name,
            _type_label(f.type_name, f.is_list),
            f.required,
            f.constraints.get("enum"),
        )
        for f in (ep.body.fields if ep.body else [])
    ] + [
        (p.name, p.type_name or "str", p.required, p.constraints.get("enum"))
        for p in ep.params
        if p.location == "body"
    ]
    rows.sort(key=lambda r: not r[2])  # required first, order kept inside each group
    if rows:
        shape = (
            "a list of objects"
            if ep.body is not None and ep.body.is_list
            else "an object"
        )
        lines += [
            "",
            f"### Body ({shape})",
            "",
            "| Field | Type | Required |",
            "| --- | --- | --- |",
        ]
        lines += [
            f"| `{_cell(n)}` | `{_cell(t)}` | {'required' if r else 'optional'} |"
            for n, t, r, _ in rows
        ]
        enums = [(n, e) for n, _, _, e in rows if isinstance(e, list) and e]
        if enums:
            lines += ["", "### Allowed values", ""]
            lines += [
                f"- `{_cell(n)}`: " + ", ".join(f"`{_cell(v)}`" for v in e)
                for n, e in enums
            ]
    keys = ep.return_keys or ep.response_fields
    if keys:
        lines += [
            "",
            "### Response",
            "",
            "Fields: " + ", ".join(f"`{_cell(k)}`" for k in keys) + ".",
        ]
    if mode == "fixed":
        note = "Fixed values. `TODO` means the code gave no example; fill it in."
    else:
        note = "Random fake values, set by the before-request script; they check the request shape, not real results."
    lines += ["", "### About this request", "", note]
    return "\n".join(lines)


def build_request(
    ep: Endpoint,
    ident: str,
    name: str,
    mode: str,
    seq: int,
    auth: AuthPlan,
    central: bool = True,
) -> _Built:
    todos: list[str] = []
    incomplete: list[str] = []
    entries = (
        _entries_fixed(ep, ident, todos) if mode == "fixed" else _entries_random(ep)
    )

    headers = [e for e in entries if e.kind == "header"]
    lines = [
        "info:",
        f"  name: {q(name)}",
        "  type: http",
        f"  seq: {seq}",
        "",
        "http:",
        f"  method: {ep.method.upper()}",
        f"  url: {q(_url(ep, entries, auth))}",
    ]
    header_rows = [(h.name, h.value) for h in headers if h.enabled]
    if auth.header:
        header_rows.append(auth.header)
    if header_rows:
        lines.append("  headers:")
        for hn, hv in header_rows:
            lines += [f"    - name: {qn(hn)}", f"      value: {q(hv)}"]

    param_rows = [e for e in entries if e.kind in ("path", "query")]
    auth_query = [auth.query] if auth.query else []
    if param_rows or auth_query:
        lines.append("  params:")
        for e in param_rows:
            lines += [
                f"    - name: {qn(e.name)}",
                f"      value: {q(e.value)}",
                f"      type: {e.kind}",
            ]
            if not e.enabled:
                lines.append("      disabled: true")
        for an, av in auth_query:
            lines += [
                f"    - name: {qn(an)}",
                f"      value: {q(av)}",
                "      type: query",
            ]

    forms = [e for e in entries if e.kind == "form" and e.enabled]
    embedded = [p for p in ep.params if p.location == "body"]
    body_json: str | None = None
    if mode == "fixed":
        if ep.body is not None:
            value, body_todos = fixed_body(ep.body, ep)
            todos += [f"{ident}: body.{t}" for t in body_todos]
            body_json = json.dumps(value, indent=2)
        elif embedded:
            data: dict[str, object] = {}
            for p in embedded:
                res = fixed_value(p, ep)
                if res.todo:
                    todos.append(f"{ident}: {p.name} ({res.reason})")
                if res.enabled:
                    data[p.name] = res.value
            body_json = json.dumps(data, indent=2)
    elif (template := random_request(ep).body_template) is not None:
        # The body refers to the random_<field> variables set by the script.
        body_json = template
    elif ep.body is not None:
        # List body: shape preview only, the script replaces it with req.setBody.
        shape = _shape(ep.body)
        body_json = json.dumps([shape] if ep.body.is_list else shape, indent=2)
    elif embedded:
        body_json = json.dumps({p.name: RANDOM_MARK for p in embedded}, indent=2)
    if body_json is not None:
        lines += ["  body:", "    type: json", f"    data: {block(body_json, 6)}"]
    elif forms:
        lines += ["  body:", "    type: form-urlencoded", "    data:"]
        for e in forms:
            lines += [f"      - name: {qn(e.name)}", f"        value: {q(e.value)}"]
    lines.append("  auth: inherit")

    if mode == "random":
        script, notes = _random_script(ep, central)
        incomplete += [f"{ident}: {n}" for n in notes]
        if script:
            lines += [
                "",
                "runtime:",
                "  scripts:",
                "    - type: before-request",
                f"      code: {block(script, 8)}",
            ]
    lines += ["", SETTINGS.rstrip("\n"), "", "docs: " + block(_docs(ep, mode), 2), ""]
    return _Built("\n".join(lines), todos, incomplete)


# ---------------------------------------------------------------- collection


def _environment(env: str, base_url: str, description: str, secrets: list[str]) -> str:
    lines = [
        f"name: {env}",
        "variables:",
        "  - name: baseUrl",
        f"    value: {q(base_url)}",
        f"    description: {q(description)}",
    ]
    for s in secrets:
        lines += ["  - secret: true", f"    name: {s}", '    description: ""']
    return "\n".join(lines) + "\n"


def _opencollection(name: str, scripts: list[tuple[str, str]]) -> str:
    lines = ["opencollection: 1.0.0", "", "info:", f"  name: {q(name)}", ""]
    if scripts:
        lines += ["request:", "  scripts:"]
        for kind, code in scripts:
            lines += [f"    - type: {kind}", f"      code: {block(code, 8)}"]
    lines += [
        "bundled: false",
        "extensions:",
        "  bruno:",
        "    ignore:",
        "      - node_modules",
        "      - .git",
        "      - docs",
        "",
    ]
    return "\n".join(lines)


@dataclass
class Rendered:
    files: dict[str, str]
    plan: Plan
    discovery: DiscoveryResult
    launch: LaunchResult
    todos: list[str] = field(default_factory=list)
    incomplete: list[str] = field(default_factory=list)
    placeholders: list[str] = field(default_factory=list)

    def report_lines(self) -> list[str]:
        lines = list(self.discovery.outcome_lines())
        n = len(self.plan.add)
        lines.append(
            f"{2 * n} requests to write for {n} new endpoint(s) (fixed and random)"
        )
        if self.plan.unchanged:
            lines.append(
                f"{len(self.plan.unchanged)} endpoint(s) already in the collection"
            )
        for c in self.plan.collisions + self.plan.conflicts:
            where = ", ".join(f"{s.file}:{s.line}" for s in c.sources)
            lines.append(
                f"not written, needs a naming decision: {', '.join(c.identities)} ({where}) {c.reason}"
            )
        for ch in self.plan.changed:
            lines.append(f"changed in the code, collection untouched: {ch.identity}")
        for old in self.plan.disappeared:
            lines.append(f"no longer in the code, collection untouched: {old}")
        for old, new in self.plan.possible_renames:
            lines.append(f"possible rename (hint only): {old} -> {new}")
        lines += [f"launch settings: {n}" for n in self.launch.notes]
        lines += [f"TODO placeholder: {t}" for t in self.todos]
        lines += [f"random value incomplete: {t}" for t in self.incomplete]
        lines += [f"fill in: {p}" for p in self.placeholders]
        return lines


SET_TOKEN = 'bru.setVar("access_token_" + bru.getEnvName().toLowerCase(), {value});'
USE_TOKEN = (
    'bru.setVar("access_token", '
    'bru.getVar("access_token_" + bru.getEnvName().toLowerCase()));'
)


def camel(name: str) -> str:
    parts = [p for p in re.split(r"[_\-\s]+", name) if p]
    if not parts:
        return "value"
    return parts[0] + "".join(p[:1].upper() + p[1:] for p in parts[1:])


def _token_files(token: TokenEndpoint, seq: int) -> dict[str, str]:
    field_name = token.token_field
    value = (
        f"res.body.{field_name}"
        if field_name.isidentifier()
        else f"res.body[{json.dumps(field_name)}]"
    )
    lines = [
        "info:",
        '  name: "Get token"',
        "  type: http",
        "  seq: 1",
        "",
        "http:",
        "  method: POST",
        f"  url: {q('{{baseUrl}}' + _path_url(token.path))}",
    ]
    if token.grant_inputs:
        lines += ["  body:", "    type: form-urlencoded", "    data:"]
        for item in token.grant_inputs:
            lines += [
                f"      - name: {qn(item)}",
                f"        value: {q('{{' + camel(item) + '}}')}",
            ]
    lines += [
        "  auth: inherit",
        "",
        "runtime:",
        "  scripts:",
        "    - type: after-response",
        f"      code: {block(SET_TOKEN.format(value=value), 8)}",
        "",
        SETTINGS.rstrip("\n"),
        "",
    ]
    return {
        "auth/folder.yml": (
            f'info:\n  name: "auth"\n  type: folder\n  seq: {seq}\n\n'
            "request:\n  auth: inherit\n"
        ),
        "auth/Get token.yml": "\n".join(lines),
    }


def render_collection(
    result: DiscoveryResult,
    name: str,
    launch: LaunchResult,
    existing: ExistingState | None = None,
    central_helpers: bool = True,
) -> Rendered:
    """All collection files as relative path -> text, for the endpoints to add."""
    token = result.token
    token_ident = f"POST {normalize_path(token.path)}" if token else None
    endpoints = [e for e in result.endpoints if identity(e) != token_ident]
    the_plan = plan(endpoints, existing or ExistingState(set(), {}))
    auth = AuthPlan.from_discovery(result)
    secrets = [auth.secret] if auth.secret else []
    collection_scripts: list[tuple[str, str]] = []
    codes: list[str] = []
    if central_helpers and the_plan.add:
        codes.append(HELPERS_SCRIPT)
    if token:
        secrets += [camel(i) for i in token.grant_inputs if camel(i) not in secrets]
        codes.append(USE_TOKEN)
    if codes:
        collection_scripts.append(("before-request", "\n".join(codes)))

    files: dict[str, str] = {
        "opencollection.yml": _opencollection(name, collection_scripts),
        ".gitignore": GITIGNORE,
    }
    proxy = (
        "URL as clients reach it, including any proxy or load balancer path prefix; "
        "the route prefix from the code stays in each request"
    )
    local_desc = (
        "URL of the app run locally, from the VS Code launch settings"
        if launch.source
        else "URL of the app run locally; set by hand"
    )
    for env, url, desc in (
        ("LOCAL", launch.url, local_desc),
        ("DEV", DEV_URL, proxy),
        ("PROD", PROD_URL, proxy),
    ):
        files[f"environments/{env}.yml"] = _environment(env, url, desc, secrets)

    rendered = Rendered(files, the_plan, result, launch)
    folders: dict[str, str] = {}
    seqs: dict[str, int] = {}
    if token:
        files.update(_token_files(token, 1))
        folders["auth"] = "auth"
        seqs["auth"] = 1
    for item in the_plan.add:
        folder = folders.setdefault(item.folder.casefold(), item.folder)
        if f"{folder}/folder.yml" not in files:
            files[f"{folder}/folder.yml"] = (
                f"info:\n  name: {q(folder)}\n  type: folder\n  seq: {len(folders)}\n\n"
                "request:\n  auth: inherit\n"
            )
        _add_pair(rendered, item, folder, seqs, auth, central_helpers)

    if launch.url.endswith("<port>"):
        rendered.placeholders.append(
            "baseUrl (LOCAL): the port is not known, set it by hand"
        )
    rendered.placeholders += [
        "baseUrl (DEV): replace https://<dev-host>",
        "baseUrl (PROD): replace https://<prod-host>",
        PROXY_NOTE,
    ]
    if token:
        rendered.placeholders.append(
            "token request auth/Get token: run it first in each environment "
            "(the token is kept per environment while Bruno is open)"
        )
    for s in secrets:
        rendered.placeholders.append(
            f"{s} (secret, LOCAL/DEV/PROD): type the value in Bruno; never commit it"
        )
    return rendered


def _add_pair(
    rendered: Rendered,
    item: Planned,
    folder: str,
    seqs: dict[str, int],
    auth: AuthPlan,
    central: bool,
) -> None:
    for mode, req_name in zip(MODES, (item.fixed_name, item.random_name)):
        seqs[folder] = seqs.get(folder, 0) + 1
        built = build_request(
            item.endpoint, item.identity, req_name, mode, seqs[folder], auth, central
        )
        rendered.files[f"{folder}/{req_name}.yml"] = built.text
        rendered.todos += built.todos
        rendered.incomplete += built.incomplete


# -------------------------------------------------------------------- writer


@dataclass
class WriteReport:
    written: list[str] = field(default_factory=list)
    skipped_existing: list[str] = field(default_factory=list)
    refused: str = ""


def _existing_names(root: Path) -> set[str]:
    found: set[str] = set()
    for base, _dirs, names in os.walk(root):
        for n in names:
            found.add(Path(base, n).relative_to(root).as_posix().casefold())
    return found


def write_collection(files: dict[str, str], out_dir: Path) -> WriteReport:
    """Write files that do not exist yet; never overwrite, delete or rename."""
    out = Path(out_dir)
    report = WriteReport()
    if out.exists():
        if not out.is_dir():
            report.refused = "the output path exists and is not a folder"
            return report
        if any(out.iterdir()) and not (out / "docs").is_dir():
            report.refused = (
                "the output folder is not empty and has no docs/ folder, so it was "
                "not made by this tool; nothing was written"
            )
            return report
    root = out.resolve()
    for rel in files:
        target = (root / rel).resolve()
        if Path(rel).is_absolute() or root not in target.parents:
            report.refused = (
                f"a file path leaves the output folder: {rel!r}; nothing was written"
            )
            return report
    present = _existing_names(out) if out.exists() else set()
    made_files: list[Path] = []
    made_dirs: list[Path] = []
    try:
        for rel, text in files.items():
            key = Path(rel).as_posix().casefold()
            if key in present:
                report.skipped_existing.append(rel)
                continue
            target = root / rel
            missing = [
                p for p in (target.parent, *target.parent.parents) if not p.exists()
            ]
            made_dirs += missing
            target.parent.mkdir(parents=True, exist_ok=True)
            with open(target, "x", encoding="utf-8", newline="\n") as handle:
                made_files.append(target)
                handle.write(text)
            present.add(key)
            report.written.append(rel)
    except OSError:
        for path in reversed(made_files):
            path.unlink(missing_ok=True)
        for path in sorted(set(made_dirs), key=lambda p: len(p.parts), reverse=True):
            try:
                path.rmdir()
            except OSError:
                pass
        report.written = []
        report.refused = (
            "a file could not be written (operating system error); the files written "
            "in this call were removed"
        )
    return report
