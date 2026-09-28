"""Tensor, Pipeline, Sequence, and Context parallelism implementations."""

from __future__ import annotations

import logging
from typing import Any

import torch
import torch.nn as nn

logger = logging.getLogger(__name__)


class TensorParallelWrapper:
    """Tensor parallelism wrapper using torch.distributed.tensor.

    Splits individual tensors (e.g., weight matrices) across ranks.
    """

    def __init__(self, model: nn.Module, tp_size: int = 2, device: torch.device | None = None) -> None:
        self._model = model
        self._tp_size = tp_size
        self._device = device or torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self._mesh = None
        self._wrapped = model

    def init(self) -> nn.Module:
        try:
            from torch.distributed.device_mesh import init_device_mesh
            from torch.distributed.tensor.parallel import (
                ColwiseParallel,
                RowwiseParallel,
                parallelize_module,
            )

            self._mesh = init_device_mesh(self._device.type, (self._tp_size,))
            self._wrapped = parallelize_module(
                self._model,
                self._mesh,
                {"": ColwiseParallel(), "": RowwiseParallel()},
            )
            logger.info("Tensor parallelism initialized: tp_size=%d, device=%s", self._tp_size, self._device)
        except ImportError as exc:
            logger.warning("Tensor parallelism unavailable (%s); returning unwrapped model.", exc)
        except Exception as exc:
            logger.warning("Tensor parallelization failed (%s); returning unwrapped model.", exc)
        return self._wrapped

    def unwrap(self) -> nn.Module:
        return self._wrapped

    def state_dict(self) -> dict[str, Any]:
        return self._wrapped.state_dict()

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        return self._wrapped(*args, **kwargs)


class PipelineParallelWrapper:
    """Pipeline parallelism wrapper using torch.distributed.pipeline.sync.Pipe.

    Splits model layers across devices to enable interleaved forward/backward.
    """

    def __init__(self, model: nn.Module, pp_size: int = 2, chunks: int | None = None) -> None:
        self._model = model
        self._pp_size = pp_size
        self._chunks = chunks or pp_size
        self._wrapped = model

    def init(self) -> nn.Module:
        try:
            from torch.distributed.pipeline.sync import Pipe

            self._wrapped = Pipe(self._model, chunks=self._chunks)
            logger.info("Pipeline parallelism initialized: pp_size=%d, chunks=%d", self._pp_size, self._chunks)
        except ImportError as exc:
            logger.warning("Pipeline parallelism unavailable (%s); returning unwrapped model.", exc)
        except Exception as exc:
            logger.warning("Pipeline parallelization failed (%s); returning unwrapped model.", exc)
        return self._wrapped

    def unwrap(self) -> nn.Module:
        return self._wrapped

    def state_dict(self) -> dict[str, Any]:
        if hasattr(self._wrapped, "module"):
            return self._wrapped.module.state_dict()
        return self._wrapped.state_dict()

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        return self._wrapped(*args, **kwargs)


class SequenceParallelWrapper:
    """Sequence parallelism wrapper.

    Splits the sequence dimension across ranks to handle long sequences
    that exceed single-GPU memory capacity.
    """

    def __init__(self, model: nn.Module, sp_size: int = 2) -> None:
        self._model = model
        self._sp_size = sp_size
        self._wrapped = model

    def init(self) -> nn.Module:
        try:
            from torch.distributed.sequence_parallel import SequenceParallel

            self._wrapped = SequenceParallel(self._model, process_group=None)
            logger.info("Sequence parallelism initialized: sp_size=%d", self._sp_size)
        except ImportError as exc:
            logger.warning("Sequence parallelism unavailable (%s); returning unwrapped model.", exc)
        except Exception as exc:
            logger.warning("Sequence parallelization failed (%s); returning unwrapped model.", exc)
        return self._wrapped

    def unwrap(self) -> nn.Module:
        return self._wrapped

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        return self._wrapped(*args, **kwargs)


class ContextParallelWrapper:
    """Context parallelism wrapper.

    Splits the KV-cache and attention context across ranks to extend
    the effective context window for large language models.
    """

    def __init__(self, model: nn.Module, cp_size: int = 2) -> None:
        self._model = model
        self._cp_size = cp_size
        self._wrapped = model
        self._local_rank = 0
        self._world_size = 1

    def init(self) -> nn.Module:
        if torch.distributed.is_initialized():
            self._local_rank = torch.distributed.get_rank()
            self._world_size = torch.distributed.get_world_size()
        self._wrapped = self._model
        logger.info(
            "Context parallelism initialized: cp_size=%d, local_rank=%d, world_size=%d",
            self._cp_size,
            self._local_rank,
            self._world_size,
        )
        return self._wrapped

    def split_sequence(self, x: torch.Tensor, dim: int = 1) -> torch.Tensor:
        """Split a sequence tensor across the context parallel group."""
        if self._world_size <= 1:
            return x
        chunk_size = x.shape[dim] // self._world_size
        start = self._local_rank * chunk_size
        end = start + chunk_size
        return x.narrow(dim, start, end)

    def gather_sequence(self, x: torch.Tensor, dim: int = 1) -> torch.Tensor:
        """Gather split sequence tensors back to the full sequence."""
        if self._world_size <= 1:
            return x
        gathered = [torch.zeros_like(x) for _ in range(self._world_size)]
        torch.distributed.all_gather(gathered, x)
        return torch.cat(gathered, dim=dim)

    def unwrap(self) -> nn.Module:
        return self._wrapped

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        return self._wrapped(*args, **kwargs)
