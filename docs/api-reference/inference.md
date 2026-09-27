# Inference API Reference

## `models.llm.inference.engine.InferenceEngine`

High-level generation engine.

### Constructor

```python
InferenceEngine(model: nn.Module, tokenizer, device=None, dtype=None)
```

### Methods

#### `generate(prompt: str, params=None, seq_id=None) -> GenerationOutput`

Generate text from a prompt.

| Parameter | Type | Description |
|-----------|------|-------------|
| `prompt` | `str` | Input prompt |
| `params` | `SamplingParams` | Sampling parameters |
| `seq_id` | `str` | Optional sequence ID for KV cache |

#### `astream_generate(prompt, params=None, seq_id=None) -> AsyncIterator[str]`

Async streaming generation.

#### `stream_generate(prompt, params=None) -> Iterator[str]`

Sync streaming generation.

#### `beam_search(prompt, beam_width=4, max_new_tokens=100) -> GenerationOutput`

Beam search decoding.

#### `batch_generate(prompts, params=None) -> List[GenerationOutput]`

Batch generation over multiple prompts.

#### `chat(messages, params=None) -> GenerationOutput`

Chat-style generation from message list.

#### `completion(prompt, params=None) -> GenerationOutput`

Simple text completion.

#### `count_tokens(text: str) -> int`

Count tokens in text.

## `models.llm.inference.engine.SamplingParams`

```python
SamplingParams(
    temperature: float = 1.0,
    top_k: Optional[int] = None,
    top_p: Optional[float] = None,
    repetition_penalty: float = 1.0,
    max_new_tokens: int = 100,
    stop: Optional[List[str]] = None,
)
```

## FastAPI Server

### `create_app(engine=None, config_path=None, checkpoint_path=None, device=None) -> FastAPI`

Create a FastAPI inference server.

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/v1/completions` | POST | Text completion |
| `/v1/chat/completions` | POST | Chat completion |
| `/v1/batch` | POST | Batch completion |
| `/metrics` | GET | Prometheus metrics |

### `run_server(host, port, config_path, checkpoint_path, device)`

Start the inference server directly.
