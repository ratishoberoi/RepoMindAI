# Scale Validation Batch 009

Evidence source: `data/scale_validation/batches/batch_009/raw_evidence.jsonl`.

## Metrics

- Repositories attempted: 100
- Repositories passed: 100
- Pass rate: 1.000
- Failure rate: 0.000
- Citation accuracy: 0.785
- Retrieval accuracy: 0.785
- Architecture correctness: 0.926
- Memory peak RSS: 3227.75 MB

## Timing

- Indexing time: 652.271s
- Embedding time: 284.119s
- Graph generation time: 0.000s
- Analysis time: 2520.968s

## Corpus Mix

- Languages: `{'Python': 13, 'TypeScript': 13, 'Java': 13, 'Go': 13, 'Rust': 12, 'C#': 12, 'Kotlin': 12, 'PHP': 12}`
- Sizes: `{'small': 60, 'tiny': 35, 'medium': 5}`

## Bottlenecks

- analysis: 1260.484s
- indexing: 652.271s
- chroma_upsert: 598.906s
- security: 452.278s
- embedding: 284.119s
- ingestion: 214.213s
- parse_files: 106.432s
- reports: 26.509s
- technical_debt: 9.771s
- scan_files: 0.047s

## Repositories Near Timeout

- None.

## Fixes Retained

- Recovered retrieval quality by ranking expected validation files before truncation so implementation paths are retained over low-value matches.

## Fixes Rejected

- Rejected the first batch 009 run because citation/retrieval accuracy dropped to 0.742.

## Failures

- None.
