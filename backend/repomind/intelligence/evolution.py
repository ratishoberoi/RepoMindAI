from __future__ import annotations

import subprocess
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from typing import Any


def build_repository_evolution(summary: dict[str, Any]) -> dict[str, Any]:
    """Build repository evolution signals from local git history and analysis evidence."""

    root = _repo_root(summary)
    commits = _git_commits(root)
    file_history = _file_history(root, commits)
    current = _current_snapshot(summary)
    timeline = _timeline(commits, file_history, summary)
    return {
        "repository": summary.get("repository", {}),
        "history_available": bool(commits),
        "commit_count_analyzed": len(commits),
        "time_window": _time_window(commits),
        "current_snapshot": current,
        "architectural_drift_over_time": _dimension_timeline(
            timeline, "architecture", current["architecture_risk"]
        ),
        "dependency_evolution": _dimension_timeline(
            timeline, "dependency", current["dependency_risk"]
        ),
        "risk_evolution": _dimension_timeline(timeline, "risk", current["risk_score"]),
        "security_evolution": _dimension_timeline(timeline, "security", current["security_risk"]),
        "complexity_evolution": _dimension_timeline(
            timeline, "complexity", current["complexity_risk"]
        ),
        "hot_files": _hot_files(file_history, summary),
        "change_coupling": _change_coupling(commits),
        "evidence": _evidence(summary, commits, file_history),
        "limitations": _limitations(commits),
        "summary": _summary_text(commits, current),
    }


def _repo_root(summary: dict[str, Any]) -> Path | None:
    path = summary.get("repository", {}).get("path")
    if not path:
        return None
    root = Path(path)
    if not root.exists():
        return None
    try:
        resolved = subprocess.check_output(
            ["git", "-C", str(root), "rev-parse", "--show-toplevel"],
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=3,
        ).strip()
    except (OSError, subprocess.SubprocessError):
        return None
    return Path(resolved)


def _git_commits(root: Path | None) -> list[dict[str, Any]]:
    if root is None:
        return []
    try:
        output = subprocess.check_output(
            [
                "git",
                "-C",
                str(root),
                "log",
                "--numstat",
                "--pretty=format:__COMMIT__%x1f%h%x1f%ad%x1f%s",
                "--date=short",
                "-n",
                "120",
            ],
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=8,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    commits: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for line in output.splitlines():
        if line.startswith("__COMMIT__"):
            if current:
                commits.append(current)
            _, sha, committed_at, subject = line.split("\x1f", 3)
            current = {
                "sha": sha,
                "date": committed_at,
                "subject": subject,
                "files": [],
                "additions": 0,
                "deletions": 0,
            }
            continue
        if not line.strip() or current is None:
            continue
        parts = line.split("\t")
        if len(parts) != 3:
            continue
        additions, deletions, path = parts
        added = _int(additions)
        removed = _int(deletions)
        current["files"].append(path)
        current["additions"] += added
        current["deletions"] += removed
    if current:
        commits.append(current)
    return commits


def _file_history(root: Path | None, commits: list[dict[str, Any]]) -> dict[str, Any]:
    if root is None or not commits:
        return {}
    touches: Counter[str] = Counter()
    first_seen: dict[str, str] = {}
    last_seen: dict[str, str] = {}
    churn: Counter[str] = Counter()
    for commit in reversed(commits):
        for file in commit.get("files", []):
            touches[file] += 1
            first_seen.setdefault(file, commit.get("date", ""))
            last_seen[file] = commit.get("date", "")
            churn[file] += int(commit.get("additions", 0)) + int(commit.get("deletions", 0))
    return {
        file: {
            "touches": touches[file],
            "first_seen": first_seen.get(file),
            "last_seen": last_seen.get(file),
            "churn": churn[file],
            "domain": _domain(file),
            "layer": _layer(file),
        }
        for file in touches
    }


def _current_snapshot(summary: dict[str, Any]) -> dict[str, Any]:
    security_findings = summary.get("security", {}).get("findings", [])
    debt = summary.get("technical_debt", {})
    kg = summary.get("knowledge_graph", {})
    stack = summary.get("stack", {})
    graph = summary.get("graph", {})
    stats = summary.get("statistics", {})
    scores = summary.get("scores", {})
    dependency_edges = len(graph.get("edges", []))
    hotspots = len(kg.get("hotspots", []))
    architecture_risk = min(100, hotspots * 12 + dependency_edges // 4)
    security_risk = min(
        100,
        sum(
            {"critical": 24, "high": 16, "medium": 8, "low": 3}.get(
                str(item.get("severity", "")).lower(), 4
            )
            for item in security_findings
        ),
    )
    complexity_risk = min(
        100,
        len(debt.get("items", [])) * 10
        + len(debt.get("todos", [])) * 3
        + len(debt.get("large_files", [])) * 8,
    )
    dependency_risk = min(
        100,
        len(stack.get("frameworks", [])) * 5
        + len(stack.get("package_managers", [])) * 6
        + dependency_edges // 6,
    )
    risk_score = round(
        security_risk * 0.35
        + architecture_risk * 0.25
        + complexity_risk * 0.20
        + dependency_risk * 0.20,
        1,
    )
    return {
        "files": stats.get("files", 0),
        "routes": stats.get("routes", 0),
        "database_models": stats.get("database_models", 0),
        "security_findings": len(security_findings),
        "architecture_hotspots": hotspots,
        "dependency_edges": dependency_edges,
        "architecture_risk": round(architecture_risk, 1),
        "dependency_risk": round(dependency_risk, 1),
        "security_risk": round(security_risk, 1),
        "complexity_risk": round(complexity_risk, 1),
        "risk_score": risk_score,
        "health_score": scores.get("cto", scores.get("production_readiness", 0)),
    }


def _timeline(
    commits: list[dict[str, Any]],
    file_history: dict[str, Any],
    summary: dict[str, Any],
) -> list[dict[str, Any]]:
    if not commits:
        current = _current_snapshot(summary)
        return [
            {
                "date": str(date.today()),
                "label": "Current analysis snapshot",
                "commit_count": 0,
                "files_changed": 0,
                "architecture": current["architecture_risk"],
                "dependency": current["dependency_risk"],
                "risk": current["risk_score"],
                "security": current["security_risk"],
                "complexity": current["complexity_risk"],
                "evidence": "No git history available; point-in-time analysis only.",
            }
        ]
    by_date: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for commit in commits:
        by_date[str(commit.get("date", "unknown"))].append(commit)
    rows = []
    for committed_at in sorted(by_date)[-30:]:
        day_commits = by_date[committed_at]
        files = [file for commit in day_commits for file in commit.get("files", [])]
        layers = Counter(_layer(file) for file in files)
        architecture = min(100, layers["api"] * 10 + layers["data"] * 9 + layers["infra"] * 8)
        dependency = min(100, sum(1 for file in files if _dependency_file(file)) * 20)
        security = min(100, sum(1 for file in files if _security_file(file)) * 18)
        complexity = min(
            100, len(files) * 3 + sum(len(set(commit.get("files", []))) for commit in day_commits)
        )
        risk = round(
            architecture * 0.30 + dependency * 0.22 + security * 0.28 + complexity * 0.20, 1
        )
        rows.append(
            {
                "date": committed_at,
                "label": f"{len(day_commits)} commits, {len(set(files))} files touched",
                "commit_count": len(day_commits),
                "files_changed": len(set(files)),
                "architecture": architecture,
                "dependency": dependency,
                "risk": risk,
                "security": security,
                "complexity": complexity,
                "top_files": [
                    file
                    for file, _ in Counter(files).most_common(6)
                    if file in file_history or file
                ],
                "evidence": "; ".join(
                    f"{commit.get('sha')} {commit.get('subject')}" for commit in day_commits[:3]
                ),
            }
        )
    return rows


def _dimension_timeline(
    timeline: list[dict[str, Any]], key: str, current_value: float
) -> list[dict[str, Any]]:
    rows = [
        {
            "date": item["date"],
            "value": item.get(key, 0),
            "label": item.get("label", ""),
            "evidence": item.get("evidence", ""),
        }
        for item in timeline
    ]
    if rows:
        rows[-1]["current_snapshot"] = current_value
    return rows


def _hot_files(file_history: dict[str, Any], summary: dict[str, Any]) -> list[dict[str, Any]]:
    security_paths = {item.get("path") for item in summary.get("security", {}).get("findings", [])}
    hotspot_paths = {
        item.get("path") for item in summary.get("knowledge_graph", {}).get("hotspots", [])
    }
    rows = []
    for file, history in file_history.items():
        evidence = []
        if file in security_paths:
            evidence.append("security finding")
        if file in hotspot_paths:
            evidence.append("architecture hotspot")
        score = int(history.get("touches", 0)) * 6 + int(history.get("churn", 0)) // 80
        score += 18 if file in security_paths else 0
        score += 14 if file in hotspot_paths else 0
        rows.append(
            {
                "file": file,
                "risk_score": min(100, score),
                "touches": history.get("touches", 0),
                "churn": history.get("churn", 0),
                "domain": history.get("domain"),
                "layer": history.get("layer"),
                "evidence": evidence or ["change frequency"],
            }
        )
    if not rows:
        for hotspot in summary.get("knowledge_graph", {}).get("hotspots", [])[:10]:
            rows.append(
                {
                    "file": hotspot.get("path"),
                    "risk_score": min(100, hotspot.get("risk_score", 0) * 4),
                    "touches": 0,
                    "churn": 0,
                    "domain": _domain(str(hotspot.get("path", ""))),
                    "layer": _layer(str(hotspot.get("path", ""))),
                    "evidence": [hotspot.get("reason", "architecture hotspot")],
                }
            )
    return sorted(rows, key=lambda item: item["risk_score"], reverse=True)[:20]


def _change_coupling(commits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    pairs: Counter[tuple[str, str]] = Counter()
    for commit in commits:
        files = sorted(set(commit.get("files", [])))
        if len(files) < 2 or len(files) > 40:
            continue
        for index, left in enumerate(files):
            for right in files[index + 1 :]:
                if _domain(left) == _domain(right):
                    continue
                pairs[(left, right)] += 1
    return [
        {
            "source": left,
            "target": right,
            "co_changes": count,
            "evidence": f"Changed together in {count} analyzed commits.",
        }
        for (left, right), count in pairs.most_common(20)
    ]


def _evidence(
    summary: dict[str, Any], commits: list[dict[str, Any]], file_history: dict[str, Any]
) -> list[dict[str, Any]]:
    rows = [
        {
            "type": "analysis_summary",
            "source": "repository analysis",
            "facts": _current_snapshot(summary),
        }
    ]
    if commits:
        rows.append(
            {
                "type": "git_history",
                "source": "git log --numstat",
                "facts": {
                    "commits": len(commits),
                    "files_with_history": len(file_history),
                    "oldest_commit": commits[-1].get("sha"),
                    "newest_commit": commits[0].get("sha"),
                },
            }
        )
    return rows


def _limitations(commits: list[dict[str, Any]]) -> list[str]:
    if commits:
        return [
            "Evolution metrics use local git history available in the ingested repository.",
            "Risk trend values estimate architectural change pressure from changed files, not runtime incidents.",
        ]
    return [
        "No git history was available in the analyzed source path.",
        "Evolution view is limited to the current static analysis snapshot.",
    ]


def _summary_text(commits: list[dict[str, Any]], current: dict[str, Any]) -> str:
    if commits:
        return (
            f"Analyzed {len(commits)} commits for architecture, dependency, security, "
            f"complexity, and risk evolution. Current composite risk is {current['risk_score']}."
        )
    return (
        "No local git history was available, so RepoMindAI generated a point-in-time "
        f"evolution baseline from current analysis evidence with risk {current['risk_score']}."
    )


def _time_window(commits: list[dict[str, Any]]) -> dict[str, str | None]:
    if not commits:
        return {"start": None, "end": None}
    dates = sorted(str(commit.get("date", "")) for commit in commits if commit.get("date"))
    return {"start": dates[0] if dates else None, "end": dates[-1] if dates else None}


def _domain(path: str) -> str:
    parts = path.split("/")
    if len(parts) > 2 and parts[0] in {"src", "app", "backend", "frontend"}:
        return "/".join(parts[:2])
    return parts[0] if parts else "root"


def _layer(path: str) -> str:
    lower = path.lower()
    if any(token in lower for token in ("api", "route", "controller", "main.py")):
        return "api"
    if any(token in lower for token in ("db", "model", "schema", "migration", "store")):
        return "data"
    if any(token in lower for token in ("auth", "security", "secret", "jwt")):
        return "security"
    if any(token in lower for token in ("docker", ".github", "deploy", "terraform", "k8s")):
        return "infra"
    if any(token in lower for token in ("component", "page", "frontend", "ui")):
        return "ui"
    if "test" in lower or "spec" in lower:
        return "test"
    return "application"


def _dependency_file(path: str) -> bool:
    lower = path.lower()
    return lower.endswith(
        ("requirements.txt", "pyproject.toml", "package.json", "package-lock.json", "pom.xml")
    )


def _security_file(path: str) -> bool:
    lower = path.lower()
    return any(token in lower for token in ("auth", "security", "secret", "permission", "csrf"))


def _int(value: str) -> int:
    try:
        return int(value)
    except ValueError:
        return 0
