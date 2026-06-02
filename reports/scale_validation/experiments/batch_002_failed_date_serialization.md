# Scale Validation Batch 002

Evidence source: `data/scale_validation/batches/batch_002/raw_evidence.jsonl`.

## Metrics

- Repositories attempted: 24
- Repositories passed: 23
- Pass rate: 0.958
- Failure rate: 0.042
- Citation accuracy: 0.825
- Retrieval accuracy: 0.825
- Architecture correctness: 0.972
- Memory peak RSS: 1913.86 MB

## Timing

- Indexing time: 113.497s
- Embedding time: 101.619s
- Graph generation time: 0.000s
- Analysis time: 281.504s

## Corpus Mix

- Languages: `{'Rust': 3, 'C#': 3, 'Kotlin': 3, 'PHP': 3, 'Python': 3, 'TypeScript': 3, 'Java': 3, 'Go': 3}`
- Sizes: `{'tiny': 22, 'small': 2}`

## Bottlenecks

- analysis: 140.752s
- indexing: 113.497s
- chroma_upsert: 111.461s
- embedding: 101.619s
- ingestion: 25.970s
- security: 22.985s
- parse_files: 2.185s
- reports: 0.954s
- technical_debt: 0.317s

## Repositories Near Timeout

- None.

## Fixes Retained

- None in this batch.

## Fixes Rejected

- None in this batch.

## Failures

- https://github.com/microsoft/slngen (C#): analysis - `Object of type date is not JSON serializable`
