# Path Fix Report

Date: 2026-05-23

## 1. Root Cause

GitHub Actions was failing during application import, before meaningful tests could run.

The import path was:

```text
get_settings()
  -> ensure_dirs()
  -> Path.mkdir()
```

The settings defaults contained workstation-specific absolute paths. On a clean runner, `ensure_dirs()` attempted to create directories outside the checked-out repository and hit a permission error.

This was a filesystem configuration bug, not a pytest bug.

## 2. Hardcoded Paths Found

The audit found machine-specific paths in:

- `backend/repomind/core/config.py`
- `tests/conftest.py`
- `tests/api/test_api.py`
- `tests/integration/test_analysis_pipeline.py`
- `tests/unit/test_utils_and_parsing.py`
- `.env.example`
- `docker-compose.yml`
- `frontend/components/RepoMindDashboard.tsx`
- `README.md`
- `docs/SETUP.md`
- `docs/USAGE.md`
- `docs/MODEL_USAGE.md`
- `INSTALL_PLAN.md`
- `MODEL_VALIDATION.md`
- `MODEL_BENCHMARK.md`
- `REALITY_CHECK.md`
- `FINAL_VERIFICATION_REPORT.md`
- `PRODUCT_REVIEW.md`
- `PROJECT_HIGHLIGHTS.md`
- `GITHUB_RELEASE_CHECKLIST.md`
- `LOCAL_MACHINE_AUDIT.md`
- `BENCHMARK_RESULTS.md`
- `data/validation/*.json`

The full audit is in `PATH_AUDIT.md`. User-home literals are redacted there to avoid reintroducing the portability failure.

## 3. Fixes Applied

### Settings

`backend/repomind/core/config.py` now detects the project root from the current file location and `pyproject.toml`.

Default paths are now relative to the detected project root:

- `DATA_DIR` -> `./data`
- `REPORTS_DIR` -> `./reports`
- `INDEX_DIR` -> `./data/indexes`
- `CHROMA_DIR` -> `./data/chroma`
- `UPLOAD_DIR` -> `./data/uploads`
- `MODEL_PATH` -> `./models/qwen-judge`

Supported environment variables:

- `REPOMIND_DATA_DIR` or `DATA_DIR`
- `REPOMIND_REPORTS_DIR`, `REPOMIND_REPORT_DIR`, `REPORTS_DIR`, or `REPORT_DIR`
- `REPOMIND_INDEX_DIR`, `REPOMIND_INDEXES_DIR`, `INDEX_DIR`, or `INDEXES_DIR`
- `REPOMIND_CHROMA_DIR`, `REPOMIND_CHROMA_PATH`, `CHROMA_DIR`, or `CHROMA_PATH`
- `REPOMIND_UPLOAD_DIR`, `REPOMIND_UPLOADS_DIR`, `UPLOAD_DIR`, or `UPLOADS_DIR`
- `REPOMIND_MODEL_PATH` or `MODEL_PATH`

Relative environment paths are resolved against the project root, not the shell's current working directory.

### Runtime Call Sites

Updated path consumers to use the new settings fields:

- Chroma uses `settings.chroma_dir`
- Index manifests use `settings.index_dir`
- Reports use `settings.reports_dir`
- Uploads use `settings.upload_dir`

Compatibility properties remain for older internal references:

- `settings.report_dir`
- `settings.chroma_path`
- `settings.indexes_dir`
- `settings.uploads_dir`

### Local Repository Import

`ingest_local_path()` now resolves relative local paths against the project root. The frontend can safely default to:

```text
sample_repos/python_fastapi_example
```

### Tests

Tests now isolate runtime writes under a temporary directory created by `tempfile`.

`tests/conftest.py` sets:

- `REPOMIND_DATA_DIR`
- `REPOMIND_REPORTS_DIR`
- `REPOMIND_INDEX_DIR`
- `REPOMIND_CHROMA_DIR`
- `REPOMIND_UPLOAD_DIR`
- `REPOMIND_MODEL_PATH`
- `REPOMIND_ENABLE_MODEL_INFERENCE=false`

The temp runtime is removed at the end of the pytest session.

Tests no longer depend on workstation sample repositories or model folders:

- API tests create sample repositories with `tmp_path`.
- Integration tests create sample repositories with `tmp_path`.
- Unit model detection uses a temp qwen-judge path.
- The full model pipeline is gated behind `REPOMIND_RUN_MODEL_TESTS=1`.

### GitHub Actions

CI now runs the full lightweight suite:

```bash
PYTHONPATH=backend .venv/bin/pytest -q
```

The workflow still installs only:

```bash
uv pip install -e ".[analysis,dev]"
```

No local models or GPU runtimes are required for CI.

### Documentation And Generated Artifacts

Examples, docs, docker compose, frontend defaults, and generated validation artifacts no longer contain workstation-specific user-home paths.

## 4. Verification

Local repository verification:

```text
pytest: 10 passed, 1 skipped
ruff: All checks passed
user-home path scan: no matches
```

Clean-checkout simulation:

```text
fresh virtual environment: created
install command: uv pip install -e ".[analysis,dev]"
resolved packages: 128
pytest: 10 passed, 1 skipped
ruff: All checks passed
settings paths: under the temporary checkout
user-home path scan: no matches
```

The clean-checkout run also set `HOME` and `UV_CACHE_DIR` inside the temporary test tree so dependency cache writes did not hide application filesystem behavior.

## 5. Result

RepoMindAI now runs from an arbitrary checkout path on Linux, macOS, Windows, and GitHub Actions without code changes.

Application runtime directories are configurable and portable:

- metadata under `DATA_DIR`
- reports under `REPORTS_DIR`
- index manifests under `INDEX_DIR`
- Chroma storage under `CHROMA_DIR`
- uploads under `UPLOAD_DIR`

No user-specific absolute paths remain in the repository.

