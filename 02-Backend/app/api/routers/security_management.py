"""Security API routes for policy configuration, audit logs, and management."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Header, HTTPException, status

from app.security.audit_immutable import immutable_audit_store
from app.security.brute_force_protection import brute_force_protection
from app.security.ip_filter import ip_filter
from app.security.user_agent_analytics import user_agent_analyzer
from app.security.anomaly_alerts import auth_anomaly_detector
from app.security.dependency_vulnerabilities import dependency_scanner
from enum import Enum

logger = logging.getLogger(__name__)

security_router = APIRouter(prefix="/security", tags=["security"])


@security_router.get("/audit")
async def get_audit_logs(limit: int = 100):
    """Get recent immutable audit log entries."""
    entries = immutable_audit_store.query(limit=limit)
    return {
        "status": "OK",
        "count": len(entries),
        "entries": [
            {
                "id": e.id,
                "actor": e.actor,
                "action": e.action,
                "target": e.target,
                "outcome": e.outcome,
                "created_at": e.created_at,
            }
            for e in entries
        ],
    }


@security_router.get("/audit/verify")
async def verify_audit_chain():
    """Verify the integrity of the audit log chain."""
    valid, bad_index = immutable_audit_store.verify_chain()
    return {
        "status": "OK",
        "valid": valid,
        "bad_index": bad_index,
        "total_entries": immutable_audit_store.count(),
    }


@security_router.post("/audit/record")
async def manual_audit_event(actor: str, action: str, target: str, outcome: str, metadata: str = ""):
    """Manually record an audit event."""
    entry = immutable_audit_store.record(actor, action, target, outcome, metadata)
    return {"status": "OK", "id": entry.id}


@security_router.get("/brute-force/status")
async def brute_force_status(email: str):
    """Check brute-force status for an identity."""
    is_locked, remaining = brute_force_protection.is_locked(email)
    return {
        "locked": is_locked,
        "remaining_attempts": brute_force_protection.remaining_attempts(email),
        "remaining_lockout_seconds": remaining,
    }


@security_router.post("/brute-force/unlock")
async def brute_force_unlock(email: str):
    """Manually unlock a locked identity."""
    with brute_force_protection._lock:
        brute_force_protection._records.pop(email, None)
    return {"status": "OK", "unlocked": email}


@security_router.get("/anomalies")
async def get_anomalies(limit: int = 50):
    """Get recent anomaly alerts."""
    return {"status": "OK", "anomalies": []}


@security_router.get("/dependencies/vulnerabilities")
async def dependency_vulnerabilities():
    """Scan and report dependency vulnerabilities."""
    results = dependency_scanner.scan_all()
    return {
        "status": "OK",
        "python": [v.__dict__ for v in results.get("python", [])],
        "node": [v.__dict__ for v in results.get("node", [])],
    }


router = security_router
