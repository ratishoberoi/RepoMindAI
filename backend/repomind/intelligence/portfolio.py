from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any


def build_multi_repository_intelligence(repositories: list[dict[str, Any]]) -> dict[str, Any]:
    analyzed = [repo for repo in repositories if repo.get("summary")]
    summaries = [repo["summary"] for repo in analyzed]
    language_counts = Counter()
    framework_counts = Counter()
    dependency_counts = Counter()
    domain_index: dict[str, list[dict[str, str]]] = defaultdict(list)
    service_index: dict[str, list[dict[str, str]]] = defaultdict(list)
    vulnerability_index: dict[str, list[dict[str, str]]] = defaultdict(list)
    risks = []
    for repo in analyzed:
        summary = repo["summary"]
        language = summary.get("languages", {}).get("primary")
        if language:
            language_counts[language] += 1
        framework_counts.update(summary.get("stack", {}).get("frameworks", []))
        dependency_counts.update(_dependencies(summary))
        for domain in summary.get("knowledge_graph", {}).get("domains", []):
            domain_index[domain.get("name", "")].append(
                {"repo_id": repo["id"], "repo": repo["name"], "role": domain.get("role", "")}
            )
        for service in _services(summary):
            service_index[service].append({"repo_id": repo["id"], "repo": repo["name"]})
        for finding in summary.get("security", {}).get("findings", []):
            key = finding.get("rule_id") or finding.get("message")
            if key:
                vulnerability_index[str(key)].append(
                    {
                        "repo_id": repo["id"],
                        "repo": repo["name"],
                        "path": finding.get("path", ""),
                        "severity": finding.get("severity", "medium"),
                    }
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
        "dependency_overlap_graph": _dependency_overlap_graph(analyzed, dependency_counts),
        "shared_dependencies": [
            {"name": name, "repository_count": count, "ecosystem": "dependency"}
            for name, count in dependency_counts.most_common(30)
            if count > 1
        ],
        "shared_vulnerabilities": _shared_vulnerabilities(vulnerability_index),
        "risk_propagation": _risk_propagation(vulnerability_index),
        "duplicate_services": _duplicate_services(service_index),
        "framework_concentration_risk": _framework_concentration(framework_counts, len(analyzed)),
        "ownership_concentration_risk": _ownership_concentration(summaries),
        "shared_domains": shared_domains[:20],
        "top_risks": sorted(risks, key=lambda item: item["risk_score"], reverse=True)[:20],
        "portfolio_score": _portfolio_score(summaries),
        "portfolio_remediation_center": _remediation_center(risks, vulnerability_index),
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


def _dependencies(summary: dict[str, Any]) -> list[str]:
    deps = []
    deps.extend(summary.get("stack", {}).get("frameworks", []))
    deps.extend(summary.get("stack", {}).get("package_managers", []))
    for item in summary.get("files", []):
        path = item.get("relative_path", "").lower()
        if path.endswith(
            (
                "requirements.txt",
                "pyproject.toml",
                "package.json",
                "pnpm-lock.yaml",
                "package-lock.json",
            )
        ):
            deps.append(path.rsplit("/", 1)[-1])
    return [str(item) for item in deps if item]


def _services(summary: dict[str, Any]) -> list[str]:
    services = []
    for domain in summary.get("knowledge_graph", {}).get("domains", []):
        role = str(domain.get("role", ""))
        name = str(domain.get("name", ""))
        if role in {"API boundary", "Data layer", "Trust boundary", "Product capability"}:
            services.append(name.rsplit("/", 1)[-1].lower())
    return services


def _dependency_overlap_graph(
    repositories: list[dict[str, Any]], dependency_counts: Counter[str]
) -> dict[str, Any]:
    nodes = []
    edges = []
    for repo in repositories:
        nodes.append({"id": repo["id"], "label": repo["name"], "kind": "repository"})
        for dependency in _dependencies(repo["summary"]):
            if dependency_counts[dependency] <= 1:
                continue
            dep_id = f"dependency:{dependency}"
            nodes.append({"id": dep_id, "label": dependency, "kind": "dependency"})
            edges.append({"source": repo["id"], "target": dep_id, "relation": "uses"})
    unique_nodes = {node["id"]: node for node in nodes}
    return {"nodes": list(unique_nodes.values()), "edges": edges[:160]}


def _shared_vulnerabilities(index: dict[str, list[dict[str, str]]]) -> list[dict[str, Any]]:
    return [
        {
            "rule": rule,
            "affected_repositories": repos,
            "repository_count": len({item["repo_id"] for item in repos}),
        }
        for rule, repos in sorted(index.items(), key=lambda item: len(item[1]), reverse=True)
        if len({item["repo_id"] for item in repos}) > 1
    ][:20]


def _risk_propagation(index: dict[str, list[dict[str, str]]]) -> list[dict[str, Any]]:
    rows = []
    for rule, repos in index.items():
        affected = sorted({item["repo"] for item in repos})
        if not affected:
            continue
        severity = max(
            (item.get("severity", "medium") for item in repos),
            key=lambda value: {"critical": 4, "high": 3, "medium": 2, "low": 1}.get(value, 0),
        )
        rows.append(
            {
                "risk": rule,
                "severity": severity,
                "affected_repositories": affected,
                "blast_radius": len(affected),
            }
        )
    return sorted(rows, key=lambda item: item["blast_radius"], reverse=True)[:20]


def _duplicate_services(index: dict[str, list[dict[str, str]]]) -> list[dict[str, Any]]:
    return [
        {"service": service, "repositories": repos, "repository_count": len(repos)}
        for service, repos in sorted(index.items(), key=lambda item: len(item[1]), reverse=True)
        if len(repos) > 1 and service not in {"src", "app", "backend", "frontend"}
    ][:20]


def _framework_concentration(
    framework_counts: Counter[str], repo_count: int
) -> list[dict[str, Any]]:
    if not repo_count:
        return []
    return [
        {
            "framework": framework,
            "repository_count": count,
            "portfolio_share": round(count / repo_count * 100, 1),
            "severity": "high"
            if count / repo_count >= 0.8
            else "medium"
            if count / repo_count >= 0.5
            else "low",
        }
        for framework, count in framework_counts.most_common()
    ]


def _ownership_concentration(summaries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for summary in summaries:
        files = max(summary.get("statistics", {}).get("files", 1), 1)
        for domain in summary.get("knowledge_graph", {}).get("domains", [])[:6]:
            share = domain.get("file_count", 0) / files
            if share >= 0.25:
                rows.append(
                    {
                        "repository": summary.get("repository", {}).get("name"),
                        "domain": domain.get("name"),
                        "file_count": domain.get("file_count"),
                        "portfolio_share": round(share * 100, 1),
                        "risk": "critical ownership concentration"
                        if share >= 0.5
                        else "ownership concentration",
                    }
                )
    return rows[:20]


def _remediation_center(
    risks: list[dict[str, Any]], vulnerability_index: dict[str, list[dict[str, str]]]
) -> list[dict[str, Any]]:
    actions = []
    for rule, repos in vulnerability_index.items():
        affected = sorted({item["repo"] for item in repos})
        if affected:
            actions.append(
                {
                    "action": f"Remediate {rule}",
                    "helps_repositories": affected,
                    "impact": len(affected),
                    "evidence": [item["path"] for item in repos[:6]],
                }
            )
    if not actions and risks:
        actions.append(
            {
                "action": "Resolve highest scoring repository risks",
                "helps_repositories": sorted({item["repo"] for item in risks if item.get("repo")}),
                "impact": len({item["repo"] for item in risks if item.get("repo")}),
                "evidence": [item.get("path") for item in risks[:6] if item.get("path")],
            }
        )
    return sorted(actions, key=lambda item: item["impact"], reverse=True)[:12]
