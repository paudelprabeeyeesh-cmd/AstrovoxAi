# Models API Reference

## `models.llm.model.LLM`

Core transformer-based language model.

### Constructor

```python
LLM(config: dict, device: torch.device = None, dtype: torch.dtype = None)
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `config` | `dict` | Model configuration (vocab_size, hidden_size, num_hidden_layers, etc.) |
| `device` | `torch.device` | Target device. Defaults to CPU. |
| `dtype` | `torch.dtype` | Weight dtype. Defaults to `torch.float32`. |

### Methods

#### `forward(input_ids, labels=None, attention_mask=None, use_gradient_checkpointing=False) -> dict`

Run forward pass.

| Parameter | Type | Description |
|-----------|------|-------------|
| `input_ids` | `torch.Tensor` | Token IDs of shape `(batch, seq_len)` |
| `labels` | `torch.Tensor` | Optional target IDs for loss computation |
| `attention_mask` | `torch.Tensor` | Optional 2D attention mask |
| `use_gradient_checkpointing` | `bool` | Enable gradient checkpointing |

**Returns:** `{"logits": torch.Tensor, "loss": Optional[torch.Tensor]}`

#### `get_num_params(trainable_only=True) -> int`

Count model parameters.

#### `estimate_memory(training=True, dtype_bytes=2) -> dict`

Estimate memory consumption in GB.

### Class Methods

#### `from_config(config: dict) -> LLM`

Instantiate from a configuration dictionary.

#### `get_num_params_from_config(config: dict, trainable_only=True) -> int`

Count parameters without instantiating the model.

#### `estimate_memory_from_config(config: dict, training=True, dtype_bytes=2) -> dict`

Estimate memory from config without instantiating.

### Configuration Keys

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `vocab_size` | `int` | required | Vocabulary size |
| `hidden_size` | `int` | required | Hidden dimension |
| `num_hidden_layers` | `int` | required | Transformer blocks |
| `num_attention_heads` | `int` | required | Attention heads |
| `intermediate_size` | `int` | required | FFN dimension |
| `max_position_embeddings` | `int` | 2048 | Context length |
| `rms_norm_eps` | `float` | 1e-5 | RMSNorm epsilon |
| `rope_theta` | `float` | 10000.0 | RoPE base frequency |
| `activation` | `str` | swiglu | Activation function |
| `attention_bias` | `bool` | False | Use bias in attention projections |
| `mlp_bias` | `bool` | False | Use bias in MLP |
| `dropout` | `float` | 0.0 | Dropout probability |
| `tie_weights` | `bool` | True | Tie input/output embeddings |
