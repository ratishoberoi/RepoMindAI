# Model Benchmark

Date: 2026-05-23 UTC

Benchmark prompt:

> Analyze repository evidence for a small FastAPI app with `pyproject.toml`, `/health`, `/admin`, `/users`, and `API_TOKEN`, then return architecture, API routes, security risk, dependency graph, and production readiness.

Runtime:

- PyTorch: 2.12.0+cu130
- Transformers: 5.9.0
- GPU: NVIDIA GeForce RTX 5090, 32,606 MiB usable VRAM
- Loader additions installed: `gptqmodel`, `compressed-tensors`, `torchvision`, `ninja`

## Results

| Model | Architecture | Tokenizer | Load | VRAM | Generation | Quality | Decision |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `/home/ratish/Forge/models/qwen-primary` | `Qwen3_5MoeForConditionalGeneration`, `qwen3_5_moe` | present | Model construction reached, generation failed | 26,707 MiB delta before failure | Failed: compressed-tensors `group_size` validation during generation | Not usable | Rejected |
| `/home/ratish/Forge/models/qwen-judge` | `Qwen2ForCausalLM`, `qwen2` | present | Success | 18,740 MiB delta in benchmark | 160 tokens in 10.99s, 14.56 tok/s | Best factual repository analysis, but verbose reasoning style | Selected |
| `/home/ratish/Forge/models/deepseek-synth` | `LlamaForCausalLM`, `llama` | present | Success | 17,548 MiB delta | 160 tokens in 9.64s, 16.6 tok/s | Usable but emitted refusal-ish text and tokenizer artifacts like `Ġ` | Rejected |

## Parameter Counts

These checkpoints are quantized, so raw `num_parameters()` reflects loaded packed modules, not necessarily original dense pre-quantization parameter count.

- `qwen-judge`: `model.num_parameters()` reported `5,732,766,720` loaded packed parameters; checkpoint index has 1,667 tensors and 19,328,804,864 weight bytes.
- `deepseek-synth`: `model.num_parameters()` reported `4,862,258,688` loaded packed parameters; checkpoint index has 1,429 tensors and 18,008,653,824 weight bytes.
- `qwen-primary`: exact loaded parameter count was not trusted because generation failed after compressed-tensors model construction; checkpoint index has 95,427 tensors.

## Selected Model

Production inference now uses only:

`/home/ratish/Forge/models/qwen-judge`

Role routing was removed. RAG, architecture/report synthesis, CTO review, recruiter review, and chat all call the same local model path through `backend/repomind/llm/adapters.py`.

