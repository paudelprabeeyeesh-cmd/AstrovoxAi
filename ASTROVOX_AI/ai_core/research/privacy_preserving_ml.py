from typing import Optional, Dict
import torch
import torch.nn as nn


class PrivacyPreservingML:
    def __init__(self, epsilon: float = 1.0, delta: float = 1e-5, noise_multiplier: float = 1.0):
        self.epsilon = epsilon
        self.delta = delta
        self.noise_multiplier = noise_multiplier
        self.privacy_budget = epsilon

    def add_gaussian_noise(self, gradients: Dict[str, torch.Tensor], noise_scale: Optional[float] = None) -> Dict[str, torch.Tensor]:
        noise_scale = noise_scale or self.noise_multiplier
        noisy_gradients = {}
        for key, grad in gradients.items():
            noise = torch.randn_like(grad) * noise_scale
            noisy_gradients[key] = grad + noise
        return noisy_gradients

    def clip_gradients(self, gradients: Dict[str, torch.Tensor], max_norm: float = 1.0) -> Dict[str, torch.Tensor]:
        total_norm = torch.norm(torch.stack([torch.norm(grad) for grad in gradients.values()]))
        clip_coef = max_norm / (total_norm + 1e-8)
        if clip_coef < 1.0:
            return {k: v * clip_coef for k, v in gradients.items()}
        return gradients

    def dp_sgd_step(self, model: nn.Module, batch: torch.Tensor, loss_fn: callable, optimizer: torch.optim.Optimizer, max_norm: float = 1.0) -> float:
        optimizer.zero_grad()
        output = model(batch)
        loss = loss_fn(output)
        loss.backward()
        grads = {n: p.grad.clone() for n, p in model.named_parameters() if p.grad is not None}
        clipped = self.clip_gradients(grads, max_norm)
        noisy = self.add_gaussian_noise(clipped)
        for n, p in model.named_parameters():
            if n in noisy:
                p.grad = noisy[n]
        optimizer.step()
        return loss.item()
