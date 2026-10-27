"""Execution context: precision, limits, educational level."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ExecutionContext:
    topic_id: str
    operation_id: str
    level: int = 0  # educational level 0-5
    precision: str = "float64"  # float32 | float64 | decimal
    rtol: float = 1e-6
    atol: float = 1e-12
    max_iterations: int = 10000
    max_input_size: int = 100000
    timeout_seconds: Optional[float] = None
    explain: bool = False  # include derivation steps
    lightweight: bool = True  # avoid heavyweight deps
    metadata: dict = field(default_factory=dict)
