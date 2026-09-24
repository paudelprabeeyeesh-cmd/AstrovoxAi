import numpy as np
import torch
import torch.nn as nn

from ..circuit_analysis import ActivationPatch, circuit_analysis


class TinyModelWithBlocks(nn.Module):
    def __init__(self, vocab_size=100, d_model=64, n_layers=2):
        super().__init__()
        self.blocks = nn.ModuleList([nn.Linear(d_model, d_model) for _ in range(n_layers)])
        self.head = nn.Linear(d_model, vocab_size)

    def forward(self, x, attention_mask=None):
        h = x
        for layer in self.blocks:
            h = layer(h)
        return self.head(h)


def test_circuit_analysis_returns_list():
    model = TinyModelWithBlocks()
    prompt_ids = torch.randn(1, 64).float()
    patches = circuit_analysis(model, prompt_ids, target_token_id=5)
    assert isinstance(patches, list)
    assert len(patches) == 2


def test_circuit_analysis_patch_attributes():
    model = TinyModelWithBlocks()
    prompt_ids = torch.randn(1, 64).float()
    patches = circuit_analysis(model, prompt_ids, target_token_id=5)
    for patch in patches:
        assert isinstance(patch, ActivationPatch)
        assert patch.layer >= 0
        assert patch.position == prompt_ids.shape[1] - 1
        assert patch.original_activation is not None
        assert isinstance(patch.original_activation, np.ndarray)


def test_circuit_analysis_no_model_blocks():
    model = nn.Linear(10, 10)
    prompt_ids = torch.randn(1, 10).float()
    patches = circuit_analysis(model, prompt_ids, target_token_id=0)
    assert isinstance(patches, list)
    assert len(patches) == 0
