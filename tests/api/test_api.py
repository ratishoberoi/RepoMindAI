import threading
import time
from pathlib import Path

import pytest
import repomind.core.jobs as jobs
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


def test_analysis_runs_as_background_job(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = tmp_path / "job_repo"
    source.mkdir()
    (source / "README.md").write_text("# Job\n")
    repo = import_local_repository(LocalPathRequest(path=str(source)))

    def fake_analyze(repository: dict, progress_callback=None, cancel_check=None) -> dict:
        if progress_callback:
            progress_callback("parsing", 25, "Parsing source files.")
        return {
            "repository": {
                "id": repository["id"],
                "name": repository["name"],
                "path": repository["path"],
                "source": repository["source"],
            },
            "statistics": {"files": 1},
            "languages": {"primary": "Markdown"},
            "stack": {},
            "scores": {},
            "architecture": {},
            "reports": {},
        }

    monkeypatch.setattr(jobs, "analyze_repository", fake_analyze)
    response = client.post(
        f"/repositories/{repo['id']}/analysis", headers={"x-api-key": "test-api-key"}
    )
    assert response.status_code == 200
    assert response.json()["job"]["status"] == "queued"
    for _ in range(20):
        status = client.get(
            f"/repositories/{repo['id']}/status", headers={"x-api-key": "test-api-key"}
        ).json()
        if status["status"] == "complete":
            break
        time.sleep(0.05)
    assert status["status"] == "complete"
    assert (
        status["analysis_job"]["stage"] == "completion"
        or status["analysis_job"]["status"] == "complete"
    )


def test_running_analysis_can_be_cancelled(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = tmp_path / "cancel_repo"
    source.mkdir()
    (source / "README.md").write_text("# Cancel\n")
    repo = import_local_repository(LocalPathRequest(path=str(source)))
    entered = threading.Event()

    def cancellable_analyze(repository: dict, progress_callback=None, cancel_check=None) -> dict:
        if progress_callback:
            progress_callback("parsing", 25, "Parsing source files.")
        entered.set()
        for _ in range(100):
            if cancel_check and cancel_check():
                raise jobs.AnalysisCancelled("Analysis cancelled.")
            time.sleep(0.01)
        raise AssertionError("analysis was not cancelled")

    monkeypatch.setattr(jobs, "analyze_repository", cancellable_analyze)
    response = client.post(
        f"/repositories/{repo['id']}/analysis", headers={"x-api-key": "test-api-key"}
    )
    assert response.status_code == 200
    assert entered.wait(timeout=2)
    cancel = client.post(
        f"/repositories/{repo['id']}/analysis/cancel", headers={"x-api-key": "test-api-key"}
    )
    assert cancel.status_code == 200
    for _ in range(50):
        status = client.get(
            f"/repositories/{repo['id']}/status", headers={"x-api-key": "test-api-key"}
        ).json()
        if status["status"] == "cancelled":
            break
        time.sleep(0.05)
    assert status["status"] == "cancelled"
    assert status["analysis_job"]["stage"] == "cancelled"
