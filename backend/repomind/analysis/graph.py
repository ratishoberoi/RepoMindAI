from __future__ import annotations

from pathlib import Path

import networkx as nx


def build_dependency_graph(files: list[dict], parsed: list[dict]) -> dict:
    graph = nx.DiGraph()
    known_modules = {Path(item["relative_path"]).with_suffix("").as_posix(): item["relative_path"] for item in files}
    for item in files:
        graph.add_node(item["relative_path"], kind="file", language=item["language"], size=item["size"])
    for item in parsed:
        source = item["relative_path"]
        for imported in item.get("imports", []):
            target = _resolve_import(imported, known_modules)
            graph.add_node(target, kind="module" if target == imported else "file")
            graph.add_edge(source, target, relation="imports")
        for fn in item.get("functions", []):
            fn_node = f"{source}::{fn['name']}"
            graph.add_node(fn_node, kind="function", line=fn.get("line"))
            graph.add_edge(source, fn_node, relation="defines")
        for method in item.get("methods", []):
            owner = method.get("class") or "module"
            method_node = f"{source}::{owner}.{method['name']}"
            graph.add_node(method_node, kind="method", line=method.get("line"), owner=owner)
            graph.add_edge(source, method_node, relation="defines")
        for cls in item.get("classes", []):
            cls_node = f"{source}::{cls['name']}"
            graph.add_node(cls_node, kind="class", line=cls.get("line"))
            graph.add_edge(source, cls_node, relation="defines")
        for route in item.get("routes", []):
            if isinstance(route, dict):
                route_id = f"{source}::{route.get('method', 'ROUTE')} {route.get('path', '')}"
                graph.add_node(route_id, kind="route", line=route.get("line"), method=route.get("method"), path=route.get("path"))
                graph.add_edge(source, route_id, relation="exposes")
        for model in item.get("database_models", []):
            model_node = f"{source}::{model['name']}"
            graph.add_node(model_node, kind="database_model", line=model.get("line"), orm=model.get("orm"))
            graph.add_edge(source, model_node, relation="models")
    centrality = nx.degree_centrality(graph) if graph.nodes else {}
    important = sorted(centrality.items(), key=lambda item: item[1], reverse=True)[:10]
    return {
        "nodes": [{"id": node, **attrs} for node, attrs in graph.nodes(data=True)],
        "edges": [{"source": a, "target": b, **attrs} for a, b, attrs in graph.edges(data=True)],
        "important_nodes": [{"id": node, "score": score} for node, score in important],
    }


def _resolve_import(imported: str, known_modules: dict[str, str]) -> str:
    normalized = imported.replace(".", "/")
    return known_modules.get(normalized, imported)
