"""Chaos testing framework for resilience validation."""
import asyncio
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ChaosResult:
    name: str
    success: bool
    recovery_seconds: float
    error: str | None = None
    details: dict[str, Any] | None = None


class ChaosScenario(ABC):
    @abstractmethod
    async def inject(self) -> None:
        raise NotImplementedError

    @abstractmethod
    async def recover(self) -> None:
        raise NotImplementedError

    @abstractmethod
    async def verify(self) -> bool:
        raise NotImplementedError


class RedisKillScenario(ChaosScenario):
    def __init__(self, redis_client: Any) -> None:
        self.redis_client = redis_client

    async def inject(self) -> None:
        if self.redis_client is None:
            raise RuntimeError("Redis client not configured")
        await self.redis_client.flushall()

    async def recover(self) -> None:
        if self.redis_client is None:
            return
        try:
            await self.redis_client.ping()
        except Exception:
            await asyncio.sleep(1)
            try:
                await self.redis_client.ping()
            except Exception as exc:
                raise RuntimeError(f"Redis recovery failed: {exc}") from exc

    async def verify(self) -> bool:
        if self.redis_client is None:
            return False
        try:
            await self.redis_client.ping()
            return True
        except Exception:
            return False


class PostgresKillScenario(ChaosScenario):
    def __init__(self, db_factory: Any) -> None:
        self.db_factory = db_factory

    async def inject(self) -> None:
        if self.db_factory is None:
            raise RuntimeError("Database factory not configured")
        connection = self.db_factory()
        try:
            connection.close()
        except Exception:
            pass

    async def recover(self) -> None:
        if self.db_factory is None:
            return
        for _ in range(5):
            try:
                with self.db_factory() as connection:
                    connection.execute("SELECT 1")
                return
            except Exception:
                await asyncio.sleep(1)
        raise RuntimeError("PostgreSQL recovery failed")

    async def verify(self) -> bool:
        if self.db_factory is None:
            return False
        try:
            with self.db_factory() as connection:
                connection.execute("SELECT 1")
            return True
        except Exception:
            return False


class NetworkPartitionScenario(ChaosScenario):
    def __init__(self, http_client: Any, base_url: str) -> None:
        self.http_client = http_client
        self.base_url = base_url

    async def inject(self) -> None:
        if self.http_client is None:
            raise RuntimeError("HTTP client not configured")

    async def recover(self) -> None:
        await asyncio.sleep(1)

    async def verify(self) -> bool:
        if self.http_client is None:
            return False
        try:
            async with self.http_client.get(f"{self.base_url}/health", timeout=aiohttp.ClientTimeout(total=5)) as resp:
                return resp.status == 200
        except Exception:
            return False


class ChaosRunner:
    def __init__(self) -> None:
        self.scenarios: dict[str, ChaosScenario] = {}

    def register(self, name: str, scenario: ChaosScenario) -> None:
        self.scenarios[name] = scenario

    async def run(self, name: str, verify_after_seconds: float = 5.0) -> ChaosResult:
        scenario = self.scenarios[name]
        start = time.perf_counter()
        try:
            await scenario.inject()
            await asyncio.sleep(verify_after_seconds)
            await scenario.recover()
            ok = await scenario.verify()
            return ChaosResult(
                name=name,
                success=ok,
                recovery_seconds=time.perf_counter() - start,
            )
        except Exception as exc:
            return ChaosResult(
                name=name,
                success=False,
                recovery_seconds=time.perf_counter() - start,
                error=str(exc),
            )

    async def run_all(self, verify_after_seconds: float = 5.0) -> list[ChaosResult]:
        results = []
        for name in self.scenarios:
            results.append(await self.run(name, verify_after_seconds))
        return results
