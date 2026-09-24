from ai_core.problem_solving import (
    ProblemSolver,
)


def test_astar_search():
    solver = ProblemSolver()
    start = 0
    goal = 5

    def goal_test(s):
        return s == goal

    def expand(s):
        if s >= goal:
            return []
        return [(s + 1, "right", 1.0), (s + 2, "jump", 1.5)]

    heuristic = lambda s: max(0, goal - s)
    plan = solver.search_solution(start, goal_test, expand, method="astar", heuristic=heuristic)
    assert plan is not None
    assert len(plan) > 0


def test_greedy_search():
    solver = ProblemSolver()
    start = 0
    goal = 3

    def goal_test(s):
        return s == goal

    def expand(s):
        return [(s + 1, "right", 1.0)]

    plan = solver.search_solution(start, goal_test, expand, method="greedy")
    assert plan is not None


def test_csp_n_queens_small():
    n = 4
    variables = [f"q{i}" for i in range(n)]
    domains = {v: list(range(n)) for v in variables}

    def constraints(assignment):
        cols = [assignment[v] for v in variables if v in assignment]
        if len(cols) != len(set(cols)):
            return False
        rows = [assignment[v] for v in variables if v in assignment]
        for r1, c1 in enumerate(rows):
            for r2, c2 in enumerate(rows):
                if r1 != r2 and abs(r1 - r2) == abs(c1 - c2):
                    return False
        return True

    solver = ProblemSolver()
    solution = solver.solve_csp(variables, domains, [constraints])
    assert solution is not None
    assert len(solution) == n


def test_analogy_engine():
    solver = ProblemSolver()
    source = {"force": "push", "mass": "heavy"}
    target = {"electric": "current", "resistance": "ohms"}
    pairs = [("force", "electric"), ("mass", "resistance")]
    result = solver.solve_by_analogy(source, target, pairs)
    assert result is not None
