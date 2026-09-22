import pytest
import torch
import torch.nn as nn

from app.core.interpretability import SparseAutoencoder, train_sae, ActivationPatch, circuit_analysis


class TinyModelWithBlocks(nn.Module):
    def __init__(self, vocab_size=100, d_model=64, n_layers=2):
        super().__init__()
        self.embed = nn.Embedding(vocab_size, d_model)
        self.blocks = nn.ModuleList([nn.Linear(d_model, d_model) for _ in range(n_layers)])
        self.head = nn.Linear(d_model, vocab_size)

    def forward(self, x, attention_mask=None):
        h = self.embed(x)
        for layer in self.blocks:
            h = layer(h)
        return self.head(h)


def test_sparse_autoencoder_forward():
    sae = SparseAutoencoder(input_dim=64, hidden_dim=128)
    x = torch.randn(4, 64)
    decoded, loss = sae(x)
    assert decoded.shape == x.shape
    assert loss.shape == ()


def test_sparse_autoencoder_encode():
    sae = SparseAutoencoder(input_dim=64, hidden_dim=128)
    x = torch.randn(4, 64)
    encoded = sae.encode(x)
    assert encoded.shape == (4, 128)


def test_sparse_autoencoder_get_features():
    sae = SparseAutoencoder(input_dim=64, hidden_dim=128)
    x = torch.randn(1, 64)
    features = sae.get_features(x, threshold=0.0)
    assert isinstance(features, list)


def test_circuit_analysis():
    model = TinyModelWithBlocks()
    prompt_ids = torch.randint(0, 100, (1, 8))
    patches = circuit_analysis(model, prompt_ids, target_token_id=5)
    assert isinstance(patches, list)
    for patch in patches:
        assert isinstance(patch, ActivationPatch)
        assert patch.layer >= 0


def test_sae_train_step():
    model = TinyModelWithBlocks()
    prompt_ids = torch.randint(0, 100, (2, 8))
    with torch.no_grad():
        _ = model(prompt_ids)
        activations = model.embed(prompt_ids).detach()
    dataloader = [{"activations": activations}]
    sae = train_sae(model, dataloader, epochs=1)
    assert isinstance(sae, SparseAutoencoder)
