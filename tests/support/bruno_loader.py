"""Import helper for the bruno-collection skill's scripts (not a package)."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from types import ModuleType

SCRIPTS = (
    Path(__file__).resolve().parents[2]
    / "CLAUDE"
    / "skills"
    / "bruno-collection"
    / "scripts"
)


def load(name: str) -> ModuleType:
    """Import one of the skill's modules with `scripts/` on `sys.path`."""
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    return importlib.import_module(name)
