from __future__ import annotations

import re
import urllib.request
from pathlib import PurePosixPath
from typing import Any

from repomind.integrations.github import fetch_pull_request_intelligence


def analyze_pr_risk(
    summary: dict[str, Any],
    changed_files: list[str],
    title: str = "",
    description: str = "",
    pr_url: str = "",
    repository: str = "",
    pr_number: int | None = None,
) -> dict[str, Any]:
    normalized = [_normalize(path) for path in changed_files if path.strip()]
    inferred_from_url = False
    diff_metadata: dict[str, Any] = {"available": False, "files": []}
    github_pr: dict[str, Any] = {"available": False}
    if pr_url or (repository and pr_number):
        github_pr = fetch_pull_request_intelligence(repository, pr_number, pr_url)
        github_files = _files_from_github_pr(github_pr)
        if github_files:
            normalized = [item["path"] for item in github_files]
            diff_metadata = {
                "available": True,
                "source": "github_api",
                "files": github_files,
                "total_additions": github_pr.get("additions", 0),
                "total_deletions": github_pr.get("deletions", 0),
                "commits": len(github_pr.get("commits", [])),
                "checks": github_pr.get("checks", []),
                "workflows": github_pr.get("workflows", []),
            }
            inferred_from_url = True
            title = title or str(github_pr.get("title", ""))
            description = description or str(github_pr.get("description", ""))
    if pr_url and not normalized:
        diff_metadata = _diff_from_pr_url(pr_url)
        normalized = [item["path"] for item in diff_metadata.get("files", [])]
        inferred_from_url = bool(normalized)
    files = {item["relative_path"]: item for item in summary.get("files", [])}
    kg = summary.get("knowledge_graph", {})
    hotspots = {item["path"]: item for item in kg.get("hotspots", [])}
    security_paths = {
        item.get("path")
        for item in summary.get("security", {}).get("findings", [])
        if item.get("severity") in {"critical", "high", "medium"}
    }
    impacted_domains = _impacted_domains(kg.get("domains", []), normalized)
    impacts = []
    score = 15
    for path in normalized:
        file_info = files.get(path, {})
        reasons = []
        file_score = 0
        layer = _layer(path)
        if path in hotspots:
            file_score += min(30, int(hotspots[path].get("risk_score", 0)))
            reasons.append("knowledge graph hotspot")
        if path in security_paths:
            file_score += 25
            reasons.append("existing security finding")
        if layer in {"interface", "data", "security"}:
            file_score += 16
            reasons.append(f"{layer} layer change")
        if file_info.get("language") in {"Dockerfile", "YAML", "JSON"} or path.endswith(
            ("pyproject.toml", "package.json", "docker-compose.yml")
        ):
            file_score += 12
            reasons.append("configuration or dependency surface")
        if "test" in path.lower() or "spec" in path.lower():
            file_score -= 10
            reasons.append("test-only mitigation")
        impacts.append(
            {
                "path": path,
                "layer": layer,
                "risk": max(0, file_score),
                "reasons": reasons or ["low graph centrality"],
            }
        )
        score += max(0, file_score)
    score += len(impacted_domains) * 8
    score = min(100, max(0, score))
    findings = _findings_from_impacts(impacts, impacted_domains)
    review_plan = _required_review(score, impacted_domains, impacts)
    tests = _test_strategy(impacted_domains, impacts)
    deployment_risk = _deployment_risk(score, impacts, impacted_domains)
    affected_services = _affected_services(summary, normalized, impacted_domains)
    reviewers = _recommended_reviewers(impacts, affected_services)
    test_impact = _test_impact(summary, normalized, impacted_domains)
    dependency_changes = _dependency_changes(normalized, diff_metadata)
    api_changes = _api_changes(summary, normalized)
    security_sensitive = _security_sensitive_changes(normalized, impacts)
    review_complexity = _review_complexity(score, normalized, diff_metadata, github_pr)
    regression_probability = _regression_probability(
        score, test_impact, dependency_changes, api_changes
    )
    ownership_routing = _ownership_routing(affected_services, reviewers, github_pr)
    impact_timeline = _impact_timeline(github_pr, normalized, affected_services)
    return {
        "title": title,
        "description": description,
        "pr_url": pr_url,
        "repository": repository or github_pr.get("repository", ""),
        "pr_number": pr_number or github_pr.get("pr_number"),
        "changed_files_source": "github_api"
        if github_pr.get("available")
        else "pr_url"
        if inferred_from_url
        else "manual",
        "changed_files": normalized,
        "risk_score": score,
        "risk_level": _risk_level(score),
        "blast_radius": {
            "file_count": len(normalized),
            "domain_count": len(impacted_domains),
            "affected_domains": [domain.get("name") for domain in impacted_domains],
            "highest_risk_files": [
                item["path"]
                for item in sorted(impacts, key=lambda row: row["risk"], reverse=True)[:8]
            ],
        },
        "diff_metadata": diff_metadata,
        "github_pr": github_pr,
        "affected_services": affected_services,
        "recommended_reviewers": reviewers,
        "required_reviewers": reviewers,
        "ownership_routing": ownership_routing,
        "test_impact_analysis": test_impact,
        "review_complexity": review_complexity,
        "regression_probability": regression_probability,
        "dependency_changes": dependency_changes,
        "api_changes": api_changes,
        "security_sensitive_changes": security_sensitive,
        "pr_impact_timeline": impact_timeline,
        "impact_prediction": _impact_prediction(score, affected_services, impacts),
        "impacted_domains": impacted_domains,
        "file_impacts": sorted(impacts, key=lambda item: item["risk"], reverse=True),
        "findings": findings,
        "required_review": review_plan,
        "review_plan": review_plan,
        "test_strategy": tests,
        "recommended_tests": tests,
        "deployment_risk": deployment_risk,
        "release_gate_recommendation": _release_gate(score, deployment_risk),
        "pr_review_packet": _review_packet(
            score,
            impacted_domains,
            impacts,
            review_plan,
            tests,
            deployment_risk,
            affected_services,
            reviewers,
            test_impact,
            review_complexity,
            regression_probability,
            impact_timeline,
        ),
        "summary": _summary(score, impacted_domains, impacts),
    }


def _files_from_pr_url(pr_url: str) -> list[str]:
    return [item["path"] for item in _diff_from_pr_url(pr_url).get("files", [])]


def _files_from_github_pr(github_pr: dict[str, Any]) -> list[dict[str, Any]]:
    if not github_pr.get("available"):
        return []
    rows = []
    for item in github_pr.get("changed_files", []):
        path = _normalize(str(item.get("path", "")))
        if path:
            rows.append(
                {
                    "path": path,
                    "status": item.get("status", ""),
                    "additions": int(item.get("additions") or 0),
                    "deletions": int(item.get("deletions") or 0),
                    "changes": int(item.get("changes") or 0),
                }
            )
    return rows


def _diff_from_pr_url(pr_url: str) -> dict[str, Any]:
    match = re.match(r"^https://github\.com/([^/]+)/([^/]+)/pull/(\d+)(?:[/?#].*)?$", pr_url)
    if not match:
        return {"available": False, "reason": "Unsupported PR URL.", "files": []}
    owner, repo, number = match.groups()
    url = f"https://github.com/{owner}/{repo}/pull/{number}.diff"
    try:
        with urllib.request.urlopen(url, timeout=8) as response:
            diff = response.read(1_000_000).decode("utf-8", errors="ignore")
    except Exception:
        return {"available": False, "reason": "Unable to fetch PR diff.", "files": []}
    files: dict[str, dict[str, Any]] = {}
    current = ""
    for line in diff.splitlines():
        if line.startswith("+++ b/"):
            current = _normalize(line.removeprefix("+++ b/").strip())
            if current and current != "/dev/null":
                files.setdefault(
                    current, {"path": current, "additions": 0, "deletions": 0, "hunks": 0}
                )
        elif current and line.startswith("@@"):
            files[current]["hunks"] += 1
        elif current and line.startswith("+") and not line.startswith("+++"):
            files[current]["additions"] += 1
        elif current and line.startswith("-") and not line.startswith("---"):
            files[current]["deletions"] += 1
    return {
        "available": True,
        "source": url,
        "files": list(files.values())[:200],
        "total_additions": sum(item["additions"] for item in files.values()),
        "total_deletions": sum(item["deletions"] for item in files.values()),
    }


def _impacted_domains(
    domains: list[dict[str, Any]], changed_files: list[str]
) -> list[dict[str, Any]]:
    impacted = []
    for domain in domains:
        samples = set(domain.get("sample_files", []))
        name = domain.get("name", "")
        if any(
            path in samples or path.startswith(f"{name}/") or name in path for path in changed_files
        ):
            impacted.append(
                {
                    "name": name,
                    "role": domain.get("role"),
                    "routes": domain.get("routes", 0),
                    "data_models": domain.get("data_models", 0),
                    "security_findings": domain.get("security_findings", 0),
                }
            )
    return impacted[:12]


def _layer(path: str) -> str:
    lower = path.lower()
    if any(token in lower for token in ("auth", "security", "session", "jwt")):
        return "security"
    if any(token in lower for token in ("route", "api", "controller", "main.py")):
        return "interface"
    if any(token in lower for token in ("db", "model", "schema", "migration", "store")):
        return "data"
    if any(token in lower for token in ("test", "spec")):
        return "test"
    if any(token in lower for token in ("component", "page", "frontend")):
        return "presentation"
    return "application"


def _risk_level(score: int) -> str:
    if score >= 75:
        return "critical"
    if score >= 55:
        return "high"
    if score >= 35:
        return "medium"
    return "low"


def _required_review(
    score: int, domains: list[dict[str, Any]], impacts: list[dict[str, Any]]
) -> list[str]:
    reviews = ["code owner review"]
    layers = {item["layer"] for item in impacts}
    if score >= 55:
        reviews.append("staff engineer architecture review")
    if "security" in layers or any(domain.get("security_findings") for domain in domains):
        reviews.append("security review")
    if "data" in layers or any(domain.get("data_models") for domain in domains):
        reviews.append("migration/data integrity review")
    if "interface" in layers or any(domain.get("routes") for domain in domains):
        reviews.append("API compatibility review")
    return reviews


def _test_strategy(domains: list[dict[str, Any]], impacts: list[dict[str, Any]]) -> list[str]:
    strategy = ["run existing unit and integration tests for changed modules"]
    layers = {item["layer"] for item in impacts}
    if "interface" in layers:
        strategy.append("add route/API contract tests for changed endpoints")
    if "data" in layers:
        strategy.append("run migration rollback and data model compatibility tests")
    if "security" in layers:
        strategy.append("run authentication/authorization regression tests")
    if len(domains) > 2:
        strategy.append("run cross-domain smoke tests because blast radius spans multiple domains")
    return strategy


def _summary(score: int, domains: list[dict[str, Any]], impacts: list[dict[str, Any]]) -> str:
    top = impacts[0]["path"] if impacts else "no files"
    domain_text = ", ".join(domain["name"] for domain in domains[:4]) or "no mapped domains"
    return f"PR risk is {_risk_level(score)} ({score}/100). Highest-impact file: {top}. Impacted domains: {domain_text}."


def _normalize(path: str) -> str:
    return PurePosixPath(path.strip().replace("\\", "/")).as_posix()


def _findings_from_impacts(
    impacts: list[dict[str, Any]], domains: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    findings = []
    for item in sorted(impacts, key=lambda row: row["risk"], reverse=True)[:12]:
        if item["risk"] <= 0:
            continue
        findings.append(
            {
                "title": f"{item['layer'].title()} change risk",
                "severity": _risk_level(min(100, item["risk"] + len(domains) * 8)),
                "file": item["path"],
                "message": ", ".join(item.get("reasons", [])),
                "recommendation": _file_recommendation(item),
            }
        )
    return findings


def _file_recommendation(item: dict[str, Any]) -> str:
    layer = item.get("layer")
    if layer == "security":
        return "Require security owner review and authentication/authorization regression tests."
    if layer == "data":
        return "Require migration, rollback, and data compatibility tests."
    if layer == "interface":
        return "Require API contract tests and backwards compatibility review."
    return "Require owner review and targeted regression tests."


def _deployment_risk(
    score: int, impacts: list[dict[str, Any]], domains: list[dict[str, Any]]
) -> dict[str, Any]:
    layers = {item["layer"] for item in impacts}
    risk = score
    if {"security", "data"} & layers:
        risk += 12
    if len(domains) >= 3:
        risk += 10
    risk = min(100, risk)
    return {
        "score": risk,
        "level": _risk_level(risk),
        "reasons": [f"{layer} layer touched" for layer in sorted(layers)]
        + ([f"{len(domains)} domains affected"] if domains else []),
    }


def _review_packet(
    score: int,
    domains: list[dict[str, Any]],
    impacts: list[dict[str, Any]],
    review_plan: list[str],
    tests: list[str],
    deployment_risk: dict[str, Any],
    affected_services: list[dict[str, Any]],
    reviewers: list[str],
    test_impact: dict[str, Any],
    review_complexity: dict[str, Any],
    regression_probability: dict[str, Any],
    impact_timeline: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "summary": _summary(score, domains, impacts),
        "blast_radius": {
            "domains": [domain.get("name") for domain in domains],
            "files": [item.get("path") for item in impacts],
        },
        "review_plan": review_plan,
        "recommended_reviewers": reviewers,
        "recommended_tests": tests,
        "test_impact_analysis": test_impact,
        "review_complexity": review_complexity,
        "regression_probability": regression_probability,
        "impact_timeline": impact_timeline,
        "affected_services": affected_services,
        "deployment_risk": deployment_risk,
        "release_gate": _release_gate(score, deployment_risk),
    }


def _affected_services(
    summary: dict[str, Any], changed_files: list[str], domains: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    services = []
    for domain in domains:
        name = str(domain.get("name", ""))
        services.append(
            {
                "service": name,
                "role": domain.get("role"),
                "changed_files": [
                    path
                    for path in changed_files
                    if name and (path.startswith(f"{name}/") or name in path)
                ],
                "risk": "high"
                if domain.get("security_findings") or domain.get("data_models")
                else "medium"
                if domain.get("routes")
                else "low",
            }
        )
    if services:
        return services[:12]
    for path in changed_files[:12]:
        services.append(
            {
                "service": path.split("/", 1)[0],
                "role": _layer(path),
                "changed_files": [path],
                "risk": _risk_level(30),
            }
        )
    return services


def _recommended_reviewers(
    impacts: list[dict[str, Any]], services: list[dict[str, Any]]
) -> list[str]:
    reviewers = {"code owner"}
    layers = {item["layer"] for item in impacts}
    if "security" in layers or any(service["risk"] == "high" for service in services):
        reviewers.add("security owner")
    if "data" in layers:
        reviewers.add("data platform owner")
    if "interface" in layers:
        reviewers.add("API owner")
    if len(services) >= 3:
        reviewers.add("staff engineer")
    return sorted(reviewers)


def _test_impact(
    summary: dict[str, Any], changed_files: list[str], domains: list[dict[str, Any]]
) -> dict[str, Any]:
    test_files = [
        file.get("relative_path", "")
        for file in summary.get("files", [])
        if "test" in file.get("relative_path", "").lower()
    ]
    related = []
    for changed in changed_files:
        stem = changed.rsplit("/", 1)[-1].split(".", 1)[0].lower()
        related.extend(path for path in test_files if stem and stem in path.lower())
    return {
        "related_tests": sorted(set(related))[:20],
        "coverage_confidence": "high" if related else "medium" if test_files else "low",
        "missing_test_warning": not bool(related),
        "domain_count": len(domains),
    }


def _impact_prediction(
    score: int, services: list[dict[str, Any]], impacts: list[dict[str, Any]]
) -> dict[str, Any]:
    return {
        "user_impact": "high"
        if any(item["layer"] == "interface" for item in impacts)
        else "medium"
        if services
        else "low",
        "operational_impact": "high" if score >= 70 else "medium" if score >= 40 else "low",
        "most_likely_failure_mode": "auth/data regression"
        if any(item["layer"] in {"security", "data"} for item in impacts)
        else "API or service behavior regression"
        if services
        else "localized code regression",
    }


def _release_gate(score: int, deployment_risk: dict[str, Any]) -> str:
    if score >= 75 or deployment_risk.get("level") == "critical":
        return "block until staff/security approval"
    if score >= 55 or deployment_risk.get("level") == "high":
        return "staff review required"
    if score >= 35:
        return "targeted owner review"
    return "standard review"


def _dependency_changes(
    changed_files: list[str], diff_metadata: dict[str, Any]
) -> list[dict[str, Any]]:
    dependency_files = {
        "requirements.txt",
        "pyproject.toml",
        "poetry.lock",
        "package.json",
        "package-lock.json",
        "pnpm-lock.yaml",
        "yarn.lock",
        "go.mod",
        "go.sum",
        "Cargo.toml",
        "Cargo.lock",
        "pom.xml",
        "build.gradle",
        "Dockerfile",
        "docker-compose.yml",
    }
    changes_by_path = {
        item.get("path"): item
        for item in diff_metadata.get("files", [])
        if isinstance(item, dict) and item.get("path")
    }
    rows = []
    for path in changed_files:
        name = path.rsplit("/", 1)[-1]
        if name in dependency_files:
            meta = changes_by_path.get(path, {})
            rows.append(
                {
                    "path": path,
                    "surface": "runtime dependency"
                    if name not in {"Dockerfile", "docker-compose.yml"}
                    else "deployment dependency",
                    "additions": meta.get("additions", 0),
                    "deletions": meta.get("deletions", 0),
                    "risk": "high"
                    if name.endswith(".lock") or name in {"Dockerfile", "docker-compose.yml"}
                    else "medium",
                }
            )
    return rows


def _api_changes(summary: dict[str, Any], changed_files: list[str]) -> list[dict[str, Any]]:
    route_files = set(summary.get("architecture", {}).get("route_files", []))
    parsed_by_path = {item.get("relative_path"): item for item in summary.get("parsed", [])}
    rows = []
    for path in changed_files:
        parsed = parsed_by_path.get(path, {})
        routes = parsed.get("routes", []) if isinstance(parsed, dict) else []
        if path in route_files or routes or _layer(path) == "interface":
            rows.append(
                {
                    "path": path,
                    "routes": [
                        f"{route.get('method', 'GET')} {route.get('path', '')}"
                        for route in routes
                        if isinstance(route, dict)
                    ],
                    "risk": "high" if routes else "medium",
                    "evidence": "Changed file is part of the analyzed API surface.",
                }
            )
    return rows


def _security_sensitive_changes(
    changed_files: list[str], impacts: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    sensitive_tokens = (
        "auth",
        "session",
        "jwt",
        "oauth",
        "password",
        "secret",
        "token",
        "permission",
        "policy",
        "cors",
        ".env",
        "settings",
        "config",
        "migration",
        "schema",
    )
    impact_by_path = {item["path"]: item for item in impacts}
    rows = []
    for path in changed_files:
        lower = path.lower()
        matched = [token for token in sensitive_tokens if token in lower]
        if matched:
            rows.append(
                {
                    "path": path,
                    "matched_signals": matched[:6],
                    "layer": impact_by_path.get(path, {}).get("layer", _layer(path)),
                    "risk": "high"
                    if any(token in matched for token in ("auth", "secret", "token", "password"))
                    else "medium",
                }
            )
    return rows


def _review_complexity(
    score: int,
    changed_files: list[str],
    diff_metadata: dict[str, Any],
    github_pr: dict[str, Any],
) -> dict[str, Any]:
    additions = int(diff_metadata.get("total_additions") or github_pr.get("additions") or 0)
    deletions = int(diff_metadata.get("total_deletions") or github_pr.get("deletions") or 0)
    commits = len(github_pr.get("commits", []))
    raw = min(100, score + len(changed_files) * 2 + (additions + deletions) // 45 + commits * 3)
    return {
        "score": raw,
        "level": _risk_level(raw),
        "file_count": len(changed_files),
        "line_delta": additions + deletions,
        "commit_count": commits,
        "review_comment_count": len(github_pr.get("comments", {}).get("review", []))
        if github_pr.get("comments")
        else 0,
    }


def _regression_probability(
    score: int,
    test_impact: dict[str, Any],
    dependency_changes: list[dict[str, Any]],
    api_changes: list[dict[str, Any]],
) -> dict[str, Any]:
    probability = score
    if test_impact.get("coverage_confidence") == "low":
        probability += 14
    elif test_impact.get("coverage_confidence") == "high":
        probability -= 10
    probability += len(dependency_changes) * 6 + len(api_changes) * 7
    probability = min(100, max(0, probability))
    return {
        "score": probability,
        "level": _risk_level(probability),
        "confidence": test_impact.get("coverage_confidence", "unknown"),
        "evidence": [
            f"{len(test_impact.get('related_tests', []))} related tests detected",
            f"{len(dependency_changes)} dependency surfaces changed",
            f"{len(api_changes)} API surfaces changed",
        ],
    }


def _ownership_routing(
    services: list[dict[str, Any]], reviewers: list[str], github_pr: dict[str, Any]
) -> list[dict[str, Any]]:
    requested = [
        item.get("login", "")
        for item in github_pr.get("reviewers", [])
        if isinstance(item, dict) and item.get("login")
    ]
    rows = []
    for service in services[:12]:
        rows.append(
            {
                "service": service.get("service"),
                "role": service.get("role"),
                "required_reviewers": reviewers,
                "requested_github_reviewers": requested,
                "routing_reason": f"{service.get('risk', 'medium')} risk service affected by changed files.",
            }
        )
    if not rows:
        rows.append(
            {
                "service": "repository",
                "role": "unmapped",
                "required_reviewers": reviewers,
                "requested_github_reviewers": requested,
                "routing_reason": "No analyzed service ownership matched the changed files.",
            }
        )
    return rows


def _impact_timeline(
    github_pr: dict[str, Any], changed_files: list[str], services: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    service_names = [str(item.get("service")) for item in services if item.get("service")]
    if not github_pr.get("commits"):
        return [
            {
                "label": "Changed files supplied manually",
                "events": changed_files[:12],
                "services": service_names[:8],
                "modules": sorted({path.split("/", 1)[0] for path in changed_files})[:8],
            }
        ]
    timeline = []
    for commit in github_pr.get("commits", [])[:20]:
        message = str(commit.get("message", "Commit"))
        touched = [
            path
            for path in changed_files
            if any(token and token.lower() in path.lower() for token in message.lower().split()[:6])
        ][:8]
        timeline.append(
            {
                "sha": str(commit.get("sha", ""))[:12],
                "label": message,
                "author": commit.get("author", ""),
                "date": commit.get("date", ""),
                "files": touched or changed_files[:6],
                "modules": sorted(
                    {path.split("/", 1)[0] for path in (touched or changed_files[:6])}
                ),
                "services": service_names[:8],
            }
        )
    return timeline
