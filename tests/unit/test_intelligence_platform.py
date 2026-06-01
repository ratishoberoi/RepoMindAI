from __future__ import annotations

from repomind.intelligence.acquisition import build_acquisition_intelligence
from repomind.intelligence.architecture_explorer import build_architecture_explorer
from repomind.intelligence.executive_reports import build_executive_report_pack
from repomind.intelligence.knowledge_graph import build_repository_knowledge_graph
from repomind.intelligence.portfolio import build_multi_repository_intelligence


def sample_summary() -> dict:
    files = [
        {"relative_path": "frontend/pages/login.tsx", "language": "TypeScript", "size": 1200},
        {"relative_path": "backend/api/auth.py", "language": "Python", "size": 1800},
        {"relative_path": "backend/db/models.py", "language": "Python", "size": 900},
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


def test_portfolio_intelligence_v2_detects_overlap() -> None:
    repo = {"id": "repo-1", "name": "sample", "summary": sample_summary()}
    other = {"id": "repo-2", "name": "sample-copy", "summary": sample_summary()}
    portfolio = build_multi_repository_intelligence([repo, other])

    assert portfolio["dependency_overlap_graph"]["edges"]
    assert portfolio["shared_vulnerabilities"]
    assert portfolio["framework_concentration_risk"][0]["framework"] == "FastAPI"
    assert portfolio["portfolio_remediation_center"]
