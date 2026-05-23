from __future__ import annotations

import gc
import importlib.util
import json
import os
import re
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ModelSpec:
    path: Path
    backend: str
    loadable: bool
    reason: str
    model_type: str | None = None
    architecture: str | None = None
    tensor_count: int | None = None
    weight_bytes: int | None = None


def detect_model(path: Path) -> ModelSpec:
    if not path.exists():
        return ModelSpec(path, "missing", False, "Model path does not exist.")
    config_path = path / "config.json"
    tokenizer = (path / "tokenizer.json").exists() or (path / "tokenizer.model").exists()
    weights = list(path.glob("*.safetensors")) or list(path.glob("*.bin"))
    if not (config_path.exists() and tokenizer and weights):
        return ModelSpec(path, "unsupported", False, "No supported local HF checkpoint layout.")

    config = json.loads(config_path.read_text())
    index_path = path / "model.safetensors.index.json"
    tensor_count = None
    weight_bytes = None
    if index_path.exists():
        index = json.loads(index_path.read_text())
        tensor_count = len(index.get("weight_map", {}))
        weight_bytes = index.get("metadata", {}).get("total_size")
    deps = all(importlib.util.find_spec(name) for name in ("torch", "transformers", "gptqmodel"))
    return ModelSpec(
        path=path,
        backend="transformers",
        loadable=deps,
        reason="HF checkpoint detected and required runtime packages are installed."
        if deps
        else "HF checkpoint detected, but torch/transformers/gptqmodel runtime packages are missing.",
        model_type=config.get("model_type"),
        architecture=(config.get("architectures") or [None])[0],
        tensor_count=tensor_count,
        weight_bytes=weight_bytes,
    )


class SingleLocalModel:
    """Lazy single-model production inference path."""

    def __init__(self, spec: ModelSpec, enabled: bool = True) -> None:
        self.spec = spec
        self.enabled = enabled
        self._lock = threading.RLock()
        self._model: Any = None
        self._tokenizer: Any = None
        self._load_seconds: float | None = None

    def status(self) -> dict[str, Any]:
        return {
            "path": str(self.spec.path),
            "backend": self.spec.backend,
            "loadable": self.spec.loadable,
            "loaded": self._model is not None,
            "enabled": self.enabled,
            "reason": self.spec.reason,
            "model_type": self.spec.model_type,
            "architecture": self.spec.architecture,
            "tensor_count": self.spec.tensor_count,
            "weight_bytes": self.spec.weight_bytes,
            "load_seconds": self._load_seconds,
        }

    def generate(self, prompt: str, max_tokens: int = 320) -> str:
        if not self.enabled:
            raise RuntimeError("Local model inference is disabled by configuration.")
        self._ensure_loaded()
        return self._generate_once(prompt, max_tokens)

    def _generate_once(self, prompt: str, max_tokens: int) -> str:
        assert self._model is not None
        assert self._tokenizer is not None

        import torch

        messages = [
            {
                "role": "system",
                "content": (
                    "You are RepoMind AI. Use only the supplied repository evidence. "
                    "Do not mention missing external access. Do not reveal hidden reasoning. "
                    "Answer with concrete file references when available."
                ),
            },
            {
                "role": "user",
                "content": f"{prompt}\n\nReturn final answer only. Start with 'Final answer:'.",
            },
        ]
        if hasattr(self._tokenizer, "apply_chat_template"):
            text = self._tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
            )
        else:
            text = prompt
        inputs = self._tokenizer(text, return_tensors="pt").to(self._model.device)
        with torch.inference_mode():
            output = self._model.generate(
                **inputs,
                max_new_tokens=max_tokens,
                do_sample=False,
                pad_token_id=self._tokenizer.eos_token_id,
            )
        generated = output[0][inputs["input_ids"].shape[-1] :]
        text = self._tokenizer.decode(generated, skip_special_tokens=True).strip()
        marker = "Final answer:"
        if marker.lower() in text.lower():
            index = text.lower().rfind(marker.lower())
            text = text[index + len(marker) :].strip()
        return _strip_reasoning_preamble(text)

    def _unload(self) -> None:
        with self._lock:
            self._model = None
            self._tokenizer = None
            try:
                import torch

                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except Exception:
                pass
            gc.collect()

    def _ensure_loaded(self) -> None:
        with self._lock:
            if self._model is not None:
                return
            if not self.spec.loadable:
                raise RuntimeError(self.spec.reason)

            venv_bin = Path(sys.prefix) / "bin"
            os.environ["PATH"] = f"{venv_bin}:{os.environ.get('PATH', '')}"
            os.environ.setdefault(
                "PYTORCH_ALLOC_CONF",
                "expandable_segments:True,max_split_size_mb:256,garbage_collection_threshold:0.7",
            )

            from transformers import AutoModelForCausalLM, AutoTokenizer

            start = time.perf_counter()
            self._tokenizer = AutoTokenizer.from_pretrained(
                self.spec.path,
                local_files_only=True,
                trust_remote_code=True,
            )
            import torch

            device_map: str | dict[str, int] = {"": 0} if torch.cuda.is_available() else "cpu"
            self._model = AutoModelForCausalLM.from_pretrained(
                self.spec.path,
                local_files_only=True,
                trust_remote_code=True,
                device_map=device_map,
                dtype="auto",
                low_cpu_mem_usage=True,
            )
            self._model.eval()
            self._load_seconds = round(time.perf_counter() - start, 2)


def _strip_reasoning_preamble(text: str) -> str:
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text.strip()) if part.strip()]
    while paragraphs and _is_meta_reasoning(paragraphs[0]):
        paragraphs.pop(0)
    cleaned = "\n\n".join(paragraphs).strip() or text.strip()
    cleaned = re.sub(r"^(Okay|Alright),?\s+", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\b(I need to|Let me|I should|I will)\b[^.\n]*\.\s*", "", cleaned, flags=re.IGNORECASE)
    return cleaned.strip()


def _is_meta_reasoning(paragraph: str) -> bool:
    lower = paragraph.lower()
    return any(
        phrase in lower
        for phrase in (
            "i need to",
            "let me start",
            "provided repository analysis",
            "based on the provided",
            "i should highlight",
            "looking at the",
        )
    )
