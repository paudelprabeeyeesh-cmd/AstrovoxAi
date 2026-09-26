import logging
import asyncio
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)


class CleanupWorker:
    def __init__(self, interval_seconds: int = 86400, retention_days: int = 30):
        self.interval = interval_seconds
        self.retention_days = retention_days
        self.running = False
        self.task: asyncio.Task | None = None

    async def start(self):
        self.running = True
        logger.info("Cleanup worker started")
        self.task = asyncio.create_task(self._run())

    async def stop(self):
        self.running = False
        if self.task:
            self.task.cancel()
        logger.info("Cleanup worker stopped")

    async def _run(self):
        while self.running:
            try:
                await self._cleanup_old_data()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cleanup worker error: {e}")
            await asyncio.sleep(self.interval)

    async def _cleanup_old_data(self):
        cutoff = datetime.now(timezone.utc) - timedelta(days=self.retention_days)
        logger.info(f"Cleaning data older than {cutoff.isoformat()}")
        # In production, delete old records from database
        pass
