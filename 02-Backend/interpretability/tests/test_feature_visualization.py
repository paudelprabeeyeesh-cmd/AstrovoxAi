import numpy as np
import pytest
import torch
import torch.nn as nn

from ..feature_visualization import visualize_feature


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


def test_feature_visualization_returns_numpy():
    model = TinyModelWithBlocks()
    result = visualize_feature(model, feature_idx=0, layer_idx=0, input_shape=(8, 64), steps=10)
    assert isinstance(result, np.ndarray)


def test_feature_visualization_shape():
    model = TinyModelWithBlocks()
    result = visualize_feature(model, feature_idx=0, layer_idx=0, input_shape=(8, 64), steps=10)
    assert result.shape == (1, 8, 64)


def test_feature_visualization_different_features():
    model = TinyModelWithBlocks()
    result0 = visualize_feature(model, feature_idx=0, layer_idx=0, input_shape=(4, 64), steps=10)
    result1 = visualize_feature(model, feature_idx=1, layer_idx=0, input_shape=(4, 64), steps=10)
    assert not np.allclose(result0, result1)
