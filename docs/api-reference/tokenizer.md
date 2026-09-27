# Tokenizer API Reference

## `models.llm.tokenizer.train_tokenizer`

Tokenizer training and loading utilities.

### Functions

#### `load_tokenizer(path: str)`

Load a tokenizer from a JSON file.

| Parameter | Type | Description |
|-----------|------|-------------|
| `path` | `str` | Path to `tokenizer.json` |

**Returns:** Tokenizer instance with `encode` and `decode` methods.

#### `train_tokenizer_from_files(files: List[str], vocab_size: int, output_path: str)`

Train a new tokenizer from text files.

| Parameter | Type | Description |
|-----------|------|-------------|
| `files` | `List[str]` | Paths to training text files |
| `vocab_size` | `int` | Target vocabulary size |
| `output_path` | `str` | Where to save `tokenizer.json` |

### `TextDataset`

PyTorch `Dataset` that tokenizes text into fixed-length blocks.

```python
TextDataset(file_path: str, tokenizer, block_size: int = 1024)
```

### `collate_fn`

Collate function for `DataLoader`.

```python
collate_fn(batch: List[dict], pad_token_id: int) -> dict
```

Pads sequences to the maximum length in the batch and creates `labels` by shifting `input_ids` right by one position.
