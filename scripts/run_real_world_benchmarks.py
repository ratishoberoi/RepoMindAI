from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from repomind.analysis.analyzer import analyze_repository  # noqa: E402
from repomind.core.cleanup import delete_repository_contents  # noqa: E402
from repomind.core.store import store  # noqa: E402
from repomind.ingestion.ingestor import ingest_github, ingest_local_path  # noqa: E402
from repomind.rag.qa import answer_question  # noqa: E402
from repomind.rag.retriever import retrieve  # noqa: E402

TARGETS = [
    {"name": "FastAPI", "kind": "github", "source": "https://github.com/fastapi/fastapi"},
    {"name": "Flask", "kind": "github", "source": "https://github.com/pallets/flask"},
    {"name": "Next.js", "kind": "github", "source": "https://github.com/vercel/next.js"},
    {"name": "RepoMindAI", "kind": "local", "source": str(ROOT)},
]

QUESTIONS = [
    ("authentication", "How does authentication work?"),
    ("routing", "How does routing work?"),
    ("database", "How does database access work?"),
]


def main() -> None:
    started = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
    results = []
    selected = {item.strip().lower() for item in os.environ.get("REPOMIND_BENCHMARK_TARGETS", "").split(",") if item.strip()}
    targets = [target for target in TARGETS if not selected or target["name"].lower() in selected]
    for target in targets:
        result = run_target(target)
        results.append(result)
        write_markdown(results, started)
    write_json(results)


def run_target(target: dict[str, str]) -> dict[str, Any]:
    item: dict[str, Any] = {"target": target["name"], "source": target["source"], "status": "started"}
    try:
        ingest_start = time.perf_counter()
        repo = ingest_github(target["source"]) if target["kind"] == "github" else ingest_local_path(target["source"])
        item["repo_id"] = repo["id"]
        item["ingestion_seconds"] = elapsed(ingest_start)

        analysis_start = time.perf_counter()
        summary = analyze_repository(repo)
        item["analysis_wall_seconds"] = elapsed(analysis_start)
        store.update(repo["id"], status="complete", summary=summary, reports=summary["reports"])

        item["statistics"] = summary["statistics"]
        item["scores"] = {key: value for key, value in summary["scores"].items() if key != "details"}
        item["timings"] = summary.get("performance", {}).get("timings", {})
        item["architecture_quality"] = architecture_quality(summary)
        item["retrieval_quality"] = retrieval_quality(repo["id"])
        item["explainer_quality"] = explainer_quality(repo["id"])
        item["reports"] = sorted(Path(path).name for path in summary.get("reports", {}).values())

        cleanup_fields = delete_repository_contents(repo)
        repo = store.update(repo["id"], **cleanup_fields)
        item["cleanup"] = {
            "repository_deleted": repo.get("repository_deleted"),
            "path_exists_after_cleanup": Path(repo["path"]).exists(),
            "reports_exist": all(Path(path).exists() for path in summary.get("reports", {}).values()),
            "index_manifest_exists": Path(summary["reports"]["analysis-summary.json"]).exists(),
        }
        item["status"] = "passed"
    except Exception as exc:
        item["status"] = "failed"
        item["error"] = str(exc)
    return item


def retrieval_quality(repo_id: str) -> dict[str, Any]:
    results = {}
    for key, question in QUESTIONS:
        start = time.perf_counter()
        chunks = retrieve(repo_id, question, limit=6)
        latency = elapsed(start)
        paths = [chunk["path"] for chunk in chunks]
        scores = [chunk["score"] for chunk in chunks]
        results[key] = {
            "question": question,
            "latency_seconds": latency,
            "top_paths": paths[:5],
            "top_score": scores[0] if scores else None,
            "quality": grade_retrieval(key, paths),
        }
    return results


def explainer_quality(repo_id: str) -> dict[str, Any]:
    results = {}
    for key, question in QUESTIONS:
        start = time.perf_counter()
        answer = answer_question(repo_id, question)
        latency = elapsed(start)
        text = answer.get("answer", "")
        results[key] = {
            "latency_seconds": latency,
            "has_explanation": "Explanation" in text,
            "has_risks": "Risk" in text or "Risks" in text,
            "has_improvements": "Improvement" in text or "Improvements" in text,
            "citation_count": len(answer.get("citations", [])),
            "critical_files": answer.get("critical_files", [])[:6],
            "answer_excerpt": text[:700],
        }
    return results


def architecture_quality(summary: dict[str, Any]) -> dict[str, Any]:
    arch = summary["architecture"]
    diagrams = arch.get("diagrams", {})
    component_count = len(arch.get("components", []))
    important_count = len(arch.get("important_files", []))
    route_count = len(arch.get("route_files", []))
    db_count = len(arch.get("database_model_files", []))
    diagram_count = sum(1 for value in diagrams.values() if value and "graph " in value)
    score = min(100, diagram_count * 14 + component_count * 3 + important_count * 2 + min(route_count, 10) * 2 + min(db_count, 5) * 2)
    return {
        "score": score,
        "diagram_count": diagram_count,
        "component_count": component_count,
        "important_file_count": important_count,
        "route_file_count": route_count,
        "database_model_file_count": db_count,
    }


def grade_retrieval(kind: str, paths: list[str]) -> str:
    joined = " ".join(paths).lower()
    expected = {
        "authentication": ("auth", "security", "login", "jwt", "oauth", "password"),
        "routing": ("route", "router", "routing", "views", "endpoint", "api"),
        "database": ("database", "db", "sql", "model", "schema", "storage", "store", "chroma", "metadata"),
    }[kind]
    hits = sum(1 for token in expected if token in joined)
    if hits >= 2:
        return "strong"
    if hits == 1:
        return "partial"
    return "weak"


def write_json(results: list[dict[str, Any]]) -> None:
    output = ROOT / "data" / "validation" / "real_world_benchmarks.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(results, indent=2))


def write_markdown(results: list[dict[str, Any]], started: str) -> None:
    lines = [
        "# Benchmark Results",
        "",
        f"Started: {started}",
        "",
        "Benchmarks use real ingestion, static analysis, BGE embeddings, ChromaDB indexing, qwen-judge report generation, qwen-judge repository explainers, and cleanup verification.",
        "",
    ]
    for item in results:
        lines.extend(target_markdown(item))
    (ROOT / "BENCHMARK_RESULTS.md").write_text("\n".join(lines) + "\n")


def target_markdown(item: dict[str, Any]) -> list[str]:
    lines = [f"## {item['target']}", "", f"- Source: `{item['source']}`", f"- Status: **{item['status']}**"]
    if item.get("error"):
        lines.append(f"- Error: `{item['error']}`")
        lines.append("")
        return lines
    timings = item.get("timings", {})
    stats = item.get("statistics", {})
    lines.extend(
        [
            f"- Repository ID: `{item.get('repo_id')}`",
            f"- Ingestion time: {item.get('ingestion_seconds')}s",
            f"- Analysis wall time: {item.get('analysis_wall_seconds')}s",
            f"- Indexing time: {timings.get('indexing_seconds')}s",
            f"- Embedding time: {timings.get('embedding_seconds')}s",
            f"- Chroma upsert time: {timings.get('chroma_upsert_seconds')}s",
            f"- Report generation time: {timings.get('report_generation_seconds')}s",
            f"- Files analyzed: {stats.get('files')}",
            f"- Indexed chunks: {stats.get('indexed_chunks')}",
            f"- Routes: {stats.get('routes')}",
            f"- Scores: `{item.get('scores')}`",
            "",
            "### Retrieval Quality",
            "",
        ]
    )
    for key, result in item.get("retrieval_quality", {}).items():
        lines.extend(
            [
                f"- {key}: **{result['quality']}**, {result['latency_seconds']}s, top score `{result['top_score']}`",
                f"  Top paths: {', '.join(f'`{path}`' for path in result['top_paths']) or 'none'}",
            ]
        )
    arch = item.get("architecture_quality", {})
    lines.extend(
        [
            "",
            "### Architecture Quality",
            "",
            f"- Score: {arch.get('score')} / 100",
            f"- Diagrams: {arch.get('diagram_count')}",
            f"- Components: {arch.get('component_count')}",
            f"- Important files: {arch.get('important_file_count')}",
            f"- Route files: {arch.get('route_file_count')}",
            f"- Database model files: {arch.get('database_model_file_count')}",
            "",
            "### Explainer Quality",
            "",
        ]
    )
    for key, result in item.get("explainer_quality", {}).items():
        lines.extend(
            [
                f"- {key}: {result['latency_seconds']}s, citations={result['citation_count']}, explanation={result['has_explanation']}, risks={result['has_risks']}, improvements={result['has_improvements']}",
                f"  Critical files: {', '.join(f'`{path}`' for path in result['critical_files']) or 'none'}",
            ]
        )
    cleanup = item.get("cleanup", {})
    lines.extend(
        [
            "",
            "### Cleanup Verification",
            "",
            f"- Repository deleted: {cleanup.get('repository_deleted')}",
            f"- Path exists after cleanup: {cleanup.get('path_exists_after_cleanup')}",
            f"- Reports still exist: {cleanup.get('reports_exist')}",
            f"- Analysis summary exists: {cleanup.get('index_manifest_exists')}",
            "",
        ]
    )
    return lines


def elapsed(start: float) -> float:
    return round(time.perf_counter() - start, 3)


if __name__ == "__main__":
    main()
