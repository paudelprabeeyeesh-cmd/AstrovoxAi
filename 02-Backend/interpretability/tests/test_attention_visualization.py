import numpy as np
import pytest
import torch
import torch.nn as nn

from ..attention_visualization import AttentionVisualizer


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


def test_attention_visualizer_returns_array():
    model = TinyModelWithBlocks()
    visualizer = AttentionVisualizer(model)
    input_ids = torch.randn(1, 64).float()
    pattern = visualizer.get_attention_patterns(input_ids, layer_idx=0)
    assert isinstance(pattern, np.ndarray)


def test_attention_visualizer_shape():
    model = TinyModelWithBlocks()
    visualizer = AttentionVisualizer(model)
    input_ids = torch.randn(1, 64).float()
    pattern = visualizer.get_attention_patterns(input_ids, layer_idx=0)
    seq_len = input_ids.shape[1]
    assert pattern.shape[-1] == seq_len or pattern.shape[-1] == 1


def test_visualize_head_returns_2d():
    pattern = np.random.rand(1, 2, 4, 4)
    visualizer = AttentionVisualizer(None)
    head_pattern = visualizer.visualize_head(pattern, head_idx=1)
    assert head_pattern.ndim == 2
    assert head_pattern.shape == (4, 4)
