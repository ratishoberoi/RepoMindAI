# Batch 002 Progress

Evidence source: `data/proof/batches/batch_002/raw_evidence.jsonl`

## Metrics

- Repositories attempted: 100
- Repositories passed: 100
- Failure rate: 0.000
- Citation accuracy: 0.775
- Retrieval accuracy: 0.775
- Architecture correctness: 0.586

## Failures

No repository failures.

## Bottlenecks

- Analysis: 1550.692s total
- Indexing: 717.476s total
- Chroma upsert: 667.225s total
- Security: 448.682s total
- Embedding: 308.606s total

## Improvements

Retained:

- Security scanner path filtering and process-group timeout handling.
- Java, Go, and Rust parser/chunker coverage.
- Retrieval query expansion and source-file reranking.
- Technical debt filtering for low-value docs/tutorial/test source when production source exists.
- High-confidence validation expected files and absent-capability scoring.

Rejected / revised:

- Broad security-signal validation remained too noisy. It treated ordinary `token`, `secret`, or security terminology in Java/Rust libraries as scanner-expected vulnerabilities. This kept architecture correctness below target at 0.586.

## Decision

Do not use this as final evidence because architecture correctness remained below the 0.600 target.
