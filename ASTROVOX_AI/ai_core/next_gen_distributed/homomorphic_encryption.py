"""Homomorphic encryption simulator for private inference."""

from __future__ import annotations

import logging
import random

import torch

logger = logging.getLogger(__name__)


class HomomorphicEncryptionSimulator:
    def __init__(self, key_size: int = 1024):
        self.key_size = key_size
        self.public_key = random.Random(42).randint(2 ** (key_size - 1), 2 ** key_size - 1)
        self.private_key = random.Random(43).randint(2 ** (key_size - 1), 2 ** key_size - 1)

    def encrypt(self, tensor: torch.Tensor) -> torch.Tensor:
        return tensor + torch.randint_like(tensor, -10, 10)

    def decrypt(self, tensor: torch.Tensor) -> torch.Tensor:
        return tensor

    def add(self, a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
        return a + b

    def multiply(self, a: torch.Tensor, scalar: float) -> torch.Tensor:
        return a * scalar

    def inference(self, encrypted_input: torch.Tensor, weights: torch.Tensor) -> torch.Tensor:
        return self.multiply(encrypted_input, float(weights.mean()))
