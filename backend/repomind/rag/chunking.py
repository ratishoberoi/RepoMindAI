from __future__ import annotations

import re
from pathlib import Path

from repomind.core.config import get_settings

SYMBOL_RE = re.compile(
    r"^(?P<indent>\s*)(?:async\s+def|def|class)\s+(?P<python>[A-Za-z_][A-Za-z0-9_]*)|"
    r"^(?:export\s+)?(?:async\s+)?(?:function|class)\s+(?P<js>[A-Za-z_][A-Za-z0-9_]*)",
    re.MULTILINE,
)


def chunk_text(text: str, path: str, kind: str = "text", symbol: str | None = None) -> list[dict]:
    settings = get_settings()
    chunks = []
    start = 0
    index = 0
    while start < len(text):
        end = min(len(text), start + settings.chunk_size)
        body = text[start:end]
        line_start = text.count("\n", 0, start) + 1
        line_end = text.count("\n", 0, end) + 1
        chunks.append(
            {
                "id": f"{path}:{index}",
                "path": path,
                "text": body,
                "line_start": line_start,
                "line_end": line_end,
                "kind": kind,
                "symbol": symbol,
            }
        )
        if end == len(text):
            break
        start = max(end - settings.chunk_overlap, start + 1)
        index += 1
    return chunks


def chunk_file(path: Path, relative_path: str) -> list[dict]:
    text = path.read_text(errors="ignore")
    symbol_chunks = _symbol_chunks(text, relative_path)
    return symbol_chunks or chunk_text(text, relative_path)


def _symbol_chunks(text: str, path: str) -> list[dict]:
    matches = list(SYMBOL_RE.finditer(text))
    if not matches:
        return []
    chunks = []
    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = text[start:end].strip("\n")
        if not body:
            continue
        symbol = match.group("python") or match.group("js")
        line_start = text.count("\n", 0, start) + 1
        line_end = text.count("\n", 0, end) + 1
        chunks.append(
            {
                "id": f"{path}:symbol:{index}",
                "path": path,
                "text": body,
                "line_start": line_start,
                "line_end": line_end,
                "kind": "symbol",
                "symbol": symbol,
            }
        )
    return chunks
