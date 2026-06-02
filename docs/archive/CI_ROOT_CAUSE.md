# CI Root Cause

Date: 2026-05-23

## Failure

GitHub Actions failed before tests started at:

```bash
uv run pytest
```

Resolver conflict:

```text
repomind-ai[analysis]
  -> semgrep
  -> opentelemetry
  -> protobuf < 7

repomind-ai[llm]
  -> gptqmodel
  -> protobuf >= 7.34
```

Result: the dependency graph is unsatisfiable when `analysis` and `llm` are resolved together.

## Files Audited

- `pyproject.toml`
- `.github/workflows/ci.yml`
- `Makefile`
- test imports that touch model status

## What Was Wrong

The workflow had two separate dependency paths:

```yaml
- run: uv pip install -e ".[dev,analysis]"
- run: uv run pytest
```

The first command used the pip-style interface and installed only the project runtime dependencies plus `dev` and `analysis` extras.

The second command was the problem. `uv run pytest` is not equivalent to `.venv/bin/pytest`. It can re-enter uv project resolution/sync before executing the command. In the failing run, that project-resolution path attempted to resolve `repomind-ai[analysis]` and `repomind-ai[llm]` together, even though CI does not need LLM dependencies.

That made CI sensitive to the optional `llm` extra:

- `analysis` includes `semgrep`
- `semgrep` pulls OpenTelemetry packages with protobuf constraints below major 7
- `llm` includes `gptqmodel`
- `gptqmodel` requires protobuf `>=7.34`
- no single protobuf version satisfies both

## Why CI Must Not Resolve `llm`

CI is intended to validate code quality only:

- linting
- lightweight unit tests
- no local model installation
- no GPU runtimes
- no qwen-judge loading
- no `gptqmodel`
- no `compressed-tensors`

Therefore CI must never install or resolve `repomind-ai[llm]`.

## Secondary CI Finding

Fresh-environment verification also showed `fastapi.testclient.TestClient(...).get(...)` hanging in the clean dependency set. This is unrelated to the protobuf conflict but affects the same GitHub Actions job.

The CI health test was changed to call the health function directly. That keeps CI focused on code quality and avoids exercising ASGI integration behavior in this lightweight workflow.

## Correct CI Principle

CI should:

1. Create a virtual environment.
2. Install exactly runtime core + analysis + dev dependencies.
3. Execute binaries from that environment directly.
4. Never call `uv run pytest`.
5. Never resolve the `llm` extra.

The safe execution form is:

```bash
PYTHONPATH=backend .venv/bin/ruff check backend tests scripts
PYTHONPATH=backend .venv/bin/pytest tests/api/test_api.py::test_health_endpoint tests/unit/test_utils_and_parsing.py -q
```
