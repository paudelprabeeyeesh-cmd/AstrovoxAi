import json
import logging
import os
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger(__name__)


@dataclass
class RetrainingConfig:
    model_path: str
    data_dir: str
    output_dir: str
    trigger_interval_hours: float = 24.0
    min_new_samples: int = 1000
    quality_threshold: float = 0.75
    rollback_threshold: float = 0.05
    max_retention: int = 5
    metrics_path: str = "retraining_metrics.jsonl"


@dataclass
class QualityReport:
    model_path: str
    score: float
    previous_score: float | None
    timestamp: float
    passed: bool
    metadata: dict[str, Any] = field(default_factory=dict)


class DataCollector:
    def __init__(self, data_dir: str) -> None:
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def collect(self, samples: list[dict[str, Any]]) -> Path:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        output_path = self.data_dir / f"samples_{timestamp}.jsonl"
        with output_path.open("w", encoding="utf-8") as f:
            for sample in samples:
                f.write(json.dumps(sample, ensure_ascii=False) + "\n")
        return output_path

    def count_total(self) -> int:
        total = 0
        for path in self.data_dir.glob("*.jsonl"):
            try:
                with path.open("r", encoding="utf-8") as f:
                    total += sum(1 for _ in f)
            except Exception as exc:
                logger.debug("Failed to count samples in %s: %s", path, exc)
        return total


class QualityMonitor:
    def __init__(self, baseline_path: str | None = None) -> None:
        self.baseline_path = baseline_path
        self._history: list[QualityReport] = []

    def evaluate(self, model_path: str, metadata: dict[str, Any] | None = None) -> QualityReport:
        previous = self._history[-1].score if self._history else None
        score = float(metadata.get("quality_score", 0.0)) if metadata else 0.0
        passed = previous is None or (score - previous) >= -0.05
        report = QualityReport(
            model_path=model_path,
            score=score,
            previous_score=previous,
            timestamp=time.time(),
            passed=passed,
            metadata=metadata or {},
        )
        self._history.append(report)
        return report

    def should_rollback(self, report: QualityReport, threshold: float) -> bool:
        if report.previous_score is None:
            return False
        return report.score < report.previous_score - threshold


class DeploymentManager:
    def __init__(self, output_dir: str, max_retention: int = 5) -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.max_retention = max_retention

    def deploy(self, model_path: str, version: str) -> Path:
        target = self.output_dir / version
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(model_path, target)
        self._prune()
        return target

    def rollback(self, current_version: str) -> Path | None:
        versions = sorted(self.output_dir.iterdir(), key=lambda p: p.stat().st_mtime)
        for path in reversed(versions):
            if path.name != current_version:
                return path
        return None

    def _prune(self) -> None:
        versions = sorted(self.output_dir.iterdir(), key=lambda p: p.stat().st_mtime)
        for old in versions[: -self.max_retention]:
            try:
                shutil.rmtree(old)
            except Exception as exc:
                logger.debug("Failed to prune old version %s: %s", old, exc)


class ContinuousRetrainer:
    def __init__(self, config: RetrainingConfig) -> None:
        self.config = config
        self.data_collector = DataCollector(config.data_dir)
        self.quality_monitor = QualityMonitor(baseline_path=config.model_path)
        self.deployment_manager = DeploymentManager(config.output_dir, max_retention=config.max_retention)
        self._last_triggered: float = 0.0
        self._current_version: str = "v1"
        self._metrics_path = Path(config.metrics_path)

    def record_metric(self, metric: dict[str, Any]) -> None:
        metric["timestamp"] = time.time()
        try:
            with self._metrics_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(metric, ensure_ascii=False) + "\n")
        except Exception as exc:
            logger.debug("Failed to record metric: %s", exc)

    def ingest(self, samples: list[dict[str, Any]]) -> int:
        path = self.data_collector.collect(samples)
        return len(samples)

    def should_trigger(self) -> bool:
        now = time.time()
        if now - self._last_triggered < self.config.trigger_interval_hours * 3600:
            return False
        total = self.data_collector.count_total()
        return total >= self.config.min_new_samples

    def train(self, train_func: Callable[[str, str], dict[str, Any]]) -> QualityReport:
        new_data_dir = str(self.data_collector.data_dir)
        output_path = str(Path(self.config.output_dir) / f"training_{int(time.time())}")
        os.makedirs(output_path, exist_ok=True)
        metadata = train_func(self.config.model_path, new_data_dir)
        score = float(metadata.get("quality_score", 0.0))
        report = self.quality_monitor.evaluate(
            model_path=output_path,
            metadata={**metadata, "quality_score": score},
        )
        self.record_metric({
            "event": "training_completed",
            "model_path": output_path,
            "score": score,
            "passed": report.passed,
        })
        if not report.passed and self.quality_monitor.should_rollback(report, self.config.rollback_threshold):
            rollback_path = self.deployment_manager.rollback(self._current_version)
            self.record_metric({
                "event": "rollback",
                "from_version": self._current_version,
                "to_version": rollback_path.name if rollback_path else None,
            })
            if rollback_path:
                self.config.model_path = str(rollback_path)
        else:
            self._current_version = f"v{int(time.time())}"
            self.deployment_manager.deploy(output_path, self._current_version)
            self.config.model_path = output_path
        self._last_triggered = time.time()
        return report
