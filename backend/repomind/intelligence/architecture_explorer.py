from __future__ import annotations

from collections import Counter, defaultdict, deque
from typing import Any

FLOW_INTENTS = {
    "authentication": ("auth", "login", "session", "jwt", "token", "user"),
    "login": ("login", "signin", "session", "auth", "token"),
    "signup": ("signup", "register", "registration", "user", "account"),
    "payment": ("payment", "checkout", "stripe", "billing", "invoice"),
    "file_upload": ("upload", "file", "zip", "multipart", "attachment"),
    "data_flow": ("data", "store", "repository", "database", "model", "schema"),
    "notification": ("notification", "email", "webhook", "message", "event"),
}


def build_architecture_explorer(summary: dict[str, Any]) -> dict[str, Any]:
    parsed = summary.get("parsed", [])
    files = summary.get("files", [])
    graph = summary.get("graph", {})
    routes = _routes(parsed)
    models = _models(parsed)
    services = _services(files, parsed)
    external = _external_integrations(summary)
    flows = [
        _request_flow(name, tokens, routes, services, models, external, graph)
        for name, tokens in FLOW_INTENTS.items()
    ]
    dependency_flows = _dependency_flows(graph, files)
    return {
        "repository": summary.get("repository", {}),
        "entry_points": routes[:40],
        "services": services[:60],
        "models": models[:40],
        "external_integrations": external,
        "request_flows": flows,
        "dependency_flows": dependency_flows,
        "narratives": _narratives(summary, flows, dependency_flows),
        "onboarding_markdown": render_onboarding_markdown(summary, flows, dependency_flows),
    }


def render_onboarding_markdown(
    summary: dict[str, Any],
    flows: list[dict[str, Any]] | None = None,
    dependency_flows: list[dict[str, Any]] | None = None,
) -> str:
    flows = flows if flows is not None else build_architecture_explorer(summary)["request_flows"]
    dependency_flows = (
        dependency_flows
        if dependency_flows is not None
        else build_architecture_explorer(summary)["dependency_flows"]
    )
    arch = summary.get("architecture", {})
    stack = summary.get("stack", {})
    stats = summary.get("statistics", {})
    important = arch.get("important_files", [])[:12]
    modules = arch.get("components", [])[:10]
    flow_lines = [
        f"- **{flow['label']}**: {flow['confidence']} confidence through {len(flow['steps'])} traced steps."
        for flow in flows
        if flow.get("steps")
    ]
    module_lines = [
        f"- `{item.get('name')}`: {item.get('role')} ({item.get('file_count')} files)"
        for item in modules
    ]
    dependency_lines = [
        f"- `{flow['source']}` -> {' -> '.join(flow['path'][1:])}" for flow in dependency_flows[:8]
    ]
    return "\n".join(
        [
            "# ONBOARDING",
            "",
            f"Repository: `{summary.get('repository', {}).get('name', 'unknown')}`",
            "",
            "## System Overview",
            "",
            arch.get("summary", "No architecture summary available."),
            "",
            "## Startup Instructions",
            "",
            "- Install the package managers detected in the repository.",
            f"- Detected package managers: {', '.join(stack.get('package_managers') or ['none detected'])}.",
            f"- Detected frameworks: {', '.join(stack.get('frameworks') or ['none detected'])}.",
            "- Run the repository's documented test and development commands before changing architecture hotspots.",
            "",
            "## Architecture Map",
            "",
            f"- Architecture style: {arch.get('style', 'unknown')}",
            f"- Files analyzed: {stats.get('files', 0)}",
            f"- Routes detected: {stats.get('routes', 0)}",
            f"- Database models detected: {stats.get('database_models', 0)}",
            "",
            "## Key Modules",
            "",
            *(module_lines or ["- No module grouping detected."]),
            "",
            "## Request Flows",
            "",
            *(
                flow_lines
                or ["- No named request flows were detected from current route/file evidence."]
            ),
            "",
            "## Dependency Flow",
            "",
            *(dependency_lines or ["- No dependency paths were resolved."]),
            "",
            "## Critical Files",
            "",
            *([f"- `{path}`" for path in important] or ["- No critical files identified."]),
            "",
        ]
    )


def _routes(parsed: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for item in parsed:
        for route in item.get("routes", []):
            if not isinstance(route, dict):
                continue
            rows.append(
                {
                    "method": route.get("method", "ROUTE"),
                    "path": route.get("path", ""),
                    "handler": route.get("handler"),
                    "file": item.get("relative_path"),
                    "line": route.get("line"),
                    "domain": _domain(item.get("relative_path", "")),
                }
            )
    return rows


def _models(parsed: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for item in parsed:
        for model in item.get("database_models", []):
            rows.append(
                {
                    "name": model.get("name"),
                    "orm": model.get("orm"),
                    "file": item.get("relative_path"),
                    "line": model.get("line"),
                    "domain": _domain(item.get("relative_path", "")),
                }
            )
    return rows


def _services(files: list[dict[str, Any]], parsed: list[dict[str, Any]]) -> list[dict[str, Any]]:
    symbol_counts: Counter[str] = Counter()
    route_counts: Counter[str] = Counter()
    for item in parsed:
        path = item.get("relative_path", "")
        symbol_counts[path] += sum(
            len(item.get(key, [])) for key in ("classes", "functions", "methods")
        )
        route_counts[path] += len(item.get("routes", []))
    rows = []
    for item in files:
        path = item.get("relative_path", "")
        lower = path.lower()
        if (
            not any(
                token in lower
                for token in (
                    "service",
                    "api",
                    "route",
                    "controller",
                    "repository",
                    "store",
                    "model",
                    "client",
                    "auth",
                    "payment",
                    "upload",
                    "security",
                )
            )
            and not symbol_counts[path]
        ):
            continue
        rows.append(
            {
                "file": path,
                "domain": _domain(path),
                "layer": _layer(path),
                "symbols": symbol_counts[path],
                "routes": route_counts[path],
                "description": _describe_service(path),
            }
        )
    return sorted(rows, key=lambda item: (item["routes"], item["symbols"]), reverse=True)


def _external_integrations(summary: dict[str, Any]) -> list[dict[str, str]]:
    stack = summary.get("stack", {})
    integrations = []
    for framework in stack.get("frameworks", []):
        integrations.append({"name": framework, "type": "framework", "evidence": "stack detection"})
    for package in stack.get("package_managers", []):
        integrations.append(
            {"name": package, "type": "package manager", "evidence": "manifest detection"}
        )
    for item in summary.get("parsed", []):
        for env in item.get("env_vars", [])[:10]:
            name = env.get("name", "env var") if isinstance(env, dict) else str(env)
            integrations.append(
                {
                    "name": name,
                    "type": "configuration",
                    "evidence": item.get("relative_path", ""),
                }
            )
    return integrations[:40]


def _request_flow(
    intent: str,
    tokens: tuple[str, ...],
    routes: list[dict[str, Any]],
    services: list[dict[str, Any]],
    models: list[dict[str, Any]],
    external: list[dict[str, str]],
    graph: dict[str, Any],
) -> dict[str, Any]:
    matched_routes = [
        route
        for route in routes
        if _matches(
            route.get("path", "")
            + " "
            + str(route.get("handler", ""))
            + " "
            + route.get("file", ""),
            tokens,
        )
    ]
    matched_services = [
        service
        for service in services
        if _matches(service.get("file", "") + " " + service.get("description", ""), tokens)
    ]
    matched_models = [
        model
        for model in models
        if _matches(str(model.get("name", "")) + " " + model.get("file", ""), tokens)
    ]
    matched_external = [
        item
        for item in external
        if _matches(item.get("name", "") + " " + item.get("type", ""), tokens)
    ]
    if not matched_routes and intent == "data_flow":
        matched_routes = routes[:6]
    if not matched_models and intent == "data_flow":
        matched_models = models[:6]
    steps = _flow_steps(
        matched_routes[:6], matched_services[:8], matched_models[:6], matched_external[:5]
    )
    confidence = (
        "high"
        if matched_routes and (matched_services or matched_models)
        else "medium"
        if steps
        else "low"
    )
    return {
        "id": intent,
        "label": intent.replace("_", " ").title(),
        "confidence": confidence,
        "entry_points": matched_routes[:8],
        "services": matched_services[:10],
        "models": matched_models[:8],
        "dependencies": _related_dependencies(graph, matched_routes, matched_services),
        "external_integrations": matched_external[:8],
        "steps": steps,
        "sequence_diagram": _sequence_diagram(intent, steps),
        "summary": _flow_summary(intent, confidence, steps),
    }


def _flow_steps(
    routes: list[dict[str, Any]],
    services: list[dict[str, Any]],
    models: list[dict[str, Any]],
    external: list[dict[str, str]],
) -> list[dict[str, str]]:
    steps: list[dict[str, str]] = []
    if routes:
        route = routes[0]
        steps.append(
            {
                "layer": "Frontend",
                "component": "Client",
                "detail": f"Calls {route.get('method')} {route.get('path')}",
            }
        )
        steps.append(
            {
                "layer": "API",
                "component": route.get("file", "route"),
                "detail": str(route.get("handler") or route.get("path")),
            }
        )
    elif services:
        steps.append(
            {
                "layer": "Entry",
                "component": services[0]["file"],
                "detail": services[0]["description"],
            }
        )
    for service in services[:4]:
        steps.append(
            {
                "layer": service["layer"],
                "component": service["file"],
                "detail": service["description"],
            }
        )
    for model in models[:3]:
        steps.append(
            {
                "layer": "Database",
                "component": str(model.get("name") or model.get("file")),
                "detail": f"Persistence evidence in {model.get('file')}",
            }
        )
    for item in external[:2]:
        steps.append(
            {
                "layer": "External",
                "component": item["name"],
                "detail": f"{item['type']} from {item['evidence']}",
            }
        )
    return _dedupe_steps(steps)[:10]


def _sequence_diagram(intent: str, steps: list[dict[str, str]]) -> str:
    if not steps:
        return f"sequenceDiagram\n  participant Analyst\n  participant Repository\n  Analyst->>Repository: No {intent.replace('_', ' ')} flow detected"
    participants = []
    for step in steps:
        name = _participant(step["layer"])
        if name not in participants:
            participants.append(name)
    lines = ["sequenceDiagram", *[f"  participant {item}" for item in participants]]
    for left, right in zip(steps, steps[1:]):
        lines.append(
            f"  {_participant(left['layer'])}->>{_participant(right['layer'])}: {_clean(right['detail'])}"
        )
    if len(steps) == 1:
        lines.append(f"  Analyst->>{_participant(steps[0]['layer'])}: {_clean(steps[0]['detail'])}")
    return "\n".join(lines)


def _flow_summary(intent: str, confidence: str, steps: list[dict[str, str]]) -> str:
    if not steps:
        return f"No concrete {intent.replace('_', ' ')} flow was detected from current repository evidence."
    layers = " -> ".join(step["layer"] for step in steps)
    return (
        f"{intent.replace('_', ' ').title()} flow traced with {confidence} confidence across "
        f"{len(steps)} steps: {layers}."
    )


def _dependency_flows(graph: dict[str, Any], files: list[dict[str, Any]]) -> list[dict[str, Any]]:
    file_set = {item.get("relative_path") for item in files}
    adjacency: dict[str, list[str]] = defaultdict(list)
    indegree: Counter[str] = Counter()
    outdegree: Counter[str] = Counter()
    for edge in graph.get("edges", []):
        source = edge.get("source")
        target = edge.get("target")
        if not source or not target or "::" in source or "::" in target:
            continue
        adjacency[source].append(target)
        outdegree[source] += 1
        indegree[target] += 1
    starters = [item for item, _ in outdegree.most_common(16) if item in file_set]
    flows = []
    for source in starters:
        path = _longest_path(source, adjacency)
        if len(path) < 2:
            continue
        flows.append(
            {
                "source": source,
                "path": path,
                "length": len(path),
                "fan_out": outdegree[source],
                "fan_in_terminal": indegree[path[-1]],
            }
        )
    return flows[:12]


def _longest_path(source: str, adjacency: dict[str, list[str]]) -> list[str]:
    best = [source]
    queue: deque[tuple[str, list[str]]] = deque([(source, [source])])
    while queue:
        node, path = queue.popleft()
        if len(path) > len(best):
            best = path
        if len(path) >= 7:
            continue
        for target in adjacency.get(node, [])[:8]:
            if target in path:
                continue
            queue.append((target, path + [target]))
    return best


def _related_dependencies(
    graph: dict[str, Any], routes: list[dict[str, Any]], services: list[dict[str, Any]]
) -> list[dict[str, str]]:
    anchors = {item.get("file") for item in routes} | {item.get("file") for item in services}
    return [
        edge
        for edge in graph.get("edges", [])
        if edge.get("source") in anchors or edge.get("target") in anchors
    ][:20]


def _narratives(
    summary: dict[str, Any], flows: list[dict[str, Any]], dependency_flows: list[dict[str, Any]]
) -> dict[str, str]:
    repo = summary.get("repository", {}).get("name", "Repository")
    scores = summary.get("scores", {})
    detected = [flow["label"] for flow in flows if flow.get("steps")]
    return {
        "executive": f"{repo} exposes {len(detected)} traceable operating flows with CTO score {scores.get('cto', 'n/a')} and security score {scores.get('security', 'n/a')}. The strongest architecture evidence is {', '.join(detected[:4]) or 'limited route/service evidence'}.",
        "engineering": f"RepoMind mapped {len(summary.get('files', []))} files, {summary.get('statistics', {}).get('routes', 0)} routes, {summary.get('statistics', {}).get('database_models', 0)} data models, and {len(dependency_flows)} dependency paths. Use the sequence diagrams to trace request entry points to services and persistence.",
        "onboarding": "Start with the highlighted request flows, then inspect critical files and dependency paths before editing hotspots.",
    }


def _matches(text: str, tokens: tuple[str, ...]) -> bool:
    lower = text.lower()
    return any(token in lower for token in tokens)


def _domain(path: str) -> str:
    parts = path.split("/")
    if len(parts) > 2 and parts[0] in {"src", "app", "backend", "frontend"}:
        return "/".join(parts[:2])
    return parts[0] if parts else "root"


def _layer(path: str) -> str:
    lower = path.lower()
    if any(token in lower for token in ("component", "page", "frontend", "ui")):
        return "Frontend"
    if any(token in lower for token in ("route", "api", "controller", "main.py")):
        return "API"
    if any(token in lower for token in ("repository", "store", "service", "client")):
        return "Service"
    if any(token in lower for token in ("model", "schema", "migration", "db")):
        return "Database"
    if any(token in lower for token in ("auth", "security", "jwt", "session")):
        return "Security"
    return "Application"


def _describe_service(path: str) -> str:
    lower = path.lower()
    if "auth" in lower or "security" in lower:
        return "Authentication and trust boundary logic"
    if "upload" in lower or "file" in lower:
        return "File ingestion or upload handling"
    if "payment" in lower or "billing" in lower or "stripe" in lower:
        return "Payment or billing integration"
    if "store" in lower or "repository" in lower or "db" in lower:
        return "Persistence and repository state management"
    if "api" in lower or "route" in lower or "main.py" in lower:
        return "HTTP API boundary"
    return "Application behavior component"


def _participant(layer: str) -> str:
    return "".join(ch for ch in layer.title() if ch.isalnum()) or "Component"


def _clean(value: str) -> str:
    return str(value).replace("\n", " ").replace(":", "-")[:90]


def _dedupe_steps(steps: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[tuple[str, str]] = set()
    unique = []
    for step in steps:
        key = (step["layer"], step["component"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(step)
    return unique
