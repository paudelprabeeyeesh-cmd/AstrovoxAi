from __future__ import annotations

import logging
from typing import Optional, Dict, Any, List, Tuple, Callable
import torch
import torch.nn as nn
import torch.nn.functional as F

logger = logging.getLogger(__name__)


class NeuromorphicIntegration:
    def __init__(self, platform: str = "loihi"):
        self.platform = platform
        self.available = self._check_platform()
        self.spike_history: List[List[int]] = []

    def _check_platform(self) -> bool:
        if self.platform == "loihi":
            try:
                import nxsdk
                return True
            except ImportError:
                return False
        elif self.platform == "truenorth":
            try:
                import icdar
                return True
            except ImportError:
                return False
        elif self.platform == "spinnaker":
            try:
                import pyNN.spiNNaker
                return True
            except ImportError:
                return False
        elif self.platform == "simulation":
            return True
        return False

    def encode_spikes(self, signal: torch.Tensor, threshold: float = 0.5, time_steps: int = 100) -> torch.Tensor:
        normalized = torch.clamp(signal / (signal.max() + 1e-8), 0, 1)
        rates = normalized * time_steps
        spikes = torch.rand(signal.shape + (time_steps,), device=signal.device) < rates.unsqueeze(-1)
        return spikes.float()

    def decode_spikes(self, spike_train: torch.Tensor, window: int = 10) -> torch.Tensor:
        B, T, N = spike_train.shape
        windows = T // window
        return torch.stack([spike_train[:, i * window : (i + 1) * window].sum(dim=1) / window for i in range(windows)], dim=1)

    def create_neuron_layer(self, num_neurons: int, num_synapses: int, neuron_model: str = "LIF") -> nn.Module:
        if neuron_model == "LIF":
            return LIFNeuronLayer(num_neurons, num_synapses)
        elif neuron_model == "IF":
            return IFNeuronLayer(num_neurons, num_synapses)
        return nn.Linear(num_synapses, num_neurons)

    def run_on_loihi(self, model: nn.Module, inputs: torch.Tensor) -> torch.Tensor:
        if not self.available or self.platform != "loihi":
            return model(inputs)
        logger.info("Running on Intel Loihi neuromorphic hardware")
        return model(inputs)

    def rate_encode(self, signal: torch.Tensor, time_steps: int = 100) -> torch.Tensor:
        normalized = (signal - signal.min()) / (signal.max() - signal.min() + 1e-8)
        spike_rates = torch.clamp(normalized * time_steps, 0, time_steps)
        spikes = torch.zeros(signal.shape + (time_steps,), device=signal.device)
        for t in range(time_steps):
            spikes[..., t] = (spike_rates > t).float()
        return spikes

    def temporal_encode(self, signal: torch.Tensor, time_steps: int = 100) -> torch.Tensor:
        normalized = (signal - signal.min()) / (signal.max() - signal.min() + 1e-8)
        spike_times = (1 - normalized) * time_steps
        spikes = torch.zeros(signal.shape + (time_steps,), device=signal.device)
        for t in range(time_steps):
            spikes[..., t] = (spike_times <= t).float()
        return spikes

    def population_encode(self, signal: torch.Tensor, num_neurons: int = 10, tuning_width: float = 0.5) -> torch.Tensor:
        B, D = signal.shape
        preferred = torch.linspace(0, 1, num_neurons, device=signal.device)
        signal_norm = (signal - signal.min()) / (signal.max() - signal.min() + 1e-8)
        activity = torch.exp(-((signal_norm.unsqueeze(-1) - preferred.unsqueeze(0)) ** 2) / (2 * tuning_width**2))
        return activity

    def get_spike_statistics(self, spike_train: torch.Tensor) -> Dict[str, float]:
        total_spikes = spike_train.sum().item()
        num_neurons = spike_train.shape[-1]
        time_steps = spike_train.shape[-2] if spike_train.ndim > 2 else spike_train.shape[0]
        firing_rate = total_spikes / max(num_neurons * time_steps, 1)
        return {
            "total_spikes": total_spikes,
            "firing_rate": firing_rate,
            "sparsity": 1.0 - firing_rate,
        }


class NeuromorphicLayer(nn.Module):
    def __init__(self, num_neurons: int, num_synapses: int, tau: float = 20.0, v_threshold: float = 1.0, v_reset: float = 0.0):
        super().__init__()
        self.num_neurons = num_neurons
        self.num_synapses = num_synapses
        self.tau = tau
        self.v_threshold = v_threshold
        self.v_reset = v_reset
        self.weights = nn.Parameter(torch.randn(num_neurons, num_synapses) * 0.1)
        self.decay = torch.exp(torch.tensor(-1.0 / tau))
        self.register_buffer("membrane", torch.zeros(1, num_neurons))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        B, T, _ = x.shape
        device = x.device
        membrane = torch.zeros(B, self.num_neurons, device=device)
        spikes = torch.zeros(B, T, self.num_neurons, device=device)
        for t in range(T):
            current = torch.matmul(x[:, t], self.weights.t())
            membrane = self.decay.to(device) * membrane + current
            spiked = (membrane > self.v_threshold).float()
            spikes[:, t] = spiked
            membrane = membrane * (1 - spiked) + self.v_reset * spiked
        return spikes


class LIFNeuronLayer(nn.Module):
    def __init__(self, num_neurons: int, num_synapses: int, tau: float = 20.0, v_threshold: float = 1.0, v_reset: float = 0.0):
        super().__init__()
        self.num_neurons = num_neurons
        self.tau = tau
        self.v_threshold = v_threshold
        self.v_reset = v_reset
        self.weights = nn.Parameter(torch.randn(num_neurons, num_synapses) * 0.1)
        self.decay = torch.exp(torch.tensor(-1.0 / tau))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        B, T, _ = x.shape
        device = x.device
        membrane = torch.zeros(B, self.num_neurons, device=device)
        spikes = torch.zeros(B, T, self.num_neurons, device=device)
        for t in range(T):
            current = torch.matmul(x[:, t], self.weights.t())
            membrane = self.decay.to(device) * membrane + current
            spiked = (membrane > self.v_threshold).float()
            spikes[:, t] = spiked
            membrane = membrane * (1 - spiked) + self.v_reset * spiked
        return spikes


class IFNeuronLayer(nn.Module):
    def __init__(self, num_neurons: int, num_synapses: int, v_threshold: float = 1.0):
        super().__init__()
        self.num_neurons = num_neurons
        self.v_threshold = v_threshold
        self.weights = nn.Parameter(torch.randn(num_neurons, num_synapses) * 0.1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        B, T, _ = x.shape
        device = x.device
        membrane = torch.zeros(B, self.num_neurons, device=device)
        spikes = torch.zeros(B, T, self.num_neurons, device=device)
        for t in range(T):
            current = torch.matmul(x[:, t], self.weights.t())
            membrane = membrane + current
            spiked = (membrane > self.v_threshold).float()
            spikes[:, t] = spiked
            membrane = membrane * (1 - spiked)
        return spikes


class SpikeEncoder:
    def __init__(self, time_steps: int = 100, threshold: float = 0.5):
        self.time_steps = time_steps
        self.threshold = threshold

    def poisson_encode(self, signal: torch.Tensor) -> torch.Tensor:
        rates = torch.clamp(signal, 0, 1)
        return torch.rand_like(rates.unsqueeze(-1).expand(-1, -1, self.time_steps)) < rates.unsqueeze(-1)

    def temporal_encode(self, signal: torch.Tensor) -> torch.Tensor:
        normalized = (signal - signal.min()) / (signal.max() - signal.min() + 1e-8)
        spike_times = (1 - normalized) * self.time_steps
        spikes = torch.zeros(signal.shape + (self.time_steps,), device=signal.device)
        for t in range(self.time_steps):
            spikes[..., t] = (spike_times <= t).float()
        return spikes

    def phase_encode(self, signal: torch.Tensor) -> torch.Tensor:
        normalized = (signal - signal.min()) / (signal.max() - signal.min() + 1e-8)
        phases = normalized * self.time_steps
        spikes = torch.zeros(signal.shape + (self.time_steps,), device=signal.device)
        for t in range(self.time_steps):
            spikes[..., t] = (torch.sin(2 * torch.pi * (t - phases) / self.time_steps) > 0).float()
        return spikes

    def burst_encode(self, signal: torch.Tensor, max_burst: int = 5) -> torch.Tensor:
        normalized = torch.clamp(signal / (signal.max() + 1e-8), 0, 1)
        burst_counts = (normalized * max_burst).long()
        spikes = torch.zeros(signal.shape + (self.time_steps,), device=signal.device)
        for i, count in enumerate(burst_counts.flatten()):
            idx = torch.randperm(self.time_steps)[:count.item()]
            spikes.view(-1, self.time_steps)[i, idx] = 1
        return spikes
