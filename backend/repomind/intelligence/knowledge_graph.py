from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


def build_repository_knowledge_graph(
    files: list[dict[str, Any]],
    parsed: list[dict[str, Any]],
    graph: dict[str, Any],
    security: dict[str, Any],
) -> dict[str, Any]:
    entities: list[dict[str, Any]] = []
    relations: list[dict[str, Any]] = []
    file_entities = {item["relative_path"]: _file_entity(item) for item in files}
    entities.extend(file_entities.values())

    for item in parsed:
        source = item["relative_path"]
        for route in item.get("routes", []):
            if isinstance(route, dict):
                entity_id = f"route:{source}:{route.get('method')}:{route.get('path')}"
                entities.append(
                    _entity(
                        entity_id,
                        route.get("path") or "<dynamic>",
                        "route",
                        source,
                        route.get("line"),
                        method=route.get("method"),
                        handler=route.get("handler"),
                    )
                )
                relations.append(_relation(source, entity_id, "exposes"))
        for model in item.get("database_models", []):
            entity_id = f"model:{source}:{model.get('name')}"
            entities.append(
                _entity(
                    entity_id,
                    model.get("name") or "model",
                    "data_model",
                    source,
                    model.get("line"),
                    orm=model.get("orm"),
                )
            )
            relations.append(_relation(source, entity_id, "persists"))
        for symbol_type in ("classes", "functions", "methods"):
            for symbol in item.get(symbol_type, []):
                name = symbol.get("name")
                if not name:
                    continue
                owner = symbol.get("class")
                label = f"{owner}.{name}" if owner else name
                entity_id = f"symbol:{source}:{symbol_type}:{label}"
                entities.append(
                    _entity(
                        entity_id,
                        label,
                        "symbol",
                        source,
                        symbol.get("line"),
                        symbol_type=symbol_type,
                    )
                )
                relations.append(_relation(source, entity_id, "defines"))

    for edge in graph.get("edges", []):
        source = edge.get("source")
        target = edge.get("target")
        if source and target:
            relations.append(_relation(source, target, edge.get("relation", "depends_on")))

    sensitive_files = _security_surface(security)
    domains = _domains(files, parsed, sensitive_files)
    hotspots = _hotspots(files, relations, sensitive_files)
    return {
        "entities": _dedupe_entities(entities),
        "relations": _dedupe_relations(relations),
        "domains": domains,
        "hotspots": hotspots,
        "metrics": {
            "entities": len(_dedupe_entities(entities)),
            "relations": len(_dedupe_relations(relations)),
            "domains": len(domains),
            "security_hotspots": len(sensitive_files),
            "route_count": sum(1 for item in entities if item.get("kind") == "route"),
            "data_model_count": sum(1 for item in entities if item.get("kind") == "data_model"),
        },
    }


def _file_entity(item: dict[str, Any]) -> dict[str, Any]:
    path = item["relative_path"]
    return _entity(
        path,
        Path(path).name,
        "file",
        path,
        None,
        language=item.get("language"),
        size=item.get("size"),
        layer=_layer(path),
    )


def _entity(
    entity_id: str,
    label: str,
    kind: str,
    path: str,
    line: int | None = None,
    **attrs: Any,
) -> dict[str, Any]:
    return {"id": entity_id, "label": label, "kind": kind, "path": path, "line": line, **attrs}


def _relation(source: str, target: str, relation: str) -> dict[str, str]:
    return {"source": source, "target": target, "relation": relation}


def _domains(
    files: list[dict[str, Any]], parsed: list[dict[str, Any]], sensitive_files: set[str]
) -> list[dict[str, Any]]:
    grouped: dict[str, list[str]] = defaultdict(list)
    route_counts: Counter[str] = Counter()
    model_counts: Counter[str] = Counter()
    for item in files:
        grouped[_domain_name(item["relative_path"])].append(item["relative_path"])
    for item in parsed:
        domain = _domain_name(item["relative_path"])
        route_counts[domain] += len(item.get("routes", []))
        model_counts[domain] += len(item.get("database_models", []))
    domains = []
    for name, paths in sorted(grouped.items(), key=lambda item: len(item[1]), reverse=True):
        domains.append(
            {
                "name": name,
                "file_count": len(paths),
                "routes": route_counts[name],
                "data_models": model_counts[name],
                "security_findings": sum(1 for path in paths if path in sensitive_files),
                "role": _domain_role(name, paths),
                "sample_files": sorted(paths)[:8],
            }
        )
    return domains[:24]


def _hotspots(
    files: list[dict[str, Any]], relations: list[dict[str, str]], sensitive_files: set[str]
) -> list[dict[str, Any]]:
    degree: Counter[str] = Counter()
    for relation in relations:
        degree[relation["source"]] += 1
        degree[relation["target"]] += 1
    file_paths = {item["relative_path"] for item in files}
    hotspots = []
    for path, score in degree.most_common(40):
        if path not in file_paths:
            continue
        risk = score + (8 if path in sensitive_files else 0)
        hotspots.append(
            {
                "path": path,
                "connectivity": score,
                "risk_score": risk,
                "reason": "security finding and dependency centrality"
                if path in sensitive_files
                else "dependency centrality",
            }
        )
    return sorted(hotspots, key=lambda item: item["risk_score"], reverse=True)[:20]


def _security_surface(security: dict[str, Any]) -> set[str]:
    return {
        finding.get("path", "")
        for finding in security.get("findings", [])
        if finding.get("severity") in {"critical", "high", "medium"}
    }


def _domain_name(path: str) -> str:
    parts = path.split("/")
    if len(parts) == 1:
        return Path(path).stem
    if parts[0] in {"src", "app", "backend", "frontend"} and len(parts) > 2:
        return "/".join(parts[:2])
    return parts[0]


def _domain_role(name: str, paths: list[str]) -> str:
    lower = " ".join([name.lower(), *[path.lower() for path in paths[:20]]])
    if any(token in lower for token in ("route", "api", "controller", "endpoint")):
        return "API boundary"
    if any(token in lower for token in ("db", "model", "schema", "migration")):
        return "Data layer"
    if any(token in lower for token in ("component", "page", "frontend", "ui")):
        return "User experience"
    if any(token in lower for token in ("security", "auth", "login", "session")):
        return "Trust boundary"
    if any(token in lower for token in ("test", "spec")):
        return "Verification"
    return "Product capability"


def _layer(path: str) -> str:
    lower = path.lower()
    if any(token in lower for token in ("route", "api", "controller", "main.py")):
        return "interface"
    if any(token in lower for token in ("db", "store", "model", "schema", "migration")):
        return "data"
    if any(token in lower for token in ("security", "auth", "session", "jwt")):
        return "security"
    if any(token in lower for token in ("test", "spec")):
        return "test"
    if any(token in lower for token in ("component", "page", "frontend")):
        return "presentation"
    return "application"


def _dedupe_entities(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    for item in items:
        by_id.setdefault(item["id"], item)
    return list(by_id.values())


def _dedupe_relations(items: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[tuple[str, str, str]] = set()
    unique = []
    for item in items:
        key = (item["source"], item["target"], item["relation"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique
