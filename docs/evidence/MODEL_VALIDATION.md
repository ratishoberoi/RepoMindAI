# Model Validation

Date: 2026-05-23 UTC

## qwen-primary

- Path: `${FORGE_MODELS}/qwen-primary`
- Config: valid JSON
- Tokenizer: `tokenizer.json`, `tokenizer_config.json`, `vocab.json` present
- Weights: 5 safetensor shards plus index
- Actual architecture: `Qwen3_5MoeForConditionalGeneration`
- Model type: `qwen3_5_moe`
- Load result: partial construction succeeded
- Inference result: failed
- Failure: `compressed_tensors` decompression raised `QuantizationArgs` validation error because group strategy received `group_size: 0`
- Fix attempted: installed `compressed-tensors`; failure persisted during generation
- Decision: not production-compatible in this Transformers runtime

## qwen-judge

- Path: `${FORGE_MODELS}/qwen-judge`
- Config: valid JSON
- Tokenizer: present
- Weights: 5 safetensor shards plus index
- Actual architecture: `Qwen2ForCausalLM`
- Model type: `qwen2`
- Load result: success after installing AWQ runtime dependencies
- Missing runtime dependencies fixed: `gptqmodel`, `torchvision`, `ninja`
- Load latency: 85.6s first run including Marlin JIT compile; later loads about 6s after cache
- VRAM delta: about 18.7 GiB
- Inference latency: 160 tokens in 10.99s
- Sample behavior: produces relevant repository analysis but often includes reasoning preamble
- Decision: selected single production model

## deepseek-synth

- Path: `${FORGE_MODELS}/deepseek-synth`
- Config: valid JSON
- Tokenizer: present
- Weights: 2 safetensor shards plus index
- Actual architecture: `LlamaForCausalLM`
- Model type: `llama`
- Load result: success after AWQ runtime dependencies
- VRAM delta: about 17.5 GiB
- Inference latency: 160 tokens in 9.64s
- Sample behavior: started with refusal language and emitted tokenizer artifacts
- Decision: rejected for production use

