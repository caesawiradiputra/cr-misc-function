#!/usr/bin/env python3
"""Prompt coach helper: masking, local capture, and review entries.

Everything stays on this machine under ``~/.claude/prompt-coach/``. Masking is a
best-effort safeguard: it hides known secret shapes, not secrets written in prose.
Runs on Python 3.9 and newer (stdlib only).
"""

from __future__ import annotations

import fcntl
import json
import os
import re
import secrets
import sys
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

KINDS: tuple[str, ...] = (
    "secret",
    "bearer",
    "url-credentials",
    "jwt",
    "private-key",
    "opaque",
    "access-key",
    "email",
    "ip",
    "error",
)

Rule = Callable[[str], str]


def _redacted(kind: str) -> str:
    return f"[REDACTED:{kind}]"


def _regex_rule(kind: str, pattern: str, repl: str, flags: int = 0) -> Rule:
    compiled = re.compile(pattern, flags)

    def apply(text: str) -> str:
        return compiled.sub(repl, text)

    return apply


def _email_rule(text: str) -> str:
    # The quick "@" test and the length bounds keep a long run of letters linear.
    if "@" not in text:
        return text
    return _EMAIL.sub(_redacted("email"), text)


def _ip_rule(text: str) -> str:
    def replace(match: re.Match[str]) -> str:
        if all(int(part) <= 255 for part in match.group(0).split(".")):
            return _redacted("ip")
        return match.group(0)

    return _IPV4.sub(replace, text)


def _opaque_rule(text: str) -> str:
    def replace(match: re.Match[str]) -> str:
        run = match.group(0)
        is_hex = re.fullmatch(r"[0-9a-fA-F]+", run) is not None
        is_mixed = (
            re.search(r"\d", run) is not None
            and re.search(r"[A-Z]", run) is not None
            and re.search(r"[a-z]", run) is not None
        )
        return _redacted("opaque") if is_hex or is_mixed else run

    return _OPAQUE_RUN.sub(replace, text)


_SECRET_KEYWORDS = (
    r"(?:password|passwd|pass|pwd|secret|token|api[_-]?key|apikey"
    r"|private[_-]?key|access[_-]?key)"
)
# The key may carry a prefix or suffix (clientSecret, DB_PASS, SECRET_KEY); the value is
# quoted (spaces allowed) or a bare run. Every part is length-bounded to stay linear.
_SECRET = re.compile(
    r"(?<![A-Za-z0-9_-])([A-Za-z0-9_-]{0,30}"
    + _SECRET_KEYWORDS
    + r"[A-Za-z0-9_-]{0,30})"
    r"([\"']?\s{0,3}[:=]\s{0,3})(?!\[REDACTED:)"
    r"(?:\"[^\"\n]{0,200}\"|'[^'\n]{0,200}'|[^\s\"',;}]{1,200})",
    re.IGNORECASE,
)


def _secret_rule(text: str) -> str:
    return _SECRET.sub(lambda m: f"{m.group(1)}{m.group(2)}{_redacted('secret')}", text)


_EMAIL = re.compile(r"[A-Za-z0-9._%+-]{1,64}@[A-Za-z0-9.-]{1,255}\.[A-Za-z]{2,24}")
_IPV4 = re.compile(r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])")
_OPAQUE_RUN = re.compile(r"[A-Za-z0-9+/]{32,}")

# Order matters: whole blocks and structured values first, loose shapes last.
_RULES: list[tuple[str, Rule]] = [
    (
        "private-key",
        _regex_rule(
            "private-key",
            r"-----BEGIN [A-Z ]{0,30}PRIVATE KEY-----"
            r"(?:.*?-----END [A-Z ]{0,30}PRIVATE KEY-----|.*)",
            _redacted("private-key"),
            re.DOTALL,
        ),
    ),
    (
        "url-credentials",
        _regex_rule(
            "url-credentials",
            r"(\b[A-Za-z][A-Za-z0-9+.-]{1,20}://)[^\s/:@]{1,128}:[^\s/]{1,128}@",
            r"\1" + _redacted("url-credentials") + "@",
        ),
    ),
    (
        "bearer",
        _regex_rule(
            "bearer",
            r"\bauthorization\s*:\s*\S+(?:[ \t]+\S+)?",
            _redacted("bearer"),
            re.IGNORECASE,
        ),
    ),
    (
        "bearer",
        _regex_rule(
            "bearer",
            r"\bbearer\s+[A-Za-z0-9._~+/=-]{8,}",
            _redacted("bearer"),
            re.IGNORECASE,
        ),
    ),
    (
        "jwt",
        _regex_rule(
            "jwt",
            r"eyJ[A-Za-z0-9_-]{5,300}\.[A-Za-z0-9_-]{5,1500}\.[A-Za-z0-9_-]{5,600}",
            _redacted("jwt"),
        ),
    ),
    (
        "access-key",
        _regex_rule(
            "access-key",
            r"\b(?:LTAI[A-Za-z0-9]{12,24}|AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{36}"
            r"|sk-[A-Za-z0-9_-]{20,})\b",
            _redacted("access-key"),
        ),
    ),
    ("secret", _secret_rule),
    ("email", _email_rule),
    ("ip", _ip_rule),
    ("opaque", _opaque_rule),
]


def mask(text: str) -> str:
    """Return ``text`` with known secret shapes replaced by ``[REDACTED:<kind>]``.

    Any failure returns ``[REDACTED:error]`` rather than the input, and nothing is
    printed, so a masking bug can never leak the unmasked value.

    Args:
        text: The text to mask.

    Returns:
        The masked text.
    """
    try:
        for _kind, rule in _RULES:
            text = rule(text)
    except Exception:
        return _redacted("error")
    return text


DEFAULT_HOME = "~/.claude/prompt-coach"
MAX_STORED_CHARS = 4000
MIN_WORDS = 4
_CONTINUATION = "This session is being continued"
_PASTE_OPEN = "<pasted_content"
_PASTE_CLOSE = "</pasted_content"


class CoachError(Exception):
    """A problem the helper reports in one short line, never with prompt text."""


def _base() -> Path:
    base = Path(os.environ.get("PROMPT_COACH_HOME") or DEFAULT_HOME)
    base = base.expanduser().resolve()
    for folder in (base, *base.parents):
        if (folder / ".git").exists():
            raise CoachError("data directory is inside a git worktree")
    return base


def data_dir() -> Path:
    """Return the data directory, created with mode 700.

    Raises:
        CoachError: The directory resolves inside a git worktree.
    """
    base = _base()
    base.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(base, 0o700)
    return base


def is_enabled() -> bool:
    """Return True when the ``enabled`` flag exists. Never creates anything."""
    return (_base() / "enabled").exists()


def _append(path: Path, text: str) -> None:
    """Append ``text`` to ``path`` under an exclusive lock (mode 600 on creation)."""
    fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
    with os.fdopen(fd, "ab") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        handle.write(text.encode("utf-8"))
        handle.flush()
        os.fsync(handle.fileno())


def _jsonl_lines(path: Path) -> list[str]:
    # Not str.splitlines(): json.dumps(ensure_ascii=False) leaves U+2028/U+0085 raw.
    return [line for line in path.read_text(encoding="utf-8").split("\n") if line]


def _split_pastes(prompt: str) -> tuple[str, str]:
    """Return the prompt with pasted blocks as stubs, and with the blocks removed.

    Plain ``str.find`` scans keep this linear; an unterminated block is left as text.
    """
    stored: list[str] = []
    own: list[str] = []
    pos = 0
    while True:
        start = prompt.find(_PASTE_OPEN, pos)
        if start == -1:
            break
        open_end = prompt.find(">", start)
        if open_end == -1:
            break
        close = prompt.find(_PASTE_CLOSE, open_end)
        if close == -1:
            break
        close_end = prompt.find(">", close)
        if close_end == -1:
            break
        chunk = prompt[pos:start]
        stored.append(chunk)
        own.append(chunk)
        stored.append(f"[pasted content, {close - open_end - 1} chars]")
        pos = close_end + 1
    tail = prompt[pos:]
    stored.append(tail)
    own.append(tail)
    return "".join(stored), "".join(own)


def classify(prompt: str) -> tuple[str, bool]:
    """Return ``(text_to_store, coach)`` for a prompt.

    Coaching is skipped for under four words (a bare slash command is one word), a
    continuation message, and a message that is only pasted blocks.
    """
    stored, own = _split_pastes(prompt)
    coach = len(own.split()) >= MIN_WORDS and not own.lstrip().startswith(_CONTINUATION)
    return stored, coach


def _stored_text(text: str) -> str:
    masked = mask(text)
    if len(masked) > MAX_STORED_CHARS:
        extra = len(masked) - MAX_STORED_CHARS
        masked = masked[:MAX_STORED_CHARS] + f"…[truncated {extra} chars]"
    return masked


def capture(
    payload: dict[str, Any], now: datetime | None = None
) -> tuple[str, bool] | None:
    """Log one prompt (masked) and return ``(id, coach)``.

    Returns None, writing nothing, when the coach is off or the payload has no usable
    prompt.

    Raises:
        CoachError: The data directory is inside a git worktree.
    """
    if not is_enabled():
        return None
    prompt = payload.get("prompt")
    if not isinstance(prompt, str) or not prompt.strip():
        return None
    text, coach = classify(prompt)
    cwd = payload.get("cwd")
    project = os.path.basename(cwd.rstrip("/")) if isinstance(cwd, str) else ""
    prompt_id = secrets.token_hex(4)
    record = {
        "id": prompt_id,
        "ts": (now or datetime.now().astimezone()).isoformat(timespec="seconds"),
        "session": str(payload.get("session_id", ""))[:64],
        "project": mask(project)[:80],
        "text": _stored_text(text),
        "coach": coach,
    }
    _append(data_dir() / "prompts.jsonl", json.dumps(record, ensure_ascii=False) + "\n")
    return prompt_id, coach


VERDICTS: tuple[str, ...] = ("clear", "minor", "unclear")
TAGS: tuple[str, ...] = (
    "missing-goal",
    "missing-subject",
    "ambiguous-reference",
    "run-on",
    "fragment",
    "tense",
    "article",
    "preposition",
    "word-choice",
    "spelling",
    "missing-constraint",
    "mixed-requests",
    "unclear-scope",
)
MAX_FIELD_CHARS = 600
MAX_ALTERNATIVES = 3
MAX_ENTRY_CHARS = 3000
_ID = re.compile(r"[0-9a-f]{8}")
_TEXT_FIELDS = ("context", "understanding", "rewrite", "changes")
_ALLOWED_FIELDS = {"id", "verdict", "alternatives", "tags", *_TEXT_FIELDS}


class EntryError(CoachError):
    """A review entry was rejected; nothing was written."""


def _fit(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[: limit - 3] + "..."


def _total_chars(entry: dict[str, Any]) -> int:
    return sum(len(entry[name]) for name in _TEXT_FIELDS) + sum(
        len(alt) for alt in entry["alternatives"]
    )


def _trim_to_total(entry: dict[str, Any]) -> None:
    """Shorten the longest field first until the entry fits ``MAX_ENTRY_CHARS``."""
    while (excess := _total_chars(entry) - MAX_ENTRY_CHARS) > 0:
        slots: list[tuple[int, str, int | None]] = [
            (len(entry[name]), name, None) for name in _TEXT_FIELDS
        ]
        slots += [
            (len(alt), "alternatives", index)
            for index, alt in enumerate(entry["alternatives"])
        ]
        length, name, index = max(slots, key=lambda slot: slot[0])
        if length <= 4:
            break
        shorter = _fit(
            entry[name] if index is None else entry["alternatives"][index],
            max(length - excess, 4),
        )
        if index is None:
            entry[name] = shorter
        else:
            entry["alternatives"][index] = shorter


def parse_entry(raw: str) -> dict[str, Any]:
    """Validate, mask and bound one review entry given as JSON text.

    Masking runs before truncation so a cut can never leave half a secret.

    Raises:
        EntryError: The JSON is malformed or breaks the field contract. The message
            names the rule, never the content.
    """
    try:
        data = json.loads(raw)
    except (ValueError, RecursionError):
        raise EntryError("entry is not valid JSON") from None
    if not isinstance(data, dict):
        raise EntryError("entry is not a JSON object")
    if set(data) - _ALLOWED_FIELDS:
        raise EntryError("entry has an unexpected field")
    prompt_id = data.get("id")
    if not isinstance(prompt_id, str) or not _ID.fullmatch(prompt_id):
        raise EntryError("id is not 8 hex characters")
    if data.get("verdict") not in VERDICTS:
        raise EntryError("verdict is not one of clear, minor, unclear")
    entry: dict[str, Any] = {"id": prompt_id, "verdict": data["verdict"]}
    for name in _TEXT_FIELDS:
        value = data.get(name, "")
        if not isinstance(value, str):
            raise EntryError(f"{name} must be text")
        entry[name] = _fit(mask(value), MAX_FIELD_CHARS)
    alternatives = data.get("alternatives", [])
    if not isinstance(alternatives, list) or not all(
        isinstance(alt, str) for alt in alternatives
    ):
        raise EntryError("alternatives must be a list of text")
    entry["alternatives"] = [
        _fit(mask(alt), MAX_FIELD_CHARS) for alt in alternatives[:MAX_ALTERNATIVES]
    ]
    tags = data.get("tags", [])
    if not isinstance(tags, list) or any(tag not in TAGS for tag in tags):
        raise EntryError("tags must come from the fixed list")
    entry["tags"] = list(tags)
    _trim_to_total(entry)
    return entry


def lookup_prompt(prompt_id: str) -> dict[str, Any] | None:
    """Return the logged prompt with this id from ``prompts.jsonl``, or None."""
    path = data_dir() / "prompts.jsonl"
    if not path.exists():
        return None
    for line in _jsonl_lines(path):
        try:
            record = json.loads(line)
        except ValueError:
            continue
        if isinstance(record, dict) and record.get("id") == prompt_id:
            return record
    return None


def _block(text: str) -> str:
    # Indent continuation lines so entry text can never start a new "## " header.
    return (text.replace("\r\n", "\n") or "-").replace("\n", "\n  ")


def _render(entry: dict[str, Any], record: dict[str, Any], when: datetime) -> str:
    alternatives = "none"
    if entry["alternatives"]:
        alternatives = "".join(f"\n- {_block(alt)}" for alt in entry["alternatives"])
    return (
        f"## {when:%Y-%m-%d %H:%M} - {entry['id']} - {record.get('project', '')}\n\n"
        f"**Verdict:** {entry['verdict']}\n"
        f"**You wrote:** {_block(str(record.get('text', '')))}\n"
        f"**Context:** {_block(entry['context'])}\n"
        f"**Understood as:** {_block(entry['understanding'])}\n"
        f"**Other readings:** {alternatives}\n"
        f"**Suggested:** {_block(entry['rewrite'])}\n"
        f"**What changed:** {_block(entry['changes'])}\n"
        f"**Tags:** {', '.join(entry['tags']) or '-'}\n\n"
    )


def add_entry(raw: str, now: datetime | None = None) -> str:
    """Validate one review entry (JSON text) and append it to this month's file.

    Returns:
        The prompt id.

    Raises:
        EntryError: The coach is off, the entry was rejected, or its id is not in
            ``prompts.jsonl``.
    """
    if not is_enabled():
        raise EntryError("coach is off")
    entry = parse_entry(raw)
    record = lookup_prompt(entry["id"])
    if record is None:
        raise EntryError("id is not in prompts.jsonl")
    when = now or datetime.now().astimezone()
    _append(data_dir() / f"{when:%Y-%m}.md", _render(entry, record, when))
    return str(entry["id"])


MASKING_WARNING = (
    "Local capture may still keep sensitive information that masking does not "
    "recognize. Do not use it for prompts that contain secrets or data you do not "
    "want stored. Switch it off with /prompt-coach off."
)
_SKILL_SCRIPT = "~/.claude/skills/prompt-coach/coach.py"


def set_enabled(on: bool) -> str:
    """Create or remove the ``enabled`` flag. Turning off never creates a directory."""
    if on:
        flag = data_dir() / "enabled"
        flag.write_text("on\n", encoding="utf-8")
        os.chmod(flag, 0o600)
        return "prompt-coach: on (takes effect on the next prompt)"
    flag = _base() / "enabled"
    if flag.exists():
        flag.unlink()
    return "prompt-coach: off"


def _month_file(base: Path) -> Path:
    return base / f"{datetime.now().astimezone():%Y-%m}.md"


def status() -> str:
    """Describe the coach: state, data path, this month's counts and the warning."""
    try:
        base = _base()
    except CoachError as exc:
        return f"prompt-coach: unavailable ({exc})\n{MASKING_WARNING}"
    state = "on" if (base / "enabled").exists() else "off"
    month = _month_file(base)
    text = month.read_text(encoding="utf-8") if month.exists() else ""
    verdicts = re.findall(r"(?m)^\*\*Verdict:\*\* (\w+)$", text)
    split = ", ".join(f"{name} {verdicts.count(name)}" for name in VERDICTS)
    log = base / "prompts.jsonl"
    logged = len(_jsonl_lines(log)) if log.exists() else 0
    return (
        f"prompt-coach: {state}\n"
        f"Data: {base}\n"
        f"Prompts logged: {logged}\n"
        f"Entries this month: {len(re.findall(r'(?m)^## ', text))}\n"
        f"Verdicts this month: {split}\n"
        f"{MASKING_WARNING}"
    )


def show(n: int = 3) -> str:
    """Return the last ``n`` review entries, newest first, without changing any file."""
    base = _base()
    entries: list[str] = []
    for path in sorted(base.glob("[0-9][0-9][0-9][0-9]-[0-9][0-9].md"), reverse=True):
        chunks = [
            c for c in re.split(r"(?m)^(?=## )", path.read_text("utf-8")) if c.strip()
        ]
        entries.extend(reversed(chunks))
        if len(entries) >= n:
            break
    if not entries:
        return "prompt-coach: no entries yet"
    return "\n".join(entry.rstrip() + "\n" for entry in entries[:n])


def _instruction(prompt_id: str) -> str:
    script = os.path.expanduser(_SKILL_SCRIPT)
    marker = f"COACH_JSON_END_{prompt_id}"
    template = (
        f'{{"id": "{prompt_id}", "verdict": "", "context": "", "understanding": "", '
        '"alternatives": [], "rewrite": "", "changes": "", "tags": []}'
    )
    return (
        "Prompt coach is on. Answer the user exactly as you would without it. The user "
        "is practising clear written English.\n"
        "As the LAST tool call before your final reply, run this once (verdict: clear, "
        f"minor or unclear; tags only from: {', '.join(TAGS)}; leave rewrite and "
        "changes empty when clear):\n"
        f"python3 {script} add <<'{marker}'\n{template}\n{marker}\n"
        "Then end your reply with a --- rule and the note, in English, at most 3 lines:\n"
        "Prompt coach: clear, no change.  (clear prompt: this one line only)\n"
        'Prompt coach: I read this as "...". then Better: "..."  (minor wording issue)\n'
        "plus Why: Alternative reading: ... Say which you meant.  (only when the choice "
        "would change what you do)\n"
        'Keep the user\'s meaning; mark a guess "(guess)". Non-English prompt: give '
        "the reading and rewrite in English. Never criticise the task itself."
    )


def hook_output(stdin_text: str) -> str:
    """Return the ``UserPromptSubmit`` hook JSON for a coached prompt, else ``""``."""
    try:
        data = json.loads(stdin_text)
    except (ValueError, RecursionError):
        return ""
    if not isinstance(data, dict):
        return ""
    try:
        result = capture(data)
    except CoachError:
        return ""
    if result is None or not result[1]:
        return ""
    return json.dumps(
        {
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": _instruction(result[0]),
            }
        }
    )


def _read_stdin() -> str:
    return sys.stdin.buffer.read().decode("utf-8", errors="replace")


def main(argv: list[str]) -> int:
    """Run one subcommand. ``hook`` and ``add`` always return 0 (fail soft)."""
    command = argv[0] if argv else ""
    soft = command in ("hook", "add")
    try:
        if command == "hook":
            output = hook_output(_read_stdin())
            if output:
                print(output)
        elif command == "add":
            print(f"prompt-coach: saved {add_entry(_read_stdin())}")
        elif command in ("on", "off"):
            print(set_enabled(command == "on"))
        elif command == "status":
            print(status())
        elif command == "show":
            print(show(int(argv[1]) if len(argv) > 1 else 3))
        else:
            print("usage: coach.py hook|add|on|off|status|show [n]", file=sys.stderr)
            return 2
    except Exception as exc:
        detail = f": {exc}" if isinstance(exc, CoachError) else ""
        # The hook's stdout is read as context by the model, so its errors go to stderr.
        stream = sys.stderr if command == "hook" else sys.stdout
        print(f"prompt-coach: {type(exc).__name__} in {command}{detail}", file=stream)
        return 0 if soft else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
