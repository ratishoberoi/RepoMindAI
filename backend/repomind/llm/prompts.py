from __future__ import annotations


def report_prompt(report_type: str, summary: dict) -> str:
    architecture = summary["architecture"]
    compact_architecture = {
        "style": architecture.get("style"),
        "important_files": architecture.get("important_files", [])[:8],
        "route_files": architecture.get("route_files", [])[:8],
        "summary": architecture.get("summary"),
    }
    compact_stack = {
        "frameworks": summary["stack"].get("frameworks", [])[:10],
        "package_managers": summary["stack"].get("package_managers", [])[:6],
        "build_tools": summary["stack"].get("build_tools", [])[:8],
        "ci_cd": summary["stack"].get("ci_cd", [])[:6],
        "docker": summary["stack"].get("docker"),
    }
    return (
        f"Create a {report_type} report from this repository analysis. "
        "Use concrete evidence, cite exact file paths, state confidence, and avoid generic advice.\n\n"
        f"Repository: {summary['repository']['name']}\n"
        f"Languages: {summary['languages']}\n"
        f"Stack: {compact_stack}\n"
        f"Scores: {summary['scores']}\n"
        f"Architecture: {compact_architecture}\n"
        f"Security findings: {summary['security']['severity_counts']}\n"
    )


def evidence_pack(summary: dict) -> dict:
    architecture = summary["architecture"]
    return {
        "repository": summary["repository"]["name"],
        "statistics": summary["statistics"],
        "languages": summary["languages"],
        "stack": {
            "frameworks": summary["stack"].get("frameworks", [])[:12],
            "package_managers": summary["stack"].get("package_managers", [])[:8],
            "build_tools": summary["stack"].get("build_tools", [])[:10],
            "ci_cd": summary["stack"].get("ci_cd", [])[:8],
        },
        "scores": {key: value for key, value in summary["scores"].items() if key != "details"},
        "score_details": summary["scores"].get("details", {}),
        "architecture": {
            "style": architecture.get("style"),
            "summary": architecture.get("summary"),
            "important_files": architecture.get("important_files", [])[:12],
            "route_files": architecture.get("route_files", [])[:12],
            "database_model_files": architecture.get("database_model_files", [])[:12],
            "components": architecture.get("components", [])[:8],
        },
        "security": {
            "severity_counts": summary["security"].get("severity_counts", {}),
            "scanner_status": summary["security"].get("scanner_status", {}),
            "findings": summary["security"].get("findings", [])[:12],
        },
        "technical_debt": {
            "score": summary["technical_debt"].get("score"),
            "items": summary["technical_debt"].get("items", [])[:12],
            "todos": summary["technical_debt"].get("todos", [])[:10],
            "large_files": summary["technical_debt"].get("large_files", [])[:8],
        },
        "performance": summary.get("performance", {}),
    }


def synthesis_prompt(section: str, summary: dict) -> str:
    import json

    return (
        f"Write the {section} section for a repository intelligence report.\n"
        "Rules:\n"
        "- Use only the provided evidence.\n"
        "- Include exact file references from evidence when making claims.\n"
        "- Include a confidence score from 0.0 to 1.0 and explain why.\n"
        "- Avoid generic LLM filler; make tradeoffs and risks specific.\n"
        "- Use concise Markdown headings and bullets.\n\n"
        f"Evidence JSON:\n{json.dumps(evidence_pack(summary), indent=2)}"
    )
