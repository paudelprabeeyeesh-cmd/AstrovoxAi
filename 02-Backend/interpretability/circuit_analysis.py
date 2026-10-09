import numpy as np
import torch
import torch.nn as nn
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class ActivationPatch:
    layer: int
    position: int
    original_activation: Optional[np.ndarray] = None
    patched_activation: Optional[np.ndarray] = None


def circuit_analysis(model: nn.Module, prompt_ids: torch.Tensor, target_token_id: int) -> List[ActivationPatch]:
    """Trace causal path of a specific decision through the model's layers using activation patching."""
    patches: List[ActivationPatch] = []
    hooks = []
    activations = {}

    def make_hook(layer_idx: int):
        def hook(module, input, output):
            activations[layer_idx] = output.detach().cpu().numpy()
        return hook

    for idx, layer in enumerate(model.blocks if hasattr(model, "blocks") else []):
        hooks.append(layer.register_forward_hook(make_hook(idx)))
    try:
        with torch.no_grad():
            logits = model(prompt_ids)
        if logits.dim() == 3:
            target_logits = logits[0, -1, :]
            float(torch.softmax(target_logits, dim=-1)[target_token_id])
        elif logits.dim() == 2:
            target_logits = logits[0, :]
            float(torch.softmax(target_logits, dim=-1)[target_token_id])
        else:
            pass
        for layer_idx, activation in activations.items():
            patch = ActivationPatch(layer=layer_idx, position=prompt_ids.shape[1] - 1, original_activation=activation)
            patches.append(patch)
    finally:
        for hook in hooks:
            hook.remove()
    return patches
