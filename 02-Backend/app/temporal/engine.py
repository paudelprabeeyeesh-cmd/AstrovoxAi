"""Temporal engine facade unifying all temporal subsystems.

Provides:
- Unified interface to time-travel debugging, temporal database, timelines,
  state management, and temporal AI
- Batch operations for temporal entities
- Cross-subsystem coordination
- Engine-wide statistics
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List

from app.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class TemporalOperation:
    operation_id: str
    operation_type: str
    entity_id: str
    payload: Dict[str, Any]
    actor: str
    issued_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BatchResult:
    batch_id: str
    success_count: int
    failure_count: int
    results: List[Dict[str, Any]]
    errors: List[Dict[str, Any]]
    took_ms: float
    issued_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class TemporalEngine:
    """Unified temporal engine facade.

    Wraps:
    - TimeTravelDebugger
    - TemporalDatabase
    - ConversationTimeline
    - ImmutableStateTree
    - StatePredictor
    - TimeAwareContextWindow
    - TemporalAttention
    - HistoricalPatternRecognizer
    - TimeSeriesForecaster
    - CausalChainAnalyzer
    """

    def __init__(self) -> None:
        from app.temporal import (
            TemporalDatabase,
            ImmutableStateTree,
            StatePredictor,
            TimeAwareContextWindow,
            TemporalAttention,
            HistoricalPatternRecognizer,
            TimeSeriesForecaster,
            get_debugger,
        )
        self.debugger = get_debugger("engine")
        self.db = TemporalDatabase()
        self.state_tree = ImmutableStateTree()
        self.predictor = StatePredictor()
        self.context_window = TimeAwareContextWindow()
        self.attention = TemporalAttention()
        self.pattern_recognizer = HistoricalPatternRecognizer()
        self.forecaster = TimeSeriesForecaster()
        self._lock = threading.Lock()
        self._operation_history: List[TemporalOperation] = []

    def record(self, operation: TemporalOperation) -> None:
        with self._lock:
            self._operation_history.append(operation)
            if len(self._operation_history) > 10_000:
                self._operation_history = self._operation_history[-10_000:]
        logger.debug("recorded temporal operation %s", operation.operation_id)

    def batch_apply(self, operations: List[Dict[str, Any]]) -> BatchResult:
        batch_id = f"batch-{uuid.uuid4().hex[:12]}"
        start = time.monotonic()
        results: List[Dict[str, Any]] = []
        errors: List[Dict[str, Any]] = []
        for op in operations:
            try:
                entity = self.db.apply(
                    entity_id=op["entity_id"],
                    operation=op.get("operation", "update"),
                    new_state=op.get("data", {}),
                    actor=op.get("actor", "system"),
                    entity_type=op.get("entity_type", "entity"),
                )
                self.record(TemporalOperation(
                    operation_id=f"op-{uuid.uuid4().hex[:8]}",
                    operation_type=op.get("operation", "update"),
                    entity_id=op["entity_id"],
                    payload=op.get("data", {}),
                    actor=op.get("actor", "system"),
                ))
                results.append({"entity_id": entity.entity_id, "version": entity.version})
            except Exception as exc:
                errors.append({"entity_id": op.get("entity_id"), "error": str(exc)})
        took_ms = (time.monotonic() - start) * 1000
        return BatchResult(
            batch_id=batch_id,
            success_count=len(results),
            failure_count=len(errors),
            results=results,
            errors=errors,
            took_ms=took_ms,
        )

    def batch_query(self, queries: List[Dict[str, Any]]) -> BatchResult:
        batch_id = f"batch-{uuid.uuid4().hex[:12]}"
        start = time.monotonic()
        results: List[Dict[str, Any]] = []
        errors: List[Dict[str, Any]] = []
        for q in queries:
            try:
                state = self.db.query(q["entity_id"], as_of=q.get("as_of"))
                results.append({"entity_id": q["entity_id"], "state": state})
            except Exception as exc:
                errors.append({"entity_id": q.get("entity_id"), "error": str(exc)})
        took_ms = (time.monotonic() - start) * 1000
        return BatchResult(
            batch_id=batch_id,
            success_count=len(results),
            failure_count=len(errors),
            results=results,
            errors=errors,
            took_ms=took_ms,
        )

    def snapshot_all(self) -> Dict[str, Any]:
        snapshots = {}
        for path, state in self.state_tree._latest.items():
            snapshots[path] = self.state_tree.get(path)
        return snapshots

    def restore_all(self, states: Dict[str, Dict[str, Any]]) -> None:
        for path, state in states.items():
            self.state_tree.commit(path, state)

    def predict_states(self, paths: List[str], steps: int = 1) -> Dict[str, List[Dict[str, Any]]]:
        predictions = {}
        for path in paths:
            current = self.state_tree.get(path)
            if current is not None:
                predictions[path] = self.predictor.predict(current, steps=steps)
        return predictions

    def detect_patterns(self, sequences: List[List[str]]) -> List[Dict[str, Any]]:
        for seq in sequences:
            self.pattern_recognizer.observe(seq)
        patterns = self.pattern_recognizer.detect_patterns()
        return [p.__dict__ for p in patterns]

    def forecast_series(self, series_id: str, horizon: int = 5) -> List[Tuple[datetime, float]]:
        return self.forecaster.forecast(series_id, horizon=horizon)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "debugger": self.debugger.get_stats(),
            "database": self.db.stats(),
            "state": self.state_tree.stats(),
            "operations": len(self._operation_history),
            "context_window": {"size": self.context_window.size()},
            "patterns": self.pattern_recognizer.stats(),
        }
