from dataclasses import dataclass
from typing import List, Optional
import numpy as np


@dataclass
class Moment:
    content: np.ndarray
    timestamp: float
    intensity: float = 0.0


class TemporalAwareness:
    def __init__(self, max_moments: int = 1024):
        self._moments: List[Moment] = []
        self._flow: float = 0.0
        self.max_moments = max_moments

    def update(self, content: np.ndarray, timestamp: float) -> Moment:
        content = np.array(content, dtype=float)
        intensity = float(np.mean(np.abs(content)))
        moment = Moment(content=content, timestamp=timestamp, intensity=intensity)
        self._moments.append(moment)
        if len(self._moments) > self.max_moments:
            self._moments.pop(0)
        self._flow = self._compute_flow()
        return moment

    def duration(self) -> float:
        if not self._moments:
            return 0.0
        return self._moments[-1].timestamp - self._moments[0].timestamp

    def last_duration(self, window: int = 5) -> float:
        if not self._moments:
            return 0.0
        ms = self._moments[-min(window, len(self._moments)):]
        return ms[-1].timestamp - ms[0].timestamp

    def flow(self) -> float:
        return self._flow

    def current_moment(self) -> Optional[Moment]:
        if not self._moments:
            return None
        return self._moments[-1]

    def _compute_flow(self) -> float:
        if len(self._moments) < 2:
            return 0.0
        ts = [m.timestamp for m in self._moments]
        dt = np.diff(ts)
        if dt.size == 0:
            return 0.0
        return float(np.mean(1.0 / (dt + 1e-9)))
