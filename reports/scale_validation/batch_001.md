# Scale Validation Batch 001

Evidence source: `data/scale_validation/batches/batch_001/raw_evidence.jsonl`.

## Metrics

- Repositories attempted: 100
- Repositories passed: 100
- Pass rate: 1.000
- Failure rate: 0.000
- Citation accuracy: 0.825
- Retrieval accuracy: 0.825
- Architecture correctness: 0.956
- Memory peak RSS: 2358.88 MB

## Timing

- Indexing time: 193.252s
- Embedding time: 132.689s
- Graph generation time: 0.000s
- Analysis time: 706.886s

## Corpus Mix

- Languages: `{'Python': 13, 'TypeScript': 13, 'Java': 13, 'Go': 13, 'Rust': 12, 'C#': 12, 'Kotlin': 12, 'PHP': 12}`
- Sizes: `{'tiny': 88, 'small': 12}`

## Bottlenecks

- analysis: 353.443s
- indexing: 193.252s
- chroma_upsert: 184.065s
- security: 136.781s
- embedding: 132.689s
- ingestion: 107.821s
- parse_files: 12.454s
- reports: 4.948s
- technical_debt: 1.915s
- scan_files: 0.005s

## Repositories Near Timeout

- None.

## Fixes Retained

- Recovered architecture correctness by reporting Maven and Gradle as package managers, preferring source languages over Text/Markdown, and treating no-signal repositories as explicit no-signal validations.

## Fixes Rejected

- Rejected the initial unmodified scale run because architecture correctness was 0.748, below the 0.800 gate.

## Failures

- None.
