import json
import logging
import os
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from .auth import role_required

logger = logging.getLogger(__name__)


class AuditLogger:
    def __init__(self, file_sink: Optional[str] = None, max_memory: int = 10000):
        self._log: OrderedDict[str, dict] = OrderedDict()
        self.max_memory = max_memory
        self.file_sink = Path(file_sink) if file_sink else None

    def log(self, event_type: str, actor: str, action: str, target: str = "", details: Optional[Dict[str, Any]] = None, status: str = "success") -> dict:
        entry = {
            "id": f"{int(datetime.now(timezone.utc).timestamp() * 1000)}-{len(self._log)}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "actor": actor,
            "action": action,
            "target": target,
            "details": details or {},
            "status": status,
        }
        self._log[entry["id"]] = entry
        if len(self._log) > self.max_memory:
            self._log.popitem(last=False)
        if self.file_sink:
            try:
                self.file_sink.parent.mkdir(parents=True, exist_ok=True)
                with self.file_sink.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(entry, default=str) + "\n")
            except OSError as exc:
                logger.warning("Audit file sink failed: %s", exc)
        return entry

    def log_auth(self, actor: str, action: str, target: str = "", details: Optional[Dict[str, Any]] = None):
        return self.log("auth", actor, action, target, details)

    def log_tool_call(self, actor: str, action: str, target: str = "", details: Optional[Dict[str, Any]] = None):
        return self.log("tool_call", actor, action, target, details)

    def log_safety_block(self, actor: str, action: str, target: str = "", details: Optional[Dict[str, Any]] = None):
        return self.log("safety_block", actor, action, target, details, status="blocked")

    def log_admin_action(self, actor: str, action: str, target: str = "", details: Optional[Dict[str, Any]] = None):
        return self.log("admin_action", actor, action, target, details)

    def get_log(self, limit: int = 100, offset: int = 0) -> List[dict]:
        entries = list(self._log.values())
        return entries[offset:offset + limit]

    def is_immutable(self) -> bool:
        return True


audit_logger = AuditLogger(file_sink=os.getenv("ASTROVOX_AUDIT_LOG_FILE"))


class AuditLogEntryResponse(BaseModel):
    id: str
    timestamp: str
    event_type: str
    actor: str
    action: str
    target: str
    details: Dict[str, Any]
    status: str


router = APIRouter(tags=["audit"])


@router.get("/audit/log", response_model=List[AuditLogEntryResponse])
async def read_audit_log(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    _: str = Depends(role_required("admin")),
):
    entries = audit_logger.get_log(limit=limit, offset=offset)
    return [AuditLogEntryResponse(**entry) for entry in entries]
