from typing import Dict, Any, List, Tuple
import torch
import torch.nn as nn
import logging

logger = logging.getLogger(__name__)


class CircuitTracer:
    def __init__(self, model: nn.Module):
        self.model = model
        self.activations: Dict[str, torch.Tensor] = {}
        self.hooks = []

    def _get_activation(self, name: str):
        def hook(module, input, output):
            self.activations[name] = output.detach()
        return hook

    def register_hooks(self, layer_names: List[str]) -> None:
        for name, module in self.model.named_modules():
            if name in layer_names:
                hook = module.register_forward_hook(self._get_activation(name))
                self.hooks.append(hook)

    def remove_hooks(self) -> None:
        for hook in self.hooks:
            hook.remove()
        self.hooks = []

    def trace_circuit(self, input_ids: torch.Tensor, attention_mask: torch.Tensor, target_layer: str, target_neuron: int) -> List[Tuple[str, float]]:
        self.activations = {}
        self.register_hooks([target_layer])
        with torch.no_grad():
            self.model(input_ids=input_ids, attention_mask=attention_mask)
        self.remove_hooks()
        target_activation = self.activations.get(target_layer)
        if target_activation is None:
            return []
        importance_scores = []
        for name, activation in self.activations.items():
            if activation.dim() == 3:
                score = activation[:, :, target_neuron].abs().mean().item()
                importance_scores.append((name, score))
        importance_scores.sort(key=lambda x: x[1], reverse=True)
        return importance_scores

    def intervene(self, input_ids: torch.Tensor, attention_mask: torch.Tensor, layer_name: str, intervention_fn) -> torch.Tensor:
        def hook(module, input, output):
            return intervention_fn(output)
        for name, module in self.model.named_modules():
            if name == layer_name:
                h = module.register_forward_hook(hook)
                self.hooks.append(h)
                break
        with torch.no_grad():
            outputs = self.model(input_ids=input_ids, attention_mask=attention_mask)
        self.remove_hooks()
        return outputs.logits


class Node:
    def __init__(self, layer: str, neuron: int, importance: float):
        self.layer = layer
        self.neuron = neuron
        self.importance = importance
        self.children: List['Node'] = []

    def add_child(self, child: 'Node') -> None:
        self.children.append(child)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'layer': self.layer,
            'neuron': self.neuron,
            'importance': self.importance,
            'children': [c.to_dict() for c in self.children]
        }
