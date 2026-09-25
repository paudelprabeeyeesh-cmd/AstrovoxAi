from typing import Any, Optional, Dict
import queue
import threading


class DistributedTaskQueue:
    def __init__(self, max_size: int = 1000):
        self.queue = queue.Queue(maxsize=max_size)
        self.lock = threading.Lock()
        self.condition = threading.Condition(self.lock)

    def put(self, item: Any, priority: int = 0, block: bool = True, timeout: Optional[float] = None) -> None:
        with self.condition:
            self.queue.put((priority, item), block=block, timeout=timeout)
            self.condition.notify_all()

    def get(self, block: bool = True, timeout: Optional[float] = None) -> Any:
        with self.condition:
            while self.queue.empty():
                if not block:
                    return None
                if not self.condition.wait(timeout):
                    return None
            _, item = self.queue.get()
            return item

    def peek(self) -> Optional[Any]:
        with self.lock:
            if not self.queue.empty():
                _, item = self.queue.queue[0]
                return item
            return None

    def size(self) -> int:
        return self.queue.qsize()

    def clear(self) -> None:
        with self.lock:
            while not self.queue.empty():
                self.queue.get_nowait()
