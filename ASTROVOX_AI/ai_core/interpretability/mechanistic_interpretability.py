from typing import Optional, Dict, Any, List, Tuple, Callable
import torch
import torch.nn as nn
import logging

logger = logging.getLogger(__name__)


class MechanisticInterpreter:
    def __init__(self, model: nn.Module):
        self.model = model
        self._activations: Dict[str, torch.Tensor] = {}
        self._hooks = []

    def _make_hook(self, name: str):
        def hook(module, input, output):
            self._activations[name] = output.detach().cpu()
        return hook

    def register_layer_hooks(self, layer_names: List[str]) -> None:
        self._activations = {}
        self._hooks = []
        for name, module in self.model.named_modules():
            if name in layer_names:
                h = module.register_forward_hook(self._make_hook(name))
                self._hooks.append(h)

    def remove_hooks(self) -> None:
        for h in self._hooks:
            h.remove()
        self._hooks = []

    def compute_circuit_paths(self, inputs: torch.Tensor, source_layer: str, target_layer: str, target_neuron: int) -> List[Tuple[str, float]]:
        self.register_layer_hooks([source_layer, target_layer])
        with torch.no_grad():
            outputs = self.model(inputs)
        self.remove_hooks()
        source_act = self._activations.get(source_layer)
        target_act = self._activations.get(target_layer)
        if source_act is None or target_act is None:
            return []
        paths: List[Tuple[str, float]] = []
        for name, activation in self._activations.items():
            if activation.dim() >= 3:
                importance = activation[:, :, target_neuron].abs().mean().item()
            elif activation.dim() == 2:
                importance = activation[:, target_neuron].abs().mean().item()
            else:
                importance = activation.abs().mean().item()
            paths.append((name, importance))
        paths.sort(key=lambda x: x[1], reverse=True)
        return paths

    def interpret_attention_head(self, layer_idx: int, head_idx: int, inputs: torch.Tensor, top_k: int = 10) -> Dict[str, Any]:
        attn_name = f"model.layers.{layer_idx}.self_attn"
        acts: Dict[str, torch.Tensor] = {}
        handles = []

        def hook(module, input, output):
            acts[attn_name] = output[1].detach().cpu() if isinstance(output, tuple) and len(output) > 1 else output.detach().cpu()

        for name, module in self.model.named_modules():
            if name == attn_name:
                handles.append(module.register_forward_hook(hook))
                break
        with torch.no_grad():
            self.model(inputs)
        for h in handles:
            h.remove()
        if attn_name not in acts:
            return {"error": "Attention weights not captured"}
        attn = acts[attn_name]
        if attn.dim() < 3:
            return {"error": "Unexpected attention shape"}
        head_attn = attn[0, head_idx]
        seq_len = head_attn.shape[-1]
        top_indices = torch.topk(head_attn.mean(dim=0), min(top_k, seq_len)).indices.tolist()
        return {"head_idx": head_idx, "layer_idx": layer_idx, "top_indices": top_indices}
