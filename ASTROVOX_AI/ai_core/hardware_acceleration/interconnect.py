from __future__ import annotations

import logging
import math
from typing import Dict, Any, List, Tuple
import torch

logger = logging.getLogger(__name__)


class InterconnectOptimizer:
    def __init__(self, topology: str = "mesh", num_nodes: int = 8):
        self.topology = topology
        self.num_nodes = num_nodes
        self.bandwidth_gbps = 400.0
        self.latency_ns = 100.0
        self.routing_table: Dict[Tuple[int, int], List[int]] = {}
        self._build_routing_table()

    def _build_routing_table(self) -> None:
        for src in range(self.num_nodes):
            for dst in range(self.num_nodes):
                if src != dst:
                    self.routing_table[(src, dst)] = self._compute_route(src, dst)

    def _compute_route(self, src: int, dst: int) -> List[int]:
        if self.topology == "mesh":
            path = [src]
            x, y = src % 4, src // 4
            while x != dst % 4:
                x += 1 if x < dst % 4 else -1
                path.append(y * 4 + x)
            while y != dst // 4:
                y += 1 if y < dst // 4 else -1
                path.append(y * 4 + x)
            return path
        if self.topology == "torus":
            path = [src]
            x, y = src % 4, src // 4
            while x != dst % 4:
                x = (x + (1 if x < dst % 4 else -1)) % 4
                path.append(y * 4 + x)
            while y != dst // 4:
                y = (y + (1 if y < dst // 4 else -1)) % 4
                path.append(y * 4 + x)
            return path
        return [src, dst]

    def compute_hop_count(self, src: int, dst: int) -> int:
        return len(self.routing_table.get((src, dst), [src, dst])) - 1

    def estimate_latency(self, src: int, dst: int, message_size_bytes: int) -> float:
        hops = self.compute_hop_count(src, dst)
        transfer_time_ns = (message_size_bytes / (self.bandwidth_gbps * 1e9 / 8)) * 1e9
        return hops * self.latency_ns + transfer_time_ns

    def route(self, src: int, dst: int) -> List[int]:
        return self.routing_table.get((src, dst), [src, dst])

    def optimize_collective(self, operation: str, num_nodes: int) -> Dict[str, Any]:
        if operation == "all_reduce":
            return {"algorithm": "ring", "steps": num_nodes - 1, "message_size_factor": 2 * (num_nodes - 1) / num_nodes}
        if operation == "all_gather":
            return {"algorithm": "ring", "steps": num_nodes - 1}
        if operation == "broadcast":
            return {"algorithm": "tree", "steps": num_nodes.bit_length()}
        if operation == "reduce_scatter":
            return {"algorithm": "ring", "steps": num_nodes - 1}
        return {"algorithm": "direct", "steps": 1}

    def simulate_traffic(self, traffic_matrix: torch.Tensor) -> Dict[str, float]:
        total_bytes = traffic_matrix.sum().item()
        max_load = traffic_matrix.max().item()
        avg_latency = self.latency_ns * self.num_nodes
        return {
            "total_bytes": total_bytes,
            "max_link_load_bytes": max_load,
            "estimated_latency_ns": avg_latency,
            "congestion_ratio": max_load / max(self.bandwidth_gbps * 1e9 / 8, 1e-6),
        }


class NVLinkTopology:
    def __init__(self, num_gpus: int = 8, switches_per_gpu: int = 6):
        self.num_gpus = num_gpus
        self.switches_per_gpu = switches_per_gpu
        self.bandwidth_gbps = 600.0
        self.latency_ns = 20.0
        self.topology = self._build_topology()

    def _build_topology(self) -> Dict[Tuple[int, int], float]:
        return {(i, j): self.bandwidth_gbps for i in range(self.num_gpus) for j in range(self.num_gpus) if i != j}

    def peer_to_peer_bandwidth(self, src: int, dst: int) -> float:
        if src == dst:
            return 0.0
        return self.topology.get((src, dst), self.bandwidth_gbps)

    def all_reduce_latency(self, num_elements: int) -> float:
        message_size_bytes = num_elements * 4
        return (message_size_bytes / (self.bandwidth_gbps * 1e9 / 8)) * 1e9 + self.latency_ns

    def estimate_collective_latency(self, operation: str, num_elements: int) -> float:
        if operation == "all_reduce":
            return self.all_reduce_latency(num_elements) * math.log2(self.num_gpus)
        if operation == "all_gather":
            return self.all_reduce_latency(num_elements) * (self.num_gpus - 1)
        return self.all_reduce_latency(num_elements)


class PCIeTopology:
    def __init__(self, num_devices: int = 4, generation: str = "gen4"):
        self.num_devices = num_devices
        self.generation = generation
        self.bandwidth_gbps = 64.0 if generation == "gen4" else 32.0
        self.latency_ns = 100.0

    def transfer_time(self, size_bytes: int) -> float:
        return (size_bytes / (self.bandwidth_gbps * 1e9 / 8)) * 1e9 + self.latency_ns

    def estimate_pcie_bottleneck(self, data_transfer_bytes: int) -> Dict[str, float]:
        transfer_time_us = self.transfer_time(data_transfer_bytes) / 1e3
        return {
            "transfer_time_us": transfer_time_us,
            "bandwidth_utilization": min(1.0, data_transfer_bytes / (self.bandwidth_gbps * 1e9 / 8 * transfer_time_us * 1e-6)),
        }
