from __future__ import annotations

import json
from urllib.request import Request

from repomind.integrations.github import fetch_pull_request_intelligence, parse_pr_reference


class FakeResponse:
    def __init__(self, payload: object) -> None:
        self.payload = payload

    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


def test_parse_pr_reference_accepts_url_and_repo_number() -> None:
    assert parse_pr_reference(pr_url="https://github.com/acme/app/pull/7").slug == "acme/app"
    assert parse_pr_reference(repository="acme/app", pr_number=8).number == 8


def test_fetch_pull_request_intelligence_uses_rest_evidence(monkeypatch) -> None:
    monkeypatch.delenv("REPOMIND_GITHUB_TOKEN", raising=False)

    def opener(request: Request, timeout: int) -> FakeResponse:
        url = request.full_url
        if "/pulls/5/files" in url:
            return FakeResponse(
                [
                    {
                        "filename": "backend/api/auth.py",
                        "status": "modified",
                        "additions": 4,
                        "deletions": 1,
                        "changes": 5,
                    }
                ]
            )
        if "/pulls/5/commits" in url:
            return FakeResponse(
                [
                    {
                        "sha": "abc",
                        "html_url": "https://github.com/acme/app/commit/abc",
                        "commit": {
                            "message": "auth change",
                            "author": {"name": "Dev", "date": "2026-01-01T00:00:00Z"},
                        },
                    }
                ]
            )
        if "/issues/5/comments" in url or "/pulls/5/comments" in url:
            return FakeResponse([])
        if "/commits/head/check-runs" in url:
            return FakeResponse(
                {"check_runs": [{"name": "tests", "status": "completed", "conclusion": "success"}]}
            )
        if "/actions/runs" in url:
            return FakeResponse(
                {"workflow_runs": [{"name": "ci", "status": "completed", "conclusion": "success"}]}
            )
        if "/pulls/5" in url:
            return FakeResponse(
                {
                    "html_url": "https://github.com/acme/app/pull/5",
                    "title": "Auth fix",
                    "body": "Harden login",
                    "state": "open",
                    "draft": False,
                    "mergeable": True,
                    "merged": False,
                    "additions": 4,
                    "deletions": 1,
                    "changed_files": 1,
                    "user": {"login": "dev"},
                    "base": {"ref": "main"},
                    "head": {"ref": "feature/auth", "sha": "head"},
                    "requested_reviewers": [{"login": "sec"}],
                    "requested_teams": [],
                    "labels": [{"name": "security", "color": "red"}],
                }
            )
        raise AssertionError(url)

    result = fetch_pull_request_intelligence(repository="acme/app", pr_number=5, opener=opener)

    assert result["available"] is True
    assert result["changed_files"][0]["path"] == "backend/api/auth.py"
    assert result["commits"][0]["sha"] == "abc"
    assert result["checks"][0]["name"] == "tests"
    assert result["workflows"][0]["name"] == "ci"
