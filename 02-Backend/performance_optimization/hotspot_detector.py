import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class HotspotReport:
    ranked: List[Dict[str, Any]]
    threshold_ms: float
    total_profiled_ms: float
    hotspot_ms: float


def _div(value: float, by: float) -> float:
    return value / by if by else 0.0


def detect_hotspots(
    records: List[Any],
    threshold_ms: float = 10.0,
) -> HotspotReport:
    ranked: List[Dict[str, Any]] = []
    total_profiled_ms = 0.0
    hotspot_ms = 0.0
    for record in records:
        total_profiled_ms += record.per_iteration_ms
    for record in records:
        if record.per_iteration_ms >= threshold_ms:
            hotspot_ms += record.per_iteration_ms
            ranked.append(
                {
                    "name": record.name,
                    "per_iteration_ms": record.per_iteration_ms,
                    "iterations": record.iterations,
                    "total_seconds": record.total_seconds,
                    "share": _div(record.per_iteration_ms, total_profiled_ms),
                }
            )
    ranked.sort(key=lambda entry: entry["per_iteration_ms"], reverse=True)
    return HotspotReport(
        ranked=ranked,
        threshold_ms=threshold_ms,
        total_profiled_ms=total_profiled_ms,
        hotspot_ms=hotspot_ms,
    )


def hotspot_summary(report: HotspotReport) -> str:
    lines = [
        f"Threshold: {report.threshold_ms:.3f} ms",
        f"Total profiled: {report.total_profiled_ms:.3f} ms",
        f"Hotspot sum: {report.hotspot_ms:.3f} ms",
    ]
    for entry in report.ranked:
        lines.append(
            f"- {entry['name']}: {entry['per_iteration_ms']:.3f} ms ({entry['share']*100:.1f}%)"
        )
    return "\n".join(lines)


def to_json(report: HotspotReport) -> str:
    return json.dumps(
        {
            "ranked": report.ranked,
            "threshold_ms": report.threshold_ms,
            "total_profiled_ms": report.total_profiled_ms,
            "hotspot_ms": report.hotspot_ms,
        }
    )
