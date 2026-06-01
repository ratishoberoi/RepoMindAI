# PROOF_OF_CAPABILITY

Evidence source: `data/proof/raw_evidence.jsonl`.

## 1. What RepoMindAI Can Actually Do

- Ingested/analyzed successfully: 19 of 20 attempted repositories.
- Graph generation success rate on passed repositories: 1.000.
- Report generation success rate on passed repositories: 1.000.
- Security scan success rate on passed repositories: 1.000.
- Chat retrieval success rate: 1.000.

## 2. What It Cannot Do

- This run does not prove semantic correctness beyond automatic static checks.
- Ownership, bus factor, and PR reviewer intelligence remain heuristic unless repository metadata supplies real ownership.
- This run does not prove public SaaS readiness, multi-tenant isolation below the API layer, or horizontal scaling.

## 3. Repository Sizes Supported

- Size mix: `{'tiny': 12, 'small': 7, 'medium': 1}`.
- Language mix: `{'Python': 20}`.

## 4. Measured Accuracy

- Mean automatic architecture/dependency/security correctness: 0.526.
- Mean citation accuracy: 0.510.
- Mean retrieval accuracy: 0.510.
- Mean answer support confidence: 0.761.

## 5. Measured Scalability

Top aggregate bottlenecks:
- analysis: 407.817s total
- security: 207.079s total
- technical_debt: 103.729s total
- indexing: 83.243s total
- chroma_upsert: 78.749s total
- embedding: 43.758s total
- ingestion: 31.346s total
- parse_files: 8.296s total
- reports: 0.009s total

## Improvement Loop Evidence

- Target: `https://github.com/pallets/click`.
- Bottleneck: `security_scan`.
- Before: analysis 78.978s, security 62.075s, findings 4.
- After: analysis 51.045s, security 36.509s, findings 4.
- Delta: analysis -27.933s, security -25.566s, findings 0.

## 6. Measured Failure Rate

- Failure rate: 0.050.
- Failures: 1.

## 7. Public Beta Readiness

- Ready for public beta: NO.
- Decision is based only on this evidence run.
