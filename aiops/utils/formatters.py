from __future__ import annotations

import re


_SECRET_PATTERNS = [
    re.compile(r"(api[-_]?key\s*=\s*)([A-Za-z0-9-_]{8,})", re.IGNORECASE),
    re.compile(r"(token\s*=\s*)([A-Za-z0-9-_]{8,})", re.IGNORECASE),
]


def redact_secrets(text: str) -> str:
    redacted = text
    for pattern in _SECRET_PATTERNS:
        redacted = pattern.sub(r"\1***", redacted)
    return redacted
