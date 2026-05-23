from __future__ import annotations

from functools import lru_cache

from repomind.core.config import get_settings
from repomind.llm.adapters import SingleLocalModel, detect_model


@lru_cache
def local_model() -> SingleLocalModel:
    settings = get_settings()
    return SingleLocalModel(
        detect_model(settings.model_path),
        enabled=settings.enable_model_inference,
    )
