from typing import Optional, Dict, Any, List
import torch
import torch.nn as nn
import logging

logger = logging.getLogger(__name__)


class AttentionVisualizer:
    def __init__(self, model: nn.Module):
        self.model = model
        self.attention_weights: List[torch.Tensor] = []

    def register_hooks(self) -> None:
        def hook(module, input, output):
            if isinstance(output, tuple) and len(output) > 1:
                self.attention_weights.append(output[1].detach().cpu())
        for module in self.model.modules():
            if hasattr(module, 'num_heads') and hasattr(module, 'head_dim'):
                module.register_forward_hook(hook)

    def get_attention_map(self, layer_idx: int, head_idx: Optional[int] = None) -> Optional[torch.Tensor]:
        if layer_idx < len(self.attention_weights):
            attn = self.attention_weights[layer_idx]
            if head_idx is not None:
                return attn[0, head_idx]
            return attn[0].mean(dim=0)
        return None

    def clear(self) -> None:
        self.attention_weights = []


class NeuronInterpreter:
    def __init__(self, model: nn.Module):
        self.model = model

    def get_activations(self, layer_name: str, inputs: torch.Tensor) -> Optional[torch.Tensor]:
        activations: Dict[str, torch.Tensor] = {}
        handles = []

        def hook(module, input, output, name=layer_name):
            activations[name] = output.detach().cpu()

        for name, module in self.model.named_modules():
            if name == layer_name:
                handles.append(module.register_forward_hook(hook))
        with torch.no_grad():
            self.model(inputs)
        for h in handles:
            h.remove()
        return activations.get(layer_name)

    def top_activating_neurons(self, layer_name: str, inputs: torch.Tensor, top_k: int = 10) -> List[int]:
        acts = self.get_activations(layer_name, inputs)
        if acts is None:
            return []
        mean_act = acts.mean(dim=0)
        _, indices = torch.topk(mean_act, min(top_k, mean_act.numel()))
        return indices.tolist()
