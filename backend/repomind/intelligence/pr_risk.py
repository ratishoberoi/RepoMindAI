from __future__ import annotations

from pathlib import PurePosixPath
from typing import Any


def analyze_pr_risk(
    summary: dict[str, Any], changed_files: list[str], title: str = ""
) -> dict[str, Any]:
    normalized = [_normalize(path) for path in changed_files if path.strip()]
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
    return {
        "title": title,
        "changed_files": normalized,
        "risk_score": score,
        "risk_level": _risk_level(score),
        "impacted_domains": impacted_domains,
        "file_impacts": sorted(impacts, key=lambda item: item["risk"], reverse=True),
        "required_review": _required_review(score, impacted_domains, impacts),
        "test_strategy": _test_strategy(impacted_domains, impacts),
        "summary": _summary(score, impacted_domains, impacts),
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
