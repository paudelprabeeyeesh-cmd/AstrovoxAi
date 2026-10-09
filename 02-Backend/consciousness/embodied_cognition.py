from dataclasses import dataclass
from typing import List, Optional
import numpy as np


@dataclass
class SensorimotorState:
    posture: np.ndarray
    touch: np.ndarray
    proprioception: np.ndarray
    action: Optional[np.ndarray] = None


class EmbodiedAgent:
    def __init__(self, posture_dim: int = 8, touch_dim: int = 8, proprio_dim: int = 8):
        self.posture_dim = posture_dim
        self.touch_dim = touch_dim
        self.proprio_dim = proprio_dim
        self._state = SensorimotorState(
            posture=np.zeros(posture_dim),
            touch=np.zeros(touch_dim),
            proprioception=np.zeros(proprio_dim),
        )
        self._history: List[SensorimotorState] = []

    def sense(self, touch: np.ndarray, proprioception: np.ndarray) -> SensorimotorState:
        touch = np.array(touch, dtype=float)
        proprioception = np.array(proprioception, dtype=float)
        if touch.size < self.touch_dim:
            touch = np.pad(touch, (0, self.touch_dim - touch.size))
        if proprioception.size < self.proprio_dim:
            proprioception = np.pad(proprioception, (0, self.proprio_dim - proprioception.size))
        self._state.touch = touch[: self.touch_dim]
        self._state.proprioception = proprioception[: self.proprio_dim]
        return self._state

    def act(self, action: np.ndarray) -> SensorimotorState:
        action = np.array(action, dtype=float)
        if action.size < self.posture_dim:
            action = np.pad(action, (0, self.posture_dim - action.size))
        self._state.action = action[: self.posture_dim]
        self._state.posture = action[: self.posture_dim] * 0.7 + self._state.posture * 0.3
        self._history.append(self._state)
        return self._state

    def sense_motor_loop(self, touch: np.ndarray, proprioception: np.ndarray, action: np.ndarray) -> SensorimotorState:
        self.sense(touch, proprioception)
        return self.act(action)

    def get_state(self) -> SensorimotorState:
        return self._state

    def body_schema(self) -> np.ndarray:
        return np.concatenate([self._state.posture, self._state.touch, self._state.proprioception])
