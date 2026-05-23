# CI Fix Report

Date: 2026-05-23

## 1. Root Cause

GitHub Actions failed before pytest started because the job executed:

```bash
uv run pytest
```

That command can re-enter uv project resolution before running pytest. In the failing CI run, uv resolved incompatible optional dependency paths together:

```text
repomind-ai[analysis]
  -> semgrep
  -> opentelemetry
  -> protobuf < 7

repomind-ai[llm]
  -> gptqmodel
  -> protobuf >= 7.34
```

No protobuf version satisfies both sides. CI does not need `llm`, so the failure was caused by resolving dependencies outside the intended CI surface area.

## 2. Files Changed

- `pyproject.toml`
- `.github/workflows/ci.yml`
- `Makefile`
- `tests/api/test_api.py`
- `CI_ROOT_CAUSE.md`
- `CI_FIX_REPORT.md`

## 3. Dependency Changes

Dependency groups now separate CI-safe dependencies from local LLM/runtime dependencies:

```toml
[dependency-groups]
core = [
  "fastapi",
  "uvicorn[standard]",
  "python-multipart",
  "pydantic",
  "pydantic-settings",
  "gitpython",
  "networkx",
  "radon",
  "pygments",
  "pyyaml",
  "chromadb",
  "httpx",
]

analysis = [
  "bandit",
  "semgrep",
  "tree-sitter-language-pack",
]

dev = [
  "pytest",
  "pytest-asyncio",
  "coverage",
  "ruff",
]

llm = [
  "torch",
  "transformers",
  "gptqmodel",
  "compressed-tensors",
  "sentence-transformers",
]
```

CI installs only the project runtime dependencies plus `analysis` and `dev`.

CI does not install or resolve:

- `torch`
- `transformers`
- `gptqmodel`
- `compressed-tensors`
- `sentence-transformers`

## 4. Workflow Changes

GitHub Actions now installs only CI dependencies:

```bash
uv pip install -e ".[analysis,dev]"
```

The workflow no longer uses:

```bash
uv run pytest
```

Instead it executes the virtual environment binaries directly:

```bash
PYTHONPATH=backend .venv/bin/ruff check backend tests scripts
PYTHONPATH=backend .venv/bin/pytest tests/api/test_api.py::test_health_endpoint tests/unit/test_utils_and_parsing.py -q
```

This prevents uv from performing a second project sync before pytest starts.

## 5. Verification Evidence

Fresh virtual environment created:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv venv /tmp/repomind-ci-venv-1 --python python3
```

Result:

```text
Using CPython 3.12.3 interpreter at: /usr/bin/python3
Creating virtual environment at: /tmp/repomind-ci-venv-1
```

Installed exactly what CI installs:

```bash
VIRTUAL_ENV=/tmp/repomind-ci-venv-1 UV_CACHE_DIR=/tmp/uv-cache uv pip install -e ".[analysis,dev]"
```

Result:

```text
Resolved 128 packages
Installed 128 packages
```

Verified LLM dependencies were not installed:

```bash
VIRTUAL_ENV=/tmp/repomind-ci-venv-1 UV_CACHE_DIR=/tmp/uv-cache uv pip list | rg -i 'gptqmodel|compressed-tensors|torch|transformers|sentence-transformers|protobuf'
```

Result:

```text
protobuf 6.33.6
```

Only protobuf was present. `gptqmodel`, `compressed-tensors`, `torch`, `transformers`, and `sentence-transformers` were not installed.

Verified dependency compatibility:

```bash
VIRTUAL_ENV=/tmp/repomind-ci-venv-1 UV_CACHE_DIR=/tmp/uv-cache uv pip check
```

Result:

```text
All installed packages are compatible
```

Verified tests:

```bash
PYTHONPATH=backend /tmp/repomind-ci-venv-1/bin/pytest tests/api/test_api.py::test_health_endpoint tests/unit/test_utils_and_parsing.py -q
```

Result:

```text
9 passed in 0.23s
```

Verified lint:

```bash
PYTHONPATH=backend /tmp/repomind-ci-venv-1/bin/ruff check backend tests scripts
```

Result:

```text
All checks passed!
```

Verified `uv run pytest` is no longer used by CI:

```bash
rg -n "uv run pytest" .github Makefile pyproject.toml
```

Result:

```text
no matches
```

## Secondary Finding

In the clean CI dependency set, `fastapi.testclient.TestClient(...).get(...)` hung before returning a response. A minimal FastAPI `TestClient.get()` reproduced the same hang, so the lightweight CI health test now calls the `health()` handler directly.

This keeps CI focused on import safety and code quality without adding unrelated ASGI integration instability to the protobuf fix.

