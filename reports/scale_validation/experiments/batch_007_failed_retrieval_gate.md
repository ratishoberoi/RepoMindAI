# Scale Validation Batch 007

Evidence source: `data/scale_validation/batches/batch_007/raw_evidence.jsonl`.

## Metrics

- Repositories attempted: 13
- Repositories passed: 13
- Pass rate: 1.000
- Failure rate: 0.000
- Citation accuracy: 0.668
- Retrieval accuracy: 0.668
- Architecture correctness: 0.910
- Memory peak RSS: 2751.33 MB

## Timing

- Indexing time: 13.303s
- Embedding time: 6.201s
- Graph generation time: 0.000s
- Analysis time: 128.508s

## Corpus Mix

- Languages: `{'Python': 2, 'TypeScript': 2, 'Java': 2, 'Go': 2, 'Rust': 2, 'C#': 1, 'Kotlin': 1, 'PHP': 1}`
- Sizes: `{'tiny': 11, 'small': 2}`

## Bottlenecks

- analysis: 64.254s
- security: 46.759s
- ingestion: 15.109s
- indexing: 13.303s
- chroma_upsert: 12.215s
- embedding: 6.201s
- technical_debt: 1.840s
- parse_files: 1.275s
- reports: 0.557s

## Repositories Near Timeout

- None.

## Fixes Retained

- None in this batch.

## Fixes Rejected

- None in this batch.

## Failures

- None.
