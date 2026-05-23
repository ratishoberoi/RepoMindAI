from __future__ import annotations

from pathlib import Path

from repomind.core.config import get_settings


def chunk_text(text: str, path: str) -> list[dict]:
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
            }
        )
        if end == len(text):
            break
        start = max(end - settings.chunk_overlap, start + 1)
        index += 1
    return chunks


def chunk_file(path: Path, relative_path: str) -> list[dict]:
    return chunk_text(path.read_text(errors="ignore"), relative_path)

