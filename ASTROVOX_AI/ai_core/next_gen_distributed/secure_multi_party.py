"""Secure multi-party computation for joint inference without data sharing."""

from __future__ import annotations

import logging
from typing import Callable, List

import torch

logger = logging.getLogger(__name__)


class SecureMultiPartyComputation:
    def __init__(self, num_parties: int, threshold: int = 2):
        self.num_parties = num_parties
        self.threshold = threshold
        self.shares: Dict[int, List[torch.Tensor]] = {}

    def secret_share(self, secret: torch.Tensor) -> List[torch.Tensor]:
        shares = [torch.randn_like(secret) for _ in range(self.num_parties)]
        shares[0] = secret - sum(shares[1:])
        return shares

    def reconstruct(self, shares: List[torch.Tensor]) -> torch.Tensor:
        return sum(shares[:self.threshold])

    def secure_compute(self, func: Callable, *inputs: torch.Tensor) -> torch.Tensor:
        all_shares = [self.secret_share(inp) for inp in inputs]
        partial_results = []
        for i in range(self.num_parties):
            party_inputs = [shares[i] for shares in all_shares]
            partial_results.append(func(*party_inputs))
        return self.reconstruct(partial_results)

    def secure_average(self, tensors: List[torch.Tensor]) -> torch.Tensor:
        def avg_func(*args: torch.Tensor) -> torch.Tensor:
            return sum(args) / len(args)
        return self.secure_compute(avg_func, *tensors)
