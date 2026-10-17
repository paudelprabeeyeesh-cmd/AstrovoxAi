"""Measured next-token evaluation and local text generation for saved checkpoints."""

from __future__ import annotations

import json
from pathlib import Path

import torch

from .config import TinyTransformerConfig
from .model import TinyTransformer
from .tokenizer import CharacterTokenizer
from .training import CHECKPOINT_SCHEMA_VERSION, _token_batches

MAX_CHECKPOINT_BYTES = 128 * 1024 * 1024


def load_experimental_checkpoint(path: str | Path) -> tuple[TinyTransformer, CharacterTokenizer, dict]:
    checkpoint_path = Path(path).expanduser().resolve(strict=True)
    if not checkpoint_path.is_file() or checkpoint_path.stat().st_size > MAX_CHECKPOINT_BYTES:
        raise ValueError("checkpoint must be a local file no larger than 128 MiB")
    payload = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
    if payload.get("schema_version") != CHECKPOINT_SCHEMA_VERSION:
        raise ValueError("checkpoint schema version is unsupported")
    config = TinyTransformerConfig(**payload["config"])
    tokenizer = CharacterTokenizer.from_dict(payload["tokenizer"])
    model = TinyTransformer(config)
    model.load_state_dict(payload["model"])
    model.eval()
    return model, tokenizer, payload


def evaluate_checkpoint(
    checkpoint_path: str | Path,
    dataset_path: str | Path,
    *,
    max_batches: int = 32,
) -> dict:
    if max_batches < 1:
        raise ValueError("max_batches must be positive")
    model, tokenizer, checkpoint = load_experimental_checkpoint(checkpoint_path)
    dataset = Path(dataset_path).expanduser().resolve(strict=True)
    if not dataset.is_file() or dataset.stat().st_size > 16 * 1024 * 1024:
        raise ValueError("evaluation dataset must be a local file no larger than 16 MiB")
    total_loss = 0.0
    token_count = 0
    batch_count = 0
    try:
        batches = _token_batches(dataset, tokenizer, model.config.context_length, model.config.batch_size, "validation")
        with torch.inference_mode():
            for inputs, targets in batches:
                _, loss = model(inputs, targets)
                if loss is None or not torch.isfinite(loss):
                    raise FloatingPointError("evaluation produced a non-finite loss")
                tokens = targets.numel()
                total_loss += loss.item() * tokens
                token_count += tokens
                batch_count += 1
                if batch_count >= max_batches:
                    break
    except KeyError as exc:
        raise ValueError("evaluation text contains characters outside this checkpoint vocabulary") from exc
    if not token_count:
        raise ValueError("evaluation dataset has no complete held-out sequence")
    mean_loss = total_loss / token_count
    return {
        "checkpoint_step": int(checkpoint["step"]),
        "evaluation_dataset_name": dataset.name,
        "evaluation_dataset_bytes": dataset.stat().st_size,
        "batches_measured": batch_count,
        "tokens_measured": token_count,
        "next_token_cross_entropy": mean_loss,
        "perplexity": float(torch.exp(torch.tensor(mean_loss)).item()),
        "status": "measured",
    }


def generate_text(
    checkpoint_path: str | Path,
    prompt: str,
    *,
    max_new_tokens: int = 64,
    temperature: float = 1.0,
    top_k: int | None = None,
) -> str:
    model, tokenizer, _ = load_experimental_checkpoint(checkpoint_path)
    input_ids = torch.tensor([tokenizer.encode(prompt)], dtype=torch.long)
    generated = model.generate(input_ids, max_new_tokens=max_new_tokens, temperature=temperature, top_k=top_k)
    return tokenizer.decode(generated[0].tolist())


def write_evaluation_report(run_dir: str | Path, results: dict) -> Path:
    destination = Path(run_dir).resolve()
    if not destination.is_dir():
        raise ValueError("run directory does not exist")
    report_path = destination / "evaluation.json"
    temporary_path = destination / "evaluation.json.tmp"
    temporary_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    temporary_path.replace(report_path)
    return report_path
