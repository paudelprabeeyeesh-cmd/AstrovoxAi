"""Resource limits for lightweight mode on 4 GB RAM."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Limits:
    max_matrix_dim: int = 2048
    max_tensor_elements: int = 1_000_000
    max_iterations: int = 100_000
    max_polynomial_degree: int = 512
    max_series_terms: int = 10_000
    max_recursion_depth: int = 1000
    enable_gpu: bool = False
    enable_heavy_deps: bool = False  # scipy/sklearn optional
