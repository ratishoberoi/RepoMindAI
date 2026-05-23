from fastapi.testclient import TestClient
from repomind.main import app, health

client = TestClient(app)


def test_health_endpoint() -> None:
    assert health()["status"] == "ok"


def test_local_import_analysis_reports_and_chat() -> None:
    response = client.post(
        "/repositories/local",
        json={"path": "/home/ratish/RepoMindAI/sample_repos/python_fastapi_example"},
    )
    assert response.status_code == 200
    repo_id = response.json()["id"]

    response = client.post(f"/repositories/{repo_id}/analysis")
    assert response.status_code == 200
    assert response.json()["summary"]["statistics"]["files"] >= 4

    response = client.get(f"/repositories/{repo_id}/reports")
    assert response.status_code == 200
    assert "README.md" in response.json()

    response = client.post(f"/repositories/{repo_id}/chat", json={"question": "What does this project do?"})
    assert response.status_code == 200
    assert response.json()["citations"]
