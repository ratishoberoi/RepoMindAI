# Scale Validation Batch 006

Evidence source: `data/scale_validation/batches/batch_006/raw_evidence.jsonl`.

## Metrics

- Repositories attempted: 100
- Repositories passed: 100
- Pass rate: 1.000
- Failure rate: 0.000
- Citation accuracy: 0.808
- Retrieval accuracy: 0.808
- Architecture correctness: 0.964
- Memory peak RSS: 2724.03 MB

## Timing

- Indexing time: 113.246s
- Embedding time: 51.308s
- Graph generation time: 0.000s
- Analysis time: 530.752s

## Corpus Mix

- Languages: `{'Rust': 13, 'C#': 13, 'Kotlin': 13, 'PHP': 13, 'Python': 12, 'TypeScript': 12, 'Java': 12, 'Go': 12}`
- Sizes: `{'tiny': 82, 'small': 18}`

## Bottlenecks

- analysis: 265.376s
- security: 126.705s
- indexing: 113.246s
- ingestion: 111.624s
- chroma_upsert: 104.610s
- embedding: 51.308s
- parse_files: 15.432s
- reports: 5.070s
- technical_debt: 0.840s
- scan_files: 0.030s

## Repositories Near Timeout

- None.

## Fixes Retained

- None in this batch.

## Fixes Rejected

- None in this batch.

## Failures

- None.
