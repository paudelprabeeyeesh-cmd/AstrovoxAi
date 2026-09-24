import numpy as np
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass
class CognitiveResource:
    memory_capacity: float
    processing_bandwidth: float
    attentional_units: int
    parallel_threads: int


class CognitiveExpander:
    def __init__(self, initial_memory: float = 100.0, initial_bandwidth: float = 10.0):
        self.memory_capacity = float(initial_memory)
        self.processing_bandwidth = float(initial_bandwidth)
        self.attentional_units = 8
        self.parallel_threads = 4
        self.expansion_log: List[Dict[str, Any]] = []

    def expand_memory(self, additional_capacity: float) -> Dict[str, Any]:
        additional_capacity = float(np.clip(additional_capacity, 0.0, self.memory_capacity * 10.0))
        old_capacity = self.memory_capacity
        self.memory_capacity += additional_capacity
        utilization = self._compute_memory_utilization()
        entry = {
            "type": "memory",
            "old_capacity": old_capacity,
            "new_capacity": self.memory_capacity,
            "added": additional_capacity,
            "utilization": utilization,
        }
        self.expansion_log.append(entry)
        return entry

    def expand_bandwidth(self, additional_bandwidth: float) -> Dict[str, Any]:
        additional_bandwidth = float(np.clip(additional_bandwidth, 0.0, self.processing_bandwidth * 10.0))
        old_bandwidth = self.processing_bandwidth
        self.processing_bandwidth += additional_bandwidth
        efficiency = self._compute_bandwidth_efficiency()
        entry = {
            "type": "bandwidth",
            "old_bandwidth": old_bandwidth,
            "new_bandwidth": self.processing_bandwidth,
            "added": additional_bandwidth,
            "efficiency": efficiency,
        }
        self.expansion_log.append(entry)
        return entry

    def allocate_attentional_units(self, n_units: int) -> Dict[str, Any]:
        n_units = max(1, n_units)
        self.attentional_units = n_units
        allocation = self._compute_attentional_allocation()
        entry = {
            "type": "attention",
            "units": n_units,
            "allocation": allocation,
        }
        self.expansion_log.append(entry)
        return entry

    def scale_parallelism(self, n_threads: int) -> Dict[str, Any]:
        n_threads = max(1, n_threads)
        self.parallel_threads = n_threads
        speedup = self._compute_speedup()
        entry = {
            "type": "parallelism",
            "threads": n_threads,
            "theoretical_speedup": speedup,
        }
        self.expansion_log.append(entry)
        return entry

    def _compute_memory_utilization(self) -> float:
        return min(1.0, np.log1p(self.memory_capacity) / (np.log1p(self.memory_capacity) + 1.0))

    def _compute_bandwidth_efficiency(self) -> float:
        return 1.0 / (1.0 + np.exp(-0.1 * (self.processing_bandwidth - 10.0)))

    def _compute_attentional_allocation(self) -> float:
        return float(np.mean(np.random.dirichlet(np.ones(self.attentional_units))))

    def _compute_speedup(self) -> float:
        return float(self.parallel_threads / (1.0 + 0.1 * np.log1p(self.parallel_threads)))

    def get_cognitive_profile(self) -> CognitiveResource:
        return CognitiveResource(
            memory_capacity=self.memory_capacity,
            processing_bandwidth=self.processing_bandwidth,
            attentional_units=self.attentional_units,
            parallel_threads=self.parallel_threads,
        )

    def get_expansion_stats(self) -> Dict[str, Any]:
        return {
            "memory_capacity": self.memory_capacity,
            "processing_bandwidth": self.processing_bandwidth,
            "attentional_units": self.attentional_units,
            "parallel_threads": self.parallel_threads,
            "total_expansions": len(self.expansion_log),
        }
