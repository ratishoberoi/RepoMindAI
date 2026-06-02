# Path Audit

Date: 2026-05-23

## Scope

Audited the repository for machine-specific filesystem paths, user-home paths, repository-root literals, and runtime settings that create directories during import.

Searches performed against Linux user-home paths, macOS user-home paths, Windows user-profile paths, repository-root literals, and settings path names.

Literal user-home search patterns and values are redacted in this report so the audit file does not reintroduce the portability failure.

## Runtime Hardcoded Paths Found

These were the CI-breaking paths because `get_settings()` calls `ensure_dirs()` during application import.

| File | Path category found | Impact |
| --- | --- | --- |
| `backend/repomind/core/config.py` | `${USER_HOME}/RepoMindAI/data` | Tried to create data directories outside the checkout on GitHub Actions. |
| `backend/repomind/core/config.py` | `${USER_HOME}/RepoMindAI/reports` | Tried to create report directories outside the checkout on GitHub Actions. |
| `backend/repomind/core/config.py` | `${USER_HOME}/RepoMindAI/data/chroma` | Tried to create Chroma directories outside the checkout on GitHub Actions. |
| `backend/repomind/core/config.py` | `${USER_HOME}/Forge/models/qwen-judge` | Made the model path machine-specific. |
| `backend/repomind/core/config.py` | validator requiring the exact local model absolute path | Prevented cloned repositories from configuring qwen-judge elsewhere. |

## Test Hardcoded Paths Found

| File | Path category found | Impact |
| --- | --- | --- |
| `tests/conftest.py` | repository-root `data` and `reports` defaults | Tests wrote into the checkout instead of isolated temp directories. |
| `tests/api/test_api.py` | `${USER_HOME}/RepoMindAI/sample_repos/python_fastapi_example` | API test only worked on one machine. |
| `tests/integration/test_analysis_pipeline.py` | `${USER_HOME}/RepoMindAI/sample_repos/python_fastapi_example` | Integration test only worked on one machine. |
| `tests/unit/test_utils_and_parsing.py` | `${USER_HOME}/Forge/models/qwen-judge` | Unit test referenced a workstation-only model path. |

## Example And Documentation Paths Found

| File | Path category found |
| --- | --- |
| `.env.example` | `${USER_HOME}/RepoMindAI/data`, `${USER_HOME}/RepoMindAI/reports`, `${USER_HOME}/RepoMindAI/data/chroma`, `${USER_HOME}/Forge/models/qwen-judge` |
| `docker-compose.yml` | `${USER_HOME}/Forge/models` bind mount |
| `frontend/components/RepoMindDashboard.tsx` | `${USER_HOME}/RepoMindAI/sample_repos/python_fastapi_example` UI default |
| `README.md` | workstation checkout and model paths |
| `docs/SETUP.md` | workstation checkout paths |
| `docs/USAGE.md` | workstation sample repository path |
| `docs/MODEL_USAGE.md` | workstation model path |
| `INSTALL_PLAN.md` | workstation checkout, dependency, data, report, and model paths |
| `MODEL_VALIDATION.md` | workstation model paths |
| `MODEL_BENCHMARK.md` | workstation model paths |
| `REALITY_CHECK.md` | workstation model path |
| `FINAL_VERIFICATION_REPORT.md` | workstation model path |
| `PRODUCT_REVIEW.md` | workstation model path |
| `PROJECT_HIGHLIGHTS.md` | workstation model path |
| `GITHUB_RELEASE_CHECKLIST.md` | workstation model path |
| `LOCAL_MACHINE_AUDIT.md` | workstation uv and model cache paths |
| `BENCHMARK_RESULTS.md` | workstation self-analysis source path |

## Generated Validation Artifact Paths Found

The generated validation JSON files contained persisted absolute workspace and report paths from prior local runs:

- `data/validation/e2e_fastapi.json`
- `data/validation/e2e_flask.json`
- `data/validation/e2e_nextjs.json`
- `data/validation/e2e_results.json`
- `data/validation/real_world_benchmarks.json`
- `data/validation/self_stress.json`

These were not executed by CI, but they still made the repository non-portable under a plain path scan.

## Current Result

No literal Linux, macOS, or Windows user-home absolute paths remain. The verification commands are listed in `PATH_FIX_REPORT.md` with the sensitive user-home token redacted.
