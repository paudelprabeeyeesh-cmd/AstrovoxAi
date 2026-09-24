import hashlib
import heapq
import json
import random
import threading
import time
import zlib
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple


@dataclass(order=True)
class Task:
    priority: int
    task_id: str = field(compare=False)
    payload: Any = field(compare=False)
    created_at: float = field(default_factory=time.time, compare=False)
    node_id: Optional[str] = field(default=None, compare=False)


class LoadBalancer:
    def __init__(self, strategy: str = "round_robin") -> None:
        self.strategy = strategy
        self._nodes: List[str] = []
        self._weights: Dict[str, int] = {}
        self._rr_index = 0
        self._lock = threading.Lock()

    def register_node(self, node_id: str, weight: int = 1) -> None:
        with self._lock:
            if node_id not in self._nodes:
                self._nodes.append(node_id)
            self._weights[node_id] = weight

    def unregister_node(self, node_id: str) -> None:
        with self._lock:
            if node_id in self._nodes:
                self._nodes.remove(node_id)
            self._weights.pop(node_id, None)

    def select_node(self) -> Optional[str]:
        with self._lock:
            if not self._nodes:
                return None
            if self.strategy == "round_robin":
                node = self._nodes[self._rr_index % len(self._nodes)]
                self._rr_index += 1
                return node
            if self.strategy == "weighted":
                total = sum(self._weights.get(n, 1) for n in self._nodes)
                target = random.uniform(0, total)
                cum = 0.0
                for n in self._nodes:
                    cum += self._weights.get(n, 1)
                    if cum >= target:
                        return n
                return self._nodes[-1]
            if self.strategy == "least_connections":
                return self._nodes[0]
            return self._nodes[0]


class DistributedExecutor:
    def __init__(self, num_workers: int = 4) -> None:
        self._num_workers = num_workers
        self._queues: List[deque] = [deque() for _ in range(num_workers)]
        self._processing: Dict[str, Tuple[str, float]] = {}
        self._completed: Dict[str, Any] = {}
        self._lock = threading.Lock()
        self._load_balancer = LoadBalancer(strategy="weighted")

    def submit(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> str:
        task_id = hashlib.sha256(f"{func.__name__}{time.time()}".encode()).hexdigest()[:16]
        task = Task(priority=0, task_id=task_id, payload={"func": func, "args": args, "kwargs": kwargs})
        node = self._load_balancer.select_node()
        node_index = self._nodes_to_indices().get(node, 0)
        self._queues[node_index].append(task)
        return task_id

    def _nodes_to_indices(self) -> Dict[str, int]:
        return {f"worker_{i}": i for i in range(self._num_workers)}

    def get_result(self, task_id: str, timeout: float = 5.0) -> Any:
        start = time.time()
        while time.time() - start < timeout:
            with self._lock:
                if task_id in self._completed:
                    return self._completed[task_id]
                if task_id in self._processing:
                    time.sleep(0.01)
                    continue
                return None
        return None

    def start(self) -> None:
        for i in range(self._num_workers):
            t = threading.Thread(target=self._worker_loop, args=(i,), daemon=True)
            t.start()

    def _worker_loop(self, index: int) -> None:
        while True:
            try:
                task = self._queues[index].popleft()
                func = task.payload["func"]
                args = task.payload.get("args", [])
                kwargs = task.payload.get("kwargs", {})
                with self._lock:
                    self._processing[task.task_id] = (f"worker_{index}", time.time())
                result = func(*args, **kwargs)
                with self._lock:
                    self._completed[task.task_id] = result
                    self._processing.pop(task.task_id, None)
            except IndexError:
                time.sleep(0.01)
            except Exception:
                time.sleep(0.01)

    def metrics(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "pending": sum(len(q) for q in self._queues),
                "processing": len(self._processing),
                "completed": len(self._completed),
            }
