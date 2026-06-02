# Scale Validation Batch 008

Evidence source: `data/scale_validation/batches/batch_008/raw_evidence.jsonl`.

## Metrics

- Repositories attempted: 100
- Repositories passed: 100
- Pass rate: 1.000
- Failure rate: 0.000
- Citation accuracy: 0.883
- Retrieval accuracy: 0.883
- Architecture correctness: 0.969
- Memory peak RSS: 2702.35 MB

## Timing

- Indexing time: 115.632s
- Embedding time: 53.213s
- Graph generation time: 0.000s
- Analysis time: 642.154s

## Corpus Mix

- Languages: `{'Rust': 13, 'C#': 13, 'Kotlin': 13, 'PHP': 13, 'Python': 12, 'TypeScript': 12, 'Java': 12, 'Go': 12}`
- Sizes: `{'tiny': 87, 'small': 13}`

## Bottlenecks

- analysis: 321.077s
- security: 182.668s
- indexing: 115.632s
- ingestion: 115.230s
- chroma_upsert: 107.168s
- embedding: 53.213s
- parse_files: 12.894s
- reports: 4.513s
- technical_debt: 1.217s
- scan_files: 0.015s

## Repositories Near Timeout

- None.

## Fixes Retained

- None in this batch.

## Fixes Rejected

- None in this batch.

## Failures

- None.
