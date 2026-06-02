from __future__ import annotations

import json
import shutil
from collections.abc import Callable as CollectionsCallable
from datetime import date, datetime
from html import escape
from pathlib import Path
from typing import Any

from repomind.core.config import get_settings
from repomind.intelligence.architecture_explorer import (
    build_architecture_explorer,
    render_onboarding_markdown,
)
from repomind.intelligence.due_diligence import (
    build_cto_due_diligence,
    render_cto_due_diligence_markdown,
)
from repomind.intelligence.executive_reports import (
    build_executive_report_pack,
    render_report_pack_markdown,
)
from repomind.llm.prompts import report_prompt, synthesis_prompt
from repomind.llm.registry import local_model
from repomind.security.redaction import redact_text

REPORT_NAMES = [
    "README.md",
    "ARCHITECTURE.md",
    "SECURITY_REPORT.md",
    "TECH_DEBT.md",
    "RECRUITER_REVIEW.md",
    "CTO_REVIEW.md",
    "CTO_DUE_DILIGENCE.md",
    "EXECUTIVE_REPORT_PACK.md",
    "ONBOARDING.md",
    "ROADMAP.md",
    "PROJECT_STATUS.md",
    "README_REPORT.md",
    "ARCHITECTURE_REPORT.md",
    "CTO_REPORT.md",
    "INVESTOR_REPORT.md",
    "DUE_DILIGENCE_REPORT.md",
    "ROADMAP_REPORT.md",
    "EXECUTIVE_SUMMARY.md",
]
HTML_REPORT_NAMES = [
    "CTO_REPORT.html",
    "EXECUTIVE_REPORT.html",
    "INVESTOR_REPORT.html",
    "DUE_DILIGENCE_REPORT.html",
    "SECURITY_REPORT.html",
    "ARCHITECTURE_REPORT.html",
]
PDF_REPORT_NAMES = [name.replace(".html", ".pdf") for name in HTML_REPORT_NAMES]
EXTRA_REPORT_NAMES = [
    "SECURITY.sarif",
    "EXECUTIVE_SUMMARY.html",
    "EXECUTIVE_SUMMARY.pdf",
    *HTML_REPORT_NAMES,
    *PDF_REPORT_NAMES,
]
CancelCheck = CollectionsCallable[[], bool]


def generate_reports(
    repo: dict[str, Any], summary: dict[str, Any], cancel_check: CancelCheck | None = None
) -> dict[str, str]:
    settings = get_settings()
    out_dir = settings.reports_dir / "generated" / repo["id"]
    out_dir.mkdir(parents=True, exist_ok=True)
    summary = _redacted_summary(summary)
    ai = _synthesize_reports(summary, cancel_check=cancel_check)
    writers: dict[str, CollectionsCallable[[dict[str, Any], dict[str, str]], str]] = {
        "README.md": _readme,
        "ARCHITECTURE.md": _architecture,
        "SECURITY_REPORT.md": _security,
        "TECH_DEBT.md": _debt,
        "RECRUITER_REVIEW.md": _recruiter,
        "CTO_REVIEW.md": _cto,
        "CTO_DUE_DILIGENCE.md": _due_diligence,
        "EXECUTIVE_REPORT_PACK.md": _executive_pack,
        "ONBOARDING.md": _onboarding,
        "ROADMAP.md": _roadmap,
        "PROJECT_STATUS.md": _status,
        "README_REPORT.md": _readme,
        "ARCHITECTURE_REPORT.md": _architecture_report,
        "CTO_REPORT.md": _cto,
        "INVESTOR_REPORT.md": _investor_report,
        "DUE_DILIGENCE_REPORT.md": _due_diligence,
        "ROADMAP_REPORT.md": _roadmap,
        "EXECUTIVE_SUMMARY.md": _executive_summary_md,
    }
    paths: dict[str, str] = {}
    for name in REPORT_NAMES:
        _checkpoint(cancel_check)
        writer = writers[name]
        path = out_dir / name
        path.write_text(redact_text(writer(summary, ai)))
        paths[name] = str(path)
    sarif_path = out_dir / "SECURITY.sarif"
    sarif_path.write_text(_json_dumps(_sarif(summary), indent=2))
    paths[sarif_path.name] = str(sarif_path)
    html_path = out_dir / "EXECUTIVE_SUMMARY.html"
    html_path.write_text(_html_summary(summary, "Executive Summary"))
    paths[html_path.name] = str(html_path)
    pdf_path = out_dir / "EXECUTIVE_SUMMARY.pdf"
    pdf_path.write_bytes(_pdf_summary(summary, "Executive Summary"))
    paths[pdf_path.name] = str(pdf_path)
    for report_name in HTML_REPORT_NAMES:
        report_title = report_name.removesuffix(".html").replace("_", " ").title()
        path = out_dir / report_name
        path.write_text(_html_summary(summary, report_title))
        paths[path.name] = str(path)
    for report_name in PDF_REPORT_NAMES:
        report_title = report_name.removesuffix(".pdf").replace("_", " ").title()
        path = out_dir / report_name
        path.write_bytes(_pdf_summary(summary, report_title))
        paths[path.name] = str(path)
    (out_dir / "analysis-summary.json").write_text(redact_text(_json_dumps(summary, indent=2)))
    paths["analysis-summary.json"] = str(out_dir / "analysis-summary.json")
    return paths


def export_bundle(repo_id: str) -> Path:
    settings = get_settings()
    source = settings.reports_dir / "generated" / repo_id
    if not source.exists():
        raise FileNotFoundError(repo_id)
    target = settings.exports_dir / f"{repo_id}-reports"
    archive = shutil.make_archive(str(target), "zip", source)
    return Path(archive)


def compare_summaries(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    left_scores = left.get("scores", {})
    right_scores = right.get("scores", {})
    left_stats = left.get("statistics", {})
    right_stats = right.get("statistics", {})
    return {
        "left": left.get("repository", {}),
        "right": right.get("repository", {}),
        "score_delta": {
            key: _number(right_scores.get(key)) - _number(left_scores.get(key))
            for key in sorted(set(left_scores) | set(right_scores))
            if key != "details"
        },
        "statistics_delta": {
            key: _number(right_stats.get(key)) - _number(left_stats.get(key))
            for key in sorted(set(left_stats) | set(right_stats))
        },
        "stack_added": sorted(
            set(right.get("stack", {}).get("frameworks", []))
            - set(left.get("stack", {}).get("frameworks", []))
        ),
        "stack_removed": sorted(
            set(left.get("stack", {}).get("frameworks", []))
            - set(right.get("stack", {}).get("frameworks", []))
        ),
    }


def _header(title: str, summary: dict[str, Any]) -> str:
    repo = summary["repository"]
    return f"# {title}\n\nRepository: `{repo['name']}`\n\nGenerated by RepoMind AI using local-only qwen-judge inference.\n\n"


def _readme(summary: dict[str, Any], ai: dict[str, str]) -> str:
    stats = summary["statistics"]
    return (
        _header("RepoMind AI Repository Brief", summary)
        + f"## Overview\n\n{summary['architecture']['summary']}\n\n"
        + f"## Key Stats\n\n- Files analyzed: {stats.get('files', 0)}\n- Functions: {stats.get('functions', 0)}\n- Methods: {stats.get('methods', 0)}\n- Classes: {stats.get('classes', 0)}\n- Routes: {stats.get('routes', 0)}\n- Database models: {stats.get('database_models', 0)}\n- Indexed chunks: {stats.get('indexed_chunks', 0)}\n\n"
        + f"## Detected Stack\n\n- Primary language: {summary['languages']['primary']}\n- Frameworks: {', '.join(summary['stack']['frameworks']) or 'None detected'}\n- Package managers: {', '.join(summary['stack']['package_managers']) or 'None detected'}\n\n"
        + _ai_section("Local Model Brief", ai["overview"])
        + "## Generated Reports\n\n- ARCHITECTURE.md\n- SECURITY_REPORT.md\n- TECH_DEBT.md\n- RECRUITER_REVIEW.md\n- CTO_REVIEW.md\n- ROADMAP.md\n"
    )


def _architecture(summary: dict[str, Any], ai: dict[str, str]) -> str:
    arch = summary["architecture"]
    important = (
        "\n".join(f"- `{path}`" for path in arch.get("important_files", []))
        or "- No graph centrality signals found."
    )
    dirs = (
        "\n".join(f"- `{path}`" for path in arch.get("top_level_directories", []))
        or "- Flat repository."
    )
    diagrams = arch.get("diagrams", {})
    diagram_blocks = "\n\n".join(
        f"## {label}\n\n```mermaid\n{body}\n```"
        for label, body in [
            ("System Diagram", diagrams.get("system")),
            ("Component Diagram", diagrams.get("component")),
            ("Dependency Diagram", diagrams.get("dependency")),
            ("Service Diagram", diagrams.get("service")),
            ("Data Flow Diagram", diagrams.get("data_flow")),
        ]
        if body
    )
    return (
        _header("Architecture", summary)
        + f"## Inferred Style\n\n{arch.get('style', 'Unknown')}\n\n## Summary\n\n{arch.get('summary', 'No architecture summary available.')}\n\n"
        + f"## Top-Level Directories\n\n{dirs}\n\n## Important Files\n\n{important}\n\n"
        + _ai_section("Architecture Explanation", ai["architecture"])
        + diagram_blocks
        + "\n"
    )


def _architecture_report(summary: dict[str, Any], ai: dict[str, str]) -> str:
    explorer = build_architecture_explorer(summary)
    review = explorer.get("architecture_review", {})
    architect_findings = explorer.get("ai_architect_review", [])
    review_sections = "\n".join(
        [
            _review_list("Architecture Strengths", review.get("strengths", [])),
            _review_list("Architecture Weaknesses", review.get("weaknesses", [])),
            _review_list("Current Risks", review.get("current_risks", [])),
            _review_list("Future Risks", review.get("future_risks", [])),
            _review_list("Refactoring Opportunities", review.get("refactoring_opportunities", [])),
            _review_list("Scaling Risks", review.get("scaling_risks", [])),
            _review_list("Tech Debt Risks", review.get("tech_debt_risks", [])),
        ]
    )
    findings = (
        "\n".join(
            "- **{severity}** {risk}\n  - Impact: {impact}\n  - Recommendation: {recommendation}\n  - Files: {files}".format(
                severity=item.get("severity", "medium"),
                risk=item.get("risk", "Architecture risk"),
                impact=item.get("impact", "Impact requires review."),
                recommendation=item.get("recommendation", "Review architecture boundary."),
                files=", ".join(f"`{path}`" for path in item.get("affected_files", [])[:8])
                or "No file evidence",
            )
            for item in architect_findings[:12]
        )
        or "- No high-confidence AI architect findings detected."
    )
    return (
        _architecture(summary, ai)
        + "\n## Architecture Review\n\n"
        + f"- Coupling: {review.get('coupling_analysis', {}).get('level', 'unknown')}\n"
        + f"- Scalability: {review.get('scalability_analysis', {}).get('level', 'unknown')}\n"
        + f"- Service boundaries: {review.get('service_boundary_analysis', {}).get('level', 'unknown')}\n"
        + f"- Modularity: {review.get('modularity_analysis', {}).get('level', 'unknown')}\n"
        + f"- Maintainability: {review.get('maintainability_analysis', {}).get('level', 'unknown')}\n\n"
        + review_sections
        + "\n## AI Architect Review\n\n"
        + findings
        + "\n"
    )


def _security(summary: dict[str, Any], ai: dict[str, str]) -> str:
    findings = summary["security"]["findings"]
    rows = (
        "\n".join(
            f"- **{item.get('severity', 'medium')}** `{item.get('path', item.get('file', 'unknown'))}:{item.get('line', 1)}` `{item.get('rule_id', 'repomind')}` - {item.get('message', item.get('title', 'Security finding'))}"
            f"\n  - OWASP: {item.get('owasp', 'Unmapped')}; CWE: {item.get('cwe', 'Unmapped')}"
            f"\n  - Impact: {item.get('impact', 'Review finding impact.')}"
            f"\n  - Remediation: {item.get('remediation', 'Review and remediate this finding.')}"
            for item in findings[:100]
        )
        or "- No high-confidence findings from enabled scanners."
    )
    return (
        _header("Security Report", summary)
        + f"Security score: **{summary['scores']['security']} / 100**\n\n"
        + _score_details("security", summary)
        + f"Scanner status: `{summary['security'].get('scanner_status', {})}`\n\n"
        + f"Severity counts: `{summary['security'].get('severity_counts', {})}`\n\n## Findings\n\n{rows}\n\n"
        + _ai_section("Local Model Security Assessment", ai["technical"])
        + "## Next Steps\n\n- Review high severity findings first.\n- Add scanner execution to CI before public release.\n- Keep generated reports private when they include sensitive paths or secrets.\n"
    )


def _debt(summary: dict[str, Any], ai: dict[str, str]) -> str:
    debt = summary["technical_debt"]
    items = (
        "\n".join(
            f"- `{item['path']}:{item['line']}` {item['message']} ({item['severity']})"
            for item in debt["items"][:100]
        )
        or "- No major complexity findings detected."
    )
    todos = (
        "\n".join(
            f"- `{item['path']}` {item['tag']}: {item['text']}" for item in debt["todos"][:50]
        )
        or "- No TODO/FIXME markers detected."
    )
    return (
        _header("Technical Debt", summary)
        + f"Maintainability score: **{debt['score']} / 100**\n\n"
        + _score_details("maintainability", summary)
        + f"## Complexity\n\n{items}\n\n## Markers\n\n{todos}\n\n"
        + _ai_section("Local Model Debt Assessment", ai["technical"])
    )


def _recruiter(summary: dict[str, Any], ai: dict[str, str]) -> str:
    return (
        _header("Recruiter Review", summary)
        + f"Recruiter score: **{summary['scores'].get('recruiter', summary['scores'].get('cto', 0))} / 100**\n\n"
        + _score_details("recruiter", summary)
        + "## Hiring Signal\n\n"
        + ai["recruiter"]
        + "\n\n## Evidence\n\n"
        + f"- Primary language: {summary['languages']['primary']}\n- Frameworks: {', '.join(summary['stack']['frameworks']) or 'None detected'}\n- Files analyzed: {summary['statistics']['files']}\n"
        + _evidence_files(summary)
    )


def _cto(summary: dict[str, Any], ai: dict[str, str]) -> str:
    return (
        _header("CTO Review", summary)
        + f"CTO score: **{summary['scores'].get('cto', 0)} / 100**\n\n"
        + _score_details("cto", summary)
        + "## Executive View\n\n"
        + ai["cto"]
        + "\n\n## Risk Snapshot\n\n"
        + f"- Security score: {summary['scores']['security']}\n- Maintainability score: {summary['scores']['maintainability']}\n- Production readiness: {summary['scores']['production_readiness']}\n"
        + _evidence_files(summary)
    )


def _due_diligence(summary: dict[str, Any], ai: dict[str, str]) -> str:
    return render_cto_due_diligence_markdown(build_cto_due_diligence(summary))


def _executive_pack(summary: dict[str, Any], ai: dict[str, str]) -> str:
    return render_report_pack_markdown(build_executive_report_pack(summary))


def _investor_report(summary: dict[str, Any], ai: dict[str, str]) -> str:
    pack = build_executive_report_pack(summary)
    investor = pack.get("investor_report", {})
    lines = [
        _header("Investor Report", summary),
        investor.get("summary", ""),
        "",
        "## Scorecard",
        "",
    ]
    lines.extend(
        f"- {key.replace('_', ' ').title()}: {value}"
        for key, value in investor.get("scorecard", {}).items()
    )
    lines.extend(["", "## Technical Moat", "", str(investor.get("technical_moat", ""))])
    lines.extend(["", "## Technical Risks", ""])
    lines.extend(f"- {_format_item(item)}" for item in investor.get("technical_risks", [])[:10])
    lines.extend(["", "## Recommendations", ""])
    lines.extend(f"- {item}" for item in investor.get("recommendations", [])[:10])
    return "\n".join(lines) + "\n"


def _executive_summary_md(summary: dict[str, Any], ai: dict[str, str]) -> str:
    evidence = summary.get("score_evidence", {})
    lines = [
        _header("Executive Summary", summary),
        summary.get("architecture", {}).get("summary", "Architecture summary unavailable."),
        "",
        "## Explainable Scores",
        "",
    ]
    for key in ("health", "security", "architecture", "investment", "acquisition", "risk"):
        item = evidence.get(key)
        if not item:
            continue
        lines.extend(
            [
                f"### {item.get('label', key.title())}",
                "",
                f"- Score: {item.get('score')}/100",
                f"- Confidence: {item.get('confidence')}",
                f"- Calculation: {item.get('calculation')}",
                "",
                "Weighted factors:",
            ]
        )
        lines.extend(
            f"- {factor.get('label')}: {factor.get('value')} x {factor.get('weight')}"
            for factor in item.get("factors", [])[:8]
        )
        citations = item.get("citations", [])[:8]
        if citations:
            lines.extend(["", "Evidence:"])
            lines.extend(
                f"- `{citation.get('file')}`:{citation.get('line', 1)} - {citation.get('evidence', citation.get('reason', 'Evidence'))}"
                for citation in citations
            )
        lines.append("")
    lines.extend(["## Executive Recommendation", "", ai["cto"]])
    return "\n".join(lines) + "\n"


def _onboarding(summary: dict[str, Any], ai: dict[str, str]) -> str:
    return render_onboarding_markdown(summary)


def _roadmap(summary: dict[str, Any], ai: dict[str, str]) -> str:
    return (
        _header("Roadmap", summary)
        + _ai_section("Local Model Roadmap", ai["technical"])
        + "## Recommended Next Steps\n\n"
        + "1. Resolve high severity security findings.\n"
        + "2. Add or strengthen automated tests around important files.\n"
        + "3. Reduce high-complexity functions and document major architecture decisions.\n"
        + "4. Add CI checks for linting, tests, dependency review, and secret scanning.\n"
        + "5. Re-run RepoMind AI after remediation to compare scores.\n"
    )


def _status(summary: dict[str, Any], ai: dict[str, str]) -> str:
    return (
        _header("Project Status", summary)
        + f"## Scores\n\n```json\n{json.dumps(summary['scores'], indent=2)}\n```\n\n"
        + f"## Performance\n\n```json\n{json.dumps(summary.get('performance', {}), indent=2)}\n```\n\n"
        + f"## Model Status\n\n```json\n{json.dumps(local_model().status(), indent=2)}\n```\n"
        + _ai_section("Local Model Status Interpretation", ai["overview"])
    )


def _sarif(summary: dict[str, Any]) -> dict[str, Any]:
    findings = summary.get("security", {}).get("findings", [])
    return {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "RepoMind AI",
                        "informationUri": "https://github.com",
                        "rules": _sarif_rules(findings),
                    }
                },
                "results": [_sarif_result(item) for item in findings],
            }
        ],
    }


def _sarif_rules(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rules = {}
    for item in findings:
        rule_id = item.get("rule_id", "repomind")
        rules[rule_id] = {
            "id": rule_id,
            "name": rule_id,
            "shortDescription": {"text": item.get("message", "RepoMind AI security finding")},
            "properties": {
                "security-severity": _sarif_security_severity(item.get("severity", "medium"))
            },
        }
    return list(rules.values())


def _sarif_result(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "ruleId": item.get("rule_id", "repomind"),
        "level": _sarif_level(item.get("severity", "medium")),
        "message": {"text": item.get("message", "RepoMind AI security finding")},
        "locations": [
            {
                "physicalLocation": {
                    "artifactLocation": {"uri": item.get("path", "")},
                    "region": {"startLine": item.get("line", 1)},
                }
            }
        ],
    }


def _html_summary(summary: dict[str, Any], report_title: str = "Executive Summary") -> str:
    scores = summary.get("scores", {})
    stats = summary.get("statistics", {})
    findings = summary.get("security", {}).get("findings", [])
    evidence = summary.get("score_evidence", {})
    rows = "".join(
        f"<div class='metric'><span>{escape(str(key))}</span><strong>{escape(str(value))}</strong></div>"
        for key, value in {
            "Repository": summary.get("repository", {}).get("name"),
            "Files": stats.get("files"),
            "Primary language": summary.get("languages", {}).get("primary"),
            "Security": scores.get("security"),
            "Maintainability": scores.get("maintainability"),
            "Production readiness": scores.get("production_readiness"),
        }.items()
    )
    scorecards = "".join(
        f"<section class='score'><h3>{escape(str(item.get('label', key)))}</h3><div class='bar'><i style='width:{float(item.get('score', 0))}%'></i></div><p>{escape(str(item.get('calculation', '')))}</p></section>"
        for key, item in evidence.items()
    )
    risk_rows = (
        "".join(
            f"<article class='risk'><b>{escape(str(item.get('severity', 'medium')).upper())}</b><span>{escape(str(item.get('message', item.get('title', 'Finding'))))}</span><small>{escape(str(item.get('path', item.get('file', ''))))}:{escape(str(item.get('line', 1)))}</small></article>"
            for item in findings[:12]
        )
        or "<article class='risk'><b>LOW</b><span>No high-confidence security findings.</span><small>Scanner output</small></article>"
    )
    recommendations = "".join(
        f"<li>{escape(str(item))}</li>" for item in _html_recommendations(summary, report_title)
    )
    evidence_rows = "".join(
        f"<article class='evidence'><b>{escape(str(citation.get('file', citation.get('path', 'evidence'))))}</b><span>{escape(str(citation.get('evidence', citation.get('reason', 'Repository evidence'))))}</span></article>"
        for item in evidence.values()
        for citation in item.get("citations", [])[:3]
    )
    return (
        f"<!doctype html><html><head><meta charset='utf-8'><title>RepoMind {escape(report_title)}</title>"
        "<style>"
        "@page{size:A4;margin:22mm}body{font-family:Inter,Arial,sans-serif;background:#f8fafc;color:#0f172a;margin:0}"
        ".cover{padding:40px;border-radius:28px;background:linear-gradient(135deg,#020617,#0f766e);color:white}"
        ".eyebrow{letter-spacing:.22em;text-transform:uppercase;color:#a5f3fc;font-size:11px;font-weight:700}"
        "h1{font-size:42px;line-height:1.05;margin:14px 0}h2{font-size:18px;margin-top:28px}.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin:22px 0}"
        ".metric,.score,.risk{background:white;border:1px solid #e2e8f0;border-radius:16px;padding:16px;box-shadow:0 10px 30px rgba(15,23,42,.06)}"
        ".metric span{display:block;color:#64748b;font-size:11px;text-transform:uppercase;letter-spacing:.12em}.metric strong{display:block;font-size:26px;margin-top:8px}"
        ".bar{height:9px;background:#e2e8f0;border-radius:999px;overflow:hidden}.bar i{display:block;height:100%;background:linear-gradient(90deg,#06b6d4,#22c55e,#facc15)}"
        ".risks{display:grid;grid-template-columns:1fr 1fr;gap:10px}.risk b{color:#be123c;margin-right:8px}.risk small{display:block;color:#64748b;margin-top:8px}"
        ".memo{background:white;border:1px solid #e2e8f0;border-radius:18px;padding:20px;margin-top:18px}.memo li{margin:8px 0}.evidence{border-left:4px solid #0891b2;background:#ecfeff;margin:8px 0;padding:10px 12px}.evidence span{display:block;color:#334155;font-size:12px;margin-top:4px}"
        "</style></head><body>"
        "<section class='cover'><p class='eyebrow'>RepoMindAI CTO Intelligence Platform</p>"
        f"<h1>{escape(str(summary.get('repository', {}).get('name', 'Repository')))} {escape(report_title)}</h1>"
        f"<p>{escape(summary.get('architecture', {}).get('summary', 'No architecture summary available.'))}</p></section>"
        f"<h2>Board Scorecard</h2><div class='grid'>{rows}</div>"
        f"<h2>Explainable Scores</h2>{scorecards}"
        f"<h2>Risk Register</h2><div class='risks'>{risk_rows}</div>"
        f"<section class='memo'><h2>Recommendations</h2><ol>{recommendations}</ol></section>"
        f"<section class='memo'><h2>Evidence and Citations</h2>{evidence_rows or '<p>No score citations available.</p>'}</section>"
        "</body></html>"
    )


def _pdf_summary(summary: dict[str, Any], report_title: str = "Executive Summary") -> bytes:
    html = _html_summary(summary, report_title)
    try:
        from weasyprint import HTML

        return HTML(string=html).write_pdf()
    except Exception:
        pass
    lines = [
        "RepoMindAI CTO Intelligence Platform",
        f"Investor-Grade {report_title}",
        f"Repository: {summary.get('repository', {}).get('name')}",
        f"Files: {summary.get('statistics', {}).get('files')}",
        f"Security: {summary.get('scores', {}).get('security')}",
        f"Maintainability: {summary.get('scores', {}).get('maintainability')}",
        f"Production readiness: {summary.get('scores', {}).get('production_readiness')}",
        f"Top findings: {len(summary.get('security', {}).get('findings', []))}",
        "Generated from repository evidence, graph signals, security findings, and score breakdowns.",
    ]
    stream = (
        "BT /F1 12 Tf 72 760 Td "
        + " Tj 0 -18 Td ".join(f"({_pdf_escape(line)})" for line in lines)
        + " Tj ET"
    )
    objects = [
        "1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj",
        "2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj",
        "3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >> endobj",
        "4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj",
        f"5 0 obj << /Length {len(stream.encode())} >> stream\n{stream}\nendstream endobj",
    ]
    body = "%PDF-1.4\n" + "\n".join(objects) + "\ntrailer << /Root 1 0 R >>\n%%EOF\n"
    return body.encode()


def _pdf_escape(value: str) -> str:
    return str(value).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _html_recommendations(summary: dict[str, Any], report_title: str) -> list[str]:
    findings = summary.get("security", {}).get("findings", [])
    evidence = summary.get("score_evidence", {})
    recommendations = []
    if findings:
        recommendations.append(
            "Remediate high-severity security findings before expanding production exposure."
        )
    if summary.get("scores", {}).get("maintainability", 100) < 75:
        recommendations.append(
            "Prioritize maintainability work in files cited by technical debt and architecture evidence."
        )
    if summary.get("scores", {}).get("production_readiness", 100) < 75:
        recommendations.append(
            "Close deployment, testing, and operational readiness gaps before enterprise rollout."
        )
    if "Investor" in report_title or "Due Diligence" in report_title:
        recommendations.append(
            "Use the cited score evidence to drive investor diligence questions and remediation timing."
        )
    if "Architecture" in report_title or "CTO" in report_title:
        recommendations.append(
            "Review ownership, API, data, and dependency concentration before major roadmap commitments."
        )
    if evidence:
        recommendations.append(
            "Validate every executive claim against the attached score citations and source files."
        )
    return recommendations or [
        "No critical remediation signal was detected from the analyzed repository evidence."
    ]


def _sarif_level(severity: str) -> str:
    return {"critical": "error", "high": "error", "medium": "warning", "low": "note"}.get(
        str(severity).lower(), "warning"
    )


def _sarif_security_severity(severity: str) -> str:
    return {"critical": "9.5", "high": "8.0", "medium": "5.0", "low": "2.0"}.get(
        str(severity).lower(), "5.0"
    )


def _number(value: Any) -> float:
    return float(value) if isinstance(value, (int, float)) else 0.0


def _score_details(score_name: str, summary: dict[str, Any]) -> str:
    detail = summary.get("scores", {}).get("details", {}).get(score_name)
    if not detail:
        return ""
    positives = "\n".join(f"- {item}" for item in detail.get("positive_contributors", []))
    negatives = "\n".join(f"- {item}" for item in detail.get("negative_contributors", []))
    return (
        "## Score Evidence\n\n"
        f"Calculation: {detail.get('calculation')}\n\n"
        f"Positive contributors:\n\n{positives or '- None'}\n\n"
        f"Negative contributors:\n\n{negatives or '- None'}\n\n"
    )


def _review_list(title: str, items: list[Any]) -> str:
    rows = "\n".join(f"- {_format_item(item)}" for item in items[:12]) or "- No signal detected."
    return f"### {title}\n\n{rows}\n\n"


def _format_item(item: Any) -> str:
    if isinstance(item, dict):
        return ", ".join(f"{key}: {value}" for key, value in item.items())
    return str(item)


def _ai_section(title: str, generated: str) -> str:
    return f"## {title}\n\n{generated}\n\n"


def _synthesize_reports(
    summary: dict[str, Any], cancel_check: CancelCheck | None = None
) -> dict[str, str]:
    model = local_model()
    return {
        "overview": _safe_generate(
            model,
            synthesis_prompt("repository overview and project status", summary),
            180,
            summary,
            cancel_check,
        ),
        "architecture": _safe_generate(
            model,
            synthesis_prompt("architecture explanation with file-level evidence", summary),
            220,
            summary,
            cancel_check,
        ),
        "technical": _safe_generate(
            model,
            synthesis_prompt("security, technical debt, and roadmap", summary),
            220,
            summary,
            cancel_check,
        ),
        "recruiter": _safe_generate(
            model,
            report_prompt("recruiter review with evidence and confidence", summary),
            220,
            summary,
            cancel_check,
        ),
        "cto": _safe_generate(
            model,
            report_prompt("CTO review with evidence, risk, and confidence", summary),
            220,
            summary,
            cancel_check,
        ),
    }


def _safe_generate(
    model: Any,
    prompt: str,
    max_tokens: int,
    summary: dict[str, Any],
    cancel_check: CancelCheck | None = None,
) -> str:
    _checkpoint(cancel_check)
    try:
        generated = model.generate(prompt, max_tokens)
        _checkpoint(cancel_check)
        return generated
    except RuntimeError as exc:
        return _evidence_only_model_fallback(summary, exc)


def _evidence_only_model_fallback(summary: dict[str, Any], exc: RuntimeError) -> str:
    return (
        "Local model generation was unavailable, so this section uses deterministic repository evidence only.\n\n"
        f"- Model status: {exc}\n"
        f"- Architecture style: {summary['architecture'].get('style')}\n"
        f"- Files analyzed: {summary['statistics'].get('files')}\n"
        f"- Primary language: {summary['languages'].get('primary')}\n"
        f"- Security score: {summary['scores'].get('security')}\n"
        f"- Maintainability score: {summary['scores'].get('maintainability')}\n"
    )


def _redacted_summary(summary: dict[str, Any]) -> dict[str, Any]:
    payload = json.loads(_json_dumps(summary))
    for finding in payload.get("security", {}).get("findings", []):
        if "message" in finding:
            finding["message"] = redact_text(str(finding["message"]))
    for todo in payload.get("technical_debt", {}).get("todos", []):
        if "text" in todo:
            todo["text"] = redact_text(str(todo["text"]))
    return payload


def _json_dumps(payload: Any, **kwargs: Any) -> str:
    return json.dumps(payload, default=_json_default, **kwargs)


def _json_default(value: Any) -> str:
    if isinstance(value, datetime | date):
        return value.isoformat()
    return str(value)


def _evidence_files(summary: dict[str, Any]) -> str:
    files: list[str] = []
    files.extend(summary["architecture"].get("important_files", [])[:6])
    files.extend(summary["architecture"].get("route_files", [])[:6])
    files.extend(
        item.get("path") for item in summary["security"].get("findings", [])[:6] if item.get("path")
    )
    unique = [item for index, item in enumerate(files) if item and item not in files[:index]]
    if not unique:
        return ""
    return "\nEvidence files:\n" + "\n".join(f"- `{path}`" for path in unique[:12]) + "\n"


def _checkpoint(cancel_check: CancelCheck | None) -> None:
    if cancel_check and cancel_check():
        from repomind.analysis.analyzer import AnalysisCancelled

        raise AnalysisCancelled("Analysis cancelled.")
