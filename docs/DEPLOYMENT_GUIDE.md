# RepoMindAI Deployment Guide

RepoMindAI can run locally with Docker Compose and can be deployed to managed container platforms. Production deployments must use PostgreSQL, API-key or OAuth protection, local path import disabled, and persistent volumes for generated reports and indexes.

## Baseline Production Compose

Use `deploy/docker-compose.production.yml`.

Required environment:

- `POSTGRES_PASSWORD`
- `REPOMIND_API_KEY`
- `FRONTEND_ORIGIN`
- `API_BASE_URL`

Run:

```bash
docker compose -f deploy/docker-compose.production.yml up --build
```

## Managed Platforms

- Railway: `deploy/railway.toml`
- Render: `deploy/render.yaml`
- Fly.io: `deploy/fly.toml`
- AWS starting point: `deploy/aws/terraform/`

The AWS Terraform intentionally provisions only the network and PostgreSQL foundation. Container service, load balancer, secrets manager, and object storage should be added according to the target account’s security baseline before public launch.

## Production Controls

- Set `REPOMIND_REQUIRE_API_KEY=true`.
- Set `REPOMIND_ENABLE_LOCAL_PATH_IMPORT=false`.
- Set `REPOMIND_TRUST_REMOTE_MODEL_CODE=false`.
- Use `postgresql+psycopg://...` for `REPOMIND_DATABASE_URL`.
- Restrict `REPOMIND_ALLOWED_GIT_HOSTS` to approved hosts.
- Put the backend behind HTTPS with request/body size limits.
- Mount durable storage for reports, Chroma, and repository artifacts.

## Migration

Run Alembic before serving traffic:

```bash
cd backend
alembic upgrade head
```

The application also contains a compatibility guard for older local SQLite databases. That guard is not a substitute for production migrations.
