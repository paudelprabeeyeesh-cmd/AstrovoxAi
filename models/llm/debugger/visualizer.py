from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import numpy as np
import torch
import torch.nn as nn

logger = logging.getLogger(__name__)


@dataclass
class AttentionMapData:
    layer: int
    head: int
    sequence_length: int
    num_heads: int
    attention_scores: list[list[float]]


@dataclass
class KVCacheData:
    layer: int
    key_blocks: list[dict[str, Any]]
    value_blocks: list[dict[str, Any]]
    max_blocks: int
    used_blocks: int


@dataclass
class HiddenStateData:
    layer: int
    shape: tuple[int, int, int]
    norm: float
    mean: float
    std: float
    layer_norm: list[list[float]]


@dataclass
class GradientFlowData:
    layer: int
    parameter: str
    norm: float
    mean_abs: float
    max_abs: float


class AttentionMapVisualizer:
    def capture(self, attention_scores: torch.Tensor, layer: int, head: int) -> AttentionMapData:
        scores = attention_scores.detach().cpu()
        seq_len, num_heads = scores.size(-2), scores.size(-1)
        scores_np = scores.numpy()
        head_scores = scores_np[0, head] if scores.dim() == 3 else scores_np[0, 0]
        return AttentionMapData(
            layer=layer,
            head=head,
            sequence_length=seq_len,
            num_heads=num_heads,
            attention_scores=head_scores.tolist(),
        )

    def to_dict(self, data: AttentionMapData) -> dict[str, Any]:
        return {
            "type": "attention_map",
            "layer": data.layer,
            "head": data.head,
            "sequence_length": data.sequence_length,
            "num_heads": data.num_heads,
            "attention_scores": data.attention_scores,
        }


class KVCacheVisualizer:
    def capture(self, kv_cache: Any, layer: int) -> KVCacheData:
        key_blocks = []
        value_blocks = []
        max_blocks = getattr(kv_cache, "max_blocks", 0)
        used_blocks = len(getattr(kv_cache, "free_blocks", []))
        for i, block in enumerate(getattr(kv_cache, "key_blocks", [])[:max_blocks]):
            key_blocks.append({"block_id": i, "shape": list(block.shape)})
        for i, block in enumerate(getattr(kv_cache, "value_blocks", [])[:max_blocks]):
            value_blocks.append({"block_id": i, "shape": list(block.shape)})
        return KVCacheData(
            layer=layer,
            key_blocks=key_blocks,
            value_blocks=value_blocks,
            max_blocks=max_blocks,
            used_blocks=max_blocks - used_blocks,
        )

    def to_dict(self, data: KVCacheData) -> dict[str, Any]:
        return {
            "type": "kv_cache",
            "layer": data.layer,
            "key_blocks": data.key_blocks,
            "value_blocks": data.value_blocks,
            "max_blocks": data.max_blocks,
            "used_blocks": data.used_blocks,
        }


class HiddenStateVisualizer:
    def capture(self, hidden_states: torch.Tensor, layer: int) -> HiddenStateData:
        states = hidden_states.detach().cpu()
        shape = tuple(states.shape)
        norm = torch.norm(states).item()
        mean = states.mean().item()
        std = states.std().item()
        layer_norm = states[0, -1].reshape(1, -1)[:, :32].reshape(1, -1).tolist()
        return HiddenStateData(
            layer=layer,
            shape=shape,
            norm=norm,
            mean=mean,
            std=std,
            layer_norm=layer_norm,
        )

    def to_dict(self, data: HiddenStateData) -> dict[str, Any]:
        return {
            "type": "hidden_state",
            "layer": data.layer,
            "shape": list(data.shape),
            "norm": data.norm,
            "mean": data.mean,
            "std": data.std,
            "layer_norm": data.layer_norm,
        }


class GradientFlowVisualizer:
    def capture(self, module: nn.Module, layer: int) -> list[GradientFlowData]:
        results: list[GradientFlowData] = []
        for name, param in module.named_parameters():
            if param.grad is not None:
                grad = param.grad.detach().cpu()
                norm = torch.norm(grad).item()
                mean_abs = grad.abs().mean().item()
                max_abs = grad.abs().max().item()
                results.append(
                    GradientFlowData(
                        layer=layer,
                        parameter=name,
                        norm=norm,
                        mean_abs=mean_abs,
                        max_abs=max_abs,
                    )
                )
        return results

    def to_dict(self, data: list[GradientFlowData]) -> dict[str, Any]:
        return {
            "type": "gradient_flow",
            "values": [
                {
                    "layer": d.layer,
                    "parameter": d.parameter,
                    "norm": d.norm,
                    "mean_abs": d.mean_abs,
                    "max_abs": d.max_abs,
                }
                for d in data
            ],
        }
