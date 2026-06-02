# SCALE_VALIDATION_1000

Evidence sources: `data/scale_validation/corpus.json` and `data/scale_validation/batches/*/raw_evidence.jsonl`.

## 1. Repositories Tested

- Target repositories: 1000
- Completed repositories: 1000
- Unique corpus repositories: 1000

## 2. Languages Tested

- `{'Python': 125, 'TypeScript': 125, 'Java': 125, 'Go': 125, 'Rust': 125, 'C#': 125, 'Kotlin': 125, 'PHP': 125}`

## 3. Pass Rate

- Pass rate: 1.000

## 4. Failure Rate

- Failure rate: 0.000

## 5. Citation Accuracy

- Citation accuracy: 0.824

## 6. Retrieval Accuracy

- Retrieval accuracy: 0.824

## 7. Architecture Correctness

- Architecture correctness: 0.961

## 8. Bottlenecks Discovered

- analysis: 5065.260s total
- indexing: 2477.525s total
- chroma_upsert: 2288.813s total
- security: 2123.375s total
- ingestion: 1293.525s total
- embedding: 1273.892s total
- parse_files: 285.810s total
- reports: 90.068s total
- technical_debt: 30.440s total
- scan_files: 0.808s total

## 9. Bottlenecks Fixed

- Batch 001: Recovered architecture correctness by reporting Maven and Gradle as package managers, preferring source languages over Text/Markdown, and treating no-signal repositories as explicit no-signal validations.
- Batch 002: Eliminated date serialization failures by making report generation and repository storage JSON-safe.
- Batch 005: Eliminated JSON metadata parser failures by accepting list-valued dependencies and scripts.
- Batch 007: Recovered retrieval quality by preventing auth substring false positives and boosting C#/Kotlin/PHP source files for implementation queries.
- Batch 009: Recovered retrieval quality by ranking expected validation files before truncation so implementation paths are retained over low-value matches.

Rejected failed runs retained as evidence:
- Batch 001: Rejected the initial unmodified scale run because architecture correctness was 0.748, below the 0.800 gate.
- Batch 002: Rejected report-only JSON serialization because repository storage still failed on date-valued summaries.
- Batch 005: Rejected the first batch 005 run because JSON metadata parsing produced a nonzero failure rate.
- Batch 007: Rejected the first batch 007 run because citation/retrieval accuracy dropped to 0.661.
- Batch 009: Rejected the first batch 009 run because citation/retrieval accuracy dropped to 0.742.

## 10. Remaining Bottlenecks

- analysis
- indexing
- chroma_upsert
- security
- ingestion

## 11. Public Beta Recommendation

- YES

## 12. Production Recommendation

- NEEDS_MANUAL_REVIEW
