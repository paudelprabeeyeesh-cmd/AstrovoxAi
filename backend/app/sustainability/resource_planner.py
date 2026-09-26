"""Resource planner for sustainable allocation."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ResourceAllocation:
    allocation_id: str
    service: str
    cpu_cores: float
    memory_mb: int
    gpu_count: int
    estimated_power_w: float
    carbon_g: float


class ResourcePlanner:
    def __init__(self) -> None:
        self._allocations: List[ResourceAllocation] = []

    def plan(self, service: str, cpu_cores: float, memory_mb: int, gpu_count: int = 0) -> ResourceAllocation:
        power_w = cpu_cores * 10 + gpu_count * 200 + memory_mb * 0.01
        carbon_g = power_w * 0.4
        allocation = ResourceAllocation(
            allocation_id=service,
            service=service,
            cpu_cores=cpu_cores,
            memory_mb=memory_mb,
            gpu_count=gpu_count,
            estimated_power_w=power_w,
            carbon_g=carbon_g,
        )
        self._allocations.append(allocation)
        return allocation


resource_planner = ResourcePlanner()
