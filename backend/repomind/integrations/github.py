from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from repomind.core.config import get_settings

UrlOpener = Callable[[urllib.request.Request, int], Any]


@dataclass(frozen=True)
class GitHubPRReference:
    owner: str
    repo: str
    number: int

    @property
    def slug(self) -> str:
        return f"{self.owner}/{self.repo}"


def parse_pr_reference(
    repository: str = "", pr_number: int | None = None, pr_url: str = ""
) -> GitHubPRReference | None:
    """Parse owner/repo + PR number or a GitHub pull request URL."""
    if pr_url:
        parsed = urllib.parse.urlparse(pr_url)
        host = parsed.netloc.lower()
        parts = [part for part in parsed.path.split("/") if part]
        if host == "github.com" and len(parts) >= 4 and parts[2] == "pull":
            try:
                return GitHubPRReference(parts[0], parts[1], int(parts[3]))
            except ValueError:
                return None
    if repository and pr_number:
        cleaned = repository.removeprefix("https://github.com/").removesuffix(".git").strip("/")
        parts = cleaned.split("/")
        if len(parts) >= 2 and re.match(r"^[A-Za-z0-9_.-]+$", parts[0] + parts[1]):
            return GitHubPRReference(parts[0], parts[1], int(pr_number))
    return None


def fetch_pull_request_intelligence(
    repository: str = "",
    pr_number: int | None = None,
    pr_url: str = "",
    opener: UrlOpener | None = None,
) -> dict[str, Any]:
    """Fetch pull request evidence from GitHub REST and GraphQL APIs.

    The function returns partial evidence with explicit errors when GitHub is unreachable or
    credentials are missing. Callers can still analyze manually supplied changed files.
    """
    reference = parse_pr_reference(repository, pr_number, pr_url)
    if reference is None:
        return {
            "available": False,
            "reason": "Provide repository owner/name with PR number or a GitHub pull request URL.",
            "changed_files": [],
            "errors": [],
        }
    settings = get_settings()
    opener = opener or _urlopen
    errors: list[str] = []
    base = settings.github_api_url.rstrip("/")

    def rest(path: str, params: dict[str, Any] | None = None) -> Any:
        url = f"{base}{path}"
        if params:
            url = f"{url}?{urllib.parse.urlencode(params)}"
        try:
            return _request_json(url, opener=opener)
        except Exception as exc:
            errors.append(f"{path}: {exc}")
            return [] if params else {}

    pull = rest(f"/repos/{reference.owner}/{reference.repo}/pulls/{reference.number}")
    files = _paginate(
        f"{base}/repos/{reference.owner}/{reference.repo}/pulls/{reference.number}/files",
        opener,
        errors,
    )
    commits = _paginate(
        f"{base}/repos/{reference.owner}/{reference.repo}/pulls/{reference.number}/commits",
        opener,
        errors,
    )
    issue_comments = _paginate(
        f"{base}/repos/{reference.owner}/{reference.repo}/issues/{reference.number}/comments",
        opener,
        errors,
    )
    review_comments = _paginate(
        f"{base}/repos/{reference.owner}/{reference.repo}/pulls/{reference.number}/comments",
        opener,
        errors,
    )
    head_sha = str((pull or {}).get("head", {}).get("sha", ""))
    branch = str((pull or {}).get("head", {}).get("ref", ""))
    checks = (
        rest(
            f"/repos/{reference.owner}/{reference.repo}/commits/{head_sha}/check-runs",
            {"per_page": 100},
        ).get("check_runs", [])
        if head_sha
        else []
    )
    workflows = rest(
        f"/repos/{reference.owner}/{reference.repo}/actions/runs",
        {"branch": branch, "per_page": 20},
    ).get("workflow_runs", [])
    graphql = _fetch_graphql(reference, opener, errors)

    changed_files = [_file_payload(item) for item in files if item.get("filename")]
    return {
        "available": bool(pull and changed_files),
        "source": "github",
        "repository": reference.slug,
        "pr_number": reference.number,
        "url": (pull or {}).get("html_url") or pr_url,
        "title": (pull or {}).get("title", ""),
        "description": (pull or {}).get("body", ""),
        "author": (pull or {}).get("user", {}).get("login", ""),
        "state": (pull or {}).get("state", ""),
        "draft": bool((pull or {}).get("draft")),
        "mergeable": (pull or {}).get("mergeable"),
        "merged": bool((pull or {}).get("merged")),
        "base_ref": (pull or {}).get("base", {}).get("ref", ""),
        "head_ref": branch,
        "head_sha": head_sha,
        "additions": int(
            (pull or {}).get("additions") or sum(item["additions"] for item in changed_files)
        ),
        "deletions": int(
            (pull or {}).get("deletions") or sum(item["deletions"] for item in changed_files)
        ),
        "changed_files_count": int((pull or {}).get("changed_files") or len(changed_files)),
        "changed_files": changed_files,
        "commits": [_commit_payload(item) for item in commits],
        "reviewers": _reviewers(pull),
        "labels": [
            {"name": item.get("name", ""), "color": item.get("color", "")}
            for item in (pull or {}).get("labels", [])
        ],
        "comments": {
            "issue": [_comment_payload(item) for item in issue_comments[:100]],
            "review": [_comment_payload(item) for item in review_comments[:100]],
        },
        "checks": [_check_payload(item) for item in checks[:100]],
        "workflows": [_workflow_payload(item) for item in workflows[:50]],
        "graphql": graphql,
        "errors": errors,
    }


def _request_json(
    url: str, opener: UrlOpener, method: str = "GET", body: bytes | None = None
) -> Any:
    settings = get_settings()
    headers = {
        "accept": "application/vnd.github+json",
        "user-agent": "RepoMindAI",
        "x-github-api-version": "2022-11-28",
    }
    if settings.github_token:
        headers["authorization"] = f"Bearer {settings.github_token}"
    if body is not None:
        headers["content-type"] = "application/json"
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    with opener(request, 12) as response:
        return json.loads(response.read().decode("utf-8"))


def _urlopen(request: urllib.request.Request, timeout: int) -> Any:
    return urllib.request.urlopen(request, timeout=timeout)


def _paginate(url: str, opener: UrlOpener, errors: list[str]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    page = 1
    while page <= 10:
        try:
            payload = _request_json(f"{url}?per_page=100&page={page}", opener=opener)
        except urllib.error.HTTPError as exc:
            errors.append(f"{url}: HTTP {exc.code}")
            break
        except Exception as exc:
            errors.append(f"{url}: {exc}")
            break
        if not isinstance(payload, list) or not payload:
            break
        items.extend(payload)
        if len(payload) < 100:
            break
        page += 1
    return items


def _fetch_graphql(
    reference: GitHubPRReference, opener: UrlOpener, errors: list[str]
) -> dict[str, Any]:
    settings = get_settings()
    if not settings.github_token:
        return {"available": False, "reason": "GitHub token not configured."}
    query = """
    query RepoMindPullRequest($owner: String!, $repo: String!, $number: Int!) {
      repository(owner: $owner, name: $repo) {
        pullRequest(number: $number) {
          reviewDecision
          mergeStateStatus
          comments { totalCount }
          reviews { totalCount }
          commits(last: 20) {
            nodes {
              commit {
                oid
                committedDate
                messageHeadline
                author { user { login } name email }
              }
            }
          }
        }
      }
    }
    """
    body = json.dumps(
        {
            "query": query,
            "variables": {
                "owner": reference.owner,
                "repo": reference.repo,
                "number": reference.number,
            },
        }
    ).encode("utf-8")
    try:
        payload = _request_json(
            settings.github_graphql_url, opener=opener, method="POST", body=body
        )
    except Exception as exc:
        errors.append(f"graphql: {exc}")
        return {"available": False, "reason": str(exc)}
    pull = (
        payload.get("data", {}).get("repository", {}).get("pullRequest")
        if isinstance(payload, dict)
        else None
    )
    if not pull:
        return {"available": False, "reason": "GraphQL pull request payload unavailable."}
    return {
        "available": True,
        "review_decision": pull.get("reviewDecision"),
        "merge_state": pull.get("mergeStateStatus"),
        "comment_count": pull.get("comments", {}).get("totalCount", 0),
        "review_count": pull.get("reviews", {}).get("totalCount", 0),
        "recent_commits": pull.get("commits", {}).get("nodes", []),
    }


def _file_payload(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "path": item.get("filename", ""),
        "status": item.get("status", ""),
        "additions": int(item.get("additions") or 0),
        "deletions": int(item.get("deletions") or 0),
        "changes": int(item.get("changes") or 0),
        "previous_filename": item.get("previous_filename"),
        "patch": item.get("patch", ""),
    }


def _commit_payload(item: dict[str, Any]) -> dict[str, Any]:
    commit = item.get("commit", {})
    author = commit.get("author", {}) or {}
    return {
        "sha": item.get("sha", ""),
        "message": commit.get("message", "").splitlines()[0],
        "author": author.get("name") or item.get("author", {}).get("login", ""),
        "date": author.get("date", ""),
        "url": item.get("html_url", ""),
    }


def _reviewers(pull: dict[str, Any] | None) -> list[dict[str, str]]:
    if not pull:
        return []
    rows = []
    for item in pull.get("requested_reviewers", []):
        rows.append({"type": "user", "login": item.get("login", "")})
    for item in pull.get("requested_teams", []):
        rows.append({"type": "team", "login": item.get("slug", "")})
    return rows


def _comment_payload(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "author": item.get("user", {}).get("login", ""),
        "body": str(item.get("body", ""))[:1000],
        "created_at": item.get("created_at", ""),
        "path": item.get("path", ""),
        "line": item.get("line") or item.get("position"),
    }


def _check_payload(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": item.get("name", ""),
        "status": item.get("status", ""),
        "conclusion": item.get("conclusion"),
        "started_at": item.get("started_at"),
        "completed_at": item.get("completed_at"),
    }


def _workflow_payload(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": item.get("name", ""),
        "status": item.get("status", ""),
        "conclusion": item.get("conclusion"),
        "event": item.get("event", ""),
        "head_branch": item.get("head_branch", ""),
        "created_at": item.get("created_at", ""),
    }
