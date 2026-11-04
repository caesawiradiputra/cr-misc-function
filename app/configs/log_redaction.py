"""Keep secrets out of log output.

Pure helpers (compatible with Python 3.9 and newer), no logging setup here: see
``init_logging`` in ``app/configs/log_config.py``, which installs them as a loguru patcher.
Two layers:

1. Exact values: every environment variable whose name looks like a secret
   (``PASSWORD``, ``SECRET``, ``ACCESS_KEY``, ``TOKEN`` ...) is masked wherever its
   value appears, so a dumped config or an exception message cannot leak it.
2. Patterns: ``user:password@host`` in URLs and ``password=...`` / ``'token': '...'``
   pairs are masked even when the value is not in the environment.
"""

from __future__ import annotations

import os
import re
from collections.abc import Mapping

MASK = "***"

# Values shorter than this are not masked: they would blank out ordinary words.
MIN_SECRET_LENGTH = 4

SECRET_NAME = re.compile(
    r"PASSWORD|PASSWD|SECRET|ACCESS_KEY|TOKEN|API_KEY|PRIVATE_KEY", re.IGNORECASE
)

PATTERNS = [
    # scheme://user:password@host
    (re.compile(r"(://[^/\s:@]+:)[^@\s/]+(@)"), r"\1" + MASK + r"\2"),
    # password=..., 'password': '...', "secret": "...", access_key = ..., token: ...
    (
        re.compile(
            r"""(?i)((?:password|passwd|secret|access[_-]?key(?:[_-]?(?:id|secret))?|token)['"]?\s*[:=]\s*['"]?)([^'"\s,;&})]+)"""
        ),
        r"\1" + MASK,
    ),
]


def collect_secret_values(environ: Mapping[str, str] | None = None) -> list[str]:
    """Collect the values of secret-looking environment variables.

    Args:
        environ: Environment to read; defaults to ``os.environ``.

    Returns:
        Distinct secret values, longest first, so a long value is masked before
        any shorter value that is a substring of it.
    """
    source = os.environ if environ is None else environ
    values = {
        value
        for name, value in source.items()
        if SECRET_NAME.search(name) and len(value) >= MIN_SECRET_LENGTH
    }
    return sorted(values, key=len, reverse=True)


def redact(text: str, secrets: list[str] | None = None) -> str:
    """Mask secrets in a log text.

    Args:
        text: The text about to be written to the log.
        secrets: Exact values to mask; defaults to the current environment's.

    Returns:
        The text with every secret value and secret-looking pair replaced by ``***``.
    """
    for value in collect_secret_values() if secrets is None else secrets:
        text = text.replace(value, MASK)

    for pattern, replacement in PATTERNS:
        text = pattern.sub(replacement, text)

    return text
