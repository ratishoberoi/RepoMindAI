from __future__ import annotations

from typing import Any

from repomind.intelligence.acquisition import build_acquisition_intelligence


def build_score_evidence(summary: dict[str, Any]) -> dict[str, Any]:
    scores = summary.get("scores", {})
    details = scores.get("details", {})
    acquisition = build_acquisition_intelligence(summary)
    confidence = _number(scores.get("confidence", _confidence_from_summary(summary)))
    security_detail = details.get("security") or {
        "score": scores.get("security"),
        "calculation": "Security score from scanner severity counts, finding density, and scanner coverage.",
        "positive_contributors": [],
        "negative_contributors": [
            item.get("message", "Security finding")
            for item in summary.get("security", {}).get("findings", [])[:6]
        ],
    }
    return {
        "health": _composite_score(
            "health",
            "Repository Health Score",
            _weighted(
                [
                    (scores.get("security"), 0.30),
                    (scores.get("production_readiness"), 0.30),
                    (scores.get("maintainability"), 0.20),
                    (scores.get("cto"), 0.20),
                ]
            ),
            confidence,
            [
                _factor(
                    "Security posture",
                    scores.get("security"),
                    0.30,
                    "Security scanner findings and normalized severity density.",
                ),
                _factor(
                    "Production readiness",
                    scores.get("production_readiness"),
                    0.30,
                    "Tests, CI, Docker, dependencies, docs, and security posture.",
                ),
                _factor(
                    "Maintainability",
                    scores.get("maintainability"),
                    0.20,
                    "Complexity, TODOs, large files, and maintainability metrics.",
                ),
                _factor(
                    "CTO score", scores.get("cto"), 0.20, "Executive engineering readiness blend."
                ),
            ],
            _citations(summary),
        ),
        "security": _detail_score(
            "security",
            "Security Score",
            security_detail,
            confidence,
            _security_factors(summary),
            _security_citations(summary),
        ),
        "architecture": _composite_score(
            "architecture",
            "Architecture Score",
            _number(scores.get("production_readiness")),
            confidence,
            [
                _factor(
                    "Production readiness",
                    scores.get("production_readiness"),
                    0.40,
                    "Operational architecture checklist score.",
                ),
                _factor(
                    "Graph density",
                    _graph_density(summary),
                    0.20,
                    "Entities, relations, domains, and hotspots.",
                ),
                _factor(
                    "Route evidence",
                    _route_signal(summary),
                    0.15,
                    "Extracted API and route boundaries.",
                ),
                _factor(
                    "Service modularity",
                    _modularity_signal(summary),
                    0.15,
                    "Domain distribution and component count.",
                ),
                _factor(
                    "Hotspot penalty",
                    _hotspot_penalty(summary),
                    0.10,
                    "Dependency and security hotspot concentration.",
                    inverse=True,
                ),
            ],
            _architecture_citations(summary),
        ),
        "investment": _composite_score(
            "investment",
            "Investment Readiness",
            _number(scores.get("cto")),
            confidence,
            [
                _factor(
                    "CTO readiness",
                    scores.get("cto"),
                    0.45,
                    "Production, security, maintainability, and CI readiness.",
                ),
                _factor(
                    "Security posture",
                    scores.get("security"),
                    0.25,
                    "Security score impact on investor risk.",
                ),
                _factor(
                    "Maintainability",
                    scores.get("maintainability"),
                    0.20,
                    "Future engineering velocity.",
                ),
                _factor(
                    "Confidence",
                    scores.get("confidence"),
                    0.10,
                    "Amount and quality of analyzable evidence.",
                ),
            ],
            _citations(summary),
        ),
        "acquisition": _composite_score(
            "acquisition",
            "Acquisition Score",
            acquisition.get("scores", {}).get("acquisition_readiness", 0),
            confidence,
            [
                _factor("CTO score", scores.get("cto"), 0.24, "Executive technical readiness."),
                _factor(
                    "Security",
                    scores.get("security"),
                    0.22,
                    "Security risk and remediation exposure.",
                ),
                _factor(
                    "Production readiness",
                    scores.get("production_readiness"),
                    0.20,
                    "Operational maturity.",
                ),
                _factor(
                    "Maintainability",
                    scores.get("maintainability"),
                    0.18,
                    "Post-acquisition engineering velocity.",
                ),
                _factor(
                    "Test confidence",
                    acquisition.get("scores", {}).get("test_coverage_confidence"),
                    0.08,
                    "Automated test signal.",
                ),
                _factor(
                    "Documentation",
                    acquisition.get("scores", {}).get("documentation_quality"),
                    0.08,
                    "Diligence and onboarding evidence.",
                ),
            ],
            _citations(summary),
        ),
        "risk": _composite_score(
            "risk",
            "Risk Score",
            _risk_score(summary, acquisition),
            confidence,
            [
                _factor(
                    "Security findings",
                    min(100, len(summary.get("security", {}).get("findings", [])) * 12),
                    0.34,
                    "Security issue count and severity.",
                ),
                _factor(
                    "Architecture hotspots",
                    min(100, len(summary.get("knowledge_graph", {}).get("hotspots", [])) * 14),
                    0.26,
                    "Dependency centrality and security-sensitive hotspots.",
                ),
                _factor(
                    "Debt findings",
                    min(100, len(summary.get("technical_debt", {}).get("items", [])) * 10),
                    0.20,
                    "Complexity and maintainability debt.",
                ),
                _factor(
                    "Enterprise gaps",
                    min(100, len(acquisition.get("red_flags", [])) * 18),
                    0.20,
                    "Acquisition and diligence red flags.",
                ),
            ],
            _citations(summary),
            higher_is_better=False,
        ),
    }


def _detail_score(
    score_id: str,
    label: str,
    detail: dict[str, Any],
    confidence: float,
    factors: list[dict[str, Any]],
    citations: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "id": score_id,
        "label": label,
        "score": round(_number(detail.get("score")), 1),
        "confidence": confidence,
        "calculation": detail.get("calculation", "Evidence-weighted score."),
        "positive_contributors": detail.get("positive_contributors", []),
        "negative_contributors": detail.get("negative_contributors", []),
        "factors": factors,
        "citations": citations,
        "higher_is_better": True,
    }


def _composite_score(
    score_id: str,
    label: str,
    score: Any,
    confidence: float,
    factors: list[dict[str, Any]],
    citations: list[dict[str, Any]],
    higher_is_better: bool = True,
) -> dict[str, Any]:
    return {
        "id": score_id,
        "label": label,
        "score": round(_number(score), 1),
        "confidence": confidence,
        "calculation": "Weighted evidence model: "
        + " + ".join(f"{item['name']} {round(item['weight'] * 100)}%" for item in factors),
        "positive_contributors": [
            item["reason"] for item in factors if _number(item.get("value")) >= 70
        ],
        "negative_contributors": [
            item["reason"] for item in factors if _number(item.get("value")) < 70
        ],
        "factors": factors,
        "citations": citations,
        "higher_is_better": higher_is_better,
    }


def _factor(
    name: str,
    value: Any,
    weight: float,
    reason: str,
    inverse: bool = False,
) -> dict[str, Any]:
    numeric = _number(value)
    impact = (100 - numeric if inverse else numeric) * weight
    return {
        "name": name,
        "value": round(numeric, 1),
        "weight": weight,
        "impact": round(impact, 2),
        "reason": reason,
    }


def _security_factors(summary: dict[str, Any]) -> list[dict[str, Any]]:
    severity = summary.get("security", {}).get("severity_counts", {})
    findings = summary.get("security", {}).get("findings", [])
    file_count = max(summary.get("statistics", {}).get("files", 1), 1)
    return [
        _factor(
            "Critical findings",
            max(0, 100 - severity.get("critical", 0) * 25),
            0.35,
            "Critical findings are heavily penalized.",
        ),
        _factor(
            "High findings",
            max(0, 100 - severity.get("high", 0) * 12),
            0.25,
            "High severity findings affect production trust.",
        ),
        _factor(
            "Finding density",
            max(0, 100 - len(findings) / file_count * 120),
            0.25,
            "Findings normalized by analyzed file count.",
        ),
        _factor(
            "Scanner coverage",
            _scanner_coverage(summary),
            0.15,
            "Custom, Bandit, and Semgrep scanner availability.",
        ),
    ]


def _security_citations(summary: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "file": item.get("path"),
            "line": item.get("line", 1),
            "evidence": item.get("message"),
            "rule_id": item.get("rule_id"),
        }
        for item in summary.get("security", {}).get("findings", [])[:12]
        if item.get("path")
    ] or _citations(summary)


def _architecture_citations(summary: dict[str, Any]) -> list[dict[str, Any]]:
    paths = []
    paths.extend(summary.get("architecture", {}).get("important_files", [])[:8])
    paths.extend(
        item.get("path") for item in summary.get("knowledge_graph", {}).get("hotspots", [])[:8]
    )
    paths.extend(item.get("relative_path") for item in summary.get("files", [])[:4])
    return _path_citations(paths)


def _citations(summary: dict[str, Any]) -> list[dict[str, Any]]:
    paths = []
    paths.extend(summary.get("architecture", {}).get("important_files", [])[:8])
    paths.extend(item.get("path") for item in summary.get("security", {}).get("findings", [])[:8])
    paths.extend(item.get("relative_path") for item in summary.get("files", [])[:8])
    return _path_citations(paths)


def _path_citations(paths: list[Any]) -> list[dict[str, Any]]:
    unique = [str(path) for index, path in enumerate(paths) if path and path not in paths[:index]]
    return [
        {"file": path, "line": 1, "evidence": "Repository analysis evidence"}
        for path in unique[:14]
    ]


def _weighted(items: list[tuple[Any, float]]) -> float:
    available = [
        (float(value), weight) for value, weight in items if isinstance(value, (int, float))
    ]
    total = sum(weight for _, weight in available)
    if not total:
        return 0.0
    return sum(value * weight for value, weight in available) / total


def _number(value: Any) -> float:
    return float(value) if isinstance(value, (int, float)) else 0.0


def _confidence_from_summary(summary: dict[str, Any]) -> float:
    stats = summary.get("statistics", {})
    file_count = _number(stats.get("files"))
    parsed = len(summary.get("parsed", []))
    indexed = _number(stats.get("indexed_chunks"))
    signal = min(100.0, 25 + min(35, file_count * 1.5) + min(20, parsed * 3) + min(20, indexed * 2))
    return round(signal, 1)


def _scanner_coverage(summary: dict[str, Any]) -> float:
    status = summary.get("security", {}).get("scanner_status", {})
    if not status:
        return 35.0
    enabled = sum(1 for value in status.values() if value)
    return min(100.0, enabled / max(len(status), 1) * 100)


def _graph_density(summary: dict[str, Any]) -> float:
    metrics = summary.get("knowledge_graph", {}).get("metrics", {})
    return min(100.0, _number(metrics.get("entities")) * 2 + _number(metrics.get("relations")))


def _route_signal(summary: dict[str, Any]) -> float:
    routes = _number(summary.get("statistics", {}).get("routes"))
    return min(100.0, 45 + routes * 12)


def _modularity_signal(summary: dict[str, Any]) -> float:
    domains = len(summary.get("knowledge_graph", {}).get("domains", []))
    components = len(summary.get("architecture", {}).get("components", []))
    return min(100.0, 35 + domains * 7 + components * 4)


def _hotspot_penalty(summary: dict[str, Any]) -> float:
    hotspots = summary.get("knowledge_graph", {}).get("hotspots", [])
    return min(
        100.0, len(hotspots) * 12 + sum(_number(item.get("risk_score")) for item in hotspots[:8])
    )


def _risk_score(summary: dict[str, Any], acquisition: dict[str, Any]) -> float:
    security = len(summary.get("security", {}).get("findings", [])) * 12
    hotspots = len(summary.get("knowledge_graph", {}).get("hotspots", [])) * 14
    debt = len(summary.get("technical_debt", {}).get("items", [])) * 10
    flags = len(acquisition.get("red_flags", [])) * 18
    return min(100.0, security * 0.34 + hotspots * 0.26 + debt * 0.20 + flags * 0.20)
