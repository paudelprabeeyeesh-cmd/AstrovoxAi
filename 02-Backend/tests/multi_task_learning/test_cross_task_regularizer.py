from multi_task_learning.cross_task_regularizer import CrossTaskRegularizer


def test_single_task_returns_zero():
    reg = CrossTaskRegularizer(strength=0.1)
    penalty = reg.compute_penalty({"task1": [1.0, 2.0, 3.0]})
    assert penalty == 0.0


def test_two_tasks_same_rep_returns_zero():
    reg = CrossTaskRegularizer(strength=0.1)
    penalty = reg.compute_penalty({
        "task1": [1.0, 2.0, 3.0],
        "task2": [1.0, 2.0, 3.0],
    })
    assert penalty == 0.0


def test_two_tasks_different_rep_positive():
    reg = CrossTaskRegularizer(strength=0.1)
    penalty = reg.compute_penalty({
        "task1": [0.0, 0.0, 0.0],
        "task2": [1.0, 1.0, 1.0],
    })
    assert penalty > 0.0


def test_three_tasks_penalty_scales():
    reg = CrossTaskRegularizer(strength=1.0)
    penalty = reg.compute_penalty({
        "task1": [0.0, 0.0],
        "task2": [1.0, 1.0],
        "task3": [2.0, 2.0],
    })
    assert penalty > 0.0


def test_strength_scales_penalty():
    reps = {
        "task1": [0.0, 0.0],
        "task2": [1.0, 1.0],
    }
    reg1 = CrossTaskRegularizer(strength=0.1)
    reg2 = CrossTaskRegularizer(strength=0.5)
    p1 = reg1.compute_penalty(reps)
    p2 = reg2.compute_penalty(reps)
    assert abs(p2 - 5.0 * p1) < 1e-9
