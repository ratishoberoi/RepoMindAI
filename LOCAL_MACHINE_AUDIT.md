# RepoMind AI Local Machine Audit

Audit date: 2026-05-23 UTC

## Host

- OS: Ubuntu 24.04.4 LTS (Noble Numbat)
- Kernel: Linux Ratish-Workspace 6.6.114.1-microsoft-standard-WSL2 x86_64
- Environment: WSL2
- CPU architecture: x86_64

## Python and Package Tooling

- Python 3: Python 3.12.3
- `python`: not present on PATH
- `pip`: pip 24.0 for Python 3.12
- `uv`: `/home/ratish/.local/bin/uv`, version 0.11.13
- `poetry`: not installed

## Node Tooling

- Node.js: v18.19.1
- npm: 9.2.0
- npx: 9.2.0
- pnpm: not installed
- yarn: not installed

## GPU, CUDA, RAM, and Disk

- GPU runtime: `nvidia-smi` available at `/usr/lib/wsl/lib/nvidia-smi`
- GPU: NVIDIA GeForce RTX 5090
- VRAM: 32607 MiB
- NVIDIA driver: 595.79
- CUDA compiler: CUDA 13.2, nvcc V13.2.78
- RAM: 45 GiB total, approximately 44 GiB available at audit time
- Swap: 12 GiB total
- Disk mounted at `/`: 1007 GiB total, 841 GiB available at audit time

## Core Developer Tools

- Git: git version 2.43.0
- Docker engine: Docker version 29.1.3
- Docker Compose plugin: not available (`docker compose` unknown)
- Legacy `docker-compose`: not installed

## Local Inference Runtimes

- Ollama: not installed
- vLLM CLI/module: not detected
- Python ML packages in global environment:
  - `torch`: missing
  - `transformers`: missing
  - `sentence_transformers`: missing

RepoMind AI must therefore create an isolated project environment and load local model files through an adapter layer. No cloud model APIs are available or required.

## Datastores and Background Job Services

- PostgreSQL CLI/server tools: not detected (`psql` missing)
- Redis server: not detected
- Python packages in global environment:
  - `chromadb`: missing
  - `redis`: missing
  - `celery`: missing
  - `psycopg`: missing
  - `sqlalchemy`: missing

Docker is available, so local PostgreSQL, Redis, and Chroma can be run through Compose after installing a Compose-compatible frontend or by using local process fallbacks during development.

## Analysis Tooling

- `tree-sitter` CLI: not installed
- Python packages in global environment:
  - `tree_sitter`: missing
  - `networkx`: missing
  - `radon`: missing
  - `bandit`: missing
  - `semgrep`: missing
  - `GitPython`: missing
  - `fastapi`: missing

These should be installed into the RepoMind AI backend virtual environment only.

## Local Model Inventory

Required local model folders are present under `/home/ratish/Forge/models`. Forge was inspected read-only.

| Role | Path | Size | Detected format | Key files | Runtime status |
| --- | --- | ---: | --- | --- | --- |
| Main analysis / generation | `/home/ratish/Forge/models/qwen-primary` | 23G | Hugging Face Transformers-style checkpoint, sharded `.safetensors` | `config.json`, `generation_config.json`, `model-00001-of-00005.safetensors` ... `model-00005-of-00005.safetensors`, `tokenizer.json`, `tokenizer_config.json` | Format valid; load pending project env because global `torch`/`transformers` are absent |
| Evaluation / critique | `/home/ratish/Forge/models/qwen-judge` | 19G | Hugging Face Transformers-style checkpoint, sharded `.safetensors` | `config.json`, `generation_config.json`, 5 safetensor shards, tokenizer files | Format valid; load pending project env |
| Long-form synthesis / report aggregation | `/home/ratish/Forge/models/deepseek-synth` | 34G | Hugging Face Transformers-style checkpoint, sharded `.safetensors` | `config.json`, `generation_config.json`, 2 safetensor shards, tokenizer files | Format valid; load pending project env |

### Model Metadata

`qwen-primary`

- Architecture: `Qwen3_5MoeForConditionalGeneration`
- Model type: `qwen3_5_moe`
- Quantization metadata: present
- Vision config: present
- GGUF files: none detected

`qwen-judge`

- Architecture: `Qwen2ForCausalLM`
- Model type: `qwen2`
- dtype: `float16`
- Max position embeddings: 40960
- Quantization metadata: present
- GGUF files: none detected

`deepseek-synth`

- Architecture: `LlamaForCausalLM`
- Model type: `llama`
- dtype: `float16`
- Max position embeddings: 16384
- Quantization metadata: present
- GGUF files: none detected

## Model Cache Scan

No additional local Hugging Face, Torch, Chroma, or Ollama model cache files were detected in the checked cache locations:

- `~/.cache/huggingface`
- `~/.cache/torch`
- `~/.cache/chroma`
- `~/.ollama`

## Audit Conclusions

1. The required Forge models exist and should be reused by role.
2. The models are local Hugging Face-style checkpoints, not GGUF.
3. Runtime loading cannot be confirmed until RepoMind AI creates an isolated Python environment with `torch`, `transformers`, and related dependencies.
4. The machine has enough GPU VRAM and system RAM to attempt local inference, but the adapter must support graceful fallback because `qwen-primary` uses a newer Qwen MoE architecture that may require a recent Transformers release.
5. Docker engine exists, but Docker Compose is missing. Compose support must be installed or documented as a prerequisite for container orchestration.
6. PostgreSQL, Redis, ChromaDB, FastAPI, tree-sitter, Bandit, Semgrep, and analysis packages are not globally installed and should be installed only inside the project environment or run as local containers.
