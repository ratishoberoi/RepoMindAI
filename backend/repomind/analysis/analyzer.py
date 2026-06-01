from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from repomind.analysis.architecture import extract_architecture
from repomind.analysis.classifier import classify_file, detect_stack, language_summary
from repomind.analysis.debt import analyze_technical_debt
from repomind.analysis.graph import build_dependency_graph
from repomind.analysis.parser import parse_file
from repomind.core.config import get_settings
from repomind.rag.indexer import index_repository
from repomind.reports.generator import generate_reports
from repomind.security.scanner import scan_security
from repomind.utils.hashing import file_sha256
from repomind.utils.ignore import should_ignore


def analyze_repository(repo: dict[str, Any]) -> dict[str, Any]:
    root = Path(repo["path"])
    timings: dict[str, float] = {}
    start = time.perf_counter()
    files = scan_files(root)
    timings["scan_files_seconds"] = _elapsed(start)
    start = time.perf_counter()
    parsed = parse_files(root, files)
    timings["parse_files_seconds"] = _elapsed(start)
    start = time.perf_counter()
    languages = language_summary(files)
    stack = detect_stack(root, files)
    graph = build_dependency_graph(files, parsed)
    timings["graph_stack_seconds"] = _elapsed(start)
    start = time.perf_counter()
    debt = analyze_technical_debt(root, files, parsed)
    timings["technical_debt_seconds"] = _elapsed(start)
    start = time.perf_counter()
    security = scan_security(root, files)
    timings["security_seconds"] = _elapsed(start)
    start = time.perf_counter()
    rag = index_repository(repo["id"], root, files)
    timings["indexing_seconds"] = _elapsed(start)
    summary = build_summary(repo, files, parsed, languages, stack, graph, security, debt, rag)
    summary["performance"] = {"timings": timings | rag.get("timings", {})}
    start = time.perf_counter()
    report_paths = generate_reports(repo, summary)
    summary["performance"]["timings"]["report_generation_seconds"] = _elapsed(start)
    summary["performance"]["timings"]["total_analysis_seconds"] = round(
        sum(
            value
            for key, value in summary["performance"]["timings"].items()
            if key.endswith("_seconds")
        ),
        3,
    )
    summary["reports"] = report_paths
    return summary


def scan_files(root: Path) -> list[dict[str, Any]]:
    settings = get_settings()
    seen_hashes: set[str] = set()
    files: list[dict[str, Any]] = []
    for path in root.rglob("*"):
        if not path.is_file() or should_ignore(path, root):
            continue
        try:
            size = path.stat().st_size
            if size > settings.max_file_bytes:
                continue
            digest = file_sha256(path)
        except OSError:
            continue
        duplicate = digest in seen_hashes
        seen_hashes.add(digest)
        rel = path.relative_to(root).as_posix()
        files.append(
            {
                "relative_path": rel,
                "size": size,
                "sha256": digest,
                "language": classify_file(path),
                "duplicate": duplicate,
            }
        )
        if len(files) >= settings.max_repository_files:
            break
    return sorted(files, key=lambda item: item["relative_path"])


def _elapsed(start: float) -> float:
    return round(time.perf_counter() - start, 3)


def parse_files(root: Path, files: list[dict[str, Any]]) -> list[dict[str, Any]]:
    parsed = []
    for item in files:
        if item["language"] in {"Text"} and item["size"] > 250_000:
            continue
        try:
            parsed.append(
                parse_file(root / item["relative_path"], item["relative_path"], item["language"])
            )
        except OSError:
            continue
    return parsed


def build_summary(
    repo: dict[str, Any],
    files: list[dict[str, Any]],
    parsed: list[dict[str, Any]],
    languages: dict[str, Any],
    stack: dict[str, Any],
    graph: dict[str, Any],
    security: dict[str, Any],
    debt: dict[str, Any],
    rag: dict[str, Any],
) -> dict[str, Any]:
    functions = sum(len(item.get("functions", [])) for item in parsed)
    classes = sum(len(item.get("classes", [])) for item in parsed)
    methods = sum(len(item.get("methods", [])) for item in parsed)
    routes = sum(len(item.get("routes", [])) for item in parsed)
    scores = score_repository(files, parsed, stack, security, debt)
    architecture = extract_architecture(files, parsed, stack, graph)
    return {
        "repository": {
            "id": repo["id"],
            "name": repo["name"],
            "path": repo["path"],
            "source": repo["source"],
        },
        "statistics": {
            "files": len(files),
            "bytes": sum(item["size"] for item in files),
            "functions": functions,
            "methods": methods,
            "classes": classes,
            "routes": routes,
            "database_models": sum(len(item.get("database_models", [])) for item in parsed),
            "indexed_chunks": rag["chunks"],
        },
        "languages": languages,
        "stack": stack,
        "files": files,
        "parsed": parsed,
        "graph": graph,
        "security": security,
        "technical_debt": debt,
        "scores": scores,
        "architecture": architecture,
    }


def score_repository(
    files: list[dict[str, Any]],
    parsed: list[dict[str, Any]],
    stack: dict[str, Any],
    security: dict[str, Any],
    debt: dict[str, Any],
) -> dict[str, Any]:
    names = {Path(item["relative_path"]).name.lower() for item in files}
    paths = {item["relative_path"].lower() for item in files}
    severity = security["severity_counts"]
    file_count = max(len(files), 1)
    security_penalty = (
        severity.get("critical", 0) * 20
        + severity.get("high", 0) * 6
        + min(35, (severity.get("medium", 0) / file_count) * 220)
        + min(10, (severity.get("low", 0) / file_count) * 5)
    )
    security_score = max(0, round(100 - min(80, security_penalty), 1))
    tests_score = 100 if any("test" in path or "spec" in path for path in paths) else 35
    ci_score = 100 if stack.get("ci_cd") else 35
    container_score = 100 if stack.get("docker") else 45
    docs_score = 100 if "readme.md" in names else 45
    dependency_score = 90 if stack.get("package_managers") else 50
    routes = sum(len(item.get("routes", [])) for item in parsed)
    symbol_count = sum(
        len(item.get("functions", [])) + len(item.get("classes", [])) for item in parsed
    )
    code_signal = min(100, 45 + routes * 8 + symbol_count * 1.5)
    production_score = round(
        security_score * 0.32
        + debt["score"] * 0.24
        + tests_score * 0.14
        + ci_score * 0.10
        + container_score * 0.08
        + dependency_score * 0.07
        + docs_score * 0.05,
        1,
    )
    recruiter_score = round(
        code_signal * 0.35 + docs_score * 0.20 + tests_score * 0.20 + debt["score"] * 0.25, 1
    )
    cto_score = round(
        production_score * 0.45 + security_score * 0.25 + debt["score"] * 0.20 + ci_score * 0.10, 1
    )
    confidence = round(
        min(
            95,
            30
            + min(len(files), 40)
            + (15 if parsed else 0)
            + (10 if stack.get("package_managers") else 0),
        ),
        1,
    )
    score_details = {
        "security": {
            "score": round(security_score, 1),
            "positive_contributors": [
                "Bandit scanner enabled"
                if security.get("scanner_status", {}).get("bandit")
                else "Bandit scanner unavailable",
                "Semgrep scanner enabled"
                if security.get("scanner_status", {}).get("semgrep")
                else "Semgrep scanner unavailable",
                f"{file_count} analyzed files provides normalized finding density",
            ],
            "negative_contributors": [
                f"{count} {level} findings" for level, count in sorted(severity.items()) if count
            ]
            or ["No enabled scanner findings"],
            "calculation": (
                "100 minus weighted severity penalty: critical*20 + high*6 + normalized medium/low density caps."
            ),
        },
        "maintainability": {
            "score": round(debt["score"], 1),
            "positive_contributors": [
                f"{len(debt.get('maintainability', []))} Python files had Radon maintainability metrics",
                f"{symbol_count} extracted classes/functions/methods",
            ],
            "negative_contributors": [
                f"{len(debt.get('items', []))} high complexity items",
                f"{len(debt.get('todos', []))} TODO/FIXME markers",
                f"{len(debt.get('large_files', []))} large files",
            ],
            "calculation": "Radon maintainability average minus normalized complexity, TODO, and large-file penalties.",
        },
        "production_readiness": {
            "score": production_score,
            "positive_contributors": [
                f"Security score {security_score}",
                f"Maintainability score {debt['score']}",
                "Tests detected" if tests_score == 100 else "No tests detected",
                "CI detected" if ci_score == 100 else "No CI detected",
                "Docker detected" if container_score == 100 else "No Docker detected",
            ],
            "negative_contributors": [
                label
                for label, value in [
                    ("test coverage signal missing", tests_score < 100),
                    ("CI signal missing", ci_score < 100),
                    ("containerization signal missing", container_score < 100),
                    ("README missing", docs_score < 100),
                ]
                if value
            ]
            or ["No major production checklist gaps detected by static evidence"],
            "calculation": "Weighted blend: security 32%, maintainability 24%, tests 14%, CI 10%, container 8%, dependencies 7%, docs 5%.",
        },
        "recruiter": {
            "score": recruiter_score,
            "positive_contributors": [
                f"Code signal {round(code_signal, 1)} from routes and symbols",
                "README present" if docs_score == 100 else "README absent",
                "Tests present" if tests_score == 100 else "Tests absent",
            ],
            "negative_contributors": [
                item
                for item, missing in [
                    ("weak documentation signal", docs_score < 100),
                    ("weak test signal", tests_score < 100),
                    ("maintainability issues lower hiring signal", debt["score"] < 80),
                ]
                if missing
            ]
            or ["No major recruiter-signal gaps detected"],
            "calculation": "Weighted blend: code signal 35%, docs 20%, tests 20%, maintainability 25%.",
        },
        "cto": {
            "score": cto_score,
            "positive_contributors": [
                f"Production readiness {production_score}",
                f"Security {security_score}",
                f"Maintainability {debt['score']}",
            ],
            "negative_contributors": [
                item
                for item, missing in [
                    ("security risk needs review", security_score < 85),
                    ("maintainability below target", debt["score"] < 80),
                    ("CI missing", ci_score < 100),
                ]
                if missing
            ]
            or ["No major CTO checklist gaps detected"],
            "calculation": "Weighted blend: production 45%, security 25%, maintainability 20%, CI 10%.",
        },
    }
    return {
        "security": round(security_score, 1),
        "maintainability": round(debt["score"], 1),
        "production_readiness": production_score,
        "recruiter": recruiter_score,
        "cto": cto_score,
        "confidence": confidence,
        "details": score_details,
    }
