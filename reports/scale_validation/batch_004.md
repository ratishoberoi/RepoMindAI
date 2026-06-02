# Scale Validation Batch 004

Evidence source: `data/scale_validation/batches/batch_004/raw_evidence.jsonl`.

## Metrics

- Repositories attempted: 100
- Repositories passed: 100
- Pass rate: 1.000
- Failure rate: 0.000
- Citation accuracy: 0.794
- Retrieval accuracy: 0.794
- Architecture correctness: 0.969
- Memory peak RSS: 2280.95 MB

## Timing

- Indexing time: 107.544s
- Embedding time: 53.942s
- Graph generation time: 0.000s
- Analysis time: 504.726s

## Corpus Mix

- Languages: `{'Rust': 13, 'C#': 13, 'Kotlin': 13, 'PHP': 13, 'Python': 12, 'TypeScript': 12, 'Java': 12, 'Go': 12}`
- Sizes: `{'tiny': 82, 'small': 18}`

## Bottlenecks

- analysis: 252.363s
- security: 125.126s
- ingestion: 113.307s
- indexing: 107.544s
- chroma_upsert: 99.798s
- embedding: 53.942s
- parse_files: 9.838s
- reports: 5.157s
- technical_debt: 0.729s
- scan_files: 0.004s

## Repositories Near Timeout

- None.

## Fixes Retained

- None in this batch.

## Fixes Rejected

- None in this batch.

## Failures

- None.
