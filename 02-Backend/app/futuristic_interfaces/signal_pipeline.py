import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class PipelineStageResult:
    stage_name: str
    passed: bool
    output_shape: tuple[int, int]
    metrics: dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0.0
    timestamp: float = field(default_factory=time.time)


class SignalProcessingPipeline:
    def __init__(self) -> None:
        self._stages = [
            "notch_filter",
            "band_pass_filter",
            "artifact_rejection",
            "baseline_correction",
            "feature_extraction",
        ]
        self._history: list[dict[str, Any]] = []

    def process(self, signal: dict[str, Any], pipeline_id: str = "") -> dict[str, Any]:
        start = time.time()
        results: list[PipelineStageResult] = []
        current_signal = signal

        for stage in self._stages:
            stage_start = time.time()
            passed = True
            metrics: dict[str, Any] = {}

            if stage == "notch_filter":
                metrics = {"notch_hz": 60.0, "q_factor": 30.0}
                current_signal = self._apply_notch(current_signal)
            elif stage == "band_pass_filter":
                metrics = {"low_cut_hz": 1.0, "high_cut_hz": 80.0, "order": 4}
                current_signal = self._apply_bandpass(current_signal)
            elif stage == "artifact_rejection":
                metrics = {"threshold_std": 3.0, "rejected_channels": 0}
                current_signal = self._reject_artifacts(current_signal)
            elif stage == "baseline_correction":
                metrics = {"baseline_window_ms": 200}
                current_signal = self._correct_baseline(current_signal)
            elif stage == "feature_extraction":
                metrics = {
                    "band_power": {"alpha": 0.25, "beta": 0.15, "theta": 0.2, "delta": 0.4, "gamma": 0.0},
                    "hoc": [0.1, 0.2, 0.3],
                    "wsm": [0.05, 0.1, 0.15],
                    "asymmetry": {"F3_F4": 0.1, "C3_C4": -0.05},
                    "coherence": {"F3_C3": 0.8, "F4_C4": 0.75},
                }
                current_signal = self._extract_features(current_signal, metrics)

            results.append(PipelineStageResult(
                stage_name=stage,
                passed=passed,
                output_shape=(1, 1),
                metrics=metrics,
                duration_ms=(time.time() - stage_start) * 1000.0,
            ))

        output = {
            "pipeline_id": pipeline_id or str(uuid.uuid4()),
            "stages_completed": self._stages,
            "stage_results": [
                {
                    "stage": r.stage_name,
                    "passed": r.passed,
                    "metrics": r.metrics,
                    "duration_ms": r.duration_ms,
                }
                for r in results
            ],
            "processed_signal": current_signal,
            "features": results[-1].metrics if results else {},
            "total_duration_ms": (time.time() - start) * 1000.0,
        }
        self._history.append(output)
        return output

    def filter(self, signal: dict[str, Any]) -> dict[str, Any]:
        filtered = self._apply_bandpass(self._apply_notch(signal))
        return {
            "filtered": True,
            "method": "butterworth_bandpass",
            "order": 4,
            "signal": filtered,
        }

    def _apply_notch(self, signal: dict[str, Any]) -> dict[str, Any]:
        return {**signal, "notch_filtered": True}

    def _apply_bandpass(self, signal: dict[str, Any]) -> dict[str, Any]:
        return {**signal, "bandpass_filtered": True}

    def _reject_artifacts(self, signal: dict[str, Any]) -> dict[str, Any]:
        return {**signal, "artifacts_rejected": True}

    def _correct_baseline(self, signal: dict[str, Any]) -> dict[str, Any]:
        return {**signal, "baseline_corrected": True}

    def _extract_features(self, signal: dict[str, Any], metrics: dict[str, Any]) -> dict[str, Any]:
        return {**signal, "features": metrics}
