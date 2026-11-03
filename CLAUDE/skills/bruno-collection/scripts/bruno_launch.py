"""The `LOCAL` base URL from the repo's VS Code launch settings.

Reads only `.vscode/launch.json`. The launch file's `envFile` is never opened and no
`env` value is copied except `HOST` and `PORT`, because the rest can hold secrets.
Python 3.9 and newer, stdlib only.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from bruno_params import Source

PLACEHOLDER = "http://localhost:<port>"
LAUNCH_FILE = ".vscode/launch.json"
SERVERS = {"uvicorn", "hypercorn", "gunicorn", "granian", "fastapi"}
NOT_THE_APP = {"pytest", "unittest", "ruff", "mypy"}
WILDCARD_HOSTS = {"0.0.0.0", "::", "[::]", "127.0.0.1", "localhost", "::1"}
SSL_OPTIONS = ("--ssl-keyfile", "--ssl-certfile", "--keyfile", "--certfile", "--certs")
DEFAULT_PORT = "8000"


@dataclass
class LaunchResult:
    url: str
    source: Source | None = None
    notes: list[str] = field(default_factory=list)


def strip_jsonc(text: str) -> str:
    """Remove comments and trailing commas outside strings (JSON with comments)."""
    out: list[str] = []
    i, n = 0, len(text)
    in_string = False
    while i < n:
        ch = text[i]
        if in_string:
            out.append(ch)
            if ch == "\\" and i + 1 < n:
                out.append(text[i + 1])
                i += 1
            elif ch == '"':
                in_string = False
        elif ch == '"':
            in_string = True
            out.append(ch)
        elif text.startswith("//", i):
            while i < n and text[i] != "\n":
                i += 1
            continue
        elif text.startswith("/*", i):
            end = text.find("*/", i + 2)
            i = n if end == -1 else end + 2
            continue
        else:
            out.append(ch)
        i += 1
    return _drop_trailing_commas("".join(out))


def _drop_trailing_commas(text: str) -> str:
    out: list[str] = []
    in_string = False
    for index, ch in enumerate(text):
        if in_string:
            out.append(ch)
            if ch == '"' and (index == 0 or text[index - 1] != "\\"):
                in_string = False
        elif ch == '"':
            in_string = True
            out.append(ch)
        elif ch == ",":
            rest = text[index + 1 :].lstrip()
            if not rest or rest[0] in "]}":
                continue
            out.append(ch)
        else:
            out.append(ch)
    return "".join(out)


def _option(args: list[str], names: tuple[str, ...]) -> str | None:
    for i, token in enumerate(args):
        for name in names:
            if token == name and i + 1 < len(args):
                return args[i + 1]
            if token.startswith(name + "="):
                return token.split("=", 1)[1]
    return None


def _args(cfg: dict[str, object]) -> list[str]:
    raw = cfg.get("args")
    return [a for a in raw if isinstance(a, str)] if isinstance(raw, list) else []


def _env(cfg: dict[str, object]) -> dict[str, object]:
    raw = cfg.get("env")
    return raw if isinstance(raw, dict) else {}


def _is_app_run(cfg: dict[str, object]) -> bool:
    module = cfg.get("module")
    args = _args(cfg)
    if isinstance(module, str):
        return module not in NOT_THE_APP and "pytest" not in args
    program = cfg.get("program")
    return (
        isinstance(program, str)
        and program.endswith(".py")
        and "test" not in program.lower()
    )


def _literal(value: object) -> str | None:
    """A plain value; an unresolved `${...}` reference is not a value."""
    if isinstance(value, (str, int)) and "${" not in str(value):
        return str(value)
    return None


def _line_of(text: str, name: object) -> int:
    if isinstance(name, str):
        match = re.search(r'"name"\s*:\s*' + re.escape(json.dumps(name)), text)
        if match:
            return text.count("\n", 0, match.start()) + 1
    return 1


def local_base_url(root: Path) -> LaunchResult:
    path = Path(root) / ".vscode" / "launch.json"
    if not path.is_file():
        return LaunchResult(
            PLACEHOLDER,
            None,
            [
                f"no {LAUNCH_FILE}; set the LOCAL baseUrl by hand (default {PLACEHOLDER})"
            ],
        )
    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(strip_jsonc(raw))
        configs = [c for c in data.get("configurations", []) if isinstance(c, dict)]
    except (OSError, ValueError, AttributeError):
        return LaunchResult(
            PLACEHOLDER,
            None,
            [f"{LAUNCH_FILE} could not be read as JSON; set the LOCAL baseUrl by hand"],
        )
    matches = [c for c in configs if _is_app_run(c)]
    if not matches:
        return LaunchResult(
            PLACEHOLDER,
            None,
            [
                f"no launch configuration in {LAUNCH_FILE} starts the app; set the LOCAL baseUrl by hand"
            ],
        )
    chosen = matches[0]
    notes = [
        f'also matches launch configuration "{c.get("name", "?")}"; not used'
        for c in matches[1:]
    ]
    args = _args(chosen)
    env = _env(chosen)
    host = _literal(_option(args, ("--host",))) or _literal(env.get("HOST"))
    port = _literal(_option(args, ("--port", "-p"))) or _literal(env.get("PORT"))
    bind = _literal(_option(args, ("--bind", "-b")))
    if bind and ":" in bind:
        bind_host, _, bind_port = bind.rpartition(":")
        host, port = host or bind_host, port or bind_port
    if not (port and port.isdigit()):
        port = None
    if port is None and chosen.get("module") in SERVERS:
        port = DEFAULT_PORT
        notes.append(
            f"no port in the launch configuration; default port {DEFAULT_PORT} assumed"
        )
    scheme = (
        "https"
        if any(_option(args, (o,)) is not None or o in args for o in SSL_OPTIONS)
        else "http"
    )
    source = Source(LAUNCH_FILE, _line_of(raw, chosen.get("name")))
    if port is None:
        notes.append(
            "no port found in the launch configuration; set the LOCAL baseUrl by hand"
        )
        return LaunchResult(PLACEHOLDER, source, notes)
    shown = "localhost" if not host or host in WILDCARD_HOSTS else host
    return LaunchResult(f"{scheme}://{shown}:{port}", source, notes)
