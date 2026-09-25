"""PagerDuty incident management integration."""

from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timezone
import requests


@dataclass
class PagerDutyConfig:
    integration_key: str
    api_token: str
    service_id: str


class PagerDutyManager:
    _config: Optional[PagerDutyConfig] = None
    _events_url = "https://events.pagerduty.com/v2/enqueue"

    @classmethod
    def initialize(cls, config: PagerDutyConfig) -> None:
        cls._config = config

    @classmethod
    def trigger_incident(cls, summary: str, severity: str = "error", source: str = "astrovox") -> Optional[str]:
        if not cls._config:
            return None
        payload = {
            "routing_key": cls._config.integration_key,
            "event_action": "trigger",
            "dedup_key": f"astrovox_{hash(summary)}",
            "payload": {
                "summary": summary,
                "severity": severity,
                "source": source,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        }
        try:
            response = requests.post(cls._events_url, json=payload, timeout=10)
            return response.json().get("dedup_key")
        except Exception:
            return None

    @classmethod
    def acknowledge(cls, incident_id: str) -> bool:
        payload = {
            "routing_key": cls._config.integration_key,
            "event_action": "acknowledge",
            "dedup_key": incident_id,
        }
        try:
            response = requests.post(cls._events_url, json=payload, timeout=10)
            return response.status_code == 202
        except Exception:
            return False

    @classmethod
    def resolve(cls, incident_id: str) -> bool:
        payload = {
            "routing_key": cls._config.integration_key,
            "event_action": "resolve",
            "dedup_key": incident_id,
        }
        try:
            response = requests.post(cls._events_url, json=payload, timeout=10)
            return response.status_code == 202
        except Exception:
            return False
