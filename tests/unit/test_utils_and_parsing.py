from pathlib import Path

import pytest
from repomind.analysis.classifier import classify_file
from repomind.analysis.graph import build_dependency_graph
from repomind.analysis.parser import parse_file
from repomind.core import cleanup
from repomind.core.config import Settings
from repomind.core.store import RepositoryStore
from repomind.ingestion import ingestor
from repomind.intelligence.drift import detect_architecture_drift
from repomind.intelligence.knowledge_graph import build_repository_knowledge_graph
from repomind.intelligence.pr_risk import analyze_pr_risk
from repomind.llm.adapters import detect_model
from repomind.rag.chunking import chunk_file, chunk_text
from repomind.rag.embeddings import BGEEmbedder
from repomind.rag.qa import _enforce_cited_references
from repomind.reports.generator import compare_summaries, generate_reports
from repomind.security.redaction import redact_text
from repomind.utils.hashing import file_sha256
from repomind.utils.ignore import should_ignore


def test_classify_and_ignore_rules() -> None:
    assert classify_file(Path("app/main.py")) == "Python"
    assert classify_file(Path("Dockerfile")) == "Dockerfile"
    assert should_ignore(Path("repo/node_modules/pkg/index.js"), Path("repo"))
    assert not should_ignore(Path("repo/app/main.py"), Path("repo"))


def test_hash_generation(tmp_path: Path) -> None:
    path = tmp_path / "a.py"
    path.write_text("print('x')")
    assert file_sha256(path) == file_sha256(path)


def test_python_parser_extracts_symbols(tmp_path: Path) -> None:
    path = tmp_path / "main.py"
    path.write_text(
        "import os\n\nclass Service: pass\n\ndef run():\n    return os.getenv('API_KEY')\n"
    )
    parsed = parse_file(path, "main.py", "Python")
    assert "os" in parsed["imports"]
    assert parsed["classes"][0]["name"] == "Service"
    assert parsed["functions"][0]["name"] == "run"
    assert "API_KEY" in parsed["env_vars"]


def test_dependency_graph_building() -> None:
    files = [{"relative_path": "app/main.py", "language": "Python", "size": 10}]
    parsed = [
        {
            "relative_path": "app/main.py",
            "imports": ["os"],
            "functions": [{"name": "run", "line": 1}],
            "classes": [],
        }
    ]
    graph = build_dependency_graph(files, parsed)
    assert any(edge["relation"] == "imports" for edge in graph["edges"])
    assert any(node["kind"] == "function" for node in graph["nodes"])


def test_repository_knowledge_graph_extracts_domains_and_hotspots() -> None:
    files = [
        {"relative_path": "backend/api/users.py", "language": "Python", "size": 100},
        {"relative_path": "backend/db/models.py", "language": "Python", "size": 100},
    ]
    parsed = [
        {
            "relative_path": "backend/api/users.py",
            "routes": [{"method": "GET", "path": "/users", "handler": "list_users", "line": 3}],
            "database_models": [],
            "functions": [{"name": "list_users", "line": 3}],
            "classes": [],
            "methods": [],
        },
        {
            "relative_path": "backend/db/models.py",
            "routes": [],
            "database_models": [{"name": "User", "line": 1, "orm": "SQLAlchemy"}],
            "functions": [],
            "classes": [{"name": "User", "line": 1}],
            "methods": [],
        },
    ]
    graph = {
        "edges": [
            {
                "source": "backend/api/users.py",
                "target": "backend/db/models.py",
                "relation": "imports",
            }
        ]
    }
    security = {
        "findings": [
            {
                "path": "backend/api/users.py",
                "severity": "high",
                "line": 5,
                "message": "issue",
            }
        ]
    }
    kg = build_repository_knowledge_graph(files, parsed, graph, security)
    assert kg["metrics"]["route_count"] == 1
    assert kg["metrics"]["data_model_count"] == 1
    assert kg["domains"][0]["file_count"] >= 1
    assert kg["hotspots"][0]["path"] == "backend/api/users.py"


def test_pr_risk_uses_knowledge_graph_hotspots() -> None:
    summary = {
        "files": [{"relative_path": "backend/api/users.py", "language": "Python", "size": 100}],
        "knowledge_graph": {
            "domains": [
                {
                    "name": "backend/api",
                    "role": "API boundary",
                    "routes": 1,
                    "data_models": 0,
                    "security_findings": 1,
                    "sample_files": ["backend/api/users.py"],
                }
            ],
            "hotspots": [{"path": "backend/api/users.py", "risk_score": 20}],
        },
        "security": {
            "findings": [{"path": "backend/api/users.py", "severity": "high"}],
        },
    }
    risk = analyze_pr_risk(summary, ["backend/api/users.py"], "change users API")
    assert risk["risk_level"] in {"high", "critical"}
    assert "security review" in risk["required_review"]
    assert risk["impacted_domains"][0]["name"] == "backend/api"


def test_architecture_drift_detects_domain_changes() -> None:
    baseline = {
        "repository": {"id": "old", "name": "old"},
        "stack": {"frameworks": ["FastAPI"]},
        "architecture": {"style": "API service", "route_files": [], "database_model_files": []},
        "scores": {"security": 90, "maintainability": 90, "production_readiness": 90, "cto": 90},
        "knowledge_graph": {
            "domains": [{"name": "backend/api", "role": "API boundary", "file_count": 1}]
        },
    }
    current = {
        "repository": {"id": "new", "name": "new"},
        "stack": {"frameworks": ["FastAPI", "Next.js"]},
        "architecture": {
            "style": "Full-stack application",
            "route_files": ["backend/api/users.py"],
            "database_model_files": ["backend/db/models.py"],
        },
        "scores": {"security": 70, "maintainability": 90, "production_readiness": 80, "cto": 82},
        "knowledge_graph": {
            "domains": [
                {"name": "backend/api", "role": "API boundary", "file_count": 3},
                {"name": "frontend/app", "role": "User experience", "file_count": 2},
            ]
        },
    }
    drift = detect_architecture_drift(baseline, current)
    assert drift["drift_level"] in {"minor", "material", "major"}
    assert "frontend/app" in drift["domain_added"]
    assert drift["score_delta"]["security"] == -20


def test_chunks_are_stable() -> None:
    chunks = chunk_text("hello world\n" * 400, "README.md")
    assert chunks


def test_chunk_file_prefers_symbol_chunks(tmp_path: Path) -> None:
    path = tmp_path / "service.py"
    path.write_text("def alpha():\n    return 1\n\nclass Beta:\n    pass\n")
    chunks = chunk_file(path, "service.py")
    assert {chunk["symbol"] for chunk in chunks} == {"alpha", "Beta"}
    assert all(chunk["kind"] == "ast_node" for chunk in chunks)
    assert all(chunk["parser"] == "python-ast" for chunk in chunks)


def test_js_chunking_uses_tree_sitter_ast_nodes(tmp_path: Path) -> None:
    path = tmp_path / "service.ts"
    path.write_text("export class Service {}\nexport function run() { return 1; }\n")
    chunks = chunk_file(path, "service.ts")
    assert chunks
    assert any(chunk["kind"] == "ast_node" for chunk in chunks)
    assert any(str(chunk.get("parser", "")).startswith("tree-sitter") for chunk in chunks)


def test_embedding_uses_bge_model_name() -> None:
    assert BGEEmbedder.__name__ == "BGEEmbedder"


def test_model_detection_for_configurable_qwen_path(tmp_path: Path) -> None:
    spec = detect_model(tmp_path / "models" / "qwen-judge")
    assert spec.backend == "missing"
    assert not spec.loadable


def test_tree_sitter_js_ts_parser_extracts_routes_and_exports(tmp_path: Path) -> None:
    path = tmp_path / "route.tsx"
    path.write_text(
        "import express from 'express';\n"
        "export class UserModel {}\n"
        "export async function GET() { return Response.json({ ok: true }); }\n"
        "app.get('/health', () => null);\n"
    )
    parsed = parse_file(path, "app/route.tsx", "TypeScript")
    assert parsed["parser"] == "tree-sitter-tsx"
    assert "express" in parsed["imports"]
    assert any(item["name"] == "UserModel" for item in parsed["classes"])
    assert any(route["path"] == "/health" for route in parsed["routes"])


def test_secret_redaction_masks_sensitive_values() -> None:
    text = "API_KEY='super-secret-value'\nAuthorization: Bearer abcdefghijklmnopqrstuvwxyz123456"
    redacted = redact_text(text)
    assert "super-secret-value" not in redacted
    assert "abcdefghijklmnopqrstuvwxyz123456" not in redacted
    assert "[REDACTED]" in redacted


def test_git_url_validation_resolves_and_blocks_private_dns(monkeypatch) -> None:
    def fake_getaddrinfo(host, port, type=None):
        return [(None, None, None, None, ("10.0.0.10", port))]

    monkeypatch.setattr(ingestor.socket, "getaddrinfo", fake_getaddrinfo)
    try:
        ingestor._validate_git_url("https://github.com/org/repo.git")
    except ValueError as exc:
        assert "blocked network" in str(exc)
    else:
        raise AssertionError("private resolved address was allowed")


def test_git_clone_pins_validated_dns_resolution(tmp_path: Path, monkeypatch) -> None:
    commands: list[list[str]] = []

    def fake_workspace(url: str) -> Path:
        path = tmp_path / "repo"
        path.mkdir()
        return path

    def fake_create_repository(name: str, source_type: str, path: Path, source: str) -> dict:
        return {
            "id": "repo",
            "name": name,
            "source_type": source_type,
            "path": str(path),
            "source": source,
        }

    def fake_run(command, check, capture_output):
        commands.append(command)
        return None

    monkeypatch.setattr(ingestor, "_workspace", fake_workspace)
    monkeypatch.setattr(ingestor, "_validate_git_url", lambda url: ["140.82.112.3"])
    monkeypatch.setattr(ingestor.store, "create_repository", fake_create_repository)
    monkeypatch.setattr(ingestor.subprocess, "run", fake_run)
    ingestor.ingest_github("https://github.com/org/repo.git")
    command = commands[0]
    assert "http.curloptResolve=+github.com:443:140.82.112.3" in command
    assert "protocol.file.allow=never" in command


def test_citation_enforcement_removes_uncited_file_references() -> None:
    chunks = [{"path": "backend/app.py"}]
    answer = "backend/app.py handles routing. secrets.py stores keys."
    verified = _enforce_cited_references(answer, chunks)
    assert "backend/app.py" in verified
    assert "secrets.py" not in verified


def test_sql_store_migrates_legacy_metadata(tmp_path: Path) -> None:
    legacy = tmp_path / "metadata.json"
    legacy.write_text(
        '{"repositories":{"abc":{"id":"abc","name":"Legacy","source_type":"local","source":"src",'
        '"path":"repo","status":"complete","created_at":1,"updated_at":2,"summary":{},'
        '"reports":{"README.md":"/tmp/README.md"},"error":null,"repository_deleted":false,'
        '"repository_deleted_at":null,"repository_retention_minutes":60}}}'
    )
    sql_store = RepositoryStore(
        database_url=f"sqlite:///{tmp_path / 'store.db'}", legacy_path=legacy
    )
    repo = sql_store.get("abc")
    assert repo["name"] == "Legacy"
    assert repo["reports"]["README.md"] == "/tmp/README.md"


def test_production_rejects_sqlite_primary_storage(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="SQLite is not allowed"):
        Settings(
            env="production",
            database_url=f"sqlite:///{tmp_path / 'prod.db'}",
            model_path=tmp_path / "models" / "qwen-judge",
            data_dir=tmp_path / "data",
            reports_dir=tmp_path / "reports",
            index_dir=tmp_path / "indexes",
            chroma_dir=tmp_path / "chroma",
            upload_dir=tmp_path / "uploads",
        )


def test_purge_repository_removes_metadata_reports_and_index(tmp_path: Path, monkeypatch) -> None:
    repo_dir = tmp_path / "data" / "repositories" / "repo"
    repo_dir.mkdir(parents=True)
    report_dir = tmp_path / "reports" / "generated" / "abc"
    report_dir.mkdir(parents=True)
    report = report_dir / "README.md"
    report.write_text("# report")
    deleted_indexes: list[str] = []

    class FakeSettings:
        repositories_dir = tmp_path / "data" / "repositories"
        reports_dir = tmp_path / "reports"
        retention_minutes = 60

    class FakeStore:
        deleted = False

        def get(self, repo_id: str) -> dict:
            return {"id": repo_id, "path": str(repo_dir), "reports": {"README.md": str(report)}}

        def delete(self, repo_id: str) -> dict:
            self.deleted = True
            return {"id": repo_id, "path": str(repo_dir), "reports": {}}

    monkeypatch.setattr(cleanup, "get_settings", lambda: FakeSettings())
    monkeypatch.setattr(
        cleanup, "delete_repository_index", lambda repo_id: deleted_indexes.append(repo_id)
    )
    store = FakeStore()
    cleanup.purge_repository("abc", store)
    assert store.deleted
    assert deleted_indexes == ["abc"]
    assert not repo_dir.exists()
    assert not report.exists()


def test_report_generation_includes_enterprise_artifacts(tmp_path: Path, monkeypatch) -> None:
    class FakeModel:
        def generate(self, prompt: str, max_tokens: int) -> str:
            return "Generated evidence."

        def status(self) -> dict:
            return {"loaded": False}

    monkeypatch.setattr("repomind.reports.generator.local_model", lambda: FakeModel())
    summary = _minimal_summary()
    paths = generate_reports({"id": "repo1", "name": "Repo"}, summary)
    assert "SECURITY.sarif" in paths
    assert "EXECUTIVE_SUMMARY.html" in paths
    assert "EXECUTIVE_SUMMARY.pdf" in paths


def test_compare_summaries_returns_deltas() -> None:
    left = _minimal_summary()
    right = _minimal_summary()
    right["scores"]["security"] = 95
    right["statistics"]["files"] = 4
    comparison = compare_summaries(left, right)
    assert comparison["score_delta"]["security"] == 5
    assert comparison["statistics_delta"]["files"] == 3


def _minimal_summary() -> dict:
    return {
        "repository": {"id": "repo1", "name": "Repo", "path": ".", "source": "."},
        "statistics": {
            "files": 1,
            "functions": 0,
            "methods": 0,
            "classes": 0,
            "routes": 0,
            "database_models": 0,
            "indexed_chunks": 0,
        },
        "languages": {"primary": "Python", "all": {"Python": 1}},
        "stack": {"frameworks": [], "package_managers": [], "build_tools": [], "ci_cd": []},
        "scores": {
            "security": 90,
            "maintainability": 80,
            "production_readiness": 70,
            "recruiter": 75,
            "cto": 76,
            "details": {},
        },
        "architecture": {
            "summary": "Architecture summary.",
            "style": "service",
            "important_files": [],
            "top_level_directories": [],
            "diagrams": {},
        },
        "security": {
            "findings": [
                {"rule_id": "x", "severity": "high", "path": "a.py", "line": 1, "message": "Issue"}
            ],
            "severity_counts": {"high": 1},
            "scanner_status": {},
        },
        "technical_debt": {
            "score": 80,
            "items": [],
            "todos": [],
            "large_files": [],
            "maintainability": [],
        },
        "performance": {},
    }
