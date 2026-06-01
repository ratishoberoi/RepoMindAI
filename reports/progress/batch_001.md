# Batch 001 Progress

Evidence source: `data/proof/raw_evidence.jsonl`

## Metrics

- Repositories attempted: 100
- Repositories passed: 98
- Failure rate: 0.020
- Citation accuracy: 0.211
- Retrieval accuracy: 0.098
- Architecture correctness: 0.148

## Failures

- `https://github.com/python/mypy`: analysis timeout at 180.197s
- `https://github.com/fastapi/fastapi`: analysis timeout at 180.058s

## Bottlenecks

- Analysis: 2239.526s total
- Security: 1594.730s total
- Indexing: 503.134s total
- Chroma upsert: 477.511s total
- Embedding: 242.331s total

## Bottleneck Explanation

- Retrieval validation used broad token matches and penalized repositories that did not implement auth, database, or API routes.
- Java, Go, and Rust lacked parser-level architecture extraction.
- Bandit and Semgrep were invoked over too many low-value files.
- Technical debt analysis spent time on tutorial/docs/test source in large repositories.

## Improvements

No retained code changes were attached to this baseline batch. This batch is the starting point.
