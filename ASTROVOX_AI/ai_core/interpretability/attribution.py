from typing import Optional, Dict, Any, List, Tuple
import torch
import torch.nn as nn
import logging

logger = logging.getLogger(__name__)


class AttributionAnalyzer:
    def __init__(self, model: nn.Module):
        self.model = model

    def integrated_gradients(self, inputs: torch.Tensor, target_class: int, baseline: Optional[torch.Tensor] = None, steps: int = 50) -> torch.Tensor:
        if baseline is None:
            baseline = torch.zeros_like(inputs)
        scale = torch.linspace(0, 1, steps, device=inputs.device)
        grad_sum = torch.zeros_like(inputs)
        for s in scale:
            x = baseline + s * (inputs - baseline)
            x.requires_grad_(True)
            outputs = self.model(x)
            logits = outputs.logits if hasattr(outputs, "logits") else outputs
            score = logits[0, -1, target_class]
            grad = torch.autograd.grad(score, x, retain_graph=False, create_graph=False)[0]
            grad_sum += grad
        attributions = (inputs - baseline) * grad_sum / steps
        return attributions.detach()

    def gradient_x_input(self, inputs: torch.Tensor, target_class: int) -> torch.Tensor:
        inputs = inputs.clone().detach().requires_grad_(True)
        outputs = self.model(inputs)
        logits = outputs.logits if hasattr(outputs, "logits") else outputs
        score = logits[0, -1, target_class]
        grad = torch.autograd.grad(score, inputs, retain_graph=False, create_graph=False)[0]
        return (inputs * grad).detach()

    def saliency_map(self, inputs: torch.Tensor, target_class: int) -> torch.Tensor:
        inputs = inputs.clone().detach().requires_grad_(True)
        outputs = self.model(inputs)
        logits = outputs.logits if hasattr(outputs, "logits") else outputs
        score = logits[0, -1, target_class]
        grad = torch.autograd.grad(score, inputs, retain_graph=False, create_graph=False)[0]
        return grad.abs().detach()

    def occlusion_sensitivity(self, inputs: torch.Tensor, target_class: int, window_size: int = 1) -> torch.Tensor:
        seq_len = inputs.shape[1]
        baseline_output = self.model(inputs)
        baseline_logits = baseline_output.logits if hasattr(baseline_output, "logits") else baseline_output
        base_score = baseline_logits[0, -1, target_class].item()
        sensitivity = torch.zeros(seq_len)
        for i in range(seq_len):
            occluded = inputs.clone()
            occluded[:, i:i + window_size] = 0
            out = self.model(occluded)
            logits = out.logits if hasattr(out, "logits") else out
            score = logits[0, -1, target_class].item()
            sensitivity[i] = base_score - score
        return sensitivity
