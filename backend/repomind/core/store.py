from __future__ import annotations

import json
import os
import time
from pathlib import Path
from threading import RLock
from typing import Any
from uuid import uuid4

from repomind.core.config import get_settings


class RepositoryStore:
    """JSON metadata store for repository records and analysis state."""

    def __init__(self, path: Path | None = None) -> None:
        settings = get_settings()
        self.path = path or settings.data_dir / "metadata.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()
        if not self.path.exists():
            self._write({"repositories": {}})

    def _read(self) -> dict[str, Any]:
        with self._lock:
            return json.loads(self.path.read_text() or '{"repositories": {}}')

    def _write(self, payload: dict[str, Any]) -> None:
        with self._lock:
            tmp_path = self.path.with_suffix(f"{self.path.suffix}.tmp")
            tmp_path.write_text(json.dumps(payload, indent=2))
            os.replace(tmp_path, self.path)

    def create_repository(self, name: str, source_type: str, path: Path, source: str) -> dict[str, Any]:
        payload = self._read()
        repo_id = uuid4().hex
        item = {
            "id": repo_id,
            "name": name,
            "source_type": source_type,
            "source": source,
            "path": str(path),
            "status": "ingested",
            "created_at": time.time(),
            "updated_at": time.time(),
            "summary": {},
            "reports": {},
            "error": None,
            "repository_deleted": False,
            "repository_deleted_at": None,
            "repository_retention_minutes": get_settings().retention_minutes,
        }
        payload["repositories"][repo_id] = item
        self._write(payload)
        return item

    def update(self, repo_id: str, **fields: Any) -> dict[str, Any]:
        payload = self._read()
        if repo_id not in payload["repositories"]:
            raise KeyError(repo_id)
        payload["repositories"][repo_id].update(fields)
        payload["repositories"][repo_id]["updated_at"] = time.time()
        self._write(payload)
        return payload["repositories"][repo_id]

    def get(self, repo_id: str) -> dict[str, Any]:
        payload = self._read()
        if repo_id not in payload["repositories"]:
            raise KeyError(repo_id)
        return payload["repositories"][repo_id]

    def list(self) -> list[dict[str, Any]]:
        payload = self._read()
        return sorted(payload["repositories"].values(), key=lambda item: item["created_at"], reverse=True)

    def delete(self, repo_id: str) -> dict[str, Any]:
        payload = self._read()
        if repo_id not in payload["repositories"]:
            raise KeyError(repo_id)
        item = payload["repositories"].pop(repo_id)
        self._write(payload)
        return item


store = RepositoryStore()
