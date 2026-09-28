from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Iterator

import numpy as np
import torch
import torch.nn as nn

logger = logging.getLogger(__name__)


@dataclass
class TokenInfo:
    token_id: int
    token_text: str
    embedding_norm: float
    positional_index: int


@dataclass
class ActivationInfo:
    layer: int
    shape: tuple[int, ...]
    norm: float
    mean: float
    std: float
    layer_norm_eps: float
    values: list[list[float]]


@dataclass
class WeightInfo:
    name: str
    shape: tuple[int, ...]
    norm: float
    mean: float
    std: float
    trainable: bool
    values: list[list[float]]


@dataclass
class GradientInfo:
    name: str
    shape: tuple[int, ...]
    norm: float
    mean_abs: float
    max_abs: float
    trainable: bool
    exists: bool


class TokenInspector:
    def __init__(self, embedding: nn.Embedding) -> None:
        self.embedding = embedding

    def inspect(self, token_id: int, positional_index: int = 0) -> TokenInfo:
        token_text = self._resolve_text(token_id)
        weight = self.embedding.weight.detach().cpu()
        token_emb = weight[token_id]
        norm = float(torch.norm(token_emb).item())
        return TokenInfo(
            token_id=token_id,
            token_text=token_text,
            embedding_norm=norm,
            positional_index=positional_index,
        )

    def _resolve_text(self, token_id: int) -> str:
        token_text = f"<token_{token_id}>"
        try:
            from tokenizers import Tokenizer

            tok = Tokenizer.from_file("tokenizer.json")
            token_text = tok.decode([token_id]) or token_text
        except Exception:
            pass
        return token_text

    def to_dict(self, info: TokenInfo) -> dict[str, Any]:
        return {
            "type": "token",
            "token_id": info.token_id,
            "token_text": info.token_text,
            "embedding_norm": info.embedding_norm,
            "positional_index": info.positional_index,
        }


class ActivationViewer:
    def __init__(self) -> None:
        self._handles: list[Any] = []
        self._activations: dict[str, torch.Tensor] = {}

    def register_hooks(self, module: nn.Module) -> None:
        self._activations = {}

        def _hook(name: str, module: nn.Module, inputs: tuple[torch.Tensor, ...], output: torch.Tensor) -> None:
            act = output if isinstance(output, torch.Tensor) else outputs[0]
            self._activations[name] = act.detach().cpu()

        for name, m in module.named_modules():
            if isinstance(m, (nn.Linear, nn.Embedding, nn.LayerNorm)):
                handle = m.register_forward_hook(self._make_hook(name))
                self._handles.append(handle)

    def _make_hook(self, name: str):
        def _hook(module: nn.Module, inputs: tuple[torch.Tensor, ...], output: torch.Tensor) -> None:
            act = output if isinstance(output, torch.Tensor) else outputs[0]
            self._activations[name] = act.detach().cpu()

        return _hook

    def forward(self, module: nn.Module, input_ids: torch.Tensor) -> None:
        self._activations = {}
        with torch.no_grad():
            module(input_ids)

    def read(self, layer: int) -> ActivationInfo:
        matches = []
        for key in self._activations:
            if f"blocks.{layer}" in key or f"{layer}" == key:
                matches.append(key)
        if not matches:
            empty = torch.zeros(1, 1)
            return ActivationInfo(
                layer=layer,
                shape=(1, 1),
                norm=0.0,
                mean=0.0,
                std=0.0,
                layer_norm_eps=1e-5,
                values=[],
            )
        key = matches[0]
        act = self._activations[key]
        norm = float(torch.norm(act).item())
        mean = float(act.mean().item())
        std = float(act.std().item())
        values = act[0, -1].reshape(1, -1)[:, :32].reshape(1, -1).tolist()
        return ActivationInfo(
            layer=layer,
            shape=tuple(act.shape),
            norm=norm,
            mean=mean,
            std=std,
            layer_norm_eps=1e-5,
            values=values,
        )

    def to_dict(self, info: ActivationInfo) -> dict[str, Any]:
        return {
            "type": "activation",
            "layer": info.layer,
            "shape": list(info.shape),
            "norm": info.norm,
            "mean": info.mean,
            "std": info.std,
            "layer_norm_eps": info.layer_norm_eps,
            "values": info.values,
        }

    def close(self) -> None:
        for handle in self._handles:
            handle.remove()
        self._handles = []


class WeightInspector:
    def read(self, module: nn.Module, param_name: str) -> WeightInfo | None:
        for name, param in module.named_parameters():
            if name == param_name:
                weight = param.detach().cpu()
                norm = float(torch.norm(weight).item())
                mean = float(weight.mean().item())
                std = float(weight.std().item())
                values = weight.flatten()[:256].reshape(1, -1).tolist()
                return WeightInfo(
                    name=name,
                    shape=tuple(weight.shape),
                    norm=norm,
                    mean=mean,
                    std=std,
                    trainable=param.requires_grad,
                    values=values,
                )
        return None

    def to_dict(self, info: WeightInfo) -> dict[str, Any]:
        return {
            "type": "weight",
            "name": info.name,
            "shape": list(info.shape),
            "norm": info.norm,
            "mean": info.mean,
            "std": info.std,
            "trainable": info.trainable,
            "values": info.values,
        }


class GradientInspector:
    def read(self, module: nn.Module, param_name: str) -> GradientInfo | None:
        for name, param in module.named_parameters():
            if name == param_name:
                grad = param.grad
                exists = grad is not None
                norm = float(torch.norm(grad).item()) if exists else 0.0
                mean_abs = float(grad.abs().mean().item()) if exists else 0.0
                max_abs = float(grad.abs().max().item()) if exists else 0.0
                return GradientInfo(
                    name=name,
                    shape=tuple(param.shape),
                    norm=norm,
                    mean_abs=mean_abs,
                    max_abs=max_abs,
                    trainable=param.requires_grad,
                    exists=exists,
                )
        return None

    def to_dict(self, info: GradientInfo) -> dict[str, Any]:
        return {
            "type": "gradient",
            "name": info.name,
            "shape": list(info.shape),
            "norm": info.norm,
            "mean_abs": info.mean_abs,
            "max_abs": info.max_abs,
            "trainable": info.trainable,
            "exists": info.exists,
        }
