import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, Dict, List, Optional


class ParallelOrchestrator:
    def __init__(self, max_workers: Optional[int] = None):
        self.max_workers = max_workers
        self.tasks: List[Callable[[], Any]] = []
        self.results: List[Any] = []
        self.barrier: Optional[threading.Barrier] = None
        self.sync_points: Dict[str, threading.Event] = {}
        self.lock = threading.Lock()

    def add_task(self, func: Callable[[], Any]) -> None:
        self.tasks.append(func)

    def set_barrier(self, parties: int) -> None:
        self.barrier = threading.Barrier(parties)

    def set_sync_point(self, name: str) -> None:
        self.sync_points[name] = threading.Event()

    def wait_sync_point(self, name: str, timeout: Optional[float] = None) -> bool:
        event = self.sync_points.get(name)
        if event is None:
            raise KeyError(f"Sync point '{name}' not defined")
        return event.wait(timeout)

    def signal_sync_point(self, name: str) -> None:
        event = self.sync_points.get(name)
        if event is None:
            raise KeyError(f"Sync point '{name}' not defined")
        event.set()

    def run(self) -> List[Any]:
        self.results = [None] * len(self.tasks)
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(func): idx for idx, func in enumerate(self.tasks)
            }
            for future in as_completed(futures):
                idx = futures[future]
                try:
                    self.results[idx] = future.result()
                except Exception as exc:
                    self.results[idx] = exc
        if self.barrier is not None:
            try:
                self.barrier.wait(timeout=1)
            except threading.BrokenBarrierError:
                pass
        return self.results
