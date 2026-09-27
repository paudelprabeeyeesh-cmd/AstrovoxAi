"""Benchmark suite for LLM training and inference workloads.

Tracks training loss, validation loss, perplexity, tokens/sec, GPU utilization,
GPU memory, CPU memory, disk I/O, checkpoint size, and inference latency.
Generates benchmark reports automatically (markdown + JSON) and supports
comparing multiple runs.
"""

from __future__ import annotations

import dataclasses
import datetime
import json
import math
import os
import statistics
import subprocess
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def _get_cpu_memory_mb() -> Optional[float]:
    """Return current process RSS in MB, or None if unavailable."""
    try:
        import psutil
        process = psutil.Process()
        return process.memory_info().rss / (1024 * 1024)
    except Exception:
        return None


def _get_gpu_memory_mb() -> Optional[float]:
    """Return current GPU allocated memory in MB, or None if unavailable."""
    try:
        import torch
        if torch.cuda.is_available():
            return torch.cuda.memory_allocated() / (1024 * 1024)
    except Exception:
        pass
    return None


def _get_gpu_utilization() -> Optional[float]:
    """Return current GPU utilization percentage, or None if unavailable."""
    try:
        import pynvml
        pynvml.nvmlInit()
        handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        util = pynvml.nvmlDeviceGetUtilizationRates(handle)
        return float(util.gpu)
    except Exception:
        pass
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=utilization.gpu", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=2,
        )
        if result.returncode == 0:
            lines = result.stdout.strip().split("\n")
            values = [float(line.strip()) for line in lines if line.strip()]
            if values:
                return sum(values) / len(values)
    except Exception:
        pass
    return None


def _get_disk_io_mb() -> Optional[float]:
    """Return cumulative disk I/O in MB, or None if unavailable."""
    try:
        import psutil
        io = psutil.disk_io_counters()
        if io:
            return (io.read_bytes + io.write_bytes) / (1024 * 1024)
    except Exception:
        pass
    return None


def _get_checkpoint_size_mb(path: str) -> Optional[float]:
    """Return checkpoint file size in MB, or None if unavailable."""
    try:
        return os.path.getsize(path) / (1024 * 1024)
    except Exception:
        return None


class SystemMonitor:
    """Background thread that samples system resources at a fixed interval."""

    def __init__(self, interval: float = 0.5) -> None:
        self.interval = interval
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self.samples: List[Dict[str, Any]] = []
        self._start_time: Optional[float] = None

    def start(self) -> None:
        """Start resource monitoring."""
        self._stop.clear()
        self._start_time = time.time()
        self._thread = threading.Thread(target=self._sample_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop resource monitoring."""
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)

    def _sample_loop(self) -> None:
        while not self._stop.is_set():
            sample = {
                "timestamp": round(time.time() - (self._start_time or time.time()), 3),
                "cpu_memory_mb": _get_cpu_memory_mb(),
                "gpu_memory_mb": _get_gpu_memory_mb(),
                "gpu_utilization_percent": _get_gpu_utilization(),
                "disk_io_mb": _get_disk_io_mb(),
            }
            self.samples.append(sample)
            time.sleep(self.interval)

    def summary(self) -> Dict[str, Any]:
        """Compute summary statistics from collected samples."""
        if not self.samples:
            return {}
        cpu_mems = [s["cpu_memory_mb"] for s in self.samples if s.get("cpu_memory_mb") is not None]
        gpu_mems = [s["gpu_memory_mb"] for s in self.samples if s.get("gpu_memory_mb") is not None]
        gpu_utils = [s["gpu_utilization_percent"] for s in self.samples if s.get("gpu_utilization_percent") is not None]

        summary: Dict[str, Any] = {}
        if cpu_mems:
            summary.update(
                {
                    "cpu_memory_avg_mb": round(statistics.mean(cpu_mems), 2),
                    "cpu_memory_max_mb": round(max(cpu_mems), 2),
                    "cpu_memory_min_mb": round(min(cpu_mems), 2),
                }
            )
        if gpu_mems:
            summary.update(
                {
                    "gpu_memory_avg_mb": round(statistics.mean(gpu_mems), 2),
                    "gpu_memory_max_mb": round(max(gpu_mems), 2),
                    "gpu_memory_min_mb": round(min(gpu_mems), 2),
                }
            )
        if gpu_utils:
            summary.update(
                {
                    "gpu_utilization_avg_percent": round(statistics.mean(gpu_utils), 2),
                    "gpu_utilization_max_percent": round(max(gpu_utils), 2),
                    "gpu_utilization_min_percent": round(min(gpu_utils), 2),
                }
            )
        return summary


@dataclasses.dataclass
class BenchmarkRun:
    """Container for all metrics collected during a single benchmark run."""

    run_id: str
    name: str
    timestamp: str
    config: Dict[str, Any]
    metrics: Dict[str, Any]
    system_samples: List[Dict[str, Any]] = dataclasses.field(default_factory=list)
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)


class BenchmarkSuite:
    """Manage multiple benchmark runs, comparisons, and report generation."""

    def __init__(self, output_dir: str = "benchmark_results") -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.runs: List[BenchmarkRun] = []

    def add_run(self, run: BenchmarkRun) -> None:
        """Register a new benchmark run."""
        self.runs.append(run)
        self._persist_run(run)

    def _persist_run(self, run: BenchmarkRun) -> None:
        run_path = self.output_dir / f"{run.run_id}.json"
        with open(run_path, "w") as f:
            json.dump(run.to_dict(), f, indent=2)

    def get_run(self, run_id: str) -> Optional[BenchmarkRun]:
        """Retrieve a run by ID."""
        for run in self.runs:
            if run.run_id == run_id:
                return run
        return None

    def compare_runs(self, run_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """Compare multiple runs on common numeric metrics."""
        if run_ids:
            runs = [self.get_run(rid) for rid in run_ids if self.get_run(rid)]
        else:
            runs = self.runs

        if len(runs) < 2:
            return {"error": "At least two runs are required for comparison"}

        comparison: Dict[str, Any] = {
            "runs": [run.to_dict() for run in runs],
            "metrics_comparison": {},
        }

        all_metrics: Dict[str, List[float]] = {}
        for run in runs:
            for key, value in run.metrics.items():
                if isinstance(value, (int, float)) and not math.isnan(value):
                    all_metrics.setdefault(key, []).append(float(value))

        for key, values in all_metrics.items():
            if len(values) >= 2:
                comparison["metrics_comparison"][key] = {
                    "values": values,
                    "min": min(values),
                    "max": max(values),
                    "avg": round(statistics.mean(values), 4),
                    "stddev": round(statistics.stdev(values), 4) if len(values) > 1 else 0.0,
                }

        return comparison

    def detect_memory_leaks(self, run: BenchmarkRun, threshold_mb: float = 10.0) -> Dict[str, Any]:
        """Detect potential memory leaks by analyzing sample trends."""
        result: Dict[str, Any] = {"leak_detected": False, "gpu_leak": None, "cpu_leak": None}

        gpu_samples = [s for s in run.system_samples if s.get("gpu_memory_mb") is not None]
        cpu_samples = [s for s in run.system_samples if s.get("cpu_memory_mb") is not None]

        if len(gpu_samples) >= 5:
            first = statistics.mean([s["gpu_memory_mb"] for s in gpu_samples[:3]])
            last = statistics.mean([s["gpu_memory_mb"] for s in gpu_samples[-3:]])
            increase = last - first
            if increase > threshold_mb:
                result["leak_detected"] = True
                result["gpu_leak"] = {
                    "initial_mb": round(first, 2),
                    "final_mb": round(last, 2),
                    "increase_mb": round(increase, 2),
                }

        if len(cpu_samples) >= 5:
            first = statistics.mean([s["cpu_memory_mb"] for s in cpu_samples[:3]])
            last = statistics.mean([s["cpu_memory_mb"] for s in cpu_samples[-3:]])
            increase = last - first
            if increase > threshold_mb:
                result["leak_detected"] = True
                result["cpu_leak"] = {
                    "initial_mb": round(first, 2),
                    "final_mb": round(last, 2),
                    "increase_mb": round(increase, 2),
                }

        return result

    def _compute_system_summary(self, run: BenchmarkRun) -> Dict[str, Any]:
        cpu_mems = [s["cpu_memory_mb"] for s in run.system_samples if s.get("cpu_memory_mb") is not None]
        gpu_mems = [s["gpu_memory_mb"] for s in run.system_samples if s.get("gpu_memory_mb") is not None]
        gpu_utils = [s["gpu_utilization_percent"] for s in run.system_samples if s.get("gpu_utilization_percent") is not None]

        summary: Dict[str, Any] = {}
        if cpu_mems:
            summary.update(
                {
                    "cpu_memory_avg_mb": round(statistics.mean(cpu_mems), 2),
                    "cpu_memory_max_mb": round(max(cpu_mems), 2),
                }
            )
        if gpu_mems:
            summary.update(
                {
                    "gpu_memory_avg_mb": round(statistics.mean(gpu_mems), 2),
                    "gpu_memory_max_mb": round(max(gpu_mems), 2),
                }
            )
        if gpu_utils:
            summary.update(
                {
                    "gpu_utilization_avg_percent": round(statistics.mean(gpu_utils), 2),
                    "gpu_utilization_max_percent": round(max(gpu_utils), 2),
                }
            )
        return summary

    def generate_markdown_report(self, run: BenchmarkRun, comparison: Optional[Dict[str, Any]] = None) -> str:
        """Generate a human-readable markdown report."""
        lines = [
            f"# Benchmark Report: {run.name}",
            "",
            f"- **Run ID:** {run.run_id}",
            f"- **Timestamp:** {run.timestamp}",
            f"- **Notes:** {run.notes or 'None'}",
            "",
            "## Configuration",
        ]
        for k, v in run.config.items():
            lines.append(f"- `{k}`: {v}")

        lines.extend(["", "## Metrics"])
        for k, v in run.metrics.items():
            if isinstance(v, float):
                lines.append(f"- **{k}:** {v:.4f}")
            elif isinstance(v, list):
                lines.append(f"- **{k}:** {len(v)} items")
            else:
                lines.append(f"- **{k}:** {v}")

        sys_summary = self._compute_system_summary(run)
        if sys_summary:
            lines.extend(["", "## System Resources"])
            if "cpu_memory_avg_mb" in sys_summary:
                lines.append(
                    f"- CPU Memory: avg={sys_summary['cpu_memory_avg_mb']} MB, "
                    f"max={sys_summary['cpu_memory_max_mb']} MB"
                )
            if "gpu_memory_avg_mb" in sys_summary:
                lines.append(
                    f"- GPU Memory: avg={sys_summary['gpu_memory_avg_mb']} MB, "
                    f"max={sys_summary['gpu_memory_max_mb']} MB"
                )
            if "gpu_utilization_avg_percent" in sys_summary:
                lines.append(
                    f"- GPU Utilization: avg={sys_summary['gpu_utilization_avg_percent']}%, "
                    f"max={sys_summary['gpu_utilization_max_percent']}%"
                )

        if comparison and "metrics_comparison" in comparison:
            lines.extend(["", "## Comparison"])
            for key, comp in comparison["metrics_comparison"].items():
                lines.append(
                    f"- **{key}:** avg={comp['avg']}, min={comp['min']}, max={comp['max']}"
                )

        return "\n".join(lines) + "\n"

    def generate_json_report(
        self,
        run: BenchmarkRun,
        comparison: Optional[Dict[str, Any]] = None,
        leak_report: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Generate a structured JSON report."""
        report: Dict[str, Any] = {
            "run": run.to_dict(),
            "system_summary": self._compute_system_summary(run),
        }
        if comparison:
            report["comparison"] = comparison
        if leak_report:
            report["memory_leak_analysis"] = leak_report
        return report

    def save_reports(
        self,
        run: BenchmarkRun,
        comparison: Optional[Dict[str, Any]] = None,
        leak_report: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Path, Path]:
        """Generate and save markdown and JSON reports."""
        md_content = self.generate_markdown_report(run, comparison)
        report_data = self.generate_json_report(run, comparison, leak_report)

        md_path = self.output_dir / f"{run.run_id}_report.md"
        json_path = self.output_dir / f"{run.run_id}_report.json"

        with open(md_path, "w") as f:
            f.write(md_content)
        with open(json_path, "w") as f:
            json.dump(report_data, f, indent=2)

        return md_path, json_path

    def save_comparison_report(self, comparison: Dict[str, Any]) -> Tuple[Path, Path]:
        """Save a comparison report for multiple runs."""
        lines = ["# Benchmark Comparison Report", ""]
        for run in comparison.get("runs", []):
            lines.append(f"- **{run['name']}** ({run['run_id']}): {run['timestamp']}")

        lines.extend(["", "## Metrics Comparison", ""])
        lines.append("| Metric | Avg | Min | Max | Std Dev |")
        lines.append("|--------|-----|-----|-----|---------|")
        for key, comp in comparison.get("metrics_comparison", {}).items():
            lines.append(
                f"| {key} | {comp['avg']} | {comp['min']} | {comp['max']} | {comp.get('stddev', 'N/A')} |"
            )

        md_path = self.output_dir / "comparison_report.md"
        json_path = self.output_dir / "comparison_report.json"

        with open(md_path, "w") as f:
            f.write("\n".join(lines) + "\n")
        with open(json_path, "w") as f:
            json.dump(comparison, f, indent=2)

        return md_path, json_path

    @classmethod
    def load_runs(cls, output_dir: str) -> BenchmarkSuite:
        """Load all persisted runs from an output directory."""
        suite = cls(output_dir=output_dir)
        run_dir = Path(output_dir)
        if not run_dir.exists():
            return suite
        for run_path in sorted(run_dir.glob("*.json")):
            if run_path.name.endswith("_report.json") or run_path.name.endswith("comparison_report.json"):
                continue
            try:
                with open(run_path, "r") as f:
                    data = json.load(f)
                suite.runs.append(BenchmarkRun(**data))
            except Exception:
                continue
        return suite
