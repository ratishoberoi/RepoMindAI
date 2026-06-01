from __future__ import annotations

import argparse
import json
import os
import resource
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
os.environ.setdefault("REPOMIND_ENABLE_LOCAL_PATH_IMPORT", "true")
os.environ.setdefault("REPOMIND_LOCAL_IMPORT_ALLOWED_ROOTS", str(ROOT))

from repomind.analysis.analyzer import analyze_repository  # noqa: E402
from repomind.core.store import store  # noqa: E402
from repomind.ingestion.ingestor import ingest_local_path  # noqa: E402
from repomind.intelligence.drift import detect_architecture_drift  # noqa: E402
from repomind.intelligence.pr_risk import analyze_pr_risk  # noqa: E402
from repomind.rag.retriever import retrieve  # noqa: E402

TARGETS = [
    {
        "tier": "tiny",
        "name": "RepoMind sample FastAPI",
        "source": str(ROOT / "sample_repos" / "python_fastapi_example"),
        "kind": "local",
        "max_files": 100,
    },
    {
        "tier": "small",
        "name": "Flask",
        "source": "https://github.com/pallets/flask.git",
        "kind": "git",
        "max_files": 1000,
    },
    {
        "tier": "medium",
        "name": "FastAPI",
        "source": "https://github.com/fastapi/fastapi.git",
        "kind": "git",
        "max_files": 5000,
    },
    {
        "tier": "large",
        "name": "Django",
        "source": "https://github.com/django/django.git",
        "kind": "git",
        "max_files": 20000,
    },
    {
        "tier": "very_large",
        "name": "Next.js",
        "source": "https://github.com/vercel/next.js.git",
        "kind": "git",
        "max_files": 100000,
    },
    {
        "tier": "massive",
        "name": "Kubernetes",
        "source": "https://github.com/kubernetes/kubernetes.git",
        "kind": "git",
        "max_files": 250000,
    },
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run RepoMindAI platform scale benchmarks.")
    parser.add_argument("--tier", action="append", help="Benchmark tier to run.")
    parser.add_argument(
        "--include-network", action="store_true", help="Clone real OSS repositories."
    )
    parser.add_argument("--limit", type=int, default=0, help="Maximum number of targets.")
    args = parser.parse_args()
    output_dir = ROOT / "reports" / "performance"
    output_dir.mkdir(parents=True, exist_ok=True)
    targets = [
        target
        for target in TARGETS
        if (not args.tier or target["tier"] in args.tier)
        and (args.include_network or target["kind"] == "local")
    ]
    if args.limit:
        targets = targets[: args.limit]
    results = [run_target(target) for target in targets]
    timestamp = time.strftime("%Y%m%d-%H%M%S", time.gmtime())
    json_path = output_dir / f"benchmark-{timestamp}.json"
    json_path.write_text(json.dumps(results, indent=2))
    (output_dir / "latest.json").write_text(json.dumps(results, indent=2))
    (output_dir / "latest.md").write_text(render_markdown(results))
    print(json_path)


def run_target(target: dict[str, Any]) -> dict[str, Any]:
    started = time.time()
    root = prepare_source(target)
    result: dict[str, Any] = {
        "tier": target["tier"],
        "name": target["name"],
        "source": target["source"],
        "status": "started",
        "started_at": started,
    }
    try:
        ingest = measure(lambda: ingest_local_path(str(root)))
        repo = ingest["value"]
        analysis = measure(lambda: analyze_repository(repo))
        summary = analysis["value"]
        store.update(repo["id"], status="complete", summary=summary, reports=summary["reports"])
        graph_time = (
            summary.get("performance", {}).get("timings", {}).get("dependency_graph_seconds", 0)
        )
        reports_time = (
            summary.get("performance", {}).get("timings", {}).get("report_generation_seconds", 0)
        )
        security_time = (
            summary.get("performance", {}).get("timings", {}).get("security_scan_seconds", 0)
        )
        retrieval = measure(lambda: retrieve(repo["id"], "architecture security risk", limit=8))
        changed_files = [
            item.get("relative_path", "")
            for item in summary.get("files", [])[:10]
            if item.get("relative_path")
        ]
        pr = measure(lambda: analyze_pr_risk(summary, changed_files))
        drift = measure(lambda: detect_architecture_drift(summary, summary))
        result.update(
            {
                "status": "passed",
                "repo_id": repo["id"],
                "file_count": summary.get("statistics", {}).get("files", 0),
                "indexed_chunks": summary.get("statistics", {}).get("indexed_chunks", 0),
                "cpu_seconds": analysis["cpu_seconds"],
                "max_rss_mb": analysis["max_rss_mb"],
                "ingestion_seconds": ingest["wall_seconds"],
                "analysis_seconds": analysis["wall_seconds"],
                "graph_build_seconds": graph_time,
                "report_generation_seconds": reports_time,
                "security_scan_seconds": security_time,
                "chat_retrieval_latency_seconds": retrieval["wall_seconds"],
                "pr_analysis_latency_seconds": pr["wall_seconds"],
                "drift_analysis_latency_seconds": drift["wall_seconds"],
                "bottlenecks": bottlenecks(
                    {
                        "analysis": analysis["wall_seconds"],
                        "graph": graph_time,
                        "reports": reports_time,
                        "security": security_time,
                        "retrieval": retrieval["wall_seconds"],
                        "pr": pr["wall_seconds"],
                        "drift": drift["wall_seconds"],
                    }
                ),
            }
        )
    except Exception as exc:
        result.update({"status": "failed", "error": str(exc)})
    finally:
        if target["kind"] == "git" and isinstance(root, Path):
            subprocess.run(["rm", "-rf", str(root)], check=False)
    return result


def prepare_source(target: dict[str, Any]) -> Path:
    if target["kind"] == "local":
        return Path(target["source"])
    tmp = Path(tempfile.mkdtemp(prefix=f"repomind-bench-{target['tier']}-"))
    subprocess.run(
        ["git", "clone", "--depth", "1", "--filter=blob:none", target["source"], str(tmp)],
        check=True,
        timeout=600,
    )
    return tmp


def measure(fn):
    start_wall = time.perf_counter()
    start_usage = resource.getrusage(resource.RUSAGE_SELF)
    value = fn()
    end_usage = resource.getrusage(resource.RUSAGE_SELF)
    return {
        "value": value,
        "wall_seconds": round(time.perf_counter() - start_wall, 4),
        "cpu_seconds": round(
            (end_usage.ru_utime + end_usage.ru_stime)
            - (start_usage.ru_utime + start_usage.ru_stime),
            4,
        ),
        "max_rss_mb": round(end_usage.ru_maxrss / 1024, 2),
    }


def bottlenecks(metrics: dict[str, float]) -> list[dict[str, Any]]:
    ranked = sorted(metrics.items(), key=lambda item: item[1], reverse=True)
    total = sum(metrics.values()) or 1
    return [
        {"stage": key, "seconds": round(value, 4), "share": round(value / total, 3)}
        for key, value in ranked
        if value > 0
    ][:5]


def render_markdown(results: list[dict[str, Any]]) -> str:
    lines = [
        "# RepoMindAI Performance Benchmark",
        "",
        "Benchmarks use real analysis, graph, security, report, retrieval, PR, and drift code paths.",
        "",
        "| Tier | Target | Files | Analysis | RSS MB | Top Bottleneck | Status |",
        "| --- | --- | ---: | ---: | ---: | --- | --- |",
    ]
    for item in results:
        top = (item.get("bottlenecks") or [{}])[0]
        lines.append(
            "| {tier} | {name} | {files} | {analysis}s | {rss} | {bottleneck} | {status} |".format(
                tier=item.get("tier"),
                name=item.get("name"),
                files=item.get("file_count", 0),
                analysis=item.get("analysis_seconds", "-"),
                rss=item.get("max_rss_mb", "-"),
                bottleneck=top.get("stage", item.get("error", "n/a")),
                status=item.get("status"),
            )
        )
    lines.extend(["", "## Bottleneck Ranking", ""])
    for item in results:
        lines.append(f"### {item.get('name')} ({item.get('tier')})")
        for bottleneck in item.get("bottlenecks", []):
            lines.append(
                f"- {bottleneck['stage']}: {bottleneck['seconds']}s ({bottleneck['share'] * 100:.1f}%)"
            )
        if item.get("error"):
            lines.append(f"- Error: `{item['error']}`")
        lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    main()
