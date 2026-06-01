from __future__ import annotations

import re
from typing import Any

FILE_REF_RE = re.compile(
    r"`?([A-Za-z0-9_./-]+\.(?:py|ts|tsx|js|jsx|json|ya?ml|toml|md|go|rs|java|kt|cs|rb|php|sql))(?:[:#][0-9]+(?:-[0-9]+)?)?`?"
)

ASSERTIVE_TERMS = (
    "implements",
    "uses",
    "calls",
    "depends",
    "stores",
    "exposes",
    "authenticates",
    "encrypts",
    "vulnerable",
    "risk",
    "critical",
)


def validate_answer_support(answer: str, citations: list[dict[str, Any]]) -> dict[str, Any]:
    """Return a machine-readable support check for generated repository answers."""
    cited_paths = {
        str(citation.get("file") or citation.get("path"))
        for citation in citations
        if citation.get("file") or citation.get("path")
    }
    referenced_paths = set(FILE_REF_RE.findall(answer or ""))
    missing = sorted(path for path in referenced_paths if path not in cited_paths)
    unsupported_sentences = _unsupported_sentences(answer, cited_paths)
    confidence = 0.95
    if not cited_paths:
        confidence = 0.15
    confidence -= min(0.5, len(missing) * 0.12)
    confidence -= min(0.35, len(unsupported_sentences) * 0.07)
    return {
        "supported": not missing and (bool(cited_paths) or not _has_assertive_claim(answer)),
        "confidence": round(max(0.0, min(1.0, confidence)), 2),
        "citation_count": len(cited_paths),
        "referenced_files": sorted(referenced_paths),
        "missing_citations": missing,
        "unsupported_claims": unsupported_sentences[:8],
    }


def _unsupported_sentences(answer: str, cited_paths: set[str]) -> list[str]:
    if not answer:
        return []
    sentences = re.split(r"(?<=[.!?])\s+", answer.strip())
    unsupported: list[str] = []
    for sentence in sentences:
        clean = sentence.strip()
        if not clean or clean.startswith("- `"):
            continue
        refs = set(FILE_REF_RE.findall(clean))
        if refs:
            continue
        if cited_paths and _has_assertive_claim(clean):
            unsupported.append(clean[:260])
    return unsupported


def _has_assertive_claim(text: str) -> bool:
    lower = text.lower()
    return any(term in lower for term in ASSERTIVE_TERMS)
