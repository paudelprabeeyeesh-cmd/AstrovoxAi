import math

import pytest
from multi_task_learning.cross_task_regularizer import CrossTaskRegularizer


class TestCrossTaskRegularizer:
    def test_penalty_is_non_negative(self):
        reg = CrossTaskRegularizer(strength=0.1)
        reps = {"task1": [0.5, 1.0, 1.5], "task2": [0.2, 0.8, 1.2]}
        penalty = reg.compute_penalty(reps)
        assert penalty >= 0.0

    def test_single_task_returns_zero(self):
        reg = CrossTaskRegularizer(strength=0.1)
        reps = {"task1": [0.5, 1.0, 1.5]}
        assert reg.compute_penalty(reps) == 0.0

    def test_empty_reps_returns_zero(self):
        reg = CrossTaskRegularizer(strength=0.1)
        assert reg.compute_penalty({}) == 0.0

    def test_same_representations_low_penalty(self):
        reg = CrossTaskRegularizer(strength=0.1)
        reps = {"task1": [1.0, 2.0, 3.0], "task2": [1.0, 2.0, 3.0]}
        penalty = reg.compute_penalty(reps)
        assert math.isclose(penalty, 0.0, abs_tol=1e-9)

    def test_different_representations_higher_penalty(self):
        reg = CrossTaskRegularizer(strength=0.1)
        same = {"task1": [1.0, 2.0, 3.0], "task2": [1.0, 2.0, 3.0]}
        diff = {"task1": [1.0, 2.0, 3.0], "task2": [10.0, 20.0, 30.0]}
        assert reg.compute_penalty(diff) > reg.compute_penalty(same)

    def test_strength_scales_penalty(self):
        reps = {"task1": [1.0, 2.0], "task2": [3.0, 4.0]}
        reg1 = CrossTaskRegularizer(strength=0.1)
        reg2 = CrossTaskRegularizer(strength=0.5)
        p1 = reg1.compute_penalty(reps)
        p2 = reg2.compute_penalty(reps)
        assert math.isclose(p2, 5.0 * p1, rel_tol=1e-9)

    def test_default_strength(self):
        reg = CrossTaskRegularizer()
        assert reg.strength == 0.1

    def test_three_tasks(self):
        reg = CrossTaskRegularizer(strength=0.1)
        reps = {
            "task1": [1.0, 2.0],
            "task2": [1.0, 2.0],
            "task3": [1.0, 2.0],
        }
        penalty = reg.compute_penalty(reps)
        assert math.isclose(penalty, 0.0, abs_tol=1e-9)

    def test_two_tasks_penalty_formula(self):
        reg = CrossTaskRegularizer(strength=1.0)
        reps = {"task1": [0.0, 0.0], "task2": [2.0, 2.0]}
        penalty = reg.compute_penalty(reps)
        expected_mean_diff = (0.0 - 2.0) ** 2
        expected_var_diff = (0.0 - 0.0) ** 2
        expected = expected_mean_diff + expected_var_diff
        assert math.isclose(penalty, expected, rel_tol=1e-9)
