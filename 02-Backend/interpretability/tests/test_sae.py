import numpy as np
import pytest
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim

from ..sae import SparseAutoencoder


class TinyModel(nn.Module):
    def __init__(self, vocab_size=100, d_model=64, n_layers=2):
        super().__init__()
        self.blocks = nn.ModuleList([nn.Linear(d_model, d_model) for _ in range(n_layers)])
        self.head = nn.Linear(d_model, vocab_size)

    def forward(self, x, attention_mask=None):
        h = x
        for layer in self.blocks:
            h = layer(h)
        return self.head(h)


def test_sae_forward_shape():
    sae = SparseAutoencoder(input_dim=64, hidden_dim=128)
    x = torch.randn(4, 64)
    decoded, loss = sae(x)
    assert decoded.shape == x.shape
    assert loss.shape == ()


def test_sae_encode_shape():
    sae = SparseAutoencoder(input_dim=64, hidden_dim=128)
    x = torch.randn(4, 64)
    encoded = sae.encode(x)
    assert encoded.shape == (4, 128)


def test_sae_get_active_features():
    sae = SparseAutoencoder(input_dim=64, hidden_dim=128)
    x = torch.randn(1, 64)
    features = sae.get_active_features(x, threshold=0.0)
    assert isinstance(features, list)
    assert all(isinstance(f, int) for f in features)


def test_sae_sparsity_penalty_effect():
    torch.manual_seed(42)
    sae = SparseAutoencoder(input_dim=64, hidden_dim=128, sparsity_coef=0.5)
    x = torch.randn(2, 64)
    _, loss1 = sae(x)
    torch.manual_seed(42)
    sae_low = SparseAutoencoder(input_dim=64, hidden_dim=128, sparsity_coef=0.0)
    _, loss2 = sae_low(x)
    assert float(loss1) >= float(loss2)


def test_sae_reconstruction_decreases_with_hidden_dim():
    torch.manual_seed(42)
    sae_small = SparseAutoencoder(input_dim=64, hidden_dim=16)
    sae_large = SparseAutoencoder(input_dim=64, hidden_dim=256)
    x = torch.randn(4, 64)
    opt_small = optim.SGD(sae_small.parameters(), lr=1e-2)
    opt_large = optim.SGD(sae_large.parameters(), lr=1e-2)
    for _ in range(20):
        _, ls = sae_small(x)
        opt_small.zero_grad()
        ls.backward()
        opt_small.step()
        _, ll = sae_large(x)
        opt_large.zero_grad()
        ll.backward()
        opt_large.step()
    with torch.no_grad():
        ds, _ = sae_small(x)
        dl, _ = sae_large(x)
    recon_small = float(F.mse_loss(ds, x))
    recon_large = float(F.mse_loss(dl, x))
    assert recon_large <= recon_small
