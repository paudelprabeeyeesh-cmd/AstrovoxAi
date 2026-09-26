# Inference Engine

The AstrovoxAI inference engine provides high-performance model serving with KV cache management, continuous batching, speculative decoding, and hallucination detection.

## Features
- **KV Cache Manager**: Efficient key-value cache with prefix caching
- **Continuous Batching**: Dynamic batching for higher throughput
- **Speculative Decoding**: Draft model + target model verification
- **Prefix Caching**: Reuse cached prefixes across requests
- **Hallucination Detection**: Factuality scoring with grounding checks
- **Advanced Inference Server**: REST/WebSocket server with health checks

## Usage
```python
from ASTROVOX_AI.ai_core.inference.inference_engine import InferenceEngine
from transformers import AutoModelForCausalLM, AutoConfig

config = AutoConfig.from_pretrained("model-name")
model = AutoModelForCausalLM.from_pretrained("model-name")
engine = InferenceEngine(model, config, device=torch.device("cuda"))
output = engine.generate(input_ids, max_new_tokens=100, temperature=0.7)
```

## API
- `POST /v1/chat/completions` — Chat completion with streaming
- `POST /v1/completions` — Text completion
- `GET /v1/models` — List available models
- `POST /v1/embeddings` — Generate embeddings
