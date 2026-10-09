import numpy as np
from typing import Optional
from .quantum_feature_map import FeatureMap


class KernelEstimator:
    def __init__(self, feature_map: Optional[FeatureMap] = None):
        self.feature_map = feature_map

    def estimate(self, x: np.ndarray, y: np.ndarray) -> float:
        raise NotImplementedError

    def matrix(self, X: np.ndarray, Y: np.ndarray) -> np.ndarray:
        n, m = X.shape[0], Y.shape[0]
        K = np.zeros((n, m))
        for i in range(n):
            for j in range(m):
                K[i, j] = self.estimate(X[i], Y[j])
        return K


class FidelityKernel(KernelEstimator):
    def __init__(self, feature_map: FeatureMap):
        super().__init__(feature_map)

    def estimate(self, x: np.ndarray, y: np.ndarray) -> float:
        circuit_x = self.feature_map.encode(x)
        circuit_y = self.feature_map.encode(y)
        state_x = circuit_x.run()
        state_y = circuit_y.run()
        return float(np.abs(np.vdot(state_x, state_y)) ** 2)
