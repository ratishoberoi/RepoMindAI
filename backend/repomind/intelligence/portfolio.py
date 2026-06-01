from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any


def build_multi_repository_intelligence(repositories: list[dict[str, Any]]) -> dict[str, Any]:
    analyzed = [repo for repo in repositories if repo.get("summary")]
    summaries = [repo["summary"] for repo in analyzed]
    language_counts = Counter()
    framework_counts = Counter()
    domain_index: dict[str, list[dict[str, str]]] = defaultdict(list)
    risks = []
    for repo in analyzed:
        summary = repo["summary"]
        language = summary.get("languages", {}).get("primary")
        if language:
            language_counts[language] += 1
        framework_counts.update(summary.get("stack", {}).get("frameworks", []))
        for domain in summary.get("knowledge_graph", {}).get("domains", []):
            domain_index[domain.get("name", "")].append(
                {"repo_id": repo["id"], "repo": repo["name"], "role": domain.get("role", "")}
            )
        risks.extend(_repo_risks(repo, summary))
    shared_domains = [
        {"domain": name, "repositories": repos}
        for name, repos in sorted(domain_index.items(), key=lambda item: len(item[1]), reverse=True)
        if name and len(repos) > 1
    ]
    return {
        "repository_count": len(analyzed),
        "repositories": [_repo_card(repo, repo["summary"]) for repo in analyzed],
        "languages": language_counts.most_common(),
        "frameworks": framework_counts.most_common(),
        "shared_domains": shared_domains[:20],
        "top_risks": sorted(risks, key=lambda item: item["risk_score"], reverse=True)[:20],
        "portfolio_score": _portfolio_score(summaries),
        "recommendations": _recommendations(summaries, shared_domains, risks),
    }


def _repo_card(repo: dict[str, Any], summary: dict[str, Any]) -> dict[str, Any]:
    scores = summary.get("scores", {})
    return {
        "id": repo["id"],
        "name": repo["name"],
        "primary_language": summary.get("languages", {}).get("primary"),
        "frameworks": summary.get("stack", {}).get("frameworks", []),
        "domains": len(summary.get("knowledge_graph", {}).get("domains", [])),
        "hotspots": len(summary.get("knowledge_graph", {}).get("hotspots", [])),
        "security": scores.get("security"),
        "production_readiness": scores.get("production_readiness"),
        "cto": scores.get("cto"),
    }


def _repo_risks(repo: dict[str, Any], summary: dict[str, Any]) -> list[dict[str, Any]]:
    risks = []
    for finding in summary.get("security", {}).get("findings", [])[:5]:
        severity = finding.get("severity", "medium")
        risks.append(
            {
                "repo_id": repo["id"],
                "repo": repo["name"],
                "path": finding.get("path"),
                "risk": finding.get("message"),
                "risk_score": {"critical": 40, "high": 30, "medium": 18, "low": 8}.get(
                    severity, 12
                ),
            }
        )
    for hotspot in summary.get("knowledge_graph", {}).get("hotspots", [])[:3]:
        risks.append(
            {
                "repo_id": repo["id"],
                "repo": repo["name"],
                "path": hotspot.get("path"),
                "risk": hotspot.get("reason", "knowledge graph hotspot"),
                "risk_score": hotspot.get("risk_score", 0),
            }
        )
    return risks


def _portfolio_score(summaries: list[dict[str, Any]]) -> float:
    if not summaries:
        return 0.0
    scores = [
        summary.get("scores", {}).get("cto", 0)
        for summary in summaries
        if isinstance(summary.get("scores", {}).get("cto"), (int, float))
    ]
    return round(sum(scores) / len(scores), 1) if scores else 0.0


def _recommendations(
    summaries: list[dict[str, Any]],
    shared_domains: list[dict[str, Any]],
    risks: list[dict[str, Any]],
) -> list[str]:
    items = []
    if shared_domains:
        items.append(
            "Standardize ownership and interfaces for domains repeated across repositories."
        )
    if any(risk["risk_score"] >= 30 for risk in risks):
        items.append(
            "Prioritize critical/high risks across the portfolio before expanding AI automation."
        )
    if len(summaries) > 1:
        items.append(
            "Use architecture drift comparison on repositories that represent product generations."
        )
    if not summaries:
        items.append("Analyze at least one repository to build portfolio intelligence.")
    return items or ["Portfolio risk is currently low based on analyzed repositories."]
