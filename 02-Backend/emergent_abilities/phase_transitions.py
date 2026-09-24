import numpy as np
from dataclasses import dataclass
from typing import Dict, List


@dataclass
class PhaseTransition:
    capability_name: str
    threshold: float
    pre_transition_performance: float
    post_transition_performance: float
    abruptness: float


class PhaseTransitionDetector:
    def __init__(self, smoothing_window: int = 3):
        self.smoothing_window = smoothing_window

    def detect_abrupt_jump(self, model_sizes: np.ndarray, performances: np.ndarray) -> PhaseTransition:
        sorted_idx = np.argsort(model_sizes)
        sizes = model_sizes[sorted_idx]
        perfs = performances[sorted_idx]
        if len(sizes) < 2:
            return PhaseTransition(capability_name="unknown", threshold=float(sizes[0]) if len(sizes) > 0 else 0.0,
                                   pre_transition_performance=float(perfs[0]) if len(perfs) > 0 else 0.0,
                                   post_transition_performance=float(perfs[-1]) if len(perfs) > 0 else 0.0,
                                   abruptness=0.0)
        if len(perfs) >= self.smoothing_window:
            smooth_perfs = np.convolve(perfs, np.ones(self.smoothing_window) / self.smoothing_window, mode='same')
        else:
            smooth_perfs = perfs
        diffs = np.diff(smooth_perfs)
        if len(diffs) == 0:
            return PhaseTransition(capability_name="unknown", threshold=float(sizes[0]),
                                   pre_transition_performance=float(perfs[0]),
                                   post_transition_performance=float(perfs[-1]),
                                   abruptness=0.0)
        max_gain_idx = int(np.argmax(diffs))
        threshold = float(sizes[max_gain_idx + 1])
        pre = float(smooth_perfs[max_gain_idx - 1]) if max_gain_idx > 0 else float(smooth_perfs[0])
        post = float(smooth_perfs[min(max_gain_idx + 2, len(smooth_perfs) - 1)])
        gain = float(post - pre)
        total_range = float(np.max(smooth_perfs) - np.min(smooth_perfs)) + 1e-8
        abruptness = min(1.0, gain / total_range)
        return PhaseTransition(capability_name="unknown", threshold=threshold, pre_transition_performance=pre,
                               post_transition_performance=post, abruptness=abruptness)

    def analyze_all_capabilities(self, model_sizes: np.ndarray, capability_data: Dict[str, np.ndarray]) -> List[PhaseTransition]:
        transitions = []
        for name, performances in capability_data.items():
            if len(performances) == len(model_sizes):
                transitions.append(self.detect_abrupt_jump(model_sizes, performances))
        return transitions


class CapabilityEmergenceTracker:
    def __init__(self):
        self.emergence_history: List[Dict[str, float]] = []

    def track_emergence(self, capability_name: str, model_sizes: np.ndarray, performances: np.ndarray) -> PhaseTransition:
        detector = PhaseTransitionDetector()
        transition = detector.detect_abrupt_jump(model_sizes, performances)
        transition.capability_name = capability_name
        self.emergence_history.append({
            "capability": capability_name, "threshold": transition.threshold,
            "abruptness": transition.abruptness, "gain": transition.post_transition_performance - transition.pre_transition_performance,
        })
        return transition

    def compute_emergence_rate(self) -> float:
        if not self.emergence_history:
            return 0.0
        return float(np.mean([h["abruptness"] for h in self.emergence_history]))

    def get_capability_order(self) -> List[str]:
        return [h["capability"] for h in sorted(self.emergence_history, key=lambda x: x["threshold"])]
