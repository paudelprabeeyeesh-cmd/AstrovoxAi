import math
from online_learning.incremental_evaluator import IncrementalEvaluator


class TestIncrementalEvaluator:
    def test_initialization(self):
        evaluator = IncrementalEvaluator()
        metrics = evaluator.get_metrics()
        assert metrics["step_count"] == 0
        assert metrics["mae"] == 0.0

    def test_update_single(self):
        evaluator = IncrementalEvaluator()
        metrics = evaluator.update(2.0, 2.0)
        assert metrics["step_count"] == 1
        assert metrics["mae"] == 0.0
        assert metrics["mse"] == 0.0

    def test_update_multiple(self):
        evaluator = IncrementalEvaluator()
        evaluator.update(2.0, 1.0)
        evaluator.update(3.0, 2.0)
        evaluator.update(4.0, 3.0)
        metrics = evaluator.get_metrics()
        assert metrics["step_count"] == 3
        expected_mae = (1.0 + 1.0 + 1.0) / 3
        assert math.isclose(metrics["mae"], expected_mae)

    def test_reset(self):
        evaluator = IncrementalEvaluator()
        evaluator.update(1.0, 2.0)
        evaluator.reset()
        metrics = evaluator.get_metrics()
        assert metrics["step_count"] == 0

    def test_bias_calculation(self):
        evaluator = IncrementalEvaluator()
        evaluator.update(3.0, 1.0)
        evaluator.update(3.0, 1.0)
        metrics = evaluator.get_metrics()
        assert math.isclose(metrics["bias"], 2.0)

    def test_rmse_calculation(self):
        evaluator = IncrementalEvaluator()
        evaluator.update(3.0, 0.0)
        evaluator.update(0.0, 3.0)
        metrics = evaluator.get_metrics()
        expected_mse = (9.0 + 9.0) / 2
        assert math.isclose(metrics["mse"], expected_mse)
        assert math.isclose(metrics["rmse"], math.sqrt(expected_mse))
