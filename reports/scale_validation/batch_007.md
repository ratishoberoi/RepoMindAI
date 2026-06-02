# Scale Validation Batch 007

Evidence source: `data/scale_validation/batches/batch_007/raw_evidence.jsonl`.

## Metrics

- Repositories attempted: 100
- Repositories passed: 100
- Pass rate: 1.000
- Failure rate: 0.000
- Citation accuracy: 0.901
- Retrieval accuracy: 0.901
- Architecture correctness: 0.948
- Memory peak RSS: 2296.12 MB

## Timing

- Indexing time: 107.000s
- Embedding time: 55.315s
- Graph generation time: 0.000s
- Analysis time: 575.310s

## Corpus Mix

- Languages: `{'Python': 13, 'TypeScript': 13, 'Java': 13, 'Go': 13, 'Rust': 12, 'C#': 12, 'Kotlin': 12, 'PHP': 12}`
- Sizes: `{'tiny': 89, 'small': 11}`

## Bottlenecks

- analysis: 287.655s
- security: 157.920s
- ingestion: 111.858s
- indexing: 107.000s
- chroma_upsert: 99.063s
- embedding: 55.315s
- parse_files: 11.531s
- reports: 4.023s
- technical_debt: 3.106s
- scan_files: 0.195s

## Repositories Near Timeout

- None.

## Fixes Retained

- Recovered retrieval quality by preventing auth substring false positives and boosting C#/Kotlin/PHP source files for implementation queries.

## Fixes Rejected

- Rejected the first batch 007 run because citation/retrieval accuracy dropped to 0.661.

## Failures

- None.
