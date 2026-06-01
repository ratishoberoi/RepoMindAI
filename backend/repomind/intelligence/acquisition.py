from __future__ import annotations

from statistics import mean
from typing import Any


def build_acquisition_intelligence(summary: dict[str, Any]) -> dict[str, Any]:
    scores = summary.get("scores", {})
    metrics = {
        "acquisition_readiness": _weighted(
            [
                (scores.get("cto"), 0.24),
                (scores.get("security"), 0.22),
                (scores.get("production_readiness"), 0.20),
                (scores.get("maintainability"), 0.18),
                (_test_confidence(summary), 0.08),
                (_documentation_quality(summary), 0.08),
            ]
        ),
        "maintainability": _number(scores.get("maintainability")),
        "scalability": _scalability(summary),
        "security": _number(scores.get("security")),
        "bus_factor": _bus_factor(summary),
        "test_coverage_confidence": _test_confidence(summary),
        "ci_cd_maturity": _ci_cd_maturity(summary),
        "documentation_quality": _documentation_quality(summary),
        "operational_readiness": _operational_readiness(summary),
    }
    verdict = _verdict(metrics["acquisition_readiness"], summary)
    red_flags = _red_flags(summary, metrics)
    risks = _risks(summary, metrics)
    evidence = _evidence(summary)
    reasons = _reasons(metrics, summary)
    negotiation = _negotiation_points(red_flags, risks)
    return {
        "repository": summary.get("repository", {}),
        "scores": {key: round(value, 1) for key, value in metrics.items()},
        "ai_verdict": verdict,
        "reasons": reasons,
        "evidence": evidence,
        "risks": risks,
        "red_flags": red_flags,
        "negotiation_points": negotiation,
        "investment_memo": _memo("Investment Memo", verdict, reasons, red_flags, negotiation),
        "ma_memo": _memo("M&A Memo", verdict, reasons, red_flags, negotiation),
        "technical_due_diligence_packet": {
            "executive_summary": _summary_text(summary, verdict),
            "scorecard": {key: round(value, 1) for key, value in metrics.items()},
            "critical_evidence": evidence[:12],
            "red_flags": red_flags,
            "required_followups": _followups(summary, red_flags),
        },
    }


def _weighted(items: list[tuple[Any, float]]) -> float:
    total_weight = sum(weight for value, weight in items if isinstance(value, (int, float)))
    if not total_weight:
        return 0.0
    return (
        sum(float(value) * weight for value, weight in items if isinstance(value, (int, float)))
        / total_weight
    )


def _scalability(summary: dict[str, Any]) -> float:
    stack = summary.get("stack", {})
    arch = summary.get("architecture", {})
    score = 45.0
    score += 12 if stack.get("docker") else 0
    score += 10 if stack.get("ci_cd") else 0
    score += min(14, len(arch.get("components", [])) * 1.5)
    score += 10 if summary.get("statistics", {}).get("routes", 0) else 0
    score -= min(18, len(summary.get("knowledge_graph", {}).get("hotspots", [])) * 1.2)
    return max(0.0, min(100.0, score))


def _bus_factor(summary: dict[str, Any]) -> float:
    domains = summary.get("knowledge_graph", {}).get("domains", [])
    if not domains:
        return 40.0
    largest = max((item.get("file_count", 0) for item in domains), default=0)
    files = max(summary.get("statistics", {}).get("files", 1), 1)
    concentration = largest / files
    return round(max(20.0, min(95.0, 100 - concentration * 120)), 1)


def _test_confidence(summary: dict[str, Any]) -> float:
    files = [item.get("relative_path", "").lower() for item in summary.get("files", [])]
    if not files:
        return 0.0
    test_files = [path for path in files if "test" in path or "spec" in path]
    return min(95.0, 35 + len(test_files) / max(len(files), 1) * 220)


def _ci_cd_maturity(summary: dict[str, Any]) -> float:
    stack = summary.get("stack", {})
    score = 35.0
    if stack.get("ci_cd"):
        score += 35
    if stack.get("docker"):
        score += 15
    if any("deploy" in str(item).lower() for item in stack.get("ci_cd", [])):
        score += 10
    return min(100.0, score)


def _documentation_quality(summary: dict[str, Any]) -> float:
    files = [item.get("relative_path", "").lower() for item in summary.get("files", [])]
    score = 35.0
    if any(path.endswith("readme.md") for path in files):
        score += 35
    if any("docs/" in path for path in files):
        score += 15
    if summary.get("architecture", {}).get("summary"):
        score += 10
    return min(100.0, score)


def _operational_readiness(summary: dict[str, Any]) -> float:
    return mean(
        [
            _number(summary.get("scores", {}).get("production_readiness")),
            _ci_cd_maturity(summary),
            _documentation_quality(summary),
            _scalability(summary),
        ]
    )


def _verdict(score: float, summary: dict[str, Any]) -> str:
    critical = summary.get("security", {}).get("severity_counts", {}).get("critical", 0)
    if critical:
        return "High Risk Candidate"
    if score >= 78:
        return "Strong Acquisition Candidate"
    if score >= 62:
        return "Moderate Risk Candidate"
    return "High Risk Candidate"


def _red_flags(summary: dict[str, Any], metrics: dict[str, float]) -> list[dict[str, str]]:
    flags = []
    for finding in summary.get("security", {}).get("findings", [])[:8]:
        if finding.get("severity") in {"critical", "high"}:
            flags.append(
                {
                    "title": finding.get("message", "Security finding"),
                    "severity": finding.get("severity", "high"),
                    "evidence": f"{finding.get('path')}:{finding.get('line', 1)}",
                }
            )
    thresholds = [
        (
            "Weak CI/CD maturity",
            "medium",
            metrics["ci_cd_maturity"],
            "CI/CD evidence below diligence threshold.",
        ),
        (
            "Low documentation quality",
            "medium",
            metrics["documentation_quality"],
            "Documentation evidence below diligence threshold.",
        ),
        (
            "Low test confidence",
            "high",
            metrics["test_coverage_confidence"],
            "Automated test signal is insufficient for acquisition diligence.",
        ),
    ]
    for title, severity, value, evidence in thresholds:
        if value < 55:
            flags.append({"title": title, "severity": severity, "evidence": evidence})
    return flags[:12]


def _risks(summary: dict[str, Any], metrics: dict[str, float]) -> list[dict[str, str]]:
    risks = [
        {
            "title": "Security posture",
            "severity": _severity(metrics["security"]),
            "evidence": f"Security score {metrics['security']:.1f}",
        },
        {
            "title": "Operational readiness",
            "severity": _severity(metrics["operational_readiness"]),
            "evidence": f"Operational readiness {metrics['operational_readiness']:.1f}",
        },
        {
            "title": "Bus factor concentration",
            "severity": _severity(metrics["bus_factor"]),
            "evidence": f"Bus factor score {metrics['bus_factor']:.1f}",
        },
    ]
    for hotspot in summary.get("knowledge_graph", {}).get("hotspots", [])[:5]:
        risks.append(
            {
                "title": "Architecture hotspot",
                "severity": "medium",
                "evidence": hotspot.get("path", ""),
            }
        )
    return risks


def _evidence(summary: dict[str, Any]) -> list[str]:
    evidence = []
    evidence.extend(summary.get("architecture", {}).get("important_files", [])[:8])
    evidence.extend(
        item.get("path") for item in summary.get("security", {}).get("findings", [])[:8]
    )
    evidence.extend(
        item.get("path") for item in summary.get("knowledge_graph", {}).get("hotspots", [])[:8]
    )
    return [item for index, item in enumerate(evidence) if item and item not in evidence[:index]]


def _reasons(metrics: dict[str, float], summary: dict[str, Any]) -> list[str]:
    return [
        f"CTO score is {_number(summary.get('scores', {}).get('cto')):.1f}/100.",
        f"Security posture is {metrics['security']:.1f}/100.",
        f"Operational readiness is {metrics['operational_readiness']:.1f}/100.",
        f"Knowledge graph identified {len(summary.get('knowledge_graph', {}).get('hotspots', []))} architectural hotspots.",
    ]


def _negotiation_points(red_flags: list[dict[str, str]], risks: list[dict[str, str]]) -> list[str]:
    points = [
        f"Require remediation evidence for {item['title']} ({item['evidence']})."
        for item in red_flags[:5]
    ]
    points.extend(f"Price diligence risk reserve around {item['title']}." for item in risks[:3])
    return points[:8]


def _memo(
    title: str,
    verdict: str,
    reasons: list[str],
    red_flags: list[dict[str, str]],
    negotiation: list[str],
) -> str:
    return "\n".join(
        [
            f"# {title}",
            "",
            f"Verdict: **{verdict}**",
            "",
            "## Reasons",
            *[f"- {item}" for item in reasons],
            "",
            "## Red Flags",
            *(
                [
                    f"- {item['severity']}: {item['title']} ({item['evidence']})"
                    for item in red_flags
                ]
                or ["- None detected."]
            ),
            "",
            "## Negotiation Points",
            *(
                [f"- {item}" for item in negotiation]
                or ["- No special negotiation points detected."]
            ),
            "",
        ]
    )


def _summary_text(summary: dict[str, Any], verdict: str) -> str:
    return (
        f"{summary.get('repository', {}).get('name', 'Repository')} is classified as {verdict}. "
        f"The assessment uses static architecture evidence, security findings, repository health scores, and knowledge graph hotspots."
    )


def _followups(summary: dict[str, Any], red_flags: list[dict[str, str]]) -> list[str]:
    questions = [
        "Validate deployment, incident response, and code ownership evidence with the engineering team."
    ]
    questions.extend(f"Request remediation plan for {item['title']}." for item in red_flags[:5])
    if not summary.get("stack", {}).get("ci_cd"):
        questions.append("Ask for CI/CD pipeline evidence outside the repository.")
    return questions


def _severity(score: float) -> str:
    if score < 50:
        return "high"
    if score < 70:
        return "medium"
    return "low"


def _number(value: Any) -> float:
    return float(value) if isinstance(value, (int, float)) else 0.0
