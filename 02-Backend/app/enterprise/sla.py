from typing import Optional, Dict, Any, List
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class SLATracker:
    def __init__(self, target_uptime_percent: float = 99.9):
        self.target_uptime_percent = target_uptime_percent
        self.incidents: List[Dict[str, Any]] = []
        self.start_time = datetime.utcnow()

    def record_uptime(self, duration_seconds: float, status: str = "operational") -> None:
        if status != "operational":
            self.incidents.append({
                "started_at": datetime.utcnow().isoformat(),
                "duration_seconds": duration_seconds,
                "status": status,
            })
        logger.info("Uptime recorded: %s for %s seconds", status, duration_seconds)

    def get_current_uptime(self) -> float:
        total_time = (datetime.utcnow() - self.start_time).total_seconds()
        downtime = sum(i["duration_seconds"] for i in self.incidents)
        if total_time == 0:
            return 100.0
        return ((total_time - downtime) / total_time) * 100

    def is_sla_met(self) -> bool:
        return self.get_current_uptime() >= self.target_uptime_percent

    def get_incident_report(self) -> Dict[str, Any]:
        return {
            "target_uptime": self.target_uptime_percent,
            "current_uptime": self.get_current_uptime(),
            "incidents": len(self.incidents),
            "details": self.incidents,
        }
