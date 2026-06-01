from __future__ import annotations

import subprocess
from collections import Counter, defaultdict, deque
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
    clusters = _clusters(file_entities.values(), parsed, security)
    insights = _insights(files, parsed, relations, hotspots, sensitive_files)
    return {
        "entities": _dedupe_entities(entities),
        "relations": _dedupe_relations(relations),
        "relationships": _dedupe_relations(relations),
        "domains": domains,
        "hotspots": hotspots,
        "clusters": clusters,
        "insights": insights,
        "critical_path": _critical_path(relations, hotspots),
        "timeline": _timeline(files),
        "metrics": {
            "entities": len(_dedupe_entities(entities)),
            "relations": len(_dedupe_relations(relations)),
            "domains": len(domains),
            "security_hotspots": len(sensitive_files),
            "route_count": sum(1 for item in entities if item.get("kind") == "route"),
            "data_model_count": sum(1 for item in entities if item.get("kind") == "data_model"),
            "clusters": len(clusters),
            "graph_insights": len(insights),
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


def _clusters(
    files: Any, parsed: list[dict[str, Any]], security: dict[str, Any]
) -> list[dict[str, Any]]:
    cluster_tokens = {
        "Auth": ("auth", "login", "session", "jwt", "token", "user"),
        "API": ("api", "route", "router", "controller", "endpoint", "main.py"),
        "Database": ("db", "database", "model", "schema", "migration", "store"),
        "Security": ("security", "secret", "csrf", "cors", "permission"),
        "Payments": ("payment", "billing", "stripe", "checkout", "invoice"),
        "Infrastructure": ("docker", "deploy", "ci", ".github", "terraform", "k8s"),
        "Frontend": ("frontend", "component", "page", "view", "ui", "react", "next"),
    }
    paths = [item["path"] for item in files]
    sensitive = _security_surface(security)
    route_paths = {item["relative_path"] for item in parsed if item.get("routes")}
    clusters = []
    assigned: set[str] = set()
    for name, tokens in cluster_tokens.items():
        members = [path for path in paths if any(token in path.lower() for token in tokens)]
        if name == "API":
            members = sorted(set(members) | route_paths)
        if not members:
            continue
        assigned.update(members)
        clusters.append(
            {
                "name": name,
                "member_count": len(members),
                "members": sorted(members)[:80],
                "security_findings": sum(1 for path in members if path in sensitive),
                "collapsed": False,
                "description": _cluster_description(name),
            }
        )
    remaining = [path for path in paths if path not in assigned]
    if remaining:
        clusters.append(
            {
                "name": "Application",
                "member_count": len(remaining),
                "members": sorted(remaining)[:80],
                "security_findings": sum(1 for path in remaining if path in sensitive),
                "collapsed": False,
                "description": "Core product code outside named platform clusters.",
            }
        )
    return clusters


def _insights(
    files: list[dict[str, Any]],
    parsed: list[dict[str, Any]],
    relations: list[dict[str, str]],
    hotspots: list[dict[str, Any]],
    sensitive_files: set[str],
) -> list[dict[str, Any]]:
    degree: Counter[str] = Counter()
    for relation in relations:
        degree[relation["source"]] += 1
        degree[relation["target"]] += 1
    file_set = {item["relative_path"] for item in files}
    insights: list[dict[str, Any]] = []
    for item in parsed:
        symbols = sum(len(item.get(key, [])) for key in ("classes", "functions", "methods"))
        if symbols >= 18:
            insights.append(
                {
                    "type": "god_class_candidate",
                    "severity": "medium",
                    "title": "Large symbol concentration",
                    "entity": item["relative_path"],
                    "evidence": f"{symbols} symbols detected in one file.",
                }
            )
    for path, count in degree.most_common(8):
        if path in file_set and count >= 6:
            insights.append(
                {
                    "type": "dependency_bottleneck",
                    "severity": "high" if count >= 12 else "medium",
                    "title": "Dependency bottleneck",
                    "entity": path,
                    "evidence": f"{count} inbound/outbound relations.",
                }
            )
    for hotspot in hotspots[:8]:
        insights.append(
            {
                "type": "hotspot",
                "severity": "high" if hotspot.get("path") in sensitive_files else "medium",
                "title": "Architecture hotspot",
                "entity": hotspot.get("path"),
                "evidence": hotspot.get("reason"),
            }
        )
    for path in sorted(sensitive_files)[:8]:
        insights.append(
            {
                "type": "security_hotspot",
                "severity": "high",
                "title": "Security-sensitive file",
                "entity": path,
                "evidence": "Security scanner finding intersects architecture graph.",
            }
        )
    return insights[:30]


def _critical_path(
    relations: list[dict[str, str]], hotspots: list[dict[str, Any]]
) -> dict[str, Any]:
    if not hotspots:
        return {"path": [], "risk_score": 0, "reason": "No graph hotspots detected."}
    adjacency: dict[str, list[str]] = defaultdict(list)
    for relation in relations:
        adjacency[relation["source"]].append(relation["target"])
    source = hotspots[0]["path"]
    best = [source]
    queue: deque[tuple[str, list[str]]] = deque([(source, [source])])
    while queue:
        node, path = queue.popleft()
        if len(path) > len(best):
            best = path
        if len(path) >= 8:
            continue
        for target in adjacency.get(node, [])[:8]:
            if target in path:
                continue
            queue.append((target, path + [target]))
    return {
        "path": best,
        "risk_score": hotspots[0].get("risk_score", 0),
        "reason": hotspots[0].get("reason"),
    }


def _timeline(files: list[dict[str, Any]]) -> list[dict[str, Any]]:
    paths = [Path(item["relative_path"]) for item in files]
    repo_root = _common_git_root(paths)
    if not repo_root:
        return []
    try:
        output = subprocess.check_output(
            [
                "git",
                "-C",
                str(repo_root),
                "log",
                "--name-only",
                "--pretty=format:%ad|%h|%s",
                "--date=short",
                "-n",
                "40",
            ],
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=2,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    events = []
    current: dict[str, Any] | None = None
    for line in output.splitlines():
        if "|" in line:
            if current:
                events.append(current)
            date, commit, subject = line.split("|", 2)
            current = {"date": date, "commit": commit, "subject": subject, "files": []}
        elif line.strip() and current is not None:
            current["files"].append(line.strip())
    if current:
        events.append(current)
    return events[:20]


def _common_git_root(paths: list[Path]) -> Path | None:
    if not paths:
        return None
    # Analysis summaries use relative paths; git history is available only when current cwd is inside a repo.
    cwd = Path.cwd()
    try:
        subprocess.check_output(
            ["git", "-C", str(cwd), "rev-parse", "--show-toplevel"], stderr=subprocess.DEVNULL
        )
        return cwd
    except (OSError, subprocess.SubprocessError):
        return None


def _cluster_description(name: str) -> str:
    return {
        "Auth": "Identity, session, token, and user trust boundaries.",
        "API": "External request surface and route handlers.",
        "Database": "Persistence models, stores, schemas, and migrations.",
        "Security": "Security controls, scanners, secrets, and policy enforcement.",
        "Payments": "Checkout, billing, invoice, and payment provider flow.",
        "Infrastructure": "Deployment, container, and CI/CD infrastructure.",
        "Frontend": "User interface, pages, and client-side workflow.",
    }.get(name, "Repository capability cluster.")


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
