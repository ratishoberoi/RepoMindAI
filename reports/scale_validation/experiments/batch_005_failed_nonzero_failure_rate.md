# Scale Validation Batch 005

Evidence source: `data/scale_validation/batches/batch_005/raw_evidence.jsonl`.

## Metrics

- Repositories attempted: 100
- Repositories passed: 99
- Pass rate: 0.990
- Failure rate: 0.010
- Citation accuracy: 0.857
- Retrieval accuracy: 0.857
- Architecture correctness: 0.981
- Memory peak RSS: 2676.31 MB

## Timing

- Indexing time: 119.716s
- Embedding time: 45.590s
- Graph generation time: 0.000s
- Analysis time: 510.014s

## Corpus Mix

- Languages: `{'Python': 13, 'TypeScript': 13, 'Java': 13, 'Go': 13, 'Rust': 12, 'C#': 12, 'Kotlin': 12, 'PHP': 12}`
- Sizes: `{'tiny': 89, 'small': 11}`

## Bottlenecks

- analysis: 255.007s
- ingestion: 152.123s
- indexing: 119.716s
- security: 108.991s
- chroma_upsert: 89.805s
- embedding: 45.590s
- parse_files: 18.141s
- reports: 3.963s
- technical_debt: 0.621s
- scan_files: 0.059s

## Repositories Near Timeout

- None.

## Fixes Retained

- None in this batch.

## Fixes Rejected

- None in this batch.

## Failures

- https://github.com/yunsmall/Android-Usbipdcpp (Kotlin): analysis - `'list' object has no attribute 'keys'`
