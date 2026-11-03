"""Read-only scan of a Bruno collection for plain-text secrets.

The report holds the kind and the length of a finding and where it is, never a
character of a value and never a line of a scanned file. A path is printed only when
every segment looks harmless, else as `<path-redacted:N>`. A file that cannot be read
safely is reported as *incomplete* and makes the exit code non-zero; it is never
counted as clean. There is no verbose mode. Line-based, no YAML parser.
Python 3.9 and newer, stdlib only.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path

MAX_BYTES = 2 * 1024 * 1024
MAX_LINE = 100_000
SCANNED_SUFFIXES = {
    ".yml", ".yaml", ".bru", ".md", ".json", ".js", ".env", ".txt", ".toml", ".ini",
    ".cfg", ".pem", ".key",
}  # fmt: skip
SKIP_DIRS = {"node_modules", ".git"}

# Last word of a name that makes it secret-like (one list, easy to extend).
SECRET_LAST_WORDS = {
    "key", "token", "secret", "password", "pass", "passwd", "pwd", "credential",
    "credentials", "apikey", "authorization", "auth", "cookie", "signature", "bearer",
}  # fmt: skip
HEADER_NAMES = {
    "authorization", "proxy-authorization", "apikey", "api-key", "x-api-key",
    "x-auth-token", "x-access-token", "x-token", "cookie",
}  # fmt: skip
HARMLESS_WORDS = {"inherit", "none", "true", "false", "null"}
HINTS = {
    "header-value": "move the value to a secret variable (for example apiKey) and write {{apiKey}}",
    "secret-name-plain-value": "mark the variable secret: true and clear the value",
    "secret-value-present": "clear the value; keep secret: true; type the value in Bruno",
    "secret-not-marked": "add secret: true to the variable",
    "bearer-token": "use Bearer {{access_token}} or a secret variable",
}

VARIABLE_ONLY = re.compile(r"^(?:[A-Za-z]+\s+)?(?:\{\{[\w.\- ]+\}\}\s*)+$")
PAIR = re.compile(r"^\s*(?:-\s+)?(?P<k>[\w.\-]+)\s*(?::\s+|=\s*|:$)\s*(?P<v>.*)$")
JSON_PAIR = re.compile(r'^\s*"(?P<k>[^"]+)"\s*:\s*(?P<v>.*?),?\s*$')
JWT = re.compile(r"eyJ[A-Za-z0-9_-]{6,}\.[A-Za-z0-9_-]{6,}\.[A-Za-z0-9_-]*")
PEM = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")
URL_CREDENTIAL = re.compile(r"[A-Za-z][A-Za-z0-9+.\-]*://[^/\s:@\"'{}]+:[^/\s@\"'{}]+@")
URL_SIGNATURE = re.compile(
    r"[?&](?:sig|signature|token|access_token|api[_-]?key|x-amz-signature)=([^&\s\"']{8,})",
    re.I,
)
CLOUD = re.compile(
    r"\b(?:AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}"
    r"|xox[abprs]-[A-Za-z0-9-]{10,}|AIza[0-9A-Za-z_\-]{35})\b"
)
BEARER = re.compile(r"\bBearer\s+([A-Za-z0-9._~+/=\-]{16,})")
OPAQUE = re.compile(r"[A-Za-z0-9+/_=\-]{32,}")
HEX = re.compile(r"^[0-9a-fA-F]{32,}$")
PATH_JWT = re.compile(r"eyJ[A-Za-z0-9_-]{5,}")
PATH_ASSIGN = re.compile(
    r"(?i)(password|passwd|pwd|pw|pass|secret|token|key|auth)\s*[=:]\s*\S"
)
PATH_OPAQUE = re.compile(r"^[A-Za-z0-9+/_=\-]{24,}$")
PRIORITY = {
    "private-key": 1, "jwt": 2, "url-credential": 3, "cloud-key": 4, "bearer-token": 5,
    "header-value": 6, "secret-value-present": 7, "secret-name-plain-value": 8,
    "secret-not-marked": 9, "url-signature": 10, "opaque-string": 11,
}  # fmt: skip


@dataclass
class Finding:
    path: str
    line: int
    kind: str
    length: int


@dataclass
class Incomplete:
    path: str
    reason: str


@dataclass
class ScanReport:
    findings: list[Finding] = field(default_factory=list)
    incomplete: list[Incomplete] = field(default_factory=list)
    scanned: int = 0
    other_types: int = 0
    lines: list[str] = field(default_factory=list)
    exit_code: int = 0


# ------------------------------------------------------------------- helpers


def _words(name: str) -> list[str]:
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", name)
    return [w.lower() for w in re.split(r"[^A-Za-z0-9]+", spaced) if w]


def secret_like(name: str) -> bool:
    words = _words(name)
    return bool(words) and words[-1] in SECRET_LAST_WORDS


def header_like(name: str) -> bool:
    return name.strip().lower().replace("_", "-") in HEADER_NAMES


def _clean(value: str) -> str:
    value = value.strip().rstrip(",").strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
        value = value[1:-1]
    return value


def _harmless(value: str) -> bool:
    """Empty, a variable reference, or a visible placeholder."""
    return (
        not value
        or value.upper() == "TODO"
        or value.lower() in HARMLESS_WORDS
        or value[0] in "[{"
        or bool(VARIABLE_ONLY.match(value))
    )


def _path_ok(rel: str) -> bool:
    if not rel.isprintable():  # control characters, newlines, undecodable bytes
        return False
    for segment in rel.split("/"):
        stem = segment.rsplit(".", 1)[0] if "." in segment else segment
        if (
            PATH_JWT.search(segment)
            or PATH_ASSIGN.search(segment)
            or re.search(r"[^/\s:@]+:[^/\s@]+@", segment)
            or (PATH_OPAQUE.match(stem) is not None and _mixed(stem))
        ):
            return False
        try:
            if _scan_text(segment):
                return False
        except ValueError:
            return False
    return True


def _display(rel: str, index: dict[str, int]) -> str:
    return rel if _path_ok(rel) else f"<path-redacted:{index[rel]}>"


# ------------------------------------------------------------ text analysis


def _num(block: dict[str, object], key: str) -> int:
    value = block.get(key)
    return value if isinstance(value, int) else 1


def _mixed(token: str) -> bool:
    return (
        any(c.isupper() for c in token)
        and any(c.islower() for c in token)
        and any(c.isdigit() for c in token)
    )


def _opaque_hit(line: str) -> int | None:
    stripped = re.sub(r"\{\{[^}]*\}\}", " ", line)
    for match in OPAQUE.finditer(stripped):
        token = match.group(0)
        mixed = _mixed(token)
        if mixed or HEX.match(token):
            return len(token)
    return None


def _scan_text(text: str) -> list[tuple[int, str, int]]:
    """(line, kind, length) for one file's text; one finding per line at most."""
    best: dict[int, tuple[int, str, int]] = {}

    def add(line: int, kind: str, length: int) -> None:
        old = best.get(line)
        if old is None or PRIORITY[kind] < old[0]:
            best[line] = (PRIORITY[kind], kind, length)

    lines = text.lstrip("﻿").splitlines()
    is_env = any(x.startswith("variables:") for x in lines)
    section = ""
    block: dict[str, object] | None = None

    def flush() -> None:
        nonlocal block
        if block is None:
            return
        name = block.get("name")
        value = block.get("value")
        if isinstance(name, str):
            real = isinstance(value, str) and not _harmless(value)
            vline = _num(block, "vline") if block.get("vline") else _num(block, "nline")
            if is_env and secret_like(name):
                if block.get("secret") and real:
                    add(vline, "secret-value-present", len(str(value)))
                elif not block.get("secret"):
                    if real:
                        add(vline, "secret-name-plain-value", len(str(value)))
                    else:
                        add(_num(block, "nline"), "secret-not-marked", 0)
            elif real and not is_env and (header_like(name) or section == "headers"):
                if header_like(name) or secret_like(name):
                    add(vline, "header-value", len(str(value)))
            elif real and not is_env and secret_like(name):
                add(vline, "secret-name-plain-value", len(str(value)))
        block = None

    for number, line in enumerate(lines, 1):
        if len(line) > MAX_LINE:
            raise ValueError("line too long")
        if PEM.search(line):
            add(number, "private-key", len(line.strip()))
        if (m := JWT.search(line)) is not None:
            add(number, "jwt", len(m.group(0)))
        if (m := URL_CREDENTIAL.search(line)) is not None:
            add(number, "url-credential", len(m.group(0)))
        if (m := CLOUD.search(line)) is not None:
            add(number, "cloud-key", len(m.group(0)))
        for m in BEARER.finditer(line):
            if not _harmless(m.group(1)):
                add(number, "bearer-token", len(m.group(1)))
        if (m := URL_SIGNATURE.search(line)) is not None and not _harmless(m.group(1)):
            add(number, "url-signature", len(m.group(1)))
        if (n := _opaque_hit(line)) is not None:
            add(number, "opaque-string", n)

        pair = PAIR.match(line) or JSON_PAIR.match(line)
        if re.match(r"^\s*-\s", line):
            flush()
            block = {"nline": number}
        if pair is None:
            continue
        key = pair.group("k").strip().strip("\"'")
        raw = pair.group("v")
        value = _clean(raw)
        if not value and raw == "" and not line.rstrip().endswith(":"):
            continue
        indent = len(line) - len(line.lstrip())
        if value == "" and line.rstrip().endswith(":"):
            if indent == 0 or key in ("headers", "params", "variables"):
                section = key if key in ("headers",) else ""
            continue
        if block is not None and key in ("name", "value", "secret", "description"):
            if key == "name":
                block["name"] = value
                block["nline"] = number
            elif key == "value":
                block["value"] = value
                block["vline"] = number
            elif key == "secret":
                block["secret"] = value.lower() == "true"
            continue
        if key in ("name", "value", "secret", "description"):
            continue
        if _harmless(value):
            continue
        if header_like(key):
            add(number, "header-value", len(value))
        elif secret_like(key) and not is_env:
            add(number, "secret-name-plain-value", len(value))
    flush()
    return [(line, kind, length) for line, (_p, kind, length) in sorted(best.items())]


def _gitignore_rule_ok(root: Path) -> bool:
    path = root / ".gitignore"
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return False
    wanted = {".env*", ".env", ".env.*", "*.env", ".env*.local"}
    return any(x.strip() in wanted for x in text.splitlines())


# ---------------------------------------------------------------------- scan


def _candidates(root: Path, unreadable: list[Path]) -> list[Path]:
    found: list[Path] = []

    def remember(error: OSError) -> None:
        if error.filename is not None:
            unreadable.append(Path(os.fsdecode(error.filename)))

    for base, dirs, names in os.walk(root, followlinks=False, onerror=remember):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        for name in sorted(names + [d for d in dirs if (Path(base) / d).is_symlink()]):
            found.append(Path(base) / name)
    return found


def _wanted(path: Path) -> bool:
    if path.is_symlink():
        return True
    return path.suffix.lower() in SCANNED_SUFFIXES or path.name.startswith(".env")


def scan(folder: Path) -> ScanReport:
    root = Path(folder).resolve()
    report = ScanReport()
    unreadable: list[Path] = []
    entries = _candidates(root, unreadable)
    rels = sorted(
        [p.relative_to(root).as_posix() for p in entries]
        + [p.relative_to(root).as_posix() for p in unreadable if root in p.parents]
    )
    index = {rel: n for n, rel in enumerate(rels, 1)}
    for path in unreadable:
        if root in path.parents:
            rel = path.relative_to(root).as_posix()
            report.incomplete.append(Incomplete(_display(rel, index), "unreadable"))
    for path in entries:
        rel = path.relative_to(root).as_posix()
        if not _wanted(path):
            if path.name != ".gitignore":
                report.other_types += 1
            continue
        shown = _display(rel, index)
        if path.is_symlink():
            report.incomplete.append(Incomplete(shown, "symlink"))
            continue
        try:
            if path.stat().st_size > MAX_BYTES:
                report.incomplete.append(Incomplete(shown, "too-large"))
                continue
            data = path.read_bytes()
        except OSError:
            report.incomplete.append(Incomplete(shown, "unreadable"))
            continue
        if b"\x00" in data:
            report.incomplete.append(Incomplete(shown, "binary"))
            continue
        try:
            text = data.decode("utf-8-sig")
        except UnicodeDecodeError:
            report.incomplete.append(Incomplete(shown, "encoding"))
            continue
        try:
            hits = _scan_text(text)
        except Exception:  # noqa: BLE001 - never let a parser message out
            report.incomplete.append(Incomplete(shown, "malformed"))
            continue
        report.scanned += 1
        report.findings += [Finding(shown, n, kind, length) for n, kind, length in hits]
    if not _gitignore_rule_ok(root):
        report.findings.append(Finding(".gitignore", 0, "missing-env-rule", 0))
    _finish(report)
    return report


def _finish(report: ScanReport) -> None:
    lines = [f"{f.path}:{f.line}  {f.kind}  {f.length}" for f in report.findings]
    lines += [f"{i.path}  scan-incomplete  {i.reason}" for i in report.incomplete]
    seen = sorted({f.kind for f in report.findings if f.kind in HINTS})
    lines += [f"hint  {k}: {HINTS[k]}" for k in seen]
    if any(f.kind == "missing-env-rule" for f in report.findings):
        lines.append("hint  missing-env-rule: add .env* to .gitignore")
    lines.append(
        f"scan summary: {len(report.findings)} finding(s), "
        f"{len(report.incomplete)} incomplete, {report.scanned} file(s) read"
    )
    if report.other_types:
        lines.append(
            f"{report.other_types} file(s) of other type(s) not read: "
            "the scan does not cover them"
        )
    if report.incomplete:
        lines.append(
            "scan incomplete: the files above were not read; the result is not clean"
        )
    if report.findings:
        lines.append(
            "removing a secret from a file does not remove it from git history: "
            "treat any secret that was ever committed as exposed and rotate it"
        )
    else:
        lines.append(
            "a clean report is not proof: unusual shapes and prose are not recognized"
        )
    if any("<path-redacted:" in x for x in lines):
        lines.append(
            "a <path-redacted:N> is the N-th path of the folder in sorted order (LC_ALL=C)"
        )
    report.lines = lines
    report.exit_code = 1 if report.findings or report.incomplete else 0


def summary(folder: Path) -> str:
    """One line for the end of the generate and sync reports."""
    try:
        report = scan(folder)
    except Exception:  # noqa: BLE001
        return "secret scan: error, run scan on the folder (result is not clean)"
    text = (
        f"secret scan: {len(report.findings)} finding(s), "
        f"{len(report.incomplete)} incomplete; a clean report is not proof"
    )
    if report.exit_code:
        text += "; run the scan command for the list"
    return text
