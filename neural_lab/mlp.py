"""A compact educational multilayer perceptron built from real PyTorch layers."""

from __future__ import annotations

from collections.abc import Sequence

import torch
from torch import nn


class MultilayerPerceptron(nn.Module):
    """Dense network with inspectable trainable weights and biases."""

    def __init__(
        self,
        input_size: int,
        hidden_sizes: Sequence[int],
        output_size: int,
        *,
        activation: str = "relu",
    ) -> None:
        super().__init__()
        dimensions = (input_size, *hidden_sizes, output_size)
        if any(not isinstance(size, int) or size < 1 for size in dimensions):
            raise ValueError("input, hidden, and output dimensions must be positive integers")
        if not hidden_sizes:
            raise ValueError("an MLP requires at least one hidden layer")
        activations = {"relu": nn.ReLU, "gelu": nn.GELU, "tanh": nn.Tanh}
        if activation not in activations:
            raise ValueError("activation must be one of: relu, gelu, tanh")
        blocks: list[nn.Module] = []
        for index, (source, destination) in enumerate(zip(dimensions[:-1], dimensions[1:], strict=True)):
            blocks.append(nn.Linear(source, destination, bias=True))
            if index < len(dimensions) - 2:
                blocks.append(activations[activation]())
        # The output layer stays linear so callers can use logits with CrossEntropyLoss.
        self.layers = nn.Sequential(*blocks)
        self.input_size = input_size
        self.output_size = output_size

    def forward(self, inputs: torch.Tensor) -> torch.Tensor:
        if inputs.ndim < 1 or inputs.shape[-1] != self.input_size:
            raise ValueError(f"input's last dimension must be {self.input_size}")
        return self.layers(inputs)
