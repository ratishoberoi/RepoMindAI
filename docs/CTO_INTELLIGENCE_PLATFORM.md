# RepoMindAI CTO Intelligence Platform

RepoMindAI turns repository analysis artifacts into CTO, diligence, and portfolio intelligence. Every screen and API in this layer is derived from repository summaries, dependency graphs, security findings, code parsing results, git history when available, and generated reports.

## Architecture Explorer

- API: `GET /repositories/{repo_id}/architecture-explorer`
- Source: parsed routes, symbols, database models, dependency graph edges, stack metadata, and security/configuration signals.
- Outputs: named request flows, sequence diagrams, dependency paths, executive/engineering/onboarding narratives, and `ONBOARDING.md` content.
- Supported flow families: authentication, login, signup, payment, file upload, data flow, and notification. Unsupported or absent flows are reported with low confidence instead of synthetic examples.

## Knowledge Graph 3.0

- API: `GET /repositories/{repo_id}/knowledge-graph`
- Adds cluster evidence for Auth, API, Database, Security, Payments, Infrastructure, Frontend, and Application domains.
- Adds graph insights for large symbol concentration, dependency bottlenecks, architecture hotspots, security hotspots, critical paths, and git timeline events when local git history is available.

## Executive Report Engine

- API: `GET /repositories/{repo_id}/executive-reports`
- Report artifacts: `EXECUTIVE_REPORT_PACK.md`, `ONBOARDING.md`, `EXECUTIVE_SUMMARY.html`, `EXECUTIVE_SUMMARY.pdf`, SARIF, and persona markdown reports.
- Reports are deterministic, evidence-first packets: board report, CTO report, investor report, security report, and 30/60/90 engineering roadmap.

## Acquisition Intelligence

- API: `GET /repositories/{repo_id}/acquisition-intelligence`
- Scores: acquisition readiness, maintainability, scalability, security, bus factor, test confidence, CI/CD maturity, documentation quality, and operational readiness.
- Outputs: verdict, reasons, evidence, red flags, negotiation points, investment memo, M&A memo, and technical due-diligence packet.

## Multi-Repository Intelligence 2.0

- API: `GET /repositories/intelligence`
- Adds dependency overlap graph, shared vulnerability detection, risk propagation, duplicate service detection, framework concentration risk, ownership concentration risk, and portfolio remediation center.

## Data Integrity

This platform does not hardcode demo content. Missing signals remain explicit: absent routes, models, CI/CD, git history, or matching flow evidence produce low-confidence or empty-state outputs with reasons.
