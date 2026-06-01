from __future__ import annotations

import json
import time
from pathlib import Path

from repomind.core.config import get_settings
from repomind.rag.chunking import chunk_file
from repomind.rag.embeddings import embedder
from repomind.security.redaction import redact_text


def index_repository(repo_id: str, root: Path, files: list[dict]) -> dict:
    settings = get_settings()
    timings: dict[str, float] = {}
    start = time.perf_counter()
    chunks = []
    for item in files:
        if item["language"] in {"Text"} and item["size"] > 250_000:
            continue
        try:
            chunks.extend(chunk_file(root / item["relative_path"], item["relative_path"]))
            if len(chunks) >= settings.max_indexed_chunks:
                chunks = chunks[: settings.max_indexed_chunks]
                break
        except OSError:
            continue
    timings["chunking_seconds"] = _elapsed(start)

    start = time.perf_counter()
    collection = _collection(repo_id, reset=True)
    batch_size = max(settings.chroma_upsert_batch_size, 100)
    timings["embedding_seconds"] = 0.0
    start = time.perf_counter()
    if chunks:
        metadatas = [
            {
                "repo_id": repo_id,
                "path": chunk["path"],
                "line_start": chunk["line_start"],
                "line_end": chunk["line_end"],
                "kind": chunk.get("kind", "text"),
                "symbol": chunk.get("symbol") or "",
                "sensitive": _is_sensitive(chunk),
            }
            for chunk in chunks
        ]
        for start_index in range(0, len(chunks), batch_size):
            end_index = start_index + batch_size
            batch = chunks[start_index:end_index]
            embedding_start = time.perf_counter()
            vectors = embedder().embed_many([_retrieval_text(chunk) for chunk in batch])
            timings["embedding_seconds"] += _elapsed(embedding_start)
            collection.upsert(
                ids=[chunk["id"] for chunk in batch],
                documents=[_stored_text(chunk) for chunk in batch],
                embeddings=vectors,
                metadatas=metadatas[start_index:end_index],
            )
    timings["embedding_seconds"] = round(timings["embedding_seconds"], 3)
    timings["chroma_upsert_seconds"] = _elapsed(start)

    start = time.perf_counter()
    manifest = {
        "repo_id": repo_id,
        "embedding_model": get_settings().embedding_model,
        "vector_store": "chromadb",
        "chunks": [
            {
                "path": chunk["path"],
                "id": chunk["id"],
                "line_start": chunk["line_start"],
                "line_end": chunk["line_end"],
                "kind": chunk.get("kind", "text"),
                "symbol": chunk.get("symbol"),
                "sensitive": _is_sensitive(chunk),
            }
            for chunk in chunks
        ],
    }
    index_path = settings.index_dir / f"{repo_id}.json"
    index_path.write_text(json.dumps(manifest, indent=2))
    timings["index_manifest_seconds"] = _elapsed(start)
    return {
        "chunks": len(chunks),
        "index_path": str(index_path),
        "vector_store": "chromadb",
        "timings": timings,
    }


def _collection(repo_id: str, reset: bool = False):
    import chromadb

    settings = get_settings()
    client = chromadb.PersistentClient(path=str(settings.chroma_dir))
    name = _collection_name(repo_id)
    if reset:
        try:
            client.delete_collection(name)
        except Exception:
            pass
    return client.get_or_create_collection(name=name, metadata={"hnsw:space": "cosine"})


def delete_repository_index(repo_id: str) -> None:
    import chromadb

    settings = get_settings()
    client = chromadb.PersistentClient(path=str(settings.chroma_dir))
    try:
        client.delete_collection(_collection_name(repo_id))
    except Exception:
        pass
    (settings.index_dir / f"{repo_id}.json").unlink(missing_ok=True)


def _collection_name(repo_id: str) -> str:
    return f"repo_{repo_id[:48]}"


def _retrieval_text(chunk: dict) -> str:
    return f"File: {chunk['path']}\nLines: {chunk['line_start']}-{chunk['line_end']}\n{_stored_text(chunk)}"


def _stored_text(chunk: dict) -> str:
    if not get_settings().redact_secrets:
        return chunk["text"]
    return redact_text(chunk["text"])


def _is_sensitive(chunk: dict) -> bool:
    text = chunk["text"]
    return redact_text(text) != text


def _elapsed(start: float) -> float:
    return round(time.perf_counter() - start, 3)
