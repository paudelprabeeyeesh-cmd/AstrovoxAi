import numpy as np
from online_meta_learning.reptile_wrapper import ReptileWrapper, ReptileConfig


class TestReptileWrapper:
    def test_initialization(self):
        config = ReptileConfig(input_dim=32, output_dim=4)
        rw = ReptileWrapper(config)
        assert rw.config.input_dim == 32
        assert rw.config.output_dim == 4
        assert rw.config.inner_lr == 0.01
        assert rw.config.meta_lr == 0.001
        assert len(rw.history) == 0
        assert 'W1' in rw.params

    def test_sample_task(self):
        config = ReptileConfig(input_dim=32, output_dim=4)
        rw = ReptileWrapper(config)
        x, y = rw.sample_task(20)
        assert x.shape == (20, 32)
        assert y.shape == (20, 4)

    def test_adapt(self):
        config = ReptileConfig(input_dim=32, output_dim=4)
        rw = ReptileWrapper(config)
        x = np.random.randn(20, 32).astype(np.float64)
        y = np.random.randn(20, 4).astype(np.float64)
        adapted = rw.adapt(x, y)
        assert isinstance(adapted, dict)
        assert 'W1' in adapted

    def test_train_step(self):
        config = ReptileConfig(input_dim=32, output_dim=4, num_tasks=2)
        rw = ReptileWrapper(config)
        result = rw.train_step()
        assert 'meta_loss' in result
        assert len(rw.history) == 1

    def test_evaluate(self):
        config = ReptileConfig(input_dim=32, output_dim=4)
        rw = ReptileWrapper(config)
        x = np.random.randn(20, 32).astype(np.float64)
        y = np.random.randn(20, 4).astype(np.float64)
        result = rw.evaluate(x, y)
        assert 'query_loss' in result

    def test_get_report(self):
        config = ReptileConfig(input_dim=32, output_dim=4)
        rw = ReptileWrapper(config)
        rw.train_step()
        report = rw.get_report()
        assert 'num_steps' in report
        assert report['inner_lr'] == 0.01
        assert report['meta_lr'] == 0.001

    def test_relu(self):
        x = np.array([[-1.0, 0.0, 2.0]], dtype=np.float64)
        out = ReptileWrapper._relu(x)
        assert np.allclose(out, [[0.0, 0.0, 2.0]])

    def test_relu_grad(self):
        x = np.array([[-1.0, 0.0, 2.0]], dtype=np.float64)
        out = ReptileWrapper._relu_grad(x)
        assert np.allclose(out, [[0.0, 0.0, 1.0]])

    def test_forward(self):
        config = ReptileConfig(input_dim=4, output_dim=2)
        rw = ReptileWrapper(config)
        x = np.random.randn(3, 4).astype(np.float64)
        logits = rw._forward(x, rw.params)
        assert logits.shape == (3, 2)

    def test_compute_loss(self):
        config = ReptileConfig(input_dim=4, output_dim=2)
        rw = ReptileWrapper(config)
        x = np.random.randn(3, 4).astype(np.float64)
        y = np.random.randn(3, 2).astype(np.float64)
        loss = rw._compute_loss(x, y, rw.params)
        assert isinstance(loss, float)
        assert loss >= 0.0

    def test_train_step_updates_params(self):
        np.random.seed(0)
        config = ReptileConfig(input_dim=8, output_dim=2, num_tasks=2, num_inner_steps=1)
        rw = ReptileWrapper(config)
        before = {k: v.copy() for k, v in rw.params.items()}
        rw.train_step()
        for k in rw.params:
            assert not np.allclose(rw.params[k], before[k])
