# Scale Validation Batch 010

Evidence source: `data/scale_validation/batches/batch_010/raw_evidence.jsonl`.

## Metrics

- Repositories attempted: 100
- Repositories passed: 100
- Pass rate: 1.000
- Failure rate: 0.000
- Citation accuracy: 0.785
- Retrieval accuracy: 0.785
- Architecture correctness: 0.966
- Memory peak RSS: 4446.36 MB

## Timing

- Indexing time: 596.832s
- Embedding time: 249.681s
- Graph generation time: 0.000s
- Analysis time: 2227.184s

## Corpus Mix

- Languages: `{'Rust': 13, 'C#': 13, 'Kotlin': 13, 'PHP': 13, 'Python': 12, 'TypeScript': 12, 'Java': 12, 'Go': 12}`
- Sizes: `{'small': 57, 'tiny': 40, 'medium': 3}`

## Bottlenecks

- analysis: 1113.592s
- indexing: 596.832s
- chroma_upsert: 552.706s
- security: 388.494s
- embedding: 249.681s
- ingestion: 153.366s
- parse_files: 79.483s
- reports: 26.879s
- technical_debt: 8.851s
- scan_files: 0.290s

## Repositories Near Timeout

- None.

## Fixes Retained

- None in this batch.

## Fixes Rejected

- None in this batch.

## Failures

- None.
