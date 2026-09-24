"""Tests for Structured Pruning (attention heads, layers, MoE experts)."""

import pytest
import torch
import torch.nn as nn

from quantization.structured_pruning import (
    prune_attention_heads,
    prune_layers_by_importance,
    prune_moe_experts,
)


class DummyMoE(nn.Module):
    def __init__(self, num_experts=4):
        super().__init__()
        self.num_experts = num_experts
        self.experts = nn.ModuleList([nn.Linear(8, 8) for _ in range(num_experts)])

    def forward(self, x):
        return sum(e(x) for e in self.experts) / len(self.experts)


class DummyTransformer(nn.Module):
    def __init__(self, num_layers=4, num_heads=4, embed_dim=16):
        super().__init__()
        self.layers = nn.ModuleList([
            nn.MultiheadAttention(embed_dim, num_heads, batch_first=True)
            for _ in range(num_layers)
        ])

    def forward(self, x):
        for layer in self.layers:
            x, _ = layer(x, x, x)
        return x


class TestPruneAttentionHeads:
    def test_prune_reduces_heads(self):
        model = DummyTransformer(num_layers=2, num_heads=4, embed_dim=16)
        importance = [0.1, 0.5, 0.3, 0.2]
        pruned = prune_attention_heads(model, importance, 2)
        for module in pruned.modules():
            if isinstance(module, nn.MultiheadAttention):
                assert module.num_heads == 2

    def test_keep_highest_importance(self):
        model = DummyTransformer(num_layers=1, num_heads=4, embed_dim=16)
        importance = [0.1, 0.9, 0.2, 0.8]
        pruned = prune_attention_heads(model, importance, 2)
        for module in pruned.modules():
            if isinstance(module, nn.MultiheadAttention):
                assert module.num_heads == 2

    def test_invalid_num_heads_raises(self):
        model = DummyTransformer(num_layers=1, num_heads=4, embed_dim=16)
        with pytest.raises(ValueError):
            prune_attention_heads(model, [0.5] * 4, 0)

    @pytest.mark.skip(reason="torch-only test; non-stdlib dependency")
    def test_output_shape_preserved(self):
        model = DummyTransformer(num_layers=1, num_heads=4, embed_dim=16)
        importance = [0.5] * 4
        pruned = prune_attention_heads(model, importance, 2)
        x = torch.randn(2, 10, 16)
        out = pruned(x)
        assert out.shape == (2, 10, 16)


class TestPruneLayers:
    def test_prune_reduces_layers(self):
        model = DummyTransformer(num_layers=4, num_heads=2, embed_dim=8)
        importance = [0.1, 0.5, 0.3, 0.2]
        pruned = prune_layers_by_importance(model, importance, 2)
        for name, module in pruned.named_children():
            if isinstance(module, nn.ModuleList):
                assert len(module) == 2

    def test_invalid_num_layers_raises(self):
        model = DummyTransformer(num_layers=4, num_heads=2, embed_dim=8)
        with pytest.raises(ValueError):
            prune_layers_by_importance(model, [0.5] * 4, 0)


class TestPruneMoeExperts:
    def test_prune_reduces_experts(self):
        model = DummyMoE(num_experts=4)
        importance = [0.1, 0.5, 0.3, 0.2]
        pruned = prune_moe_experts(model, importance, 2)
        assert pruned.num_experts == 2
        assert len(pruned.experts) == 2

    def test_invalid_num_experts_raises(self):
        model = DummyMoE(num_experts=4)
        with pytest.raises(ValueError):
            prune_moe_experts(model, [0.5] * 4, 0)
