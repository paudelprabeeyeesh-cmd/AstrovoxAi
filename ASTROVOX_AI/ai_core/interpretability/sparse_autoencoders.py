from typing import Tuple
import torch
import torch.nn as nn
import logging

logger = logging.getLogger(__name__)


class SparseAutoencoder:
    def __init__(self, input_dim: int, hidden_dim: int, sparsity_coef: float = 0.1, lr: float = 1e-3):
        self.encoder = nn.Linear(input_dim, hidden_dim, bias=True)
        self.decoder = nn.Linear(hidden_dim, input_dim, bias=True)
        self.sparsity_coef = sparsity_coef
        self.lr = lr
        self.optimizer = torch.optim.Adam(list(self.encoder.parameters()) + list(self.decoder.parameters()), lr=lr)

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        z = torch.relu(self.encoder(x))
        reconstructed = self.decoder(z)
        recon_loss = nn.functional.mse_loss(reconstructed, x)
        l1_loss = z.abs().mean()
        loss = recon_loss + self.sparsity_coef * l1_loss
        return reconstructed, z, loss

    def train_step(self, x: torch.Tensor) -> float:
        self.optimizer.zero_grad()
        _, _, loss = self.forward(x)
        loss.backward()
        self.optimizer.step()
        return loss.item()

    def encode(self, x: torch.Tensor) -> torch.Tensor:
        with torch.no_grad():
            return torch.relu(self.encoder(x))

    def decode(self, z: torch.Tensor) -> torch.Tensor:
        with torch.no_grad():
            return self.decoder(z)


class TopKSparseAutoencoder(SparseAutoencoder):
    def __init__(self, input_dim: int, hidden_dim: int, k: int = 50, sparsity_coef: float = 0.1, lr: float = 1e-3):
        super().__init__(input_dim, hidden_dim, sparsity_coef, lr)
        self.k = k

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        z = self.encoder(x)
        topk_values, topk_indices = torch.topk(z, k=self.k, dim=-1)
        z_sparse = torch.zeros_like(z)
        z_sparse.scatter_(-1, topk_indices, topk_values)
        reconstructed = self.decoder(z_sparse)
        recon_loss = nn.functional.mse_loss(reconstructed, x)
        loss = recon_loss
        return reconstructed, z_sparse, loss
