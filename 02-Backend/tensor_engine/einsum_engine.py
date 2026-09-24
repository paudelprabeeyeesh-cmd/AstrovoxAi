import numpy as np
from .einsum import EinsumEquation, einsum


class EinsumEngine:
    def __init__(self, default_optimize="greedy"):
        self.default_optimize = default_optimize
        self._cache = {}

    def compute(self, equation, *operands, optimize=None):
        if optimize is None:
            optimize = self.default_optimize
        key = (equation, optimize, tuple(np.asarray(op).shape for op in operands))
        if key not in self._cache:
            eq = EinsumEquation(equation)
            shapes = [np.asarray(op).shape for op in operands]
            eq.verify_shapes(shapes)
            self._cache[key] = eq.compute_output_shape(shapes)
        return einsum(equation, *operands, optimize=optimize)

    def shape(self, equation, *shapes):
        eq = EinsumEquation(equation)
        eq.verify_shapes(shapes)
        return eq.compute_output_shape(shapes)

    def optimize_path(self, equation, *shapes):
        eq = EinsumEquation(equation)
        eq.verify_shapes(shapes)
        return eq.contract_labels

    def clear_cache(self):
        self._cache.clear()

    def cache_info(self):
        return {"size": len(self._cache), "keys": list(self._cache.keys())}
