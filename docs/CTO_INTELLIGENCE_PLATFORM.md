# RepoMindAI CTO Intelligence Platform

RepoMindAI turns repository analysis artifacts into CTO, diligence, and portfolio intelligence. Every screen and API in this layer is derived from repository summaries, dependency graphs, security findings, code parsing results, git history when available, and generated reports.

## Evidence Engine

- Source: `summary.score_evidence`, generated during repository analysis.
- Scores covered: health, security, architecture, investment readiness, acquisition readiness, and risk.
- Every score includes a numeric result, confidence, calculation narrative, weighted factors, positive and negative contributors, and source citations with file and line evidence where available.
- The Executive screen renders the same structure through the Score Evidence panel so users can inspect why a number exists before trusting it.
- Report artifacts include `EXECUTIVE_SUMMARY.md`, which serializes the same explainable score evidence for offline review.

## Architecture Explorer

- API: `GET /repositories/{repo_id}/architecture-explorer`
- Source: parsed routes, symbols, database models, dependency graph edges, stack metadata, and security/configuration signals.
- Outputs: named request flows, sequence diagrams, dependency paths, executive/engineering/onboarding narratives, architecture review, AI architect review, and `ONBOARDING.md` content.
- Supported flow families: authentication, login, signup, payment, file upload, data flow, and notification. Unsupported or absent flows are reported with low confidence instead of synthetic examples.
- Architecture Review covers strengths, weaknesses, coupling, scalability, service boundaries, modularity, maintainability, current risks, future risks, refactoring opportunities, scaling risks, and tech debt risks.
- AI Architect Review emits risk, impact, recommendation, affected files, and severity for high-signal architecture problems such as coupled domains, weak CI/CD, database concentration, and business logic mixed into transport routes.

## Knowledge Graph 3.0

- API: `GET /repositories/{repo_id}/knowledge-graph`
- Graph query API: `GET /repositories/{repo_id}/graph-query?query=overview|hotspots|ownership`
- Neo4j integration is enabled with `REPOMIND_NEO4J_URI`, `REPOMIND_NEO4J_USER`, and `REPOMIND_NEO4J_PASSWORD`. Without Neo4j, RepoMindAI uses the same graph projection locally so the product remains functional.
- Adds cluster evidence for Auth, API, Database, Security, Payments, Infrastructure, Frontend, and Application domains.
- Adds graph insights for large symbol concentration, dependency bottlenecks, architecture hotspots, security hotspots, critical paths, and git timeline events when local git history is available.

## Executive Report Engine

- API: `GET /repositories/{repo_id}/executive-reports`
- Report artifacts: `README_REPORT.md`, `ARCHITECTURE_REPORT.md`, `SECURITY_REPORT.md`, `CTO_REPORT.md`, `INVESTOR_REPORT.md`, `DUE_DILIGENCE_REPORT.md`, `ROADMAP_REPORT.md`, `EXECUTIVE_SUMMARY.md`, `EXECUTIVE_REPORT_PACK.md`, `ONBOARDING.md`, `EXECUTIVE_SUMMARY.html`, `EXECUTIVE_SUMMARY.pdf`, SARIF, and persona markdown reports.
- Reports are deterministic, evidence-first packets: board report, CTO report, investor report, security report, and 30/60/90 engineering roadmap.

## Source Citation System

- Chat citations include source file, start/end line metadata, and retrieved evidence snippets.
- The Chat UI renders clickable citations and a source preview panel so users can inspect the evidence behind the selected answer.
- Generated reports and score evidence reuse repository paths and line numbers from parsing, scanner, graph, and retrieval outputs.

## PR Risk Analyzer 2.0

- API: `POST /repositories/{repo_id}/pr-risk`
- Inputs: changed file paths, PR title/description, or a public GitHub PR URL.
- For GitHub PR URLs, RepoMindAI fetches the `.diff` representation and extracts changed files. Private PRs or inaccessible URLs fail closed into the normal no-files validation instead of fabricating changes.
- Outputs: blast radius, affected domains, affected services, recommended reviewers, test impact analysis, impact prediction, risk score, review plan, deployment risk, release gate recommendation, and PR review packet.

## Architecture Drift Engine

- API: `GET /repositories/{repo_id}/architecture-drift?baseline_repo_id=...`
- Compares repository vs repository, branch vs branch, commit vs commit, or release vs release metadata when refs are provided.
- Detects new/removed services, domain changes, dependency changes, security changes, external integration changes, API surface changes, and produces a drift timeline, visual diff, and drift report narrative.

## Security Center 2.0

- Source: normalized security scanner findings.
- Scanners: custom rules, high-entropy secret detection, Bandit, Semgrep, Trivy when installed, npm audit when lockfiles exist, and pip-audit when installed.
- Findings are enriched with OWASP category, CWE mapping, CVSS, exploitability, business impact, remediation, affected files, severity, source path, and source line.
- Frontend surfaces include security score, severity mix, OWASP/CWE heatmap, risk matrix, and remediation evidence cards.

## Portfolio Ownership Intelligence

- Multi-repository intelligence maps teams, owners, services, domains, repositories, and ownership relationships.
- Outputs include bus factor, critical ownership concentration, orphaned services, single points of failure, ownership graph, dependency overlap graph, shared vulnerabilities, and portfolio remediation actions.

## Investor-Grade PDF Pipeline

- `EXECUTIVE_SUMMARY.html` is now a board-ready HTML document with cover section, scorecards, explainable score sections, and risk register.
- `EXECUTIVE_SUMMARY.pdf` uses HTML-to-PDF rendering through WeasyPrint when available and falls back to a deterministic PDF writer when the optional renderer is not installed.

## Acquisition Intelligence

- API: `GET /repositories/{repo_id}/acquisition-intelligence`
- Scores: acquisition readiness, maintainability, scalability, security, bus factor, test confidence, CI/CD maturity, documentation quality, and operational readiness.
- Outputs: verdict, reasons, evidence, red flags, negotiation points, investment memo, M&A memo, and technical due-diligence packet.

## Multi-Repository Intelligence 2.0

- API: `GET /repositories/intelligence`
- Adds dependency overlap graph, shared vulnerability detection, risk propagation, duplicate service detection, framework concentration risk, ownership concentration risk, and portfolio remediation center.

## Data Integrity

This platform does not hardcode demo content. Missing signals remain explicit: absent routes, models, CI/CD, git history, or matching flow evidence produce low-confidence or empty-state outputs with reasons.
