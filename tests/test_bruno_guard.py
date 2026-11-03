"""Task 10: the public skill, its tests and its docs hold no company or personal data."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Built by concatenation so this file does not match itself.
FORBIDDEN = re.compile(
    "|".join(
        [
            "DA-(?!1234)" + r"\d+",
            "da-" + "(?:privis|pricelist|negative|airflow|app)",
            "b" + "fi",
            "203" + "715",
            "/home/" + "patst",
            "/mnt/c/Users/(?!<WINDOWS_USERNAME>)[A-Za-z0-9._-]+",
            r"\.co\.id",
        ]
    ),
    re.IGNORECASE,
)


def _files() -> list[Path]:
    skill = ROOT / "CLAUDE" / "skills" / "bruno-collection"
    files = [
        p for p in skill.rglob("*") if p.is_file() and "__pycache__" not in p.parts
    ]
    files += [
        p
        for p in (ROOT / "tests").glob("test_bruno_*.py")
        if p.name != Path(__file__).name
    ]
    files += [p for p in (ROOT / "tests" / "support").glob("bru*") if p.is_file()]
    files += [
        ROOT
        / "docs"
        / "superpowers"
        / "specs"
        / "2026-11-02-bruno-collection-design.md",
        ROOT / "docs" / "superpowers" / "plans" / "2026-11-02-bruno-collection.md",
    ]
    return files


def test_no_company_names_hosts_or_user_paths_in_skill_tests_or_docs() -> None:
    files = _files()
    assert len(files) > 15
    found = {
        str(f.relative_to(ROOT)): FORBIDDEN.findall(f.read_text(encoding="utf-8"))
        for f in files
    }
    assert {name: hits for name, hits in found.items() if hits} == {}


def test_skill_md_carries_the_safety_rules() -> None:
    text = (ROOT / "CLAUDE" / "skills" / "bruno-collection" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    for phrase in (
        "Never use `Read`",
        "old collections are never read",
        "user-owned",
        "Add-only",
        "okf_watch.py check --max-age 14",
        "git history",
        "Reset",
        "Which rule wins",
        "trailing slash",
    ):
        assert phrase.lower() in text.lower(), phrase
