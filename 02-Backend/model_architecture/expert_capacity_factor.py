import numpy as np


class ExpertCapacityFactor:
    def __init__(self, capacity_factor=1.25, num_experts=8):
        self.capacity_factor = capacity_factor
        self.num_experts = num_experts

    def compute_capacity(self, batch_size):
        tokens_per_expert = (batch_size * self.capacity_factor) / self.num_experts
        return max(1, int(np.ceil(tokens_per_expert)))

    def route_with_fallback(self, probs, topk_idx):
        B, T = probs.shape
        capacities = {e: self.compute_capacity(B) for e in range(self.num_experts)}
        counts = {e: 0 for e in range(self.num_experts)}
        accepted = np.zeros_like(topk_idx, dtype=bool)
        overflow = []

        for i in range(B):
            assigned = []
            for j in range(topk_idx.shape[1]):
                e = topk_idx[i, j]
                if counts[e] < capacities[e]:
                    counts[e] += 1
                    accepted[i, j] = True
                    assigned.append(e)
            if len(assigned) == 0:
                overflow.append(i)

        return accepted, overflow
