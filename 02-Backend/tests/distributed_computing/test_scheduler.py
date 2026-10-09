import threading
import time

from distributed_computing.scheduler import Scheduler
from distributed_computing.worker_node import WorkerNode


def test_register_worker():
    s = Scheduler()
    w = WorkerNode(node_id="w1", max_workers=2)
    s.register_worker(w)
    assert w.node_id in s._workers


def test_submit_and_execute():
    s = Scheduler()
    w = WorkerNode(node_id="w1", max_workers=2)
    s.register_worker(w)
    s.start()
    ready = threading.Event()

    def slow():
        ready.set()
        return "done"

    tid = s.submit(slow)
    ready.wait(timeout=2)
    time.sleep(0.2)
    assert s._queue.size() == 0
    s.stop()


def test_fifo_order():
    s = Scheduler()
    w = WorkerNode(node_id="w1", max_workers=1)
    s.register_worker(w)
    s.start()
    order = []

    def record(name):
        order.append(name)
        return name

    s.submit(record, "first", priority=0)
    s.submit(record, "second", priority=0)
    time.sleep(0.5)
    s.stop()
    assert order == ["first", "second"]
