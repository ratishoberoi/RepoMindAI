from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

SECRET_RE = re.compile(r"(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*['\"][^'\"\n]{8,}['\"]")
DANGEROUS_PATTERNS = [
    ("python-eval", re.compile(r"\beval\s*\("), "Use of eval can execute arbitrary code."),
    ("python-exec", re.compile(r"\bexec\s*\("), "Use of exec can execute arbitrary code."),
    (
        "shell-true",
        re.compile(r"shell\s*=\s*True"),
        "Subprocess shell=True increases injection risk.",
    ),
    ("js-inner-html", re.compile(r"innerHTML\s*="), "Direct innerHTML assignment can enable XSS."),
    (
        "sql-format",
        re.compile(r"SELECT\s+.+(%|\\.format|f['\"])", re.IGNORECASE),
        "Possible dynamic SQL string construction.",
    ),
]


CancelCheck = Callable[[], bool]


def scan_security(
    root: Path, files: list[dict], cancel_check: CancelCheck | None = None
) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    for index, item in enumerate(files):
        if index % 25 == 0:
            _checkpoint(cancel_check)
        path = root / item["relative_path"]
        if item["size"] > 1_000_000:
            continue
        text = path.read_text(errors="ignore")
        for line_no, line in enumerate(text.splitlines(), start=1):
            if SECRET_RE.search(line):
                severity = "low" if _is_example_path(item["relative_path"]) else "high"
                findings.append(
                    _finding(
                        "hardcoded-secret",
                        severity,
                        item["relative_path"],
                        line_no,
                        "Possible hardcoded credential.",
                    )
                )
            for rule_id, regex, message in DANGEROUS_PATTERNS:
                if regex.search(line):
                    severity = "low" if _is_example_path(item["relative_path"]) else "medium"
                    findings.append(
                        _finding(rule_id, severity, item["relative_path"], line_no, message)
                    )
    _checkpoint(cancel_check)
    findings.extend(_run_bandit(root, cancel_check))
    _checkpoint(cancel_check)
    findings.extend(_run_semgrep(root, cancel_check))
    severity_counts: dict[str, int] = {}
    for finding in findings:
        severity_counts[finding["severity"]] = severity_counts.get(finding["severity"], 0) + 1
    scanner_status = {
        "bandit": bool(_tool("bandit")),
        "semgrep": bool(_tool("semgrep")),
        "custom_rules": True,
    }
    return {
        "findings": findings,
        "severity_counts": severity_counts,
        "scanner_status": scanner_status,
    }


def _finding(rule_id: str, severity: str, path: str, line: int, message: str) -> dict[str, Any]:
    return {
        "rule_id": rule_id,
        "severity": severity,
        "path": path,
        "line": line,
        "message": message,
    }


def _is_example_path(path: str) -> bool:
    lower = path.lower()
    return (
        lower.startswith(("docs/", "examples/", "tests/", "test/"))
        or "/docs/" in lower
        or "/examples/" in lower
    )


def _run_bandit(root: Path, cancel_check: CancelCheck | None = None) -> list[dict[str, Any]]:
    bandit = _tool("bandit")
    if not bandit:
        return []
    try:
        proc = _run_subprocess(
            [bandit, "-r", str(root), "-f", "json", "-q"],
            timeout=60,
            cancel_check=cancel_check,
        )
        payload = json.loads(proc.stdout or "{}")
    except (subprocess.SubprocessError, json.JSONDecodeError):
        return []
    results = []
    for item in payload.get("results", []):
        path = Path(item.get("filename", "")).resolve()
        try:
            rel = path.relative_to(root.resolve()).as_posix()
        except ValueError:
            rel = str(path)
        results.append(
            _finding(
                item.get("test_id", "bandit"),
                item.get("issue_severity", "medium").lower(),
                rel,
                item.get("line_number", 1),
                item.get("issue_text", "Bandit finding"),
            )
        )
    return results


def _run_semgrep(root: Path, cancel_check: CancelCheck | None = None) -> list[dict[str, Any]]:
    semgrep = _tool("semgrep")
    if not semgrep:
        return []
    try:
        proc = _run_subprocess(
            [
                semgrep,
                "scan",
                "--config",
                str(Path(__file__).with_name("semgrep_rules.yml")),
                "--json",
                "--quiet",
                "--error",
                "--timeout",
                "45",
                str(root),
            ],
            timeout=90,
            cancel_check=cancel_check,
        )
        payload = json.loads(proc.stdout or "{}")
    except (subprocess.SubprocessError, json.JSONDecodeError):
        return []
    findings = []
    for item in payload.get("results", []):
        path = Path(item.get("path", "")).resolve()
        try:
            rel = path.relative_to(root.resolve()).as_posix()
        except ValueError:
            rel = item.get("path", "")
        extra = item.get("extra", {})
        metadata = extra.get("metadata", {})
        severity = str(extra.get("severity") or metadata.get("impact") or "medium").lower()
        findings.append(
            _finding(
                item.get("check_id", "semgrep"),
                _normalize_semgrep_severity(severity),
                rel,
                item.get("start", {}).get("line", 1),
                extra.get("message", "Semgrep finding"),
            )
        )
    return findings


def _normalize_semgrep_severity(value: str) -> str:
    value = value.lower()
    if value in {"critical", "error"}:
        return "critical"
    if value in {"high", "warning"}:
        return "high"
    if value in {"low", "info", "note"}:
        return "low"
    return "medium"


def _tool(name: str) -> str | None:
    direct = shutil.which(name)
    if direct:
        return direct
    venv_tool = Path(sys.prefix) / "bin" / name
    return str(venv_tool) if venv_tool.exists() else None


def _run_subprocess(
    command: list[str], timeout: int, cancel_check: CancelCheck | None = None
) -> subprocess.CompletedProcess[str]:
    start = time.monotonic()
    proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        while proc.poll() is None:
            _checkpoint(cancel_check)
            if time.monotonic() - start > timeout:
                proc.kill()
                raise subprocess.TimeoutExpired(command, timeout)
            time.sleep(0.1)
        stdout, stderr = proc.communicate()
        return subprocess.CompletedProcess(command, proc.returncode, stdout, stderr)
    except Exception:
        proc.kill()
        proc.communicate()
        raise


def _checkpoint(cancel_check: CancelCheck | None) -> None:
    if cancel_check and cancel_check():
        from repomind.analysis.analyzer import AnalysisCancelled

        raise AnalysisCancelled("Analysis cancelled.")
