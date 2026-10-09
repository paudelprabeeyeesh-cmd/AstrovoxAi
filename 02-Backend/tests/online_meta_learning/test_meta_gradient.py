import numpy as np
from online_meta_learning.meta_gradient import MetaGradientComputer


class TestMetaGradientComputer:
    def test_compute_basic(self):
        mgc = MetaGradientComputer(normalize=False, clip_norm=None)
        base = {'W1': np.ones((4, 4), dtype=np.float64), 'b1': np.zeros(4, dtype=np.float64)}
        adapted = {'W1': np.ones((4, 4), dtype=np.float64) + 0.1, 'b1': np.zeros(4, dtype=np.float64)}
        query_grad = {'W1': np.ones((4, 4), dtype=np.float64)}
        result = mgc.compute(adapted, base, query_grad)
        assert 'W1' in result
        assert 'b1' in result
        assert np.allclose(result['W1'], 0.1)

    def test_compute_missing_query_grad(self):
        mgc = MetaGradientComputer(normalize=False, clip_norm=None)
        base = {'W1': np.ones((4, 4), dtype=np.float64)}
        adapted = {'W1': np.ones((4, 4), dtype=np.float64) + 0.2}
        result = mgc.compute(adapted, base, {})
        assert np.allclose(result['W1'], 0.2)

    def test_normalize(self):
        mgc = MetaGradientComputer(normalize=True, clip_norm=None)
        base = {'W1': np.zeros((4, 4), dtype=np.float64)}
        adapted = {'W1': np.ones((4, 4), dtype=np.float64) * 3.0}
        result = mgc.compute(adapted, base, {'W1': np.ones((4, 4), dtype=np.float64)})
        assert np.allclose(result['W1'], 3.0 / np.sqrt(16 * 9))

    def test_clip_norm(self):
        mgc = MetaGradientComputer(normalize=False, clip_norm=0.5)
        base = {'W1': np.zeros((4, 4), dtype=np.float64)}
        adapted = {'W1': np.ones((4, 4), dtype=np.float64) * 10.0}
        result = mgc.compute(adapted, base, {'W1': np.ones((4, 4), dtype=np.float64)})
        norm = np.sqrt(np.sum(result['W1'] ** 2))
        assert norm <= 0.5 + 1e-6

    def test_average_history(self):
        mgc = MetaGradientComputer(normalize=False, clip_norm=None)
        base = {'W1': np.zeros((2, 2), dtype=np.float64)}
        adapted = {'W1': np.ones((2, 2), dtype=np.float64)}
        mgc.compute(adapted, base, {'W1': np.ones((2, 2), dtype=np.float64)})
        mgc.compute(adapted, base, {'W1': np.ones((2, 2), dtype=np.float64)})
        avg = mgc.average_history()
        assert 'W1' in avg
        assert np.allclose(avg['W1'], 1.0)

    def test_get_report(self):
        mgc = MetaGradientComputer()
        report = mgc.get_report()
        assert 'num_gradients' in report
        assert 'normalize' in report
        assert 'clip_norm' in report

    def test_compute_missing_adapted_key_skipped(self):
        mgc = MetaGradientComputer(normalize=False, clip_norm=None)
        base = {'W1': np.zeros((2, 2), dtype=np.float64), 'b1': np.zeros(2, dtype=np.float64)}
        adapted = {'W1': np.ones((2, 2), dtype=np.float64)}
        query_grad = {'W1': np.ones((2, 2), dtype=np.float64)}
        result = mgc.compute(adapted, base, query_grad)
        assert 'W1' in result
        assert 'b1' not in result
