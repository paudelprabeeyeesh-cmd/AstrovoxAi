from typing import Dict, List
import torch
import torch.nn as nn
import logging

logger = logging.getLogger(__name__)


class LogitLens:
    def __init__(self, model: nn.Module):
        self.model = model
        self._layer_outputs: Dict[int, torch.Tensor] = {}

    def _make_hook(self, layer_idx: int):
        def hook(module, input, output):
            self._layer_outputs[layer_idx] = output.detach().cpu()
        return hook

    def register_hooks(self, layers: List[int]) -> None:
        self._layer_outputs = {}
        for idx, layer in enumerate(self.model.blocks if hasattr(self.model, "blocks") else []):
            if idx in layers:
                layer.register_forward_hook(self._make_hook(idx))

    def analyze(self, inputs: torch.Tensor, layers: List[int], target_token_id: int, vocab_size: int) -> Dict[int, float]:
        self.register_hooks(layers)
        with torch.no_grad():
            outputs = self.model(inputs)
        logits = outputs.logits if hasattr(outputs, "logits") else outputs
        results: Dict[int, float] = {}
        for idx, activation in self._layer_outputs.items():
            if activation.dim() >= 3:
                last_token = activation[0, -1, :]
            else:
                last_token = activation[0, -1]
            proj = torch.matmul(last_token, self.model.lm_head.weight.T[:vocab_size])
            prob = torch.softmax(proj, dim=-1)[target_token_id].item()
            results[idx] = prob
        return results

    def trace_token_prediction(self, inputs: torch.Tensor, target_token_id: int, vocab_size: int) -> List[Tuple[int, float]]:
        num_layers = len(self.model.blocks) if hasattr(self.model, "blocks") else 0
        layers = list(range(num_layers))
        results = self.analyze(inputs, layers, target_token_id, vocab_size)
        return sorted(results.items(), key=lambda x: x[0])
