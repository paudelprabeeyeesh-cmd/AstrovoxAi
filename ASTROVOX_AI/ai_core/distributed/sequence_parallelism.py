"""Sequence parallelism: split sequence dimension across ranks."""

from __future__ import annotations

import logging
from dataclasses import dataclass

import torch
import torch.nn as nn
import torch.distributed as dist

logger = logging.getLogger(__name__)


@dataclass
class SequenceParallelConfig:
    world_size: int = 1
    rank: int = 0
    seq_dim: int = 1


class SequenceParallelism:
    def __init__(self, config: SequenceParallelConfig):
        self.config = config
        self.world_size = config.world_size
        self.rank = config.rank
        self.seq_dim = config.seq_dim

    def split_input(self, input_tensor: torch.Tensor) -> torch.Tensor:
        total_seq = input_tensor.shape[self.seq_dim]
        assert total_seq % self.world_size == 0, "Sequence length must be divisible by SP size"
        chunk_size = total_seq // self.world_size
        start = self.rank * chunk_size
        end = start + chunk_size
        if self.seq_dim == 1:
            return input_tensor[:, start:end, :].contiguous()
        return input_tensor.narrow(self.seq_dim, start, chunk_size).contiguous()

    def gather_output(self, local_output: torch.Tensor, dim: int = -1) -> torch.Tensor:
        if self.world_size <= 1:
            return local_output
        gathered = [torch.zeros_like(local_output) for _ in range(self.world_size)]
        dist.all_gather(gathered, local_output)
        return torch.cat(gathered, dim=dim)

    def all_reduce_sequence(self, tensor: torch.Tensor) -> torch.Tensor:
        if self.world_size <= 1:
            return tensor
        dist.all_reduce(tensor, op=dist.ReduceOp.SUM)
        return tensor

    def scatter_sequence(self, tensor: torch.Tensor, dim: int = 1) -> torch.Tensor:
        total = tensor.shape[dim]
        chunk = total // self.world_size
        start = self.rank * chunk
        end = start + chunk
        return tensor.narrow(dim, start, end).contiguous()

    def apply_to_attention(self, attention: nn.Module, seq_dim: int = 1) -> None:
        if not hasattr(attention, "forward"):
            return
        orig_forward = attention.forward
        sp = self

        def wrapped_forward(*args, **kwargs):
            if args:
                args_list = list(args)
                args_list[0] = sp.split_input(args_list[0])
                args = tuple(args_list)
            elif "hidden_states" in kwargs:
                kwargs["hidden_states"] = sp.split_input(
                    kwargs["hidden_states"]
                )
            out = orig_forward(*args, **kwargs)
            if isinstance(out, tuple):
                return (sp.gather_output(out[0]),) + out[1:]
            return sp.gather_output(out)

        attention.forward = wrapped_forward
