from typing import Optional, Dict, Any, List
import torch
import torch.nn as nn
import logging

logger = logging.getLogger(__name__)


class ProbeClassifier:
    def __init__(self, input_dim: int, num_classes: int, probe_type: str = 'linear'):
        self.input_dim = input_dim
        self.num_classes = num_classes
        self.probe_type = probe_type
        if probe_type == 'linear':
            self.model = nn.Linear(input_dim, num_classes)
        else:
            self.model = nn.Sequential(nn.Linear(input_dim, input_dim // 2), nn.ReLU(), nn.Linear(input_dim // 2, num_classes))
        self.criterion = nn.CrossEntropyLoss()
        self.optimizer = torch.optim.Adam(self.model.parameters(), lr=1e-3)

    def train_step(self, features: torch.Tensor, labels: torch.Tensor) -> float:
        logits = self.model(features)
        loss = self.criterion(logits, labels)
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()
        return loss.item()

    def evaluate(self, features: torch.Tensor, labels: torch.Tensor) -> Dict[str, float]:
        with torch.no_grad():
            logits = self.model(features)
            preds = logits.argmax(dim=-1)
            accuracy = (preds == labels).float().mean().item()
        return {'accuracy': accuracy, 'loss': self.criterion(logits, labels).item()}


class CausalTracer:
    def __init__(self, model: nn.Module):
        self.model = model

    def trace_causal_effect(self, layer_name: str, neuron_idx: int, inputs: torch.Tensor, target_output: torch.Tensor) -> float:
        original_state: Optional[torch.Tensor] = None

        def intervention_hook(module, input, output):
            nonlocal original_state
            original_state = output.clone()
            if isinstance(output, torch.Tensor):
                output = output.clone()
                if output.dim() > 2 and neuron_idx < output.shape[-1]:
                    output[..., neuron_idx] = 0
                elif output.dim() == 2 and neuron_idx < output.shape[-1]:
                    output[:, neuron_idx] = 0

        handle = None
        for name, module in self.model.named_modules():
            if name == layer_name:
                handle = module.register_forward_hook(intervention_hook)
                break
        if handle is None:
            logger.warning("Layer %s not found for causal tracing", layer_name)
            return 0.0
        with torch.no_grad():
            intervened_output = self.model(inputs)
        handle.remove()
        if original_state is None:
            return 0.0
        effect = torch.norm(original_state - intervened_output).item()
        return effect
