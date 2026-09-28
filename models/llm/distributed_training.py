"""
Phase 3 Distributed Training Module
=====================================

Provides a unified interface for distributed training strategies.
The implementation lives in ``models.llm.training.distributed``;
this module re-exports everything for backward compatibility.
"""

import contextlib
import logging
import os
import warnings
from enum import StrEnum
from typing import Any

import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset

logger = logging.getLogger(__name__)

from models.llm.training.distributed import (
    DDPWrapper,
    FSDPWrapper,
    ZeROConfig,
    ZeROOptimizer,
    TensorParallelWrapper,
    PipelineParallelWrapper,
    SequenceParallelWrapper,
    ContextParallelWrapper,
    ElasticConfig,
    ElasticTrainer,
    save_sharded_checkpoint,
    load_sharded_checkpoint,
    async_save_sharded_checkpoint,
    verify_checkpoint,
    setup_multi_node,
    synchronize_gradients,
)


class DistributedStrategy(StrEnum):
    DDP = "ddp"
    FSDP = "fsdp"
    ZERO_1 = "zero1"
    ZERO_2 = "zero2"
    ZERO_3 = "zero3"
    TENSOR_PARALLEL = "tensor_parallel"
    PIPELINE_PARALLEL = "pipeline_parallel"
    SEQUENCE_PARALLEL = "sequence_parallel"
    CPU_OFFLOAD = "cpu_offload"


def get_rank() -> int:
    return int(os.environ.get("RANK", os.environ.get("LOCAL_RANK", "0")))


def get_world_size() -> int:
    return int(os.environ.get("WORLD_SIZE", "1"))


def get_local_rank() -> int:
    return int(os.environ.get("LOCAL_RANK", get_rank()))


def get_num_gpus() -> int:
    return torch.cuda.device_count() if torch.cuda.is_available() else 0


def is_main_process() -> bool:
    return get_rank() == 0


def barrier() -> None:
    if is_distributed() and torch.distributed.is_initialized():
        torch.distributed.barrier()


def is_distributed() -> bool:
    return get_world_size() > 1


def log_memory_usage(prefix: str = "") -> None:
    rank = get_rank()
    if torch.cuda.is_available():
        allocated = torch.cuda.memory_allocated(rank) / (1024**2)
        reserved = torch.cuda.memory_reserved(rank) / (1024**2)
        logger.info(
            "%s[Rank %d] CUDA Memory: %.2f MB allocated, %.2f MB reserved",
            prefix,
            rank,
            allocated,
            reserved,
        )
    else:
        logger.debug("%s[Rank %d] CUDA not available.", prefix, rank)


def log_model_memory(model: nn.Module, prefix: str = "") -> None:
    rank = get_rank()
    param_mem = sum(p.numel() * p.element_size() for p in model.parameters()) / (1024**2)
    buffer_mem = sum(b.numel() * b.element_size() for b in model.buffers()) / (1024**2)
    logger.info(
        "%s[Rank %d] Model Memory: %.2f MB parameters, %.2f MB buffers",
        prefix,
        rank,
        param_mem,
        buffer_mem,
    )


def init_distributed(backend: str = "nccl", init_method: str | None = None) -> bool:
    if is_distributed():
        if not torch.distributed.is_initialized():
            if init_method is None:
                init_method = "env://"
            try:
                torch.distributed.init_process_group(backend=backend, init_method=init_method)
                logger.info(
                    "Initialized distributed process group: backend=%s, rank=%d, world_size=%d",
                    backend,
                    get_rank(),
                    get_world_size(),
                )
                return True
            except Exception as exc:
                warnings.warn(f"Failed to initialize distributed: {exc}", stacklevel=2)
                return False
    return False


def destroy_distributed() -> None:
    if torch.distributed.is_initialized():
        with contextlib.suppress(Exception):
            torch.distributed.destroy_process_group()


def wrap_model_ddp(
    model: nn.Module,
    device_ids: list | None = None,
    output_device: int | None = None,
    find_unused_parameters: bool = False,
    gradient_as_bucket_view: bool = True,
) -> nn.Module:
    if not is_distributed() or not torch.distributed.is_initialized():
        return model
    device_ids = device_ids or [get_local_rank()]
    output_device = output_device if output_device is not None else get_local_rank()
    model = nn.parallel.DistributedDataParallel(
        model,
        device_ids=device_ids,
        output_device=output_device,
        find_unused_parameters=find_unused_parameters,
        gradient_as_bucket_view=gradient_as_bucket_view,
    )
    return model


def wrap_model_fsdp(
    model: nn.Module,
    cpu_offload: bool = False,
    mixed_precision: torch.dtype | None = None,
    auto_wrap_policy: Any | None = None,
    sharding_strategy: Any | None = None,
) -> nn.Module:
    if not is_distributed() or not torch.distributed.is_initialized():
        return model
    try:
        from torch.distributed.fsdp import BackwardPrefetch, MixedPrecision, ShardingStrategy
        from torch.distributed.fsdp import FullyShardedDataParallel as FSDP
    except ImportError:
        warnings.warn("FSDP is unavailable; falling back to single-device model.", stacklevel=2)
        return model

    mp = MixedPrecision(
        param_dtype=mixed_precision or torch.float16,
        reduce_dtype=mixed_precision or torch.float16,
        buffer_dtype=torch.float32,
    )
    strategy = sharding_strategy or ShardingStrategy.FULL_SHARD
    model = FSDP(
        model,
        cpu_offload=cpu_offload,
        mixed_precision=mp,
        auto_wrap_policy=auto_wrap_policy,
        sharding_strategy=strategy,
        backward_prefetch=BackwardPrefetch.BACKWARD_PRE,
    )
    return model


def _zero3_wrap(model: nn.Module, cpu_offload: bool = False) -> nn.Module:
    return wrap_model_fsdp(
        model,
        cpu_offload=cpu_offload,
        sharding_strategy=torch.distributed.fsdp.ShardingStrategy.FULL_SHARD,
    )


def _zero2_wrap(model: nn.Module, cpu_offload: bool = False) -> nn.Module:
    return wrap_model_fsdp(
        model,
        cpu_offload=cpu_offload,
        sharding_strategy=torch.distributed.fsdp.ShardingStrategy.SHARD_GRAD_OP,
    )


def _zero1_wrap(model: nn.Module) -> nn.Module:
    return wrap_model_fsdp(
        model, sharding_strategy=torch.distributed.fsdp.ShardingStrategy.NO_SHARD
    )


def wrap_model_tensor_parallel(
    model: nn.Module,
    tp_size: int = 2,
    device: torch.device | None = None,
) -> nn.Module:
    device = device or torch.device("cuda" if torch.cuda.is_available() else "cpu")
    try:
        from torch.distributed.tensor.parallel import (
            ColwiseParallel,
            RowwiseParallel,
            parallelize_module,
        )

        tp_mesh = torch.distributed.device_mesh.init_device_mesh(device.type, (tp_size,))
        model = parallelize_module(model, tp_mesh, {"": ColwiseParallel(), "": RowwiseParallel()})
        return model
    except Exception:
        warnings.warn(
            "Tensor parallelism unavailable or failed; returning unwrapped model.", stacklevel=2
        )
        return model


def wrap_model_pipeline_parallel(
    model: nn.Module,
    pp_size: int = 2,
    chunks: int | None = None,
) -> nn.Module:
    try:
        from torch.distributed.pipeline.sync import Pipe

        chunks = chunks or pp_size
        model = Pipe(model, chunks=chunks)
        return model
    except Exception:
        warnings.warn(
            "Pipeline parallelism unavailable or failed; returning unwrapped model.", stacklevel=2
        )
        return model


def wrap_model_sequence_parallel(
    model: nn.Module,
    sp_size: int = 2,
) -> nn.Module:
    try:
        from torch.distributed.sequence_parallel import SequenceParallel

        model = SequenceParallel(model, process_group=None)
        return model
    except Exception:
        warnings.warn(
            "Sequence parallelism unavailable or failed; returning unwrapped model.", stacklevel=2
        )
        return model


def wrap_model_cpu_offload(
    model: nn.Module,
    device: torch.device,
) -> nn.Module:
    if not torch.cuda.is_available():
        return model
    model = model.to(device)
    if hasattr(torch, "cpu") and hasattr(model, "cpu"):
        pass
    try:
        from accelerate import cpu_offload, init_empty_weights

        with init_empty_weights():
            pass
        model = cpu_offload(model, device)
        return model
    except Exception:
        warnings.warn(
            "CPU offload via accelerate unavailable; returning model on target device.",
            stacklevel=2,
        )
        return model.to(device)


def wrap_model(
    model: nn.Module,
    strategy: DistributedStrategy | str,
    device: torch.device | None = None,
    **kwargs: Any,
) -> nn.Module:
    if isinstance(strategy, str):
        strategy = DistributedStrategy(strategy.lower())

    device = device or torch.device("cuda" if torch.cuda.is_available() else "cpu")

    if strategy == DistributedStrategy.DDP:
        return wrap_model_ddp(model, **kwargs)
    if strategy == DistributedStrategy.FSDP:
        return wrap_model_fsdp(model, **kwargs)
    if strategy == DistributedStrategy.ZERO_3:
        return _zero3_wrap(model, **kwargs)
    if strategy == DistributedStrategy.ZERO_2:
        return _zero2_wrap(model, **kwargs)
    if strategy == DistributedStrategy.ZERO_1:
        return _zero1_wrap(model, **kwargs)
    if strategy == DistributedStrategy.TENSOR_PARALLEL:
        return wrap_model_tensor_parallel(model, **kwargs)
    if strategy == DistributedStrategy.PIPELINE_PARALLEL:
        return wrap_model_pipeline_parallel(model, **kwargs)
    if strategy == DistributedStrategy.SEQUENCE_PARALLEL:
        return wrap_model_sequence_parallel(model, **kwargs)
    if strategy == DistributedStrategy.CPU_OFFLOAD:
        return wrap_model_cpu_offload(model, device, **kwargs)
    warnings.warn(f"Unknown strategy: {strategy}; returning unwrapped model.", stacklevel=2)
    return model


def add_gradient_sync_hooks(model: nn.Module) -> None:
    def _sync(grad):
        if is_distributed() and torch.distributed.is_initialized():
            with contextlib.suppress(Exception):
                torch.distributed.all_reduce(grad, op=torch.distributed.ReduceOp.SUM)
        return grad

    for p in model.parameters():
        if p.requires_grad:
            p.register_hook(_sync)


def remove_gradient_sync_hooks(model: nn.Module) -> None:
    for p in model.parameters():
        if hasattr(p, "_grad_sync_hook"):
            with contextlib.suppress(Exception):
                p._grad_sync_hook.remove()


def create_distributed_dataloader(
    dataset: Dataset,
    batch_size: int = 1,
    shuffle: bool = False,
    num_workers: int = 0,
    pin_memory: bool = True,
    drop_last: bool = True,
) -> DataLoader:
    sampler = None
    if is_distributed():
        try:
            sampler = torch.utils.data.distributed.DistributedSampler(dataset, shuffle=shuffle)
        except Exception:
            warnings.warn("DistributedSampler unavailable; using default sampler.", stacklevel=2)
            shuffle = False
    loader = DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=(shuffle and sampler is None),
        sampler=sampler,
        num_workers=num_workers,
        pin_memory=pin_memory,
        drop_last=drop_last,
    )
    return loader


def save_distributed_checkpoint(
    path: str,
    model: nn.Module,
    optimizer: torch.optim.Optimizer | None = None,
    scheduler: Any | None = None,
    epoch: int = 0,
    best_val_loss: float = float("inf"),
    config: dict[str, Any] | None = None,
    strategy: DistributedStrategy | str = DistributedStrategy.DDP,
    use_safetensors: bool = False,
) -> None:
    if is_main_process():
        os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)

    state = {
        "epoch": epoch,
        "best_val_loss": best_val_loss,
        "timestamp": torch.tensor(0).float().cpu().item(),
        "config": config,
    }

    try:
        state["model_state_dict"] = (
            model.module.state_dict() if hasattr(model, "module") else model.state_dict()
        )
    except Exception as exc:
        warnings.warn(f"Could not serialize model state: {exc}", stacklevel=2)
        state["model_state_dict"] = {}

    if optimizer is not None:
        try:
            state["optimizer_state_dict"] = optimizer.state_dict()
        except Exception as exc:
            warnings.warn(f"Could not serialize optimizer state: {exc}", stacklevel=2)
            state["optimizer_state_dict"] = {}

    if scheduler is not None:
        try:
            state["scheduler_state_dict"] = scheduler.state_dict()
        except Exception as exc:
            warnings.warn(f"Could not serialize scheduler state: {exc}", stacklevel=2)
            state["scheduler_state_dict"] = {}

    if is_main_process():
        if use_safetensors:
            try:
                from safetensors.torch import save_file

                save_file({k: v for k, v in state.items() if torch.is_tensor(v)}, path)
                logger.info("Saved distributed checkpoint (safetensors): %s", path)
            except Exception as exc:
                warnings.warn(
                    f"safetensors save failed: {exc}; falling back to torch.save.", stacklevel=2
                )
                torch.save(state, path)
        else:
            torch.save(state, path)
            logger.info("Saved distributed checkpoint: %s", path)

    barrier()


def load_distributed_checkpoint(
    path: str,
    model: nn.Module,
    optimizer: torch.optim.Optimizer | None = None,
    scheduler: Any | None = None,
    device: torch.device | None = None,
    strategy: DistributedStrategy | str = DistributedStrategy.DDP,
    strict: bool = True,
) -> dict[str, Any]:
    device = device or torch.device("cpu")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Checkpoint not found: {path}")

    if path.endswith(".safetensors"):
        try:
            from safetensors.torch import load_file

            state = load_file(path)
        except Exception as exc:
            raise RuntimeError(f"Failed to load safetensors checkpoint: {exc}")
    else:
        state = torch.load(path, map_location=device, weights_only=False)

    model_state = state.get("model_state_dict", {})
    target_model = model.module if hasattr(model, "module") else model
    missing_keys, unexpected_keys = target_model.load_state_dict(model_state, strict=strict)
    if missing_keys or unexpected_keys:
        warnings.warn(
            f"Missing keys: {missing_keys}, Unexpected keys: {unexpected_keys}", stacklevel=2
        )

    if optimizer is not None and state.get("optimizer_state_dict"):
        try:
            optimizer.load_state_dict(state["optimizer_state_dict"])
        except Exception as exc:
            warnings.warn(f"Failed to load optimizer state: {exc}", stacklevel=2)

    if scheduler is not None and state.get("scheduler_state_dict"):
        try:
            scheduler.load_state_dict(state["scheduler_state_dict"])
        except Exception as exc:
            warnings.warn(f"Failed to load scheduler state: {exc}", stacklevel=2)

    barrier()
    return {
        "epoch": state.get("epoch", 0),
        "best_val_loss": state.get("best_val_loss", float("inf")),
        "config": state.get("config"),
    }


class SingleDeviceTrainer:
    def __init__(
        self,
        model: nn.Module,
        optimizer: torch.optim.Optimizer,
        scheduler: Any | None = None,
        device: torch.device | None = None,
    ):
        self.model = model
        self.optimizer = optimizer
        self.scheduler = scheduler
        self.device = device or torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)
        self.scaler = torch.cuda.amp.GradScaler() if self.device.type == "cuda" else None
        logger.warning(
            "Running in single-device fallback mode (rank=%d, world_size=%d).",
            get_rank(),
            get_world_size(),
        )

    def train_step(self, batch: Any, criterion: nn.Module) -> float:
        self.model.train()
        self.optimizer.zero_grad(set_to_none=True)
        with torch.autocast(
            device_type=self.device.type, dtype=torch.float16, enabled=self.device.type == "cuda"
        ):
            outputs = self.model(batch)
            loss = criterion(outputs, batch["target"])
        if self.scaler is not None:
            self.scaler.scale(loss).backward()
            self.scaler.step(self.optimizer)
            self.scaler.update()
        else:
            loss.backward()
            self.optimizer.step()
        if self.scheduler is not None:
            self.scheduler.step()
        return loss.item()


class DistributedTrainer:
    def __init__(
        self,
        model: nn.Module,
        optimizer: torch.optim.Optimizer,
        scheduler: Any | None = None,
        strategy: DistributedStrategy | str = DistributedStrategy.DDP,
        device: torch.device | None = None,
        checkpoint_dir: str = "checkpoints",
        use_amp: bool = True,
        max_grad_norm: float = 1.0,
        cpu_offload: bool = False,
        gradient_accumulation_steps: int = 1,
    ):
        self.strategy = DistributedStrategy(strategy) if isinstance(strategy, str) else strategy
        self.device = device or torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.checkpoint_dir = checkpoint_dir
        self.use_amp = use_amp and self.device.type == "cuda"
        self.max_grad_norm = max_grad_norm
        self.cpu_offload = cpu_offload
        self.gradient_accumulation_steps = max(1, gradient_accumulation_steps)
        self.step_count = 0

        self._is_distributed = init_distributed()
        if not self._is_distributed:
            logger.warning("Distributed mode not initialized; using single-device fallback.")

        self.model = model.to(self.device)
        self.optimizer = optimizer
        self.scheduler = scheduler
        self.scaler = torch.cuda.amp.GradScaler(enabled=self.use_amp)

        self.model = wrap_model(
            self.model, self.strategy, device=self.device, cpu_offload=self.cpu_offload
        )
        if self._is_distributed:
            add_gradient_sync_hooks(self.model)

    def train_step(self, batch: Any, criterion: nn.Module) -> float:
        self.model.train()
        self.optimizer.zero_grad(set_to_none=True)
        with torch.autocast(
            device_type=self.device.type, dtype=torch.float16, enabled=self.use_amp
        ):
            outputs = self.model(batch)
            loss = criterion(outputs, batch["target"])
        loss = loss / self.gradient_accumulation_steps
        if self.scaler is not None:
            self.scaler.scale(loss).backward()
        else:
            loss.backward()

        self.step_count += 1
        if self.step_count % self.gradient_accumulation_steps == 0:
            if self.scaler is not None:
                if self.max_grad_norm > 0:
                    self.scaler.unscale_(self.optimizer)
                    torch.nn.utils.clip_grad_norm_(self.model.parameters(), self.max_grad_norm)
                self.scaler.step(self.optimizer)
                self.scaler.update()
            else:
                if self.max_grad_norm > 0:
                    torch.nn.utils.clip_grad_norm_(self.model.parameters(), self.max_grad_norm)
                self.optimizer.step()
            if self.scheduler is not None:
                self.scheduler.step()
            self.optimizer.zero_grad(set_to_none=True)
        return loss.item() * self.gradient_accumulation_steps

    def save_checkpoint(
        self, filename: str = "checkpoint.pt", use_safetensors: bool = False
    ) -> None:
        path = os.path.join(self.checkpoint_dir, filename)
        save_distributed_checkpoint(
            path=path,
            model=self.model,
            optimizer=self.optimizer,
            scheduler=self.scheduler,
            config=getattr(self, "_config", None),
            strategy=self.strategy,
            use_safetensors=use_safetensors,
        )

    def load_checkpoint(
        self, filename: str = "checkpoint.pt", strict: bool = True
    ) -> dict[str, Any]:
        path = os.path.join(self.checkpoint_dir, filename)
        return load_distributed_checkpoint(
            path=path,
            model=self.model,
            optimizer=self.optimizer,
            scheduler=self.scheduler,
            strategy=self.strategy,
            strict=strict,
        )

    def cleanup(self) -> None:
        remove_gradient_sync_hooks(self.model)
        destroy_distributed()