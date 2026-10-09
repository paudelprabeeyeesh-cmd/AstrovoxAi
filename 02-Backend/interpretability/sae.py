import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import List, Tuple


class SparseAutoencoder(nn.Module):
    """Sparse Autoencoder for decomposing activations into interpretable features with L1 sparsity penalty."""

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

    def get_active_features(self, x: torch.Tensor, threshold: float = 0.1) -> List[int]:
        with torch.no_grad():
            encoded = self.encode(x)
            active = (encoded > threshold).nonzero(as_tuple=True)[1]
        return active.tolist()
