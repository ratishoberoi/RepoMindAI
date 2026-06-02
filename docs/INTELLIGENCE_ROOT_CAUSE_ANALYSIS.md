# Intelligence Root Cause Analysis

Evidence sources:

- `data/proof/raw_evidence.jsonl`
- `data/proof/summary.json`
- `data/proof/improvement_loop.json`
- `docs/evidence/FAILURE_REPORT.md`
- `docs/evidence/PROOF_OF_CAPABILITY.md`

## Baseline

- Repositories attempted: 100
- Repositories passed: 98
- Failure rate: 0.020
- Mean citation accuracy: 0.211
- Mean retrieval accuracy: 0.098
- Mean architecture correctness: 0.148

## Failure Pattern

Two repositories failed because analysis exceeded the 180 second validation deadline:

- `https://github.com/python/mypy`
- `https://github.com/fastapi/fastapi`

Aggregate bottleneck evidence from `data/proof/summary.json`:

- Analysis: 2239.526s total
- Security: 1594.730s total
- Indexing: 503.134s total
- Chroma upsert: 477.511s total
- Embedding: 242.331s total

The security scanner was the largest identifiable sub-stage. `data/proof/improvement_loop.json` shows the retained security scanner optimization reduced `pallets/click` analysis from 78.978s to 51.045s while preserving the same finding count.

## Retrieval And Citation Root Causes

The baseline validation generated expected files by searching broad tokens across source text. This created false expectations for repositories that do not implement the requested capability.

Example from `pallets/click`:

- The `routes` expected set included `src/click/parser.py`, `src/click/testing.py`, `src/click/types.py`, and test files because terms such as `parser`, `api`, `server`, and `handler` appeared in source.
- The product found relevant Click documentation and core files, but the validation scored most citations as missing because Click is not a web API service.

Observed expected-file distribution:

- Minimum expected files per question: 0
- Median expected files per question: 18
- 90th percentile expected files per question: 50
- Maximum expected files per question: 50

The retrieval validator requested only six citations. With 18 to 50 expected files, the original recall-style denominator made scores below target even when all six citations were relevant. The measured retrieval metric therefore mixed three things:

- actual retrieval quality
- capability absence handling
- an impossible top-6 recall denominator for large expected sets

## Architecture Correctness Root Causes

Architecture correctness used the same broad route expected set. For libraries and CLI tools, route terms in parser or API documentation were treated as web/API route evidence. This penalized repositories where the correct architecture conclusion is that no application route surface exists.

Language coverage was another real limitation:

- Python had parser support through Python AST and tree-sitter fallback.
- JavaScript and TypeScript had tree-sitter support.
- Java, Go, and Rust were classified as languages but did not have comparable architecture extraction for imports, functions, route signals, or data model signals.

Baseline architecture correctness by language:

- Go: 0.052
- Java: 0.108
- Python: 0.285
- Rust: 0.023
- TypeScript: 0.284

The lowest scores correlate with the languages lacking parser-level architecture extraction.

## Graph Understanding Root Causes

Graph generation succeeded on passed repositories, but usefulness was not proven by the baseline metrics. The dependency graph depends on parsed imports, classes, functions, routes, and models. Because Java, Go, and Rust parsing was shallow, graph nodes existed but represented less architecture semantics for those languages.

## Large Repository Timeout Root Causes

Timeout failures occurred during full analysis, not ingestion. The stage aggregate points to three likely contributors:

- external scanner runtime, especially security scanning
- embedding and Chroma upsert volume
- repository-wide parsing and debt analysis on medium/large repositories

The retained security optimization is the first measured timeout mitigation. Additional timeout proof requires rerunning the failed repositories after the scanner change.

## Retained Fix Direction

The next validation pass must measure both product improvements and corrected validation semantics:

- high-confidence expected files instead of broad token matches
- explicit scoring for capability absence when a repository does not implement auth, database, or routes
- parser/chunker coverage for Java, Go, and Rust
- retrieval reranking that favors implementation files over docs/tests for implementation questions
- targeted reruns of `python/mypy` and `fastapi/fastapi` to verify timeout behavior
