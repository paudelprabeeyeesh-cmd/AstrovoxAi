import json
import csv
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from io import StringIO, BytesIO

logger = logging.getLogger(__name__)


class ExportFormat(Enum):
    JSON = "json"
    CSV = "csv"
    MARKDOWN = "markdown"
    PDF = "pdf"
    PARQUET = "parquet"


@dataclass
class AnalyticsEvent:
    event_id: str
    event_type: str
    conversation_id: str
    user_id: str
    timestamp: str
    properties: Dict[str, Any] = field(default_factory=dict)
    duration_ms: Optional[float] = None


class AnalyticsExportAdapter:
    def __init__(self, storage_client=None):
        self.storage_client = storage_client
        self._events: List[AnalyticsEvent] = []

    def record_event(self, event: AnalyticsEvent):
        self._events.append(event)

    def export_events(self, start: Optional[str] = None, end: Optional[str] = None, format: ExportFormat = ExportFormat.JSON) -> bytes:
        filtered = self._filter_events(start, end)
        if format == ExportFormat.JSON:
            return self._export_json(filtered)
        elif format == ExportFormat.CSV:
            return self._export_csv(filtered)
        elif format == ExportFormat.MARKDOWN:
            return self._export_markdown(filtered)
        else:
            raise ValueError(f"Unsupported export format: {format}")

    def export_by_conversation(self, conversation_id: str, format: ExportFormat = ExportFormat.JSON) -> bytes:
        events = [e for e in self._events if e.conversation_id == conversation_id]
        return self._serialize(events, format)

    def export_by_user(self, user_id: str, format: ExportFormat = ExportFormat.JSON) -> bytes:
        events = [e for e in self._events if e.user_id == user_id]
        return self._serialize(events, format)

    def get_summary(self, start: Optional[str] = None, end: Optional[str] = None) -> Dict[str, Any]:
        filtered = self._filter_events(start, end)
        summary = {
            "total_events": len(filtered),
            "by_type": {},
            "by_user": {},
            "average_duration_ms": 0.0,
        }
        durations = []
        for event in filtered:
            summary["by_type"][event.event_type] = summary["by_type"].get(event.event_type, 0) + 1
            summary["by_user"][event.user_id] = summary["by_user"].get(event.user_id, 0) + 1
            if event.duration_ms is not None:
                durations.append(event.duration_ms)
        if durations:
            summary["average_duration_ms"] = sum(durations) / len(durations)
        return summary

    def _filter_events(self, start: Optional[str], end: Optional[str]) -> List[AnalyticsEvent]:
        filtered = self._events
        if start:
            filtered = [e for e in filtered if e.timestamp >= start]
        if end:
            filtered = [e for e in filtered if e.timestamp <= end]
        return filtered

    def _serialize(self, events: List[AnalyticsEvent], format: ExportFormat) -> bytes:
        if format == ExportFormat.JSON:
            return self._export_json(events)
        elif format == ExportFormat.CSV:
            return self._export_csv(events)
        elif format == ExportFormat.MARKDOWN:
            return self._export_markdown(events)
        else:
            raise ValueError(f"Unsupported format: {format}")

    def _export_json(self, events: List[AnalyticsEvent]) -> bytes:
        data = [{"event_id": e.event_id, "event_type": e.event_type, "conversation_id": e.conversation_id, "user_id": e.user_id, "timestamp": e.timestamp, "properties": e.properties, "duration_ms": e.duration_ms} for e in events]
        return json.dumps(data, indent=2).encode('utf-8')

    def _export_csv(self, events: List[AnalyticsEvent]) -> bytes:
        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=["event_id", "event_type", "conversation_id", "user_id", "timestamp", "duration_ms"])
        writer.writeheader()
        for event in events:
            writer.writerow({"event_id": event.event_id, "event_type": event.event_type, "conversation_id": event.conversation_id, "user_id": event.user_id, "timestamp": event.timestamp, "duration_ms": event.duration_ms})
        return output.getvalue().encode('utf-8')

    def _export_markdown(self, events: List[AnalyticsEvent]) -> bytes:
        lines = ["# Analytics Export", f"Generated: {datetime.utcnow().isoformat()}", ""]
        lines.append(f"Total events: {len(events)}")
        lines.append("")
        for event in events:
            lines.append(f"- {event.timestamp} | {event.event_type} | {event.conversation_id} | {event.user_id}")
        return "\n".join(lines).encode('utf-8')

    def clear(self):
        self._events.clear()
