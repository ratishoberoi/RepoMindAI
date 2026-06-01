from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any


def architecture_fingerprint(summary: dict[str, Any]) -> dict[str, Any]:
    kg = summary.get("knowledge_graph", {})
    arch = summary.get("architecture", {})
    integrations = _external_integrations(summary)
    return {
        "style": arch.get("style"),
        "frameworks": sorted(summary.get("stack", {}).get("frameworks", [])),
        "dependencies": sorted(_dependencies(summary)),
        "external_integrations": sorted(integrations),
        "api_surface": sorted(_api_surface(summary)),
        "domains": {
            item["name"]: {
                "role": item.get("role"),
                "file_count": item.get("file_count", 0),
                "routes": item.get("routes", 0),
                "data_models": item.get("data_models", 0),
            }
            for item in kg.get("domains", [])
        },
        "route_files": sorted(arch.get("route_files", [])),
        "database_model_files": sorted(arch.get("database_model_files", [])),
        "security_hotspots": sorted(item.get("path") for item in kg.get("hotspots", [])[:20]),
        "ownership": _ownership(summary),
        "security_posture": _security_posture(summary),
        "scores": {
            key: summary.get("scores", {}).get(key)
            for key in ("security", "maintainability", "production_readiness", "cto")
        },
    }


def detect_architecture_drift(
    baseline: dict[str, Any],
    current: dict[str, Any],
    compare_type: str = "repository",
    baseline_ref: str = "",
    target_ref: str = "",
) -> dict[str, Any]:
    left = architecture_fingerprint(baseline)
    right = architecture_fingerprint(current)
    domain_added = sorted(set(right["domains"]) - set(left["domains"]))
    domain_removed = sorted(set(left["domains"]) - set(right["domains"]))
    domain_changed = []
    for name in sorted(set(left["domains"]) & set(right["domains"])):
        before = left["domains"][name]
        after = right["domains"][name]
        if before != after:
            domain_changed.append({"name": name, "before": before, "after": after})
    score_delta = {
        key: _number(right["scores"].get(key)) - _number(left["scores"].get(key))
        for key in sorted(set(left["scores"]) | set(right["scores"]))
    }
    route_delta = len(right["route_files"]) - len(left["route_files"])
    model_delta = len(right["database_model_files"]) - len(left["database_model_files"])
    dependency_changes = _set_changes(left["dependencies"], right["dependencies"])
    integration_changes = _set_changes(
        left["external_integrations"], right["external_integrations"]
    )
    api_surface_changes = _set_changes(left["api_surface"], right["api_surface"])
    ownership_changes = _ownership_changes(left["ownership"], right["ownership"])
    security_posture_changes = _security_posture_changes(
        left["security_posture"], right["security_posture"]
    )
    ref_changes = (
        _git_ref_changes(current, baseline_ref, target_ref) if compare_type != "repository" else {}
    )
    drift_score = min(
        100,
        len(domain_added) * 10
        + len(domain_removed) * 14
        + len(domain_changed) * 8
        + abs(route_delta) * 4
        + abs(model_delta) * 5
        + len(dependency_changes["added"]) * 4
        + len(dependency_changes["removed"]) * 5
        + len(integration_changes["added"]) * 6
        + len(api_surface_changes["added"]) * 6
        + len(api_surface_changes["removed"]) * 8
        + len(ownership_changes["orphaned_added"]) * 8
        + max(0, security_posture_changes["severity_score_delta"]) * 2
        + sum(8 for value in score_delta.values() if value <= -10),
    )
    findings = _findings(
        drift_score,
        domain_added,
        domain_removed,
        domain_changed,
        score_delta,
        right,
        left,
    )
    return {
        "baseline": baseline.get("repository", {}),
        "current": current.get("repository", {}),
        "compare_type": compare_type,
        "baseline_ref": baseline_ref,
        "target_ref": target_ref,
        "drift_score": drift_score,
        "drift_level": _level(drift_score),
        "domain_added": domain_added,
        "domain_removed": domain_removed,
        "domain_changed": domain_changed[:20],
        "added_domains": [
            {"name": name, **right["domains"].get(name, {})} for name in domain_added
        ],
        "removed_domains": [
            {"name": name, **left["domains"].get(name, {})} for name in domain_removed
        ],
        "new_services": domain_added,
        "removed_services": domain_removed,
        "route_file_delta": route_delta,
        "data_model_file_delta": model_delta,
        "score_delta": score_delta,
        "dependency_changes": domain_changed[:20],
        "dependency_surface_changes": dependency_changes,
        "external_integration_changes": integration_changes,
        "api_surface_changes": api_surface_changes,
        "git_ref_changes": ref_changes,
        "security_changes": {
            "baseline_hotspots": left["security_hotspots"],
            "current_hotspots": right["security_hotspots"],
            "added": sorted(set(right["security_hotspots"]) - set(left["security_hotspots"])),
            "removed": sorted(set(left["security_hotspots"]) - set(right["security_hotspots"])),
        },
        "ownership_changes": ownership_changes,
        "security_posture_changes": security_posture_changes,
        "frameworks_added": sorted(set(right["frameworks"]) - set(left["frameworks"])),
        "frameworks_removed": sorted(set(left["frameworks"]) - set(right["frameworks"])),
        "recommendations": _recommendations(drift_score, domain_added, domain_removed, score_delta),
        "findings": findings,
        "timeline": _timeline(
            compare_type,
            baseline_ref,
            target_ref,
            domain_added,
            domain_removed,
            dependency_changes,
            api_surface_changes,
            score_delta,
            ownership_changes,
            security_posture_changes,
        ),
        "visual_diff": _visual_diff(
            domain_added,
            domain_removed,
            domain_changed,
            dependency_changes,
            integration_changes,
            api_surface_changes,
            ownership_changes,
            security_posture_changes,
        ),
        "drift_report": _drift_report(
            drift_score,
            domain_added,
            domain_removed,
            domain_changed,
            findings,
            compare_type,
            dependency_changes,
            integration_changes,
            api_surface_changes,
            ownership_changes,
            security_posture_changes,
        ),
        "baseline_snapshot": left,
        "current_snapshot": right,
        "summary": _summary(drift_score, domain_added, domain_removed, domain_changed),
    }


def _number(value: Any) -> float:
    return float(value) if isinstance(value, (int, float)) else 0.0


def _dependencies(summary: dict[str, Any]) -> list[str]:
    deps = []
    deps.extend(summary.get("stack", {}).get("frameworks", []))
    deps.extend(summary.get("stack", {}).get("package_managers", []))
    for file in summary.get("files", []):
        path = str(file.get("relative_path", "")).lower()
        if path.endswith(
            ("requirements.txt", "pyproject.toml", "package.json", "package-lock.json")
        ):
            deps.append(path.rsplit("/", 1)[-1])
    return [str(dep) for dep in deps if dep]


def _api_surface(summary: dict[str, Any]) -> list[str]:
    rows = []
    for item in summary.get("parsed", []):
        for route in item.get("routes", []):
            if isinstance(route, dict):
                rows.append(
                    f"{route.get('method', 'GET')} {route.get('path', '')} {item.get('relative_path')}"
                )
    return rows


def _ownership(summary: dict[str, Any]) -> dict[str, Any]:
    rows: dict[str, Any] = {}
    for domain in summary.get("knowledge_graph", {}).get("domains", []):
        name = str(domain.get("name", ""))
        if not name:
            continue
        owner = _owner_for_domain(name)
        rows[name] = {
            "owner": owner,
            "role": domain.get("role"),
            "file_count": domain.get("file_count", 0),
            "bus_factor": 1 if owner == "Core Engineering" else 2,
        }
    return rows


def _owner_for_domain(domain: str) -> str:
    lower = domain.lower()
    if any(token in lower for token in ("auth", "security", "session")):
        return "Security Platform"
    if any(token in lower for token in ("db", "model", "data", "store")):
        return "Data Platform"
    if any(token in lower for token in ("front", "ui", "component", "page")):
        return "Product Experience"
    if any(token in lower for token in ("infra", "deploy", "docker", "ci")):
        return "Infrastructure"
    return "Core Engineering"


def _security_posture(summary: dict[str, Any]) -> dict[str, Any]:
    findings = summary.get("security", {}).get("findings", [])
    severity_counts = {
        severity: sum(1 for finding in findings if finding.get("severity") == severity)
        for severity in ("critical", "high", "medium", "low")
    }
    severity_score = (
        severity_counts["critical"] * 10
        + severity_counts["high"] * 6
        + severity_counts["medium"] * 3
        + severity_counts["low"]
    )
    return {
        "finding_count": len(findings),
        "severity_counts": severity_counts,
        "severity_score": severity_score,
        "mapped_findings": sorted(
            f"{item.get('path', '')}:{item.get('rule_id', item.get('title', 'finding'))}"
            for item in findings[:200]
        ),
    }


def _external_integrations(summary: dict[str, Any]) -> list[str]:
    tokens = []
    for item in summary.get("parsed", []):
        for env in item.get("env_vars", []):
            name = str(env).lower()
            if any(token in name for token in ("url", "api", "stripe", "s3", "slack", "github")):
                tokens.append(str(env))
    for dep in _dependencies(summary):
        if any(token in dep.lower() for token in ("stripe", "slack", "aws", "s3", "github")):
            tokens.append(dep)
    return tokens


def _set_changes(left: list[str], right: list[str]) -> dict[str, list[str]]:
    return {
        "added": sorted(set(right) - set(left)),
        "removed": sorted(set(left) - set(right)),
        "unchanged": sorted(set(left) & set(right))[:50],
    }


def _ownership_changes(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    added = sorted(set(right) - set(left))
    removed = sorted(set(left) - set(right))
    owner_changed = []
    for name in sorted(set(left) & set(right)):
        if left[name].get("owner") != right[name].get("owner"):
            owner_changed.append(
                {
                    "service": name,
                    "before": left[name].get("owner"),
                    "after": right[name].get("owner"),
                }
            )
    orphaned_added = [
        name
        for name, payload in right.items()
        if payload.get("bus_factor", 0) <= 1 and name not in left
    ]
    return {
        "added": added,
        "removed": removed,
        "owner_changed": owner_changed,
        "orphaned_added": orphaned_added,
    }


def _security_posture_changes(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    return {
        "finding_count_delta": int(right.get("finding_count", 0))
        - int(left.get("finding_count", 0)),
        "severity_score_delta": int(right.get("severity_score", 0))
        - int(left.get("severity_score", 0)),
        "severity_counts_before": left.get("severity_counts", {}),
        "severity_counts_after": right.get("severity_counts", {}),
        "added_findings": sorted(
            set(right.get("mapped_findings", [])) - set(left.get("mapped_findings", []))
        )[:50],
        "removed_findings": sorted(
            set(left.get("mapped_findings", [])) - set(right.get("mapped_findings", []))
        )[:50],
    }


def _git_ref_changes(summary: dict[str, Any], baseline_ref: str, target_ref: str) -> dict[str, Any]:
    repo_path = summary.get("repository", {}).get("path")
    if not repo_path or not baseline_ref or not target_ref:
        return {"available": False, "reason": "Repository path or refs unavailable."}
    root = Path(repo_path)
    if not (root / ".git").exists():
        return {"available": False, "reason": "Local git history unavailable."}
    try:
        diff = subprocess.run(
            ["git", "-C", str(root), "diff", "--name-status", baseline_ref, target_ref],
            check=True,
            capture_output=True,
            text=True,
            timeout=20,
        )
    except Exception as exc:
        return {"available": False, "reason": str(exc)}
    files = []
    for line in diff.stdout.splitlines():
        parts = line.split(maxsplit=1)
        if len(parts) == 2:
            files.append({"status": parts[0], "path": parts[1]})
    return {"available": True, "changed_files": files[:500], "change_count": len(files)}


def _level(score: int) -> str:
    if score >= 70:
        return "major"
    if score >= 40:
        return "material"
    if score >= 15:
        return "minor"
    return "stable"


def _recommendations(
    drift_score: int, added: list[str], removed: list[str], score_delta: dict[str, float]
) -> list[str]:
    items = []
    if added:
        items.append("Review new domains for ownership, tests, and architecture decision records.")
    if removed:
        items.append("Verify removed domains are intentional and no callers still depend on them.")
    if any(value <= -10 for value in score_delta.values()):
        items.append("Investigate score regressions before accepting architecture drift.")
    if drift_score >= 40:
        items.append("Require staff-level architecture review before release.")
    return items or ["No material architecture drift detected."]


def _summary(
    score: int, added: list[str], removed: list[str], changed: list[dict[str, Any]]
) -> str:
    return (
        f"Architecture drift is {_level(score)} ({score}/100): "
        f"{len(added)} domains added, {len(removed)} removed, {len(changed)} changed."
    )


def _findings(
    score: int,
    added: list[str],
    removed: list[str],
    changed: list[dict[str, Any]],
    score_delta: dict[str, float],
    right: dict[str, Any],
    left: dict[str, Any],
) -> list[dict[str, Any]]:
    findings = []
    for name in added:
        findings.append(
            {
                "title": "New service/domain detected",
                "severity": "medium",
                "file": name,
                "evidence": f"{name} exists in current snapshot only.",
                "recommendation": "Verify ownership, tests, and release readiness for the new domain.",
            }
        )
    for name in removed:
        findings.append(
            {
                "title": "Removed service/domain detected",
                "severity": "high",
                "file": name,
                "evidence": f"{name} exists in baseline snapshot only.",
                "recommendation": "Confirm removal is intentional and downstream callers are migrated.",
            }
        )
    for item in changed[:8]:
        findings.append(
            {
                "title": "Domain dependency or responsibility changed",
                "severity": "medium",
                "file": item.get("name"),
                "evidence": f"Before {item.get('before')} after {item.get('after')}.",
                "recommendation": "Require architecture review for changed ownership, routes, or data models.",
            }
        )
    for key, delta in score_delta.items():
        if delta <= -10:
            findings.append(
                {
                    "title": f"{key} score regressed",
                    "severity": "high" if delta <= -20 else "medium",
                    "file": key,
                    "evidence": f"{key} changed by {round(delta, 1)} points.",
                    "recommendation": "Block release until score regression is explained or remediated.",
                }
            )
    added_security = sorted(set(right["security_hotspots"]) - set(left["security_hotspots"]))
    for path in added_security[:6]:
        findings.append(
            {
                "title": "New security hotspot",
                "severity": "high",
                "file": path,
                "evidence": "Current snapshot contains a security hotspot absent from baseline.",
                "recommendation": "Review remediation before accepting drift.",
            }
        )
    if not findings:
        findings.append(
            {
                "title": "No material architecture drift",
                "severity": "low",
                "file": "",
                "evidence": f"Drift score {_level(score)} at {score}/100.",
                "recommendation": "Continue monitoring drift across releases.",
            }
        )
    return findings[:20]


def _timeline(
    compare_type: str,
    baseline_ref: str,
    target_ref: str,
    added: list[str],
    removed: list[str],
    dependency_changes: dict[str, list[str]],
    api_changes: dict[str, list[str]],
    score_delta: dict[str, float],
    ownership_changes: dict[str, Any],
    security_posture_changes: dict[str, Any],
) -> list[dict[str, Any]]:
    baseline_label = baseline_ref or "baseline"
    target_label = target_ref or "current"
    return [
        {
            "label": baseline_label,
            "type": compare_type,
            "events": ["Baseline architecture fingerprint captured."],
        },
        {
            "label": "diff",
            "type": "analysis",
            "events": [
                f"{len(added)} services added",
                f"{len(removed)} services removed",
                f"{len(dependency_changes['added']) + len(dependency_changes['removed'])} dependency changes",
                f"{len(api_changes['added']) + len(api_changes['removed'])} API surface changes",
                f"{len(ownership_changes['owner_changed']) + len(ownership_changes['orphaned_added'])} ownership changes",
                f"{security_posture_changes['severity_score_delta']} security posture delta",
            ],
            "score_delta": score_delta,
        },
        {
            "label": target_label,
            "type": compare_type,
            "events": ["Current architecture fingerprint captured."],
        },
    ]


def _visual_diff(
    added: list[str],
    removed: list[str],
    changed: list[dict[str, Any]],
    dependency_changes: dict[str, list[str]],
    integration_changes: dict[str, list[str]],
    api_changes: dict[str, list[str]],
    ownership_changes: dict[str, Any],
    security_posture_changes: dict[str, Any],
) -> dict[str, Any]:
    nodes = []
    edges = []
    for kind, items, status in (
        ("service", added, "added"),
        ("service", removed, "removed"),
        ("dependency", dependency_changes["added"], "added"),
        ("dependency", dependency_changes["removed"], "removed"),
        ("integration", integration_changes["added"], "added"),
        ("api", api_changes["added"], "added"),
        ("api", api_changes["removed"], "removed"),
        (
            "owner",
            [item.get("service", "") for item in ownership_changes["owner_changed"]],
            "changed",
        ),
        ("security", security_posture_changes["added_findings"], "added"),
    ):
        for item in items[:50]:
            node_id = f"{kind}:{status}:{item}"
            nodes.append({"id": node_id, "label": item, "kind": kind, "status": status})
            edges.append({"source": "baseline", "target": node_id, "relation": status})
    for item in changed[:50]:
        node_id = f"service:changed:{item.get('name')}"
        nodes.append(
            {"id": node_id, "label": item.get("name"), "kind": "service", "status": "changed"}
        )
    return {
        "nodes": [{"id": "baseline", "label": "Architecture baseline", "kind": "baseline"}, *nodes],
        "edges": edges,
    }


def _drift_report(
    score: int,
    added: list[str],
    removed: list[str],
    changed: list[dict[str, Any]],
    findings: list[dict[str, Any]],
    compare_type: str = "repository",
    dependency_changes: dict[str, list[str]] | None = None,
    integration_changes: dict[str, list[str]] | None = None,
    api_changes: dict[str, list[str]] | None = None,
    ownership_changes: dict[str, Any] | None = None,
    security_posture_changes: dict[str, Any] | None = None,
) -> str:
    dependency_changes = dependency_changes or {"added": [], "removed": []}
    integration_changes = integration_changes or {"added": [], "removed": []}
    api_changes = api_changes or {"added": [], "removed": []}
    ownership_changes = ownership_changes or {"owner_changed": [], "orphaned_added": []}
    security_posture_changes = security_posture_changes or {
        "severity_score_delta": 0,
        "added_findings": [],
    }
    lines = [
        "# Architecture Drift Report",
        "",
        f"Comparison type: **{compare_type}**",
        f"Drift level: **{_level(score)}** ({score}/100)",
        "",
        "## Services Added",
        *([f"- `{item}`" for item in added] or ["- None"]),
        "",
        "## Services Removed",
        *([f"- `{item}`" for item in removed] or ["- None"]),
        "",
        "## Dependency Changes",
        *([f"- Added `{item}`" for item in dependency_changes["added"]] or []),
        *([f"- Removed `{item}`" for item in dependency_changes["removed"]] or []),
        *(
            [
                f"- `{item.get('name')}` changed from `{item.get('before')}` to `{item.get('after')}`"
                for item in changed[:10]
            ]
            or ["- None"]
        ),
        "",
        "## External Integration Changes",
        *([f"- Added `{item}`" for item in integration_changes["added"]] or []),
        *([f"- Removed `{item}`" for item in integration_changes["removed"]] or ["- None"]),
        "",
        "## API Surface Changes",
        *([f"- Added `{item}`" for item in api_changes["added"]] or []),
        *([f"- Removed `{item}`" for item in api_changes["removed"]] or ["- None"]),
        "",
        "## Ownership Changes",
        *(
            [
                f"- `{item.get('service')}` moved from `{item.get('before')}` to `{item.get('after')}`"
                for item in ownership_changes["owner_changed"]
            ]
            or ["- None"]
        ),
        *([f"- Orphan risk added: `{item}`" for item in ownership_changes["orphaned_added"]] or []),
        "",
        "## Security Posture Changes",
        f"- Severity score delta: `{security_posture_changes['severity_score_delta']}`",
        *(
            [
                f"- Added finding `{item}`"
                for item in security_posture_changes["added_findings"][:20]
            ]
            or []
        ),
        "",
        "## Findings",
        *[
            f"- **{item.get('severity')}** {item.get('title')}: {item.get('evidence')}"
            for item in findings
        ],
        "",
    ]
    return "\n".join(lines)
