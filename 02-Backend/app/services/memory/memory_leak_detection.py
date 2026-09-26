#!/usr/bin/env python3
"""Memory leak detection harness."""
from __future__ import annotations

import gc
import logging
import sys
import tracemalloc
from typing import Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def take_snapshot() -> tracemalloc.Snapshot:
    gc.collect()
    return tracemalloc.take_snapshot()


def diff_snapshots(before: tracemalloc.Snapshot, after: tracemalloc.Snapshot) -> None:
    stats = after.compare_to(before, "lineno")
    top = stats[:20]
    if not top:
        logger.info("No significant memory growth detected")
        return
    logger.info("Top memory growths:")
    for stat in top:
        logger.info("%s: %.1f KiB", stat, stat.size_diff / 1024)


def detect_leaks(scenario_name: str, workload: Any) -> None:
    tracemalloc.start(25)
    logger.info("Starting memory leak detection for scenario: %s", scenario_name)
    before = take_snapshot()
    workload()
    after = take_snapshot()
    diff_snapshots(before, after)
    tracemalloc.stop()


def main() -> int:
    detect_leaks("baseline", lambda: None)
    return 0


if __name__ == "__main__":
    sys.exit(main())
