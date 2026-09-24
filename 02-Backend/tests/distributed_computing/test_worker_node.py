import threading

from distributed_computing.worker_node import WorkerNode


def test_execute_success():
    w = WorkerNode(node_id="w1", max_workers=2)
    result = w.execute(lambda: 42)
    assert result == 42


def test_capacity_limit():
    w = WorkerNode(node_id="w2", max_workers=1)
    gate = threading.Event()

    def block():
        gate.wait()

    t = threading.Thread(target=w.execute, args=(block,))
    t.start()
    import time
    time.sleep(0.1)
    try:
        w.execute(lambda: 1)
        assert False, "Expected RuntimeError"
    except RuntimeError:
        pass
    finally:
        gate.set()
        t.join(timeout=2)


def test_available():
    w = WorkerNode(node_id="w3", max_workers=2)
    assert w.available() is True
    w.execute(lambda: 1)
    assert w.available() is True


def test_active_count():
    w = WorkerNode(node_id="w4", max_workers=2)
    assert w.active_count() == 0
    w.execute(lambda: 1)
    assert w.active_count() == 0
