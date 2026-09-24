
import numpy as np
import pytest
from advanced_planning.multi_objective import MultiObjectiveEvaluator, NSGAII


def test_multi_objective_evaluator():
    ev = MultiObjectiveEvaluator(2, ["cost", "time"])
    sol = {"objectives": [1.0, 2.0]}
    result = ev.evaluate(sol)
    assert np.allclose(result, [1.0, 2.0])


def test_dominates():
    ev = MultiObjectiveEvaluator(2)
    a = np.array([1.0, 1.0])
    b = np.array([2.0, 2.0])
    assert ev.dominates(a, b)
    assert not ev.dominates(b, a)


def test_non_dominated_sort():
    ev = MultiObjectiveEvaluator(2)
    pop = [
        {"objectives": [1.0, 1.0]},
        {"objectives": [2.0, 2.0]},
        {"objectives": [1.5, 1.5]},
        {"objectives": [3.0, 3.0]},
    ]
    fronts = ev.non_dominated_sort(pop)
    assert len(fronts) >= 1
    assert fronts[0] == [0]


def test_crowding_distance():
    ev = MultiObjectiveEvaluator(2)
    pop = [
        {"objectives": [1.0, 1.0]},
        {"objectives": [2.0, 2.0]},
        {"objectives": [3.0, 3.0]},
    ]
    fronts = ev.non_dominated_sort(pop)
    objectives = np.array([ev.evaluate(p) for p in pop])
    # fronts[0] has all 3 points, they're all non-dominated since each is strictly better/worse
    distances = ev.crowding_distance(fronts[0], objectives)
    assert distances[fronts[0][0]] == float("inf")
    assert distances[fronts[0][-1]] == float("inf")


def test_nsga2_initialize_population():
    ev = MultiObjectiveEvaluator(2)
    nsga = NSGAII(ev, population_size=10)
    pop = nsga.initialize_population([(0.0, 1.0), (0.0, 1.0)], 10)
    assert len(pop) == 10
    assert all("objectives" in p for p in pop)


def test_nsga2_run_returns_pareto():
    np.random.seed(42)
    ev = MultiObjectiveEvaluator(2)
    nsga = NSGAII(ev, population_size=10)
    pareto = nsga.run(bounds=[(0.0, 1.0), (0.0, 1.0)], generations=3)
    assert len(pareto) >= 1


def test_nsga2_tournament_select():
    ev = MultiObjectiveEvaluator(2)
    nsga = NSGAII(ev)
    ranks = np.array([0, 1, 2, 0, 1])
    distances = {i: 0.5 for i in range(5)}
    idx = nsga.tournament_select([{} for _ in range(5)], ranks, distances)
    assert 0 <= idx < 5


def test_nsga2_crossover():
    ev = MultiObjectiveEvaluator(2)
    nsga = NSGAII(ev, crossover_rate=1.0)
    p1 = {"genes": np.array([0.2, 0.8]), "objectives": [1.0, 1.0]}
    p2 = {"genes": np.array([0.8, 0.2]), "objectives": [2.0, 2.0]}
    c1, c2 = nsga.crossover(p1, p2)
    assert "genes" in c1
    assert "genes" in c2


def test_nsga2_mutate():
    ev = MultiObjectiveEvaluator(2)
    nsga = NSGAII(ev, mutation_rate=0.5)
    ind = {"genes": np.array([0.5, 0.5]), "objectives": [1.0, 1.0]}
    result = nsga.mutate(ind, [(0.0, 1.0), (0.0, 1.0)])
    assert 0.0 <= result["genes"][0] <= 1.0
    assert len(result["objectives"]) == 2
