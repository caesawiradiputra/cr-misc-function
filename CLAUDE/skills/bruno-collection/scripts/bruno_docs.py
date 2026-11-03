"""The `docs/` OKF bundle of a collection: write it, read it back, keep the log.

Mechanical facts (identity, names, parameters, where each fixed value came from,
the original sample and schema, the source `file:line`, variable names) are written
here. Descriptions and the log reason come from Claude and are passed in. Nothing in
the bundle holds a value of a variable or a token. Python 3.9 and newer, stdlib only.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import importlib.util
import json
import re
from dataclasses import asdict, is_dataclass
from pathlib import Path

from bruno_identity import (
    DocEntry,
    ExistingState,
    Planned,
    normalize_path,
    safe_name,
    signature,
)
from bruno_params import FieldSpec, ModelSpec
from bruno_render import ENVIRONMENTS, PROXY_NOTE, Rendered
from bruno_values import fixed_body, fixed_value

BRUNO_VERSION = "4.3.0"
STATE_HEADING = "# State"
FENCE = re.compile(r"```json\n(.*?)\n```", re.S)


class DocsError(Exception):
    """`docs/` is missing or cannot be read; sync must write nothing."""


def _now() -> dt.datetime:
    return dt.datetime.now().astimezone()


def _stamp(now: dt.datetime) -> str:
    return now.isoformat(timespec="seconds")


def _q(text: object) -> str:
    return json.dumps(str(text), ensure_ascii=True)


def slug(ep_identity: str) -> str:
    method, _, path = ep_identity.partition(" ")
    cleaned = re.sub(r"[{}]", "", normalize_path(path)).lower()
    return f"{method.lower()}-" + (
        re.sub(r"[^a-z0-9]+", "-", cleaned).strip("-") or "root"
    )


# ----------------------------------------------------------------- state JSON


def _jsonable(value: object) -> object:
    if is_dataclass(value) and not isinstance(value, type):
        return {k: _jsonable(v) for k, v in asdict(value).items()}
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def _model(model: ModelSpec) -> dict[str, object]:
    return {
        "name": model.name,
        "is_list": model.is_list,
        "fields": [_field(f) for f in model.fields],
    }


def _field(f: FieldSpec) -> dict[str, object]:
    out: dict[str, object] = {
        "name": f.name,
        "type": f.type_name,
        "required": f.required,
        "constraints": _jsonable(f.constraints),
        "is_list": f.is_list,
    }
    if f.enum_values is not None:
        out["enum"] = _jsonable(f.enum_values)
    if f.children is not None:
        out["children"] = _model(f.children)
    return out


def _state(item: Planned) -> dict[str, object]:
    ep = item.endpoint
    params: dict[str, object] = {}
    origins: dict[str, str] = {}
    for p in ep.params:
        if p.location in ("path", "query", "header", "form", "body"):
            res = fixed_value(p, ep)
            params[p.name] = {
                "in": p.location,
                "value": _jsonable(res.value),
                "enabled": res.enabled,
            }
            origins[p.name] = res.origin
    body: object = None
    if ep.body is not None:
        body = _jsonable(fixed_body(ep.body, ep)[0])
    return {
        "identity": item.identity,
        "function": ep.function,
        "signature": signature(ep),
        "files": list(item.files),
        "origins": origins,
        "original": {"params": params, "body": body},
        "schema": {
            "params": [
                {
                    "name": p.name,
                    "in": p.location,
                    "type": p.type_name,
                    "required": p.required,
                    "constraints": _jsonable(p.constraints),
                }
                for p in ep.params
            ],
            "body": _model(ep.body) if ep.body is not None else None,
        },
    }


def _state_text(state: dict[str, object]) -> str:
    return json.dumps(state, indent=2, sort_keys=True).replace("`", "\\u0060")


# ------------------------------------------------------------------- concepts


def _frontmatter(
    kind: str,
    title: str,
    description: str,
    resource: str | None,
    tags: list[str],
    model: str,
    now: dt.datetime,
    sources: list[str],
) -> str:
    lines = [
        "---",
        f"type: {kind}",
        f"title: {_q(title)}",
        f"description: {_q(description)}",
    ]
    if resource:
        lines.append(f"resource: {_q(resource)}")
    lines += [
        f"tags: [{', '.join(tags)}]",
        "generated:",
        f"  by: {model}",
        f"  at: {_stamp(now)}",
        "status: draft",
        "sources:",
    ]
    for n, src in enumerate(sources, 1):
        lines += [f"  - id: src{n}", f"    resource: {_q(src)}"]
    lines.append("---")
    return "\n".join(lines) + "\n"


def request_concept(item: Planned, model: str, now: dt.datetime) -> str:
    ep = item.endpoint
    state = _state(item)
    origins = state["origins"]
    assert isinstance(origins, dict)
    src = f"{ep.source.file}:{ep.source.line}"
    summary = (ep.docstring or "").strip().splitlines()[0] if ep.docstring else ""
    description = summary or f"{ep.method.upper()} {normalize_path(ep.path)} in the API"
    rows = [
        "| Name | In | Type | Required | Fixed value from |",
        "| --- | --- | --- | --- | --- |",
    ]
    for p in ep.params:
        rows.append(
            f"| `{p.name}` | {p.location} | `{p.type_name or '?'}` | "
            f"{'yes' if p.required else 'no'} | {origins.get(p.name, '')} |"
        )
    body_line = (
        f"Body model: `{ep.body.name}`." if ep.body is not None else "No body model."
    )
    return (
        _frontmatter(
            "Request",
            f"{ep.method.upper()} {normalize_path(ep.path)}",
            description,
            item.identity,
            ["request", item.folder.lower()],
            model,
            now,
            [src],
        )
        + f"\n{description}[^src1]\n\n"
        f"Requests in folder `{item.folder}`: `{item.fixed_name}` and `{item.random_name}`.\n"
        f"Handler: `{ep.function}`.\n\n"
        "# Parameters\n\n" + "\n".join(rows) + f"\n\n{body_line}\n\n"
        "Random values are generated by the request's before-request script and prove "
        "the request shape, not real results.\n\n"
        f"{STATE_HEADING}\n\nMachine-readable; sync and reset read it. Do not edit by hand.\n\n"
        f"```json\n{_state_text(state)}\n```\n\n"
        f"[^src1]: `{src}` in the repo.\n"
    )


def environments_concept(rendered: Rendered, model: str, now: dt.datetime) -> str:
    secrets = _secret_names(rendered)
    rows = [
        "| Variable | Secret | Filled by | Used by |",
        "| --- | --- | --- | --- |",
        "| `baseUrl` | no | the user, per environment | every request |",
    ]
    rows += [
        f"| `{s}` | yes | the user, in Bruno (never in a file) | {_used_by(s)} |"
        for s in secrets
    ]
    if rendered.discovery.token is not None:
        rows.append(
            "| `access_token` | runtime | copied by the collection script | requests with `Authorization` |"
        )
    return (
        _frontmatter(
            "Environments",
            "Environments",
            "Variable names of the LOCAL, DEV and PROD environments; no values.",
            None,
            ["environments"],
            model,
            now,
            ["environments/"],
        )
        + "\nThe collection has the environments "
        + ", ".join(f"`{e}`" for e in ENVIRONMENTS)
        + " with identical variable names. Values are never written here.[^src1]\n\n"
        + "\n".join(rows)
        + "\n\n# Addresses\n\n"
        "- `LOCAL`: taken from the VS Code launch settings of the repo, when found.\n"
        "- `DEV`, `PROD`: placeholders; replace them in Bruno.\n\n"
        "# Proxy and gateway (open)\n\n"
        f"- `DEV` and `PROD`: {PROXY_NOTE}.\n"
        "- Details follow from the user (an nginx sample, the Apigee gateway); until then "
        "this stays a note.\n\n"
        "[^src1]: The environment files of this collection.\n"
    )


def _secret_names(rendered: Rendered) -> list[str]:
    text = rendered.files["environments/DEV.yml"]
    return re.findall(r"- secret: true\n    name: (\w+)", text)


def _used_by(secret: str) -> str:
    return (
        "`auth/Get token`"
        if secret not in ("apiKey", "bearerToken", "basicCredentials")
        else "every request"
    )


def token_concept(rendered: Rendered, model: str, now: dt.datetime) -> str:
    token = rendered.discovery.token
    assert token is not None
    src = f"{token.source.file}:{token.source.line}"
    inputs = ", ".join(f"`{i}`" for i in token.grant_inputs) or "none"
    return (
        _frontmatter(
            "Authentication",
            "Token request",
            "How the access token is fetched and kept per environment.",
            f"POST {normalize_path(token.path)}",
            ["auth", "token"],
            model,
            now,
            [src],
        )
        + f"\nThe request `auth/Get token` calls `POST {normalize_path(token.path)}`[^src1] "
        f"with the secret variables for {inputs}. Its response field `{token.token_field}` is kept per "
        "environment as `access_token_local`, `access_token_dev` or `access_token_prod`.\n\n"
        "A collection-level before-request script copies the active environment's token into "
        "`access_token`, and requests send `Authorization: Bearer {{access_token}}`. "
        "If the environment has no token yet, the request fails visibly; it never "
        "carries another environment's token. Nothing is written to a file.\n\n"
        f"[^src1]: `{src}` in the repo.\n"
    )


# ------------------------------------------------------------- index and log


def _index_line(item: Planned, ident_slug: str) -> str:
    return f"- [{item.endpoint.method.upper()} {normalize_path(item.endpoint.path)}](/requests/{ident_slug}.md): {item.fixed_name}, {item.random_name}"


def _log_entry(
    rendered: Rendered, added: list[Planned], reason: str, creation: bool
) -> list[str]:
    lines: list[str] = []
    names = ", ".join(f"`{i.fixed_name}`/`{i.random_name}`" for i in added)
    sources = ", ".join(
        sorted({f"{i.endpoint.source.file}:{i.endpoint.source.line}" for i in added})
    )
    if added:
        label = "Creation" if creation else "Added"
        lines.append(
            f"- **{label}**: {len(added)} endpoint(s): {names}. Reason: {reason}. "
            f"Source: {sources}. Unverified: no human has reviewed it yet."
        )
    plan = rendered.plan
    for c in plan.collisions + plan.conflicts:
        where = ", ".join(f"{s.file}:{s.line}" for s in c.sources)
        lines.append(
            f"- **Needs a decision**: {', '.join(c.identities)} ({where}): {c.reason}. Nothing was written."
        )
    for ch in plan.changed:
        lines.append(
            f"- **Needs a decision**: `{ch.identity}` changed in the code (before {ch.before}, now {ch.now}). The request files were not touched."
        )
    for old in plan.disappeared:
        lines.append(
            f"- **Needs a decision**: `{old}` is no longer in the code. Nothing was deleted."
        )
    for old, new in plan.possible_renames:
        lines.append(
            f"- **Needs a decision**: `{old}` may have been renamed to `{new}` (hint only)."
        )
    return lines


def _slugs(items: list[Planned], taken: set[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    used = {t.casefold() for t in taken}
    for item in items:
        s = slug(item.identity)
        if s.casefold() in used:
            s = f"{s}-{hashlib.sha1(item.identity.encode()).hexdigest()[:6]}"
        used.add(s.casefold())
        out[item.identity] = s
    return out


def docs_files(
    rendered: Rendered, name: str, model: str, reason: str
) -> dict[str, str]:
    """A fresh bundle: index, log, environments, token doc, one concept per request."""
    now = _now()
    items = rendered.plan.add
    slugs = _slugs(items, set())
    files: dict[str, str] = {}
    groups = [
        "## Environments",
        "",
        "- [Environments](/environments.md): variable names and where each is filled; no values",
    ]
    files["docs/environments.md"] = environments_concept(rendered, model, now)
    if rendered.discovery.token is not None:
        files["docs/auth/token.md"] = token_concept(rendered, model, now)
        groups += [
            "",
            "## Authentication",
            "",
            "- [Token request](/auth/token.md): how the token is fetched and kept per environment",
        ]
    groups += ["", "## Requests", ""]
    for item in items:
        files[f"docs/requests/{slugs[item.identity]}.md"] = request_concept(
            item, model, now
        )
        groups.append(_index_line(item, slugs[item.identity]))
    title = f"{name} collection"
    files["docs/index.md"] = (
        '---\nokf_version: "0.2"\n---\n\n'
        f"# {title}\n\nDocumentation and change tracking of the Bruno collection `{name}`, "
        f"written for Bruno {BRUNO_VERSION} (the file format was verified against that version). "
        "Read this index, then only the concepts the task needs.\n\n"
        + "\n".join(groups)
        + "\n"
    )
    entry = _log_entry(rendered, items, reason, True)
    files["docs/log.md"] = (
        f"# Log\n\n## {now.date().isoformat()}\n\n" + "\n".join(entry) + "\n"
    )
    return files


# ------------------------------------------------------------------- reading


def read_docs(out_dir: Path) -> ExistingState:
    """Existing collection files and the request concepts; raises `DocsError`."""
    root = Path(out_dir)
    docs = root / "docs"
    if not docs.is_dir():
        raise DocsError(
            "the docs/ folder is missing, so this is not a collection made by this tool"
        )
    for needed in ("index.md", "log.md"):
        if not (docs / needed).is_file():
            raise DocsError(f"docs/{needed} is missing")
        try:
            (docs / needed).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            raise DocsError(f"docs/{needed} cannot be read as UTF-8 text") from None
    entries: dict[str, DocEntry] = {}
    bad: list[str] = []
    requests = docs / "requests"
    for path in sorted(requests.glob("*.md")) if requests.is_dir() else []:
        try:
            entries_from = _parse_concept(path)
        except (ValueError, KeyError, OSError, TypeError):
            bad.append(f"docs/requests/{path.name}")
            continue
        entries[entries_from.identity] = entries_from
    if bad:
        raise DocsError("cannot read these concepts: " + ", ".join(bad))
    files = {
        p.relative_to(root).as_posix()
        for p in root.rglob("*")
        if p.is_file() and ".git" not in p.parts
    }
    return ExistingState(files, entries)


def _parse_concept(path: Path) -> DocEntry:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n") or STATE_HEADING not in text:
        raise ValueError("not a request concept")
    match = FENCE.search(text.split(STATE_HEADING, 1)[1])
    if match is None:
        raise ValueError("no state block")
    state = json.loads(match.group(1))
    return DocEntry(
        str(state["identity"]),
        str(state["function"]),
        [str(x) for x in state["signature"]],
        [str(x) for x in state["files"]],
    )


# ---------------------------------------------------------------------- sync


def sync_docs(rendered: Rendered, out_dir: Path, model: str, reason: str) -> list[str]:
    """Add concepts for new endpoints and extend `index.md` and `log.md`; never rewrite."""
    root = Path(out_dir) / "docs"
    now = _now()
    items = rendered.plan.add
    entry = _log_entry(rendered, items, reason, False)
    if not entry:
        return []
    taken = (
        {p.stem for p in (root / "requests").glob("*.md")}
        if (root / "requests").is_dir()
        else set()
    )
    slugs = _slugs(items, taken)
    written: list[str] = []
    index_lines: list[str] = []
    for item in items:
        rel = f"requests/{slugs[item.identity]}.md"
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "x", encoding="utf-8", newline="\n") as handle:
            handle.write(request_concept(item, model, now))
        written.append("docs/" + rel)
        index_lines.append(_index_line(item, slugs[item.identity]))
    if index_lines:
        _append_index(root / "index.md", index_lines)
    _add_log(root / "log.md", now.date().isoformat(), entry)
    return written


def _append_index(path: Path, lines: list[str], group: str = "Requests") -> None:
    text = path.read_text(encoding="utf-8")
    marker = f"\n## {group}\n"
    if marker in text:
        head, tail = text.split(marker, 1)
        rest = tail.split("\n## ", 1)
        block = rest[0].rstrip("\n") + "\n" + "\n".join(lines) + "\n"
        more = ("\n## " + rest[1]) if len(rest) > 1 else ""
        text = head + marker + block + more
    else:
        text = text.rstrip("\n") + f"\n\n## {group}\n\n" + "\n".join(lines) + "\n"
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def _add_log(path: Path, day: str, entry: list[str]) -> None:
    text = path.read_text(encoding="utf-8")
    heading = f"## {day}\n"
    if heading in text:
        text = text.replace(heading, heading + "\n" + "\n".join(entry) + "\n", 1)
    else:
        marker = "# Log\n"
        pos = text.find(marker)
        cut = pos + len(marker) if pos >= 0 else 0
        text = text[:cut] + f"\n{heading}\n" + "\n".join(entry) + "\n" + text[cut:]
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


# ---------------------------------------------------------------------- lint


def lint_summary(out_dir: Path) -> str:
    """Run the okf-writer linter on `docs/`, if that skill sits next to this one."""
    script = (
        Path(__file__).resolve().parents[2] / "okf-writer" / "scripts" / "okf_lint.py"
    )
    if not script.is_file():
        return (
            "OKF lint: not run (the okf-writer skill was not found next to this skill)"
        )
    spec = importlib.util.spec_from_file_location("okf_lint_for_bruno", script)
    if spec is None or spec.loader is None:
        return "OKF lint: not run (the linter could not be loaded)"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    report = module.lint(Path(out_dir) / "docs")
    return (
        f"OKF lint: {len(report.errors)} error(s), {len(report.warnings)} warning(s); "
        f"trust: {module.trust_summary((Path(out_dir) / 'docs').resolve())}"
    )


# ------------------------------------------------------- user-owned requests

NOT_REQUESTS = {"opencollection.yml", "folder.yml"}
GENERATED_AREAS = {"environments", "docs", "node_modules"}


def user_owned(out_dir: Path, existing: ExistingState) -> list[str]:
    """Request files no `docs/requests/` concept lists: external or hand-made.

    These are never overwritten, renamed or deleted by sync, edit or reset.
    """
    generated = {f.casefold() for e in existing.docs.values() for f in e.files}
    if (Path(out_dir) / "auth" / "Get token.yml").is_file():
        generated.add("auth/get token.yml")
    owned: list[str] = []
    for rel in sorted(existing.files):
        parts = rel.split("/")
        if (
            not rel.endswith(".yml")
            or parts[0] in GENERATED_AREAS
            or parts[-1] in NOT_REQUESTS
            or len(parts) < 2
            or rel.casefold() in generated
        ):
            continue
        owned.append(rel)
    return owned


METHODS = ("GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS")


def external_paths(title: str) -> tuple[str, str, str]:
    """(request file, concept file, slug) for an external placeholder title."""
    name = safe_name(title)
    if name.casefold() == "folder":  # would collide with external/folder.yml
        name += " request"
    ext_slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "request"
    return f"external/{name}.yml", f"docs/external/{ext_slug}.md", ext_slug


def external_files(
    title: str, method: str, model: str, reason: str
) -> tuple[dict[str, str], str, str]:
    """A placeholder request in `external/` and its concept.

    Returns (files, slug, request file path). `method` must be one of `METHODS`.
    """
    if method.upper() not in METHODS:
        raise ValueError("method")
    now = _now()
    request_path, concept_path, ext_slug = external_paths(title)
    name = Path(request_path).stem
    verb = method.upper()
    request = (
        f"info:\n  name: {_q(name)}\n  type: http\n  seq: 1\n\n"
        f'http:\n  method: {verb}\n  url: "TODO"\n  auth: inherit\n\n'
        "settings:\n  encodeUrl: true\n  timeout: 0\n  followRedirects: true\n"
        "  maxRedirects: 5\n  forwardAuthorizationHeader: true\n"
    )
    concept = (
        _frontmatter(
            "External Request",
            name,
            "A request that does not come from the repo's code, kept by the user.",
            None,
            ["external"],
            model,
            now,
            [request_path],
        )
        + f"\nPlaceholder `{name}` ({verb}) in the `external/` folder[^src1]. The user fills "
        "the URL and the values; this tool never overwrites, renames or deletes it, "
        "and a reset of the collection keeps it.\n\n"
        f"Created because: {reason}.\n\n"
        "[^src1]: The request file in this collection.\n"
    )
    folder = (
        'info:\n  name: "external"\n  type: folder\n  seq: 99\n\n'
        "request:\n  auth: inherit\n"
    )
    files = {
        request_path: request,
        "external/folder.yml": folder,
        concept_path: concept,
    }
    return files, ext_slug, request_path


def log_external(out_dir: Path, name: str, ext_slug: str, reason: str) -> None:
    root = Path(out_dir) / "docs"
    _append_index(
        root / "index.md",
        [f"- [{name}](/external/{ext_slug}.md): placeholder request kept by the user"],
        "External requests",
    )
    _add_log(
        root / "log.md",
        _now().date().isoformat(),
        [
            f"- **Added**: external placeholder `{name}` in `external/`. Reason: {reason}. "
            "Source: the user (not generated from the repo's code). "
            "Unverified: no human has reviewed it yet."
        ],
    )
