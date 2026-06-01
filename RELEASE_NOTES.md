# Release Notes

## Production Hardening Remediation

This release remediates the repository audit backlog across security, scalability, storage, AI retrieval, maintainability, and enterprise reporting.

### Highlights

- Added API key protection, request tracing, audit logging, rate limiting, safer CORS defaults, guarded local path import, Git host allowlisting, upload limits, ZIP bomb protections, secret redaction, and safer local model loading.
- Moved repository analysis into background jobs with progress state, cancellation support, bounded workers, and repository purge lifecycle cleanup.
- Replaced JSON metadata persistence with SQLAlchemy-backed repository, job, and artifact tables, plus Alembic migration scaffolding and Docker Compose PostgreSQL wiring.
- Added code-aware and symbol-aware chunking, sensitive chunk filtering, BM25-style lexical retrieval, hybrid retrieval, stricter prompt isolation, and validated chat response envelopes.
- Reduced technical debt by extracting analysis debt logic and dashboard controls.
- Added SARIF export, HTML and PDF executive report artifacts, repository comparison, and safe runtime configuration reporting.

### Validation

- Backend tests: `19 passed, 1 skipped`
- Backend lint: `ruff check` passed
- Backend formatting: `ruff format --check` passed
- Frontend tests/typecheck: `npm run test` passed
- Frontend production build: `npm run build` passed
