# Changelog

## Unreleased

### Security

- Added API key authentication across protected API routes.
- Added request IDs, audit logging, and in-memory rate limiting.
- Restricted local path import behind configuration and allowed roots.
- Restricted Git ingestion to HTTPS allowlisted hosts.
- Added upload size limits, ZIP file-count limits, extracted-size limits, compression-ratio checks, and ZIP symlink rejection.
- Added secret redaction for indexed chunks, retrieved evidence, generated answers, and reports.
- Disabled remote model code trust by default.

### Scalability

- Added background analysis jobs with persisted progress and cancellation state.
- Added bounded analysis workers.
- Added repository purge cleanup for source files, Chroma collections, index manifests, reports, jobs, and artifacts.
- Added repository file and indexed chunk caps.
- Batched embedding generation and Chroma upserts to reduce memory pressure.
- Made metadata writes atomic before migrating storage.

### Storage

- Added SQLAlchemy repository, analysis job, and artifact tables.
- Added PostgreSQL-compatible persistence and SQLite local fallback.
- Added Alembic migration scaffolding.
- Added safe migration from legacy `data/metadata.json`.
- Added Docker Compose PostgreSQL service.

### AI

- Added symbol-aware code chunking for Python and JS/TS files.
- Added sensitive chunk metadata and retrieval filtering.
- Added BM25-style lexical candidates alongside vector retrieval and path-aware reranking.
- Added structured chat response validation.
- Strengthened prompt isolation against repository prompt injection.

### Product

- Added SARIF security export.
- Added HTML and PDF executive summary artifacts.
- Added repository comparison API.
- Added safe runtime configuration endpoint.
- Added frontend typecheck/test scripts.

### Refactor

- Extracted technical debt analysis into `backend/repomind/analysis/debt.py`.
- Extracted reusable dashboard controls into `frontend/components/dashboard/Controls.tsx`.
- Applied repository-wide Python formatting.
