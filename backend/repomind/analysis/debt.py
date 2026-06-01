from __future__ import annotations

from pathlib import Path
from typing import Any

from radon.complexity import cc_visit
from radon.metrics import mi_visit


def analyze_technical_debt(
    root: Path, files: list[dict[str, Any]], parsed: list[dict[str, Any]]
) -> dict[str, Any]:
    debt_items: list[dict[str, Any]] = []
    maintainability: list[dict[str, Any]] = []
    todos = []
    for item in parsed:
        for todo in item.get("todos", []):
            todos.append({"path": item["relative_path"], **todo})
    for item in files:
        path = root / item["relative_path"]
        if item["language"] != "Python":
            continue
        text = path.read_text(errors="ignore")
        try:
            complexity = cc_visit(text)
            mi = mi_visit(text, True)
        except Exception:
            continue
        maintainability.append(
            {"path": item["relative_path"], "maintainability_index": round(mi, 2)}
        )
        for block in complexity:
            if block.complexity >= 10:
                debt_items.append(
                    {
                        "path": item["relative_path"],
                        "line": block.lineno,
                        "type": "complexity",
                        "message": f"{block.name} has cyclomatic complexity {block.complexity}.",
                        "severity": "high" if block.complexity >= 15 else "medium",
                    }
                )
    large_files = [
        {"path": item["relative_path"], "size": item["size"], "severity": "medium"}
        for item in files
        if item["size"] > 150_000
    ]
    mi_values = [item["maintainability_index"] for item in maintainability]
    mi_score = sum(mi_values) / len(mi_values) if mi_values else 72
    file_count = max(len(files), 1)
    score = max(
        0,
        min(
            100,
            round(
                mi_score
                - (len(debt_items) / file_count) * 180
                - (len(todos) / file_count) * 45
                - (len(large_files) / file_count) * 35,
                1,
            ),
        ),
    )
    return {
        "score": score,
        "items": debt_items,
        "todos": todos,
        "large_files": large_files,
        "maintainability": maintainability,
    }
