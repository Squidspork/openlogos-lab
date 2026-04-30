from __future__ import annotations

import os
import re

SECRET_PATTERNS = (
    re.compile(r"sk-lm-[A-Za-z0-9:_-]+"),
    re.compile(r"(?i)(api[_-]?key|token|authorization)(\s*[:=]\s*)([^\s,;]+)"),
)


def redact(value: object) -> str:
    text = str(value)
    for pattern in SECRET_PATTERNS:
        if pattern.groups >= 3:
            text = pattern.sub(lambda match: f"{match.group(1)}{match.group(2)}[REDACTED]", text)
        else:
            text = pattern.sub("[REDACTED]", text)
    api_key = os.getenv("LM_STUDIO_API_KEY")
    if api_key:
        text = text.replace(api_key, "[REDACTED]")
    return text
