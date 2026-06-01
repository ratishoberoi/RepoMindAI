from __future__ import annotations

import math
import re

SECRET_ASSIGNMENT_RE = re.compile(
    r"(?i)\b(api[_-]?key|secret|token|password|private[_-]?key|client[_-]?secret)\b"
    r"(\s*[:=]\s*)"
    r"(['\"]?)[A-Za-z0-9_./+=:@-]{8,}(['\"]?)"
)
BEARER_RE = re.compile(r"(?i)\b(bearer|token)\s+[A-Za-z0-9._~+/=-]{16,}")
HIGH_ENTROPY_RE = re.compile(r"\b[A-Za-z0-9_+/=-]{32,}\b")


def redact_text(text: str) -> str:
    text = SECRET_ASSIGNMENT_RE.sub(r"\1\2\3[REDACTED]\4", text)
    text = BEARER_RE.sub(r"\1 [REDACTED]", text)
    return HIGH_ENTROPY_RE.sub(_redact_high_entropy, text)


def redact_mapping(value):
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, list):
        return [redact_mapping(item) for item in value]
    if isinstance(value, dict):
        return {key: redact_mapping(item) for key, item in value.items()}
    return value


def _redact_high_entropy(match: re.Match[str]) -> str:
    value = match.group(0)
    if _entropy(value) < 4.0:
        return value
    return "[REDACTED]"


def _entropy(value: str) -> float:
    if not value:
        return 0.0
    counts = {char: value.count(char) for char in set(value)}
    return -sum((count / len(value)) * math.log2(count / len(value)) for count in counts.values())
