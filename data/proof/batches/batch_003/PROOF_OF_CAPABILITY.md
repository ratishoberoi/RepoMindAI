# PROOF_OF_CAPABILITY

Evidence source: `data/proof/raw_evidence.jsonl`.

## 1. What RepoMindAI Can Actually Do

- Ingested/analyzed successfully: 100 of 100 attempted repositories.
- Graph generation success rate on passed repositories: 1.000.
- Report generation success rate on passed repositories: 1.000.
- Security scan success rate on passed repositories: 1.000.
- Chat retrieval success rate: 1.000.

## 2. What It Cannot Do

- This run does not prove semantic correctness beyond automatic static checks.
- Ownership, bus factor, and PR reviewer intelligence remain heuristic unless repository metadata supplies real ownership.
- This run does not prove public SaaS readiness, multi-tenant isolation below the API layer, or horizontal scaling.

## 3. Repository Sizes Supported

- Size mix: `{'tiny': 53, 'small': 36, 'medium': 10, 'large': 1}`.
- Language mix: `{'Python': 20, 'TypeScript': 20, 'Java': 20, 'Go': 20, 'Rust': 20}`.

## 4. Measured Accuracy

- Mean automatic architecture/dependency/security correctness: 0.848.
- Mean citation accuracy: 0.775.
- Mean retrieval accuracy: 0.775.
- Mean answer support confidence: 0.765.

## 5. Measured Scalability

Top aggregate bottlenecks:
- analysis: 1549.328s total
- indexing: 715.352s total
- chroma_upsert: 664.75s total
- security: 446.903s total
- embedding: 306.903s total
- ingestion: 225.848s total
- parse_files: 214.598s total
- technical_debt: 101.372s total
- reports: 50.694s total

## Improvement Loop Evidence

- Target: `https://github.com/pallets/click`.
- Bottleneck: `security_scan`.
- Before: analysis 78.978s, security 62.075s, findings 4.
- After: analysis 51.045s, security 36.509s, findings 4.
- Delta: analysis -27.933s, security -25.566s, findings 0.

## 6. Measured Failure Rate

- Failure rate: 0.000.
- Failures: 0.

## 7. Public Beta Readiness

- Ready for public beta: MAYBE.
- Decision is based only on this evidence run.
