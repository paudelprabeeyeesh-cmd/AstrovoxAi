"""CPU profiler toggle."""

import cProfile
import logging
import pstats
import io
import threading
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger("astrovox.cpu_profiler")


class CPUProfilerToggle:
    """Toggle CPU profiling for functions or blocks of code."""

    def __init__(self) -> None:
        self._profiler: Optional[cProfile.Profile] = None
        self._results: Dict[str, pstats.Stats] = {}
        self._lock = threading.Lock()

    def start(self) -> None:
        with self._lock:
            if self._profiler is not None:
                logger.warning("Profiler already running")
                return
            self._profiler = cProfile.Profile()
            self._profiler.enable()
            logger.info("CPU profiler started")

    def stop(self, label: str = "default") -> Dict[str, Any]:
        with self._lock:
            if self._profiler is None:
                logger.warning("Profiler is not running")
                return {}
            self._profiler.disable()
            stream = io.StringIO()
            stats = pstats.Stats(self._profiler, stream=stream)
            stats.sort_stats("cumulative")
            stats.print_stats(20)
            result = {
                "label": label,
                "stats": stream.getvalue(),
                "total_calls": stats.total_calls,
                "prim_calls": stats.prim_calls,
            }
            self._results[label] = stats
            self._profiler = None
            logger.info("CPU profiler stopped for label: %s", label)
            return result

    def profile_function(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        self.start()
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            self.stop(label=getattr(func, "__name__", repr(func)))

    def get_results(self, label: str = "default") -> Optional[Dict[str, Any]]:
        with self._lock:
            stats = self._results.get(label)
            if stats is None:
                return None
            stream = io.StringIO()
            stats.sort_stats("cumulative")
            stats.print_stats(20)
            return {
                "label": label,
                "stats": stream.getvalue(),
                "total_calls": stats.total_calls,
                "prim_calls": stats.prim_calls,
            }

    def clear(self) -> None:
        with self._lock:
            self._results.clear()


cpu_profiler = CPUProfilerToggle()
