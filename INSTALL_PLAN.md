# RepoMind AI Install Plan

This plan is based on `LOCAL_MACHINE_AUDIT.md` and follows the local-first constraints for RepoMind AI.

## Already Available

- Ubuntu 24.04.4 on WSL2
- Python 3.12.3
- pip 24.0
- uv 0.11.13
- Node.js v18.19.1 and npm 9.2.0
- Git 2.43.0
- Docker engine 29.1.3
- NVIDIA RTX 5090 with 32607 MiB VRAM
- CUDA 13.2 compiler
- 45 GiB RAM
- 841 GiB free disk space under `/`

## Local Assets to Reuse

The following existing model folders must be reused and must not be downloaded again:

- Main analysis model: `/home/ratish/Forge/models/qwen-primary`
- Judge model: `/home/ratish/Forge/models/qwen-judge`
- Synthesis model: `/home/ratish/Forge/models/deepseek-synth`

RepoMind AI will register these by role in its model registry instead of hardcoding brand-specific behavior.

## Must Be Installed in the Project Environment

Backend Python dependencies, installed into `/home/ratish/RepoMindAI/.venv`:

- FastAPI and Uvicorn for the API
- Pydantic settings and validation packages
- SQLAlchemy and psycopg for PostgreSQL metadata
- ChromaDB for local vector search
- Redis and Celery clients for background jobs
- GitPython for repository cloning
- NetworkX for dependency and relationship graphs
- Radon for complexity and maintainability metrics
- Pygments for local syntax/language assistance
- Bandit for Python security scans
- Semgrep for rule-based scans where available
- Tree-sitter Python bindings and language packages where feasible
- Transformers, safetensors, accelerate, and torch for local HF checkpoint loading
- sentence-transformers or a local fallback embedding implementation
- pytest, pytest-asyncio, httpx, and coverage tooling for validation

Frontend dependencies, installed under `/home/ratish/RepoMindAI/frontend`:

- Next.js
- TypeScript
- Tailwind CSS
- shadcn/ui-compatible primitives
- React UI dependencies
- Vitest/Testing Library if frontend tests are enabled

## Must Be Installed or Replaced for Full Container Workflow

- Docker Compose is missing. Either install the Docker Compose plugin or use a compatible `docker-compose` binary.
- PostgreSQL and Redis are not installed locally. They can be provided by Docker Compose.

## Can Be Skipped Initially

- Ollama, because the available models are Hugging Face-style checkpoints rather than Ollama models.
- vLLM, because the first implementation can use a Transformers backend and a deterministic fallback backend.
- Downloading any additional LLMs, because the required Forge model folders exist.
- Downloading a large embedding model. The first implementation should use a small local deterministic embedding fallback and optionally load a local sentence-transformer only if one already exists.
- Installing Poetry, because uv is available.
- Installing pnpm or yarn, because npm is available.

## Must Not Be Downloaded

- Any replacement for `/home/ratish/Forge/models/qwen-primary`
- Any replacement for `/home/ratish/Forge/models/qwen-judge`
- Any replacement for `/home/ratish/Forge/models/deepseek-synth`
- Any paid API SDKs that imply cloud inference use as a runtime dependency
- OpenAI, Anthropic, Groq, Pinecone, or other SaaS API clients

## Offline Behavior

After setup, RepoMind AI should work offline for:

- ZIP repository ingestion
- Local path ingestion
- Repository file scanning
- Static analysis
- Local model inference
- Embedding and retrieval
- Report generation
- UI and API usage

The only expected network operation after setup is cloning a GitHub repository when the user provides a GitHub URL.

## Implementation Strategy

1. Create a monorepo-style project with `backend`, `frontend`, `docs`, `sample_repos`, and `reports`.
2. Implement the backend so it can run with local SQLite in development when PostgreSQL is unavailable, while retaining PostgreSQL configuration and Docker Compose for production-like local deployments.
3. Implement the model adapter layer with backend detection:
   - Hugging Face Transformers when `config.json`, tokenizer files, and safetensor/bin weights are present.
   - GGUF runner placeholder when `.gguf` files are present.
   - Ollama runner only if Ollama exists and a model is explicitly configured.
   - Deterministic local fallback when runtime dependencies are unavailable, so tests and static analysis remain usable offline.
4. Implement local deterministic embeddings first, with an optional sentence-transformers adapter if a local embedding checkpoint is configured.
5. Add tests that avoid loading the large models by default. Model verification tests should validate metadata and adapter selection, and only perform heavy loading when explicitly enabled.
6. Keep all generated repositories, indexes, exports, and working files inside `/home/ratish/RepoMindAI/data` and `/home/ratish/RepoMindAI/reports`.
