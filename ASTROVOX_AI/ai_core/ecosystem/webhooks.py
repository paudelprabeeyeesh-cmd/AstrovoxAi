"""AI webhook manager."""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class AIWebhook:
    webhook_id: str
    url: str
    secret: str
    events: List[str]
    active: bool = True


class AIWebhookManager:
    def __init__(self) -> None:
        self._webhooks: Dict[str, AIWebhook] = {}

    def register(self, webhook: AIWebhook) -> None:
        self._webhooks[webhook.webhook_id] = webhook

    async def send(self, webhook_id: str, event: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        webhook = self._webhooks.get(webhook_id)
        if not webhook or not webhook.active:
            raise ValueError("webhook not found or inactive")
        return {"status": "sent", "event": event}


ai_webhook_manager = AIWebhookManager()
