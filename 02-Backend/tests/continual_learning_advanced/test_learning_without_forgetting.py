import math
import pytest
from continual_learning_advanced.learning_without_forgetting import (
    LearningWithoutForgetting,
    LwFConfig,
)


class TestLearningWithoutForgetting:
    def test_initialization(self):
        lwf = LearningWithoutForgetting()
        assert lwf.config.alpha == 1.0
        assert lwf.config.temperature == 2.0
        assert lwf.old_model_params == {}

    def test_freeze_old_model(self):
        lwf = LearningWithoutForgetting()
        lwf.freeze_old_model({"W": [0.1, 0.2], "b": [0.0]})
        assert lwf.old_model_params["W"] == [0.1, 0.2]
        assert lwf.old_model_params["b"] == [0.0]

    def test_softmax(self):
        lwf = LearningWithoutForgetting()
        probs = lwf._softmax([0.0, 1.0, 2.0])
        assert abs(sum(probs) - 1.0) < 1e-6
        assert probs[2] > probs[1] > probs[0]

    def test_forward_logits(self):
        lwf = LearningWithoutForgetting()
        params = {"W": [0.5, -0.5, 0.2, -0.2], "b": [0.1, -0.1]}
        logits = lwf._forward_logits(params, [1.0, 1.0])
        assert len(logits) == 2
        assert math.isclose(logits[0], 0.5 - 0.5 + 0.1)
        assert math.isclose(logits[1], 0.2 - 0.2 - 0.1)

    def test_distillation_loss_zero_when_no_old_model(self):
        lwf = LearningWithoutForgetting()
        loss = lwf.distillation_loss({"W": [1.0], "b": [0.0]}, [0.5])
        assert loss == 0.0

    def test_distillation_loss_positive(self):
        lwf = LearningWithoutForgetting(LwFConfig(alpha=1.0, temperature=2.0))
        old_params = {"W": [1.0, -1.0], "b": [0.0, 0.0]}
        new_params = {"W": [0.8, -0.8], "b": [0.0, 0.0]}
        lwf.freeze_old_model(old_params)
        loss = lwf.distillation_loss(new_params, [1.0, 1.0])
        assert loss > 0.0

    def test_train_step_loss(self):
        lwf = LearningWithoutForgetting(LwFConfig(alpha=0.5, temperature=2.0))
        params = {"W": [0.5, -0.5], "b": [0.0]}
        lwf.freeze_old_model(params)
        total = lwf.train_step_loss(1, params, [1.0, 1.0], [0.0])
        assert total >= 0.0
        assert len(lwf.task_loss_history[1]) == 1

    def test_register_task_outputs(self):
        lwf = LearningWithoutForgetting()
        lwf.register_task_outputs(1, [[0.1, 0.2], [0.3, 0.4]])
        assert lwf.task_outputs[1] == [[0.1, 0.2], [0.3, 0.4]]

    def test_get_task_report(self):
        lwf = LearningWithoutForgetting()
        lwf.task_loss_history[1] = [0.5, 0.6]
        report = lwf.get_task_report(1)
        assert report["steps"] == 2.0
        assert math.isclose(report["avg_loss"], 0.55)
