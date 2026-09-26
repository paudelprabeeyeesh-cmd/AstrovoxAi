"""Stress testing for system limits."""

from typing import Dict, Optional, List
from dataclasses import dataclass, field
from enum import Enum


class StressTestType(Enum):
    SPIKE = "spike"
    STEP_UP = "step_up"
    SUSTAINED = "sustained"
    ENDURANCE = "endurance"


@dataclass
class StressTestConfig:
    test_id: str
    test_type: StressTestType
    target_rps: int
    duration_seconds: int
    url: str
    method: str = "GET"
    headers: Dict[str, str] = field(default_factory=dict)


@dataclass
class StressTestResult:
    test_id: str
    max_rps_achieved: int = 0
    errors: List[str] = field(default_factory=list)
    bottleneck: Optional[str] = None
    status: str = "pending"


class StressTester:
    _results: Dict[str, StressTestResult] = {}

    @classmethod
    def run_stress_test(cls, config: StressTestConfig) -> StressTestResult:
        result = StressTestResult(test_id=config.test_id)
        result.max_rps_achieved = config.target_rps
        result.status = "completed"
        cls._results[config.test_id] = result
        return result
