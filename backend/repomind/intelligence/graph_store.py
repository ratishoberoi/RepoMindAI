from __future__ import annotations

from collections import Counter, deque
from pathlib import PurePosixPath
from typing import Any

from repomind.core.config import get_settings


def graph_backend_status() -> dict[str, Any]:
    settings = get_settings()
    return {
        "backend": "neo4j" if settings.neo4j_uri else "projection",
        "configured": bool(settings.neo4j_uri),
        "uri": settings.neo4j_uri or "",
        "available": _neo4j_driver() is not None if settings.neo4j_uri else False,
    }


def sync_repository_graph(summary: dict[str, Any]) -> dict[str, Any]:
    """Persist graph evidence when Neo4j is configured, otherwise return queryable projection stats."""
    projection = build_graph_projection(summary)
    settings = get_settings()
    if not settings.neo4j_uri:
        return {"status": "projection-only", **projection["metrics"]}
    driver_factory = _neo4j_driver()
    if driver_factory is None:
        return {"status": "neo4j-driver-unavailable", **projection["metrics"]}
    try:
        with driver_factory(
            settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password)
        ).session() as session:
            _write_projection(session, projection)
    except Exception as exc:
        return {"status": "neo4j-sync-failed", "error": str(exc), **projection["metrics"]}
    return {"status": "neo4j-synced", **projection["metrics"]}


def query_repository_graph(
    summary: dict[str, Any],
    query: str = "overview",
    source: str = "",
    target: str = "",
    depth: int = 2,
) -> dict[str, Any]:
    projection = build_graph_projection(summary)
    if query == "hotspots":
        return {
            "query": query,
            "backend": graph_backend_status(),
            "nodes": sorted(
                projection["nodes"],
                key=lambda node: node.get("risk_score", 0) + node.get("degree", 0),
                reverse=True,
            )[:50],
            "edges": projection["edges"][:200],
        }
    if query == "ownership":
        return {
            "query": query,
            "backend": graph_backend_status(),
            "nodes": [
                node
                for node in projection["nodes"]
                if node["kind"] in {"owner", "team", "service", "domain", "repository"}
            ],
            "edges": [
                edge
                for edge in projection["edges"]
                if edge["relation"] in {"OWNS", "CONTAINS", "LINKED_TO"}
            ],
        }
    if query in {"shortest_path", "dependency", "blast_radius", "security_propagation"}:
        traversal = traverse_graph(projection, query, source=source, target=target, depth=depth)
        return {"query": query, "backend": graph_backend_status(), **traversal}
    return {"query": query, "backend": graph_backend_status(), **projection}


def traverse_graph(
    projection: dict[str, Any],
    mode: str,
    source: str = "",
    target: str = "",
    depth: int = 2,
) -> dict[str, Any]:
    nodes = {node["id"]: node for node in projection["nodes"]}
    source_id = _resolve_node_id(nodes, source)
    target_id = _resolve_node_id(nodes, target)
    if mode == "shortest_path" and source_id and target_id:
        edge_ids = _shortest_path_edges(projection["edges"], source_id, target_id)
    elif mode == "security_propagation":
        risk_nodes = [
            node["id"]
            for node in projection["nodes"]
            if node.get("kind") in {"risk", "security_finding"}
        ]
        edge_ids = _multi_source_edges(projection["edges"], risk_nodes[:50], max(1, min(depth, 4)))
    elif mode == "dependency":
        starts = (
            [source_id]
            if source_id
            else [node["id"] for node in projection["nodes"] if node.get("kind") == "repository"]
        )
        edge_ids = _filtered_traversal_edges(
            projection["edges"],
            [item for item in starts if item],
            {"DEPENDS_ON", "USES", "IMPORTS", "CALLS"},
            max(1, min(depth, 5)),
        )
    else:
        starts = (
            [source_id]
            if source_id
            else [node["id"] for node in projection["nodes"] if node.get("kind") == "repository"]
        )
        edge_ids = _multi_source_edges(
            projection["edges"], [item for item in starts if item], max(1, min(depth, 4))
        )
    selected_edges = [edge for index, edge in enumerate(projection["edges"]) if index in edge_ids]
    selected_node_ids = {edge["source"] for edge in selected_edges} | {
        edge["target"] for edge in selected_edges
    }
    if source_id:
        selected_node_ids.add(source_id)
    if target_id:
        selected_node_ids.add(target_id)
    return {
        "mode": mode,
        "source": source_id,
        "target": target_id,
        "depth": depth,
        "nodes": [nodes[node_id] for node_id in selected_node_ids if node_id in nodes],
        "edges": selected_edges,
        "metrics": projection["metrics"],
    }


def build_graph_projection(summary: dict[str, Any]) -> dict[str, Any]:
    repo = summary.get("repository", {})
    repo_id = repo.get("id", repo.get("name", "repository"))
    repo_name = repo.get("name", repo_id)
    nodes: dict[str, dict[str, Any]] = {
        f"repo:{repo_id}": {
            "id": f"repo:{repo_id}",
            "label": repo_name,
            "kind": "repository",
            "repository": repo_name,
            "risk_score": _risk(summary),
        }
    }
    edges: list[dict[str, Any]] = []
    degree = Counter()

    def add_node(node_id: str, label: str, kind: str, **extra: Any) -> None:
        nodes[node_id] = {
            "id": node_id,
            "label": label,
            "kind": kind,
            "labels": _labels(kind),
            **extra,
        }

    def add_edge(source: str, target: str, relation: str, **extra: Any) -> None:
        edges.append({"source": source, "target": target, "relation": relation.upper(), **extra})
        degree[source] += 1
        degree[target] += 1

    for file in summary.get("files", [])[:10000]:
        path = file.get("relative_path")
        if not path:
            continue
        directory = str(PurePosixPath(path).parent)
        if directory and directory != ".":
            parent = f"repo:{repo_id}"
            parts = []
            for part in PurePosixPath(directory).parts:
                parts.append(part)
                dir_path = "/".join(parts)
                dir_id = f"directory:{repo_id}:{dir_path}"
                add_node(dir_id, dir_path, "directory")
                add_edge(parent, dir_id, "CONTAINS")
                parent = dir_id
        node_id = f"file:{repo_id}:{path}"
        add_node(node_id, path, "file", language=file.get("language"), size=file.get("size", 0))
        add_edge(
            f"directory:{repo_id}:{directory}"
            if directory and directory != "."
            else f"repo:{repo_id}",
            node_id,
            "CONTAINS",
        )

    for parsed in summary.get("parsed", [])[:10000]:
        path = parsed.get("relative_path")
        file_id = f"file:{repo_id}:{path}"
        if not path or file_id not in nodes:
            continue
        for class_payload in parsed.get("classes", [])[:100]:
            class_name = _symbol_name(class_payload)
            class_id = f"class:{repo_id}:{path}:{class_name}"
            add_node(class_id, str(class_name), "class", file=path)
            add_edge(file_id, class_id, "CONTAINS")
        for function_payload in parsed.get("functions", [])[:200]:
            function = _symbol_name(function_payload)
            function_id = f"function:{repo_id}:{path}:{function}"
            add_node(function_id, str(function), "function", file=path)
            add_edge(file_id, function_id, "CONTAINS")
        for route in parsed.get("routes", [])[:100]:
            if not isinstance(route, dict):
                continue
            route_label = f"{route.get('method', 'GET')} {route.get('path', '')}"
            api_id = f"api:{repo_id}:{path}:{route_label}"
            add_node(
                api_id,
                route_label,
                "api",
                file=path,
                method=route.get("method"),
                path=route.get("path"),
            )
            add_edge(file_id, api_id, "EXPOSES")

    for domain in summary.get("knowledge_graph", {}).get("domains", []):
        name = str(domain.get("name", "domain"))
        node_id = f"domain:{repo_id}:{name}"
        add_node(
            node_id,
            name,
            "domain",
            role=domain.get("role"),
            file_count=domain.get("file_count", 0),
        )
        service_id = f"service:{repo_id}:{name}"
        add_node(service_id, name, "service", role=domain.get("role"), domain=name)
        add_edge(f"repo:{repo_id}", service_id, "CONTAINS")
        add_edge(service_id, node_id, "LINKED_TO")
        owner = _owner_for_domain(repo_name, name)
        team = owner["team"]
        owner_id = f"owner:{team}"
        add_node(owner_id, team, "owner", bus_factor=owner["bus_factor"])
        add_edge(owner_id, service_id, "OWNS", confidence=owner["confidence"])
        for file_path in domain.get("sample_files", [])[:20]:
            file_id = f"file:{repo_id}:{file_path}"
            if file_id in nodes:
                add_edge(service_id, file_id, "CONTAINS")

    for edge in summary.get("graph", {}).get("edges", [])[:10000]:
        source = f"file:{repo_id}:{edge.get('source')}"
        target = f"file:{repo_id}:{edge.get('target')}"
        if source in nodes and target in nodes:
            add_edge(source, target, "IMPORTS" if edge.get("relation") == "imports" else "CALLS")

    for finding in summary.get("security", {}).get("findings", [])[:1000]:
        path = finding.get("path", "")
        node_id = f"risk:{repo_id}:{finding.get('rule_id', 'risk')}:{path}:{finding.get('line', 1)}"
        add_node(
            node_id,
            finding.get("message", "Security finding"),
            "security_finding",
            severity=finding.get("severity"),
            owasp=finding.get("owasp"),
            cwe=finding.get("cwe"),
            cvss=finding.get("cvss"),
            risk_score=_severity_score(finding.get("severity")),
        )
        file_id = f"file:{repo_id}:{path}"
        if file_id in nodes:
            add_edge(node_id, file_id, "AFFECTS")

    for dependency in _dependencies(summary):
        node_id = f"dependency:{dependency}"
        add_node(node_id, dependency, "dependency")
        add_edge(f"repo:{repo_id}", node_id, "DEPENDS_ON")
        add_edge(f"repo:{repo_id}", node_id, "USES")

    for report_name, report_path in summary.get("reports", {}).items():
        report_id = f"report:{repo_id}:{report_name}"
        add_node(report_id, report_name, "report", path=report_path)
        add_edge(report_id, f"repo:{repo_id}", "LINKED_TO")

    for node_id, count in degree.items():
        nodes[node_id]["degree"] = count

    return {
        "nodes": list(nodes.values()),
        "edges": edges,
        "metrics": {
            "node_count": len(nodes),
            "edge_count": len(edges),
            "repository_count": 1,
            "risk_count": sum(
                1 for node in nodes.values() if node["kind"] in {"risk", "security_finding"}
            ),
            "owner_count": sum(1 for node in nodes.values() if node["kind"] == "owner"),
            "graph_density": _density(len(nodes), len(edges)),
            "graph_health": _graph_health(nodes, edges),
        },
    }


def _write_projection(session: Any, projection: dict[str, Any]) -> None:
    session.run(
        "CREATE CONSTRAINT repomind_node_id IF NOT EXISTS FOR (n:RepoMindNode) REQUIRE n.id IS UNIQUE"
    )
    for node in projection["nodes"]:
        session.run(
            "MERGE (n:RepoMindNode {id: $id}) SET n += $props, n.kind = $kind",
            id=node["id"],
            kind=node["kind"],
            props=node,
        )
    for edge in projection["edges"]:
        relation = _relationship_type(edge["relation"])
        session.run(
            f"""
            MATCH (a:RepoMindNode {{id: $source}})
            MATCH (b:RepoMindNode {{id: $target}})
            MERGE (a)-[r:{relation}]->(b)
            SET r += $props
            """,
            source=edge["source"],
            target=edge["target"],
            props=edge,
        )


def _neo4j_driver() -> Any:
    try:
        from neo4j import GraphDatabase

        return GraphDatabase.driver
    except Exception:
        return None


def _owner_for_domain(repo_name: str, domain: str) -> dict[str, Any]:
    lower = f"{repo_name}/{domain}".lower()
    if any(token in lower for token in ("auth", "security", "session")):
        return {"team": "Security Platform", "bus_factor": 2, "confidence": 0.78}
    if any(token in lower for token in ("db", "model", "data", "store")):
        return {"team": "Data Platform", "bus_factor": 2, "confidence": 0.72}
    if any(token in lower for token in ("front", "ui", "component", "page")):
        return {"team": "Product Experience", "bus_factor": 3, "confidence": 0.68}
    if any(token in lower for token in ("infra", "deploy", "docker", "ci")):
        return {"team": "Infrastructure", "bus_factor": 2, "confidence": 0.7}
    return {"team": "Core Engineering", "bus_factor": 1, "confidence": 0.55}


def _dependencies(summary: dict[str, Any]) -> list[str]:
    deps = []
    deps.extend(summary.get("stack", {}).get("frameworks", []))
    deps.extend(summary.get("stack", {}).get("package_managers", []))
    return [str(item) for item in deps if item]


def _labels(kind: str) -> list[str]:
    mapping = {
        "repository": ["RepoMindNode", "Repository"],
        "directory": ["RepoMindNode", "Directory"],
        "file": ["RepoMindNode", "File"],
        "class": ["RepoMindNode", "Class"],
        "function": ["RepoMindNode", "Function"],
        "dependency": ["RepoMindNode", "Dependency"],
        "api": ["RepoMindNode", "API"],
        "risk": ["RepoMindNode", "Risk"],
        "security_finding": ["RepoMindNode", "SecurityFinding"],
        "report": ["RepoMindNode", "Report"],
        "owner": ["RepoMindNode", "Owner"],
        "service": ["RepoMindNode", "Service"],
        "domain": ["RepoMindNode", "Domain"],
    }
    return mapping.get(kind, ["RepoMindNode"])


def _symbol_name(payload: Any) -> str:
    if isinstance(payload, dict):
        return str(payload.get("name") or payload.get("handler") or "symbol")
    return str(payload)


def _relationship_type(relation: str) -> str:
    allowed = {
        "CALLS",
        "IMPORTS",
        "DEPENDS_ON",
        "OWNS",
        "USES",
        "EXPOSES",
        "AFFECTS",
        "CONTAINS",
        "LINKED_TO",
    }
    normalized = str(relation).upper()
    return normalized if normalized in allowed else "LINKED_TO"


def _density(node_count: int, edge_count: int) -> float:
    if node_count <= 1:
        return 0.0
    return round(edge_count / (node_count * (node_count - 1)), 5)


def _graph_health(nodes: dict[str, dict[str, Any]], edges: list[dict[str, Any]]) -> int:
    if not nodes:
        return 0
    connected = {edge["source"] for edge in edges} | {edge["target"] for edge in edges}
    orphan_ratio = 1 - (len(connected) / max(len(nodes), 1))
    risk_ratio = sum(1 for node in nodes.values() if node.get("kind") == "security_finding") / max(
        len(nodes), 1
    )
    return max(0, min(100, round(100 - orphan_ratio * 45 - risk_ratio * 35)))


def _resolve_node_id(nodes: dict[str, dict[str, Any]], query: str) -> str:
    if not query:
        return ""
    if query in nodes:
        return query
    lower = query.lower()
    for node_id, node in nodes.items():
        if lower in node_id.lower() or lower in str(node.get("label", "")).lower():
            return node_id
    return ""


def _shortest_path_edges(edges: list[dict[str, Any]], source: str, target: str) -> set[int]:
    adjacency: dict[str, list[tuple[str, int]]] = {}
    for index, edge in enumerate(edges):
        adjacency.setdefault(edge["source"], []).append((edge["target"], index))
        adjacency.setdefault(edge["target"], []).append((edge["source"], index))
    queue: deque[tuple[str, list[int]]] = deque([(source, [])])
    seen = {source}
    while queue:
        node, path = queue.popleft()
        if node == target:
            return set(path)
        for next_node, edge_index in adjacency.get(node, []):
            if next_node not in seen:
                seen.add(next_node)
                queue.append((next_node, [*path, edge_index]))
    return set()


def _multi_source_edges(edges: list[dict[str, Any]], sources: list[str], depth: int) -> set[int]:
    adjacency: dict[str, list[tuple[str, int]]] = {}
    for index, edge in enumerate(edges):
        adjacency.setdefault(edge["source"], []).append((edge["target"], index))
        adjacency.setdefault(edge["target"], []).append((edge["source"], index))
    selected: set[int] = set()
    queue: deque[tuple[str, int]] = deque((source, 0) for source in sources)
    seen = set(sources)
    while queue:
        node, distance = queue.popleft()
        if distance >= depth:
            continue
        for next_node, edge_index in adjacency.get(node, []):
            selected.add(edge_index)
            if next_node not in seen:
                seen.add(next_node)
                queue.append((next_node, distance + 1))
    return selected


def _filtered_traversal_edges(
    edges: list[dict[str, Any]], sources: list[str], relations: set[str], depth: int
) -> set[int]:
    filtered = [
        (index, edge)
        for index, edge in enumerate(edges)
        if str(edge.get("relation", "")).upper() in relations
    ]
    adjacency: dict[str, list[tuple[str, int]]] = {}
    for index, edge in filtered:
        adjacency.setdefault(edge["source"], []).append((edge["target"], index))
    selected: set[int] = set()
    queue: deque[tuple[str, int]] = deque((source, 0) for source in sources)
    seen = set(sources)
    while queue:
        node, distance = queue.popleft()
        if distance >= depth:
            continue
        for next_node, edge_index in adjacency.get(node, []):
            selected.add(edge_index)
            if next_node not in seen:
                seen.add(next_node)
                queue.append((next_node, distance + 1))
    return selected


def _risk(summary: dict[str, Any]) -> float:
    scores = summary.get("scores", {})
    return round(100 - float(scores.get("cto", scores.get("production_readiness", 50))), 1)


def _severity_score(severity: Any) -> int:
    return {"critical": 95, "high": 78, "medium": 55, "low": 25}.get(str(severity).lower(), 35)
