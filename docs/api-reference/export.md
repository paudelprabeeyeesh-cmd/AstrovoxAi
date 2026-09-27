# Export API Reference

## `models.llm.export`

Model export utilities.

### Formats

| Format | Class | Description |
|--------|-------|-------------|
| `huggingface` | `HuggingFaceExporter` | HuggingFace Transformers format |
| `onnx` | `ONNXExporter` | ONNX with optional ORT validation |
| `tensorrt` | `TensorRTExporter` | TensorRT engine (requires ONNX) |
| `gguf` | `GGUFExporter` | GGUF for llama.cpp / Ollama |
| `safetensors` | `SafeTensorsExporter` | SafeTensors format |

### High-level API

#### `export_model(model, config, output_dir, format="huggingface", tokenizer=None, **kwargs) -> ExportMetadata`

Export a model to the specified format.

#### `export_from_checkpoint(checkpoint_path, output_dir, config, format="huggingface", tokenizer=None, **kwargs) -> ExportMetadata`

Load a checkpoint and export it.

#### `export_from_state_dict(state_dict, config, output_dir, format="huggingface", tokenizer=None, **kwargs) -> ExportMetadata`

Export from a raw state dict.

#### `validate_export(output_dir) -> dict`

Validate an export directory and return a status report.

#### `report_export_sizes(output_dir) -> dict`

Return per-file size breakdown.

#### `list_supported_formats() -> List[str]`

Return available export formats.

## Data Classes

### `ExportMetadata`

```python
ExportMetadata(
    model_name: str,
    format: str,
    timestamp: str,
    original_config: Dict[str, Any],
    exported_files: List[str],
    export_params: Dict[str, Any],
    size_bytes: int,
    validation_status: str,
    notes: List[str],
)
```

## Exceptions

- `FormatValidationError` — Model or state dict validation failed.
- `ExportError` — Export operation failed.
