"""Log retention policy with lifecycle management and cleanup."""

from __future__ import annotations

import os
import time
import shutil
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class RetentionAction(str, Enum):
    COMPRESS = "compress"
    ARCHIVE = "archive"
    DELETE = "delete"
    REDACT = "redact"


class LogLevel(str, Enum):
    TRACE = "trace"
    DEBUG = "debug"
    INFO = "info"
    WARN = "warn"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class RetentionRule:
    rule_id: str
    name: str
    pattern: str
    retention_days: int
    action: RetentionAction = RetentionAction.COMPRESS
    min_level: LogLevel = LogLevel.TRACE
    archive_path: Optional[str] = None
    enabled: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class RetentionStats:
    total_files: int = 0
    compressed_files: int = 0
    archived_files: int = 0
    deleted_files: int = 0
    redacted_files: int = 0
    bytes_freed: int = 0
    last_run: Optional[datetime] = None


class LogRetentionPolicy:
    _instance: Optional["LogRetentionPolicy"] = None
    _lock = threading.Lock()

    def __init__(self, base_log_dir: str = "/tmp/astravox-logs") -> None:
        self._base_log_dir = base_log_dir
        self._rules: Dict[str, RetentionRule] = {}
        self._stats = RetentionStats()
        self._lock = threading.RLock()
        self._dry_run = False
        self._redact_fn: Optional[Callable[[str], str]] = None

    @classmethod
    def get_instance(cls) -> "LogRetentionPolicy":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def add_rule(self, rule: RetentionRule) -> None:
        with self._lock:
            self._rules[rule.rule_id] = rule

    def remove_rule(self, rule_id: str) -> None:
        with self._lock:
            self._rules.pop(rule_id, None)

    def set_dry_run(self, dry_run: bool) -> None:
        with self._lock:
            self._dry_run = dry_run

    def set_redaction_fn(self, fn: Callable[[str], str]) -> None:
        with self._lock:
            self._redact_fn = fn

    def run_cleanup(self) -> RetentionStats:
        with self._lock:
            stats = RetentionStats()
            if not os.path.isdir(self._base_log_dir):
                return stats

            now = datetime.now(timezone.utc)
            entries = sorted(os.scandir(self._base_log_dir), key=lambda e: e.name)
            for entry in entries:
                if not entry.is_file():
                    continue
                file_mtime = datetime.fromtimestamp(entry.stat().st_mtime, tz=timezone.utc)
                applicable_rules = [
                    r for r in self._rules.values()
                    if r.enabled and self._matches_pattern(entry.name, r.pattern)
                    and now - file_mtime > timedelta(days=r.retention_days)
                ]
                if not applicable_rules:
                    continue
                rule = min(applicable_rules, key=lambda r: r.retention_days)
                try:
                    if rule.action == RetentionAction.COMPRESS:
                        if not entry.name.endswith(".gz"):
                            if not self._dry_run:
                                self._compress_file(entry.path)
                            stats.compressed_files += 1
                    elif rule.action == RetentionAction.ARCHIVE:
                        if rule.archive_path:
                            if not self._dry_run:
                                self._archive_file(entry.path, rule.archive_path)
                            stats.archived_files += 1
                    elif rule.action == RetentionAction.DELETE:
                        if not self._dry_run:
                            os.remove(entry.path)
                            stats.bytes_freed += entry.stat().st_size
                        stats.deleted_files += 1
                    elif rule.action == RetentionAction.REDACT:
                        if self._redact_fn and not self._dry_run:
                            self._redact_file(entry.path, self._redact_fn)
                        stats.redacted_files += 1
                    stats.total_files += 1
                except OSError:
                    continue
            stats.last_run = now
            self._stats = stats
            return stats

    def get_stats(self) -> RetentionStats:
        with self._lock:
            return self._stats

    def _matches_pattern(self, filename: str, pattern: str) -> bool:
        import fnmatch
        return fnmatch.fnmatch(filename, pattern)

    def _compress_file(self, path: str) -> None:
        import gzip
        output_path = path + ".gz"
        with open(path, "rb") as f_in, gzip.open(output_path, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)
        os.remove(path)

    def _archive_file(self, path: str, archive_dir: str) -> None:
        os.makedirs(archive_dir, exist_ok=True)
        shutil.move(path, os.path.join(archive_dir, os.path.basename(path)))

    def _redact_file(self, path: str, redact_fn: Callable[[str], str]) -> None:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        with open(path, "w", encoding="utf-8") as f:
            f.write(redact_fn(content))


log_retention = LogRetentionPolicy.get_instance()
