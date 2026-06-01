from __future__ import annotations

from typing import Any


def build_cto_due_diligence(summary: dict[str, Any]) -> dict[str, Any]:
    scores = summary.get("scores", {})
    security = summary.get("security", {})
    kg = summary.get("knowledge_graph", {})
    top_risks = _top_risks(summary)
    strengths = _strengths(summary)
    enterprise_gaps = _enterprise_gaps(summary)
    recommendation = _recommendation(scores, top_risks, enterprise_gaps)
    return {
        "repository": summary.get("repository", {}),
        "investment_readiness": _readiness(scores, top_risks, enterprise_gaps),
        "recommendation": recommendation,
        "executive_summary": (
            f"{summary.get('repository', {}).get('name', 'Repository')} is a "
            f"{summary.get('architecture', {}).get('style', 'software')} with "
            f"{summary.get('statistics', {}).get('files', 0)} analyzed files, "
            f"{len(kg.get('domains', []))} mapped domains, and "
            f"{sum(security.get('severity_counts', {}).values())} security findings."
        ),
        "strengths": strengths,
        "top_risks": top_risks,
        "enterprise_gaps": enterprise_gaps,
        "critical_evidence": _critical_evidence(summary),
        "diligence_questions": _diligence_questions(summary),
        "scorecard": {
            "security": scores.get("security"),
            "maintainability": scores.get("maintainability"),
            "production_readiness": scores.get("production_readiness"),
            "cto": scores.get("cto"),
            "knowledge_graph_domains": len(kg.get("domains", [])),
            "knowledge_graph_hotspots": len(kg.get("hotspots", [])),
        },
    }


def render_cto_due_diligence_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# CTO Due-Diligence Report",
        "",
        f"Repository: `{report['repository'].get('name', 'unknown')}`",
        "",
        f"Investment readiness: **{report['investment_readiness']}**",
        "",
        f"Recommendation: **{report['recommendation']}**",
        "",
        "## Executive Summary",
        "",
        report["executive_summary"],
        "",
        "## Strengths",
        "",
        *_bullets(report["strengths"]),
        "",
        "## Top Risks",
        "",
        *_bullets(
            [
                f"{item['severity']}: {item['risk']} ({item['evidence']})"
                for item in report["top_risks"]
            ]
        ),
        "",
        "## Enterprise Gaps",
        "",
        *_bullets(report["enterprise_gaps"]),
        "",
        "## Critical Evidence",
        "",
        *_bullets(report["critical_evidence"]),
        "",
        "## Diligence Questions",
        "",
        *_bullets(report["diligence_questions"]),
    ]
    return "\n".join(lines) + "\n"


def _readiness(scores: dict[str, Any], risks: list[dict[str, str]], gaps: list[str]) -> str:
    cto = _number(scores.get("cto"))
    if cto >= 80 and len(risks) <= 2 and len(gaps) <= 3:
        return "strong"
    if cto >= 65 and len(risks) <= 5:
        return "moderate"
    if cto >= 50:
        return "early"
    return "high-risk"


def _recommendation(scores: dict[str, Any], risks: list[dict[str, str]], gaps: list[str]) -> str:
    if _number(scores.get("security")) < 55 or any(
        item["severity"] == "critical" for item in risks
    ):
        return "do not approve without remediation"
    if len(gaps) > 5:
        return "approve only with enterprise hardening plan"
    if _number(scores.get("cto")) >= 75:
        return "approve technical diligence with monitoring"
    return "request remediation plan before approval"


def _top_risks(summary: dict[str, Any]) -> list[dict[str, str]]:
    risks = []
    for finding in summary.get("security", {}).get("findings", [])[:8]:
        risks.append(
            {
                "severity": finding.get("severity", "medium"),
                "risk": finding.get("message", "security finding"),
                "evidence": f"{finding.get('path')}:{finding.get('line', 1)}",
            }
        )
    for hotspot in summary.get("knowledge_graph", {}).get("hotspots", [])[:5]:
        risks.append(
            {
                "severity": "high" if hotspot.get("risk_score", 0) >= 20 else "medium",
                "risk": "architectural hotspot",
                "evidence": hotspot.get("path", ""),
            }
        )
    return risks[:10]


def _strengths(summary: dict[str, Any]) -> list[str]:
    strengths = []
    stack = summary.get("stack", {})
    if stack.get("frameworks"):
        strengths.append(f"Frameworks detected: {', '.join(stack['frameworks'])}.")
    if summary.get("statistics", {}).get("routes", 0):
        strengths.append("Route surface was extracted and mapped.")
    if summary.get("knowledge_graph", {}).get("domains"):
        strengths.append("Repository domains are mapped into a knowledge graph.")
    if summary.get("scores", {}).get("maintainability", 0) >= 75:
        strengths.append("Maintainability score is above diligence threshold.")
    return strengths or ["Repository contains enough analyzable structure for technical diligence."]


def _enterprise_gaps(summary: dict[str, Any]) -> list[str]:
    paths = {item.get("relative_path", "").lower() for item in summary.get("files", [])}
    gaps = []
    if not any("test" in path or "spec" in path for path in paths):
        gaps.append("Automated test signal is weak or absent.")
    if not any(path.startswith(".github/") or "gitlab-ci" in path for path in paths):
        gaps.append("CI/CD evidence is weak or absent.")
    if "readme.md" not in {path.rsplit("/", 1)[-1] for path in paths}:
        gaps.append("README or operator documentation is missing.")
    if summary.get("scores", {}).get("security", 100) < 80:
        gaps.append("Security score needs remediation before enterprise approval.")
    if not summary.get("architecture", {}).get("database_model_files"):
        gaps.append("Persistence model evidence is limited or absent.")
    return gaps


def _critical_evidence(summary: dict[str, Any]) -> list[str]:
    evidence = []
    evidence.extend(summary.get("architecture", {}).get("important_files", [])[:5])
    evidence.extend(
        item.get("path") for item in summary.get("knowledge_graph", {}).get("hotspots", [])[:5]
    )
    evidence.extend(
        item.get("path") for item in summary.get("security", {}).get("findings", [])[:5]
    )
    return [item for index, item in enumerate(evidence) if item and item not in evidence[:index]][
        :12
    ]


def _diligence_questions(summary: dict[str, Any]) -> list[str]:
    questions = [
        "Which mapped domains have clear code owners and release accountability?",
        "Which hotspots require manual review before enterprise deployment?",
    ]
    if summary.get("security", {}).get("findings"):
        questions.append("What is the remediation SLA for current security findings?")
    if summary.get("architecture", {}).get("database_model_files"):
        questions.append("How are schema migrations tested and rolled back?")
    else:
        questions.append("Where is durable state modeled and documented?")
    return questions


def _bullets(items: list[str]) -> list[str]:
    return [f"- {item}" for item in items] or ["- None."]


def _number(value: Any) -> float:
    return float(value) if isinstance(value, (int, float)) else 0.0
