# Scale Validation Batch 009

Evidence source: `data/scale_validation/batches/batch_009/raw_evidence.jsonl`.

## Metrics

- Repositories attempted: 32
- Repositories passed: 32
- Pass rate: 1.000
- Failure rate: 0.000
- Citation accuracy: 0.742
- Retrieval accuracy: 0.742
- Architecture correctness: 0.894
- Memory peak RSS: 3332.51 MB

## Timing

- Indexing time: 187.699s
- Embedding time: 81.293s
- Graph generation time: 0.000s
- Analysis time: 744.202s

## Corpus Mix

- Languages: `{'Python': 4, 'TypeScript': 4, 'Java': 4, 'Go': 4, 'Rust': 4, 'C#': 4, 'Kotlin': 4, 'PHP': 4}`
- Sizes: `{'small': 19, 'tiny': 11, 'medium': 2}`

## Bottlenecks

- analysis: 372.101s
- indexing: 187.699s
- chroma_upsert: 171.428s
- security: 104.250s
- ingestion: 94.589s
- embedding: 81.293s
- parse_files: 64.101s
- reports: 11.248s
- technical_debt: 0.758s

## Repositories Near Timeout

- None.

## Fixes Retained

- None in this batch.

## Fixes Rejected

- None in this batch.

## Failures

- None.
