# Training API Reference

## `models.llm.trainer.train`

### `train(config_path: str = "configs/config_4b.yaml")`

Run pre-training from a YAML config.

| Parameter | Type | Description |
|-----------|------|-------------|
| `config_path` | `str` | Path to training config YAML |

### `models.llm.trainer.finetune`

### `finetune(config_path: str, model_path: str, output_dir: str)`

Run instruction tuning / fine-tuning.

| Parameter | Type | Description |
|-----------|------|-------------|
| `config_path` | `str` | Fine-tuning config YAML |
| `model_path` | `str` | Path to pretrained checkpoint |
| `output_dir` | `str` | Where to save fine-tuned model |

### `models.llm.trainer.pretrain`

### `pretrain(config_path: str)`

Run full pre-training loop (alias for `train` with additional logging).

### `models.llm.trainer.checkpoint`

### `save_checkpoint(model, optimizer, scheduler, epoch, path: str)`

Save training state.

### `load_checkpoint(model, optimizer, scheduler, path: str) -> int`

Load training state and return the next epoch.

### `models.llm.trainer.metrics`

### `compute_perplexity(model, dataloader, device) -> float`

Compute perplexity on a validation dataloader.

### `validate(model, dataloader, device) -> dict`

Run validation and return loss and perplexity.

### Training Config Keys

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `train_file` | `str` | required | Path to training data |
| `val_file` | `str` | required | Path to validation data |
| `batch_size` | `int` | 4 | Per-device batch size |
| `epochs` | `int` | 1 | Number of epochs |
| `lr` | `float` | 3e-4 | Learning rate |
| `gradient_accumulation_steps` | `int` | 1 | Gradient accumulation |
| `gradient_checkpointing` | `bool` | False | Enable activation checkpointing |
| `mixed_precision` | `str` | none | fp16, bf16, or none |
| `output_dir` | `str` | model.pt | Checkpoint save path |
