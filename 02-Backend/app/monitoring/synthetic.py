"""Synthetic monitoring checks."""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import aiohttp
import asyncio


class CheckStatus(Enum):
    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"


@dataclass
class HealthCheck:
    check_id: str
    name: str
    url: str
    method: str = "GET"
    expected_status: int = 200
    interval_seconds: int = 60
    timeout_seconds: int = 10
    headers: Dict[str, str] = field(default_factory=dict)
    body: Optional[str] = None


class SyntheticMonitor:
    _checks: Dict[str, HealthCheck] = {}
    _results: Dict[str, List[Dict[str, Any]]] = {}

    @classmethod
    def register_check(cls, check: HealthCheck) -> None:
        cls._checks[check.check_id] = check

    @classmethod
    async def run_check(cls, check_id: str) -> Dict[str, Any]:
        check = cls._checks.get(check_id)
        if not check:
            return {"status": CheckStatus.FAIL, "error": "Check not found"}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    check.method,
                    check.url,
                    headers=check.headers,
                    data=check.body,
                    timeout=aiohttp.ClientTimeout(total=check.timeout_seconds),
                ) as resp:
                    status = CheckStatus.PASS if resp.status == check.expected_status else CheckStatus.FAIL
                    result = {
                        "check_id": check_id,
                        "status": status.value,
                        "http_status": resp.status,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "latency_ms": 0,
                    }
                    if check_id not in cls._results:
                        cls._results[check_id] = []
                    cls._results[check_id].append(result)
                    return result
        except Exception as e:
            result = {
                "check_id": check_id,
                "status": CheckStatus.FAIL.value,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            return result

    @classmethod
    async def run_all(cls) -> List[Dict[str, Any]]:
        results = []
        for check_id in cls._checks:
            result = await cls.run_check(check_id)
            results.append(result)
        return results
