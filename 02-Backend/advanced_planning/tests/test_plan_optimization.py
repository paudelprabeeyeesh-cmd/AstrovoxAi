
from advanced_planning.plan_optimization import PlanOptimizer


def test_compress_removes_duplicates():
    optimizer = PlanOptimizer()
    plan = ["a", "a", "b", "a", "a"]
    compressed = optimizer.compress(plan, equivalence_fn=lambda x, y: x == y)
    assert compressed == ["a", "b", "a"]


def test_compress_empty_plan():
    optimizer = PlanOptimizer()
    result = optimizer.compress([], lambda x, y: x == y)
    assert result == []


def test_compress_single_element():
    optimizer = PlanOptimizer()
    result = optimizer.compress(["a"], lambda x, y: x == y)
    assert result == ["a"]


def test_compress_with_merge():
    optimizer = PlanOptimizer()
    plan = ["a", "a", "b"]

    def merge_fn(a, b):
        if a == b:
            return a + b
        return None

    compressed = optimizer.compress_with_merge(plan, merge_fn)
    assert len(compressed) < len(plan)


def test_prune_redundant():
    optimizer = PlanOptimizer()
    plan = ["keep", "remove", "keep"]

    def validity_fn(p):
        return "remove" not in p

    def should_remove(a):
        return a == "remove"

    pruned = optimizer.prune_redundant(plan, validity_fn, should_remove)
    assert "remove" not in pruned


def test_prune_redundant_all_keep():
    optimizer = PlanOptimizer()
    plan = ["a", "b", "c"]

    def validity_fn(p):
        return True

    pruned = optimizer.prune_redundant(plan, validity_fn, lambda a: False)
    assert pruned == ["a", "b", "c"]


def test_reorder_respects_order():
    optimizer = PlanOptimizer()
    # "a" must NOT come before "b" — initial ["b", "a"] already satisfies this
    plan = ["b", "a"]

    def partial_order(a, b):
        if a == "a" and b == "b":
            return False
        return None

    def cost_fn(p):
        return sum(1 for x in p if x == "a")

    reordered = optimizer.reorder(plan, partial_order, cost_fn)
    # Current order already satisfies partial_order, so no swap should occur
    assert reordered == ["b", "a"]


def test_optimize_cost():
    optimizer = PlanOptimizer()
    plan = ["a", "b"]

    def cost_fn(a):
        return 1.0 if a == "b" else 0.0

    def validity_fn(p):
        return True

    optimized = optimizer.optimize_cost(plan, cost_fn, validity_fn)
    assert cost_fn(optimized[0]) <= cost_fn(optimized[-1])


def test_optimization_history():
    optimizer = PlanOptimizer()
    plan = ["a", "a", "b"]
    optimizer.compress(plan, lambda x, y: x == y)
    assert len(optimizer.optimization_history) == 1
    assert optimizer.optimization_history[0]["original_length"] == 3
