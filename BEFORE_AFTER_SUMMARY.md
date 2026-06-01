# Before vs After Summary

## Before

- Public API with no authentication or authorization boundary.
- Local path import could copy arbitrary readable server directories.
- ZIP ingestion lacked resource limits.
- Git ingestion accepted broad clone targets.
- Repository analysis ran synchronously inside request handlers.
- Metadata used a single JSON file with whole-file rewrites.
- RAG used fixed-size chunks without symbol metadata or lexical retrieval.
- Secrets could appear in indexed chunks, retrieved evidence, reports, or answers.
- No SARIF, HTML, PDF, comparison, or safe runtime config outputs.
- Large frontend and backend modules concentrated unrelated responsibilities.

## After

- Protected API routes require an API key by default.
- Request tracing, audit logging, rate limiting, safer CORS, and secure runtime config are in place.
- Local import is disabled by default and constrained by allowed roots when enabled.
- Git ingestion is HTTPS and host allowlist constrained.
- ZIP and upload protections limit file count, extracted size, compressed ratio, symlinks, and upload size.
- Analysis runs as a background job with progress, cancellation, bounded workers, and status polling.
- SQLAlchemy persistence stores repositories, jobs, and artifacts with PostgreSQL support and legacy JSON migration.
- RAG uses symbol-aware chunks, sensitive evidence filtering, Chroma vector retrieval, BM25-style lexical retrieval, and structured answer validation.
- Reports include Markdown, SARIF, HTML, PDF, and export bundles.
- Repository comparison and runtime configuration endpoints are available.
- Technical debt logic and reusable dashboard controls are split into dedicated modules.

## Validation Snapshot

- Backend tests: `19 passed, 1 skipped`
- Backend lint and formatting: passed
- Frontend typecheck/test: passed
- Frontend production build: passed
