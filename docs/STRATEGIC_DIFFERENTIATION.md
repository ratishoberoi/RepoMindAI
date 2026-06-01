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
