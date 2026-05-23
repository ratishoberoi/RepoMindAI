# Project Highlights

## One-Line Pitch

RepoMind AI is an offline AI-powered repository intelligence platform that turns any repository into architecture maps, security findings, CTO/recruiter reports, and cited repository chat using local qwen-judge inference.

## What Makes It Stand Out

- Local-only generation with `/home/ratish/Forge/models/qwen-judge`.
- Real semantic retrieval with BGE embeddings and ChromaDB.
- Four-level architecture visualization: executive, service, module, implementation.
- Layered dependency explorer designed to avoid file graph hairballs.
- Repository answer engine with direct answers, architecture impact, diagrams, risks, improvements, and citations.
- Real-world benchmark validation against FastAPI, Flask, Next.js, and RepoMindAI itself.
- Repository cleanup lifecycle that persists metadata, vector indexes, and reports while deleting cloned source contents.

## AI Stack

- Local model: qwen-judge
- Embeddings: `BAAI/bge-small-en-v1.5`
- Vector store: ChromaDB
- Retrieval: vector search + lexical reranking + path-aware boosts + citations
- Reports: generated locally from repository evidence

## Engineering Stack

- Backend: FastAPI
- Frontend: Next.js + React Flow
- Graph layout: ELK.js with Dagre fallback
- Parsing: Python AST plus Tree-sitter for JS/TS/JSX/TSX
- Security: Bandit, Semgrep, custom rules
- Diagrams: Mermaid and React Flow

## Benchmark Results

| Repository | Files | Chunks | Analysis | Indexing | Retrieval |
|---|---:|---:|---:|---:|---|
| FastAPI | 2,748 | 10,862 | 214.669s | 34.913s | strong |
| Flask | 231 | 857 | 71.975s | 1.940s | strong/partial |
| Next.js | 25,024 | 50,996 | 200.799s | 92.848s | strong |
| RepoMindAI | 66 | 220 | 84.715s | 9.770s | partial |

## Hard Problems Solved

- Preventing architecture diagrams from turning into unreadable file graphs.
- Making repository chat say “not implemented” when evidence is missing.
- Keeping generated answers grounded in citations.
- Running local model inference without cloud API fallback.
- Preserving analysis artifacts while deleting cloned repository contents.
- Producing a UI that makes architecture understandable in seconds.

## Honest Gaps

- Large repository report generation is slow.
- Public installation still assumes a local Forge model path.
- Dependency audit has remaining Next.js/PostCSS advisories.
- Browser regression tests need to be formalized.
- Self-retrieval for RepoMindAI improved but still needs stronger benchmark tracking.

## Best Demo Flow

1. Open the Architecture tab.
2. Show Executive Architecture.
3. Switch to Service Architecture.
4. Open Dependencies.
5. Ask: “How does authentication work?”
6. Show the direct answer: “Authentication is not implemented.”
7. Open the generated CTO or recruiter report.
