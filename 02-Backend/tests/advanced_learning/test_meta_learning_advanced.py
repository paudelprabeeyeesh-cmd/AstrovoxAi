import numpy as np
import pytest
from advanced_learning.meta_learning_advanced import AdvancedMetaLearner, MetaConfig


class TestAdvancedMetaLearner:
    def test_initialization(self):
        config = MetaConfig(input_dim=32, output_dim=4)
        ml = AdvancedMetaLearner(config)
        assert ml.config.input_dim == 32
        assert ml.config.output_dim == 4
        assert ml.config.inner_lr == 0.01
        assert len(ml.meta_history) == 0

    def test_sample_task(self):
        config = MetaConfig(input_dim=32, output_dim=4)
        ml = AdvancedMetaLearner(config)
        x_s, y_s, x_q, y_q = ml.sample_task(20)
        assert x_s.shape == (20, 32)
        assert y_s.shape == (20, 4)
        assert x_q.shape == (20, 32)
        assert y_q.shape == (20, 4)

    def test_adapt(self):
        config = MetaConfig(input_dim=32, output_dim=4)
        ml = AdvancedMetaLearner(config)
        x_s = np.random.randn(20, 32).astype(np.float64)
        y_s = np.random.randn(20, 4).astype(np.float64)
        adapted = ml.adapt(x_s, y_s)
        assert isinstance(adapted, dict)
        assert "W1" in adapted

    def test_meta_train_step(self):
        config = MetaConfig(input_dim=32, output_dim=4, num_tasks=2)
        ml = AdvancedMetaLearner(config)
        result = ml.meta_train_step()
        assert "meta_loss" in result
        assert len(ml.meta_history) == 1

    def test_evaluate(self):
        config = MetaConfig(input_dim=32, output_dim=4)
        ml = AdvancedMetaLearner(config)
        x_q = np.random.randn(20, 32).astype(np.float64)
        y_q = np.random.randn(20, 4).astype(np.float64)
        result = ml.evaluate(x_q, y_q)
        assert "query_loss" in result

    def test_get_meta_report(self):
        config = MetaConfig(input_dim=32, output_dim=4)
        ml = AdvancedMetaLearner(config)
        ml.meta_train_step()
        report = ml.get_meta_report()
        assert "num_meta_steps" in report
        assert report["inner_lr"] == 0.01
        assert report["meta_lr"] == 0.001
