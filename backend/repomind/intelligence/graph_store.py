from __future__ import annotations

from collections import Counter
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


def query_repository_graph(summary: dict[str, Any], query: str = "overview") -> dict[str, Any]:
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
                if node["kind"] in {"owner", "team", "service", "repository"}
            ],
            "edges": [
                edge
                for edge in projection["edges"]
                if edge["relation"] in {"owns", "contains", "maintains"}
            ],
        }
    return {"query": query, "backend": graph_backend_status(), **projection}


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
        nodes[node_id] = {"id": node_id, "label": label, "kind": kind, **extra}

    def add_edge(source: str, target: str, relation: str, **extra: Any) -> None:
        edges.append({"source": source, "target": target, "relation": relation, **extra})
        degree[source] += 1
        degree[target] += 1

    for file in summary.get("files", [])[:10000]:
        path = file.get("relative_path")
        if not path:
            continue
        node_id = f"file:{repo_id}:{path}"
        add_node(node_id, path, "file", language=file.get("language"), size=file.get("size", 0))
        add_edge(f"repo:{repo_id}", node_id, "contains")

    for domain in summary.get("knowledge_graph", {}).get("domains", []):
        name = str(domain.get("name", "domain"))
        node_id = f"domain:{repo_id}:{name}"
        add_node(
            node_id,
            name,
            "service",
            role=domain.get("role"),
            file_count=domain.get("file_count", 0),
        )
        add_edge(f"repo:{repo_id}", node_id, "contains")
        owner = _owner_for_domain(repo_name, name)
        team = owner["team"]
        owner_id = f"owner:{team}"
        add_node(owner_id, team, "team", bus_factor=owner["bus_factor"])
        add_edge(owner_id, node_id, "owns", confidence=owner["confidence"])
        for file_path in domain.get("sample_files", [])[:20]:
            file_id = f"file:{repo_id}:{file_path}"
            if file_id in nodes:
                add_edge(node_id, file_id, "maintains")

    for edge in summary.get("graph", {}).get("edges", [])[:10000]:
        source = f"file:{repo_id}:{edge.get('source')}"
        target = f"file:{repo_id}:{edge.get('target')}"
        if source in nodes and target in nodes:
            add_edge(source, target, edge.get("relation", "imports"))

    for finding in summary.get("security", {}).get("findings", [])[:1000]:
        path = finding.get("path", "")
        node_id = f"risk:{repo_id}:{finding.get('rule_id', 'risk')}:{path}:{finding.get('line', 1)}"
        add_node(
            node_id,
            finding.get("message", "Security finding"),
            "risk",
            severity=finding.get("severity"),
            owasp=finding.get("owasp"),
            cwe=finding.get("cwe"),
            cvss=finding.get("cvss"),
            risk_score=_severity_score(finding.get("severity")),
        )
        file_id = f"file:{repo_id}:{path}"
        if file_id in nodes:
            add_edge(file_id, node_id, "security_finding")

    for dependency in _dependencies(summary):
        node_id = f"dependency:{dependency}"
        add_node(node_id, dependency, "dependency")
        add_edge(f"repo:{repo_id}", node_id, "dependency")

    for node_id, count in degree.items():
        nodes[node_id]["degree"] = count

    return {
        "nodes": list(nodes.values()),
        "edges": edges,
        "metrics": {
            "node_count": len(nodes),
            "edge_count": len(edges),
            "repository_count": 1,
            "risk_count": sum(1 for node in nodes.values() if node["kind"] == "risk"),
            "owner_count": sum(1 for node in nodes.values() if node["kind"] == "team"),
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
        session.run(
            """
            MATCH (a:RepoMindNode {id: $source})
            MATCH (b:RepoMindNode {id: $target})
            MERGE (a)-[r:RELATES_TO {relation: $relation}]->(b)
            SET r += $props
            """,
            source=edge["source"],
            target=edge["target"],
            relation=edge["relation"],
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


def _risk(summary: dict[str, Any]) -> float:
    scores = summary.get("scores", {})
    return round(100 - float(scores.get("cto", scores.get("production_readiness", 50))), 1)


def _severity_score(severity: Any) -> int:
    return {"critical": 95, "high": 78, "medium": 55, "low": 25}.get(str(severity).lower(), 35)
