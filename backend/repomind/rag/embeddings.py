from __future__ import annotations

from collections.abc import Iterable
from functools import lru_cache

from repomind.core.config import get_settings


class BGEEmbedder:
    """Real local semantic embeddings using BAAI/bge-small-en-v1.5."""

    def __init__(self, model_name: str | None = None) -> None:
        settings = get_settings()
        self.model_name = model_name or settings.embedding_model
        try:
            from sentence_transformers import SentenceTransformer
        except Exception as exc:
            raise RuntimeError(
                "sentence-transformers is required for repository embeddings. "
                "Install the llm extra; hash embeddings are intentionally not available."
            ) from exc
        try:
            self._model = SentenceTransformer(self.model_name)
        except Exception as exc:
            raise RuntimeError(f"Failed to load embedding model {self.model_name}: {exc}") from exc

    def embed(self, text: str) -> list[float]:
        return self.embed_many([text])[0]

    def embed_many(self, texts: Iterable[str]) -> list[list[float]]:
        values = list(texts)
        if not values:
            return []
        embeddings = self._model.encode(
            values,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
            batch_size=get_settings().embedding_batch_size,
        )
        return embeddings.astype(float).tolist()


@lru_cache
def embedder() -> BGEEmbedder:
    return BGEEmbedder()
