from __future__ import annotations

import json
import time
from pathlib import Path

from repomind.core.config import get_settings
from repomind.rag.chunking import chunk_file
from repomind.rag.embeddings import embedder


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
        except OSError:
            continue
    timings["chunking_seconds"] = _elapsed(start)

    start = time.perf_counter()
    texts = [_retrieval_text(chunk) for chunk in chunks]
    vectors = embedder().embed_many(texts)
    timings["embedding_seconds"] = _elapsed(start)
    start = time.perf_counter()
    collection = _collection(repo_id, reset=True)
    if chunks:
        metadatas = [
            {
                "repo_id": repo_id,
                "path": chunk["path"],
                "line_start": chunk["line_start"],
                "line_end": chunk["line_end"],
            }
            for chunk in chunks
        ]
        batch_size = max(settings.chroma_upsert_batch_size, 100)
        for start_index in range(0, len(chunks), batch_size):
            end_index = start_index + batch_size
            collection.upsert(
                ids=[chunk["id"] for chunk in chunks[start_index:end_index]],
                documents=[chunk["text"] for chunk in chunks[start_index:end_index]],
                embeddings=vectors[start_index:end_index],
                metadatas=metadatas[start_index:end_index],
            )
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
            }
            for chunk in chunks
        ],
    }
    index_path = settings.index_dir / f"{repo_id}.json"
    index_path.write_text(json.dumps(manifest, indent=2))
    timings["index_manifest_seconds"] = _elapsed(start)
    return {"chunks": len(chunks), "index_path": str(index_path), "vector_store": "chromadb", "timings": timings}


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


def _collection_name(repo_id: str) -> str:
    return f"repo_{repo_id[:48]}"


def _retrieval_text(chunk: dict) -> str:
    return f"File: {chunk['path']}\nLines: {chunk['line_start']}-{chunk['line_end']}\n{chunk['text']}"


def _elapsed(start: float) -> float:
    return round(time.perf_counter() - start, 3)
