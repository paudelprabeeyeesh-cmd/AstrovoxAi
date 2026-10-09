import logging
import threading
from collections import OrderedDict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class PipelineService:
    def __init__(self):
        self._steps: OrderedDict[str, dict] = OrderedDict()
        self._contexts: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def add_step(self, step_id: str, agent: str, action: str, depends_on: Optional[str] = None) -> dict:
        entry = {
            "step_id": step_id,
            "agent": agent,
            "action": action,
            "depends_on": depends_on,
            "status": "pending",
            "added_at": datetime.now(timezone.utc).isoformat(),
        }
        with self._lock:
            self._steps[step_id] = entry
        logger.info("Added pipeline step: %s", step_id)
        return entry

    def run_step(self, step_id: str, context: Optional[Dict[str, Any]] = None) -> dict:
        with self._lock:
            step = self._steps.get(step_id)
            if step is None:
                raise KeyError(f"Unknown step: {step_id}")
            if context is not None:
                self._contexts[step_id] = context
            step["status"] = "running"
            step["started_at"] = datetime.now(timezone.utc).isoformat()
            step["finished_at"] = datetime.now(timezone.utc).isoformat()
            step["status"] = "completed"
            result = {
                "step_id": step_id,
                "status": "completed",
                "agent": step["agent"],
                "action": step["action"],
                "finished_at": step["finished_at"],
            }
            logger.info("Completed pipeline step: %s", step_id)
            return result

    def get_status(self, step_id: str) -> dict:
        with self._lock:
            step = self._steps.get(step_id)
            if step is None:
                raise KeyError(f"Unknown step: {step_id}")
            return dict(step)

    def get_pipeline_metrics(self) -> dict:
        with self._lock:
            counts: Dict[str, int] = {}
            for step in self._steps.values():
                counts[step["status"]] = counts.get(step["status"], 0) + 1
            return {"steps": len(self._steps), "status_counts": counts}


pipeline_service = PipelineService()
