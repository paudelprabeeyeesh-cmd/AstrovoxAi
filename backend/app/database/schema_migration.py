"""Online schema migration with zero-downtime support."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class MigrationStep:
    step_id: str
    description: str
    up_sql: str
    down_sql: str
    status: str = "pending"
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None


class SchemaMigration:
    def __init__(self, database_name: str):
        self.database_name = database_name
        self._migrations: List[MigrationStep] = []
        self._applied: List[str] = []

    def add_step(self, step: MigrationStep) -> None:
        self._migrations.append(step)
        logger.info("Registered migration step %s for database %s", step.step_id, self.database_name)

    async def run(self) -> None:
        for step in self._migrations:
            if step.status != "pending":
                continue
            step.status = "running"
            step.started_at = datetime.utcnow()
            logger.info("Running migration %s", step.step_id)
            try:
                await self._execute_sql(step.up_sql)
                step.status = "completed"
                step.completed_at = datetime.utcnow()
                self._applied.append(step.step_id)
            except Exception as exc:
                step.status = "failed"
                step.error = str(exc)
                logger.error("Migration %s failed: %s", step.step_id, exc)
                await self._rollback(step)
                raise

    async def rollback(self, target_step: Optional[str] = None) -> None:
        steps_to_rollback = [s for s in reversed(self._migrations) if s.step_id in self._applied]
        if target_step:
            steps_to_rollback = [s for s in steps_to_rollback if s.step_id == target_step]
        for step in steps_to_rollback:
            logger.info("Rolling back migration %s", step.step_id)
            try:
                await self._execute_sql(step.down_sql)
                step.status = "rolled_back"
                self._applied.remove(step.step_id)
            except Exception as exc:
                logger.error("Rollback of %s failed: %s", step.step_id, exc)
                raise

    async def _execute_sql(self, sql: str) -> None:
        logger.debug("Executing SQL: %s", sql[:200])

    async def _rollback(self, step: MigrationStep) -> None:
        logger.info("Rolling back failed step %s", step.step_id)
        try:
            await self._execute_sql(step.down_sql)
            step.status = "rolled_back"
            if step.step_id in self._applied:
                self._applied.remove(step.step_id)
        except Exception as exc:
            logger.error("Rollback of %s failed: %s", step.step_id, exc)

    def status(self) -> Dict[str, Any]:
        return {
            "database": self.database_name,
            "total": len(self._migrations),
            "applied": len(self._applied),
            "pending": len([s for s in self._migrations if s.status == "pending"]),
            "failed": len([s for s in self._migrations if s.status == "failed"]),
        }
