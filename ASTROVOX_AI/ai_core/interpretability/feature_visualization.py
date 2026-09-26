from typing import Optional, Dict, Any, List, Tuple
import torch
import torch.nn as nn
import logging

logger = logging.getLogger(__name__)


class FeatureVisualizer:
    def __init__(self, model: nn.Module):
        self.model = model

    def visualize_neuron(self, layer_name: str, neuron_idx: int, lr: float = 0.1, steps: int = 200) -> torch.Tensor:
        input_shape = (1, 3, 224, 224)
        vis = torch.randn(*input_shape, requires_grad=True, device='cpu')
        optimizer = torch.optim.Adam([vis], lr=lr)
        target = torch.zeros(1, device='cpu')
        target[0] = 1.0
        for _ in range(steps):
            optimizer.zero_grad()
            acts = self._get_activation(vis, layer_name)
            if acts is None:
                break
            loss = -acts[0, neuron_idx].mean()
            loss.backward()
            optimizer.step()
        with torch.no_grad():
            vis.clamp_(0, 1)
        return vis.detach()

    def _get_activation(self, x: torch.Tensor, layer_name: str) -> Optional[torch.Tensor]:
        acts: Dict[str, torch.Tensor] = {}
        handles = []

        def hook(module, input, output, name=layer_name):
            acts[name] = output

        for name, module in self.model.named_modules():
            if name == layer_name:
                handles.append(module.register_forward_hook(hook))
                break
        self.model(x)
        for h in handles:
            h.remove()
        return acts.get(layer_name)

    def generate_feature_grid(self, layer_name: str, num_neurons: int = 16) -> List[torch.Tensor]:
        visuals = []
        for i in range(min(num_neurons, 64)):
            vis = self.visualize_neuron(layer_name, i)
            visuals.append(vis)
        return visuals
