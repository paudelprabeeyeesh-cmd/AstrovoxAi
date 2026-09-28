from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from models.llm.compiler.graph import ComputationGraph, Node


class KernelCodeGenerator(ABC):
    @abstractmethod
    def generate(self, graph: ComputationGraph, kernel_name: str) -> str:
        raise NotImplementedError


class CUDABackend(KernelCodeGenerator):
    def generate(self, graph: ComputationGraph, kernel_name: str) -> str:
        return f"// CUDA stub for {kernel_name}\n// nodes={len(graph.nodes)}"


class TritonBackend(KernelCodeGenerator):
    def generate(self, graph: ComputationGraph, kernel_name: str) -> str:
        return f"# Triton stub for {kernel_name}\n# nodes={len(graph.nodes)}"


class CPUBackend(KernelCodeGenerator):
    def generate(self, graph: ComputationGraph, kernel_name: str) -> str:
        lines: List[str] = [f"def {kernel_name}("]
        for node in graph.nodes.values():
            lines.append(f"  # {node.op}")
        lines.append(")")
        return "\n".join(lines)
