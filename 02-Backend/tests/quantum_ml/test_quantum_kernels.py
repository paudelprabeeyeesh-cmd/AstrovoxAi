import numpy as np
import pytest
from quantum_ml.quantum_kernels import QuantumKernel, QuantumSVM


class TestQuantumKernel:
    def test_kernel_symmetry(self):
        kernel = QuantumKernel()
        x = np.array([0.1, 0.2, 0.3])
        y = np.array([0.4, 0.5, 0.6])
        k_xy = kernel.kernel(x, y)
        k_yx = kernel.kernel(y, x)
        np.testing.assert_allclose(k_xy, k_yx, atol=1e-10)

    def test_kernel_self_similarity(self):
        kernel = QuantumKernel()
        x = np.array([0.1, 0.2, 0.3])
        k = kernel.kernel(x, x)
        assert k > 0
        assert k <= 1

    def test_kernel_matrix_shape(self):
        kernel = QuantumKernel()
        X = np.random.randn(5, 3)
        Y = np.random.randn(4, 3)
        K = kernel.kernel_matrix(X, Y)
        assert K.shape == (5, 4)

    def test_kernel_matrix_positive(self):
        kernel = QuantumKernel()
        X = np.random.randn(3, 2)
        K = kernel.kernel_matrix(X, X)
        eigenvals = np.linalg.eigvalsh(K)
        assert all(eigenvals >= -1e-10)

    def test_kernel_amplitude_encoding(self):
        kernel = QuantumKernel(encoding="amplitude")
        x = np.array([1.0, 0.0, 0.0, 0.0])
        y = np.array([1.0, 0.0, 0.0, 0.0])
        k = kernel.kernel(x, y)
        assert k > 0


class TestQuantumSVM:
    def test_fit_predict(self):
        X = np.random.randn(20, 2)
        y = np.array([1] * 10 + [-1] * 10)
        svm = QuantumSVM()
        svm.fit(X, y, epochs=20, lr=0.01)
        preds = svm.predict(X)
        assert preds.shape == (20,)

    def test_predict_labels(self):
        X = np.random.randn(20, 2)
        y = np.array([1] * 10 + [-1] * 10)
        svm = QuantumSVM()
        svm.fit(X, y, epochs=20, lr=0.01)
        preds = svm.predict(X)
        assert set(np.unique(preds)).issubset({1, -1})

    def test_score(self):
        X = np.random.randn(20, 2)
        y = np.array([1] * 10 + [-1] * 10)
        svm = QuantumSVM()
        svm.fit(X, y, epochs=20, lr=0.01)
        score = svm.score(X, y)
        assert 0 <= score <= 1

    def test_predict_before_fit_raises(self):
        svm = QuantumSVM()
        X = np.random.randn(5, 2)
        with pytest.raises(ValueError):
            svm.predict(X)
