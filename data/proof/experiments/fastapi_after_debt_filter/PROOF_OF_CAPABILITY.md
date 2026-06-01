# PROOF_OF_CAPABILITY

Evidence source: `data/proof/raw_evidence.jsonl`.

## 1. What RepoMindAI Can Actually Do

- Ingested/analyzed successfully: 1 of 1 attempted repositories.
- Graph generation success rate on passed repositories: 1.000.
- Report generation success rate on passed repositories: 1.000.
- Security scan success rate on passed repositories: 1.000.
- Chat retrieval success rate: 1.000.

## 2. What It Cannot Do

- This run does not prove semantic correctness beyond automatic static checks.
- Ownership, bus factor, and PR reviewer intelligence remain heuristic unless repository metadata supplies real ownership.
- This run does not prove public SaaS readiness, multi-tenant isolation below the API layer, or horizontal scaling.

## 3. Repository Sizes Supported

- Size mix: `{'medium': 1}`.
- Language mix: `{'Python': 1}`.

## 4. Measured Accuracy

- Mean automatic architecture/dependency/security correctness: 0.048.
- Mean citation accuracy: 0.000.
- Mean retrieval accuracy: 0.000.
- Mean answer support confidence: 0.463.

## 5. Measured Scalability

Top aggregate bottlenecks:
- analysis: 67.415s total
- indexing: 36.528s total
- chroma_upsert: 35.162s total
- security: 27.097s total
- embedding: 21.315s total
- ingestion: 5.624s total
- technical_debt: 1.341s total
- parse_files: 1.2s total

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

- Ready for public beta: NO.
- Decision is based only on this evidence run.
