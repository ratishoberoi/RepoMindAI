from __future__ import annotations

import json
import os
import re
import shutil
import signal
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
    findings.extend(_run_bandit(root, files, cancel_check))
    _checkpoint(cancel_check)
    findings.extend(_run_semgrep(root, files, cancel_check))
    _checkpoint(cancel_check)
    findings.extend(_run_trivy(root, cancel_check))
    _checkpoint(cancel_check)
    findings.extend(_run_dependency_audit(root, cancel_check))
    _checkpoint(cancel_check)
    findings.extend(_entropy_secret_scan(root, files, cancel_check))
    severity_counts: dict[str, int] = {}
    for finding in findings:
        severity_counts[finding["severity"]] = severity_counts.get(finding["severity"], 0) + 1
    scanner_status = {
        "bandit": bool(_tool("bandit")),
        "semgrep": bool(_tool("semgrep")),
        "trivy": bool(_tool("trivy")),
        "dependency_audit": bool(_tool("npm")) or bool(_tool("pip-audit")),
        "secret_detection": True,
        "custom_rules": True,
    }
    return {
        "findings": findings,
        "severity_counts": severity_counts,
        "scanner_status": scanner_status,
    }


def _finding(rule_id: str, severity: str, path: str, line: int, message: str) -> dict[str, Any]:
    taxonomy = _taxonomy(rule_id)
    return {
        "rule_id": rule_id,
        "severity": severity,
        "path": path,
        "line": line,
        "message": message,
        "affected_files": [path],
        "impact": _impact(rule_id, severity),
        "remediation": _remediation(rule_id),
        "owasp": taxonomy["owasp"],
        "cwe": taxonomy["cwe"],
        "cvss": taxonomy["cvss"],
        "exploitability": _exploitability(rule_id, severity),
        "business_impact": _business_impact(rule_id, severity),
        "scanner": _scanner_name(rule_id),
    }


def _taxonomy(rule_id: str) -> dict[str, str]:
    lower = rule_id.lower()
    if "secret" in lower:
        return {"owasp": "A02:2021-Cryptographic Failures", "cwe": "CWE-798", "cvss": 8.1}
    if "eval" in lower or "exec" in lower:
        return {"owasp": "A03:2021-Injection", "cwe": "CWE-95", "cvss": 9.1}
    if "shell" in lower:
        return {"owasp": "A03:2021-Injection", "cwe": "CWE-78", "cvss": 9.0}
    if "inner-html" in lower:
        return {"owasp": "A03:2021-Injection", "cwe": "CWE-79", "cvss": 7.4}
    if "sql" in lower:
        return {"owasp": "A03:2021-Injection", "cwe": "CWE-89", "cvss": 8.8}
    if lower.startswith("trivy"):
        return {
            "owasp": "A06:2021-Vulnerable and Outdated Components",
            "cwe": "CWE-937",
            "cvss": 7.5,
        }
    if lower.startswith("dependency"):
        return {
            "owasp": "A06:2021-Vulnerable and Outdated Components",
            "cwe": "CWE-1104",
            "cvss": 7.2,
        }
    if lower.startswith("b"):
        return {"owasp": "A05:2021-Security Misconfiguration", "cwe": "CWE-693", "cvss": 6.5}
    return {"owasp": "A06:2021-Vulnerable and Outdated Components", "cwe": "CWE-20", "cvss": 5.0}


def _impact(rule_id: str, severity: str) -> str:
    lower = rule_id.lower()
    if "secret" in lower:
        return "Credential disclosure can allow unauthorized access to systems or data."
    if "eval" in lower or "exec" in lower or "shell" in lower:
        return "Untrusted input could reach command or code execution paths."
    if "inner-html" in lower:
        return "Untrusted HTML rendering can expose users to cross-site scripting."
    if "sql" in lower:
        return "Dynamic SQL construction can expose data to injection and leakage."
    return f"{severity.title()} security finding requires engineering review before release."


def _remediation(rule_id: str) -> str:
    lower = rule_id.lower()
    if "secret" in lower:
        return "Move secrets into environment or secret manager, rotate exposed values, and add secret scanning to CI."
    if "eval" in lower or "exec" in lower:
        return (
            "Replace dynamic code execution with explicit parsing or allowlisted command dispatch."
        )
    if "shell" in lower:
        return "Use subprocess argument arrays with shell disabled and validate all inputs."
    if "inner-html" in lower:
        return "Render sanitized content only and prefer framework-safe text rendering."
    if "sql" in lower:
        return "Use parameterized queries or ORM query builders."
    return "Review the finding, add a regression test, and document the accepted remediation."


def _exploitability(rule_id: str, severity: str) -> str:
    if severity in {"critical", "high"}:
        return "high"
    if any(token in rule_id.lower() for token in ("secret", "shell", "exec", "eval", "sql")):
        return "medium"
    return "low"


def _business_impact(rule_id: str, severity: str) -> str:
    if "secret" in rule_id.lower():
        return "Potential credential exposure can create incident response, compliance, and customer trust risk."
    if severity in {"critical", "high"}:
        return "Could block enterprise adoption or require remediation before diligence approval."
    return "Should be tracked as part of normal security debt management."


def _scanner_name(rule_id: str) -> str:
    lower = rule_id.lower()
    if lower.startswith("trivy"):
        return "trivy"
    if lower.startswith("dependency"):
        return "dependency-audit"
    if lower.startswith("semgrep"):
        return "semgrep"
    if lower.startswith("b"):
        return "bandit"
    if "secret" in lower:
        return "secret-detection"
    return "custom-rules"


def _is_example_path(path: str) -> bool:
    lower = path.lower()
    return (
        lower.startswith(("docs/", "examples/", "tests/", "test/"))
        or "/docs/" in lower
        or "/examples/" in lower
    )


def _run_bandit(
    root: Path, files: list[dict], cancel_check: CancelCheck | None = None
) -> list[dict[str, Any]]:
    bandit = _tool("bandit")
    if not bandit:
        return []
    paths = _scanner_paths(root, files, {".py"}, limit=600)
    if not paths:
        return []
    try:
        proc = _run_subprocess(
            [bandit, "-f", "json", "-q", *paths],
            timeout=25,
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


def _run_semgrep(
    root: Path, files: list[dict], cancel_check: CancelCheck | None = None
) -> list[dict[str, Any]]:
    semgrep = _tool("semgrep")
    if not semgrep:
        return []
    paths = _scanner_paths(
        root,
        files,
        {".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".go", ".rs"},
        limit=800,
    )
    if not paths:
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
                "12",
                *paths,
            ],
            timeout=25,
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


def _run_trivy(root: Path, cancel_check: CancelCheck | None = None) -> list[dict[str, Any]]:
    trivy = _tool("trivy")
    if not trivy:
        return []
    try:
        proc = _run_subprocess(
            [trivy, "fs", "--format", "json", "--quiet", str(root)],
            timeout=120,
            cancel_check=cancel_check,
        )
        payload = json.loads(proc.stdout or "{}")
    except (subprocess.SubprocessError, json.JSONDecodeError):
        return []
    findings = []
    for result in payload.get("Results", []):
        target = result.get("Target", "")
        for vuln in result.get("Vulnerabilities", [])[:200]:
            severity = str(vuln.get("Severity", "medium")).lower()
            findings.append(
                _finding(
                    f"trivy-{vuln.get('VulnerabilityID', 'vulnerability')}",
                    _normalize_semgrep_severity(severity),
                    target,
                    1,
                    f"{vuln.get('PkgName', 'dependency')} {vuln.get('VulnerabilityID', '')}: {vuln.get('Title', 'Vulnerable dependency')}",
                )
            )
    return findings


def _scanner_paths(root: Path, files: list[dict], suffixes: set[str], limit: int) -> list[str]:
    production_paths = []
    fallback_paths = []
    for item in files:
        rel = item.get("relative_path", "")
        if not rel:
            continue
        path = root / rel
        if path.suffix.lower() not in suffixes or not path.exists():
            continue
        if _is_low_value_scan_path(rel):
            fallback_paths.append(str(path))
        else:
            production_paths.append(str(path))
        if len(production_paths) >= limit:
            break
    paths = production_paths or fallback_paths
    return paths[:limit]


def _is_low_value_scan_path(path: str) -> bool:
    lower = path.lower()
    parts = set(lower.split("/"))
    return bool(
        {"test", "tests", "docs", "doc", "docs_src", "examples", "example", "fixtures", "fixture"}
        & parts
        or lower.startswith(("docs_src/", "tests/", "test/"))
        or lower.endswith((".md", ".rst", ".txt"))
    )


def _run_dependency_audit(
    root: Path, cancel_check: CancelCheck | None = None
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    npm = _tool("npm")
    if npm and (root / "package-lock.json").exists():
        try:
            proc = _run_subprocess(
                [npm, "--prefix", str(root), "audit", "--json", "--audit-level=low"],
                timeout=90,
                cancel_check=cancel_check,
            )
            payload = json.loads(proc.stdout or "{}")
            for name, vuln in (payload.get("vulnerabilities") or {}).items():
                findings.append(
                    _finding(
                        f"dependency-npm-{name}",
                        _normalize_semgrep_severity(str(vuln.get("severity", "medium"))),
                        "package-lock.json",
                        1,
                        f"npm audit vulnerability in {name}",
                    )
                )
        except (subprocess.SubprocessError, json.JSONDecodeError):
            pass
    pip_audit = _tool("pip-audit")
    if pip_audit and ((root / "requirements.txt").exists() or (root / "pyproject.toml").exists()):
        try:
            proc = _run_subprocess(
                [pip_audit, "--format", "json", "--path", str(root)],
                timeout=90,
                cancel_check=cancel_check,
            )
            payload = json.loads(proc.stdout or "{}")
            for dep in payload.get("dependencies", []):
                for vuln in dep.get("vulns", []):
                    findings.append(
                        _finding(
                            f"dependency-pip-{vuln.get('id', dep.get('name', 'dependency'))}",
                            "high" if vuln.get("fix_versions") else "medium",
                            "pyproject.toml"
                            if (root / "pyproject.toml").exists()
                            else "requirements.txt",
                            1,
                            f"pip audit vulnerability in {dep.get('name')}: {vuln.get('id')}",
                        )
                    )
        except (subprocess.SubprocessError, json.JSONDecodeError):
            pass
    return findings


def _entropy_secret_scan(
    root: Path, files: list[dict], cancel_check: CancelCheck | None = None
) -> list[dict[str, Any]]:
    findings = []
    token_re = re.compile(r"['\"]([A-Za-z0-9_\-]{32,})['\"]")
    for index, item in enumerate(files[:3000]):
        if index % 50 == 0:
            _checkpoint(cancel_check)
        if item.get("size", 0) > 300_000:
            continue
        path = root / item["relative_path"]
        text = path.read_text(errors="ignore")
        for line_no, line in enumerate(text.splitlines(), start=1):
            for match in token_re.finditer(line):
                token = match.group(1)
                if _entropy(token) >= 4.1:
                    severity = "low" if _is_example_path(item["relative_path"]) else "medium"
                    findings.append(
                        _finding(
                            "hardcoded-secret-entropy",
                            severity,
                            item["relative_path"],
                            line_no,
                            "High-entropy token-like string detected.",
                        )
                    )
                    break
    return findings[:200]


def _entropy(value: str) -> float:
    from math import log2

    counts = {char: value.count(char) for char in set(value)}
    total = len(value)
    return -sum((count / total) * log2(count / total) for count in counts.values())


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
    proc = subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True
    )
    try:
        while proc.poll() is None:
            _checkpoint(cancel_check)
            if time.monotonic() - start > timeout:
                _kill_process_group(proc)
                raise subprocess.TimeoutExpired(command, timeout)
            time.sleep(0.1)
        stdout, stderr = proc.communicate()
        return subprocess.CompletedProcess(command, proc.returncode, stdout, stderr)
    except Exception:
        _kill_process_group(proc)
        proc.communicate()
        raise


def _kill_process_group(proc: subprocess.Popen[str]) -> None:
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except ProcessLookupError:
        return
    except Exception:
        proc.kill()


def _checkpoint(cancel_check: CancelCheck | None) -> None:
    if cancel_check and cancel_check():
        from repomind.analysis.analyzer import AnalysisCancelled

        raise AnalysisCancelled("Analysis cancelled.")
