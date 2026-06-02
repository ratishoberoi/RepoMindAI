# Scale Validation Batch 002

Evidence source: `data/scale_validation/batches/batch_002/raw_evidence.jsonl`.

## Metrics

- Repositories attempted: 67
- Repositories passed: 66
- Pass rate: 0.985
- Failure rate: 0.015
- Citation accuracy: 0.784
- Retrieval accuracy: 0.784
- Architecture correctness: 0.959
- Memory peak RSS: 2134.85 MB

## Timing

- Indexing time: 184.536s
- Embedding time: 145.355s
- Graph generation time: 0.000s
- Analysis time: 597.316s

## Corpus Mix

- Languages: `{'Rust': 9, 'C#': 9, 'Kotlin': 9, 'PHP': 8, 'Python': 8, 'TypeScript': 8, 'Java': 8, 'Go': 8}`
- Sizes: `{'tiny': 63, 'small': 4}`

## Bottlenecks

- analysis: 298.658s
- indexing: 184.536s
- chroma_upsert: 178.739s
- embedding: 145.355s
- security: 102.218s
- ingestion: 72.337s
- parse_files: 5.372s
- reports: 2.797s
- technical_debt: 1.391s
- scan_files: 0.002s

## Repositories Near Timeout

- None.

## Fixes Retained

- None in this batch.

## Fixes Rejected

- None in this batch.

## Failures

- https://github.com/microsoft/slngen (C#): unknown - `(raised as a result of Query-invoked autoflush; consider using a session.no_autoflush block if this flush is occurring prematurely)
(builtins.TypeError) Object of type date is not JSON serializable
[SQL: UPDATE repositories SET status=?, updated_at=?, summary=?, reports=? WHERE repositories.id = ?]
[parameters: [{'summary': {'repository': {'id': '145276c4c5054371a90f187a3a49fe5e', 'name': 'slngen', 'path': '/home/ratish/RepoMindAI/data/scale_validation/runtime ... (882799 characters truncated) ... ports/generated/145276c4c5054371a90f187a3a49fe5e/analysis-summary.json'}, 'status': 'complete', 'repositories_id': '145276c4c5054371a90f187a3a49fe5e'}]]`
