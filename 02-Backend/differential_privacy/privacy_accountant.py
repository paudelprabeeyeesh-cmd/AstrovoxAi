from differential_privacy.typing import DPParams


class PrivacyAccountant:
    def __init__(self):
        self.mechanisms = []

    def add(self, mechanism) -> None:
        self.mechanisms.append(mechanism)

    def total_budget(self) -> DPParams:
        total_epsilon = 0.0
        for m in self.mechanisms:
            total_epsilon += m.budget().epsilon
        delta = 0.0
        for m in self.mechanisms:
            delta = max(delta, m.budget().delta)
        return DPParams(epsilon=total_epsilon, delta=delta)
