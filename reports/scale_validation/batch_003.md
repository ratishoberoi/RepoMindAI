# Scale Validation Batch 003

Evidence source: `data/scale_validation/batches/batch_003/raw_evidence.jsonl`.

## Metrics

- Repositories attempted: 100
- Repositories passed: 100
- Pass rate: 1.000
- Failure rate: 0.000
- Citation accuracy: 0.802
- Retrieval accuracy: 0.802
- Architecture correctness: 0.959
- Memory peak RSS: 2338.30 MB

## Timing

- Indexing time: 238.468s
- Embedding time: 173.276s
- Graph generation time: 0.000s
- Analysis time: 906.264s

## Corpus Mix

- Languages: `{'Python': 13, 'TypeScript': 13, 'Java': 13, 'Go': 13, 'Rust': 12, 'C#': 12, 'Kotlin': 12, 'PHP': 12}`
- Sizes: `{'tiny': 86, 'small': 14}`

## Bottlenecks

- analysis: 453.132s
- indexing: 238.468s
- chroma_upsert: 228.118s
- security: 192.796s
- embedding: 173.276s
- ingestion: 113.683s
- parse_files: 11.236s
- reports: 4.866s
- technical_debt: 1.693s
- scan_files: 0.158s

## Repositories Near Timeout

- https://github.com/KaQus/claude-code-pentest (Python): 148.696s of 180s

## Fixes Retained

- None in this batch.

## Fixes Rejected

- None in this batch.

## Failures

- None.
