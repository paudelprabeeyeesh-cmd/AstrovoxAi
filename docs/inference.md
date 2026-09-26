# Inference Engine

The AstrovoxAI inference engine provides high-performance model serving with advanced optimization techniques including KV cache management, continuous batching, speculative decoding, and hallucination detection.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                      INFERENCE ENGINE                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────┐  │
│  │   Request    │    │   Scheduler  │    │   Batch Manager      │  │
│  │   Handler    │───►│              │───►│   (Continuous)       │  │
│  └──────────────┘    └──────────────┘    └──────────┬───────────┘  │
│                                                       │             │
│  ┌──────────────┐    ┌──────────────┐    ┌───────────▼───────────┐  │
│  │   Speculative │    │   KV Cache   │    │   Model Executor     │  │
│  │   Decoder     │    │   Manager    │    │   (GPU/CPU/TPU)      │  │
│  └──────────────┘    └──────────────┘    └───────────┬───────────┘  │
│                                                       │             │
│  ┌──────────────┐    ┌──────────────┐    ┌───────────▼───────────┐  │
│  │   Hallucination│   │   Output     │    │   Token Sampler      │  │
│  │   Detector    │    │   Processor  │    │   (Top-p, Top-k)     │  │
│  └──────────────┘    └──────────────┘    └──────────────────────┘  │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

## Core Components

### KV Cache Manager

Efficiently manages key-value caches for transformer models:

```python
from ASTROVOX_AI.ai_core.inference.kv_cache_manager import KVCacheManager

cache = KVCacheManager(
    num_layers=32,
    num_heads=32,
    head_dim=128,
    max_seq_len=8192,
    device="cuda"
)

# Prefix caching - reuse cached prefixes
cached_prefix = cache.get_prefix("common_system_prompt")
if cached_prefix:
    key, value = cached_prefix
else:
    key, value = model.compute_prefix(common_system_prompt)
    cache.put_prefix("common_system_prompt", key, value)

# Cache eviction strategies
cache.set_eviction_policy("lru")  # or "fifo", "lfu"
```

### Continuous Batching

Dynamic batching for higher throughput:

```python
from ASTROVOX_AI.ai_core.inference.continuous_batcher import ContinuousBatcher

batcher = ContinuousBatcher(
    max_batch_size=32,
    max_wait_time_ms=10,
    max_seq_len=4096
)

# Add requests dynamically
batcher.add_request(request_id="req-1", tokens=input_ids_1)
batcher.add_request(request_id="req-2", tokens=input_ids_2)

# Process batch when ready or timeout
batch = batcher.get_batch()
outputs = model.forward(batch)
batcher.complete_requests(outputs)
```

### Speculative Decoding

Accelerate inference with draft model verification:

```python
from ASTROVOX_AI.ai_core.inference.speculative_decoder import SpeculativeDecoder

decoder = SpeculativeDecoder(
    target_model=target_model,
    draft_model=draft_model,
    num_draft_tokens=5,
    acceptance_threshold=0.8
)

# Generate with speculative decoding
tokens = decoder.generate(
    prompt_ids=input_ids,
    max_new_tokens=100,
    temperature=0.7
)
```

### Hallucination Detection

Factuality scoring and grounding checks:

```python
from ASTROVOX_AI.ai_core.inference.hallucination_detector import HallucinationDetector

detector = HallucinationDetector(
    embedding_model="text-embedding-004",
    fact_checker=fact_checker_model
)

# Detect hallucinations
result = detector.check(
    generated_text=response,
    source_documents=context_docs,
    threshold=0.7
)

if result.has_hallucinations:
    print(f"Hallucinations detected: {result.spans}")
    print(f"Confidence: {result.confidence}")
```

## Usage

### Python API

```python
from ASTROVOX_AI.ai_core.inference.inference_engine import InferenceEngine
from transformers import AutoModelForCausalLM, AutoTokenizer, AutoConfig
import torch

# Load model
config = AutoConfig.from_pretrained("meta-llama/Llama-2-7b-chat-hf")
model = AutoModelForCausalLM.from_pretrained(
    "meta-llama/Llama-2-7b-chat-hf",
    torch_dtype=torch.float16,
    device_map="auto"
)
tokenizer = AutoTokenizer.from_pretrained("meta-llama/Llama-2-7b-chat-hf")

# Initialize engine
engine = InferenceEngine(
    model=model,
    tokenizer=tokenizer,
    config=config,
    device=torch.device("cuda"),
    enable_kv_cache=True,
    enable_speculative=True,
    enable_hallucination_detection=True
)

# Generate with streaming
for token in engine.stream_generate(
    prompt="Explain quantum computing",
    max_new_tokens=500,
    temperature=0.7,
    top_p=0.9
):
    print(token, end="", flush=True)

# Batch generation
outputs = engine.batch_generate(
    prompts=["Hello", "Explain AI", "What is Python?"],
    max_new_tokens=100
)
```

### REST API

| Method | Path | Description |
|--------|------|-------------|
| POST | `/v1/chat/completions` | Chat completion with streaming |
| POST | `/v1/completions` | Text completion |
| GET | `/v1/models` | List available models |
| POST | `/v1/embeddings` | Generate embeddings |
| POST | `/v1/chat/stream` | Streaming chat (SSE) |
| GET | `/v1/health` | Inference server health |

### Example Request

```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama-2-7b",
    "messages": [{"role": "user", "content": "Hello!"}],
    "stream": true,
    "temperature": 0.7,
    "max_tokens": 100
  }'
```

## Advanced Features

### Prefix Caching

Reuse KV cache for common prefixes across requests:

```python
engine.enable_prefix_caching([
    "system: You are a helpful assistant.",
    "system: You are a coding expert."
])

# Subsequent requests with matching prefix skip recomputation
```

### Quantization

Support for INT8, FP8, FP4, and NF4 quantization:

```python
from ASTROVOX_AI.ai_core.quantization.quantizer import Quantizer

quantizer = Quantizer(model, method="awq")
quantized_model = quantizer.quantize(bits=4)

# 4x smaller model, 2-3x faster inference
```

### Tensor Parallelism

Distribute model across multiple GPUs:

```python
engine = InferenceEngine(
    model=model,
    tensor_parallel_size=4,  # 4 GPUs
    pipeline_parallel_size=2  # 2 pipeline stages
)
```

## Performance Tuning

| Parameter | Default | Description |
|-----------|---------|-------------|
| `max_batch_size` | 32 | Maximum concurrent requests |
| `max_wait_time_ms` | 10 | Max wait time for batch formation |
| `num_draft_tokens` | 5 | Draft tokens for speculative decoding |
| `kv_cache_size` | 8192 | KV cache sequence length |
| `temperature` | 0.7 | Sampling temperature |
| `top_p` | 0.9 | Nucleus sampling threshold |

## Monitoring

The inference engine exposes metrics for monitoring:

- Request throughput (requests/second)
- Token generation speed (tokens/second)
- P50/P95/P99 latency
- Cache hit/miss rates
- Batch sizes
- GPU utilization
- Memory usage
