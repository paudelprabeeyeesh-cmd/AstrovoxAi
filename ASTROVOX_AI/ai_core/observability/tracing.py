from typing import Dict, Any
import time


class ModelTracer:
    def __init__(self):
        self.traces: Dict[str, Dict[str, Any]] = {}

    def start_trace(self, trace_id: str, model_name: str) -> None:
        self.traces[trace_id] = {
            "model": model_name,
            "start_time": time.time(),
            "steps": [],
        }

    def log_step(self, trace_id: str, step: str, metadata: Dict[str, Any]) -> None:
        if trace_id in self.traces:
            self.traces[trace_id]["steps"].append({
                "step": step,
                "timestamp": time.time(),
                "metadata": metadata,
            })

    def end_trace(self, trace_id: str) -> Dict[str, Any]:
        trace = self.traces.get(trace_id)
        if trace:
            trace["end_time"] = time.time()
            trace["duration"] = trace["end_time"] - trace["start_time"]
        return trace
