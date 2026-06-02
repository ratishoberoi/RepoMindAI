# Benchmark Results

Started: 2026-05-23 11:17:00 UTC

Benchmarks use real ingestion, static analysis, BGE embeddings, ChromaDB indexing, qwen-judge report generation, qwen-judge repository explainers, and cleanup verification.

## FastAPI

- Source: `https://github.com/fastapi/fastapi`
- Status: **passed**
- Repository ID: `c9e588c3b3b04339a2d432a899c6bf80`
- Ingestion time: 9.128s
- Analysis wall time: 214.669s
- Indexing time: 34.913s
- Embedding time: 22.133s
- Chroma upsert time: 12.487s
- Report generation time: 75.228s
- Files analyzed: 2748
- Indexed chunks: 10862
- Routes: 1254
- Scores: `{'security': 42.9, 'maintainability': 67.7, 'production_readiness': 68.9, 'recruiter': 91.9, 'cto': 65.3, 'confidence': 95}`

### Retrieval Quality

- authentication: **strong**, 0.054s, top score `0.7928`
  Top paths: `docs/en/docs/tutorial/security/index.md`, `docs/en/docs/tutorial/security/first-steps.md`, `docs/en/docs/tutorial/security/simple-oauth2.md`, `docs/en/docs/tutorial/security/oauth2-jwt.md`, `docs/en/docs/tutorial/security/first-steps.md`
- routing: **strong**, 0.012s, top score `0.5624`
  Top paths: `docs/en/docs/tutorial/bigger-applications.md`, `docs/en/docs/tutorial/first-steps.md`, `docs/en/docs/tutorial/bigger-applications.md`, `fastapi/routing.py`, `docs/en/docs/how-to/custom-request-and-route.md`
- database: **strong**, 0.011s, top score `0.7236`
  Top paths: `docs/en/docs/tutorial/sql-databases.md`, `docs/en/docs/tutorial/sql-databases.md`, `docs/en/docs/tutorial/sql-databases.md`, `docs/en/docs/tutorial/sql-databases.md`, `docs/uk/docs/tutorial/sql-databases.md`

### Architecture Quality

- Score: 100 / 100
- Diagrams: 5
- Components: 14
- Important files: 10
- Route files: 544
- Database model files: 7

### Explainer Quality

- authentication: 22.685s, citations=6, explanation=True, risks=True, improvements=True
  Critical files: `docs/en/docs/tutorial/security/index.md`, `docs/en/docs/tutorial/security/first-steps.md`, `docs/en/docs/tutorial/security/simple-oauth2.md`, `docs/en/docs/tutorial/security/oauth2-jwt.md`, `docs/de/docs/advanced/security/http-basic-auth.md`, `docs/de/docs/advanced/security/index.md`
- routing: 25.67s, citations=6, explanation=True, risks=True, improvements=True
  Critical files: `docs/en/docs/tutorial/bigger-applications.md`, `docs/en/docs/tutorial/first-steps.md`, `fastapi/routing.py`, `docs/en/docs/how-to/custom-request-and-route.md`, `docs_src/additional_responses/tutorial001_py310.py`, `docs_src/additional_responses/tutorial002_py310.py`
- database: 22.439s, citations=6, explanation=True, risks=True, improvements=True
  Critical files: `docs/en/docs/tutorial/sql-databases.md`, `docs/uk/docs/tutorial/sql-databases.md`, `docs_src/sql_databases/tutorial001_py310.py`, `docs_src/dependencies/tutorial013_an_py310.py`, `docs_src/dependencies/tutorial014_an_py310.py`, `docs_src/sql_databases/tutorial001_an_py310.py`

### Cleanup Verification

- Repository deleted: True
- Path exists after cleanup: False
- Reports still exist: True
- Analysis summary exists: True

## Flask

- Source: `https://github.com/pallets/flask`
- Status: **passed**
- Repository ID: `e61f2b3dcc874b2ea1e2f59de40cccff`
- Ingestion time: 4.078s
- Analysis wall time: 71.975s
- Indexing time: 1.94s
- Embedding time: 1.138s
- Chroma upsert time: 0.789s
- Report generation time: 67.421s
- Files analyzed: 231
- Indexed chunks: 857
- Routes: 20
- Scores: `{'security': 25.3, 'maintainability': 37.3, 'production_readiness': 55.9, 'recruiter': 84.3, 'cto': 48.9, 'confidence': 95}`

### Retrieval Quality

- authentication: **strong**, 0.05s, top score `0.7749`
  Top paths: `docs/web-security.rst`, `examples/tutorial/flaskr/auth.py`, `examples/tutorial/tests/test_auth.py`, `examples/tutorial/flaskr/auth.py`, `examples/tutorial/tests/test_auth.py`
- routing: **partial**, 0.011s, top score `0.6112`
  Top paths: `docs/design.rst`, `docs/api.rst`, `docs/lifecycle.rst`, `docs/api.rst`, `src/flask/sansio/scaffold.py`
- database: **strong**, 0.02s, top score `0.8305`
  Top paths: `docs/patterns/sqlite3.rst`, `docs/tutorial/database.rst`, `docs/tutorial/database.rst`, `docs/patterns/sqlite3.rst`, `docs/patterns/sqlite3.rst`

### Architecture Quality

- Score: 100 / 100
- Diagrams: 5
- Components: 14
- Important files: 10
- Route files: 7
- Database model files: 1

### Explainer Quality

- authentication: 22.769s, citations=6, explanation=True, risks=True, improvements=True
  Critical files: `docs/web-security.rst`, `examples/tutorial/flaskr/auth.py`, `examples/tutorial/tests/test_auth.py`, `examples/tutorial/flaskr/templates/auth/login.html`, `examples/tutorial/flaskr/templates/auth/register.html`
- routing: 23.352s, citations=6, explanation=True, risks=True, improvements=True
  Critical files: `docs/design.rst`, `docs/api.rst`, `docs/lifecycle.rst`, `src/flask/sansio/scaffold.py`, `docs/quickstart.rst`, `examples/celery/src/task_app/views.py`
- database: 23.101s, citations=6, explanation=True, risks=True, improvements=True
  Critical files: `docs/patterns/sqlite3.rst`, `docs/tutorial/database.rst`, `docs/patterns/sqlalchemy.rst`, `tests/test_config.py`

### Cleanup Verification

- Repository deleted: True
- Path exists after cleanup: False
- Reports still exist: True
- Analysis summary exists: True

## Next.js

- Source: `https://github.com/vercel/next.js`
- Status: **passed**
- Repository ID: `05221cad5f6a4aa69ecd1e61798ae46b`
- Ingestion time: 23.016s
- Analysis wall time: 200.799s
- Indexing time: 92.848s
- Embedding time: 47.352s
- Chroma upsert time: 44.085s
- Report generation time: 65.757s
- Files analyzed: 25024
- Indexed chunks: 50996
- Routes: 445
- Scores: `{'security': 20, 'maintainability': 38.9, 'production_readiness': 59.0, 'recruiter': 84.7, 'cto': 49.3, 'confidence': 95}`

### Retrieval Quality

- authentication: **strong**, 0.041s, top score `0.7917`
  Top paths: `docs/01-app/02-guides/authentication.mdx`, `docs/01-app/02-guides/authentication.mdx`, `docs/01-app/02-guides/authentication.mdx`, `docs/01-app/02-guides/authentication.mdx`, `docs/01-app/02-guides/data-security.mdx`
- routing: **strong**, 0.012s, top score `0.6086`
  Top paths: `docs/02-pages/03-building-your-application/01-routing/03-linking-and-navigating.mdx`, `docs/02-pages/03-building-your-application/01-routing/07-api-routes.mdx`, `docs/01-app/01-getting-started/15-route-handlers.mdx`, `docs/02-pages/03-building-your-application/02-rendering/02-static-site-generation.mdx`, `docs/01-app/02-guides/multi-zones.mdx`
- database: **strong**, 0.011s, top score `0.7218`
  Top paths: `examples/with-mysql/README.md`, `examples/with-passport-and-next-connect/lib/db.js`, `examples/with-mysql/README.md`, `examples/with-mysql/.env.example`, `docs/01-app/02-guides/data-security.mdx`

### Architecture Quality

- Score: 100 / 100
- Diagrams: 5
- Components: 14
- Important files: 10
- Route files: 399
- Database model files: 0

### Explainer Quality

- authentication: 18.916s, citations=6, explanation=True, risks=True, improvements=True
  Critical files: `docs/01-app/02-guides/authentication.mdx`, `docs/01-app/02-guides/data-security.mdx`, `.agents/skills/authoring-skills/SKILL.md`, `docs/01-app/02-guides/content-security-policy.mdx`, `docs/01-app/03-api-reference/03-file-conventions/unauthorized.mdx`, `docs/01-app/03-api-reference/04-functions/unauthorized.mdx`
- routing: 23.232s, citations=6, explanation=True, risks=True, improvements=True
  Critical files: `docs/02-pages/03-building-your-application/01-routing/03-linking-and-navigating.mdx`, `docs/02-pages/03-building-your-application/01-routing/07-api-routes.mdx`, `docs/01-app/01-getting-started/15-route-handlers.mdx`, `docs/02-pages/03-building-your-application/02-rendering/02-static-site-generation.mdx`, `docs/01-app/02-guides/multi-zones.mdx`, `docs/01-app/03-api-reference/07-adapters/05-routing-with-next-routing.mdx`
- database: 22.278s, citations=6, explanation=True, risks=True, improvements=True
  Critical files: `examples/with-mysql/README.md`, `examples/with-passport-and-next-connect/lib/db.js`, `examples/with-mysql/.env.example`, `docs/01-app/02-guides/data-security.mdx`

### Cleanup Verification

- Repository deleted: True
- Path exists after cleanup: False
- Reports still exist: True
- Analysis summary exists: True

## RepoMindAI

- Source: `${PROJECT_ROOT}`
- Status: **passed**
- Repository ID: `41060817053c4d099c0ac6bee28defcb`
- Ingestion time: 3.618s
- Analysis wall time: 84.715s
- Indexing time: 9.77s
- Embedding time: 9.321s
- Chroma upsert time: 0.444s
- Report generation time: 73.348s
- Files analyzed: 66
- Indexed chunks: 220
- Routes: 16
- Scores: `{'security': 63.2, 'maintainability': 1.0, 'production_readiness': 63.8, 'recruiter': 75.2, 'cto': 54.7, 'confidence': 95}`

### Retrieval Quality

- authentication: **partial**, 0.74s, top score `0.68`
  Top paths: `backend/repomind/security/scanner.py`, `backend/repomind/security/semgrep_rules.yml`, `backend/repomind/security/scanner.py`, `backend/repomind/security/scanner.py`, `frontend/components/RepoMindDashboard.tsx`
- routing: **partial**, 0.721s, top score `0.78`
  Top paths: `backend/repomind/main.py`, `backend/repomind/main.py`, `backend/repomind/main.py`, `backend/repomind/main.py`, `scripts/run_real_world_benchmarks.py`
- database: **partial**, 0.768s, top score `0.9`
  Top paths: `backend/repomind/core/store.py`, `backend/repomind/core/store.py`, `backend/repomind/rag/indexer.py`, `backend/repomind/rag/indexer.py`, `backend/repomind/rag/retriever.py`

### Architecture Quality

- Score: 100 / 100
- Diagrams: 5
- Components: 14
- Important files: 10
- Route files: 1
- Database model files: 0

### Explainer Quality

- authentication: 30.189s, citations=6, explanation=True, risks=True, improvements=True
  Critical files: `backend/repomind/security/scanner.py`, `backend/repomind/security/semgrep_rules.yml`, `frontend/components/RepoMindDashboard.tsx`, `scripts/run_real_world_benchmarks.py`
- routing: 26.852s, citations=6, explanation=True, risks=True, improvements=True
  Critical files: `backend/repomind/main.py`, `scripts/run_real_world_benchmarks.py`, `frontend/lib/api.ts`
- database: 22.609s, citations=6, explanation=True, risks=True, improvements=True
  Critical files: `backend/repomind/core/store.py`, `backend/repomind/rag/indexer.py`, `backend/repomind/rag/retriever.py`

### Cleanup Verification

- Repository deleted: True
- Path exists after cleanup: False
- Reports still exist: True
- Analysis summary exists: True

