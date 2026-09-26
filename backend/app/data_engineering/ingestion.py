"""Data ingestion pipeline for batch and streaming workloads."""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class IngestionStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class IngestionSource(Enum):
    DATABASE = "database"
    API = "api"
    FILE = "file"
    STREAM = "stream"
    MESSAGE_QUEUE = "message_queue"


@dataclass
class IngestionResult:
    source: str
    records_ingested: int
    bytes_processed: int
    checksum: str
    status: IngestionStatus
    error: Optional[str] = None
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None


@dataclass
class IngestionTask:
    task_id: str
    source_type: IngestionSource
    source_uri: str
    format: str
    options: Dict[str, Any] = field(default_factory=dict)


class DataIngestionPipeline:
    def __init__(self, output_dir: str = "/tmp/astrovox_ingestion"):
        self.output_dir = output_dir
        self._tasks: Dict[str, IngestionTask] = {}
        self._results: List[IngestionResult] = []
        os.makedirs(output_dir, exist_ok=True)

    def register_task(self, task: IngestionTask) -> None:
        self._tasks[task.task_id] = task

    async def run_task(self, task_id: str) -> IngestionResult:
        task = self._tasks.get(task_id)
        if not task:
            raise ValueError(f"Unknown ingestion task: {task_id}")
        checksum = hashlib.sha256()
        records = 0
        start = datetime.now(timezone.utc)
        try:
            for chunk in self._read_source(task):
                checksum.update(chunk)
                records += chunk.count(b"\n") if isinstance(chunk, (bytes, bytearray)) else chunk.count("\n")
            status = IngestionStatus.COMPLETED
            error = None
        except Exception as exc:
            status = IngestionStatus.FAILED
            error = str(exc)
        completed = datetime.now(timezone.utc)
        result = IngestionResult(
            source=task.source_uri,
            records_ingested=records,
            bytes_processed=checksum.digest().__len__(),
            checksum=checksum.hexdigest(),
            status=status,
            error=error,
            completed_at=completed,
        )
        self._results.append(result)
        return result

    def _read_source(self, task: IngestionTask):
        if task.source_type == IngestionSource.FILE:
            path = task.source_uri.replace("file://", "")
            with open(path, "rb") as f:
                while True:
                    chunk = f.read(1024 * 1024)
                    if not chunk:
                        break
                    yield chunk
        else:
            yield b""

    def get_results(self) -> List[IngestionResult]:
        return list(self._results)


data_ingestion_pipeline = DataIngestionPipeline()
