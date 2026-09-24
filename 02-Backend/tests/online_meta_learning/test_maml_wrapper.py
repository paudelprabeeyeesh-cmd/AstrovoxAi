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

    def test_relu(self):
        x = np.array([[-1.0, 0.0, 2.0]], dtype=np.float64)
        out = MAMLWrapper._relu(x)
        assert np.allclose(out, [[0.0, 0.0, 2.0]])

    def test_relu_grad(self):
        x = np.array([[-1.0, 0.0, 2.0]], dtype=np.float64)
        out = MAMLWrapper._relu_grad(x)
        assert np.allclose(out, [[0.0, 0.0, 1.0]])

    def test_forward(self):
        config = MAMLConfig(input_dim=4, output_dim=2)
        mw = MAMLWrapper(config)
        x = np.random.randn(3, 4).astype(np.float64)
        logits = mw._forward(x, mw.params)
        assert logits.shape == (3, 2)

    def test_compute_loss(self):
        config = MAMLConfig(input_dim=4, output_dim=2)
        mw = MAMLWrapper(config)
        x = np.random.randn(3, 4).astype(np.float64)
        y = np.random.randn(3, 2).astype(np.float64)
        loss = mw._compute_loss(x, y, mw.params)
        assert isinstance(loss, float)
        assert loss >= 0.0

    def test_adapt_returns_trajectory(self):
        config = MAMLConfig(input_dim=4, output_dim=2, num_inner_steps=3)
        mw = MAMLWrapper(config)
        x = np.random.randn(5, 4).astype(np.float64)
        y = np.random.randn(5, 2).astype(np.float64)
        adapted, trajectory = mw._adapt(x, y, mw.params)
        assert isinstance(adapted, dict)
        assert isinstance(trajectory, list)
        assert len(trajectory) == 4

    def test_meta_train_step_updates_params(self):
        np.random.seed(0)
        config = MAMLConfig(input_dim=8, output_dim=2, num_tasks=2, num_inner_steps=1)
        mw = MAMLWrapper(config)
        before = {k: v.copy() for k, v in mw.params.items()}
        mw.meta_train_step()
        for k in mw.params:
            assert not np.allclose(mw.params[k], before[k])
