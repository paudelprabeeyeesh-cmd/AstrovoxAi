"""Single-job, streaming CPU trainer for the educational character model."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import threading
import time
import uuid
from collections.abc import Iterator
from contextlib import suppress
from datetime import UTC, datetime
from pathlib import Path

import psutil
import torch

from .config import TinyTransformerConfig
from .model import TinyTransformer
from .resources import enforce_memory_budget
from .tokenizer import CharacterTokenizer

_JOB_LOCK = threading.Lock()
CHECKPOINT_SCHEMA_VERSION = 1


def _acquire_process_training_lock():
    """Acquire one OS-level lock so separate CLI processes cannot train together."""
    lock_path = Path(tempfile.gettempdir()) / "astrovox-neural-lab-training.lock"
    handle = lock_path.open("a+b")
    handle.seek(0, os.SEEK_END)
    if handle.tell() == 0:
        handle.write(b"\0")
        handle.flush()
    handle.seek(0)
    try:
        if os.name == "nt":
            import msvcrt

            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except (OSError, BlockingIOError):
        handle.close()
        raise RuntimeError("another Neural Lab training process is already running") from None
    return handle


def _release_process_training_lock(handle) -> None:
    handle.seek(0)
    if os.name == "nt":
        import msvcrt

        with suppress(OSError):
            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        import fcntl

        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    handle.close()


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(temporary, path)


def _save_checkpoint(path: Path, model: TinyTransformer, optimizer: torch.optim.Optimizer,
                     step: int, config: TinyTransformerConfig, tokenizer: CharacterTokenizer,
                     optimizer_name: str, epoch: int = 0, dataset_digest: str | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=path.stem, suffix=".tmp", dir=path.parent)
    os.close(fd)
    try:
        torch.save({
            "schema_version": CHECKPOINT_SCHEMA_VERSION,
            "model": model.state_dict(),
            "optimizer": optimizer.state_dict(),
            "optimizer_name": optimizer_name,
            "step": step,
            "epoch": epoch,
            "dataset_digest": dataset_digest,
            "config": config.to_dict(),
            "tokenizer": tokenizer.to_dict(),
        }, temp_name)
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def _token_batches(path: Path, tokenizer: CharacterTokenizer, context: int, batch_size: int,
                   split: str) -> Iterator[tuple[torch.Tensor, torch.Tensor]]:
    """Read fixed-size chunks from disk; every tenth chunk is held out for validation."""
    window: list[int] = []
    batch_x: list[list[int]] = []
    batch_y: list[list[int]] = []
    chunk_index = 0
    with path.open("r", encoding="utf-8", errors="strict") as stream:
        while text_chunk := stream.read(8192):
            for char in text_chunk:
                window.append(tokenizer._ids[char])
                if len(window) < context + 1:
                    continue
                is_validation = chunk_index % 10 == 0
                if (split == "validation") == is_validation:
                    batch_x.append(window[:-1])
                    batch_y.append(window[1:])
                    if len(batch_x) == batch_size:
                        yield torch.tensor(batch_x, dtype=torch.long), torch.tensor(batch_y, dtype=torch.long)
                        batch_x, batch_y = [], []
                chunk_index += 1
                window = []
    if batch_x:
        yield torch.tensor(batch_x, dtype=torch.long), torch.tensor(batch_y, dtype=torch.long)


def _next_batch(path: Path, tokenizer: CharacterTokenizer, config: TinyTransformerConfig,
                split: str, iterator: Iterator | None) -> tuple[tuple[torch.Tensor, torch.Tensor], Iterator, bool]:
    cycled = False
    if iterator is None:
        iterator = iter(_token_batches(path, tokenizer, config.context_length, config.batch_size, split))
    try:
        return next(iterator), iterator, cycled
    except StopIteration:
        cycled = True
        iterator = iter(_token_batches(path, tokenizer, config.context_length, config.batch_size, split))
        try:
            return next(iterator), iterator, cycled
        except StopIteration as exc:
            raise ValueError(f"dataset has no complete {split} sequence for this context length") from exc


def _make_optimizer(name: str, parameters, learning_rate: float) -> torch.optim.Optimizer:
    normalized = name.lower()
    if normalized == "adamw":
        return torch.optim.AdamW(parameters, lr=learning_rate)
    if normalized == "adam":
        return torch.optim.Adam(parameters, lr=learning_rate)
    if normalized == "sgd":
        return torch.optim.SGD(parameters, lr=learning_rate)
    raise ValueError("optimizer must be one of: adamw, adam, sgd")


def train_tiny_model(
    dataset_path: str | Path,
    output_dir: str | Path,
    *,
    context_length: int = 32,
    hidden_size: int = 16,
    num_layers: int = 1,
    num_heads: int = 2,
    batch_size: int = 1,
    max_steps: int = 10,
    learning_rate: float = 1e-3,
    seed: int = 17,
    job_id: str | None = None,
    optimizer_name: str = "adamw",
    checkpoint_interval: int = 5,
    memory_budget_mib: int = 256,
    reserve_memory_mib: int = 1536,
    resume_from: str | Path | None = None,
    cancel_event: threading.Event | None = None,
) -> dict:
    """Train a tiny model on a local UTF-8 text file and return measured job metadata."""
    if max_steps < 1 or learning_rate <= 0 or checkpoint_interval < 1:
        raise ValueError("max_steps, checkpoint_interval, and learning_rate must be positive")
    if job_id is not None and (
        not isinstance(job_id, str) or len(job_id) != 32
        or any(char not in "0123456789abcdef" for char in job_id)
    ):
        raise ValueError("job_id must be 32 lowercase hexadecimal characters")
    if not _JOB_LOCK.acquire(blocking=False):
        raise RuntimeError("another Neural Lab training job is already running")
    try:
        process_lock = _acquire_process_training_lock()
    except Exception:
        _JOB_LOCK.release()
        raise
    started = time.monotonic()
    job_id = job_id or uuid.uuid4().hex
    dataset = Path(dataset_path)
    out = Path(output_dir)
    job_path = out / "job.json"
    metrics_path = out / "metrics.jsonl"
    job = {
        "schema_version": 1, "config_schema_version": 1,
        "job_id": job_id, "state": "QUEUED", "dataset_name": dataset.name,
        "training_config": {"max_steps": max_steps, "learning_rate": learning_rate,
                            "checkpoint_interval": checkpoint_interval, "optimizer": optimizer_name.lower(),
                            "seed": seed},
        "dataset_bytes": None, "token_count": None, "start_time": _now(), "end_time": None,
        "step": 0, "epoch": 0, "training_loss": None, "validation_loss": None,
        "observed_rss_bytes": None, "checkpoints": [], "error": None,
    }
    output_already_used = job_path.exists()

    def set_state(state: str) -> None:
        job["state"] = state
        _atomic_json(job_path, job)

    try:
        if output_already_used:
            raise FileExistsError("output directory already contains a job; resume into a fresh run directory")
        set_state("QUEUED")
        set_state("PREPARING")
        if not dataset.is_file():
            raise FileNotFoundError("dataset file does not exist")
        job["dataset_bytes"] = dataset.stat().st_size
        tokenizer = CharacterTokenizer.from_file(dataset)
        digest = hashlib.sha256()
        with dataset.open("rb") as source_stream:
            while data_chunk := source_stream.read(64 * 1024):
                digest.update(data_chunk)
        job["dataset_id"] = digest.hexdigest()
        job["token_count"] = tokenizer.token_count
        config = TinyTransformerConfig(
            vocab_size=tokenizer.vocab_size, context_length=context_length, hidden_size=hidden_size,
            num_layers=num_layers, num_heads=num_heads, batch_size=batch_size,
            memory_budget_mib=memory_budget_mib, reserve_memory_mib=reserve_memory_mib,
            seed=seed,
        )
        estimate = enforce_memory_budget(config)
        train_sequences = job["token_count"] // (config.context_length + 1)
        validation_sequences = (train_sequences + 9) // 10
        training_sequences = max(0, train_sequences - validation_sequences)
        batches_per_epoch = max(1, (training_sequences + config.batch_size - 1) // config.batch_size)
        job["config"] = config.to_dict()
        torch.set_num_threads(1)
        torch.manual_seed(config.seed)
        model = TinyTransformer(config).cpu()
        if model.parameter_count != estimate.parameter_count:
            # The estimator intentionally over-counts a few bias/norm terms; model count is authoritative.
            job["estimated_parameter_count"] = estimate.parameter_count
        job["parameter_count"] = model.parameter_count
        job["memory_estimate_bytes"] = estimate.estimated_total_bytes
        job["optimizer_name"] = optimizer_name.lower()
        optimizer = _make_optimizer(optimizer_name, model.parameters(), learning_rate)
        if resume_from is not None:
            checkpoint = torch.load(Path(resume_from), map_location="cpu", weights_only=True)
            if checkpoint["config"] != config.to_dict() or checkpoint["tokenizer"] != tokenizer.to_dict():
                raise ValueError("checkpoint configuration or tokenizer does not match this run")
            if checkpoint.get("optimizer_name", "adamw") != optimizer_name.lower():
                raise ValueError("checkpoint optimizer does not match this run")
            if checkpoint.get("dataset_digest") not in (None, job["dataset_id"]):
                raise ValueError("checkpoint dataset does not match this run")
            model.load_state_dict(checkpoint["model"])
            optimizer.load_state_dict(checkpoint["optimizer"])
            job["step"] = int(checkpoint["step"])
            job["epoch"] = max(int(checkpoint.get("epoch", 0)), job["step"] // batches_per_epoch + 1)
            train_iterator = iter(_token_batches(dataset, tokenizer, config.context_length, config.batch_size, "train"))
            for _ in range(job["step"] % batches_per_epoch):
                next(train_iterator)
        else:
            train_iterator = None
        set_state("TRAINING")
        if job["epoch"] == 0:
            job["epoch"] = 1
        process = psutil.Process()
        with metrics_path.open("a", encoding="utf-8") as metrics:
            while job["step"] < max_steps:
                if cancel_event is not None and cancel_event.is_set():
                    checkpoint_path = out / "checkpoints" / f"step-{job['step']}.pt"
                    _save_checkpoint(checkpoint_path, model, optimizer, job["step"], config, tokenizer,
                                     optimizer_name.lower(), job["epoch"], job["dataset_id"])
                    job["checkpoints"].append(str(checkpoint_path))
                    set_state("CANCELLED")
                    break
                (inputs, targets), train_iterator, epoch_finished = _next_batch(dataset, tokenizer, config, "train", train_iterator)
                if epoch_finished:
                    job["epoch"] += 1
                optimizer.zero_grad(set_to_none=True)
                _, loss = model(inputs, targets)
                if loss is None or not torch.isfinite(loss):
                    raise FloatingPointError("training produced a non-finite loss")
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()
                job["step"] += 1
                job["training_loss"] = float(loss.detach().item())
                job["observed_rss_bytes"] = process.memory_info().rss
                metrics.write(json.dumps({"epoch": job["epoch"], "step": job["step"], "training_loss": job["training_loss"],
                                          "elapsed_seconds": time.monotonic() - started,
                                          "observed_rss_bytes": job["observed_rss_bytes"]}) + "\n")
                metrics.flush()
                if job["step"] % checkpoint_interval == 0 or job["step"] == max_steps:
                    checkpoint_path = out / "checkpoints" / f"step-{job['step']}.pt"
                    _save_checkpoint(checkpoint_path, model, optimizer, job["step"], config, tokenizer,
                                     optimizer_name.lower(), job["epoch"], job["dataset_id"])
                    job["checkpoints"].append(str(checkpoint_path))
                _atomic_json(job_path, job)
            if job["state"] != "CANCELLED":
                set_state("VALIDATING")
                try:
                    (val_x, val_y), _, _ = _next_batch(dataset, tokenizer, config, "validation", None)
                    model.eval()
                    with torch.no_grad():
                        _, validation_loss = model(val_x, val_y)
                    job["validation_loss"] = float(validation_loss.item()) if validation_loss is not None else None
                    model.train()
                except ValueError:
                    job["validation_loss"] = None
                set_state("CHECKPOINTING")
                final_path = out / "checkpoints" / f"step-{job['step']}.pt"
                if str(final_path) not in job["checkpoints"]:
                    _save_checkpoint(final_path, model, optimizer, job["step"], config, tokenizer,
                                     optimizer_name.lower(), job["epoch"], job["dataset_id"])
                    job["checkpoints"].append(str(final_path))
                set_state("COMPLETED")
        job["end_time"] = _now()
        job["elapsed_seconds"] = time.monotonic() - started
        _atomic_json(job_path, job)
        return job
    except Exception as exc:
        job["state"] = "FAILED"
        job["error"] = f"{type(exc).__name__}: {exc}"
        job["end_time"] = _now()
        job["elapsed_seconds"] = time.monotonic() - started
        if not output_already_used:
            _atomic_json(job_path, job)
        raise
    finally:
        _release_process_training_lock(process_lock)
        _JOB_LOCK.release()
