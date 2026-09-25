from __future__ import annotations

import logging
from typing import Optional, Dict, Any, List
import torch

logger = logging.getLogger(__name__)


class PowerManager:
    def __init__(self, tdp_watts: float = 350.0):
        self.tdp_watts = tdp_watts
        self.current_power = 0.0
        self.power_budget = tdp_watts
        self.allocations: Dict[str, float] = {}

    def set_power_budget(self, budget_watts: float) -> None:
        self.power_budget = budget_watts

    def allocate_power(self, component: str, watts: float) -> bool:
        available = self.power_budget - sum(self.allocations.values())
        if watts <= available:
            self.allocations[component] = watts
            return True
        return False

    def release_power(self, component: str) -> None:
        self.allocations.pop(component, None)

    def get_power_usage(self) -> Dict[str, Any]:
        return {
            "current_power_watts": self.current_power,
            "budget_watts": self.power_budget,
            "allocations": dict(self.allocations),
            "headroom": self.power_budget - sum(self.allocations.values()),
        }


class DVFSController:
    def __init__(self, min_freq_ghz: float = 0.5, max_freq_ghz: float = 2.5):
        self.min_freq_ghz = min_freq_ghz
        self.max_freq_ghz = max_freq_ghz
        self.current_freq_ghz = max_freq_ghz
        self.voltage_v = 1.0

    def set_frequency(self, freq_ghz: float) -> None:
        self.current_freq_ghz = max(self.min_freq_ghz, min(self.max_freq_ghz, freq_ghz))

    def scale_for_power(self, power_remaining_ratio: float) -> float:
        target = self.min_freq_ghz + (self.max_freq_ghz - self.min_freq_ghz) * max(0.0, min(1.0, power_remaining_ratio))
        self.set_frequency(target)
        return self.current_freq_ghz

    def estimate_power(self, utilization: float) -> float:
        alpha = 1.0
        beta = 2.0
        return self.voltage_v * self.current_freq_ghz * (alpha * utilization + beta * (1 - utilization))


class PowerBudgetAllocator:
    def __init__(self, total_budget_watts: float = 350.0):
        self.total_budget = total_budget_watts
        self.components: Dict[str, float] = {}

    def allocate(self, component: str, watts: float) -> None:
        self.components[component] = watts

    def rebalance(self, priorities: Dict[str, float]) -> Dict[str, float]:
        total_priority = sum(priorities.values())
        if total_priority == 0:
            return {}
        allocations = {}
        allocated = 0.0
        for component, priority in sorted(priorities.items(), key=lambda x: x[1], reverse=True):
            share = (priority / total_priority) * self.total_budget
            allocations[component] = share
            allocated += share
        return allocations
