from typing import Optional, Dict, Any, List, Callable
import threading
import queue
from datetime import datetime


class DistributedTask:
    def __init__(self, task_id: str, fn: callable, args: tuple = (), kwargs: Optional[Dict] = None, priority: int = 0):
        self.task_id = task_id
        self.fn = fn
        self.args = args
        self.kwargs = kwargs or {}
        self.priority = priority
        self.status = 'pending'
        self.created_at = datetime.now()
        self.completed_at = None
        self.result = None
        self.error = None

    def execute(self) -> Any:
        try:
            self.result = self.fn(*self.args, **self.kwargs)
            self.status = 'completed'
            self.completed_at = datetime.now()
            return self.result
        except Exception as e:
            self.error = str(e)
            self.status = 'failed'
            raise

    def to_dict(self) -> Dict[str, Any]:
        return {'task_id': self.task_id, 'status': self.status, 'priority': self.priority, 'created_at': self.created_at.isoformat(), 'completed_at': self.completed_at.isoformat() if self.completed_at else None, 'error': self.error}


class DistributedScheduler:
    def __init__(self, num_workers: int = 4, max_retries: int = 3):
        self.task_queue: queue.PriorityQueue = queue.PriorityQueue()
        self.running: Dict[str, DistributedTask] = {}
        self.completed: Dict[str, DistributedTask] = {}
        self.num_workers = num_workers
        self.max_retries = max_retries
        self.workers: List[threading.Thread] = []
        self.shutdown = threading.Event()
        self.lock = threading.Lock()
        for _ in range(num_workers):
            t = threading.Thread(target=self._worker_loop, daemon=True)
            t.start()
            self.workers.append(t)

    def submit(self, task: DistributedTask) -> str:
        self.task_queue.put((-task.priority, task.task_id, task))
        return task.task_id

    def _worker_loop(self) -> None:
        while not self.shutdown.is_set():
            try:
                _, _, task = self.task_queue.get(timeout=1.0)
                with self.lock:
                    self.running[task.task_id] = task
                task.execute()
                with self.lock:
                    self.completed[task.task_id] = task
                    del self.running[task.task_id]
                self.task_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                task.error = str(e)
                with self.lock:
                    if task.task_id in self.running:
                        del self.running[task.task_id]

    def get_status(self, task_id: str) -> Optional[str]:
        if task_id in self.running:
            return self.running[task_id].status
        if task_id in self.completed:
            return self.completed[task_id].status
        return 'not_found'

    def shutdown_scheduler(self) -> None:
        self.shutdown.set()
        for t in self.workers:
            t.join()
