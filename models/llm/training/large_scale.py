"""
Phase K Large-Scale Training Module
=====================================

Production-ready large-scale LLM training supporting:
- 1B / 3.7B / 10B parameter models
- DeepSpeed-style ZeRO (Stage 1 / 2 / 3)
- Fully Sharded Data Parallel (FSDP)
- Pipeline Parallelism
- Tensor Parallelism
- Mixed Precision (BF16 / FP16)
- Gradient Checkpointing
- Activation Checkpointing / Recomputation
- Distributed checkpoint save / resume
- Training metrics reporting
- Model card generation

Hardware support:
- Multi-GPU (NVIDIA CUDA)
- Multi-node via RANK / WORLD_SIZE / LOCAL_RANK environment variables
- Graceful fallback to single-device when distributed features are unavailable
"""

from __future__ import annotations

import argparse
import gc
import json
import logging
import math
import os
import sys
import time
import warnings
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import torch
import torch.nn as nn
import yaml

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Internal imports with graceful fallback
# ---------------------------------------------------------------------------
try:
    from ..utils.helpers import load_config, get_device, set_cpu_threads, count_parameters

    _HELPERS_AVAILABLE = True
except Exception:  # pragma: no cover
    _HELPERS_AVAILABLE = False
    load_config = get_device = set_cpu_threads = count_parameters = None  # type: ignore[misc,assignment]

try:
    from ..model.model import LLM

    _LLM_AVAILABLE = True
except Exception:  # pragma: no cover
    _LLM_AVAILABLE = False
    LLM = None  # type: ignore[misc,assignment]

try:
    from ..tokenizer.train_tokenizer import load_tokenizer, TextDataset, collate_fn

    _TOKENIZER_AVAILABLE = True
except Exception:  # pragma: no cover
    _TOKENIZER_AVAILABLE = False
    load_tokenizer = TextDataset = collate_fn = None  # type: ignore[misc,assignment]

try:
    from ..trainer.checkpoint import save_checkpoint, load_checkpoint, list_checkpoints

    _CHECKPOINT_AVAILABLE = True
except Exception:  # pragma: no cover
    _CHECKPOINT_AVAILABLE = False
    save_checkpoint = load_checkpoint = list_checkpoints = None  # type: ignore[misc,assignment]

try:
    from ..distributed_training import (
        DistributedStrategy,
        init_distributed,
        destroy_distributed,
        wrap_model,
        create_distributed_dataloader,
        is_main_process,
        barrier,
        get_rank,
        get_world_size,
        get_local_rank,
        is_distributed,
        log_memory_usage,
    )

    _DISTRIBUTED_AVAILABLE = True
except Exception:  # pragma: no cover
    _DISTRIBUTED_AVAILABLE = False
    DistributedStrategy = None  # type: ignore[misc,assignment]
    init_distributed = destroy_distributed = wrap_model = None  # type: ignore[misc,assignment]
    create_distributed_dataloader = is_main_process = barrier = None  # type: ignore[misc,assignment]
    get_rank = get_world_size = get_local_rank = is_distributed = None  # type: ignore[misc,assignment]
    log_memory_usage = None  # type: ignore[misc,assignment]

try:
    from ..memory_optimization import (
        MemoryProfiler,
        checkpoint_forward,
        SelectiveRecompute,
        MixedPrecisionTraining,
    )

    _MEMORY_OPT_AVAILABLE = True
except Exception:  # pragma: no cover
    _MEMORY_OPT_AVAILABLE = False
    MemoryProfiler = checkpoint_forward = SelectiveRecompute = MixedPrecisionTraining = None  # type: ignore[misc,assignment]

try:
    from ..training.optimizers import get_optimizer_and_scheduler

    _OPTIMIZERS_AVAILABLE = True
except Exception:  # pragma: no cover
    _OPTIMIZERS_AVAILABLE = False
    get_optimizer_and_scheduler = None  # type: ignore[misc,assignment]

try:
    from ..training.experiment_tracker import ExperimentLogger

    _EXPERIMENT_TRACKER_AVAILABLE = True
except Exception:  # pragma: no cover
    _EXPERIMENT_TRACKER_AVAILABLE = False
    ExperimentLogger = None  # type: ignore[misc,assignment]

try:
    from ..trainer.metrics import evaluate_metrics, compute_perplexity

    _METRICS_AVAILABLE = True
except Exception:  # pragma: no cover
    _METRICS_AVAILABLE = False
    evaluate_metrics = compute_perplexity = None  # type: ignore[misc,assignment]


# ---------------------------------------------------------------------------
# Built-in model presets for 1B / 3.7B / 10B
# ---------------------------------------------------------------------------
MODEL_PRESETS: Dict[str, Dict[str, Any]] = {
    "1b": {
        "vocab_size": 32000,
        "hidden_size": 2048,
        "num_hidden_layers": 24,
        "num_attention_heads": 32,
        "intermediate_size": 8192,
        "max_position_embeddings": 2048,
        "dropout": 0.0,
        "rms_norm_eps": 1e-5,
        "rope_theta": 10000.0,
        "activation": "swiglu",
        "attention_bias": False,
        "mlp_bias": False,
        "tie_weights": True,
    },
    "3.7b": {
        "vocab_size": 32000,
        "hidden_size": 2560,
        "num_hidden_layers": 32,
        "num_attention_heads": 32,
        "intermediate_size": 10240,
        "max_position_embeddings": 2048,
        "dropout": 0.0,
        "rms_norm_eps": 1e-5,
        "rope_theta": 10000.0,
        "activation": "swiglu",
        "attention_bias": False,
        "mlp_bias": False,
        "tie_weights": True,
    },
    "10b": {
        "vocab_size": 32000,
        "hidden_size": 4096,
        "num_hidden_layers": 40,
        "num_attention_heads": 32,
        "intermediate_size": 11008,
        "max_position_embeddings": 2048,
        "dropout": 0.0,
        "rms_norm_eps": 1e-5,
        "rope_theta": 10000.0,
        "activation": "swiglu",
        "attention_bias": False,
        "mlp_bias": False,
        "tie_weights": True,
    },
}

# Alias for convenience
MODEL_PRESETS["3b"] = MODEL_PRESETS["3.7b"]
MODEL_PRESETS["10"] = MODEL_PRESETS["10b"]


# ---------------------------------------------------------------------------
# Configuration dataclasses
# ---------------------------------------------------------------------------
@dataclass
class DistributedConfig:
    """Distributed training configuration."""

    strategy: str = "ddp"
    tensor_parallel_size: int = 1
    pipeline_parallel_size: int = 1
    zero_stage: int = 0
    cpu_offload: bool = False
    fsdp_cpu_offload: bool = False
    fsdp_sharding_strategy: str = "FULL_SHARD"
    find_unused_parameters: bool = False
    gradient_as_bucket_view: bool = True
    broadcast_buffers: bool = True

    def __post_init__(self) -> None:
        strategy = self.strategy.lower().replace("-", "_").replace(" ", "_")
        valid = {
            "ddp",
            "fsdp",
            "zero1",
            "zero2",
            "zero3",
            "zero_1",
            "zero_2",
            "zero_3",
            "tensor_parallel",
            "pipeline_parallel",
            "cpu_offload",
            "none",
        }
        if strategy not in valid:
            raise ValueError(f"Unknown distributed strategy: {self.strategy}. Valid: {sorted(valid)}")
        self.strategy = strategy


@dataclass
class PrecisionConfig:
    """Mixed precision configuration."""

    dtype: str = "none"
    gradient_scaling: bool = True

    def __post_init__(self) -> None:
        dtype = self.dtype.lower().replace("-", "_")
        valid = {"none", "fp16", "bf16", "float16", "bfloat16", "amp"}
        if dtype not in valid:
            raise ValueError(f"Unknown precision dtype: {self.dtype}. Valid: {sorted(valid)}")
        self.dtype = dtype


@dataclass
class CheckpointConfig:
    """Checkpointing configuration."""

    dir: str = "checkpoints"
    interval: int = 500
    keep_last_n: int = 3
    save_safetensors: bool = False
    resume_from: Optional[str] = None


@dataclass
class TrainingConfig:
    """Unified training configuration for large-scale training."""

    # Model
    model_size: str = "1b"
    config_path: Optional[str] = None
    output_dir: str = "output"
    tokenizer_path: str = "tokenizer.json"
    train_file: str = "data/train.txt"
    val_file: Optional[str] = None
    val_ratio: float = 0.05

    # Training hyperparameters
    epochs: int = 1
    batch_size: int = 1
    gradient_accumulation_steps: int = 1
    lr: float = 3e-4
    weight_decay: float = 0.1
    betas: Tuple[float, float] = (0.9, 0.95)
    grad_clip: float = 1.0
    warmup_steps: int = 0
    min_lr: float = 1e-6
    lr_scheduler: str = "cosine"

    # Precision
    precision: PrecisionConfig = field(default_factory=PrecisionConfig)

    # Distributed
    distributed: DistributedConfig = field(default_factory=DistributedConfig)

    # Checkpointing
    checkpoint: CheckpointConfig = field(default_factory=CheckpointConfig)

    # Memory optimization
    gradient_checkpointing: bool = False
    activation_checkpointing: bool = False
    activation_recompute: bool = False

    # Logging
    log_dir: str = "logs"
    experiment_name: Optional[str] = None
    seed: int = 42

    def __post_init__(self) -> None:
        if isinstance(self.precision, dict):
            self.precision = PrecisionConfig(**self.precision)
        if isinstance(self.distributed, dict):
            self.distributed = DistributedConfig(**self.distributed)
        if isinstance(self.checkpoint, dict):
            self.checkpoint = CheckpointConfig(**self.checkpoint)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TrainingConfig":
        nested = {}
        for key in ("precision", "distributed", "checkpoint"):
            if key in data and isinstance(data[key], dict):
                nested[key] = data.pop(key)
        config = cls(**data)
        for key, value in nested.items():
            setattr(config, key, value)
        return config


# ---------------------------------------------------------------------------
# Helper: resolve torch dtype from PrecisionConfig
# ---------------------------------------------------------------------------
def _resolve_dtype(precision: PrecisionConfig, device: torch.device) -> torch.dtype:
    dtype_map = {
        "none": torch.float32,
        "fp16": torch.float16 if device.type == "cuda" else torch.float32,
        "float16": torch.float16 if device.type == "cuda" else torch.float32,
        "bf16": torch.bfloat16 if torch.cuda.is_available() and torch.cuda.get_device_capability()[0] >= 8 else torch.float32,
        "bfloat16": torch.bfloat16 if torch.cuda.is_available() and torch.cuda.get_device_capability()[0] >= 8 else torch.float32,
        "amp": torch.float16 if device.type == "cuda" else torch.float32,
    }
    return dtype_map.get(precision.dtype, torch.float32)


def _should_use_amp(precision: PrecisionConfig, device: torch.device) -> bool:
    return precision.dtype in ("fp16", "float16", "amp") and device.type == "cuda"


# ---------------------------------------------------------------------------
# Core Trainer
# ---------------------------------------------------------------------------
class LargeScaleTrainer:
    """
    Large-scale LLM trainer with support for distributed strategies,
    mixed precision, checkpointing, and metrics tracking.
    """

    def __init__(
        self,
        config: Optional[TrainingConfig] = None,
        config_path: Optional[str] = None,
        model_size: str = "1b",
        **config_overrides: Any,
    ) -> None:
        if config is not None:
            self.config = config
        elif config_path is not None:
            raw = load_config(config_path) if _HELPERS_AVAILABLE else {}
            raw["model_size"] = raw.get("model_size", model_size)
            raw.update(config_overrides)
            self.config = TrainingConfig.from_dict(raw)  # type: ignore[attr-defined]
        else:
            preset = MODEL_PRESETS.get(model_size.lower(), MODEL_PRESETS["1b"])
            preset["model_size"] = model_size
            preset.update(config_overrides)
            self.config = TrainingConfig.from_dict(preset)  # type: ignore[attr-defined]

        if not _HELPERS_AVAILABLE:
            raise RuntimeError("helpers module not available; cannot initialize trainer.")

        self.device = torch.device(get_device())
        if self.device == torch.device("cpu"):
            set_cpu_threads(min(4, os.cpu_count() or 2))

        torch.manual_seed(self.config.seed)
        torch.cuda.manual_seed_all(self.config.seed)

        self.dtype = _resolve_dtype(self.config.precision, self.device)
        self.use_amp = _should_use_amp(self.config.precision, self.device)
        self.scaler = torch.cuda.amp.GradScaler(enabled=self.use_amp)

        self.model: Optional[nn.Module] = None
        self.optimizer: Optional[torch.optim.Optimizer] = None
        self.scheduler: Optional[Any] = None
        self.train_loader: Optional[Any] = None
        self.val_loader: Optional[Any] = None

        self.start_epoch: int = 0
        self.global_step: int = 0
        self.best_val_loss: float = float("inf")
        self.train_log: List[Dict[str, Any]] = []
        self.val_log: List[Dict[str, Any]] = []

        self.memory_profiler = MemoryProfiler(enabled=(self.device.type == "cuda")) if _MEMORY_OPT_AVAILABLE else None
        self.experiment_logger: Optional[Any] = None

        self._initialized = False

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LargeScaleTrainer":
        config = TrainingConfig.from_dict(data)
        return cls(config=config)

    def _init_distributed(self) -> bool:
        if not _DISTRIBUTED_AVAILABLE:
            logger.warning("Distributed training module unavailable; running single-device.")
            return False
        return init_distributed()

    def _build_model(self) -> nn.Module:
        model_cfg = self._get_model_config()
        if _LLM_AVAILABLE and LLM is not None:
            try:
                model = LLM(model_cfg, device=self.device, dtype=self.dtype)
                logger.info("Built model from config.")
                return model
            except RuntimeError as exc:
                if "not enough memory" in str(exc):
                    logger.warning("Insufficient memory; attempting meta-device init.")
                    model = LLM(model_cfg, device=torch.device("meta"), dtype=self.dtype)
                    model.to_empty(self.device)
                    return model
                raise
        raise RuntimeError("LLM model class not available.")

    def _get_model_config(self) -> Dict[str, Any]:
        if self.config.config_path and os.path.exists(self.config.config_path):
            cfg = load_config(self.config.config_path)
        else:
            cfg = dict(MODEL_PRESETS.get(self.config.model_size.lower(), MODEL_PRESETS["1b"]))
        cfg.setdefault("vocab_size", 32000)
        cfg.setdefault("hidden_size", 2048)
        cfg.setdefault("num_hidden_layers", 24)
        cfg.setdefault("num_attention_heads", 32)
        cfg.setdefault("intermediate_size", 8192)
        cfg.setdefault("max_position_embeddings", 2048)
        cfg.setdefault("dropout", 0.0)
        cfg.setdefault("rms_norm_eps", 1e-5)
        cfg.setdefault("rope_theta", 10000.0)
        cfg.setdefault("activation", "swiglu")
        cfg.setdefault("attention_bias", False)
        cfg.setdefault("mlp_bias", False)
        cfg.setdefault("tie_weights", True)
        return cfg

    def _build_dataloaders(self) -> Tuple[Any, Any]:
        if not _TOKENIZER_AVAILABLE:
            raise RuntimeError("Tokenizer module not available.")

        tokenizer = load_tokenizer(self.config.tokenizer_path)
        pad_token_id = tokenizer.token_to_id("<pad>") or 0
        block_size = self._get_model_config().get("max_position_embeddings", 2048)

        train_dataset = TextDataset(self.config.train_file, tokenizer, block_size=block_size)
        n = len(train_dataset)
        g = torch.Generator().manual_seed(self.config.seed)
        indices = torch.randperm(n, generator=g).tolist()
        split = int(n * (1 - self.config.val_ratio))

        from torch.utils.data import Subset, DataLoader

        train_subset = Subset(train_dataset, indices[:split])
        val_subset = Subset(train_dataset, indices[split:])

        train_loader = DataLoader(
            train_subset,
            batch_size=self.config.batch_size,
            shuffle=True,
            num_workers=0,
            pin_memory=(self.device.type == "cuda"),
            collate_fn=lambda b: collate_fn(b, pad_token_id),
            drop_last=True,
        )
        val_loader = DataLoader(
            val_subset,
            batch_size=max(1, self.config.batch_size // 2),
            shuffle=False,
            num_workers=0,
            pin_memory=(self.device.type == "cuda"),
            collate_fn=lambda b: collate_fn(b, pad_token_id),
            drop_last=False,
        )
        return train_loader, val_loader

    def _build_optimizer_and_scheduler(self, dataloader_len: int) -> Tuple[torch.optim.Optimizer, Optional[Any]]:
        if _OPTIMIZERS_AVAILABLE and get_optimizer_and_scheduler is not None:
            cfg = {
                "optimizer": "adamw",
                "lr": self.config.lr,
                "weight_decay": self.config.weight_decay,
                "betas": list(self.config.betas),
                "lr_scheduler": self.config.lr_scheduler,
                "epochs": self.config.epochs,
                "warmup_steps": self.config.warmup_steps,
                "min_lr": self.config.min_lr,
            }
            return get_optimizer_and_scheduler(cfg, self.model, dataloader_len)

        optimizer = torch.optim.AdamW(
            self.model.parameters(),
            lr=self.config.lr,
            betas=self.config.betas,
            weight_decay=self.config.weight_decay,
        )
        total_steps = dataloader_len * self.config.epochs
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
            optimizer, T_max=total_steps, eta_min=self.config.min_lr
        )
        return optimizer, scheduler

    def _wrap_model(self) -> nn.Module:
        if not _DISTRIBUTED_AVAILABLE or not is_distributed():
            return self.model

        strategy = self.config.distributed.strategy
        if strategy in ("zero1", "zero_1"):
            strategy = "fsdp"
        if strategy in ("zero2", "zero_2"):
            strategy = "fsdp"
        if strategy in ("zero3", "zero_3"):
            strategy = "fsdp"

        kwargs: Dict[str, Any] = {}
        if strategy == "fsdp":
            from torch.distributed.fsdp import ShardingStrategy

            strategy_map = {
                "FULL_SHARD": ShardingStrategy.FULL_SHARD,
                "SHARD_GRAD_OP": ShardingStrategy.SHARD_GRAD_OP,
                "NO_SHARD": ShardingStrategy.NO_SHARD,
            }
            sharding = strategy_map.get(
                self.config.distributed.fsdp_sharding_strategy.upper(),
                ShardingStrategy.FULL_SHARD,
            )
            kwargs["cpu_offload"] = self.config.distributed.fsdp_cpu_offload
            kwargs["sharding_strategy"] = sharding
            kwargs["mixed_precision"] = self.dtype if self.dtype in (torch.float16, torch.bfloat16) else torch.float32

        return wrap_model(self.model, strategy, device=self.device, **kwargs)

    def _apply_gradient_checkpointing(self) -> None:
        if self.config.gradient_checkpointing and hasattr(self.model, "blocks"):
            for block in self.model.blocks:
                if hasattr(block, "attn") and hasattr(block.attn, "use_gradient_checkpointing"):
                    block.attn.use_gradient_checkpointing = True
                if hasattr(block, "mlp") and hasattr(block.mlp, "use_gradient_checkpointing"):
                    block.mlp.use_gradient_checkpointing = True

    def _apply_activation_checkpointing(self) -> None:
        if self.config.activation_checkpointing and hasattr(self.model, "blocks"):
            self.model.blocks = nn.ModuleList(
                [SelectiveRecompute(block) for block in self.model.blocks]
            )

    def initialize(self, resume_from: Optional[str] = None) -> None:
        """Initialize model, optimizer, scheduler, and dataloaders."""
        logger.info("Initializing large-scale trainer...")
        logger.info("Model size: %s", self.config.model_size)
        logger.info("Distributed strategy: %s", self.config.distributed.strategy)
        logger.info("Precision: %s", self.config.precision.dtype)

        self._init_distributed()
        self.model = self._build_model()
        self.model = self._wrap_model()
        self._apply_gradient_checkpointing()
        self._apply_activation_checkpointing()

        if _MEMORY_OPT_AVAILABLE and self.memory_profiler:
            self.memory_profiler.snapshot("post_init")

        self.train_loader, self.val_loader = self._build_dataloaders()
        self.optimizer, self.scheduler = self._build_optimizer_and_scheduler(len(self.train_loader))

        if resume_from and os.path.exists(resume_from):
            self._load_checkpoint(resume_from)

        self._log_model_info()
        self._initialized = True

    def _log_model_info(self) -> None:
        if not _LLM_AVAILABLE or self.model is None:
            return
        params = count_parameters(self.model) if count_parameters else sum(p.numel() for p in self.model.parameters())
        mem = self.model.estimate_memory(training=True, dtype_bytes=2 if self.dtype in (torch.float16, torch.bfloat16) else 4)
        logger.info("Parameters: %s (%sB)", f"{params:,}", f"{params/1e9:.2f}")
        logger.info("Estimated memory: weights=%.1fGB, total=%.1fGB", mem.get("weights_gb", 0), mem.get("total_base_gb", 0))
        if is_main_process() if _DISTRIBUTED_AVAILABLE else True:
            logger.info("World size: %s, Rank: %s", get_world_size() if _DISTRIBUTED_AVAILABLE else 1, get_rank() if _DISTRIBUTED_AVAILABLE else 0)

    def _load_checkpoint(self, path: str) -> None:
        if not _CHECKPOINT_AVAILABLE:
            logger.warning("Checkpoint module unavailable; cannot resume.")
            return
        try:
            state = load_checkpoint(self.model, self.optimizer, self.scheduler, path, device=self.device)
            self.start_epoch = state.get("epoch", 0)
            self.best_val_loss = state.get("best_val_loss", float("inf"))
            logger.info("Resumed from checkpoint: %s (epoch=%d)", path, self.start_epoch)
        except Exception as exc:
            logger.error("Failed to load checkpoint %s: %s", path, exc)

    def train_step(self, batch: Dict[str, torch.Tensor]) -> float:
        """Execute a single training step."""
        if self.model is None or self.optimizer is None:
            raise RuntimeError("Trainer not initialized. Call initialize() first.")

        self.model.train()
        self.optimizer.zero_grad(set_to_none=True)

        input_ids = batch["input_ids"].to(self.device, non_blocking=True)
        labels = batch["labels"].to(self.device, non_blocking=True)

        loss = None
        if self.use_amp:
            with torch.cuda.amp.autocast(dtype=self.dtype):
                outputs = self.model(input_ids, labels=labels, use_gradient_checkpointing=self.config.gradient_checkpointing)
                loss = outputs["loss"] / self.config.gradient_accumulation_steps
            self.scaler.scale(loss).backward()
        else:
            outputs = self.model(input_ids, labels=labels, use_gradient_checkpointing=self.config.gradient_checkpointing)
            loss = outputs["loss"] / self.config.gradient_accumulation_steps
            loss.backward()

        self.global_step += 1

        if self.global_step % self.config.gradient_accumulation_steps == 0:
            if self.use_amp:
                if self.config.grad_clip > 0:
                    self.scaler.unscale_(self.optimizer)
                    torch.nn.utils.clip_grad_norm_(self.model.parameters(), self.config.grad_clip)
                self.scaler.step(self.optimizer)
                self.scaler.update()
            else:
                if self.config.grad_clip > 0:
                    torch.nn.utils.clip_grad_norm_(self.model.parameters(), self.config.grad_clip)
                self.optimizer.step()

            if self.scheduler is not None:
                self.scheduler.step()
            self.optimizer.zero_grad(set_to_none=True)

        return loss.item() * self.config.gradient_accumulation_steps

    @torch.no_grad()
    def validate(self, max_batches: Optional[int] = None) -> Dict[str, Any]:
        if self.model is None or self.val_loader is None:
            return {}
        if _METRICS_AVAILABLE and evaluate_metrics is not None:
            return evaluate_metrics(self.model, self.val_loader, self.device, max_batches=max_batches)
        self.model.eval()
        total_loss = 0.0
        total_tokens = 0
        correct = 0
        count = 0
        for batch in self.val_loader:
            input_ids = batch["input_ids"].to(self.device, non_blocking=True)
            labels = batch["labels"].to(self.device, non_blocking=True)
            if self.use_amp:
                with torch.cuda.amp.autocast(dtype=self.dtype):
                    outputs = self.model(input_ids, labels=labels, use_gradient_checkpointing=False)
            else:
                outputs = self.model(input_ids, labels=labels, use_gradient_checkpointing=False)
            loss = outputs["loss"].item()
            logits = outputs["logits"]
            total_loss += loss * labels.numel()
            total_tokens += labels.numel()
            preds = logits.argmax(dim=-1)
            mask = labels != -100
            correct += ((preds == labels) & mask).sum().item()
            count += 1
            if max_batches is not None and count >= max_batches:
                break
        avg_loss = total_loss / max(total_tokens, 1)
        accuracy = correct / max(total_tokens, 1)
        perplexity = compute_perplexity(avg_loss) if _METRICS_AVAILABLE else (math.exp(avg_loss) if avg_loss < 100 else float("inf"))
        return {"loss": avg_loss, "perplexity": perplexity, "accuracy": accuracy, "tokens": total_tokens}

    def train(self, resume_from: Optional[str] = None) -> Dict[str, Any]:
        """Run full training loop."""
        if not self._initialized:
            self.initialize(resume_from=resume_from)

        os.makedirs(self.config.checkpoint.dir, exist_ok=True)
        os.makedirs(self.config.log_dir, exist_ok=True)
        os.makedirs(self.config.output_dir, exist_ok=True)

        if _EXPERIMENT_TRACKER_AVAILABLE and ExperimentLogger is not None:
            self.experiment_logger = ExperimentLogger(self.config.log_dir)

        start_time = time.time()
        accumulation = self.config.gradient_accumulation_steps
        grad_clip = self.config.grad_clip
        ckpt_cfg = self.config.checkpoint

        for epoch in range(self.start_epoch, self.config.epochs):
            epoch_start = time.time()
            self.model.train()
            total_loss = 0.0
            total_tokens = 0
            tokens_per_sec = 0.0
            grad_norm = 0.0

            pbar = None
            if is_main_process() if _DISTRIBUTED_AVAILABLE else True:
                try:
                    from tqdm import tqdm

                    pbar = tqdm(self.train_loader, desc=f"Epoch {epoch+1}/{self.config.epochs}")
                except ImportError:
                    pbar = None

            iterator = self.train_loader if pbar is None else pbar
            for i, batch in enumerate(iterator):
                loss = self.train_step(batch)
                total_loss += loss * accumulation
                total_tokens += batch["labels"].numel()

                if pbar is not None:
                    elapsed = time.time() - epoch_start
                    tokens_per_sec = total_tokens / max(elapsed, 1e-6)
                    grad_norm = self._get_grad_norm()
                    pbar.set_postfix(
                        {
                            "loss": f"{total_loss / max(i+1, 1):.4f}",
                            "tokens/s": f"{tokens_per_sec:.1f}",
                            "grad": f"{grad_norm:.2f}",
                        }
                    )

                if self.memory_profiler:
                    self.memory_profiler.snapshot(f"epoch{epoch}_step{i}")

            train_metrics = {
                "epoch": epoch + 1,
                "train_loss": total_loss / max(len(self.train_loader), 1),
                "tokens": total_tokens,
                "tokens_per_sec": tokens_per_sec,
                "grad_norm": grad_norm,
                "time": time.time() - epoch_start,
            }
            self.train_log.append(train_metrics)

            val_metrics = self.validate()
            self.val_log.append(val_metrics)

            if is_main_process() if _DISTRIBUTED_AVAILABLE else True:
                logger.info(
                    "Epoch %d/%d | Train loss: %.4f | Val loss: %.4f | Val ppl: %.2f | Tokens/s: %.1f",
                    epoch + 1,
                    self.config.epochs,
                    train_metrics["train_loss"],
                    val_metrics.get("loss", float("inf")),
                    val_metrics.get("perplexity", float("inf")),
                    tokens_per_sec,
                )

            if self.experiment_logger:
                self.experiment_logger.log_metrics({**train_metrics, **val_metrics}, step=epoch + 1)

            val_loss = val_metrics.get("loss", float("inf"))
            if val_loss < self.best_val_loss:
                self.best_val_loss = val_loss
                self._save_checkpoint(os.path.join(ckpt_cfg.dir, "best.pt"), epoch)

            if (epoch + 1) % max(1, ckpt_cfg.interval // len(self.train_loader)) == 0 or epoch == self.config.epochs - 1:
                self._save_checkpoint(os.path.join(ckpt_cfg.dir, "latest.pt"), epoch)

            if is_distributed():
                barrier()

        self._cleanup_old_checkpoints(ckpt_cfg.dir, ckpt_cfg.keep_last_n)
        total_time = time.time() - start_time

        if self.memory_profiler:
            self.memory_profiler.log_summary()

        report_path = self._generate_training_report(total_time)
        model_card_path = self._save_model_card(report_path)

        result = {
            "best_val_loss": self.best_val_loss,
            "train_log": self.train_log,
            "val_log": self.val_log,
            "total_time": total_time,
            "report_path": report_path,
            "model_card_path": model_card_path,
        }
        logger.info("Training complete. Best val loss: %.4f", self.best_val_loss)
        return result

    def _get_grad_norm(self) -> float:
        if self.model is None:
            return 0.0
        try:
            total_norm = 0.0
            for p in self.model.parameters():
                if p.grad is not None:
                    total_norm += p.grad.data.norm(2).item() ** 2
            return math.sqrt(total_norm)
        except Exception:
            return 0.0

    def _save_checkpoint(self, filename: str, epoch: int) -> None:
        if not _CHECKPOINT_AVAILABLE or self.model is None or self.optimizer is None:
            return
        try:
            save_checkpoint(
                self.model,
                self.optimizer,
                self.scheduler,
                epoch,
                self.best_val_loss,
                filename,
                config=self._get_model_config(),
                global_step=self.global_step,
            )
        except Exception as exc:
            logger.error("Failed to save checkpoint %s: %s", filename, exc)

    def _cleanup_old_checkpoints(self, directory: str, keep_last_n: int) -> None:
        if not _CHECKPOINT_AVAILABLE:
            return
        try:
            ckpts = list_checkpoints(directory)
            for old in ckpts[:-keep_last_n]:
                if os.path.exists(old):
                    os.remove(old)
        except Exception as exc:
            logger.warning("Failed to cleanup checkpoints: %s", exc)

    def _generate_training_report(self, total_time: float) -> str:
        report = {
            "model_size": self.config.model_size,
            "strategy": self.config.distributed.strategy,
            "precision": self.config.precision.dtype,
            "epochs_completed": len(self.train_log),
            "best_val_loss": self.best_val_loss,
            "total_time_s": total_time,
            "train_log": self.train_log,
            "val_log": self.val_log,
            "config": self._get_model_config(),
            "timestamp": datetime.now().isoformat(),
        }
        report_path = os.path.join(self.config.log_dir, f"{self.config.model_size}_training_report.json")
        os.makedirs(self.config.log_dir, exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, default=str)
        logger.info("Training report saved to %s", report_path)
        return report_path

    def _save_model_card(self, report_path: str) -> str:
        model_card = f"""---
language: en
license: apache-2.0
tags:
  - llm
  - {self.config.model_size}
  - astrovox-ai
---

# Astrovox AI {self.config.model_size.upper()} Model

## Model Details
- **Model Size**: {self.config.model_size.upper()}
- **Parameters**: {count_parameters(self.model) if self.model is not None and count_parameters else 'N/A':,}
- **Architecture**: Transformer (RoPE, SwiGLU, RMSNorm)
- **Training Precision**: {self.config.precision.dtype}
- **Distributed Strategy**: {self.config.distributed.strategy}
- **Vocabulary Size**: {self._get_model_config().get('vocab_size', 32000)}

## Training Summary
- **Best Validation Loss**: {self.best_val_loss:.4f}
- **Epochs**: {len(self.train_log)}
- **Gradient Checkpointing**: {self.config.gradient_checkpointing}
- **Activation Checkpointing**: {self.config.activation_checkpointing}

## Usage
```python
from models.llm.model.model import LLM
model = LLM.from_pretrained("{self.config.output_dir}")
```

## Training Report
See `{report_path}` for detailed training metrics.

## Limitations
- Model trained on synthetic or limited data
- May exhibit hallucinations or biased outputs
- Requires further evaluation for production use
"""
        model_card_path = os.path.join(self.config.output_dir, "MODEL_CARD.md")
        os.makedirs(self.config.output_dir, exist_ok=True)
        with open(model_card_path, "w", encoding="utf-8") as f:
            f.write(model_card)
        logger.info("Model card saved to %s", model_card_path)
        return model_card_path

    def cleanup(self) -> None:
        if _DISTRIBUTED_AVAILABLE:
            destroy_distributed()
        if self.experiment_logger:
            try:
                self.experiment_logger.close()
            except Exception:
                pass
        gc.collect()
        torch.cuda.empty_cache()


# ---------------------------------------------------------------------------
# Training entry point
# ---------------------------------------------------------------------------
def train_large_scale(
    model_size: str = "1b",
    config_path: Optional[str] = None,
    resume_from: Optional[str] = None,
    output_dir: str = "output",
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    High-level entry point for large-scale training.

    Args:
        model_size: One of '1b', '3.7b', '10b'.
        config_path: Optional YAML config path. Overrides model_size preset.
        resume_from: Optional checkpoint path to resume from.
        output_dir: Directory to save outputs.
        **kwargs: Overrides for TrainingConfig fields.

    Returns:
        Training result dict with best_val_loss, logs, report paths, etc.
    """
    config = TrainingConfig(
        model_size=model_size,
        config_path=config_path,
        output_dir=output_dir,
        **kwargs,
    )
    trainer = LargeScaleTrainer(config=config)
    try:
        return trainer.train(resume_from=resume_from)
    finally:
        trainer.cleanup()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Phase K Large-Scale LLM Training",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--model-size", type=str, default="1b", choices=list(MODEL_PRESETS.keys()))
    parser.add_argument("--config", type=str, default=None, help="Path to YAML config")
    parser.add_argument("--resume", type=str, default=None, help="Checkpoint path to resume from")
    parser.add_argument("--output-dir", type=str, default="output")
    parser.add_argument("--epochs", type=int, default=None)
    parser.add_argument("--batch-size", type=int, default=None)
    parser.add_argument("--lr", type=float, default=None)
    parser.add_argument("--gradient-accumulation-steps", type=int, default=None)
    parser.add_argument("--mixed-precision", type=str, default=None, choices=["none", "fp16", "bf16", "amp"])
    parser.add_argument("--strategy", type=str, default="ddp", choices=["ddp", "fsdp", "zero1", "zero2", "zero3", "tensor_parallel", "pipeline_parallel", "none"])
    parser.add_argument("--gradient-checkpointing", action="store_true", default=None)
    parser.add_argument("--activation-checkpointing", action="store_true", default=None)
    parser.add_argument("--grad-clip", type=float, default=None)
    parser.add_argument("--warmup-steps", type=int, default=None)
    parser.add_argument("--checkpoint-dir", type=str, default="checkpoints")
    parser.add_argument("--checkpoint-interval", type=int, default=500)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--local_rank", type=int, default=int(os.environ.get("LOCAL_RANK", 0)), help=argparse.SUPPRESS)

    args = parser.parse_args(argv)

    kwargs: Dict[str, Any] = {}
    for field_name in ["epochs", "batch_size", "lr", "gradient_accumulation_steps", "grad_clip", "warmup_steps", "seed"]:
        val = getattr(args, field_name.replace("-", "_"), None)
        if val is not None:
            kwargs[field_name] = val

    if args.mixed_precision is not None:
        kwargs["precision"] = {"dtype": args.mixed_precision}
    if args.strategy is not None:
        kwargs["distributed"] = {"strategy": args.strategy}
    if args.gradient_checkpointing is not None:
        kwargs["gradient_checkpointing"] = args.gradient_checkpointing
    if args.activation_checkpointing is not None:
        kwargs["activation_checkpointing"] = args.activation_checkpointing

    try:
        result = train_large_scale(
            model_size=args.model_size,
            config_path=args.config,
            resume_from=args.resume,
            output_dir=args.output_dir,
            **kwargs,
        )
        logger.info("Training finished. Best val loss: %.4f", result.get("best_val_loss", float("inf")))
        return 0
    except Exception as exc:
        logger.error("Training failed: %s", exc, exc_info=True)
        return 1


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    sys.exit(main())
