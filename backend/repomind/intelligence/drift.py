from __future__ import annotations

from typing import Any


def architecture_fingerprint(summary: dict[str, Any]) -> dict[str, Any]:
    kg = summary.get("knowledge_graph", {})
    arch = summary.get("architecture", {})
    return {
        "style": arch.get("style"),
        "frameworks": sorted(summary.get("stack", {}).get("frameworks", [])),
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
        "scores": {
            key: summary.get("scores", {}).get(key)
            for key in ("security", "maintainability", "production_readiness", "cto")
        },
    }


def detect_architecture_drift(baseline: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
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
    drift_score = min(
        100,
        len(domain_added) * 10
        + len(domain_removed) * 14
        + len(domain_changed) * 8
        + abs(route_delta) * 4
        + abs(model_delta) * 5
        + sum(8 for value in score_delta.values() if value <= -10),
    )
    return {
        "baseline": baseline.get("repository", {}),
        "current": current.get("repository", {}),
        "drift_score": drift_score,
        "drift_level": _level(drift_score),
        "domain_added": domain_added,
        "domain_removed": domain_removed,
        "domain_changed": domain_changed[:20],
        "route_file_delta": route_delta,
        "data_model_file_delta": model_delta,
        "score_delta": score_delta,
        "frameworks_added": sorted(set(right["frameworks"]) - set(left["frameworks"])),
        "frameworks_removed": sorted(set(left["frameworks"]) - set(right["frameworks"])),
        "recommendations": _recommendations(drift_score, domain_added, domain_removed, score_delta),
        "summary": _summary(drift_score, domain_added, domain_removed, domain_changed),
    }


def _number(value: Any) -> float:
    return float(value) if isinstance(value, (int, float)) else 0.0


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
