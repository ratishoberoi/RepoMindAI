# Setup Guide

## Backend

```bash
cd ${PROJECT_ROOT}
uv venv
uv pip install -e ".[dev,analysis]"
PYTHONPATH=backend uvicorn repomind.main:app --reload
```

Local model inference:

```bash
uv pip install -e ".[llm]"
```

The selected model loads lazily on the first report or chat generation.

## Frontend

```bash
cd ${PROJECT_ROOT}/frontend
npm install
npm run dev
```

## Services

RepoMind AI stores repository metadata in `data/metadata.json`, generated reports under
`reports/generated`, and semantic vector indexes in embedded ChromaDB under `data/chroma`.
It does not require PostgreSQL or Redis.

For a production-like local deployment, install Docker Compose and run:

```bash
docker compose up --build
```
