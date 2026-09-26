"""Schema migration and versioning system."""
from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class Migration:
    version: str
    name: str
    up: Callable[..., Any]
    down: Optional[Callable[..., Any]] = None
    checksum: str = ""
    applied_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.checksum:
            self.checksum = hashlib.sha256(self.name.encode()).hexdigest()


class SchemaMigrator:
    def __init__(self) -> None:
        self._migrations: List[Migration] = []
        self._applied: Dict[str, Migration] = {}
        self._current_version: str = "0.0.0"

    def register(self, migration: Migration) -> None:
        self._migrations.append(migration)
        self._migrations.sort(key=lambda m: m.version)

    async def migrate(self, target_version: Optional[str] = None) -> List[Migration]:
        target = target_version or self._migrations[-1].version if self._migrations else self._current_version
        pending = [m for m in self._migrations if m.version > self._current_version and m.version <= target]
        applied = []
        for migration in pending:
            try:
                logger.info("Applying migration %s: %s", migration.version, migration.name)
                result = await self._call(migration.up)
                migration.applied_at = datetime.now(timezone.utc)
                self._applied[migration.version] = migration
                self._current_version = migration.version
                applied.append(migration)
            except Exception:
                logger.exception("Migration %s failed", migration.version)
                if migration.down:
                    try:
                        await self._call(migration.down)
                    except Exception:
                        logger.exception("Rollback failed for migration %s", migration.version)
                raise
        return applied

    async def rollback(self, steps: int = 1) -> List[Migration]:
        rolled_back = []
        for _ in range(steps):
            last = self._applied.get(self._current_version)
            if not last or not last.down:
                break
            try:
                logger.info("Rolling back migration %s", last.version)
                await self._call(last.down)
                last.applied_at = None
                del self._applied[last.version]
                rolled_back.append(last)
                versions = sorted(self._applied.keys())
                self._current_version = versions[-1] if versions else "0.0.0"
            except Exception:
                logger.exception("Rollback failed for migration %s", last.version)
                break
        return rolled_back

    async def _call(self, func: Callable[..., Any]) -> Any:
        import inspect
        sig = inspect.signature(func)
        if asyncio.iscoroutinefunction(func):
            return await func()
        return func()

    @property
    def current_version(self) -> str:
        return self._current_version

    @property
    def pending_migrations(self) -> List[Migration]:
        return [m for m in self._migrations if m.version > self._current_version]


schema_migrator = SchemaMigrator()
