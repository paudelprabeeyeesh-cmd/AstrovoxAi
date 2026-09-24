import time
import tracemalloc
import numpy as np
from typing import Dict, List, Optional


class TensorProfiler:
    def __init__(self):
        self._records: List[Dict] = []
        tracemalloc.start()

    def profile(self, name, func, *args, **kwargs):
        snap_before = tracemalloc.take_snapshot()
        start = time.perf_counter()
        result = func(*args, **kwargs)
        end = time.perf_counter()
        snap_after = tracemalloc.take_snapshot()
        stats = snap_after.compare_to(snap_before, "lineno")
        mem_delta = sum(stat.size_diff for stat in stats)
        record = {
            "name": name,
            "time": end - start,
            "mem_delta": mem_delta,
            "result_shape": np.asarray(result).shape if result is not None else None,
        }
        self._records.append(record)
        return result

    def report(self) -> Dict:
        total_time = sum(r["time"] for r in self._records)
        total_mem = sum(r["mem_delta"] for r in self._records)
        return {
            "calls": len(self._records),
            "total_time": total_time,
            "total_mem_delta": total_mem,
            "records": self._records,
        }

    def reset(self):
        self._records.clear()

    def stop(self):
        tracemalloc.stop()
