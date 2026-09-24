import numpy as np
import torch
import torch.nn.functional as F
from typing import Optional, List


class AttentionVisualizer:
    """Visualize attention patterns with interpretation."""

    def __init__(self, model: nn.Module):
        self.model = model
        self.attention_weights = []

    def get_attention_patterns(self, input_ids: torch.Tensor, layer_idx: int = -1) -> np.ndarray:
        self.attention_weights = []

        def hook(module, input, output):
            if isinstance(output, tuple) and len(output) > 1:
                self.attention_weights.append(output[1].detach().cpu().numpy())
            elif isinstance(output, torch.Tensor):
                self.attention_weights.append(output.detach().cpu().numpy())

        target_layer = self.model.blocks[layer_idx] if hasattr(self.model, "blocks") else None
        if target_layer is None:
            return np.zeros((1, 1, input_ids.shape[1], input_ids.shape[1]))

        handle = target_layer.register_forward_hook(hook)
        try:
            with torch.no_grad():
                _ = self.model(input_ids)
        finally:
            handle.remove()

        if self.attention_weights:
            return self.attention_weights[0]
        return np.zeros((1, 1, input_ids.shape[1], input_ids.shape[1]))

    def visualize_head(self, attention_pattern: np.ndarray, head_idx: int = 0) -> np.ndarray:
        if len(attention_pattern.shape) == 4:
            return attention_pattern[0, head_idx]
        return attention_pattern
