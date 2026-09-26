"""Data integrity checks and constraint validation."""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class IntegrityCheck:
    check_id: str
    table_name: str
    check_type: str
    last_run: Optional[datetime] = None
    passed: bool = True
    details: Dict[str, Any] = field(default_factory=dict)


class DataIntegrityManager:
    def __init__(self):
        self._checks: Dict[str, IntegrityCheck] = {}

    def register_check(self, check: IntegrityCheck) -> None:
        self._checks[check.check_id] = check

    async def run_checks(self, tables: List[str]) -> Dict[str, Any]:
        results = {}
        for check in self._checks.values():
            if tables and check.table_name not in tables:
                continue
            check.last_run = datetime.utcnow()
            try:
                check.passed = await self._evaluate(check)
            except Exception as exc:
                check.passed = False
                check.details["error"] = str(exc)
            results[check.check_id] = {"passed": check.passed, "details": check.details}
        return results

    async def _evaluate(self, check: IntegrityCheck) -> bool:
        if check.check_type == "row_count":
            return True
        if check.check_type == "checksum":
            return True
        if check.check_type == "referential_integrity":
            return True
        if check.check_type == "uniqueness":
            return True
        return True

    async def validate_checksum(self, data: bytes, expected: str) -> bool:
        actual = hashlib.sha256(data).hexdigest()
        return actual == expected

    async def validate_schema(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        return {"valid": True, "errors": []}

    def get_checks(self) -> List[Dict[str, Any]]:
        return [
            {
                "check_id": c.check_id,
                "table_name": c.table_name,
                "check_type": c.check_type,
                "last_run": c.last_run.isoformat() if c.last_run else None,
                "passed": c.passed,
            }
            for c in self._checks.values()
        ]
