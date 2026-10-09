import threading
import time
from typing import Any, Callable, Dict, List, Optional

from distributed_computing.task_queue import Task, TaskQueue
from distributed_computing.worker_node import WorkerNode


class Scheduler:
    def __init__(self, strategy: str = "fifo") -> None:
        self.strategy = strategy
        self._queue = TaskQueue()
        self._workers: Dict[str, WorkerNode] = {}
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def register_worker(self, worker: WorkerNode) -> None:
        with self._lock:
            self._workers[worker.node_id] = worker

    def submit(self, func: Callable[..., Any], *args: Any, priority: int = 0, **kwargs: Any) -> str:
        task = Task(
            priority=priority,
            task_id=str(time.time()).replace(".", "")[-8:],
            payload={"func": func, "args": args, "kwargs": kwargs},
        )
        return self._queue.enqueue(task)

    def start(self) -> None:
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        while self._running:
            task = self._queue.dequeue(timeout=0.1)
            if task is None:
                continue
            func = task.payload["func"]
            args = task.payload.get("args", [])
            kwargs = task.payload.get("kwargs", {})
            worker = self._select_worker()
            if worker is None:
                self._queue.enqueue(task)
                time.sleep(0.05)
                continue
            try:
                worker.execute(func, *args, **kwargs)
            except RuntimeError:
                self._queue.enqueue(task)
                time.sleep(0.05)

    def _select_worker(self) -> Optional[WorkerNode]:
        with self._lock:
            for w in self._workers.values():
                if w.available():
                    return w
            return None

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
        self._queue.close()
