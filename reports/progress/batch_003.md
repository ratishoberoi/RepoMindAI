# Batch 003 Progress

Evidence source: `data/proof/batches/batch_003/raw_evidence.jsonl`

## Metrics

- Repositories attempted: 100
- Repositories passed: 100
- Failure rate: 0.000
- Citation accuracy: 0.775
- Retrieval accuracy: 0.775
- Architecture correctness: 0.848

## Per-Language Metrics

- Go: 20 repos, citation 0.850, retrieval 0.850, architecture 0.893, max runtime 16.11s
- Java: 20 repos, citation 0.662, retrieval 0.662, architecture 0.658, max runtime 175.21s
- Python: 20 repos, citation 0.757, retrieval 0.757, architecture 0.850, max runtime 125.97s
- Rust: 20 repos, citation 0.859, retrieval 0.859, architecture 0.953, max runtime 33.06s
- TypeScript: 20 repos, citation 0.749, retrieval 0.749, architecture 0.888, max runtime 53.47s

## Failures

No repository failures.

## Bottlenecks

- Analysis: 1549.328s total
- Indexing: 715.352s total
- Chroma upsert: 664.750s total
- Security: 446.903s total
- Embedding: 306.903s total

## Improvements Retained

- Security scanner path filtering and process-group timeout handling.
- Java, Go, and Rust parser/chunker coverage.
- Architecture route/data file heuristics for framework source files.
- Retrieval query expansion, implementation-file reranking, and pinned-path ranking.
- Technical debt filtering for low-value docs/tutorial/test source when production source exists.
- High-confidence validation expected files, absent-capability scoring, and stricter hardcoded-secret validation.

## Remaining Bottlenecks

- `assertj/assertj` completed in 175.209s, close to the 180s timeout. Its top bottleneck was Java parse time at 132.299s.
- Chroma upsert remains the largest aggregate indexing cost.
- The validation corpus is still 100 repositories, not the requested 1000-repository total.
