"""Digital forensics and evidence collection."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Sequence

import numpy as np


@dataclass
class EvidenceItem:
    evidence_id: str
    source: str
    data: bytes
    hash_sha256: str
    collected_at: float
    metadata: dict = field(default_factory=dict)


@dataclass
class TimelineEvent:
    timestamp: float
    source: str
    event: str
    significance: float


@dataclass
class ForensicReport:
    case_id: str
    evidence_count: int
    timeline_events: list[TimelineEvent]
    integrity_verified: bool
    summary: str


class ForensicCollector:
    def __init__(self, case_id: str | None = None) -> None:
        self.case_id = case_id or f"FOR-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        self._evidence: list[EvidenceItem] = []

    def collect(self, source: str, data: bytes, metadata: dict | None = None) -> EvidenceItem:
        sha = hashlib.sha256(data).hexdigest()
        item = EvidenceItem(
            evidence_id=f"{self.case_id}-{len(self._evidence)+1:04d}",
            source=source,
            data=data,
            hash_sha256=sha,
            collected_at=float(__import__("time").time()),
            metadata=metadata or {},
        )
        self._evidence.append(item)
        return item

    def verify_integrity(self, item: EvidenceItem) -> bool:
        return hashlib.sha256(item.data).hexdigest() == item.hash_sha256

    def collect_text(self, source: str, text: str, metadata: dict | None = None) -> EvidenceItem:
        return self.collect(source, text.encode("utf-8"), metadata)

    def build_timeline(self, events: Sequence[TimelineEvent]) -> list[TimelineEvent]:
        return sorted(events, key=lambda e: e.timestamp)

    def analyze_patterns(self, events: Sequence[TimelineEvent]) -> dict:
        if not events:
            return {"event_count": 0, "mean_significance": 0.0, "peak_hour": None}
        timestamps = np.array([e.timestamp for e in events], dtype=np.float64)
        significances = np.array([e.significance for e in events], dtype=np.float64)
        hours = (timestamps % 86400.0) / 3600.0
        peak_idx = int(np.argmax(np.bincount(np.floor(hours).astype(int), minlength=24)))
        return {
            "event_count": len(events),
            "mean_significance": float(np.mean(significances)),
            "max_significance": float(np.max(significances)),
            "std_significance": float(np.std(significances)),
            "peak_hour": peak_idx,
        }

    def generate_report(self, timeline_events: Sequence[TimelineEvent]) -> ForensicReport:
        timeline = self.build_timeline(timeline_events)
        all_verified = all(self.verify_integrity(e) for e in self._evidence) if self._evidence else True
        patterns = self.analyze_patterns(timeline)
        summary = json.dumps({
            "case_id": self.case_id,
            "evidence_items": len(self._evidence),
            "timeline_events": len(timeline),
            "patterns": patterns,
            "integrity_verified": all_verified,
        })
        return ForensicReport(
            case_id=self.case_id,
            evidence_count=len(self._evidence),
            timeline_events=timeline,
            integrity_verified=all_verified,
            summary=summary,
        )
