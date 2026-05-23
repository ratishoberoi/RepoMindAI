from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


def extract_architecture(files: list[dict], parsed: list[dict], stack: dict[str, Any], graph: dict[str, Any]) -> dict[str, Any]:
    paths = [item["relative_path"] for item in files]
    top_dirs = sorted({p.split("/", 1)[0] for p in paths if "/" in p})
    route_files = [item["relative_path"] for item in parsed if item.get("routes")]
    db_model_files = [item["relative_path"] for item in parsed if item.get("database_models")]
    components = _components(paths)
    important = [node["id"] for node in graph.get("important_nodes", []) if "::" not in node["id"]][:12]
    diagrams = {
        "system": _system_diagram(stack, components, route_files, db_model_files),
        "component": _component_diagram(components),
        "dependency": _dependency_diagram(graph),
        "service": _service_diagram(parsed),
        "data_flow": _data_flow_diagram(route_files, db_model_files),
    }
    return {
        "style": _architecture_style(paths, stack),
        "top_level_directories": top_dirs[:20],
        "important_files": important,
        "route_files": route_files,
        "database_model_files": db_model_files,
        "components": components,
        "diagrams": diagrams,
        "summary": (
            f"Detected {len(components)} repository components across {len(files)} files. "
            f"Framework signals: {', '.join(stack.get('frameworks') or ['none detected'])}. "
            f"Architecture evidence includes {len(route_files)} route files and {len(db_model_files)} database model files."
        ),
    }


def _components(paths: list[str]) -> list[dict[str, Any]]:
    groups: dict[str, list[str]] = defaultdict(list)
    for path in paths:
        root = path.split("/", 1)[0] if "/" in path else Path(path).stem
        groups[root].append(path)
    ranked = sorted(groups.items(), key=lambda item: len(item[1]), reverse=True)[:14]
    return [
        {
            "name": name,
            "file_count": len(component_paths),
            "files": sorted(component_paths)[:8],
            "role": _component_role(name, component_paths),
        }
        for name, component_paths in ranked
    ]


def _component_role(name: str, paths: list[str]) -> str:
    lower = " ".join([name.lower(), *[path.lower() for path in paths[:20]]])
    if any(token in lower for token in ("api", "route", "router", "view", "controller")):
        return "API surface"
    if any(token in lower for token in ("db", "database", "model", "schema", "migration")):
        return "Data access"
    if any(token in lower for token in ("test", "spec")):
        return "Tests"
    if any(token in lower for token in ("frontend", "component", "app", "page")):
        return "User interface"
    if any(token in lower for token in ("security", "auth", "login")):
        return "Security/authentication"
    if any(token in lower for token in ("docs", "readme")):
        return "Documentation"
    return "Application code"


def _system_diagram(stack: dict[str, Any], components: list[dict[str, Any]], route_files: list[str], db_files: list[str]) -> str:
    framework = (stack.get("frameworks") or ["Application"])[0]
    route_label = _file_label(route_files[:2]) if route_files else "no route file detected"
    db_label = _file_label(db_files[:2]) if db_files else "no database model file detected"
    component_lines = "\n".join(
        f'  App --> C{idx}["{_clean(component["name"])} ({_clean(component["role"])})<br/>{_file_label(component["files"][:2])}"]'
        for idx, component in enumerate(components[:6], start=1)
    )
    return f"""graph TD
  User["Repository analyst"] --> App["{_clean(framework)} repository intelligence"]
  App --> Routes["Routes<br/>{_clean(route_label)}"]
  App --> Data["Data models<br/>{_clean(db_label)}"]
{component_lines or '  App --> Files["Repository files"]'}"""


def _component_diagram(components: list[dict[str, Any]]) -> str:
    lines = ["graph LR"]
    for idx, component in enumerate(components[:10], start=1):
        files = _file_label(component["files"][:2])
        lines.append(f'  C{idx}["{_clean(component["name"])}<br/>{_clean(component["role"])}<br/>{_clean(files)}"]')
        if idx > 1:
            lines.append(f"  C1 --> C{idx}")
    return "\n".join(lines)


def _dependency_diagram(graph: dict[str, Any]) -> str:
    edges = []
    for edge in graph.get("edges", []):
        if edge.get("relation") != "imports":
            continue
        source = edge["source"]
        target = edge["target"]
        if "::" in source or "::" in target:
            continue
        edges.append((source, target))
        if len(edges) >= 28:
            break
    if not edges:
        return 'graph TD\n  "repository files" --> "no imports resolved"'
    lines = ["graph TD"]
    for source, target in edges:
        lines.append(f'  "{_clean(source)}" --> "{_clean(target)}"')
    return "\n".join(lines)


def _service_diagram(parsed: list[dict[str, Any]]) -> str:
    route_rows = []
    for item in parsed:
        for route in item.get("routes", []):
            if isinstance(route, dict):
                route_rows.append((item["relative_path"], route.get("method", "ROUTE"), route.get("path", "")))
            else:
                route_rows.append((item["relative_path"], "ROUTE", str(route)))
    if not route_rows:
        return 'graph LR\n  Client --> App["No service routes detected"]'
    lines = ["graph LR", '  Client["Client"] --> Gateway["Application routes"]']
    for idx, (path, method, route_path) in enumerate(route_rows[:16], start=1):
        lines.append(f'  Gateway --> R{idx}["{_clean(method)} {_clean(route_path)}<br/>{_clean(path)}"]')
    return "\n".join(lines)


def _data_flow_diagram(route_files: list[str], db_files: list[str]) -> str:
    lines = ["graph TD", '  Input["Request / repository question"] --> Service["Application service"]']
    if route_files:
        lines.append(f'  Service --> Routes["Route handlers<br/>{_clean(_file_label(route_files[:4]))}"]')
    if db_files:
        lines.append(f'  Routes --> Models["Database models<br/>{_clean(_file_label(db_files[:4]))}"]')
        lines.append('  Models --> Store["Database / persistence layer"]')
    else:
        lines.append('  Service --> Files["Repository files and package metadata"]')
    lines.append('  Service --> Output["Reports, diagrams, scores, cited answers"]')
    return "\n".join(lines)


def _architecture_style(paths: list[str], stack: dict[str, Any]) -> str:
    if any(p.startswith("apps/") or p.startswith("packages/") for p in paths):
        return "Monorepo"
    if "Next.js" in stack.get("frameworks", []):
        return "Frontend web application"
    if "FastAPI" in stack.get("frameworks", []):
        return "API service"
    if any(p.startswith("frontend/") for p in paths) and any(p.startswith("backend/") for p in paths):
        return "Full-stack application"
    counts = Counter(path.split("/", 1)[0] for path in paths if "/" in path)
    if len(counts) > 5:
        return "Multi-component repository"
    return "General software repository"


def _file_label(paths: list[str]) -> str:
    if not paths:
        return "no files"
    return "<br/>".join(paths)


def _clean(value: str) -> str:
    return str(value).replace('"', "'").replace("\n", " ")[:180]
