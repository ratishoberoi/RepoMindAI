from __future__ import annotations

import copy

from repomind.core.config import get_settings
from repomind.intelligence.acquisition import build_acquisition_intelligence
from repomind.intelligence.architecture_explorer import build_architecture_explorer
from repomind.intelligence.drift import detect_architecture_drift
from repomind.intelligence.evidence import build_score_evidence
from repomind.intelligence.executive_reports import build_executive_report_pack
from repomind.intelligence.graph_store import build_graph_projection, query_repository_graph
from repomind.intelligence.knowledge_graph import build_repository_knowledge_graph
from repomind.intelligence.portfolio import build_multi_repository_intelligence
from repomind.intelligence.pr_risk import analyze_pr_risk
from repomind.reports.generator import generate_reports
from repomind.security.scanner import _finding


def sample_summary() -> dict:
    files = [
        {"relative_path": "frontend/pages/login.tsx", "language": "TypeScript", "size": 1200},
        {"relative_path": "backend/api/auth.py", "language": "Python", "size": 1800},
        {"relative_path": "backend/db/models.py", "language": "Python", "size": 900},
        {"relative_path": "tests/test_auth.py", "language": "Python", "size": 450},
        {"relative_path": ".github/workflows/ci.yml", "language": "YAML", "size": 300},
        {"relative_path": "README.md", "language": "Markdown", "size": 500},
    ]
    parsed = [
        {
            "relative_path": "backend/api/auth.py",
            "routes": [{"method": "POST", "path": "/login", "handler": "login", "line": 12}],
            "database_models": [],
            "env_vars": ["API_TOKEN"],
            "classes": [],
            "functions": [{"name": "login", "line": 12}],
            "methods": [],
        },
        {
            "relative_path": "backend/db/models.py",
            "routes": [],
            "database_models": [{"name": "User", "orm": "SQLAlchemy", "line": 4}],
            "env_vars": [],
            "classes": [{"name": "User", "line": 4}],
            "functions": [],
            "methods": [],
        },
    ]
    graph = {
        "edges": [
            {
                "source": "frontend/pages/login.tsx",
                "target": "backend/api/auth.py",
                "relation": "calls",
            },
            {
                "source": "backend/api/auth.py",
                "target": "backend/db/models.py",
                "relation": "imports",
            },
        ],
        "important_nodes": [{"id": "backend/api/auth.py"}],
    }
    security = {
        "findings": [
            {
                "severity": "high",
                "message": "hardcoded token",
                "path": "backend/api/auth.py",
                "line": 14,
                "rule_id": "secret",
            }
        ],
        "severity_counts": {"critical": 0, "high": 1, "medium": 0, "low": 0},
    }
    kg = build_repository_knowledge_graph(files, parsed, graph, security)
    return {
        "repository": {"id": "repo-1", "name": "sample", "path": "/tmp/sample", "source": "local"},
        "statistics": {"files": len(files), "routes": 1, "database_models": 1, "indexed_chunks": 4},
        "languages": {"primary": "Python"},
        "stack": {
            "frameworks": ["FastAPI"],
            "package_managers": ["pip"],
            "ci_cd": ["GitHub Actions"],
            "docker": True,
        },
        "files": files,
        "parsed": parsed,
        "graph": graph,
        "security": security,
        "technical_debt": {"items": [], "todos": [], "score": 82},
        "scores": {"cto": 76, "security": 68, "maintainability": 82, "production_readiness": 74},
        "architecture": {
            "style": "API service",
            "summary": "Sample API service.",
            "important_files": ["backend/api/auth.py"],
            "components": [{"name": "backend", "role": "API surface", "file_count": 2}],
        },
        "knowledge_graph": kg,
    }


def test_architecture_explorer_traces_login_flow() -> None:
    explorer = build_architecture_explorer(sample_summary())

    login = next(flow for flow in explorer["request_flows"] if flow["id"] == "login")
    assert login["entry_points"]
    assert "sequenceDiagram" in login["sequence_diagram"]
    assert "ONBOARDING" in explorer["onboarding_markdown"]
    assert explorer["architecture_review"]["coupling_analysis"]["level"]
    assert explorer["ai_architect_review"]
    assert explorer["ai_architect_review"][0]["confidence"] > 0
    assert explorer["ai_architect_review"][0]["evidence"]


def test_score_evidence_explains_scores_with_citations() -> None:
    evidence = build_score_evidence(sample_summary())

    assert {"health", "security", "architecture", "investment", "acquisition", "risk"} <= set(
        evidence
    )
    security = evidence["security"]
    assert security["calculation"]
    assert security["factors"]
    assert security["confidence"] > 0
    assert any(citation["file"] == "backend/api/auth.py" for citation in security["citations"])


def test_knowledge_graph_30_adds_clusters_and_insights() -> None:
    graph = sample_summary()["knowledge_graph"]

    assert graph["clusters"]
    assert graph["insights"]
    assert "critical_path" in graph


def test_acquisition_and_executive_reports_are_evidence_backed() -> None:
    summary = sample_summary()
    acquisition = build_acquisition_intelligence(summary)
    reports = build_executive_report_pack(summary)

    assert acquisition["ai_verdict"] in {
        "Strong Acquisition Candidate",
        "Moderate Risk Candidate",
        "High Risk Candidate",
    }
    assert acquisition["red_flags"]
    assert reports["board_report"]["scorecard"]["security_posture"] == 68
    assert reports["engineering_roadmap"]["timeline"]


def test_pr_risk_packet_includes_blast_radius_and_deployment_risk() -> None:
    result = analyze_pr_risk(
        sample_summary(),
        ["backend/api/auth.py", "frontend/pages/login.tsx"],
        title="Auth hardening",
    )

    assert result["risk_score"] > 0
    assert result["blast_radius"]["file_count"] == 2
    assert result["deployment_risk"]["level"] in {"low", "medium", "high", "critical"}
    assert result["pr_review_packet"]["recommended_tests"]
    assert result["affected_services"]
    assert result["recommended_reviewers"]
    assert result["test_impact_analysis"]["coverage_confidence"]
    assert result["release_gate_recommendation"]
    assert result["findings"]
    assert result["review_complexity"]["score"] > 0
    assert result["regression_probability"]["score"] > 0
    assert result["pr_impact_timeline"]


def test_pr_risk_uses_github_pr_evidence(monkeypatch) -> None:
    monkeypatch.setattr(
        "repomind.intelligence.pr_risk.fetch_pull_request_intelligence",
        lambda repository, pr_number, pr_url: {
            "available": True,
            "repository": "org/repo",
            "pr_number": 42,
            "title": "Secure auth",
            "description": "Auth hardening",
            "additions": 120,
            "deletions": 20,
            "changed_files": [
                {"path": "backend/api/auth.py", "additions": 80, "deletions": 10, "changes": 90},
                {"path": "package.json", "additions": 40, "deletions": 10, "changes": 50},
            ],
            "commits": [{"sha": "abc123", "message": "secure auth", "author": "dev"}],
            "reviewers": [{"type": "user", "login": "security-reviewer"}],
            "comments": {"review": [{"body": "check auth"}]},
            "checks": [{"name": "test", "conclusion": "success"}],
            "workflows": [{"name": "ci", "conclusion": "success"}],
        },
    )

    result = analyze_pr_risk(sample_summary(), [], repository="org/repo", pr_number=42)

    assert result["changed_files_source"] == "github_api"
    assert result["github_pr"]["available"] is True
    assert result["dependency_changes"]
    assert result["api_changes"]
    assert result["security_sensitive_changes"]
    assert result["ownership_routing"]


def test_drift_report_detects_changed_services_dependencies_and_security() -> None:
    baseline = sample_summary()
    current = copy.deepcopy(baseline)
    current["stack"]["frameworks"].append("Celery")
    current["knowledge_graph"]["domains"].append(
        {
            "name": "workers",
            "role": "Background processing",
            "file_count": 4,
            "routes": 0,
            "data_models": 0,
        }
    )

    result = detect_architecture_drift(
        baseline, current, compare_type="branch", baseline_ref="main", target_ref="feature"
    )

    assert "workers" in result["new_services"]
    assert "Celery" in result["frameworks_added"]
    assert result["timeline"]
    assert result["visual_diff"]["nodes"]
    assert result["dependency_surface_changes"]["added"]
    assert "ownership_changes" in result
    assert "security_posture_changes" in result
    assert result["drift_report"]


def test_security_findings_include_taxonomy_and_remediation() -> None:
    finding = _finding("hardcoded-secret", "high", "auth.py", 5, "Hardcoded secret")

    assert finding["owasp"] == "A02:2021-Cryptographic Failures"
    assert finding["cwe"] == "CWE-798"
    assert finding["cvss"] >= 8
    assert finding["exploitability"]
    assert finding["business_impact"]
    assert finding["impact"]
    assert finding["remediation"]


def test_portfolio_intelligence_v2_detects_overlap() -> None:
    repo = {"id": "repo-1", "name": "sample", "summary": sample_summary()}
    other = {"id": "repo-2", "name": "sample-copy", "summary": sample_summary()}
    portfolio = build_multi_repository_intelligence([repo, other])

    assert portfolio["dependency_overlap_graph"]["edges"]
    assert portfolio["shared_vulnerabilities"]
    assert portfolio["framework_concentration_risk"][0]["framework"] == "FastAPI"
    assert portfolio["team_ownership"]
    assert portfolio["service_ownership"]
    assert portfolio["bus_factor"]["portfolio_min"] >= 1
    assert portfolio["ownership_graph"]["nodes"]
    assert portfolio["portfolio_remediation_center"]


def test_graph_projection_supports_repository_queries() -> None:
    summary = sample_summary()
    projection = build_graph_projection(summary)
    query = query_repository_graph(summary, "ownership")

    assert projection["metrics"]["node_count"] > 0
    assert projection["metrics"]["graph_density"] >= 0
    assert any(node["kind"] == "api" for node in projection["nodes"])
    assert any(node["kind"] == "test" for node in projection["nodes"])
    assert any(node["kind"] == "deployment" for node in projection["nodes"])
    assert any(edge["relation"] == "EXPOSES" for edge in projection["edges"])
    assert projection["edges"]
    assert query["query"] == "ownership"
    assert query["nodes"]
    traversal = query_repository_graph(
        summary, "blast_radius", source="backend/api/auth.py", depth=2
    )
    assert traversal["nodes"]


def test_report_generation_creates_enterprise_aliases(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("REPOMIND_REPORTS_DIR", str(tmp_path / "reports"))
    monkeypatch.setenv("REPOMIND_EXPORTS_DIR", str(tmp_path / "exports"))
    monkeypatch.setenv("REPOMIND_DATA_DIR", str(tmp_path / "data"))
    get_settings.cache_clear()
    summary = sample_summary()
    summary["score_evidence"] = build_score_evidence(summary)
    repo = {"id": "repo-1", "name": "sample"}

    try:
        paths = generate_reports(repo, summary)

        for name in (
            "README_REPORT.md",
            "ARCHITECTURE_REPORT.md",
            "CTO_REPORT.md",
            "INVESTOR_REPORT.md",
            "DUE_DILIGENCE_REPORT.md",
            "ROADMAP_REPORT.md",
            "EXECUTIVE_SUMMARY.md",
        ):
            assert name in paths
            assert "sample" in open(paths[name], encoding="utf-8").read()
        for name in ("CTO_REPORT.html", "INVESTOR_REPORT.pdf", "SECURITY_REPORT.html"):
            assert name in paths
    finally:
        get_settings.cache_clear()
