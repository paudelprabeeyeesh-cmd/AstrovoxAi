import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class PendingApproval:
    approval_id: str
    tool_name: str
    arguments: dict
    user_id: str
    tier: str
    operation: str
    created_at: float = field(default_factory=time.time)
    ttl_seconds: float = 300.0
    status: str = "pending"
    result: Optional[dict] = None
    resolved_at: Optional[float] = None
    resolved_by: Optional[str] = None
    resolution: Optional[str] = None


class ApprovalStore:
    def __init__(self) -> None:
        self._store: Dict[str, PendingApproval] = {}
        self._lock = threading.Lock()
        self._history: List[PendingApproval] = []
        self._max_history = 1000

    def create(self, tool_name: str, arguments: dict, user_id: str, tier: str, operation: str, ttl_seconds: float = 300.0) -> PendingApproval:
        approval_id = str(uuid.uuid4())
        approval = PendingApproval(
            approval_id=approval_id,
            tool_name=tool_name,
            arguments=arguments,
            user_id=user_id,
            tier=tier,
            operation=operation,
            ttl_seconds=ttl_seconds,
        )
        with self._lock:
            self._store[approval_id] = approval
        return approval

    def get(self, approval_id: str) -> Optional[PendingApproval]:
        with self._lock:
            approval = self._store.get(approval_id)
        if approval and approval.status == "pending" and time.time() - approval.created_at > approval.ttl_seconds:
            with self._lock:
                approval.status = "expired"
            return None
        return approval

    def approve(self, approval_id: str, resolved_by: Optional[str] = None) -> Optional[PendingApproval]:
        with self._lock:
            approval = self._store.get(approval_id)
        if approval and approval.status == "pending":
            if time.time() - approval.created_at > approval.ttl_seconds:
                with self._lock:
                    approval.status = "expired"
                return None
            approval.status = "approved"
            approval.resolved_at = time.time()
            approval.resolved_by = resolved_by
            approval.resolution = "approved"
            self._archive(approval)
            return approval
        return None

    def reject(self, approval_id: str, resolved_by: Optional[str] = None) -> Optional[PendingApproval]:
        with self._lock:
            approval = self._store.get(approval_id)
        if approval and approval.status == "pending":
            approval.status = "rejected"
            approval.resolved_at = time.time()
            approval.resolved_by = resolved_by
            approval.resolution = "rejected"
            self._archive(approval)
            return approval
        return None

    def list_pending(self) -> List[PendingApproval]:
        now = time.time()
        with self._lock:
            return [
                a for a in self._store.values()
                if a.status == "pending" and now - a.created_at <= a.ttl_seconds
            ]

    def list_history(self, limit: int = 100) -> List[PendingApproval]:
        with self._lock:
            return list(self._history[-limit:])

    def get_stats(self) -> Dict[str, int]:
        now = time.time()
        with self._lock:
            pending = sum(1 for a in self._store.values() if a.status == "pending" and now - a.created_at <= a.ttl_seconds)
            expired = sum(1 for a in self._store.values() if a.status == "expired")
            approved = sum(1 for a in self._history if a.resolution == "approved")
            rejected = sum(1 for a in self._history if a.resolution == "rejected")
            return {
                "pending": pending,
                "expired": expired,
                "approved": approved,
                "rejected": rejected,
                "total": len(self._store) + len(self._history),
            }

    def cleanup_expired(self) -> None:
        now = time.time()
        with self._lock:
            expired = [aid for aid, a in self._store.items() if a.status == "pending" and now - a.created_at > a.ttl_seconds]
            for aid in expired:
                self._store[aid].status = "expired"
                self._archive(self._store[aid])

    def _archive(self, approval: PendingApproval) -> None:
        with self._lock:
            self._history.append(approval)
            if len(self._history) > self._max_history:
                self._history = self._history[-self._max_history:]


approval_store = ApprovalStore()

