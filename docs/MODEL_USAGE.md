# Model Usage Guide

RepoMind AI never calls OpenAI, Anthropic, Groq, Pinecone, or cloud LLM APIs.

## Selected Production Model

RepoMind AI uses one production local model:

- `${FORGE_MODELS}/qwen-judge`

## Backend Detection

The adapter checks for:

1. GGUF files.
2. Hugging Face `config.json`, tokenizer files, and `.safetensors` or `.bin` weights.
3. Ollama runtime availability.
There is no production role router. The benchmark selected `qwen-judge` because it is the only tested model that loads and produces usable repository-analysis output on this machine.

## Heavy Loading

Install optional LLM dependencies:

```bash
uv pip install -e ".[llm]"
```

Model loading uses `local_files_only=True`.
