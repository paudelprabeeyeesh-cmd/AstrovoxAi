import threading
from typing import Dict, List, Optional

import numpy as np


class LatencyMetrics:
    def __init__(self):
        self._ttft: List[float] = []
        self._inter_token: List[float] = []
        self._total_times: List[float] = []
        self._lock = threading.Lock()

    def record_ttft(self, ms: float):
        with self._lock:
            self._ttft.append(ms)

    def record_inter_token(self, ms: float):
        with self._lock:
            self._inter_token.append(ms)

    def record_total(self, ms: float):
        with self._lock:
            self._total_times.append(ms)

    def percentile(self, values: List[float], p: float) -> Optional[float]:
        if not values:
            return None
        return float(np.percentile(values, p))

    def ttft_p50(self) -> Optional[float]:
        return self.percentile(self._ttft, 50)

    def ttft_p99(self) -> Optional[float]:
        return self.percentile(self._ttft, 99)

    def inter_token_p50(self) -> Optional[float]:
        return self.percentile(self._inter_token, 50)

    def inter_token_p99(self) -> Optional[float]:
        return self.percentile(self._inter_token, 99)

    def total_p50(self) -> Optional[float]:
        return self.percentile(self._total_times, 50)

    def total_p99(self) -> Optional[float]:
        return self.percentile(self._total_times, 99)

    def summary(self) -> Dict[str, Optional[float]]:
        return {
            "ttft_p50": self.ttft_p50(),
            "ttft_p99": self.ttft_p99(),
            "inter_token_p50": self.inter_token_p50(),
            "inter_token_p99": self.inter_token_p99(),
            "total_p50": self.total_p50(),
            "total_p99": self.total_p99(),
        }
