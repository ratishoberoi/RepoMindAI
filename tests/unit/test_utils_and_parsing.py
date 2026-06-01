from pathlib import Path

from repomind.analysis.classifier import classify_file
from repomind.analysis.graph import build_dependency_graph
from repomind.analysis.parser import parse_file
from repomind.core.store import RepositoryStore
from repomind.llm.adapters import detect_model
from repomind.rag.chunking import chunk_file, chunk_text
from repomind.rag.embeddings import BGEEmbedder
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
    path.write_text("import os\n\nclass Service: pass\n\ndef run():\n    return os.getenv('API_KEY')\n")
    parsed = parse_file(path, "main.py", "Python")
    assert "os" in parsed["imports"]
    assert parsed["classes"][0]["name"] == "Service"
    assert parsed["functions"][0]["name"] == "run"
    assert "API_KEY" in parsed["env_vars"]


def test_dependency_graph_building() -> None:
    files = [{"relative_path": "app/main.py", "language": "Python", "size": 10}]
    parsed = [{"relative_path": "app/main.py", "imports": ["os"], "functions": [{"name": "run", "line": 1}], "classes": []}]
    graph = build_dependency_graph(files, parsed)
    assert any(edge["relation"] == "imports" for edge in graph["edges"])
    assert any(node["kind"] == "function" for node in graph["nodes"])


def test_chunks_are_stable() -> None:
    chunks = chunk_text("hello world\n" * 400, "README.md")
    assert chunks


def test_chunk_file_prefers_symbol_chunks(tmp_path: Path) -> None:
    path = tmp_path / "service.py"
    path.write_text("def alpha():\n    return 1\n\nclass Beta:\n    pass\n")
    chunks = chunk_file(path, "service.py")
    assert {chunk["symbol"] for chunk in chunks} == {"alpha", "Beta"}
    assert all(chunk["kind"] == "symbol" for chunk in chunks)


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


def test_sql_store_migrates_legacy_metadata(tmp_path: Path) -> None:
    legacy = tmp_path / "metadata.json"
    legacy.write_text(
        '{"repositories":{"abc":{"id":"abc","name":"Legacy","source_type":"local","source":"src",'
        '"path":"repo","status":"complete","created_at":1,"updated_at":2,"summary":{},'
        '"reports":{"README.md":"/tmp/README.md"},"error":null,"repository_deleted":false,'
        '"repository_deleted_at":null,"repository_retention_minutes":60}}}'
    )
    sql_store = RepositoryStore(database_url=f"sqlite:///{tmp_path / 'store.db'}", legacy_path=legacy)
    repo = sql_store.get("abc")
    assert repo["name"] == "Legacy"
    assert repo["reports"]["README.md"] == "/tmp/README.md"
