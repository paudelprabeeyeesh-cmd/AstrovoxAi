import numpy as np
import pytest
from quantum_ml.quantum_feature_map import ZZFeatureMap
from quantum_ml.quantum_kernel_estimator import KernelEstimator, FidelityKernel


class TestFidelityKernel:
    def test_estimate_symmetry(self):
        fmap = ZZFeatureMap(2)
        kernel = FidelityKernel(fmap)
        x = np.array([0.1, 0.2, 0.3])
        y = np.array([0.4, 0.5, 0.6])
        k_xy = kernel.estimate(x, y)
        k_yx = kernel.estimate(y, x)
        np.testing.assert_allclose(k_xy, k_yx, atol=1e-10)

    def test_estimate_self_similarity(self):
        fmap = ZZFeatureMap(2)
        kernel = FidelityKernel(fmap)
        x = np.array([0.1, 0.2, 0.3])
        k = kernel.estimate(x, x)
        assert k > 0
        assert k <= 1

    def test_matrix_shape(self):
        fmap = ZZFeatureMap(2)
        kernel = FidelityKernel(fmap)
        X = np.random.randn(5, 3)
        Y = np.random.randn(4, 3)
        K = kernel.matrix(X, Y)
        assert K.shape == (5, 4)

    def test_matrix_positive_semi_definite(self):
        fmap = ZZFeatureMap(2)
        kernel = FidelityKernel(fmap)
        X = np.random.randn(3, 2)
        K = kernel.matrix(X, X)
        eigenvals = np.linalg.eigvalsh(K)
        assert all(eigenvals >= -1e-10)

    def test_different_inputs(self):
        fmap = ZZFeatureMap(2)
        kernel = FidelityKernel(fmap)
        x1 = np.array([0.0, 0.0])
        x2 = np.array([np.pi, np.pi])
        k = kernel.estimate(x1, x2)
        assert 0 <= k <= 1

    def test_same_input_high_value(self):
        fmap = ZZFeatureMap(2)
        kernel = FidelityKernel(fmap)
        x = np.array([0.5, 0.5])
        k = kernel.estimate(x, x)
        assert k > 0.9


class TestKernelEstimator:
    def test_estimate_raises_not_implemented(self):
        estimator = KernelEstimator()
        x = np.array([0.1, 0.2])
        y = np.array([0.3, 0.4])
        with pytest.raises(NotImplementedError):
            estimator.estimate(x, y)

    def test_matrix_raises_not_implemented(self):
        estimator = KernelEstimator()
        X = np.random.randn(3, 2)
        with pytest.raises(NotImplementedError):
            estimator.matrix(X, X)
