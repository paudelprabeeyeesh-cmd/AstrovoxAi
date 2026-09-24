import numpy as np
import pytest
from ..expert_capacity_factor import ExpertCapacityFactor


class TestExpertCapacityFactor:
    def test_compute_capacity(self):
        ecf = ExpertCapacityFactor(capacity_factor=1.0, num_experts=4)
        cap = ecf.compute_capacity(batch_size=8)
        assert cap >= 1

    def test_route_with_fallback(self):
        ecf = ExpertCapacityFactor(capacity_factor=1.0, num_experts=4)
        B, T = 2, 5
        probs = np.random.rand(B * T, 4)
        probs = probs / probs.sum(axis=-1, keepdims=True)
        topk_idx = np.argsort(probs, axis=-1)[:, :2]
        accepted, overflow = ecf.route_with_fallback(probs, topk_idx)
        assert accepted.shape == (B * T, 2)
        assert isinstance(overflow, list)
