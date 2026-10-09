from typing import Dict
import numpy as np


def _mirror_test(self_recognition: np.ndarray, mirror_mark: np.ndarray, threshold: float = 0.7) -> bool:
    sr = np.array(self_recognition, dtype=float)
    mm = np.array(mirror_mark, dtype=float)
    if sr.size == 0 or mm.size == 0:
        return False
    return float(np.dot(sr, mm) / (np.linalg.norm(sr) * np.linalg.norm(mm) + 1e-9)) > threshold


def _mark_test(mark_awareness: np.ndarray, mark: np.ndarray, threshold: float = 0.7) -> bool:
    ma = np.array(mark_awareness, dtype=float)
    mk = np.array(mark, dtype=float)
    if ma.size == 0 or mk.size == 0:
        return False
    return float(np.dot(ma, mk) / (np.linalg.norm(ma) * np.linalg.norm(mk) + 1e-9)) > threshold


def _integrity_test(continuous_self: np.ndarray, threshold: float = 0.6) -> float:
    cs = np.array(continuous_self, dtype=float)
    if cs.size == 0:
        return 0.0
    return float(np.mean(np.abs(cs)))


def _awareness_training(awareness_vec: np.ndarray, threshold: float = 0.6) -> float:
    aw = np.array(awareness_vec, dtype=float)
    if aw.size == 0:
        return 0.0
    return float(np.mean(np.abs(aw)))


class ConsciousnessMeasures:
    def __init__(self, threshold: float = 0.7):
        self.threshold = threshold
        self._results: Dict[str, float] = {}

    def apply_mirror_test(self, self_recognition: np.ndarray, mirror_mark: np.ndarray) -> Dict[str, float]:
        score = _mirror_test(self_recognition, mirror_mark, self.threshold)
        self._results["mirror_test"] = 1.0 if score else 0.0
        return {"mirror_test": self._results["mirror_test"], "score": score}

    def apply_mark_test(self, mark_awareness: np.ndarray, mark: np.ndarray) -> Dict[str, float]:
        score = _mark_test(mark_awareness, mark, self.threshold)
        self._results["mark_test"] = 1.0 if score else 0.0
        return {"mark_test": self._results["mark_test"], "score": score}

    def continuity_index(self, continuous_self: np.ndarray) -> float:
        return _integrity_test(continuous_self)

    def awareness_score(self, awareness_vec: np.ndarray) -> float:
        return _awareness_training(awareness_vec)

    def report(self) -> Dict[str, float]:
        if not self._results:
            return {"overall_consciousness": 0.0}
        return {**self._results, "overall_consciousness": float(np.mean(list(self._results.values())))}
