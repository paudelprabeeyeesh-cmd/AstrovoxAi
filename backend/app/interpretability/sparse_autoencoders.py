from typing import Optional, Dict, Any, List, Tuple
import torch
import torch.nn as nn
import torch.nn.functional as F
import logging

logger = logging.getLogger(__name__)


class SparseAutoencoder(nn.Module):
    def __init__(self, input_dim: int, hidden_dim: int, sparsity_coef: float = 0.1, lr: float = 1e-3):
        super().__init__()
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.sparsity_coef = sparsity_coef
        self.encoder = nn.Linear(input_dim, hidden_dim, bias=True)
        self.decoder = nn.Linear(hidden_dim, input_dim, bias=True)
        self.optimizer = torch.optim.Adam(list(self.encoder.parameters()) + list(self.decoder.parameters()), lr=lr)

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        z = torch.relu(self.encoder(x))
        reconstructed = self.decoder(z)
        recon_loss = F.mse_loss(reconstructed, x)
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

    def get_features(self, x: torch.Tensor, threshold: float = 0.1) -> List[int]:
        with torch.no_grad():
            encoded = self.encode(x)
            active = (encoded > threshold).nonzero(as_tuple=True)[1]
        return active.tolist()


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
        recon_loss = F.mse_loss(reconstructed, x)
        loss = recon_loss
        return reconstructed, z_sparse, loss


def train_sae(model: nn.Module, dataloader, device: str = "cpu", epochs: int = 10) -> SparseAutoencoder:
    input_dim = 64
    hidden_dim = 128
    sae = SparseAutoencoder(input_dim=input_dim, hidden_dim=hidden_dim)
    optimizer = torch.optim.Adam(sae.parameters(), lr=1e-3)
    for epoch in range(epochs):
        total_loss = 0.0
        for batch in dataloader:
            x = batch["activations"]
            _, _, loss = sae(x)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            total_loss += loss.item()
        logger.info("SAE epoch %d: loss=%.4f", epoch, total_loss / max(len(dataloader), 1))
    return sae
