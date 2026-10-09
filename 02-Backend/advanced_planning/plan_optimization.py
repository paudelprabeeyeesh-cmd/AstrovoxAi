
from typing import Any, Callable, Dict, List, Optional


class PlanOptimizer:
    def __init__(self):
        self.optimization_history: List[Dict[str, Any]] = []

    def compress(self, plan: List[Any], equivalence_fn: Callable[[Any, Any], bool]) -> List[Any]:
        if not plan:
            return []
        compressed = [plan[0]]
        for action in plan[1:]:
            if not equivalence_fn(action, compressed[-1]):
                compressed.append(action)
        self.optimization_history.append({"type": "compress", "original_length": len(plan),
                                           "compressed_length": len(compressed)})
        return compressed

    def compress_with_merge(self, plan: List[Any], merge_fn: Callable[[Any, Any], Any]) -> List[Any]:
        if len(plan) < 2:
            return list(plan)
        compressed = list(plan)
        i = 0
        while i < len(compressed) - 1:
            merged = merge_fn(compressed[i], compressed[i + 1])
            if merged is not None:
                compressed[i] = merged
                compressed.pop(i + 1)
            else:
                i += 1
        self.optimization_history.append({"type": "merge", "original_length": len(plan),
                                           "compressed_length": len(compressed)})
        return compressed

    def prune_redundant(self, plan: List[Any], validity_fn: Callable[[List[Any]], bool],
                        should_remove: Callable[[Any], bool]) -> List[Any]:
        pruned = list(plan)
        i = 0
        while i < len(pruned):
            if not should_remove(pruned[i]):
                i += 1
                continue
            candidate = pruned[:i] + pruned[i + 1:]
            if validity_fn(candidate):
                pruned = candidate
            else:
                i += 1
        self.optimization_history.append({"type": "prune", "original_length": len(plan),
                                           "pruned_length": len(pruned)})
        return pruned

    def reorder(self, plan: List[Any], partial_order: Callable[[Any, Any], Optional[bool]],
                cost_fn: Callable[[List[Any]], float]) -> List[Any]:
        if len(plan) < 2:
            return list(plan)
        best_order = list(plan)
        best_cost = cost_fn(best_order)
        for i in range(len(plan)):
            for j in range(i + 1, len(plan)):
                candidate = list(plan)
                candidate[i], candidate[j] = candidate[j], candidate[i]
                if self._respects_order(candidate, partial_order):
                    c = cost_fn(candidate)
                    if c < best_cost:
                        best_cost = c
                        best_order = candidate
        self.optimization_history.append({"type": "reorder", "original_length": len(plan),
                                           "best_cost": best_cost})
        return best_order

    def _respects_order(self, plan: List[Any], partial_order: Callable[[Any, Any], Optional[bool]]) -> bool:
        for i in range(len(plan)):
            for j in range(i + 1, len(plan)):
                order = partial_order(plan[j], plan[i])
                if order is False:
                    return False
        return True

    def optimize_cost(self, plan: List[Any], cost_fn: Callable[[Any], float],
                      validity_fn: Callable[[List[Any]], bool]) -> List[Any]:
        if not plan:
            return []
        current = list(plan)
        best_cost = sum(cost_fn(a) for a in current)
        improved = True
        while improved:
            improved = False
            for i in range(len(current)):
                for j in range(i + 1, len(current)):
                    candidate = list(current)
                    candidate[i], candidate[j] = candidate[j], candidate[i]
                    if validity_fn(candidate):
                        c = sum(cost_fn(a) for a in candidate)
                        if c < best_cost:
                            best_cost = c
                            current = candidate
                            improved = True
        return current
