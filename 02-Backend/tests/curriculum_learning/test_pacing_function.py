import math
import pytest
from curriculum_learning.pacing_function import (
    PacingFunction,
    ScheduleType,
    linear_pacing,
    exponential_pacing,
    root_pacing,
    step_pacing,
    sigmoid_pacing,
)


class TestLinearPacing:
    def test_at_zero(self):
        assert linear_pacing(0.0) == 0.0

    def test_at_one(self):
        assert linear_pacing(1.0) == 1.0

    def test_at_half(self):
        assert linear_pacing(0.5) == 0.5

    def test_clamped_negative(self):
        assert linear_pacing(-0.1) == -0.1


class TestExponentialPacing:
    def test_at_zero(self):
        assert exponential_pacing(0.0) == 0.0

    def test_at_one(self):
        assert math.isclose(exponential_pacing(1.0), 1.0)

    def test_concave(self):
        assert exponential_pacing(0.5) < 0.5


class TestRootPacing:
    def test_at_zero(self):
        assert root_pacing(0.0) == 0.0

    def test_at_one(self):
        assert root_pacing(1.0) == 1.0

    def test_convex(self):
        assert root_pacing(0.5) > 0.5


class TestStepPacing:
    def test_at_zero(self):
        assert step_pacing(0.0) == 0.0

    def test_at_one(self):
        assert step_pacing(1.0) == 1.0

    def test_step_levels(self):
        assert step_pacing(0.1, steps=5) == 0.0
        assert step_pacing(0.3, steps=5) == 0.2


class TestSigmoidPacing:
    def test_at_zero(self):
        assert sigmoid_pacing(0.0) < 0.5

    def test_at_one(self):
        assert sigmoid_pacing(1.0) > 0.5

    def test_at_zero_progress(self):
        assert sigmoid_pacing(0.0) < 0.5


class TestPacingFunction:
    def test_linear_default(self):
        pf = PacingFunction()
        assert math.isclose(pf.get_difficulty(0.0), 0.0)
        assert math.isclose(pf.get_difficulty(1.0), 1.0)

    def test_linear_custom_range(self):
        pf = PacingFunction(ScheduleType.LINEAR, start_difficulty=0.2, end_difficulty=0.8)
        assert math.isclose(pf.get_difficulty(0.0), 0.2)
        assert math.isclose(pf.get_difficulty(1.0), 0.8)

    def test_exponential(self):
        pf = PacingFunction(ScheduleType.EXPONENTIAL, start_difficulty=0.1, end_difficulty=1.0)
        d0 = pf.get_difficulty(0.0)
        d1 = pf.get_difficulty(1.0)
        assert math.isclose(d0, 0.1)
        assert math.isclose(d1, 1.0)

    def test_root(self):
        pf = PacingFunction(ScheduleType.ROOT, start_difficulty=0.0, end_difficulty=1.0)
        d = pf.get_difficulty(0.25)
        assert d > 0.25

    def test_step(self):
        pf = PacingFunction(ScheduleType.STEP, start_difficulty=0.0, end_difficulty=1.0)
        d = pf.get_difficulty(0.1)
        assert d == 0.0

    def test_sigmoid(self):
        pf = PacingFunction(ScheduleType.SIGMOID, start_difficulty=0.0, end_difficulty=1.0)
        d = pf.get_difficulty(0.5)
        assert math.isclose(d, 0.5)

    def test_get_difficulty_at_epoch(self):
        pf = PacingFunction(ScheduleType.LINEAR, start_difficulty=0.0, end_difficulty=1.0)
        assert math.isclose(pf.get_difficulty_at_epoch(1, 10), 0.0)
        assert math.isclose(pf.get_difficulty_at_epoch(10, 10), 1.0)

    def test_get_difficulty_curve_length(self):
        pf = PacingFunction()
        curve = pf.get_difficulty_curve(50)
        assert len(curve) == 50

    def test_clamping(self):
        pf = PacingFunction()
        assert pf.get_difficulty(-0.1) == pf.get_difficulty(0.0)
        assert pf.get_difficulty(1.1) == pf.get_difficulty(1.0)
