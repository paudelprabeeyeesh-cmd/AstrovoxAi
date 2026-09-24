import numpy as np
from online_meta_learning.maml_wrapper import MAMLWrapper, MAMLConfig


class TestMAMLWrapper:
    def test_initialization(self):
        config = MAMLConfig(input_dim=32, output_dim=4)
        mw = MAMLWrapper(config)
        assert mw.config.input_dim == 32
        assert mw.config.output_dim == 4
        assert mw.config.inner_lr == 0.01
        assert mw.config.meta_lr == 0.001
        assert len(mw.history) == 0
        assert 'W1' in mw.params

    def test_sample_task(self):
        config = MAMLConfig(input_dim=32, output_dim=4)
        mw = MAMLWrapper(config)
        x_s, y_s, x_q, y_q = mw.sample_task(20)
        assert x_s.shape == (20, 32)
        assert y_s.shape == (20, 4)
        assert x_q.shape == (20, 32)
        assert y_q.shape == (20, 4)

    def test_adapt(self):
        config = MAMLConfig(input_dim=32, output_dim=4)
        mw = MAMLWrapper(config)
        x = np.random.randn(20, 32).astype(np.float64)
        y = np.random.randn(20, 4).astype(np.float64)
        adapted = mw.adapt(x, y)
        assert isinstance(adapted, dict)
        assert 'W1' in adapted

    def test_meta_train_step(self):
        config = MAMLConfig(input_dim=32, output_dim=4, num_tasks=2)
        mw = MAMLWrapper(config)
        result = mw.meta_train_step()
        assert 'meta_loss' in result
        assert len(mw.history) == 1

    def test_evaluate(self):
        config = MAMLConfig(input_dim=32, output_dim=4)
        mw = MAMLWrapper(config)
        x = np.random.randn(20, 32).astype(np.float64)
        y = np.random.randn(20, 4).astype(np.float64)
        result = mw.evaluate(x, y)
        assert 'query_loss' in result

    def test_get_report(self):
        config = MAMLConfig(input_dim=32, output_dim=4)
        mw = MAMLWrapper(config)
        mw.meta_train_step()
        report = mw.get_report()
        assert 'num_meta_steps' in report
        assert report['inner_lr'] == 0.01
        assert report['meta_lr'] == 0.001
