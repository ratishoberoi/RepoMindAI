# Release Candidate Report

Date: 2026-05-23 UTC

## Completed Features

- GitHub, ZIP, and local repository ingestion.
- Single local qwen-judge inference path.
- BGE embeddings with ChromaDB persistence.
- Retrieval with reranking and citations.
- Tree-sitter parsing for Python, JavaScript, TypeScript, JSX, and TSX.
- AST extraction for imports, exports, classes, functions, methods, routes, and database models.
- Mermaid architecture diagrams: system, component, dependency, service, data flow.
- Security scanning with custom rules, Bandit, and Semgrep.
- Evidence-backed scoring for security, maintainability, production, recruiter, and CTO views.
- Post-analysis repository content deletion and scheduled cleanup.
- Dark frontend with rendered Mermaid diagrams, architecture viewer, repository map, dependency graph, file tree, report viewer, and semantic chat.
- Real-world benchmark harness.

## Verified Features

Verification commands:

```bash
PYTHONPATH=backend .venv/bin/ruff check backend tests scripts
PYTHONPATH=backend .venv/bin/pytest tests/api/test_api.py::test_health_endpoint tests/unit/test_utils_and_parsing.py -q
cd frontend && npm run build
cd frontend && npm audit --omit=dev --json
PYTHONPATH=backend .venv/bin/python scripts/run_real_world_benchmarks.py
```

Results:

- Ruff: passed.
- Focused backend tests: 9 passed.
- Frontend production build: passed.
- Real-world benchmarks: FastAPI, Flask, Next.js, RepoMindAI passed.
- Cleanup verification: passed for all benchmark targets.
- Dependency audit: failed with 1 high and 1 moderate advisory through Next.js/PostCSS.

## Benchmark Results

| Target | Analysis | Indexing | Report Gen | Files | Chunks | Retrieval | Cleanup |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
| FastAPI | 214.669s | 34.913s | 75.228s | 2,748 | 10,862 | auth/routing/db strong | passed |
| Flask | 71.975s | 1.940s | 67.421s | 231 | 857 | auth/db strong, routing partial | passed |
| Next.js | 200.799s | 92.848s | 65.757s | 25,024 | 50,996 | auth/routing/db strong | passed |
| RepoMindAI | 84.715s | 9.770s | 73.348s | 66 | 220 | auth/routing/db partial | passed |

Detailed benchmark output is in `BENCHMARK_RESULTS.md` and `data/validation/real_world_benchmarks.json`.

## Remaining Gaps

- Upgrade Next.js safely to clear current advisories. Current fix path is a major upgrade to Next 16.
- Add Playwright browser tests and screenshot evidence.
- Improve qwen-judge report polishing further; model output still occasionally has “analysis process” phrasing.
- Reduce report generation latency through streaming, shorter prompts, or background jobs.
- Improve self-retrieval so RepoMindAI questions route consistently to implementation files instead of benchmark/support files.
- Make architecture quality scoring stricter.
- Add progress streaming for long clone/index/report phases.

## Scores

- GitHub readiness score: **68 / 100**
- LinkedIn showcase score: **82 / 100**

LinkedIn showcase is higher because the local-model, benchmarked, visual repo-intelligence story is strong. GitHub readiness is lower because public users will notice dependency advisories, setup specificity, long generation latency, and limited browser test evidence.
