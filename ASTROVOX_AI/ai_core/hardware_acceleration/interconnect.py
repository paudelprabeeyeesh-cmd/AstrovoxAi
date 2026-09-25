from __future__ import annotations

import logging
from typing import Optional, Dict, Any, List, Tuple
import torch

logger = logging.getLogger(__name__)


class InterconnectOptimizer:
    def __init__(self, topology: str = "mesh", num_nodes: int = 8):
        self.topology = topology
        self.num_nodes = num_nodes
        self.bandwidth_gbps = 400.0
        self.latency_ns = 100.0
        self.routing_table: Dict[Tuple[int, int], List[int]] = {}

    def compute_hop_count(self, src: int, dst: int) -> int:
        if self.topology == "mesh":
            src_x, src_y = src % 4, src // 4
            dst_x, dst_y = dst % 4, dst // 4
            return abs(src_x - dst_x) + abs(src_y - dst_y)
        if self.topology == "torus":
            src_x, src_y = src % 4, src // 4
            dst_x, dst_y = dst % 4, dst // 4
            dx = min(abs(src_x - dst_x), 4 - abs(src_x - dst_x))
            dy = min(abs(src_y - dst_y), 4 - abs(src_y - dst_y))
            return dx + dy
        return abs(src - dst)

    def estimate_latency(self, src: int, dst: int, message_size_bytes: int) -> float:
        hops = self.compute_hop_count(src, dst)
        transfer_time_ns = (message_size_bytes / (self.bandwidth_gbps * 1e9 / 8)) * 1e9
        return hops * self.latency_ns + transfer_time_ns

    def route(self, src: int, dst: int) -> List[int]:
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
        return [src, dst]

    def optimize_collective(self, operation: str, num_nodes: int) -> Dict[str, Any]:
        if operation == "all_reduce":
            return {"algorithm": "ring", "steps": num_nodes - 1, "message_size_factor": 2 * (num_nodes - 1) / num_nodes}
        if operation == "all_gather":
            return {"algorithm": "ring", "steps": num_nodes - 1}
        if operation == "broadcast":
            return {"algorithm": "tree", "steps": num_nodes.bit_length()}
        return {"algorithm": "direct", "steps": 1}


class NVLinkTopology:
    def __init__(self, num_gpus: int = 8, switches_per_gpu: int = 6):
        self.num_gpus = num_gpus
        self.switches_per_gpu = switches_per_gpu
        self.bandwidth_gbps = 600.0
        self.latency_ns = 20.0

    def peer_to_peer_bandwidth(self, src: int, dst: int) -> float:
        if src == dst:
            return 0.0
        return self.bandwidth_gbps

    def all_reduce_latency(self, num_elements: int) -> float:
        message_size_bytes = num_elements * 4
        return (message_size_bytes / (self.bandwidth_gbps * 1e9 / 8)) * 1e9 + self.latency_ns


class PCIeTopology:
    def __init__(self, num_devices: int = 4, generation: str = "gen4"):
        self.num_devices = num_devices
        self.generation = generation
        self.bandwidth_gbps = 64.0 if generation == "gen4" else 32.0
        self.latency_ns = 100.0

    def transfer_time(self, size_bytes: int) -> float:
        return (size_bytes / (self.bandwidth_gbps * 1e9 / 8)) * 1e9 + self.latency_ns
