from typing import Optional, Dict, Any, List
import torch
import torch.nn as nn
import logging

logger = logging.getLogger(__name__)


class NeuronAnalyzer:
    def __init__(self, model: nn.Module):
        self.model = model

    def get_activations(self, layer_name: str, inputs: torch.Tensor) -> Optional[torch.Tensor]:
        acts: Dict[str, torch.Tensor] = {}
        handles = []

        def hook(module, input, output, name=layer_name):
            acts[name] = output.detach().cpu()

        for name, module in self.model.named_modules():
            if name == layer_name:
                handles.append(module.register_forward_hook(hook))
        with torch.no_grad():
            self.model(inputs)
        for h in handles:
            h.remove()
        return acts.get(layer_name)

    def top_activating_neurons(self, layer_name: str, inputs: torch.Tensor, top_k: int = 10) -> List[int]:
        acts = self.get_activations(layer_name, inputs)
        if acts is None:
            return []
        mean_act = acts.mean(dim=0)
        _, indices = torch.topk(mean_act, min(top_k, mean_act.numel()))
        return indices.tolist()

    def neuron_statistics(self, layer_name: str, inputs: torch.Tensor) -> Dict[str, Any]:
        acts = self.get_activations(layer_name, inputs)
        if acts is None:
            return {}
        flat = acts.reshape(-1)
        return {
            "mean": flat.mean().item(),
            "std": flat.std().item(),
            "max": flat.max().item(),
            "min": flat.min().item(),
            "sparsity": (flat == 0).float().mean().item(),
            "num_neurons": acts.shape[-1] if acts.dim() >= 2 else 1,
        }

    def ablate_neuron(self, layer_name: str, neuron_idx: int, inputs: torch.Tensor) -> torch.Tensor:
        acts: Dict[str, torch.Tensor] = {}
        handles = []

        def hook(module, input, output, name=layer_name):
            acts[name] = output.detach().cpu()

        for name, module in self.model.named_modules():
            if name == layer_name:
                handles.append(module.register_forward_hook(hook))
                break

        def zero_hook(module, input, output):
            if isinstance(output, torch.Tensor) and output.dim() >= 2 and neuron_idx < output.shape[-1]:
                output = output.clone()
                output[..., neuron_idx] = 0
            return output

        for name, module in self.model.named_modules():
            if name == layer_name:
                handles.append(module.register_forward_hook(zero_hook))
                break

        with torch.no_grad():
            outputs = self.model(inputs)
        for h in handles:
            h.remove()
        return outputs.logits if hasattr(outputs, "logits") else outputs
