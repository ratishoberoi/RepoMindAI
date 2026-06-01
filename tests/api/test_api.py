import threading
import time
from pathlib import Path

import pytest
import repomind.core.jobs as jobs
from fastapi import HTTPException
from fastapi.testclient import TestClient
from repomind.core.config import get_settings
from repomind.core.store import RepositoryStore, store
from repomind.main import app, health, import_local_repository
from repomind.schemas import LocalPathRequest
from sqlalchemy import create_engine, text

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
    assert response.headers["x-content-type-options"] == "nosniff"


def test_admin_system_reports_operational_snapshot() -> None:
    response = client.get("/admin/system", headers={"x-api-key": "test-api-key"})
    assert response.status_code == 200
    payload = response.json()
    assert "requests" in payload
    assert "repositories" in payload
    assert "tenancy" in payload
    assert payload["tenancy"]["organizations"] >= 1


def test_repository_listing_is_org_scoped(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    (first / "README.md").write_text("# First\n")
    (second / "README.md").write_text("# Second\n")

    response_a = client.post(
        "/repositories/local",
        json={"path": str(first)},
        headers={"x-api-key": "test-api-key", "x-org-id": "org-a", "x-user-id": "user-a"},
    )
    response_b = client.post(
        "/repositories/local",
        json={"path": str(second)},
        headers={"x-api-key": "test-api-key", "x-org-id": "org-b", "x-user-id": "user-b"},
    )

    assert response_a.status_code == 200
    assert response_b.status_code == 200
    org_a = client.get(
        "/repositories", headers={"x-api-key": "test-api-key", "x-org-id": "org-a"}
    ).json()
    org_b = client.get(
        "/repositories", headers={"x-api-key": "test-api-key", "x-org-id": "org-b"}
    ).json()

    assert response_a.json()["id"] in {repo["id"] for repo in org_a}
    assert response_b.json()["id"] not in {repo["id"] for repo in org_a}
    assert response_b.json()["id"] in {repo["id"] for repo in org_b}
    denied = client.get(
        f"/repositories/{response_b.json()['id']}/status",
        headers={"x-api-key": "test-api-key", "x-org-id": "org-a"},
    )
    assert denied.status_code == 404


def test_local_import_rejects_disallowed_path() -> None:
    with pytest.raises(HTTPException) as exc:
        import_local_repository(LocalPathRequest(path="/etc"))
    assert "outside configured allowed roots" in exc.value.detail


def test_store_upgrades_legacy_repository_schema(tmp_path: Path) -> None:
    db_path = tmp_path / "legacy.db"
    engine = create_engine(f"sqlite:///{db_path}", future=True)
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE repositories ("
                "id VARCHAR(64) PRIMARY KEY, "
                "name VARCHAR(512) NOT NULL, "
                "source_type VARCHAR(64) NOT NULL, "
                "source TEXT NOT NULL, "
                "path TEXT NOT NULL, "
                "status VARCHAR(64) NOT NULL, "
                "created_at FLOAT NOT NULL, "
                "updated_at FLOAT NOT NULL, "
                "summary JSON NOT NULL, "
                "reports JSON NOT NULL, "
                "analysis_job JSON, "
                "error TEXT, "
                "repository_deleted BOOLEAN NOT NULL, "
                "repository_deleted_at FLOAT, "
                "repository_retention_minutes INTEGER NOT NULL"
                ")"
            )
        )
        connection.execute(
            text(
                "INSERT INTO repositories VALUES ("
                "'legacy','Legacy','local','/tmp/legacy','/tmp/legacy','ingested',1,1,"
                "'{}','{}',NULL,NULL,0,NULL,60)"
            )
        )

    upgraded = RepositoryStore(
        database_url=f"sqlite:///{db_path}", legacy_path=tmp_path / "none.json"
    )
    repo = upgraded.get("legacy")

    assert repo["org_id"] == "default"
    assert repo["created_by_user_id"] == "local-admin"


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
