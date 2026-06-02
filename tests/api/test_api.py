import threading
import time
from pathlib import Path
from typing import Any

import pytest
import repomind.core.auth as auth_module
import repomind.core.jobs as jobs
from fastapi import HTTPException
from fastapi.testclient import TestClient
from repomind.core import alerts as alerts_module
from repomind.core.auth import (
    complete_github_oauth,
    complete_google_oauth,
    decrypt_secret,
    encrypt_secret,
    issue_oauth_state,
)
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


def test_user_can_signup_login_and_use_session() -> None:
    signup = client.post(
        "/auth/signup",
        json={
            "email": "founder@example.com",
            "name": "Founder",
            "password": "correct horse battery staple",
            "organization_name": "Founder Workspace",
        },
    )
    assert signup.status_code == 200
    token = signup.json()["access_token"]
    assert token

    listed = client.get("/repositories", headers={"authorization": f"Bearer {token}"})
    assert listed.status_code == 200

    login = client.post(
        "/auth/login",
        json={"email": "founder@example.com", "password": "correct horse battery staple"},
    )
    assert login.status_code == 200
    assert login.json()["organization"]["id"] == signup.json()["organization"]["id"]


def test_session_tenant_cannot_be_overridden_with_headers(tmp_path: Path) -> None:
    signup = client.post(
        "/auth/signup",
        json={
            "email": "tenant-lock@example.com",
            "name": "Tenant Lock",
            "password": "tenant lock password",
        },
    ).json()
    token = signup["access_token"]
    source = tmp_path / "tenant_session"
    source.mkdir()
    (source / "README.md").write_text("# Tenant session\n")

    imported = client.post(
        "/repositories/local",
        json={"path": str(source)},
        headers={
            "authorization": f"Bearer {token}",
            "x-org-id": "attacker-controlled-org",
            "x-user-id": "attacker",
        },
    )
    assert imported.status_code == 200
    repo = store.get(imported.json()["id"])
    assert repo["org_id"] == signup["organization"]["id"]
    assert repo["org_id"] != "attacker-controlled-org"


def test_user_can_delete_account_and_repository_data(tmp_path: Path) -> None:
    signup = client.post(
        "/auth/signup",
        json={
            "email": "delete-me@example.com",
            "name": "Delete Me",
            "password": "delete account password",
        },
    ).json()
    token = signup["access_token"]
    source = tmp_path / "delete_repo"
    source.mkdir()
    (source / "README.md").write_text("# Delete\n")
    imported = client.post(
        "/repositories/local",
        json={"path": str(source)},
        headers={"authorization": f"Bearer {token}"},
    ).json()
    repo_path = Path(store.get(imported["id"])["path"])
    assert repo_path.exists()

    deleted = client.delete("/account", headers={"authorization": f"Bearer {token}"})
    assert deleted.status_code == 200
    assert deleted.json()["deleted"]["repositories"] == 1
    assert not repo_path.exists()
    with pytest.raises(KeyError):
        store.get(imported["id"])
    with pytest.raises(KeyError):
        store.get_user(signup["user"]["id"])


def test_secret_encryption_round_trips_without_plaintext() -> None:
    encrypted = encrypt_secret("gho_secret_token")
    assert "gho_secret_token" not in encrypted
    assert decrypt_secret(encrypted) == "gho_secret_token"


@pytest.mark.asyncio
async def test_github_oauth_callback_creates_session_and_encrypted_external_account(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "github_oauth_client_id", "github-client")
    monkeypatch.setattr(settings, "github_oauth_client_secret", "github-secret")
    state = issue_oauth_state("github", "http://localhost/github/callback")
    monkeypatch.setattr(auth_module.httpx, "AsyncClient", _fake_oauth_client("github-token"))

    result = await complete_github_oauth("code", state)

    assert result["access_token"]
    account = store.get_external_account(
        result["organization"]["id"], result["user"]["id"], "github"
    )
    assert "github-token" not in account["access_token_encrypted"]
    assert decrypt_secret(account["access_token_encrypted"]) == "github-token"


@pytest.mark.asyncio
async def test_google_oauth_callback_creates_session_and_encrypted_external_account(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "google_oauth_client_id", "google-client")
    monkeypatch.setattr(settings, "google_oauth_client_secret", "google-secret")
    state = issue_oauth_state("google", "http://localhost/google/callback")
    monkeypatch.setattr(auth_module.httpx, "AsyncClient", _fake_oauth_client("google-token"))

    result = await complete_google_oauth("code", state)

    assert result["access_token"]
    account = store.get_external_account(
        result["organization"]["id"], result["user"]["id"], "google"
    )
    assert "google-token" not in account["access_token_encrypted"]
    assert decrypt_secret(account["access_token_encrypted"]) == "google-token"


def test_github_app_installation_requires_valid_state(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "github_app_slug", "repomind-ai")
    signup = client.post(
        "/auth/signup",
        json={
            "email": "github-app@example.com",
            "name": "GitHub App",
            "password": "github app password",
        },
    ).json()
    token = signup["access_token"]
    install = client.get(
        "/github/app/install-url",
        headers={"authorization": f"Bearer {token}"},
    )
    assert install.status_code == 200
    state = install.json()["state"]
    invalid = client.post(
        "/github/app/callback",
        json={
            "installation_id": "123",
            "setup_action": "install",
            "state": "wrong-state-that-is-long-enough",
        },
        headers={"authorization": f"Bearer {token}"},
    )
    assert invalid.status_code == 400
    valid = client.post(
        "/github/app/callback",
        json={"installation_id": "123", "setup_action": "install", "state": state},
        headers={"authorization": f"Bearer {token}"},
    )
    assert valid.status_code == 200
    assert valid.json()["connected"] is True


def _fake_oauth_client(access_token: str):
    class FakeResponse:
        def __init__(self, payload: Any, status_code: int = 200) -> None:
            self._payload = payload
            self.status_code = status_code

        def json(self) -> Any:
            return self._payload

        def raise_for_status(self) -> None:
            if self.status_code >= 400:
                raise RuntimeError("HTTP error")

    class FakeClient:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        async def __aenter__(self) -> "FakeClient":
            return self

        async def __aexit__(self, *args: Any) -> None:
            return None

        async def post(self, url: str, **kwargs: Any) -> FakeResponse:
            if "github.com" in url:
                return FakeResponse({"access_token": access_token, "scope": "repo,user"})
            return FakeResponse({"access_token": access_token, "refresh_token": "refresh-token"})

        async def get(self, url: str, **kwargs: Any) -> FakeResponse:
            if url.endswith("/user"):
                return FakeResponse({"id": 4242, "login": "repomind-user", "name": "RepoMind User"})
            if url.endswith("/user/emails"):
                return FakeResponse(
                    [{"email": "repomind-github@example.com", "primary": True, "verified": True}]
                )
            return FakeResponse(
                {
                    "sub": "google-subject",
                    "email": "repomind-google@example.com",
                    "name": "RepoMind Google",
                }
            )

    return FakeClient


def test_rate_limiting_is_enforced(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "rate_limit_requests", 2)
    monkeypatch.setattr(settings, "rate_limit_window_seconds", 60)
    path = "/config"
    statuses = [
        client.get(path, headers={"x-api-key": "test-api-key"}).status_code for _ in range(3)
    ]
    assert statuses[-1] == 429
    monkeypatch.setattr(settings, "rate_limit_requests", 120)


def test_metrics_endpoint_exports_prometheus_text() -> None:
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "repomind_" in response.text


def test_alert_webhook_delivery_reports_actual_status(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "alert_webhook_url", "https://alerts.example.test")

    class FakeResponse:
        status_code = 200
        is_success = True

    calls = []

    def fake_post(url: str, json: dict, timeout: int) -> FakeResponse:
        calls.append({"url": url, "json": json, "timeout": timeout})
        return FakeResponse()

    monkeypatch.setattr(alerts_module.httpx, "post", fake_post)

    result = alerts_module.send_alert("test_event", {"repo_id": "repo"})

    assert calls[0]["url"] == "https://alerts.example.test"
    assert result["deliveries"][0]["ok"] is True
    monkeypatch.setattr(settings, "alert_webhook_url", None)


def test_admin_system_reports_operational_snapshot() -> None:
    response = client.get("/admin/system", headers={"x-api-key": "test-api-key"})
    assert response.status_code == 200
    payload = response.json()
    assert "requests" in payload
    assert "repositories" in payload
    assert "tenancy" in payload
    assert "queue" in payload
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


def test_rq_backend_enqueues_durable_job_without_running_inline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "rq_repo"
    source.mkdir()
    (source / "README.md").write_text("# RQ\n")
    repo = import_local_repository(LocalPathRequest(path=str(source)))
    settings = get_settings()
    monkeypatch.setattr(settings, "analysis_queue_backend", "rq")
    monkeypatch.setattr(settings, "redis_url", "redis://localhost:6379/0")

    class FakeQueue:
        def __init__(self) -> None:
            self.enqueued = []

        def enqueue(self, func, *args, **kwargs):
            self.enqueued.append({"func": func, "args": args, "kwargs": kwargs})

        def __len__(self) -> int:
            return len(self.enqueued)

    fake_queue = FakeQueue()
    monkeypatch.setattr(jobs, "_redis_queue", lambda: fake_queue)
    monkeypatch.setattr(jobs, "_rq_retry", lambda: None)

    job = jobs.start_analysis_job(repo["id"])

    assert job["status"] == "queued"
    assert fake_queue.enqueued[0]["args"] == (repo["id"], job["id"])
    assert store.get(repo["id"])["status"] == "queued"
    monkeypatch.setattr(settings, "analysis_queue_backend", "local")
    monkeypatch.setattr(settings, "redis_url", None)


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
