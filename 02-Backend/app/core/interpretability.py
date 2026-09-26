"""
Interpretability layer: Sparse Autoencoders (SAE), circuit analysis, activation patching, logit lens, attribution, mechanistic interpretability, neuron analysis, attention visualization.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

logger = logging.getLogger(__name__)


class SparseAutoencoder(nn.Module):
    """Sparse Autoencoder for decomposing model activations into interpretable features."""

    def __init__(self, input_dim: int, hidden_dim: int, sparsity_coef: float = 0.1, lr: float = 1e-3):
        super().__init__()
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.sparsity_coef = sparsity_coef
        self.encoder = nn.Linear(input_dim, hidden_dim, bias=True)
        self.decoder = nn.Linear(hidden_dim, input_dim, bias=True)
        self.optimizer = torch.optim.Adam(list(self.encoder.parameters()) + list(self.decoder.parameters()), lr=lr)

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        z = torch.relu(self.encoder(x))
        reconstructed = self.decoder(z)
        recon_loss = F.mse_loss(reconstructed, x)
        l1_loss = z.abs().mean()
        loss = recon_loss + self.sparsity_coef * l1_loss
        return reconstructed, z, loss

    def train_step(self, x: torch.Tensor) -> float:
        self.optimizer.zero_grad()
        _, _, loss = self.forward(x)
        loss.backward()
        self.optimizer.step()
        return loss.item()

    def encode(self, x: torch.Tensor) -> torch.Tensor:
        with torch.no_grad():
            return torch.relu(self.encoder(x))

    def decode(self, z: torch.Tensor) -> torch.Tensor:
        with torch.no_grad():
            return self.decoder(z)

    def get_features(self, x: torch.Tensor, threshold: float = 0.1) -> List[int]:
        with torch.no_grad():
            encoded = self.encode(x)
            active = (encoded > threshold).nonzero(as_tuple=True)[1]
        return active.tolist()


class TopKSparseAutoencoder(SparseAutoencoder):
    def __init__(self, input_dim: int, hidden_dim: int, k: int = 50, sparsity_coef: float = 0.1, lr: float = 1e-3):
        super().__init__(input_dim, hidden_dim, sparsity_coef, lr)
        self.k = k

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        z = self.encoder(x)
        topk_values, topk_indices = torch.topk(z, k=self.k, dim=-1)
        z_sparse = torch.zeros_like(z)
        z_sparse.scatter_(-1, topk_indices, topk_values)
        reconstructed = self.decoder(z_sparse)
        recon_loss = F.mse_loss(reconstructed, x)
        loss = recon_loss
        return reconstructed, z_sparse, loss


def train_sae(model: nn.Module, dataloader, device: str = "cpu", epochs: int = 10) -> SparseAutoencoder:
    """Train SAE on model activations."""
    input_dim = 64
    hidden_dim = 128
    sae = SparseAutoencoder(input_dim=input_dim, hidden_dim=hidden_dim)
    optimizer = torch.optim.Adam(sae.parameters(), lr=1e-3)
    for epoch in range(epochs):
        total_loss = 0.0
        for batch in dataloader:
            x = batch["activations"]
            _, _, loss = sae(x)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            total_loss += loss.item()
        logger.info("SAE epoch %d: loss=%.4f", epoch, total_loss / max(len(dataloader), 1))
    return sae


@dataclass
class ActivationPatch:
    layer: int
    position: int
    original_activation: Optional[np.ndarray] = None
    patched_activation: Optional[np.ndarray] = None


def circuit_analysis(model: nn.Module, prompt_ids: torch.Tensor, target_token_id: int) -> List[ActivationPatch]:
    """Trace causal path of a specific decision through the model's layers."""
    patches: List[ActivationPatch] = []
    hooks = []
    activations: Dict[int, torch.Tensor] = {}

    def make_hook(layer_idx: int):
        def hook(module, input, output):
            activations[layer_idx] = output.detach().cpu().numpy()
        return hook

    for idx, layer in enumerate(model.blocks if hasattr(model, "blocks") else []):
        hooks.append(layer.register_forward_hook(make_hook(idx)))
    try:
        with torch.no_grad():
            logits = model(prompt_ids)
        target_logits = logits[0, -1, :]
        target_prob = float(torch.softmax(target_logits, dim=-1)[target_token_id])
        for layer_idx, activation in activations.items():
            patch = ActivationPatch(layer=layer_idx, position=prompt_ids.shape[1] - 1, original_activation=activation)
            patches.append(patch)
    finally:
        for hook in hooks:
            hook.remove()
    return patches


class ActivationPatcher:
    def __init__(self, model: nn.Module):
        self.model = model
        self.hooks = []
        self._original_state: Dict[str, Any] = {}

    def _get_activation(self, name: str):
        def hook(module, input, output):
            self._original_state[name] = output.clone() if isinstance(output, torch.Tensor) else output
        return hook

    def register_hook(self, layer_name: str) -> None:
        for name, module in self.model.named_modules():
            if name == layer_name:
                hook = module.register_forward_hook(self._get_activation(name))
                self.hooks.append(hook)
                break

    def apply_patch(self, layer_name: str, patch_fn) -> None:
        def hook(module, input, output):
            return patch_fn(output)
        for name, module in self.model.named_modules():
            if name == layer_name:
                self.hooks.append(module.register_forward_hook(hook))
                break

    def remove_hooks(self) -> None:
        for hook in self.hooks:
            hook.remove()
        self.hooks = []

    def patch_forward(self, inputs: torch.Tensor, layer_name: str, patch_fn, attention_mask: Optional[torch.Tensor] = None) -> torch.Tensor:
        self.apply_patch(layer_name, patch_fn)
        with torch.no_grad():
            if attention_mask is not None:
                outputs = self.model(inputs, attention_mask=attention_mask)
            else:
                outputs = self.model(inputs)
        self.remove_hooks()
        return outputs.logits if hasattr(outputs, "logits") else outputs

    def restore_forward(self, inputs: torch.Tensor, layer_name: str, attention_mask: Optional[torch.Tensor] = None) -> torch.Tensor:
        original = self._original_state.get(layer_name)
        if original is None:
            logger.warning("No original activation stored for %s", layer_name)
            return self._forward_default(inputs, attention_mask)
        patch_fn = lambda output: original.to(output.device)
        return self.patch_forward(inputs, layer_name, patch_fn, attention_mask)

    def _forward_default(self, inputs: torch.Tensor, attention_mask: Optional[torch.Tensor] = None) -> torch.Tensor:
        with torch.no_grad():
            if attention_mask is not None:
                outputs = self.model(inputs, attention_mask=attention_mask)
            else:
                outputs = self.model(inputs)
        return outputs.logits if hasattr(outputs, "logits") else outputs


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


class AttentionVisualizer:
    def __init__(self, model: nn.Module):
        self.model = model
        self.attention_weights: List[torch.Tensor] = []

    def register_hooks(self) -> None:
        def hook(module, input, output):
            if isinstance(output, tuple) and len(output) > 1:
                self.attention_weights.append(output[1].detach().cpu())
        for module in self.model.modules():
            if hasattr(module, "num_heads") and hasattr(module, "head_dim"):
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

