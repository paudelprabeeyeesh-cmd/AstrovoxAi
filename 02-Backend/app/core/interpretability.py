"""
Interpretability layer: Sparse Autoencoders (SAE) and circuit analysis.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Optional, Tuple

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

logger = logging.getLogger(__name__)


class SparseAutoencoder(nn.Module):
    """Sparse Autoencoder for decomposing model activations into interpretable features."""

    def __init__(self, input_dim: int, hidden_dim: int, sparsity_coef: float = 0.1):
        super().__init__()
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.sparsity_coef = sparsity_coef
        self.encoder = nn.Linear(input_dim, hidden_dim, bias=True)
        self.decoder = nn.Linear(hidden_dim, input_dim, bias=True)

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        encoded = F.relu(self.encoder(x))
        decoded = self.decoder(encoded)
        reconstruction_loss = F.mse_loss(decoded, x)
        sparsity_loss = self.sparsity_coef * encoded.abs().mean()
        loss = reconstruction_loss + sparsity_loss
        return decoded, loss

    def encode(self, x: torch.Tensor) -> torch.Tensor:
        return F.relu(self.encoder(x))

    def get_features(self, x: torch.Tensor, threshold: float = 0.1) -> List[int]:
        with torch.no_grad():
            encoded = self.encode(x)
            active = (encoded > threshold).nonzero(as_tuple=True)[1]
        return active.tolist()


def train_sae(model: nn.Module, dataloader, device: str = "cpu", epochs: int = 10) -> SparseAutoencoder:
    """Train SAE on model activations."""
    input_dim = 64
    hidden_dim = 128
    sae = SparseAutoencoder(input_dim=input_dim, hidden_dim=hidden_dim)
    optimizer = torch.optim.Adam(sae.parameters(), lr=1e-3)
    for epoch in range(epochs):
        total_loss = 0.0
        for batch in dataloader:
            x = batch["activations"]
            _, loss = sae(x)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            total_loss += loss.item()
        logger.info(f"SAE epoch {epoch}: loss={total_loss / max(len(dataloader), 1):.4f}")
    return sae


@dataclass
class ActivationPatch:
    layer: int
    position: int
    original_activation: Optional[np.ndarray] = None
    patched_activation: Optional[np.ndarray] = None


def circuit_analysis(model: nn.Module, prompt_ids: torch.Tensor, target_token_id: int) -> List[ActivationPatch]:
    """Trace causal path of a specific decision through the model's layers."""
    patches: List[ActivationPatch] = []
    hooks = []
    activations: Dict[int, torch.Tensor] = {}

    def make_hook(layer_idx: int):
        def hook(module, input, output):
            activations[layer_idx] = output.detach().cpu().numpy()
        return hook

    for idx, layer in enumerate(model.blocks if hasattr(model, "blocks") else []):
        hooks.append(layer.register_forward_hook(make_hook(idx)))
    try:
        with torch.no_grad():
            logits = model(prompt_ids)
        target_logits = logits[0, -1, :]
        target_prob = float(torch.softmax(target_logits, dim=-1)[target_token_id])
        for layer_idx, activation in activations.items():
            patch = ActivationPatch(layer=layer_idx, position=prompt_ids.shape[1] - 1, original_activation=activation)
            patches.append(patch)
    finally:
        for hook in hooks:
            hook.remove()
    return patches
