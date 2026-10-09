from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class PhaseTransition:
    capability_name: str
    threshold: float
    pre_transition_performance: float
    post_transition_performance: float
    abruptness: float


@dataclass
class CapabilitySuddennessReport:
    capability_name: str
    threshold: float
    pre_performance: float
    post_performance: float
    suddenness: float
    supporting_evidence: List[str]


def _mean(values: List[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def _smooth(values: List[float], window: int) -> List[float]:
    if window <= 1 or len(values) < window:
        return values[:]
    half = window // 2
    result = []
    for i in range(len(values)):
        start = max(0, i - half)
        end = min(len(values), i + half + 1)
        result.append(_mean(values[start:end]))
    return result


class CapabilitySuddennessDetector:
    def __init__(self, smoothing_window: int = 3, suddenness_threshold: float = 0.3):
        self.smoothing_window = smoothing_window
        self.suddenness_threshold = suddenness_threshold

    def detect_sudden_jump(self, model_sizes: List[float], performances: List[float], capability_name: str = "unknown") -> CapabilitySuddennessReport:
        paired = sorted(zip(model_sizes, performances), key=lambda p: p[0])
        if len(paired) < 2:
            size, perf = (paired[0] if paired else (0.0, 0.0))
            return CapabilitySuddennessReport(
                capability_name=capability_name,
                threshold=size,
                pre_performance=perf,
                post_performance=perf,
                suddenness=0.0,
                supporting_evidence=["insufficient data points"],
            )
        sizes, perfs = zip(*paired)
        sizes = list(sizes)
        perfs = list(perfs)
        smooth_perfs = _smooth(perfs, self.smoothing_window)
        diffs = [smooth_perfs[i + 1] - smooth_perfs[i] for i in range(len(smooth_perfs) - 1)]
        if not diffs:
            return CapabilitySuddennessReport(
                capability_name=capability_name,
                threshold=sizes[0],
                pre_performance=smooth_perfs[0],
                post_performance=smooth_perfs[-1],
                suddenness=0.0,
                supporting_evidence=["no detectable jump"],
            )
        max_gain_idx = diffs.index(max(diffs))
        threshold = sizes[max_gain_idx + 1]
        pre_start = max(0, max_gain_idx - 1)
        pre_end = max_gain_idx + 1
        post_start = max_gain_idx + 1
        post_end = min(len(smooth_perfs), max_gain_idx + 3)
        pre_perf = _mean(smooth_perfs[pre_start:pre_end])
        post_perf = _mean(smooth_perfs[post_start:post_end])
        gain = post_perf - pre_perf
        avg_perf = (pre_perf + post_perf) / 2.0
        if avg_perf > 1e-8:
            abruptness = min(1.0, gain / avg_perf)
        else:
            abruptness = 0.0
        evidence = [
            f"threshold at model_size={threshold:.4f}",
            f"pre-transition performance={pre_perf:.4f}",
            f"post-transition performance={post_perf:.4f}",
            f"gain={gain:.4f}, avg_perf={avg_perf:.4f}",
            f"suddenness={abruptness:.4f}",
        ]
        is_sudden = abruptness >= self.suddenness_threshold
        evidence.append(f"classified_as_sudden={is_sudden}")
        return CapabilitySuddennessReport(
            capability_name=capability_name,
            threshold=threshold,
            pre_performance=pre_perf,
            post_performance=post_perf,
            suddenness=abruptness,
            supporting_evidence=evidence,
        )

    def analyze_all_capabilities(self, model_sizes: List[float], capability_data: Dict[str, List[float]]) -> List[CapabilitySuddennessReport]:
        expected_len = len(model_sizes)
        reports = []
        for name, performances in capability_data.items():
            if len(performances) == expected_len:
                reports.append(self.detect_sudden_jump(model_sizes, performances, name))
        return reports

    def detect_gradual_vs_sudden(self, model_sizes: List[float], performances: List[float]) -> Dict[str, any]:
        report = self.detect_sudden_jump(model_sizes, performances)
        if report.suddenness >= self.suddenness_threshold:
            regime = "sudden"
        elif report.suddenness >= 0.1:
            regime = "transitional"
        else:
            regime = "gradual"
        return {
            "regime": regime,
            "suddenness": report.suddenness,
            "threshold": report.threshold,
            "pre_performance": report.pre_performance,
            "post_performance": report.post_performance,
        }


class EmergenceCapabilityTracker:
    def __init__(self):
        self.emergence_history: List[Dict[str, float]] = []

    def track_emergence(self, capability_name: str, model_sizes: List[float], performances: List[float], detector: Optional[CapabilitySuddennessDetector] = None) -> CapabilitySuddennessReport:
        if detector is None:
            detector = CapabilitySuddennessDetector()
        report = detector.detect_sudden_jump(model_sizes, performances, capability_name)
        self.emergence_history.append({
            "capability": capability_name,
            "threshold": report.threshold,
            "suddenness": report.suddenness,
            "gain": report.post_performance - report.pre_performance,
        })
        return report

    def emergence_rate(self) -> float:
        if not self.emergence_history:
            return 0.0
        return _mean([h["suddenness"] for h in self.emergence_history])

    def capability_order_by_threshold(self) -> List[str]:
        return [h["capability"] for h in sorted(self.emergence_history, key=lambda x: x["threshold"])]

    def sudden_capabilities(self, threshold: float = 0.3) -> List[str]:
        return [h["capability"] for h in self.emergence_history if h["suddenness"] >= threshold]
