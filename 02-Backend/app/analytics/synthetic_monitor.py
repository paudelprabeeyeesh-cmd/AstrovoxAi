
import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class SyntheticCheck:
    name: str
    url: str
    method: str = "GET"
    expected_status: int = 200
    timeout: float = 10.0
    headers: Dict[str, str] = field(default_factory=dict)
    body: Optional[Dict[str, Any]] = None


@dataclass
class SyntheticResult:
    name: str
    success: bool
    status_code: Optional[int] = None
    latency_ms: float = 0.0
    error: Optional[str] = None
    checked_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class SyntheticMonitor:
    def __init__(self, base_url: str = "http://localhost:8000") -> None:
        self.base_url = base_url.rstrip("/")
        self.checks: List[SyntheticCheck] = []

    def add_check(self, check: SyntheticCheck) -> None:
        self.checks.append(check)

    async def run_check(self, check: SyntheticCheck) -> SyntheticResult:
        import aiohttp
        start = time.perf_counter()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(check.method, f"{self.base_url}{check.url}", headers=check.headers, json=check.body, timeout=aiohttp.ClientTimeout(total=check.timeout)) as resp:
                    latency_ms = (time.perf_counter() - start) * 1000
                    success = resp.status == check.expected_status
                    return SyntheticResult(name=check.name, success=success, status_code=resp.status, latency_ms=latency_ms)
        except Exception as exc:
            latency_ms = (time.perf_counter() - start) * 1000
            return SyntheticResult(name=check.name, success=False, latency_ms=latency_ms, error=str(exc))

    async def run_all(self) -> List[SyntheticResult]:
        results = []
        for check in self.checks:
            results.append(await self.run_check(check))
        return results

    def run_sync(self) -> List[SyntheticResult]:
        return asyncio.get_event_loop().run_until_complete(self.run_all())
