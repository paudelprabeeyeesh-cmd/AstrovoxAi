from typing import Optional, Dict
import numpy as np
import logging

logger = logging.getLogger(__name__)


class KalmanFilter:
    def __init__(self, state_dim: int, obs_dim: int):
        self.state_dim = state_dim
        self.obs_dim = obs_dim
        self.x = np.zeros((state_dim, 1))
        self.P = np.eye(state_dim)
        self.F = np.eye(state_dim)
        self.H = np.eye(obs_dim, state_dim)
        self.Q = np.eye(state_dim) * 0.01
        self.R = np.eye(obs_dim) * 0.1

    def predict(self, u: Optional[np.ndarray] = None) -> np.ndarray:
        self.x = self.F @ self.x
        self.P = self.F @ self.P @ self.F.T + self.Q
        return self.x

    def update(self, z: np.ndarray) -> np.ndarray:
        y = z.reshape(-1, 1) - self.H @ self.x
        S = self.H @ self.P @ self.H.T + self.R
        K = self.P @ self.H.T @ np.linalg.inv(S)
        self.x = self.x + K @ y
        self.P = (np.eye(self.state_dim) - K @ self.H) @ self.P
        return self.x


class SensorFusion:
    def __init__(self):
        self.filters: Dict[str, KalmanFilter] = {}

    def add_sensor(self, name: str, state_dim: int, obs_dim: int) -> None:
        self.filters[name] = KalmanFilter(state_dim, obs_dim)
        logger.info("Added sensor fusion filter: %s", name)

    def fuse(self, sensor_name: str, measurement: np.ndarray) -> np.ndarray:
        filt = self.filters.get(sensor_name)
        if filt is None:
            logger.warning("Unknown sensor %s", sensor_name)
            return measurement
        filt.predict()
        return filt.update(measurement).flatten()
