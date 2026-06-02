from __future__ import annotations

import re
from collections import Counter
from typing import Any

from repomind.core.store import store
from repomind.rag.embeddings import embedder
from repomind.rag.indexer import _collection
from repomind.security.redaction import redact_text

WORD_RE = re.compile(r"[A-Za-z0-9_./-]+")


def retrieve(repo_id: str, question: str, limit: int = 6) -> list[dict[str, Any]]:
    query_terms = _expanded_query_terms(question)
    query_text = f"{question} {' '.join(sorted(query_terms))}"
    query_vector = embedder().embed(query_text)
    collection = _collection(repo_id)
    try:
        payload = collection.query(
            query_embeddings=[query_vector],
            n_results=max(limit * 12, 72),
            include=["documents", "metadatas", "distances"],
            where={"sensitive": False},
        )
    except Exception as exc:
        raise RuntimeError(f"Chroma retrieval failed for repository {repo_id}: {exc}") from exc

    candidates = []
    ids = payload.get("ids", [[]])[0]
    docs = payload.get("documents", [[]])[0]
    metas = payload.get("metadatas", [[]])[0]
    distances = payload.get("distances", [[]])[0]
    for chunk_id, doc, meta, distance in zip(ids, docs, metas, distances):
        base = 1.0 - float(distance or 0.0)
        doc = redact_text(doc)
        lexical = _lexical_score(query_terms, doc)
        score = (
            base * 0.66
            + lexical * 0.22
            + _path_boost(str(meta.get("path", "")), query_terms)
            + _source_quality_boost(str(meta.get("path", "")), query_terms)
        )
        candidates.append(
            {
                "id": chunk_id,
                "path": meta.get("path"),
                "line_start": meta.get("line_start"),
                "line_end": meta.get("line_end"),
                "text": doc,
                "score": round(score, 4),
                "vector_score": round(base, 4),
                "rerank_score": round(lexical, 4),
                "symbol": meta.get("symbol"),
                "kind": meta.get("kind"),
            }
        )
    candidates.extend(_pinned_candidates(collection, repo_id, question, query_terms))
    candidates.extend(_bm25_candidates(collection, question, query_terms, limit * 8))
    candidates = _dedupe(candidates)
    candidates.sort(key=lambda item: item["score"], reverse=True)
    return candidates[:limit]


def _pinned_candidates(
    collection: Any, repo_id: str, question: str, query_terms: set[str]
) -> list[dict[str, Any]]:
    paths = _pinned_paths(repo_id, question)
    if not paths:
        return []
    candidates = []
    for path in _rank_pinned_paths(paths)[:12]:
        try:
            payload = collection.get(
                where={"path": path}, include=["documents", "metadatas"], limit=3
            )
        except Exception:
            continue
        for chunk_id, doc, meta in zip(
            payload.get("ids", []), payload.get("documents", []), payload.get("metadatas", [])
        ):
            if meta.get("sensitive"):
                continue
            doc = redact_text(doc)
            lexical = _lexical_score(query_terms, doc)
            score = (
                0.72
                + lexical * 0.18
                + _path_boost(str(meta.get("path", "")), query_terms)
                + _source_quality_boost(str(meta.get("path", "")), query_terms)
            )
            candidates.append(
                {
                    "id": chunk_id,
                    "path": meta.get("path"),
                    "line_start": meta.get("line_start"),
                    "line_end": meta.get("line_end"),
                    "text": doc,
                    "score": round(score, 4),
                    "vector_score": 0.5,
                    "rerank_score": round(lexical, 4),
                    "symbol": meta.get("symbol"),
                    "kind": meta.get("kind"),
                }
            )
    return candidates


def _bm25_candidates(
    collection: Any, question: str, query_terms: set[str], limit: int
) -> list[dict[str, Any]]:
    try:
        payload = collection.get(include=["documents", "metadatas"], limit=2000)
    except Exception:
        return []
    docs = [
        (chunk_id, redact_text(doc), meta)
        for chunk_id, doc, meta in zip(
            payload.get("ids", []), payload.get("documents", []), payload.get("metadatas", [])
        )
        if not meta.get("sensitive")
    ]
    if not docs:
        return []
    tokenized = [WORD_RE.findall(doc.lower()) for _, doc, _ in docs]
    avg_len = sum(len(tokens) for tokens in tokenized) / max(len(tokenized), 1)
    doc_freq = Counter(term for tokens in tokenized for term in set(tokens))
    candidates = []
    for (chunk_id, doc, meta), tokens in zip(docs, tokenized):
        score = _bm25_score(query_terms, tokens, doc_freq, len(docs), avg_len)
        if score <= 0:
            continue
        final_score = min(
            0.95,
            0.42
            + score / 18
            + _path_boost(str(meta.get("path", "")), query_terms)
            + _source_quality_boost(str(meta.get("path", "")), query_terms),
        )
        candidates.append(
            {
                "id": chunk_id,
                "path": meta.get("path"),
                "line_start": meta.get("line_start"),
                "line_end": meta.get("line_end"),
                "text": doc,
                "score": round(final_score, 4),
                "vector_score": 0.0,
                "rerank_score": round(final_score, 4),
                "symbol": meta.get("symbol"),
                "kind": meta.get("kind"),
            }
        )
    candidates.sort(key=lambda item: item["score"], reverse=True)
    return candidates[:limit]


def _bm25_score(
    query_terms: set[str], tokens: list[str], doc_freq: Counter[str], doc_count: int, avg_len: float
) -> float:
    if not query_terms or not tokens:
        return 0.0
    counts = Counter(tokens)
    k1 = 1.5
    b = 0.75
    score = 0.0
    for term in query_terms:
        freq = counts.get(term, 0)
        if not freq:
            continue
        idf = max(0.0, (doc_count - doc_freq[term] + 0.5) / (doc_freq[term] + 0.5))
        denom = freq + k1 * (1 - b + b * len(tokens) / max(avg_len, 1))
        score += idf * ((freq * (k1 + 1)) / denom)
    return score


def _pinned_paths(repo_id: str, question: str) -> list[str]:
    try:
        summary = store.get(repo_id).get("summary") or {}
    except KeyError:
        return []
    architecture = summary.get("architecture", {})
    parsed = summary.get("parsed", [])
    lower = question.lower()
    paths: list[str] = []
    if any(token in lower for token in ("routing", "route", "api", "endpoint")):
        paths.extend(architecture.get("route_files", []))
        paths.extend(item.get("relative_path") for item in parsed if item.get("routes"))
    if any(token in lower for token in ("database", "db", "storage", "persist")):
        paths.extend(architecture.get("database_model_files", []))
        paths.extend(
            item.get("relative_path")
            for item in parsed
            if any(
                token in item.get("relative_path", "").lower()
                for token in ("database", "db", "store", "storage", "repository", "sql")
            )
        )
    if any(token in lower for token in ("auth", "authentication", "login", "jwt", "session")):
        paths.extend(
            item.get("relative_path")
            for item in parsed
            if any(
                token in item.get("relative_path", "").lower()
                for token in ("auth", "jwt", "middleware", "session", "login", "oauth", "security")
            )
        )
    return [path for index, path in enumerate(paths) if path and path not in paths[:index]]


def _rank_pinned_paths(paths: list[str]) -> list[str]:
    unique = [path for index, path in enumerate(paths) if path and path not in paths[:index]]
    return sorted(unique, key=lambda path: (_low_value_path(path), path.count("/"), path))


def _low_value_path(path: str) -> bool:
    lower = path.lower()
    parts = set(lower.split("/"))
    return bool(
        {"test", "tests", "docs", "doc", "docs_src", "examples", "example", "fixtures", "fixture"}
        & parts
        or lower.startswith(("docs_src/", "tests/", "test/", "scripts/", ".github/"))
        or lower.endswith((".md", ".rst", ".txt", ".yml", ".yaml"))
    )


def _dedupe(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    for item in candidates:
        existing = by_id.get(item["id"])
        if existing is None or item["score"] > existing["score"]:
            by_id[item["id"]] = item
    return list(by_id.values())


def _expanded_query_terms(question: str) -> set[str]:
    terms = set(WORD_RE.findall(question.lower()))
    if {"auth", "authentication", "login", "oauth", "jwt", "session"} & terms:
        terms.update(
            {
                "auth",
                "authentication",
                "authenticate",
                "authorization",
                "authorize",
                "login",
                "jwt",
                "oauth",
                "session",
                "password",
                "middleware",
                "guard",
            }
        )
    if {"database", "db", "sql", "storage", "persist", "used"} & terms:
        terms.update(
            {
                "database",
                "db",
                "sql",
                "storage",
                "store",
                "repository",
                "model",
                "schema",
                "migration",
                "postgres",
                "sqlite",
                "mysql",
                "redis",
                "orm",
                "prisma",
                "mongoose",
                "sequelize",
                "gorm",
                "sqlx",
                "diesel",
            }
        )
    if {"route", "routes", "routing", "api", "endpoint", "defined"} & terms:
        terms.update(
            {
                "route",
                "routes",
                "router",
                "routing",
                "api",
                "endpoint",
                "controller",
                "handler",
                "server",
                "get",
                "post",
                "put",
                "patch",
                "delete",
            }
        )
    return terms


def _lexical_score(query_terms: set[str], document: str) -> float:
    if not query_terms:
        return 0.0
    doc_terms = set(WORD_RE.findall(document.lower()))
    return len(query_terms & doc_terms) / len(query_terms)


def _path_boost(path: str, query_terms: set[str]) -> float:
    lower = path.lower()
    boost = 0.0
    if {"what", "project", "do", "overview"} & query_terms:
        if lower == "readme.md":
            boost += 0.22
        elif lower in {"package.json", "pyproject.toml"}:
            boost += 0.12
        if lower.startswith("examples/"):
            boost -= 0.12
    if {"authentication", "auth", "login", "oauth", "jwt", "session"} & query_terms:
        if any(
            token in lower
            for token in ("auth", "jwt", "middleware", "session", "login", "oauth", "security")
        ):
            boost += 0.34
        if lower.endswith(("semgrep_rules.yml", "scanner.py")):
            boost -= 0.45
    if {"payment", "payments", "stripe", "billing", "invoice"} & query_terms:
        if any(token in lower for token in ("payment", "stripe", "billing", "invoice", "checkout")):
            boost += 0.18
    if {"database", "db", "sql", "model", "schema"} & query_terms:
        if any(
            token in lower
            for token in (
                "database",
                "db",
                "sql",
                "storage",
                "store",
                "model",
                "schema",
                "chroma",
                "metadata",
            )
        ):
            boost += 0.18
        if lower.endswith(("store.py", "indexer.py", "retriever.py", "config.py")):
            boost += 0.22
    if {"route", "routes", "routing", "api", "endpoint"} & query_terms:
        if any(
            token in lower
            for token in ("route", "routing", "router", "view", "endpoint", "controller", "handler")
        ):
            boost += 0.16
        if lower.endswith(("main.py", "main.ts", "main.tsx")):
            boost += 0.28
    if "/compiled/" in lower or lower.endswith((".min.js", ".bundle.js")):
        boost -= 0.3
    return boost


def _source_quality_boost(path: str, query_terms: set[str]) -> float:
    lower = path.lower()
    implementation_query = bool(
        {
            "authentication",
            "auth",
            "login",
            "database",
            "db",
            "route",
            "routes",
            "api",
            "endpoint",
        }
        & query_terms
    )
    if not implementation_query:
        return 0.0
    boost = 0.0
    if any(
        part in lower.split("/")
        for part in ("test", "tests", "docs", "doc", "docs_src", "examples", "scripts")
    ):
        boost -= 0.24
    if lower.startswith(("docs_src/", "tests/", "test/", "scripts/", ".github/")):
        boost -= 0.22
    if lower.endswith((".md", ".rst", ".txt")):
        boost -= 0.22
    if lower.endswith(
        (".py", ".ts", ".tsx", ".js", ".jsx", ".java", ".go", ".rs", ".cs", ".kt", ".kts", ".php")
    ):
        boost += 0.16
    return boost


def citations_for(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "path": chunk["path"],
            "file": chunk["path"],
            "line_start": chunk["line_start"],
            "line_end": chunk["line_end"],
            "start_line": chunk["line_start"],
            "end_line": chunk["line_end"],
            "text": chunk.get("text", "")[:700],
            "score": chunk["score"],
            "vector_score": chunk["vector_score"],
            "rerank_score": chunk["rerank_score"],
            "symbol": chunk.get("symbol"),
            "kind": chunk.get("kind"),
        }
        for chunk in chunks
    ]
