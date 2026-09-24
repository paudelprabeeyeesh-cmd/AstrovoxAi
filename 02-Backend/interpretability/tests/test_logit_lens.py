import torch
import torch.nn as nn

from ..logit_lens import LogitLens


class TinyModelWithHead(nn.Module):
    def __init__(self, vocab_size=100, d_model=64):
        super().__init__()
        self.blocks = nn.ModuleList([nn.Linear(d_model, d_model) for _ in range(2)])
        self.head = nn.Linear(d_model, vocab_size)

    def forward(self, x, attention_mask=None):
        h = x
        for layer in self.blocks:
            h = layer(h)
        return self.head(h)


def test_logit_lens_project_shape():
    model = TinyModelWithHead()
    lens = LogitLens(model, model.head)
    activations = torch.randn(2, 8, 64)
    logits = lens.project(activations)
    assert logits.shape == (2, 8, 100)


def test_logit_lens_interpret_layer_top_k():
    model = TinyModelWithHead()
    lens = LogitLens(model, model.head)
    layer_output = torch.randn(1, 8, 64)
    top_probs, top_indices = lens.interpret_layer(layer_output, top_k=5)
    assert top_probs.shape == (1, 8, 5)
    assert top_indices.shape == (1, 8, 5)
    assert float(top_probs.sum(dim=-1).max()) <= 1.0 + 1e-5
