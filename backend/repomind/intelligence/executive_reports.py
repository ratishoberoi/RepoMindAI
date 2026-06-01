from __future__ import annotations

from typing import Any

from repomind.intelligence.acquisition import build_acquisition_intelligence


def build_executive_report_pack(summary: dict[str, Any]) -> dict[str, Any]:
    acquisition = build_acquisition_intelligence(summary)
    return {
        "repository": summary.get("repository", {}),
        "board_report": _board_report(summary, acquisition),
        "cto_report": _cto_report(summary),
        "investor_report": _investor_report(summary, acquisition),
        "security_report": _security_report(summary),
        "engineering_roadmap": _engineering_roadmap(summary),
        "exports": {
            "markdown": "available through report downloads",
            "html": "available through report downloads",
            "pdf": "available through report downloads",
        },
    }


def render_report_pack_markdown(pack: dict[str, Any]) -> str:
    sections = [
        ("Board Report", pack.get("board_report", {})),
        ("CTO Report", pack.get("cto_report", {})),
        ("Investor Report", pack.get("investor_report", {})),
        ("Security Report", pack.get("security_report", {})),
        ("Engineering Roadmap", pack.get("engineering_roadmap", {})),
    ]
    lines = ["# Executive Intelligence Report Pack", ""]
    for title, section in sections:
        lines.extend([f"## {title}", "", section.get("summary", "")])
        for key in ("scorecard", "top_risks", "recommendations", "timeline"):
            value = section.get(key)
            if not value:
                continue
            lines.extend(["", f"### {key.replace('_', ' ').title()}"])
            if isinstance(value, dict):
                lines.extend(f"- {item}: {score}" for item, score in value.items())
            else:
                lines.extend(f"- {_format_item(item)}" for item in value)
        lines.append("")
    return "\n".join(lines)


def _board_report(summary: dict[str, Any], acquisition: dict[str, Any]) -> dict[str, Any]:
    scores = summary.get("scores", {})
    risks = _top_risks(summary)
    return {
        "summary": f"Board-level posture: {acquisition['ai_verdict']} with CTO score {scores.get('cto', 'n/a')} and acquisition readiness {acquisition['scores']['acquisition_readiness']}.",
        "scorecard": {
            "architecture_posture": scores.get("cto", 0),
            "security_posture": scores.get("security", 0),
            "technical_debt": scores.get("maintainability", 0),
            "production_readiness": scores.get("production_readiness", 0),
        },
        "top_risks": risks[:6],
        "recommendations": acquisition.get("negotiation_points", [])[:5],
        "remediation_roadmap": _roadmap(summary),
    }


def _cto_report(summary: dict[str, Any]) -> dict[str, Any]:
    return {
        "summary": summary.get("architecture", {}).get(
            "summary", "Architecture evidence is limited."
        ),
        "scorecard": {
            "scalability": _scalability(summary),
            "maintainability": summary.get("scores", {}).get("maintainability", 0),
            "engineering_health": summary.get("scores", {}).get("cto", 0),
            "architecture_quality": summary.get("scores", {}).get("production_readiness", 0),
        },
        "ownership_concerns": _ownership_concerns(summary),
        "top_risks": _top_risks(summary)[:8],
        "recommendations": _cto_recommendations(summary),
    }


def _investor_report(summary: dict[str, Any], acquisition: dict[str, Any]) -> dict[str, Any]:
    return {
        "summary": acquisition.get("technical_due_diligence_packet", {}).get(
            "executive_summary", ""
        ),
        "scorecard": acquisition.get("scores", {}),
        "technical_moat": _technical_moat(summary),
        "engineering_maturity": acquisition["scores"].get("operational_readiness", 0),
        "technical_risks": acquisition.get("risks", [])[:8],
        "recommendations": acquisition.get("negotiation_points", [])[:8],
    }


def _security_report(summary: dict[str, Any]) -> dict[str, Any]:
    findings = summary.get("security", {}).get("findings", [])
    return {
        "summary": f"{len(findings)} security findings with score {summary.get('scores', {}).get('security', 'n/a')}.",
        "scorecard": summary.get("security", {}).get("severity_counts", {}),
        "vulnerabilities": findings[:25],
        "secrets": [
            item
            for item in findings
            if "secret" in str(item.get("rule_id", "")).lower()
            or "secret" in str(item.get("message", "")).lower()
        ][:12],
        "exposure": _exposure(summary),
        "risk_matrix": _risk_matrix(findings),
    }


def _engineering_roadmap(summary: dict[str, Any]) -> dict[str, Any]:
    return {
        "summary": "Sequenced remediation plan generated from repository evidence.",
        "timeline": _roadmap(summary),
        "recommendations": _cto_recommendations(summary),
    }


def _roadmap(summary: dict[str, Any]) -> list[dict[str, str]]:
    risks = _top_risks(summary)
    return [
        {
            "window": "30 days",
            "theme": "Stabilize",
            "actions": "Resolve critical/high security findings and add regression tests around hotspots.",
        },
        {
            "window": "60 days",
            "theme": "Harden",
            "actions": "Add CI/CD enforcement, ownership boundaries, and operational runbooks.",
        },
        {
            "window": "90 days",
            "theme": "Scale",
            "actions": "Reduce dependency bottlenecks and formalize architecture governance."
            if risks
            else "Institutionalize architecture drift monitoring.",
        },
    ]


def _top_risks(summary: dict[str, Any]) -> list[dict[str, Any]]:
    risks = []
    for finding in summary.get("security", {}).get("findings", [])[:10]:
        risks.append(
            {
                "title": finding.get("message"),
                "severity": finding.get("severity"),
                "evidence": f"{finding.get('path')}:{finding.get('line', 1)}",
            }
        )
    for hotspot in summary.get("knowledge_graph", {}).get("hotspots", [])[:8]:
        risks.append(
            {"title": "Architecture hotspot", "severity": "medium", "evidence": hotspot.get("path")}
        )
    return risks


def _scalability(summary: dict[str, Any]) -> float:
    score = 45.0
    score += 12 if summary.get("stack", {}).get("docker") else 0
    score += 12 if summary.get("stack", {}).get("ci_cd") else 0
    score += min(18, len(summary.get("architecture", {}).get("components", [])) * 1.5)
    score -= min(15, len(summary.get("knowledge_graph", {}).get("hotspots", [])))
    return round(max(0, min(100, score)), 1)


def _ownership_concerns(summary: dict[str, Any]) -> list[str]:
    domains = summary.get("knowledge_graph", {}).get("domains", [])
    concerns = [
        f"{domain.get('name')} concentrates {domain.get('file_count')} files."
        for domain in domains
        if domain.get("file_count", 0) >= 10
    ]
    if not concerns:
        concerns.append("No ownership concentration signal detected from repository structure.")
    return concerns[:8]


def _cto_recommendations(summary: dict[str, Any]) -> list[str]:
    recommendations = []
    if summary.get("security", {}).get("findings"):
        recommendations.append(
            "Create a vulnerability burn-down plan with owner and SLA per finding."
        )
    if summary.get("knowledge_graph", {}).get("hotspots"):
        recommendations.append(
            "Refactor or document high-centrality architecture hotspots before scaling team ownership."
        )
    if not summary.get("stack", {}).get("ci_cd"):
        recommendations.append(
            "Add CI checks for tests, linting, dependency review, and secret scanning."
        )
    if not recommendations:
        recommendations.append("Keep architecture drift and risk reporting in the release process.")
    return recommendations


def _technical_moat(summary: dict[str, Any]) -> str:
    frameworks = summary.get("stack", {}).get("frameworks", [])
    domains = len(summary.get("knowledge_graph", {}).get("domains", []))
    return f"Detected {domains} architecture domains and framework signals: {', '.join(frameworks) or 'none detected'}."


def _exposure(summary: dict[str, Any]) -> list[str]:
    return [
        f"{item.get('method')} {item.get('path')} in {item.get('file')}"
        for item in _routes(summary)[:20]
    ] or ["No HTTP route exposure detected."]


def _routes(summary: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for item in summary.get("parsed", []):
        for route in item.get("routes", []):
            if isinstance(route, dict):
                rows.append(
                    {
                        "method": route.get("method"),
                        "path": route.get("path"),
                        "file": item.get("relative_path"),
                    }
                )
    return rows


def _risk_matrix(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "severity": severity,
            "count": sum(1 for item in findings if item.get("severity") == severity),
            "likelihood": "high" if severity in {"critical", "high"} else "medium",
        }
        for severity in ("critical", "high", "medium", "low")
    ]


def _format_item(item: Any) -> str:
    if isinstance(item, dict):
        return ", ".join(f"{key}: {value}" for key, value in item.items())
    return str(item)
