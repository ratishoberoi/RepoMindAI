from pathlib import Path

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from repomind.core.config import get_settings
from repomind.core.store import store
from repomind.main import app, health, import_local_repository
from repomind.schemas import LocalPathRequest

client = TestClient(app)


def test_health_endpoint() -> None:
    assert health()["status"] == "ok"


def test_local_import_uses_configured_workspace(tmp_path: Path) -> None:
    source = tmp_path / "sample_repo"
    source.mkdir()
    (source / "README.md").write_text("# Sample\n")

    response = import_local_repository(LocalPathRequest(path=str(source)))
    repo = store.get(response["id"])
    workspace = Path(repo["path"])

    assert response["source_type"] == "local"
    assert workspace.exists()
    assert workspace.is_relative_to(get_settings().repositories_dir)


def test_api_requires_key() -> None:
    response = client.get("/repositories")
    assert response.status_code == 401


def test_api_accepts_configured_key() -> None:
    response = client.get("/repositories", headers={"x-api-key": "test-api-key"})
    assert response.status_code == 200


def test_local_import_rejects_disallowed_path() -> None:
    with pytest.raises(HTTPException) as exc:
        import_local_repository(LocalPathRequest(path="/etc"))
    assert "outside configured allowed roots" in exc.value.detail
