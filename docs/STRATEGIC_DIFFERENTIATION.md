# Strategic Differentiation

RepoMindAI now treats a repository as an evidence graph rather than only a set of files. The goal is to create private, audit-grade code intelligence that IDE coding assistants do not provide out of the box.

## Repository Knowledge Graph

Architecture:

- The analyzer builds a deterministic knowledge graph during repository analysis.
- Graph entities include files, routes, data models, symbols, domains, and hotspots.
- Relations are derived from imports, definitions, routes, and persistence signals.
- The graph is stored in the repository analysis summary and exposed through `/repositories/{repo_id}/knowledge-graph`.

User value:

- Engineering leaders can see product domains, trust boundaries, and critical files without reading the whole codebase.
- Later intelligence features reuse the same evidence substrate for PR risk, drift, due diligence, and multi-repo analysis.

## PR Risk Analysis

Architecture:

- The `/repositories/{repo_id}/pr-risk` endpoint accepts changed file paths and maps them onto the repository knowledge graph.
- Risk scoring combines graph hotspots, security findings, architectural layer, configuration surfaces, and impacted domains.
- The dashboard exposes required review and test strategy instead of only a numeric score.

User value:

- Teams can judge blast radius before merging a PR.
- CTOs get an evidence-backed review checklist that coding assistants do not infer from a whole-repo graph by default.

## Architecture Drift Detection

Architecture:

- Each analyzed repository can be converted into a stable architecture fingerprint.
- `/repositories/{repo_id}/architecture-drift?baseline_id=...` compares domains, route surfaces, data models, frameworks, hotspots, and score regressions.
- The dashboard turns drift into release-review recommendations.

User value:

- Teams can detect whether a repo is drifting from its intended architecture.
- Investors and CTOs can compare snapshots or branches as evidence of architectural control.

## CTO Due-Diligence Reports

Architecture:

- `/repositories/{repo_id}/due-diligence` returns a structured CTO diligence packet.
- Report generation also emits `CTO_DUE_DILIGENCE.md` in every report bundle.
- The report combines score evidence, security findings, knowledge graph hotspots, enterprise gaps, and diligence questions.

User value:

- Produces investor/acquirer-ready evidence instead of a generic code summary.
- Helps founders and CTOs answer technical diligence questions before an external review.

## Multi-Repository Intelligence

Architecture:

- `/repositories/intelligence` aggregates every analyzed repository into a portfolio view.
- The aggregator compares languages, frameworks, repeated domains, repository scorecards, and cross-repo risks.
- The dashboard includes a portfolio view that is independent of any single active repository.

User value:

- CTOs can inspect organization-level risk and duplicated domains.
- This creates a moat around private codebase intelligence rather than single-file coding assistance.
