import threading

from distributed_computing.task_queue import Task, TaskQueue


def test_enqueue_dequeue():
    q = TaskQueue()
    task = Task(priority=0, task_id="t1", payload="hello")
    q.enqueue(task)
    result = q.dequeue()
    assert result is not None
    assert result.task_id == "t1"
    assert result.payload == "hello"


def test_priority_order():
    q = TaskQueue()
    q.enqueue(Task(priority=5, task_id="high", payload="h"))
    q.enqueue(Task(priority=1, task_id="low", payload="l"))
    q.enqueue(Task(priority=3, task_id="mid", payload="m"))
    first = q.dequeue()
    assert first.task_id == "low"
    second = q.dequeue()
    assert second.task_id == "mid"
    third = q.dequeue()
    assert third.task_id == "high"


def test_queue_empty_timeout():
    q = TaskQueue()
    result = q.dequeue(timeout=0.1)
    assert result is None


def test_queue_close():
    q = TaskQueue()
    q.close()
    result = q.dequeue(timeout=0.1)
    assert result is None
