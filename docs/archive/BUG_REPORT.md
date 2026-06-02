# Bug Report

Date: 2026-05-23 UTC

## Critical/High Bugs Found and Fixed

1. Multi-model routing hid the fact that no model was actually loaded.
   - Evidence: `backend/repomind/llm/registry.py` routed `analysis`, `judge`, `synthesis`; `TransformersAdapter.generate()` fell back when `_pipeline` was `None`.
   - Fix: replaced with one lazy-loaded `SingleLocalModel` using qwen-judge only.

2. Missing model runtime dependencies.
   - Evidence: actual load failed for AWQ and compressed-tensors checkpoints.
   - Fix: installed and recorded `gptqmodel`, `compressed-tensors`, `torchvision`, `ninja`; updated `pyproject.toml`.

3. AWQ JIT could not find `ninja`.
   - Evidence: `Marlin torch.ops kernels are not properly installed... Ninja is required`.
   - Fix: model adapter prepends `.venv/bin` to `PATH`.

4. Report prompts were too large on real repos and triggered CUDA instability.
   - Evidence: FastAPI E2E failed with `CUDA driver error: device not ready`.
   - Fix: compacted `report_prompt()` to bounded evidence.

5. JSON store crashed on mixed YAML keys.
   - Evidence: `TypeError: '<' not supported between instances of 'bool' and 'str'` from `json.dumps(... sort_keys=True)`.
   - Fix: removed `sort_keys=True` in `RepositoryStore._write()`.

6. Local path import copied generated/heavy directories.
   - Evidence: `ingest_local_path()` ignored only `.git`.
   - Fix: reuse `IGNORED_DIRS` in `shutil.copytree()`.

7. RAG retrieved compiled/example noise for broad questions.
   - Evidence: Next.js “what does this project do?” initially retrieved compiled/example files.
   - Fix: ignore `compiled`, `.min.js`, `.bundle.js`; add query-aware path boosts.

8. Scores were arbitrary and collapsed on large repos.
   - Evidence: security and maintainability were absolute penalties; FastAPI/Flask scored zero.
   - Fix: normalized scoring by file count and severity density.

## Remaining Bugs / Limitations

- qwen-judge output quality is not ideal; it often emits reasoning preambles.
- PostgreSQL path is not used by runtime.
- Celery task exists but API analysis is synchronous.
- ChromaDB dependency exists but runtime vector store is JSON plus deterministic hash embeddings.
- Semgrep is not implemented.
- PDF export is not implemented.
- Frontend lacks automated tests.
- Docker Compose was not verified because Compose is not installed on this machine.
- `npm audit --omit=dev` still reports Next.js advisories; upgrading to Next 16 is breaking on the current Node 18 environment.

