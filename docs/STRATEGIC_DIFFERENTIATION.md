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
