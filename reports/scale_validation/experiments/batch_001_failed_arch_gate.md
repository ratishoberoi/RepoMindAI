# Scale Validation Batch 001

Evidence source: `data/scale_validation/batches/batch_001/raw_evidence.jsonl`.

## Metrics

- Repositories attempted: 100
- Repositories passed: 100
- Pass rate: 1.000
- Failure rate: 0.000
- Citation accuracy: 0.825
- Retrieval accuracy: 0.825
- Architecture correctness: 0.748
- Memory peak RSS: 2374.02 MB

## Timing

- Indexing time: 210.542s
- Embedding time: 150.353s
- Graph generation time: 0.000s
- Analysis time: 747.380s

## Corpus Mix

- Languages: `{'Python': 13, 'TypeScript': 13, 'Java': 13, 'Go': 13, 'Rust': 12, 'C#': 12, 'Kotlin': 12, 'PHP': 12}`
- Sizes: `{'tiny': 88, 'small': 12}`

## Bottlenecks

- analysis: 373.690s
- indexing: 210.542s
- chroma_upsert: 201.253s
- embedding: 150.353s
- security: 139.724s
- ingestion: 111.030s
- parse_files: 12.371s
- reports: 4.984s
- technical_debt: 1.897s
- scan_files: 0.013s

## Repositories Near Timeout

- None.

## Fixes Retained

- None in this batch.

## Fixes Rejected

- None in this batch.

## Failures

- None.
