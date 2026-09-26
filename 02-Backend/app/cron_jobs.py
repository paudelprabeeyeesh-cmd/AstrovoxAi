"""Cron jobs for scheduled execution."""

from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from croniter import croniter
import asyncio


@dataclass
class CronJob:
    job_id: str
    name: str
    cron_expression: str
    callback: Callable
    payload: Dict[str, Any] = field(default_factory=dict)
    active: bool = True
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    run_count: int = 0


class CronJobManager:
    _jobs: Dict[str, CronJob] = {}
    _running = False

    @classmethod
    def register(cls, job: CronJob) -> None:
        job.next_run = cls._get_next_run(job.cron_expression)
        cls._jobs[job.job_id] = job

    @classmethod
    def _get_next_run(cls, cron_expr: str) -> datetime:
        now = datetime.now(timezone.utc)
        cron = croniter(cron_expr, now)
        return datetime.fromtimestamp(cron.get_next(float), tz=timezone.utc)

    @classmethod
    async def run_due_jobs(cls) -> None:
        now = datetime.now(timezone.utc)
        for job in cls._jobs.values():
            if not job.active:
                continue
            if job.next_run and now >= job.next_run:
                try:
                    if asyncio.iscoroutinefunction(job.callback):
                        await job.callback(**job.payload)
                    else:
                        job.callback(**job.payload)
                    job.last_run = now
                    job.run_count += 1
                    job.next_run = cls._get_next_run(job.cron_expression)
                except Exception:
                    logger.warning("cron job %s failed", job.name, exc_info=True)

    @classmethod
    def start_scheduler(cls) -> None:
        cls._running = True
        asyncio.create_task(cls._schedule_loop())

    @classmethod
    async def _schedule_loop(cls) -> None:
        while cls._running:
            await cls.run_due_jobs()
            await asyncio.sleep(60)

    @classmethod
    def stop(cls) -> None:
        cls._running = False
