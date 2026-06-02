# Scale Validation Batch 002

Evidence source: `data/scale_validation/batches/batch_002/raw_evidence.jsonl`.

## Metrics

- Repositories attempted: 100
- Repositories passed: 100
- Pass rate: 1.000
- Failure rate: 0.000
- Citation accuracy: 0.798
- Retrieval accuracy: 0.798
- Architecture correctness: 0.972
- Memory peak RSS: 2282.32 MB

## Timing

- Indexing time: 224.799s
- Embedding time: 165.746s
- Graph generation time: 0.000s
- Analysis time: 994.292s

## Corpus Mix

- Languages: `{'Rust': 13, 'C#': 13, 'Kotlin': 13, 'PHP': 13, 'Python': 12, 'TypeScript': 12, 'Java': 12, 'Go': 12}`
- Sizes: `{'tiny': 93, 'small': 7}`

## Bottlenecks

- analysis: 497.146s
- security: 253.860s
- indexing: 224.799s
- chroma_upsert: 216.069s
- embedding: 165.746s
- ingestion: 107.577s
- parse_files: 8.991s
- reports: 4.228s
- technical_debt: 1.707s
- scan_files: 0.002s

## Repositories Near Timeout

- None.

## Fixes Retained

- Eliminated date serialization failures by making report generation and repository storage JSON-safe.

## Fixes Rejected

- Rejected report-only JSON serialization because repository storage still failed on date-valued summaries.

## Failures

- None.
