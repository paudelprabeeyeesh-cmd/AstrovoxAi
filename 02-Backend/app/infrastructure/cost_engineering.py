"""Cost engineering for cloud optimization."""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class OptimizationType(Enum):
    RIGHTSIZING = "rightsizing"
    RESERVED_INSTANCES = "reserved_instances"
    SPOT_INSTANCES = "spot_instances"
    IDLE_RESOURCES = "idle_resources"
    STORAGE_TIERING = "storage_tiering"


@dataclass
class CostOptimization:
    optimization_id: str
    optimization_type: OptimizationType
    resource_id: str
    current_cost: float
    projected_savings: float
    description: str
    implemented: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class CostEngineering:
    _optimizations: List[CostOptimization] = []

    @classmethod
    def add_optimization(cls, optimization: CostOptimization) -> None:
        cls._optimizations.append(optimization)

    @classmethod
    def get_total_potential_savings(cls) -> float:
        return sum(o.projected_savings for o in cls._optimizations if not o.implemented)

    @classmethod
    def mark_implemented(cls, optimization_id: str) -> bool:
        for opt in cls._optimizations:
            if opt.optimization_id == optimization_id:
                opt.implemented = True
                return True
        return False

    @classmethod
    def get_recommendations(cls) -> List[CostOptimization]:
        return [o for o in cls._optimizations if not o.implemented]
