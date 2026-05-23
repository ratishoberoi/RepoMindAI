# LinkedIn Post

I built RepoMind AI: an offline AI-powered repository intelligence platform.

It takes a GitHub URL, ZIP, or local repository and turns it into:

- executive architecture maps
- service and module diagrams
- layered dependency graphs
- security findings
- CTO and recruiter reviews
- technical debt reports
- cited repository chat

The constraint: no cloud LLM APIs.

Everything runs locally through:

- qwen-judge for generation
- BGE-small embeddings
- ChromaDB vector search
- AST and Tree-sitter parsing
- Bandit, Semgrep, and custom security rules
- Next.js + React Flow for the UI

The hardest part was not “calling an LLM.”

The hard part was making the system behave like a real engineering tool:

- say “Authentication is not implemented” when there is no evidence
- avoid fake fallback answers
- cite files for every repository answer
- delete cloned repositories after analysis
- keep reports and vector indexes persisted
- make architecture diagrams useful instead of file-level hairballs

I benchmarked it on real repositories:

| Repo | Files | Chunks | Analysis | Indexing |
|---|---:|---:|---:|---:|
| FastAPI | 2,748 | 10,862 | 214.669s | 34.913s |
| Flask | 231 | 857 | 71.975s | 1.940s |
| Next.js | 25,024 | 50,996 | 200.799s | 92.848s |
| RepoMindAI | 66 | 220 | 84.715s | 9.770s |

The architecture page became the hero feature:

- Executive view: understand the project in 10 seconds
- Service view: see how repository intelligence flows
- Module view: navigate ownership without a graph hairball
- Implementation view: inspect files, symbols, and routes only when needed

This is still not a hosted SaaS.

It is a local AI engineering project built to answer one question:

What would repository onboarding look like if the tool could read code, build architecture maps, retrieve evidence, and write like a senior engineer?

Screenshots:

- `screenshots/dashboard-overview.png`
- `screenshots/architecture-view.png`
- `screenshots/dependency-view.png`
- `screenshots/security-view.png`
- `screenshots/repository-chat.png`

#AI #OpenSource #LocalAI #SoftwareEngineering #FastAPI #NextJS #ChromaDB #CodeIntelligence
