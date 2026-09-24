import torch
import torch.nn as nn
import numpy as np
from typing import Callable, Optional, Tuple


def visualize_feature(model: nn.Module, feature_idx: int, layer_idx: int,
                      input_shape: Tuple[int, ...], lr: float = 0.1, steps: int = 100,
                      device: str = "cpu") -> np.ndarray:
    """Visualize what a neuron responds to with gradient ascent maximization."""
    model.eval()

    x = torch.randn(1, *input_shape, device=device, requires_grad=True)
    optimizer = torch.optim.Adam([x], lr=lr)

    activations = {}

    def hook(module, input, output):
        activations['output'] = output

    target_layer = model.blocks[layer_idx] if hasattr(model, "blocks") else list(model.modules())[layer_idx + 1]
    handle = target_layer.register_forward_hook(hook)

    try:
        for _ in range(steps):
            optimizer.zero_grad()
            _ = model(x)
            act = activations.get('output', x)
            if len(act.shape) >= 3:
                loss = -act[0, -1, feature_idx].mean()
            else:
                loss = -act[0, feature_idx].mean()
            loss.backward()
            optimizer.step()
    finally:
        handle.remove()

    return x.detach().cpu().numpy()
