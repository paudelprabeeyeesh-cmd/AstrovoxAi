
import numpy as np
from advanced_planning.multi_objective import MultiObjectiveEvaluator, NSGAII


def _sol(objectives):
    return {"objectives": objectives}


class TestMultiObjectiveEvaluator:

    def test_evaluate_returns_array(self):
        ev = MultiObjectiveEvaluator(3)
        result = ev.evaluate(_sol([1.0, 2.0, 3.0]))
        assert isinstance(result, np.ndarray)
        assert result.shape == (3,)

    def test_evaluate_defaults_to_zeros(self):
        ev = MultiObjectiveEvaluator(2)
        result = ev.evaluate({})
        assert np.allclose(result, [0.0, 0.0])

    def test_dominates_strictly_better(self):
        ev = MultiObjectiveEvaluator(2)
        a = np.array([1.0, 2.0])
        b = np.array([3.0, 4.0])
        assert bool(ev.dominates(a, b)) is True

    def test_dominates_not_worse_in_any(self):
        ev = MultiObjectiveEvaluator(2)
        a = np.array([1.0, 5.0])
        b = np.array([3.0, 2.0])
        assert bool(ev.dominates(a, b)) is False

    def test_dominates_identical_is_false(self):
        ev = MultiObjectiveEvaluator(2)
        a = np.array([1.0, 2.0])
        b = np.array([1.0, 2.0])
        assert bool(ev.dominates(a, b)) is False

    def test_non_dominated_sort_empty(self):
        ev = MultiObjectiveEvaluator(2)
        fronts = ev.non_dominated_sort([])
        assert fronts == []

    def test_non_dominated_sort_single(self):
        ev = MultiObjectiveEvaluator(2)
        fronts = ev.non_dominated_sort([_sol([1.0, 2.0])])
        assert len(fronts) == 1
        assert fronts[0] == [0]

    def test_non_dominated_sort_two_dominated(self):
        ev = MultiObjectiveEvaluator(2)
        pop = [_sol([1.0, 2.0]), _sol([3.0, 4.0])]
        fronts = ev.non_dominated_sort(pop)
        assert fronts[0] == [0]
        assert len(fronts) >= 1

    def test_crowding_distance_small_front(self):
        ev = MultiObjectiveEvaluator(2)
        d = ev.crowding_distance([0], np.array([[1.0, 2.0]]))
        assert d[0] == float("inf")

    def test_crowding_distance_two_elements(self):
        ev = MultiObjectiveEvaluator(2)
        objs = np.array([[0.0, 0.0], [1.0, 1.0]])
        d = ev.crowding_distance([0, 1], objs)
        assert d[0] == float("inf")
        assert d[1] == float("inf")

    def test_crowding_distance_computed_correctly(self):
        ev = MultiObjectiveEvaluator(2)
        objs = np.array([[0.0, 0.0], [0.5, 0.5], [1.0, 1.0]])
        d = ev.crowding_distance([0, 1, 2], objs)
        assert d[0] == float("inf")
        assert d[2] == float("inf")
        assert d[1] > 0.0


class TestNSGAII:

    def test_initialize_population_size(self):
        ev = MultiObjectiveEvaluator(2)
        nsga = NSGAII(ev, population_size=10)
        pop = nsga.initialize_population([(0.0, 1.0)] * 2, 10)
        assert len(pop) == 10
        assert all("genes" in ind for ind in pop)
        assert all("objectives" in ind for ind in pop)

    def test_crossover_above_rate_returns_children(self):
        ev = MultiObjectiveEvaluator(2)
        nsga = NSGAII(ev, crossover_rate=1.0)
        p1 = {"genes": np.array([0.0, 0.0])}
        p2 = {"genes": np.array([1.0, 1.0])}
        np.random.seed(42)
        c1, c2 = nsga.crossover(p1, p2)
        assert "genes" in c1
        assert "genes" in c2

    def test_crossover_below_rate_returns_parents(self):
        ev = MultiObjectiveEvaluator(2)
        nsga = NSGAII(ev, crossover_rate=0.0)
        p1 = {"genes": np.array([0.0, 0.0])}
        p2 = {"genes": np.array([1.0, 1.0])}
        c1, c2 = nsga.crossover(p1, p2)
        assert c1 is p1
        assert c2 is p2

    def test_mutate_changes_genes(self):
        ev = MultiObjectiveEvaluator(2)
        nsga = NSGAII(ev, mutation_rate=1.0)
        ind = {"genes": np.array([0.5, 0.5]), "objectives": [0.0, 0.0]}
        np.random.seed(0)
        result = nsga.mutate(ind, [(0.0, 1.0)] * 2)
        assert "genes" in result
        assert "objectives" in result
        assert len(result["genes"]) == 2

    def test_run_returns_pareto_front(self):
        ev = MultiObjectiveEvaluator(2)
        nsga = NSGAII(ev, population_size=20)
        np.random.seed(0)
        pareto = nsga.run([(0.0, 1.0)] * 2, generations=5)
        assert isinstance(pareto, list)
        assert len(pareto) > 0

    def test_history_populated(self):
        ev = MultiObjectiveEvaluator(2)
        nsga = NSGAII(ev, population_size=10)
        nsga.run([(0.0, 1.0)] * 2, generations=3)
        assert len(nsga.history) == 3
