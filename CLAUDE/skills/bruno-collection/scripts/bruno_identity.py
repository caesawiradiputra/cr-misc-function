"""Endpoint identity, request and file names, collisions and the add-only plan.

The plan is pure: it takes discovered endpoints and the state of an existing
collection and says what may be added. It never overwrites, deletes or renames;
anything unclear (a collision, a changed endpoint, a disappeared one) is listed for
the user to decide. Names are compared case-folded, because the collection lives on
a Windows disk. Python 3.9 and newer, stdlib only.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from bruno_discover import Endpoint
from bruno_params import Source

NOISE = re.compile(r"^(api|v\d+)$", re.IGNORECASE)
INVALID = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
PARAM = re.compile(r"^\{([^}:]+)(?::[^}]*)?\}$")


@dataclass
class DocEntry:
    """What `docs/requests/` recorded about one endpoint."""

    identity: str
    function: str
    signature: list[str]
    files: list[str]


@dataclass
class ExistingState:
    files: set[str]
    docs: dict[str, DocEntry]


@dataclass
class Planned:
    endpoint: Endpoint
    identity: str
    folder: str
    fixed_name: str
    random_name: str
    files: tuple[str, str]


@dataclass
class Collision:
    reason: str
    identities: list[str]
    sources: list[Source]
    files: list[str] = field(default_factory=list)


@dataclass
class Changed:
    identity: str
    before: list[str]
    now: list[str]


@dataclass
class Plan:
    add: list[Planned] = field(default_factory=list)
    collisions: list[Collision] = field(default_factory=list)
    conflicts: list[Collision] = field(default_factory=list)
    changed: list[Changed] = field(default_factory=list)
    unchanged: list[str] = field(default_factory=list)
    disappeared: list[str] = field(default_factory=list)
    possible_renames: list[tuple[str, str]] = field(default_factory=list)


def normalize_path(path: str) -> str:
    cleaned = re.sub(r"\{([^}:]+):[^}]*\}", r"{\1}", path)
    cleaned = re.sub(r"/{2,}", "/", cleaned)
    if not cleaned.startswith("/"):
        cleaned = "/" + cleaned
    return cleaned.rstrip("/") or "/"


def identity(ep: Endpoint) -> str:
    """Method plus the full resolved path; parameter names kept, converters dropped."""
    return f"{ep.method.upper()} {normalize_path(ep.path)}"


def signature(ep: Endpoint) -> list[str]:
    items = sorted(f"{p.name}:{p.location}" for p in ep.params)
    if ep.body is not None:
        items.append(f"body:{ep.body.name}")
    return items


def safe_name(text: str, limit: int = 80) -> str:
    cleaned = re.sub(r"\s+", " ", INVALID.sub(" ", text)).strip(" .")
    return cleaned[:limit].strip(" .") or "unnamed"


def _segments(path: str) -> list[str]:
    return [s for s in normalize_path(path).split("/") if s and not NOISE.match(s)]


def _words(text: str) -> list[str]:
    return [w for w in re.split(r"[\s\-_.]+", INVALID.sub(" ", text.lower())) if w]


def _resource(path: str) -> str:
    tokens: list[str] = []
    previous = ""
    for segment in _segments(path):
        match = PARAM.match(segment)
        if match:
            words = _words(match.group(1))
            if len(words) > 1 and words[0] == previous.removesuffix("s"):
                words = words[1:]
            tokens.extend(["by", *words])
        else:
            words = _words(segment)
            tokens.extend(words)
            previous = words[-1] if words else previous
    return " ".join(tokens) or "root"


def request_names(ep: Endpoint) -> tuple[str, str]:
    """`<Verb> <resource> (fixed)` and `(random)`; the file name equals the name."""
    base = safe_name(f"{ep.method.capitalize()} {_resource(ep.path)}")
    return f"{base} (fixed)", f"{base} (random)"


def folder_for(ep: Endpoint) -> str:
    if ep.tags:
        return safe_name(ep.tags[0])
    for segment in _segments(ep.path):
        if not PARAM.match(segment):
            return safe_name(segment.lower())
    return "root"


def _planned(ep: Endpoint) -> Planned:
    folder = folder_for(ep)
    fixed, random_ = request_names(ep)
    return Planned(
        ep,
        identity(ep),
        folder,
        fixed,
        random_,
        (f"{folder}/{fixed}.yml", f"{folder}/{random_}.yml"),
    )


def plan(endpoints: list[Endpoint], existing: ExistingState) -> Plan:
    result = Plan()
    groups: dict[str, list[Endpoint]] = {}
    for ep in endpoints:
        groups.setdefault(identity(ep), []).append(ep)

    candidates: list[Planned] = []
    for ident, eps in groups.items():
        if len(eps) > 1:
            result.conflicts.append(
                Collision(
                    "the same method and path is declared more than once; "
                    "needs a naming decision",
                    [ident],
                    [e.source for e in eps],
                )
            )
        elif ident in existing.docs:
            before, now = existing.docs[ident].signature, signature(eps[0])
            if before != now:
                result.changed.append(Changed(ident, before, now))
            else:
                result.unchanged.append(ident)
        else:
            candidates.append(_planned(eps[0]))

    by_file: dict[str, list[Planned]] = {}
    for cand in candidates:
        for path in cand.files:
            by_file.setdefault(path.casefold(), []).append(cand)
    clashed = {id(c) for group in by_file.values() if len(group) > 1 for c in group}
    seen: set[frozenset[int]] = set()
    for group in by_file.values():
        key = frozenset(id(c) for c in group)
        if len(group) > 1 and key not in seen:
            seen.add(key)
            result.collisions.append(
                Collision(
                    "two endpoints map to the same file name; needs a naming decision",
                    [c.identity for c in group],
                    [c.endpoint.source for c in group],
                    sorted({p for c in group for p in c.files}),
                )
            )

    present = {path.casefold(): path for path in existing.files}
    for cand in candidates:
        if id(cand) in clashed:
            continue
        hits = [present[p.casefold()] for p in cand.files if p.casefold() in present]
        if hits:
            result.collisions.append(
                Collision(
                    "a file with this name already exists and is not overwritten; "
                    "needs a naming decision",
                    [cand.identity],
                    [cand.endpoint.source],
                    hits,
                )
            )
        else:
            result.add.append(cand)

    result.disappeared = [i for i in existing.docs if i not in groups]
    for old in result.disappeared:
        doc = existing.docs[old]
        for cand in result.add:
            if (
                cand.endpoint.function == doc.function
                and signature(cand.endpoint) == doc.signature
            ):
                result.possible_renames.append((old, cand.identity))
    return result
