# Scale Validation Batch 005

Evidence source: `data/scale_validation/batches/batch_005/raw_evidence.jsonl`.

## Metrics

- Repositories attempted: 100
- Repositories passed: 100
- Pass rate: 1.000
- Failure rate: 0.000
- Citation accuracy: 0.857
- Retrieval accuracy: 0.857
- Architecture correctness: 0.981
- Memory peak RSS: 2262.33 MB

## Timing

- Indexing time: 128.481s
- Embedding time: 54.603s
- Graph generation time: 0.000s
- Analysis time: 521.984s

## Corpus Mix

- Languages: `{'Python': 13, 'TypeScript': 13, 'Java': 13, 'Go': 13, 'Rust': 12, 'C#': 12, 'Kotlin': 12, 'PHP': 12}`
- Sizes: `{'tiny': 89, 'small': 11}`

## Bottlenecks

- analysis: 260.992s
- ingestion: 144.846s
- indexing: 128.481s
- security: 106.747s
- chroma_upsert: 98.310s
- embedding: 54.603s
- parse_files: 17.519s
- reports: 3.875s
- technical_debt: 0.611s
- scan_files: 0.062s

## Repositories Near Timeout

- None.

## Fixes Retained

- Eliminated JSON metadata parser failures by accepting list-valued dependencies and scripts.

## Fixes Rejected

- Rejected the first batch 005 run because JSON metadata parsing produced a nonzero failure rate.

## Failures

- None.
