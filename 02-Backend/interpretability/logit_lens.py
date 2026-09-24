import torch
import torch.nn as nn
from typing import Tuple


class LogitLens:
    """Project intermediate activations to vocabulary with understanding projection."""

    def __init__(self, model: nn.Module, unembedding: nn.Linear):
        self.model = model
        self.unembedding = unembedding

    def project(self, activations: torch.Tensor) -> torch.Tensor:
        return self.unembedding(activations)

    def interpret_layer(self, layer_output: torch.Tensor, top_k: int = 10) -> Tuple[torch.Tensor, torch.Tensor]:
        logits = self.project(layer_output)
        probs = torch.softmax(logits, dim=-1)
        top_probs, top_indices = torch.topk(probs, top_k, dim=-1)
        return top_probs, top_indices
